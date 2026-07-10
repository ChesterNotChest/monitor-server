## 1. 清理 e2e 目录

- [ ] 1.1 移动 `e2e/test_live_camera.py` → `tools/live_camera_demo.py`
- [ ] 1.2 移动 `e2e/test_yamnet_live.py` → `tools/yamnet_live_demo.py`
- [ ] 1.3 删除 `e2e/_test.md`
- [ ] 1.4 验证 `pytest src/tests/` collection 不再尝试收集这三个文件

## 2. Spec 更新

- [ ] 2.1 创建 `local-dev-e2e-paradigm` spec（新增 capability）
- [ ] 2.2 更新 `test-organization-standard` spec（MODIFIED: 命名约束 + e2e 目录规范）

## 3. README 修正

- [ ] 3.1 Server README 中 `STREAM_DEBUG` → `RTMP_DEBUG`（对齐 Node 当前变量名）
- [ ] 3.2 README E2E 验证步骤补充 Node 端 `SERVER_BASE_URL=127.0.0.1 DEBUG_WSS=false` 配置

## 4. 验证

- [ ] 4.1 `pytest src/tests/e2e/` 只收集到 `test_recording_lifecycle` + `test_wss_app_integration`
- [ ] 4.2 `python tools/live_camera_demo.py` 能独立运行（依赖已安装时）
- [ ] 4.3 核心回归 205 pass 不受影响
