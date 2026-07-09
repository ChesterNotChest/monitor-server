# Face Recognition Pipeline

**Purpose:** 基于 YOLO person crop → dlib 人脸检测 → 128D 特征比对 NamedPerson 库，产出 FaceRecognitionResult 枚举事件。

## ADDED Requirements

### Requirement: 人脸检测

系统 SHALL 对 ByteTrack 产出的每个 person 区域裁剪（person crop），在 crop 内使用 face_recognition 做人脸检测。输入前 SHALL 做 BGR→RGB 转换（OpenCV 默认 BGR，face_recognition 期望 RGB）。若 crop 尺寸小于 50×50 px，SHALL 跳过。

#### Scenario: 检测到人脸

- **WHEN** person crop 尺寸 200×300，内含清晰人脸
- **THEN** `face_recognition.face_locations(person_crop)` 返回人脸坐标

#### Scenario: 人形框太小跳过

- **WHEN** person crop 尺寸 30×40
- **THEN** 跳过人脸识别，不产 FaceResult 事件

### Requirement: 128D 特征比对

系统 SHALL 在启动时一次性加载所有 NamedPerson 的 128D 特征向量到内存。检测到人脸后 SHALL 提取 128D 特征并比对。匹配阈值 SHALL 可配置（`FACE_MATCH_TOLERANCE`，默认 0.6）。

#### Scenario: 匹配已录入人员

- **WHEN** 人脸 128D 特征与 NamedPerson "张三" 的距离 < 0.6
- **THEN** 产出 `FaceRecognitionResult.NORMAL (3)` 事件，标注 "张三"

#### Scenario: 陌生人

- **WHEN** 人脸 128D 特征与所有 NamedPerson 的距离 ≥ 0.6
- **THEN** 产出 `FaceRecognitionResult.STRANGER (2)` 事件，标注 "陌生人"

### Requirement: 跳帧策略

系统 SHALL 每 N 帧做一次人脸识别（`FACE_SKIP_FRAMES`，默认 5），中间帧复用上次结果。

#### Scenario: 中间帧复用

- **WHEN** `FACE_SKIP_FRAMES=5` 且帧 1 识别为 "张三"
- **THEN** 帧 2-5 直接复用帧 1 的结果标注
