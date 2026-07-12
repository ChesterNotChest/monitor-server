# Annotation Overlay

**Purpose:** OpenCV 在 YOLO/人脸结果上画框、标签、时间戳，产出标注帧。

## ADDED Requirements

### Requirement: 标注叠加

系统 SHALL 在 YOLO person 框和 face recognition 结果上叠加标注。标注内容包括：实体类型标签、人脸姓名/陌生人标签、时间戳。

#### Scenario: 标注已知人员

- **WHEN** YOLO 检出 person + 人脸识别匹配 "张三"
- **THEN** 标注帧显示 person 框 + 上方文字 "张三" + 右下角时间戳

#### Scenario: 无检测结果

- **WHEN** 当前帧 YOLO 未检出任何实体
- **THEN** 标注帧仅显示时间戳，画面内容与原帧相同

### Requirement: 标注帧推 FFmpeg

系统 SHALL 将标注帧通过 pipe 推送给 FFmpeg merge 进程。FFmpeg SHALL 接收 rawvideo 格式输入（BGR24），编码为 FLV 后与音频合并推 SRS。

#### Scenario: 推标注帧

- **WHEN** 标注帧就绪
- **THEN** frame.tobytes() 写入 FFmpeg stdin pipe
