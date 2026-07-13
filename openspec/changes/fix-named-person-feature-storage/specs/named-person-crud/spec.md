## MODIFIED Requirements

### Requirement: 上传人物头像

系统 SHALL 提供独立的人像上传端点，支持替换已有头像。上传头像时，系统 SHALL 保存头像文件，并在检测到人脸时提取 128D 人脸特征向量 JSON 写入人物记录。

#### Scenario: 为已有记录上传头像

- **WHEN** 客户端 `POST /api/v1/persons/1/avatar` 以 multipart/form-data 发送 `avatar=@new_face.jpg`
- **THEN** 系统保存图片到 `person_1/avatar.jpg`
- **AND** 更新 `avatar_path` 为 `person_1/avatar.jpg`
- **AND** 若检测到人脸，更新 `feat_json_id` 为完整特征 JSON 字符串
- **AND** 返回更新后的人物记录

#### Scenario: 为不存在的人物上传头像

- **WHEN** 客户端 `POST /api/v1/persons/99999/avatar`
- **THEN** 系统返回 404 Not Found

#### Scenario: 上传非图片文件

- **WHEN** 客户端上传的 avatar 文件不是 image/jpeg 或 image/png
- **THEN** 系统返回 422 验证错误
