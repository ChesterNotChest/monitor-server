# Monitor Server Models

这个目录用于存放生产服务器上的模型权重文件。模型文件不提交到 GitHub，部署时通过 Docker volume 挂载到 `monitor-app` 容器内。

## 路径关系

宿主机路径：

```text
/home/liusu/video/models
```

容器内路径：

```text
/app/models
```

当前 `docker-compose.prod.yml` 已配置：

```yaml
${MODEL_DIR:-/home/liusu/video/models}:/app/models:ro
```

也就是说，代码在容器里应该从 `/app/models/...` 读取模型；在宿主机上把模型文件放到 `/home/liusu/video/models/...`。

## 推荐目录结构

```text
/home/liusu/video/models/
├── yolo/
│   ├── yolov8n.pt
│   ├── yolov8s.pt
│   └── custom.pt
├── dlib/
│   ├── shape_predictor_68_face_landmarks.dat
│   └── dlib_face_recognition_resnet_model_v1.dat
├── slowfast/
│   └── slowfast_model.pth
└── yamnet/
    └── yamnet.tflite
```

实际文件名可以按项目代码约定调整，但建议保持四类模型分目录存放：

- `yolo/`：目标检测、人脸检测等 YOLO 权重。
- `dlib/`：Dlib 人脸关键点、人脸识别模型。
- `slowfast/`：异常行为检测使用的视频动作识别模型。
- `yamnet/`：声学事件检测模型。

## OpenCV 放在哪里

OpenCV 不是模型文件，不应该放在这个目录里。

OpenCV 是运行依赖，应该安装到 `monitor-app` 镜像里，也就是写进：

```text
/home/liusu/video/monitor-server/monitor-server/requirements.txt
```

例如后续代码需要 `import cv2` 时，可以加入：

```text
opencv-python-headless
```

如果需要显示窗口或 GUI 能力才考虑 `opencv-python`，服务器部署通常优先用 `opencv-python-headless`。

## 本地开发

如果开发人员要在自己电脑上本地运行模型推理，也需要在自己电脑上准备一份模型目录，并通过环境变量指定：

```bash
export MODEL_DIR=/path/to/local/models
```

本地代码读取模型时建议统一使用配置项，不要把 `/home/liusu/video/models` 写死在业务代码里。

## 部署检查

部署后可以进入容器确认挂载是否生效：

```bash
docker exec monitor-app ls -lah /app/models
docker exec monitor-app find /app/models -maxdepth 2 -type f
```

如果容器里能看到宿主机 `/home/liusu/video/models` 下的文件，说明模型挂载正常。