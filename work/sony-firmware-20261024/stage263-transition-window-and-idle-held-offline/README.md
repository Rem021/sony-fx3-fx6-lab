# SERVICE等待窗口与空闲HELD的离线修复

本目录针对262的实际故障，不是新相机上机包。**等待窗口和对应回执校验已修正；协作退出只有纯状态分类器，尚未接入原生owner、helper及观察器。** 未运行root、未打开USB、未修改正在运行的261程序或旧许可。相机恢复普通模式优先于重试。

## 修改与针对性验证

- `transition_identity.c`与`service_flow.c`共用5秒/50样本/100毫秒策略，仍受原整体期限限制，不给既有窗口续期。`flow_receiver.py`同步限定5秒和50次，不接受更大范围。
- 测试链接实际C stream、witness、flow和journal，但底层USB、时间、端口及peer均为自写虚构提供者。虚拟3.2秒SERVICE/3.6秒返回流程被新解码器完整接受；五秒未出现、错误物理端口和三秒整体期限均进入HELD，未尝试SERVICE打开或STOP。
- 重算哈希链仍无法使超过5秒窗口或第51样本被接收。没有把保存字节重新当成活连接来源。
- 新增`idle_held.c`只分类flow自己的对象。未结束调用、仍持有MSC/SERVICE对象、接口状态不符、日志失败等均拒绝空闲判定。它不能单独证明native_owner无引用，也不授权退出、解锁或相机恢复。
- 另一个真实普通用户子进程对测试用本地journal写UNKNOWN并退出；父进程重新申请被现有global_guard拒绝。证明“程序结束”可以与“持久UNKNOWN继续阻止新owner”分离；并未改动运行中root的锁。

[构建命令及结果](build-attempt01.json) · [6组针对性回归与边界](test-receipt.json) · [基础源文件摘要](source-base.json)。编译启用ASan/UBSan，两个测试程序均不链接IOKit。测试包装曾修正Identity构造参数与缺失的owner_ipc链接依赖；早期产物保留，最终结果对应`runs/attempt02`。

## 尚未完成的协作退出集成

后续必须在owner_core已真实返回的主线程内，检查原生provider的active值、已转交的device/interface指针及打开标志，再结合flow对象分类。无SERVICE获取且旧MSC已成功处置时，才可能收尾host日志、停止并join watchdog、保存持久UNKNOWN，并以新的“主机空闲退出、机身未归还”终态结束。观察器须接受该终态并验证真实进程退出，不能把它解码为COMPLETE/MSC恢复。任何在途调用、对象所有权或日志状态不明，仍保留原实例。

当前程序没有该合作入口，不能热补丁、发信号冒充协作退出或通过另一锁文件绕过它。对当前旧程序的任何额外终止/锁交接，都须先取得普通模式恢复证据，并另行形成明确操作范围；本目录不执行这些操作。

## 实机状态与下一步

262仍为历史HELD；原helper85066及观察器82324保持运行。用户已报告拍摄界面，但新的缓存仍为SERVICE0336，访问灯状态待反馈。先按[恢复审查](../stage262-port-association-diagnostic01-execution/recovery-review.md)解决实际相机状态，再评估新的诊断。没有新增许可/固定目标/可运行原生包，未放行新USB试验或持久写入。原G01至G16、健康备份、独立恢复和MAIN HEVC验收均保留。
