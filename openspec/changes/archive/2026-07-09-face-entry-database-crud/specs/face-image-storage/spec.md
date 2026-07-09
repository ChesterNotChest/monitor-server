## ADDED Requirements

### Requirement: 人脸图片本地存储
系统 SHALL 将人脸图片存储到配置的本地目录 `FACE_IMAGE_DIR`，按人物 ID 组织子目录，文件名统一为 `avatar.<ext>`。

#### Scenario: 保存新头像
- **WHEN** 调用存储服务保存图片 `face.jpg` 至人物 ID=1
- **THEN** 系统创建目录 `{FACE_IMAGE_DIR}/person_1/`，将图片以 `avatar.jpg` 命名存储，返回相对路径 `person_1/avatar.jpg`

#### Scenario: 替换已有头像
- **WHEN** 调用存储服务保存图片 `face.png` 至已有人物 ID=1
- **THEN** 系统覆盖 `{FACE_IMAGE_DIR}/person_1/avatar.png`（删除旧 jpg，写入新 png），返回相对路径 `person_1/avatar.png`

#### Scenario: 删除人物头像
- **WHEN** 调用存储服务删除人物 ID=1 的头像
- **THEN** 系统删除 `{FACE_IMAGE_DIR}/person_1/` 整个目录及其所有文件

#### Scenario: 删除不存在的头像目录
- **WHEN** 调用存储服务删除人物 ID=99 的头像，但该目录不存在
- **THEN** 系统静默成功（幂等操作），不抛出异常

### Requirement: 图片格式校验
系统 SHALL 仅接受 JPEG 和 PNG 格式的图片，通过文件扩展名和 MIME 类型双重校验。

#### Scenario: 接受 JPEG 图片
- **WHEN** 上传文件 MIME 类型为 `image/jpeg` 且扩展名为 `.jpg`
- **THEN** 系统接受并保存该图片

#### Scenario: 接受 PNG 图片
- **WHEN** 上传文件 MIME 类型为 `image/png` 且扩展名为 `.png`
- **THEN** 系统接受并保存该图片

#### Scenario: 拒绝非图片文件
- **WHEN** 上传文件 MIME 类型为 `text/plain`
- **THEN** 系统拒绝并抛出 `ValueError`，提示"仅支持 JPEG/PNG 格式"

### Requirement: 图片大小限制
系统 SHALL 限制单张人脸图片不超过 10MB。

#### Scenario: 上传小于 10MB 的图片
- **WHEN** 上传一张 5MB 的图片
- **THEN** 系统接受并保存

#### Scenario: 上传超过 10MB 的图片
- **WHEN** 上传一张 15MB 的图片
- **THEN** 系统拒绝并抛出 `ValueError`，提示"图片大小不能超过 10MB"
