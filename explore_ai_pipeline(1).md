# Explore — 智能解析管线架构

> 日期：2026-07-09
> 主题：AI 推理管线——帧截取、调度队列、标注叠加、告警触发

---

## 1. 整体数据通路

```
                          ┌──────────┐
                          │   SRS    │
                          │  流中枢   │
                          └──┬───┬───┘
                             │   │
             RTMP audio (有声)│   │RTMP video (无声)
                             │   │
                             ▼   ▼
                    ┌───────────┐  ┌─────────────────┐
                    │  YAMNet   │  │  OpenCV 解码     │
                    │  音频分类 │  │  & 预处理        │
                    └─────┬─────┘  └────────┬────────┘
                          │                │
                          │                ▼
                          │       ┌───────────────┐
                          │       │   YOLO11 检测  │
                          │       └───────┬───────┘
                          │               │
                          │     ┌─────────┴─────────┐
                          │     │   person crop     │
                          │     └─────────┬─────────┘
                          │               │
                          │    ┌──────────┴──────────┐
                          │    │  ByteTrack UID 分配  │
                          │    └──────────┬──────────┘
                          │               │
                          │    ┌──────────┼──────────┐
                          │    │          │          │
                          │    ▼          ▼          ▼
                          │ ┌────────┐ ┌────────┐ ┌────┐
                          │ │单帧→人脸│ │T帧→SF │ │T帧→│
                          │ │识别    │ │Kine.   │ │AVA │
                          │ └───┬────┘ └───┬────┘ └──┬─┘
                          │     │          │         │
                          │     └──────────┼─────────┘
                          │               │
                          │               ▼
                          │      ┌───────────────┐
                          │      │ OpenCV 叠加标注│
                          │      │ 框/姓名/标签   │
                          │      └───────┬───────┘
                          │              │
                          │     ┌────────┴────────┐
                          │     │                 │
                          │     ▼                 ▼
                          │ ┌─────────┐   ┌──────────────┐
                          │ │ 缓存区   │   │ 加框 video 帧 │
                          │ └─────────┘   └──────┬───────┘
                          │                      │
                          │                      │
                          │                      │
                  SoundType 事件                  │
                          │                      │
                          ▼                      │
                 ┌─────────────────┐             │
                 │    告警引擎      │             │
                 │ ExceptionDef匹配 │             │
                 │ → AlertGroup    │             │
                 │ → ResponseAction│             │
                 │ → SituationEvent│             │
                 └────────┬────────┘             │
                          │                      │
                          │   ┌──────────────────┘
                          │   │
                          │   │    ┌─────────────────┐
                          │   │    │ 加框 video 帧    │
                          │   │    └────────┬────────┘
                          │   │             │
                          │   │    RTMP audio (原始，有声)
                          │   │             │
                          │   │             ▼
                          │   │    ┌──────────────────┐
                          │   │    │   FFmpeg merge   │
                          │   │    │  video + audio   │
                          │   │    └────────┬─────────┘
                          │   │             │
                          │   │             ▼ (RTMP push)
                          │   │    ┌───────────────────┐
                          │   │    │       SRS         │
                          │   │    │   View 成品流      │
                          │   │    └─────────┬─────────┘
                          │   │              │
                          │   │              ▼ (HTTP-FLV / WebRTC)
                          │   │    ┌───────────────┐
                          │   │    │   Browser     │
                          │   │    │  前端播放      │
                          │   │    └───────────────┘
                          │   │
                    (两路独立汇入合并与告警)


Browser 播放的永远是 AI 标注后的流。如需原始画面（证据留存），从缓存区读取。


## 2. 帧截取方案

```
SRS ──pull video──▶ AI 标注管线 ──▶ 加框 video ──┐
                                                 ├─▶ FFmpeg merge ──▶ SRS (标注 View 流)
SRS ──pull audio─────────────────────────────────┘
```

前端永远看到 AI 标注后的画面。需要原始画面（证据留存）时从缓存区读取——不推第二路 SRS 流。

### AI 进程：独立拉流 + 独立处理 + 产出标注帧

AI 推理作为独立进程，自己从 SRS 拉一路视频流。FFmpeg merge 管线接收 AI 产出的标注帧。

**优点**：
- 推理进程崩溃不影响主推流
- 可独立扩缩（GPU/CPU 分离部署）
- 推理结果异步写入 DB，不阻塞帧处理

**缺点**：
- 多拉一路流，带宽 ×2（同一 SRS 内网，可忽略）
- 标注流有 ~1-2 秒延迟（推理耗时 + 重编码）

### 为何不用 FFmpeg filter 插入

FFmpeg 的 `dnn` filter 或自定义 filter 可直接在编码前处理帧，但：
- 需要 C/C++ 写 filter，开发成本高
- Python 模型（PyTorch/Ultralytics/face_recognition）无法直接嵌入 FFmpeg C 进程
- GPU 资源竞争：FFmpeg 编码和 AI 推理抢显存

---

## 3. OpenCV 帧处理与标注叠加

### 从 SRS 拉流

```python
import cv2

