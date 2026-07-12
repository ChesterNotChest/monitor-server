## Context

Smoke test (`test_replay_smoke.py`) 用 OpenCV 生成测试帧 → FrameRingBuffer → RecordingSession → FFmpeg → .flv 产物。验证了环形缓存和录制启停正常，但暴露帧格式和 mapper 两个 bug。

## Decisions

### 1. FrameRingBuffer 加 `format` 参数

```python
class FrameRingBuffer:
    def __init__(self, max_seconds=30, fps=25, format="raw_bgr24"):
        self.format = format  # "raw_bgr24" | "jpeg"
```

### 2. FFmpeg 命令按格式分支

```
format == "raw_bgr24":
  ffmpeg -f rawvideo -pix_fmt bgr24 -s WxH -r FPS -i pipe:0 -c:v libx264 -f flv OUT

format == "jpeg":
  ffmpeg -f image2pipe -c:v mjpeg -i pipe:0 -c:v copy -f flv OUT
```

JPEG 模式用 `-c:v copy` 避免重编码，零质量损失。

### 3. RecordingRepo.create() 用原生 INSERT

绕过 ORM mapper 配置问题。`Recording` 模型无 relationship，纯 INSERT 即可。

```python
def create(self, view_id, file_path, start_time, end_time):
    stmt = insert(Recording).values(view_id=view_id, file_path=file_path,
                                     start_time=start_time, end_time=end_time)
    self.db.execute(stmt)
    self.db.commit()
```
