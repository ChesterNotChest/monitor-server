# Stage 4 任务清单 — 标注数据流修复 + 显示策略固化

**接手范围**: `monitor-server/src/service/` 下 vision_module、vision_task  
**状态**: ✅ SOUND 修复完成，显示策略文档化（2026-07-12）

---

## 一、基线确认（2026-07-12 干净重启验证）

| 模块 | 状态 | 证据 |
|------|------|------|
| SRS :1935 | ✅ | LISTENING，FrameReader connected |
| YOLO | ✅ | model loaded，Person 框正常 |
| ByteTrack | ✅ | 13+ track ID 追踪 |
| Face 识别 | ✅ | `[Direct] Face labels: {1: 'Stranger', ...}` 正确产出 |
| Action 识别 | ✅ | `[Direct] Action labels: {2: 'Standing', ...}` 正常产出 |
| NVENC 推流 | ✅ | h264_nvenc → `rtmp://127.0.0.1:1935/view/1` |
| Auto-recovery | ✅ | `recovered=1 skipped=0` |
| obs | ✅ | push FPS ~16，管线健康 |
| RECORDING | ✅ | subscriber registered |
| SOUND | ✅ | subscriber registered（本 stage 修复） |

---

## 二、已修复问题

### 2.1 SOUND 键名不匹配 ✅ (2026-07-12)

**根因**: YAMNet 发布 `"sound_type": int`，旧的 `_on_sound` 读取 `payload.get("sound_name", "")` — 键名不一致。

**修复**: 重建 `_on_sound` (`vision_task.py:30-43`)，使用正确键名 + `YAMNetSoundType` 映射：

```python
async def _on_sound(payload: dict) -> None:
    from src.constants import YAMNetSoundType
    sound_type = payload.get("sound_type")
    if sound_type is not None:
        try:
            name = YAMNetSoundType(sound_type).name.capitalize()
        except (ValueError, TypeError):
            name = str(sound_type)
        set_sound_label(name)
```

**改动文件**:
- `vision_task.py` — 新增 `_on_sound` 函数 + SOUND 订阅注册（`await event_bus.subscribe(SOUND, _on_sound)`）
- `vision_annotation.py` — 新增 `set_sound_label()` + `draw_sound_overlay()`
- `vision_pipeline.py` — `_run_loop` 中调用 `draw_sound_overlay(annotated)`

### 2.2 fire-and-forget 总线订阅 ✅ (2026-07-12)

**根因**: `vision_annotation.py` 旧代码用 `loop.create_task(event_bus.subscribe(...))` 创建 FACE/FENCE/ACTION 订阅。日志确凿证明 **FaceSub=0** — 这些订阅从未触发。

**修复**: 用户回退时彻底删除了这三个 fire-and-forget 订阅和对应的回调函数。FACE / ACTION / FENCE 标签完全依赖直接旁路（`video_ai_processor.py`）。

---

## 三、显示策略参考

### 3.1 标注框内容（YOLO Person 框）

每个检测到的人框上显示：`Person ID N [Face: X] [Fence-N] [action]`

标注通过 `_enrich_detection_labels()` 生成，写入 `Detection.label_suffix`，`draw_detections()` 单遍绘制。

代码位置：
- 富化：`vision_pipeline.py:90-139` `_enrich_detection_labels()`
- 绘制：`vision_annotation.py:109-130` `draw_detections()`

### 3.2 动作三层过滤

| 层级 | 集合 | 动作 | 显示效果 |
|------|------|------|---------|
| **压制** | `_SUPPRESSED_ACTIONS` | Walking, Standing, Sitting | **不显示** |
| **关注** | `_WATCH_ACTIONS` | Loitering, Crowding, Waving, Pointing, Hugging | **白字标签** |
| **红警** | `_RED_ALERT_ACTIONS` | Smoking, Falling, Lying_down, Fighting, Running, Climbing, Throwing, Pushing | **红框 + `! 标签`** |

过滤代码：`vision_pipeline.py:131-137`

```python
for act in action.split("|"):
    if act in _RED_ALERT_ACTIONS:
        parts.append(f"! {act}")
        det.is_red_alert = True
    elif act not in _SUPPRESSED_ACTIONS:
        parts.append(act)
```

