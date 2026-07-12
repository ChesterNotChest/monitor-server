# Sound Enum Model

**Purpose:** 定义 YAMNet 音频分类声音类别枚举模型，用于标注检测到的声音类型。

## Requirements

### Requirement: 声音状态枚举表定义
系统 SHALL 定义 `SoundType` 模型，映射到 `sound_types` 表，存储 YAMNet 音频分类的声音类别枚举。

- `id`: 自增主键（Integer）
- `name`: 声音类别名称（String，唯一，非空），如 `gunshot`、`siren`、`scream` 等

#### Scenario: 注册 YAMNet 声音类别
- **WHEN** 向 `sound_types` 表插入声音名称
- **THEN** 系统持久化该声音类型枚举值

#### Scenario: 查询所有声音类型
- **WHEN** 查询 `sound_types` 全表
- **THEN** 系统返回所有已注册的声音类别列表
