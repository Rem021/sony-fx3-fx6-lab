# r26 单次工具返回适配（离线准备）

已完成8例历史回放；同一次顶层工具调用实际展示了观察截图和独立固定PNG。未运行原operate动作、未启动VM、未创建浏览器/服务、未更改冻结r26或正在封存的真实任务。

- return_adapter.py：只执行一个明确的原operate动作，命令固定到冻结r26，逐次独占输出目录。
- tool_call.mjs / show_result.mjs：真实Node工具可执行、从文件读取本次有界摘要、复核PNG并返回字节；不解析终端屏幕。
- [可直接使用的准确工具模板](TOOL-TEMPLATE.md)。展示后必须结束本次工具调用，让模型真正看图；下一调用才能作独立pin/confirm等决定。
- [验证回执](evidence/TEST-RESULT.json)、[Node负例](evidence/NODE-LOAD-NEGATIVES.json)、[极小exec上限同次显示](evidence/display-observation.json)、[同Node执行至固定图显示](evidence/display-fixed-node.json)。

每次调用保存完整child.stdout.json、child.stderr.txt和process.json。摘要小于4096字节，仅包含status、适用step/attempt、本次回执路径和图片路径/SHA/作用范围或确认结果。观察截图、固定snapshot、未入队恢复图的scope分开，哈希只证明字节一致，不判断语义。

成功图片必须来自本次完整stdout，位于当前task且mtime不早于child调用开始，PNG/哈希一致后才产生returned.png。失败不读取旧current-return.json，不展示图、不重发、不自动pin/confirm。Node收到非零/未知退出时连summary都不读，旧成功文件不能变成本次成功。adapter自身不追加End：若原operate已失败，它会走原End；若返回适配/展示失败，操作代理必须下一次明确调用冻结runtime-wrapper/cleanup.py，原20秒alarm仍兜底，禁止重发原动作。

samples/、fake_child.py、test_replay.py全部是历史离线回放；生产CLI没有fake-child或任意command参数。首次回放中空JSON被错误当作无图成功，已修为action/status双向白名单；首轮失败原件保留，最终8例通过。这里只消除结果截断/图片返回故障，不证明真实20秒内完成所有审阅，更不证明八步通过。