cap = cv2.VideoCapture("rtmp://srs:1935/live/video_1")
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
```

### YOLO 坐标转换与画框

YOLO 输出归一化坐标 `(x_center, y_center, width, height)`，转像素坐标：

```python
def yolo_to_pixel(box, frame_w, frame_h):
    x_center, y_center, w, h = box
    x1 = int((x_center - w/2) * frame_w)
    y1 = int((y_center - h/2) * frame_h)
    x2 = int((x_center + w/2) * frame_w)
    y2 = int((y_center + h/2) * frame_h)
    return x1, y1, x2, y2
```

OpenCV 叠加：

```python
# 实体框
cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
# 标签
cv2.putText(frame, "张三", (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
# 时间戳
cv2.putText(frame, "2026-07-09 19:30:00", (10, height - 10), ...)
```

### 推加框流到 SRS

用 OpenCV VideoWriter（需要 ffmpeg 支持）：

```python
fourcc = cv2.VideoWriter_fourcc(*'FLV1')
out = cv2.VideoWriter(
    f"rtmp://{srs_host}:{srs_port}/view/annotated_{view_id}",
    fourcc, fps, (width, height)
)
out.write(annotated_frame)
```

或通过 FFmpeg 子进程 pipe 推流（更可控）：

```python
proc = await asyncio.create_subprocess_exec(
    "ffmpeg", "-f", "rawvideo", "-pix_fmt", "bgr24",
    "-s", f"{width}x{height}", "-r", str(fps),
    "-i", "pipe:0",
    "-c:v", "libx264", "-f", "flv",
    f"rtmp://srs/view/annotated_{view_id}",
    stdin=asyncio.subprocess.PIPE,
)
proc.stdin.write(frame.tobytes())
```

---

## 4. 人脸识别链路

```
YOLO "person" 框 → 裁剪人形区域 → OpenCV 人脸检测 → Dlib 128D 特征 → 比对 NamedPerson 库
```

### 三级判定

| 条件 | 标注 | 事件 |
|------|------|------|
| 人脸匹配 NamedPerson（已知人物） | 框上方写姓名 | 无告警（已知人员） |
| 人脸不匹配任何人 | 框上方标"陌生人" | 产生"未录入人员"告警 |
| 人形框内未检测到人脸 | 保留 YOLO 原框（"person"） | 无 |

### 人脸裁剪

```python
# YOLO 检出 person 后
person_crop = frame[y1:y2, x1:x2]  # 裁剪人形区域

# 在人形区域内做人脸检测
face_locations = face_recognition.face_locations(person_crop)

# 如果检测到人脸
if face_locations:
    face_encoding = face_recognition.face_encodings(person_crop, face_locations)[0]
    # 比对 NamedPerson 库
    matches = face_recognition.compare_faces(known_encodings, face_encoding)
```

### 性能优化

- 每 N 帧做一次人脸识别（如每 5 帧），中间帧复用上次结果
- NamedPerson 的 128D 向量在启动时一次性加载到内存
- 如果人形框太小（宽/高 < 50px），跳过人脸识别

---

## 5. SlowFast 调度队列

### 核心问题

YOLO 每帧独立检测，帧间同一个人的框需要关联。SlowFast 需要同一个人的**连续 T 帧**（通常 32-64 帧）作为输入。

### ByteTrack / DeepSORT 做跨帧追踪

不自己写 IOU 匹配——用 ByteTrack（轻量，Python 原生）：

```python
from bytetrack import BYTETracker

tracker = BYTETracker(...)

for frame in stream:
    dets = yolo(frame)  # YOLO 检出所有 person 框
    tracks = tracker.update(dets)  # ByteTrack 分配 UID
    # tracks = [(x1,y1,x2,y2, track_id, score), ...]
    
    for track in tracks:
        uid = track.track_id
        person_queue[uid].append(frame_clip)
        if len(person_queue[uid]) >= 32:
            action = slowfast(person_queue[uid])  # 送 SlowFast
            person_queue[uid].clear()
```

### 调度分拣器结构

```
YOLO + ByteTrack 产出:
  帧 N:   UID-A(x1,y1), UID-B(x2,y2)
  帧 N+1: UID-A(x1',y1'), UID-B(x2',y2')  ← ByteTrack 自动关联

→ person_clip_queues = {
    "UID-A": [clip_N, clip_N+1, ...],   ← 满了 T 帧 → SlowFast
    "UID-B": [clip_N, clip_N+1, ...],   ← 满了 T 帧 → SlowFast
  }
```

### Kinetics vs AVA：两个 SlowFast 的分工

同一个人的 T 帧 clip 同时送两个模型，但它们的输出维度不同：

| | SlowFast Kinetics | SlowFast AVA |
|---|---|---|
| **输入** | (T, C, H, W) 人形 clip | (T, C, H, W) 人形 clip + 人物框坐标 |
| **输出** | 1 个全局动作标签 | 每个人物框上的动作标签 |
| **粒度** | "这个人在做什么" | "这个人的具体动作" |
| **训练集** | Kinetics-400 (~240k 视频) | AVA 2.2 (430 个视频，60 类) |
| **映射枚举** | ActionType (15 类) | 无专属枚举，smoking 等归入异常行为 |
| **用途** | 打架/跌倒/奔跑 → ActionType 告警 | 抽烟/打电话/喝水 → 精细行为告警 |

**关键差异**：Kinetics 分类是全局的——一个 clip 输出一个 label，适合判断"这个人是站立还是跌倒"。AVA 检测是 per-box 的——每个框输出一个 label，适合判断"这个人是不是在抽烟"。Kinetics 无法告诉你"第 3 个人在抽烟"，因为它不区别人。AVA 就是为这个场景设计的。

---

## 6. 音频推理 — YAMNet

### 独立音频分支

音频和视频在 AI 管线中走两条独立的路径，结果在告警引擎汇合：

```
SRS ──pull audio──▶ YAMNet 推理 ──▶ SoundType 事件 ──┐
                                                       │
                                                       ▼
                                                  告警引擎
                                                       ▲
                                                       │
SRS ──pull video──▶ YOLO + SlowFast ──▶ EntityType/ActionType 事件
```

### 处理方式

```python
import tensorflow_hub as hub
import numpy as np

# YAMNet 模型（启动时加载一次）
yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")

# 从 SRS 拉音频流（FFmpeg 解音频 → numpy array）
# ffmpeg -i rtmp://srs/live/audio_1 -f f32le -ac 1 -ar 16000 pipe:1
audio_samples = np.frombuffer(audio_pipe.read(CHUNK_SIZE), dtype=np.float32)

# YAMNet 推理（每 0.96 秒一次）
scores, embeddings, spectrogram = yamnet_model(audio_samples)
# scores: (N, 521) — 521 个 AudioSet 类别的概率
# 筛选监控相关类
triggered_sounds = []
for sound_type in YAMNetSoundType:
    if scores[:, sound_type_audio_set_id[sound_type]].max() > 0.5:
        triggered_sounds.append(sound_type)
```

### ExceptionDef 排列组合：全或无

告警不是"有多少模态就升级多少可信度"，而是 **ExceptionDef 要求的排列组合必须全部满足才触发**。这是确定性规则，方便调试。

```
ExceptionDef "FIGHTING"   绑定: ActionType.FIGHTING + SoundType.SCREAM
                           → 两项必须同时出现（5 秒窗口内）
                           → 只检测到 FIGHTING 但不尖叫 → 不触发
                           → 只听到 SCREAM 但没打架 → 不触发

ExceptionDef "LIKELY_FIGHTING" 绑定: ActionType.FIGHTING
                                → 只要检测到打架就触发
                                → 不需要音频佐证

ExceptionDef "GUNSHOT"    绑定: SoundType.GUNSHOT
                           → 只要检测到枪声就触发
                           → 不需要视频佐证

ExceptionDef "INTRUDER"   绑定: EntityType.PERSON + face 不匹配
                           → 需要同时满足：检测到人 + 人脸不匹配库
```

**设计原则**：每条 ExceptionDef 的 `exception_entities`、`exception_actions`、`exception_sounds` 关联表定义了一个需要同时达标的组合。告警引擎每隔 N 秒检查一次：当前活跃的 EntityType/ActionType/SoundType 是否覆盖了某条规则的全部要求——覆盖则触发，不覆盖则静默。

这种模式：
- **可调试**：告警不自举——你能回溯看到"当时哪些检测满足、哪些没满足，所以这条规则没触发"
- **可梯度**：`LIKELY_FIGHTING`（只有视觉）和 `FIGHTING`（视觉+音频）可以设不同 AlertGroup 等级
- **与 DB 一致**：ExceptionDef 的关联表已经支持这种多对多绑定，告警引擎只需查表匹配

---

## 7. 告警引擎

### 触发链路

```
每个检测窗口（5 秒）:
  活跃 EntityType  = {PERSON, KNIFE, ...}
  活跃 ActionType  = {FIGHTING, RUNNING, ...}
  活跃 SoundType   = {SCREAM, ...}
  face_events       = ["陌生人", "张三", "无脸"]

  遍历 ExceptionDef:
    if  活跃集合 ⊇ def.required_entities
    AND 活跃集合 ⊇ def.required_actions
    AND 活跃集合 ⊇ def.required_sounds:
      → 触发告警

  同一 ExceptionDef 连续触发 → 去重（只保留第一条）
```

### 去重

用 `(view_id, exception_def_id, timestamp // 5s)` 去重。同一规则在同一时间窗口内不重复触发。

---

## 8. 缓存区与触发录制

`MonitorView.cache_path` 指向磁盘路径。

### 滚动缓冲区

AI 进程中始终维护一个环形缓冲区，保存最近 N 秒的加框前原始帧（默认 30s，可通过 config 配置）。超过时间窗口的帧自动删除。

### 触发录制

告警触发时，将缓冲区中从此前 N 秒到当前时刻的帧一起写入录制文件。录制持续进行直到**停止条件**满足：连续 M 秒（如 60s）无新的告警触发。

```
时间线:
  ├──[30s 缓冲区]──┤
                   ├─ 告警触发 ──────────────────────┤
                   │  写入录制文件                      │
                   │                                   │
                   │          ┌─ 连续 60s 无新告警 ─┐  │
                   │          ▼                     │  │
                   ├──────────■─────────────────────■──┤
                              ↑                     ↑
                          录制开始               录制停止
```

### 配置项

```python
# config.py
CACHE_DURATION_SECONDS: int = 30     # 缓冲区保留时长
RECORD_STOP_SILENCE_SECONDS: int = 60  # 连续无告警多少秒后停止录制
```

### 存储管理

录制文件按 `{cache_path}/view_{id}_{timestamp}.flv` 命名。超出配置的存储上限或保留天数后自动清理旧文件。具体的存储上限和保留天数后续按需加配置项。



## 9. 技术栈总览

| 层级 | 技术 | 用途 |
|------|------|------|
| 帧读取 | OpenCV VideoCapture | 从 SRS 拉 RTMP 流 |
| 目标检测 | YOLO11 (ultralytics) | 人/车/物品检测 |
| 跨帧追踪 | ByteTrack | UID 分配 |
| 人脸检测 | face_recognition / dlib | HOG + CNN 人脸定位 |
| 人脸识别 | face_recognition 128D | 特征向量比对 |
| 行为分类 | SlowFast Kinetics | 场景级行为（打架/跌倒） |
| 行为检测 | SlowFast AVA | 人物级动作（抽烟/打电话） |
| 音频分类 | YAMNet (tensorflow-hub) | 枪声/尖叫/警报 |
| 帧标注 | OpenCV | 画框/文字/时间戳 |
| 编码推流 | FFmpeg pipe / OpenCV VideoWriter | 加框流推 SRS |
| 告警触发 | ExceptionDef → AlertGroup → ResponseAction | 已有基础设施 |
| 事件记录 | SituationEvent + repo | 已有基础设施 |

---

## 10. 待定问题与详细解释

### 9.1 DeepSORT vs ByteTrack

两者解决同一个问题：跨帧追踪——把帧 N 的 "person 框 A" 和帧 N+1 的 "person 框 B" 关联为同一个人。

```
DeepSORT:
  检测 → 卡尔曼滤波预测下一帧位置 → ReID 模型提取外观特征(128D) → 匈牙利匹配
  需要额外下载 ReID 模型权重 (~50MB)
  精度高，两段式架构（检测 + 外观关联分离）
  推理速度：适合 GPU，CPU 上 ReID 特征提取较慢

ByteTrack:
  检测 → 按置信度分三档(高分/中分/低分) → 逐档 IOU 空间匹配
  不需要额外模型，纯几何运算
  推理快 3-5 倍，高分框优先匹配，低分框（遮挡/模糊）最后匹配
  MOT17 基准上和 DeepSORT 精度持平
```

**差异本质**：DeepSORT 用深度学习判断"这人长这样所以是同一个"（外观匹配），ByteTrack 用简单的"这框和上一帧的框重叠最多所以是同一人"（空间匹配）。

**监控场景适用性**：人物移动慢、帧率稳定（15fps）、遮挡少——空间匹配足够可靠。ByteTrack 不需要额外模型权重，部署更简单。

>答：建议 ByteTrack。

---

### 9.2 GPU vs CPU 推理

```
CPU 推理 (YOLO11n + SlowFast + face_recognition):
  YOLO11n         ~50ms/帧  (20fps)
  SlowFast        ~200ms/32帧 (不占主循环，~6fps 产出速率)
  face_recognition ~30ms/人脸
  标注叠加         ~5ms/帧
  FFmpeg 编码      ~10ms/帧
  ─────────────────────────────
  主循环总耗时:     ~95ms/帧 → 有效 10fps 处理速率

GPU 推理 (RTX 3060):
  YOLO11n         ~8ms/帧
  SlowFast        ~40ms/32帧
  face_recognition CPU-only (不占 GPU)
  ─────────────────────────────
  主循环总耗时:     ~23ms/帧 → 40fps+
```

**差异分析**：监控场景通常 15fps 输入。CPU 10fps 意味着每 3 帧处理 2 帧、跳 1 帧——对人眼几乎不可感知。YOLO11n 本身就是轻量模型，为 CPU 推理优化过。

**扩展考量**：单路 View CPU 够用。如果后续加到 4 路 View 同时推理（40fps 总负载），CPU 会吃力——届时再加 GPU。

>答：我的GPU有且够用。CPU倒是可以作为应急回退。
---

### 9.3 原始流与标注流的分工


```
标注 View 流 (加框):
  前端"智能视图"切换按钮
  调试时观察模型检测效果
  告警确认——看标注框判断是否是误报
  演示——展示系统 AI 能力
```



>答：直接提供一条流吧。因为需求没要求。我刚刚说保留只是方便我阅读。

---

### 9.4 SlowFast 队列满时丢弃策略

SlowFast 需要连续 T 帧（通常 32 帧）作为输入。帧来得快、模型消费慢，队列满时有两种选择：

```
FIFO 丢旧帧 (建议):
  队列: [N-3, N-2, N-1, N]  (满)
  新帧 N+1 来 → 弹出 N-3 → 入队 N+1
  队列: [N-2, N-1, N, N+1]
  
  分析的是最近的 32 帧 → "当前正在发生什么"
  适用: 实时监控，需要最新的检测结果
```

**监控场景**：需要实时性。如果队列频繁满（消费不过来），丢旧帧意味着你错过了 1 秒前的动作，但看到的是最新状态——这比等 3 秒才知道"有人在打架"好得多。

> 答： 丢旧帧（FIFO）。

---

### 9.5 音视频同步

AI 标注管线给视频加了约 80-100ms 延迟（推理 + 叠加），但音频没有经过 AI 管线，造成不同步：

```
问题: 标注视频比原始音频晚 80ms
     → 合并后嘴型比声音慢 80ms

方案 A: 标注流不带音频，前端同时拉两路
  video = 标注流 (SRS stream: view_1_annotated)
  audio = 原始 audio 流 (SRS stream: view_1_audio_only)
  HTML5 MediaStream API 合并
  ❌ audio 比 video 早 80ms，前端 CO 处理更复杂

方案 B: FFmpeg 命令行延迟音频
  ffmpeg -itsoffset 0.08 -i audio_pipe -i video_pipe ...
  ✅ 一行参数解决，不需要改架构
  ❌ 延迟量需要实测后调优

方案 C: 不做同步
  80ms 延迟人耳无法分辨（<100ms 属于"即时"感知）
  操作员看监控主要关注画面，声音辅助
  ✅ 零成本
  ❌ 如果推理延迟涨到 200ms+，人耳可感知
```

**差异**：80ms 约等于 1/12 秒。人说话时嘴型和声音的同步误差在 100ms 内不会被察觉。但 SlowFast 的 32 帧缓冲如果导致总延迟超过 200ms，就会像"配音不同步"的电影。

> 先不做同步（方案 C）。
