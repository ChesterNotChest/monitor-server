# 任务1 - 关于编码模式优化与兼容修复

**接手范围**: conda 环境、ffmpeg 编码器参数、WAL 文件清理、启动可靠性
**依赖**: 需要显卡 RTX 4060 ；不需要改 Python 代码

---

## 一、上下文

AI 管线全链路已打通。coding 层面的主要 Bug 已有修复。剩下的是环境层面的稳定性和性能调优，全部落在 conda 环境配置、ffmpeg 编码器选型、和启动流程上。

---

## 二、NVENC 编码器参数调试（换成GPU编码）

### 背景

Server 的 AI 合流当前用 `libx264` CPU 软编，每帧编码延迟 ~20-30ms，是整条管线最大的单点瓶颈。RTX 4060 有独立 NVENC 编码芯片（与 YOLO 用的 CUDA Core 是不同硬件单元，互不抢占），换 NVENC 后编码延迟降到 ~2ms。

### 当前状态

之前裸 `-c:v h264_nvenc` 测试时 ffmpeg 进程断开（`ConnectionResetError`），原因是缺少 preset 参数。

### 需要做的事

1. 在开发机上手动测试 NVENC 推流稳定性：

```powershell
# 先确保 RTMP :1935 和 :1936 都在跑
# 然后手动模拟 AI 合流（用静态图片代替 pipe）
ffmpeg -f lavfi -i testsrc2=size=640x480:rate=15 -i rtmp://127.0.0.1:1935/live/<audio_stream_name> \
  -c:v h264_nvenc -preset p1 -tune ll -b:v 2M -rc vbr \
  -c:a aac -f flv rtmp://127.0.0.1:1936/view/test
```

2. 用 ffprobe 验证流可播放，VLC 确认画面正常。

3. 让该命令持续运行 5 分钟以上，确认不崩溃。

4. 测试不同的 preset/tune 组合，找到最稳定的那一组：

| preset | 延迟 | 画质 | 说明 |
|--------|------|------|------|
| p1 | 最低 | 最低 | 首选（low latency） |
| p2 | 低 | 中 | p1 不稳定时的回退 |
| p3 | 中 | 高 | 最后的回退 |

5. 确认最终可用参数后，告知 Server 管线域写入 `vision_merger.py`。

### 验证命令

```bash
ffprobe -v quiet -show_entries stream=codec_name,codec_type "rtmp://127.0.0.1:1936/view/test"
# 期望输出: codec_name=h264, codec_type=video
```

---

## 三、dlib + face_recognition 兼容修复

### 背景

人脸特征提取在调用 `face_recognition.face_encodings()` 时崩溃：

```
TypeError: compute_face_descriptor(): incompatible function arguments
```

### 根因

dlib 升级到 pybind11 后 C++ 绑定参数签名改变，face_recognition 库仍按旧 API 调用。

### 需要做的事

1. 确认当前 dlib 和 face_recognition 版本：

```bash
conda activate monitor-server
python -c "import dlib; print('dlib', dlib.__version__)"
python -c "import face_recognition; print('face_recognition', face_recognition.__version__)"
```

2. 二选一修复：

   a. **降 dlib**：`conda install -c conda-forge dlib=19.22`（预 pybind11 版本）
   b. **升 face_recognition**：`pip install --upgrade face_recognition`（找兼容新版 dlib 的 release）

3. 验证修复：

```bash
python -c "
import face_recognition
img = face_recognition.load_image_file('src/tests/fixtures/lfw_subset/<任意一张>.jpg')
enc = face_recognition.face_encodings(img)
print('Encodings found:', len(enc))
"
```

4. 修复后运行测试确认：

```bash
pytest src/tests/service/test_face_image.py -v
# 期望 test_extract_from_real_image 不再 skip，变为 PASSED
```

---

## 四、启动顺序验证

如果 `ffprobe rtmp://127.0.0.1:1935/live/USB_webcam_video_1` 卡住无输出：

1. `curl http://127.0.0.1:8000/api/v1/nodes/1/videos` — 看 `streaming` 是否为 `true`
2. 如果 `streaming: false`，说明 UPDATE_STREAM 未发送或 Node 未执行 → 大概率是 WAL 残留
3. 如果 `streaming: true` 但无流，检查 Node 日志是否卡在 `Starting: USB webcam` → 可能是摄像头被其他程序占用
