# Person Tracking

**Purpose:** ByteTrack 跨帧人物追踪，为 YOLO person 框分配稳定 track_id。

## ADDED Requirements

### Requirement: ByteTrack 追踪

系统 SHALL 使用 ByteTrack 为 YOLO 产出的 person 框分配跨帧稳定的 track_id。同一物理人在连续帧中 SHALL 保持相同 track_id。

#### Scenario: 单人追踪

- **WHEN** 连续 5 帧中出现同一物理人
- **THEN** ByteTrack 为 5 帧中的 person 框分配相同 track_id

#### Scenario: 多人追踪

- **WHEN** 画面中同时出现 3 个人
- **THEN** ByteTrack 为每人分配独立且稳定的 track_id，互不混淆

#### Scenario: 人物离开再出现

- **WHEN** person 离开画面 2 帧后重新出现
- **THEN** ByteTrack 分配新 track_id（非旧 ID）

### Requirement: 追踪输出格式

ByteTrack SHALL 输出 `[(x1, y1, x2, y2, track_id, score), ...]` 格式，与 YOLO 原始检测结果对齐。

#### Scenario: 输出格式

- **WHEN** YOLO 检出 2 个 person（bbox 坐标）
- **THEN** ByteTrack 输出 2 个追踪结果，含 track_id 和置信度