常量定义：`vision_pipeline.py:76-87`

### 3.3 数据流架构（修复后）

```
FaceRecognizer.get_face_labels()  ──→  _face_labels.update()   (直接旁路)
SlowFast.collect_results()        ──→  _action_labels.update()  (直接旁路)
FenceEngine.check_and_publish()   ──→  _fence_labels[x] = ...   (直接旁路)
YAMNet ──→ EventBus SOUND ──→ _on_sound ──→ set_sound_label()  (总线, await)
```

**核心原则**: FACE / ACTION / FENCE 走直接旁路（一条通道，无竞争）。总线仅用于 SOUND（`await` 订阅，可靠）和 RECORDING（`await` 订阅，可靠）。

### 3.4 音频事件显示

| 属性 | 值 |
|------|-----|
| 位置 | 左下角，半透明黑底 + 红字 |
| 格式 | `SOUND: Gunshot (3s ago)` |
| 持久性 | **常驻** — 最后一次检测结果一直显示，直到新事件覆盖或管线停止 |
| 代码 | `vision_annotation.py` `draw_sound_overlay()` + `set_sound_label()` |

YAMNet 发布 `{"sound_type": int, "score": float}` → `_on_sound` 映射为 `YAMNetSoundType.name.capitalize()` → `set_sound_label()` → `draw_sound_overlay()` 绘制。

### 3.5 YOLO 实体框颜色

| 实体 | 颜色 | 备注 |
|------|------|------|
| Person | 绿色 `(0,255,0)` | 正常 |
| Person（红警行为） | **红色 `(0,0,255)`** | `det.is_red_alert = True` |
| Knife / 其他物品 | 红色 `(0,0,255)` | COCO 12 类中非 Person 类 |

代码：`vision_annotation.py:99-103` `_bbox_color()`，检测红警由 `vision_pipeline.py:134` 设置。

### 3.6 16 类 SlowFast 动作枚举

| ID | 枚举 | 显示名 | 策略 |
|----|------|--------|------|
| 1 | WALKING | Walking | 压制 |
| 2 | RUNNING | Running | 红警 |
| 3 | FALLING | Falling | 红警 |
| 4 | FIGHTING | Fighting | 红警 |
| 5 | CLIMBING | Climbing | 红警 |
| 6 | THROWING | Throwing | 红警 |
| 7 | POINTING | Pointing | 关注 |
| 8 | WAVING | Waving | 关注 |
| 9 | HUGGING | Hugging | 关注 |
| 10 | PUSHING | Pushing | 红警 |
| 11 | SITTING | Sitting | 压制 |
| 12 | STANDING | Standing | 压制 |
| 13 | SMOKING | Smoking | 红警 |
| 14 | LYING_DOWN | Lying_down | 红警 |
| 15 | LOITERING | Loitering | 关注 |
| 16 | CROWDING | Crowding | 关注 |

### 3.7 15 类 YAMNet 声音枚举

| ID | 枚举 | 显示名 |
|----|------|--------|
| 0 | GUNSHOT | Gunshot |
| 1 | SCREAM | Scream |
| 2 | SIREN | Siren |
| 3 | EXPLOSION | Explosion |
| 4 | GLASS_BREAKING | Glass_breaking |
| 5 | DOG_BARKING | Dog_barking |
| 6 | CAR_HORN | Car_horn |
| 7 | ENGINE | Engine |
| 8 | BABY_CRYING | Baby_crying |
| 9 | ALARM | Alarm |
| 10 | THUNDER | Thunder |
| 11 | WIND | Wind |
| 12 | RAIN | Rain |
| 13 | FOOTSTEPS | Footsteps |
| 14 | SILENCE | Silence |

---

## 四、待修复（Stage 5）

- [ ] `_face_labels` / `_action_labels` 使用 `update()` 不清理旧 track → 改用 `clear()` + `update()` 或全量赋值
- [ ] AlertEngine `type` 字段缺失 → 所有事件落入 ENTITY 池（详见 `task_stage3_alert_debug.md`）
