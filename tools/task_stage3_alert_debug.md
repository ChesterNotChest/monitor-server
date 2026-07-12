# Stage 3 任务清单 — 告警引擎调试与修复

**接手范围**: `monitor-server/src/service/alert_module/engine.py` + 5 个 EventBus 发布点
**前置**: 已有 debug 日志输出（`[AlertEngine]` + `[EventBus]` 前缀），可直接观察

---

## 一、现象

AlertEngine 启动后日志显示：

```
[AlertEngine v=1] _on_event ENTITY keys=[...] pool_sizes={'ENTITY': 274, 'ACTION': 0, ...}
[AlertEngine v=1] _check pool={'ENTITY': 274, ...} active: E=set() A=set() S=set() F=set() FE=set()
[AlertEngine v=1] _check skip: no active ids
```

- `_pool` ENTITY 堆积 274 条，其他池始终为 0
- `_collect_ids` 始终返回空集 → `_check` 每次都 skip
- 没有任何告警被触发

## 二、根因分析

两层 bug 叠加，每层都能独立导致告警永不触发：

### Bug 1: `type` 字段缺失 → 所有事件混入 ENTITY 池

**位置**: 5 个 EventBus 发布点，全部缺少 `"type"` 字段

`engine.py:59`:
```python
event_type = payload.get("type", ENTITY)  # 默认值是 ENTITY！
```

| 发布点 | 文件 | 行 | 实际 event_type | 落入池 |
|--------|------|-----|-----------------|--------|
| YOLO 检测 | `vision_yolo/detector.py` | 152 | ENTITY | ENTITY ✅ |
| 人脸识别 | `vision_face/face_recognizer.py` | 121 | FACE | **ENTITY** ❌ |
| 行为识别 | `vision_slowfast/slowfast_runner.py` | 242 | ACTION | **ENTITY** ❌ |
| 音频分类 | `audio_module/audio_yamnet.py` | 158 | SOUND | **ENTITY** ❌ |
| 围栏事件 | `vision_fence/fence_engine.py` | 136 | FENCE | **ENTITY** ❌ |

**结论**: FACE/ACTION/SOUND/FENCE 四个模块的事件全部错误地进入了 ENTITY 池。

### Bug 2: 键名不匹配 → `_collect_ids` 始终返回空集

**位置**: `engine.py:87-91` + `engine.py:186-194`

`_collect_ids` 期望的 payload key vs 发布者实际用的 key：

| 事件类型 | `_collect_ids` 期望的 key | 发布者实际的 key | 内层结构 |
|----------|--------------------------|-----------------|---------|
| ENTITY | `"entity_type_ids"` | `"entities"` | `[{"entity_type_id": int, ...}]` |
| ACTION | `"action_type_ids"` | `"actions"` | `[{"action_type_id": int, ...}]` |
| SOUND | `"sound_type_ids"` | `"sound_type"` | 单个 int（不是 list） |
| FACE | `"face_result_ids"` | `"faces"` | `[{"result_id": int, ...}]` |
| FENCE | `"fence_event_ids"` | `"fences"` | `[{"result_id": int, ...}]` |

`_collect_ids` 当前实现：
```python
def _collect_ids(self, event_type: str, key: str) -> set[int]:
    ids = set()
    for entry in self._pool[event_type]:
        val = entry.payload.get(key, [])     # key 不匹配 → 永远返回 []
        if isinstance(val, list):
            ids.update(val)                  # 即使 key 对了，list 里是 dict 不是 int
        elif isinstance(val, int):
            ids.add(val)
    return ids
```

两个子问题：
1. **key 名不对**：`payload.get("entity_type_ids", [])` 永远找不到，payload 里是 `"entities"`
2. **嵌套结构**：即使 key 对了，`"entities"` 的值是 `[{"entity_type_id": 1}, ...]`，list 元素是 dict 不是 int

### Bug 1 + Bug 2 叠加效果

即使修了 Bug 2，FACE/ACTION/SOUND/FENCE 的事件仍在 ENTITY 池里，`_collect_ids` 用对应的 key 去各自池里找，找到的是空池 → 还是空集。

**必须两个 bug 一起修。**

---

## 三、修复任务

### 3.1 发布者：补 `"type"` 字段 ✅ 简单机械

每个发布点的 payload 加一个 `"type"` 字段，值用已有的常量。

- [ ] 3.1.1 `vision_yolo/detector.py:152` — payload 加 `"type": ENTITY`
- [ ] 3.1.2 `vision_face/face_recognizer.py:121` — payload 加 `"type": FACE`
- [ ] 3.1.3 `vision_slowfast/slowfast_runner.py:242` — payload 加 `"type": ACTION`
- [ ] 3.1.4 `audio_module/audio_yamnet.py:158` — payload 加 `"type": SOUND`
- [ ] 3.1.5 `vision_fence/fence_engine.py:136` — payload 加 `"type": FENCE`

每个文件顶部已 import 常量（如 `ENTITY, FACE`），直接加到 dict 里即可。

### 3.2 `_collect_ids`：修复键名 + 支持嵌套提取

改 `engine.py:186-194` 的 `_collect_ids`，加一个 `id_key` 参数：

```python
def _collect_ids(self, event_type: str, key: str, id_key: str | None = None) -> set[int]:
    ids: set[int] = set()
    for entry in self._pool[event_type]:
        val = entry.payload.get(key, [])
        if isinstance(val, list):
            if id_key:
                for item in val:
                    if isinstance(item, dict) and id_key in item:
                        ids.add(item[id_key])
            else:
                ids.update(val)
        elif isinstance(val, int):
            ids.add(val)
    return ids
```

同时改 `_check` 中的调用（engine.py:87-91）：

