目标：把 Part C 的 AlertEngine 和 YamnetRunner 挂入 Part A 的管线生命周期。​
要改的文件​
​文件	做什么
vision_task.py	start_pipeline() 里创建并启动 AlertEngine；有 audio_id 时创建并启动 YamnetRunner；stop_pipeline() 里停止两者

vision_task.py 或 app.py 或 view_task.py	找一个合适的触发点调用 start_pipeline(view_id, video_id, audio_id) —— View 创建/启动时

src/tests/test_alert_engine_unit.py	删掉 src/tests/ 根目录的旧副本，保留 service/ 下的

src/tests/test_fence_event_types.py	同上，删旧留新
​
你的 AlertEngine 和 YamnetRunner 代码本身没问题，逻辑正确、EventBus 连接也正确。现在唯一的问题是——它们没有被任何人启动。​
背景​
Part A 已经有了完整的 AI 管线调度器 vision_task.py，负责启动 YOLO 检测、帧标注、推流。这个管线的入口函数 start_pipeline(view_id, video_id, audio_id) 已经定义好了，内部会创建 AIPipeline 并跑主循环。你要做的就是把自己的 Part C 模块也挂到这个入口里。​
具体要做的​
第一步：在管线启动时启动 AlertEngine 和 YamnetRunner​
打开 vision_task.py 的 start_pipeline 函数。在 AIPipeline.start() 成功之后，追加：​
•
创建一个 AlertEngine(view_id) 实例，调 await alert.start()，存到全局字典里​
•
如果传了 audio_id，创建一个 YamnetRunner(view_id, audio_id) 实例，用 asyncio.create_task(yamnet.run()) 启动，也存到全局字典里​
这样每个 View 启动时，告警引擎和音频分类器就跟着一起跑了。​
第二步：在管线停止时也停掉它们​
在 stop_pipeline(view_id) 和 stop_all() 里，从全局字典取出对应实例，调 stop()。​
第三步：找一个 View 启动的触发点​
目前没有任何代码调 vision_task.start_pipeline()。你需要找一个合适的地方——比如 View 创建成功后的回调、或者一个独立的 API 端点——来触发管线启动。这个你根据产品逻辑判断。​
第四步：清理旧的测试文件​
src/tests/ 根目录下有两个旧副本：​
•
test_alert_engine_unit.py​
•
test_fence_event_types.py​
正确的版本已经在 service/ 和 api/ 子目录下了，把根目录的旧版删掉。​
验收标准（你跟 agent 说的）​
1.
管线能完整启动：创建 View 后启动管线，日志里应依次出现 "AIPipeline started"、"AlertEngine started"、以及 YAMNet 模型加载的日志​
2.
告警引擎能工作：YOLO 检测到目标后通过 EventBus 发布事件，AlertEngine 收到事件后匹配 ExceptionDef，匹配成功则写入 SituationEvent 并触发录制​
3.
音频分类能工作：音频流接入后 YAMNet 周期性推理，检测到匹配的声音类型时通过 EventBus 发布 SOUND 事件，最终触发告警匹配​
4.
管线停止干净：重复启停 10 次不残留任何 asyncio task，不泄漏内存​
5.
全量测试通过：跑 pytest src/tests/ 零失败​
6.
根目录无旧测试文件：确认 src/tests/test_alert_engine_unit.py 和 src/tests/test_fence_event_types.py 已删除