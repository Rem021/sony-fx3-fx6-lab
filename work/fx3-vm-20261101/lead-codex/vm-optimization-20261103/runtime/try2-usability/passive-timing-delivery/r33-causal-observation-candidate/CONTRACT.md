# r33 停止边界合同

本目录是**离线可实施性失败证据包**，不是可运行的因果观察候选。

- 输入所有原件只读；唯一写入是本目录。布局准入遇到尚未排除的动态 GPE 可写别名后停止，不改原GPE/DMM策略来制造“空闲区”。
- `actual-fx3-*.so` 两个文件是从既有 CPIO 抽出的**未修改审计输入副本**；host-fixture 里的 Mach-O 是 mock 谓词审计程序。它们都不是新 guest helper，不得替换到 runner/CPIO 或部署入口。
- 实现、host测试、交叉编译、真实运行必须分别报告。本轮：运行候选未实现；11项实际基线函数的host fixture通过；guest交叉编译未执行；VM/Start/服务/浏览器/QMP/设备均未执行。
- 不把合成 resource 反例说成真实 native resource，不把本地谓词接受说成整条固件draw已执行；不把缺少全 writer 排除证明说成真实覆盖已发生或r31根因。
- 不把 UI 全区初始化抹掉的早期记录说成“0次publication”；没有collector就绪/同PID/同module epoch/有效commit证据均unknown。UC不新增exclusive RMW/原子锁。
- 没有新的publication/bind/alloc/send/consume witness，没有新summary解析器或额外export。并发drop/覆盖/回绕/丢序/跨chunk/End、全部publication/bind分支、每hook成本/2KiB预算、原调用/rc/ABI完整等价性等**候选验收均未完成**，不能用11项布局fixture替代。
- 原有4×A35/5120MiB/MTTCG/noicount、QEMU/kernel/DTB、guest控制流与返回、PAGE/server、180s/20s、pin/confirm/recovery和原退出清理保持原件。FX6仍是优先主线，本支线没有改FX6基线或provider拒绝。
- 本任务不授权任何下一轮VM。恢复实施需先完成NEXT-DATA.md所列离线排除/身份证明，再由协调端审阅；不增加运行次数碰运气、不延长预算。