```python
active_entities = self._collect_ids(ENTITY, "entities", "entity_type_id")
active_actions  = self._collect_ids(ACTION, "actions", "action_type_id")
active_sounds   = self._collect_ids(SOUND, "sound_type")        # 单个 int，不需要 id_key
active_faces    = self._collect_ids(FACE, "faces", "result_id")
active_fences   = self._collect_ids(FENCE, "fences", "result_id")
```

**注意 SOUND**: 发布者发的是单个 `"sound_type": int`，不是 list。`_collect_ids` 的 `isinstance(val, int)` 分支已覆盖。

### 3.3 YAMNet 可观测性：加 debug 日志

YAMNet 是目前唯一从未端到端验证过的 AI 模块。当前日志覆盖面几乎为零——只有报错时才能看到它。需要加以下日志点：

- [ ] 3.3.1 `run()` 入口加 `logger.info("YAMNet started view=%d audio=%s threshold=%.2f", ...)` — 确认模块启动
- [ ] 3.3.2 `_start_ffmpeg()` 成功后加 `logger.info("YAMNet ffmpeg connected view=%d", ...)` — 确认拉流成功
- [ ] 3.3.3 `_inference_loop` 每处理 N 个窗口（建议 10 个 ≈ 10s）加心跳日志：`logger.info("YAMNet alive view=%d windows=%d events=%d", ...)` — 心跳，确认推理在持续运行。累计 `events` 计数器
- [ ] 3.3.4 `_classify` 中当所有 15 类 score 都低于阈值时，每 60s 打一次 `logger.debug("YAMNet all below threshold view=%d max_score=%.3f", ...)` — 区分"没声音"和"没在跑"
- [ ] 3.3.5 已有的 `logger.exception("YAMNet error...")` 保留不动

**验收标准**: 启动后在日志里能直接回答三个问题：
1. YAMNet 启动了吗？（3.3.1）
2. YAMNet 的 ffmpeg 拉流成功了吗？（3.3.2）
3. YAMNet 在推理吗？产出 SOUND 事件了吗？（3.3.3 + EventBus 日志）

### 3.4 单元测试更新

- [ ] 3.4.1 `test_alert_engine_unit.py` — 现有测试直接调 `_match`，不经过 `_collect_ids`，可能不需要改
- [ ] 3.4.2 （可选）新增 `_collect_ids` 的单元测试，覆盖 nested dict 提取 + scalar 提取

### 3.5 验证方法

按 playbook 启动全链路后：

```powershell
# 1. 确认 YAMNet 存活
# 期望看到: YAMNet started view=1 ... → YAMNet ffmpeg connected view=1 → YAMNet alive view=1 windows=10 events=0
# 至少要看到 started + ffmpeg connected

# 2. 查看 AlertEngine 日志，确认各池都有数据
# 期望看到: pool_sizes={'ENTITY': N, 'ACTION': M, 'SOUND': K, 'FACE': P, 'FENCE': Q}
# 而不是全部挤在 ENTITY

# 3. 确认 _check 不再 skip
# 期望看到: active: E={1,2} A={3} S={4} F={2,3} FE={1}
# 而不是 E=set() A=set() S=set() F=set() FE=set()

# 4. 如果有配好的 ExceptionDef，确认 _match 能命中
# 期望看到: _match exc=1 detail={...} → MATCH
```

---

## 四、影响面评估

| 改动文件 | 改动量 | 风险 |
|----------|--------|------|
| `detector.py` | +1 行 | 零 — 只加字段，不影响下游 |
| `face_recognizer.py` | +1 行 | 零 |
| `slowfast_runner.py` | +1 行 | 零 |
| `audio_yamnet.py` | ~15 行（+type +日志） | 低 — 纯日志 + 一个字段 |
| `fence_engine.py` | +1 行 | 零 |
| `engine.py` `_collect_ids` | ~6 行改 | 低 — 逻辑扩展，向后兼容 |
| `engine.py` `_check` 调用 | 5 行改 | 低 — 参数替换 |

所有改动集中在 EventBus 发布/消费两侧，不影响管线主逻辑（检测/识别/推流）。

---

## 五、附录：数据流全貌

```
YOLO detections  →  EventBus.publish(ENTITY,  {"entities": [{"entity_type_id": N}]})    ─┐
FaceRecognizer   →  EventBus.publish(FACE,    {"faces":    [{"result_id": N}]})          ─┤
SlowFast         →  EventBus.publish(ACTION,   {"actions":  [{"action_type_id": N}]})    ─┤
YAMNet           →  EventBus.publish(SOUND,    {"sound_type": N})                        ─┤
FenceEngine      →  EventBus.publish(FENCE,    {"fences":   [{"result_id": N}]})         ─┘
                                                                                          │
                    AlertEngine._on_event ─→ 按 payload["type"] 分池                       │
                    AlertEngine._check   ─→ _collect_ids 提取活跃 ID                      │
                    AlertEngine._match   ─→ AND 条件 vs ExceptionDef                      │
                    AlertEngine._trigger ─→ SituationEvent 入库 + RECORDING keep_alive     │
```

### ID 对应关系

| 事件类型 | Payload 内层 ID 字段 | 对应 DB 表 | ExceptionDef 匹配字段 |
|----------|---------------------|-----------|----------------------|
| ENTITY | `entity_type_id` | `entity_types.id` | `exc.entities` (M2M) |
| ACTION | `action_type_id` | `action_types.id` | `exc.actions` (M2M) |
| SOUND | `sound_type` (scalar) | `sound_types.id` | `exc.sounds` (M2M) |
| FACE | `result_id` | `face_recognition_results.id` | `exc.face_result_id` |
| FENCE | `result_id` | `fence_event_types.id` | `exc.fence_event_id` |
