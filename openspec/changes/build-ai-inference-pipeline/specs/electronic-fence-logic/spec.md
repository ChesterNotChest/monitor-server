# Electronic Fence Logic

**Purpose:** YOLO person_bbox × fence polygon 交集检测 + 滑动窗口密度判定 → FenceEventType 枚举事件。

## ADDED Requirements

### Requirement: 交集检测

系统 SHALL 对每个 YOLO person 框与绑定到当前 View 的每个围栏 polygon 做 IoU 检测。person_bbox ∩ fence_polygon ≠ ∅ 时 SHALL 记录 `(fence_id, track_id, timestamp, True)` 到滑动窗口。无交集时 SHALL 记录 False。

#### Scenario: 人在围栏内

- **WHEN** person_bbox 与 `coords=[(0,0), (100,0), (100,100), (0,100)]` 有面积重叠
- **THEN** 记录 `(fence_id=1, track_id=A, now(), True)`

#### Scenario: 人在围栏外

- **WHEN** person_bbox 坐标为 `(200,200,300,300)`，围栏在 `(0,0)-(100,100)` 区域
- **THEN** 记录 False

### Requirement: 滑动窗口密度判定

系统 SHALL 为每个 `(fence_id, track_id)` 维护 `collections.deque`。保留 `{now - fence.dwell_time} ~ {now}` 窗口内的条目。窗口内 True 占比 ≥ `fence.density` 时 SHALL 触发 `FenceEventType.ENTERED`。

#### Scenario: 密度达标触发

- **WHEN** `dwell_time=10s`、`density=0.6`，窗口内 10 帧中 7 帧 True
- **THEN** 触发 `ENTERED`

#### Scenario: 密度不达标

- **WHEN** `dwell_time=10s`、`density=0.6`，窗口内 10 帧中 4 帧 True
- **THEN** 不触发

### Requirement: 状态机防重复

同一 `(fence_id, track_id)` SHALL 维护 ENTERED / NOT_ENTERED 状态。触发 ENTERED 后 SHALL 抑制后续触发，直到连续 `leave_frames` 帧无重叠才重置为 NOT_ENTERED。

#### Scenario: 持续抑制

- **WHEN** track_id=A 已触发 ENTERED 且仍在围栏内
- **THEN** 不再产生新 ENTERED 事件

#### Scenario: 离开重置

- **WHEN** track_id=A 连续 `leave_frames=5` 帧无重叠
- **THEN** 状态重置为 NOT_ENTERED，允许再次触发
