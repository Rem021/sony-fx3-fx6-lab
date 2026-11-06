# r35 离线首次 publication / bind 观测候选

**隔离候选实现、宿主验证和 AArch64 交叉编译通过；未集成、未部署、未执行 VM。** 当前 UI72656B/OSD119544B 调试 ELF 超过 N64 原 slot 58856B/109000B，不能直接交固定 runner 使用。后续 release 打包、两成员差分及 runner 绑定需另任务审查。本报告不宣称零首帧根因修复、boot/menu 或 FX6 通过。

卷 UUID 已核 F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B。仅本新目录写入；项目根非 Git，没有复制 runtime 或 CPIO。371/371 必要技术输入结束复核一致，包括 r32 原123输入、r33/r34/r30冻结交付及实际编译依赖；共享项目README不作运行冻结。未改部署 r10、guest、GPE/DMM、物理布局、QEMU/kernel/DTB、4×A35/5120MiB/MTTCG/noicount、180秒/20秒、PAGE/server、pin/confirm/recovery、退出清理或 FX6 候选。

## 实施与审查结论

1. **普通 BSS 补盲点**：OSD 两个独立 first-captured 记录保存严格原 CONTROL publication schema 的 entry/原 hsend rc，以及原 observer_bind entry、-1/-2/-3/-4/成功分支、mmap阶段、原写magic后一次实际load。ring为null时也能记账。只读原发送前副本，不再读已移交消息；原 hsend 调用、rc/errno、alloc/send/consume和原失败处理不变。不提前bind、不重试、不ACK补发。
2. **身份先于记录**：依协调端 msg_46c6a32261e9 修订，唯一新增热路径 syscall 是实时 getpid/TGID。每个记录入口/快照至多1次；原选中UI回调含跨helper至多2次。先查询再读owner/碰锁；不同TGID无任何诊断BSS写入、预算重置或输出。最终去掉草稿atfork依赖，由实时查询拒绝libc及raw路径的外来TGID；目标raw clone/vfork未运行，宿主注入和实际fork测试分开。
3. **唯一生产实例与预算**：原全局 O_EXCL claim 在任何probe install之前；额外模块、新exec或重载不能第二次安装。foreign TGID即使共享BSS也不能改parent记录/额度。保持原active preload/claim/hook寿命及外部host run身份合同，不能仅以PID/时间戳当全局runID。摘要只在原UI_GATE_SAMPLE调用内追加，固定184B，7个独立单调obligation使整轮最多7条1288B，低于2048B。未初始化或没有原日志出口时unknown，无额外日志兜底。
4. **交错覆盖已修正**：初审发现bind优先分类会压住后来的首次CONTROL；现按pub/bind各自entry/return独立前进，一次快照同时覆盖所有新位。六种合法交错均通过，先bind完成再pub begin/end不会被抑制；没有增加额度或I/O调用。
5. **观测边界**：初始化之前unknown，loss时不保证first-captured是全序最早；pub与bind不冒充同一消息因果链。magic是一次读回而非终态。快照仅对collector自己的有界记录一致，不是server、guest、firmware原子准入或End原子状态。历史四轮的305/328/305/306原输出机会未被说成未来保证。UI7000–77ff仍不准入，r33 failed/r34 unknown不变。

精确实现、ABI/wire字段、生命周期、时钟及失效范围见 [CONTRACT.md](CONTRACT.md)；最坏完整wrapper累计与宿主数值见 [COST.md](COST.md)。

## 实际来源链

- N64 CPIO SHA `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9`，流式遍历1140个header，重新校验实际init、libc、pthread、OSD和UI成员；未打包新CPIO。
- OSD原r3源码/flags重编 `.text` 与原编译ELF及实际N64成员一致；UI原r15 N64同样一致。SDK libc/pthread与实际CPIO字节完全一致。见 ACTUAL-BINDING.json、BASELINE-REBUILD.json、BUILD-INPUTS-BEFORE.json。
- 原init同一bootin launch行 preload 两helper；四个startup窗口同一im PID maps均包含两者，且各仅一条UI_GATE_BOUND。原claim/install顺序的源码检查与实际宿主O_EXCL新进程拒绝测试见 INSTANCE-CONTRACT.json。宿主物理map仍mock。
- 实际libc `syscall` 使用w0→w8、svc #0；固定Image syscall table172/178分别指向实际sys_getpid/sys_gettid，而非拿gettid替代TGID。AS-SEMBLY-AUDIT.txt/JSON保存原字节、VA、原生SVC、记录点、弱CAS失败边。observer_bind实际magic load由反汇编确认，原probe机器指令仅同目标BL重定位不同。

## 针对性验证

`run_offline.py` 13个步骤均exit0，stdout/stderr完整保存于receipts/offline-*，总表 OFFLINE-RECEIPT.json；未导入runner。

- **实际wrapper及bind**：编译整个原/候选OSD C翻译单元；native、open/read/mmap/worker均mock。8个模式包含claim、cmdline open/内容、selfmem、devmem、mmap失败、成功及原send失败，原rc/errno和send/open/read/map/close/log/thread次数完全一致。另验证严格schema拒绝、递归、发送后原消息被改写仍只用原副本、zero-ring及early初始化。HOST-WRAPPER.json与两份原始stdout可逐行比较。
- **实际collector/log**：真实宿主pthread与fork；另有foreign TGID共享BSS注入覆盖每个入口、已持锁状态、相同PID缓存与预算复制，均拒绝且整份parent状态不变。同TGID多线程、有界claim失败、end丢失保持phase1、首记录不覆盖、重复end/loss、版本失败、预算耗尽与损坏计数不回绕均通过。六种pub/bind交错、7条184B/1288B、未绑定无I/O兜底均通过。见HOST-COLLECTOR.json和receipts/collector-log.stderr。
- **原UI真实选中block**：自动从两源码提取原条件/整个选中日志block编译，n1..1001仍51次原clock/gettid/dprintf；去掉唯一184B后缀后原字段逐字节相同。完整路径原子与跨helper开销未藏在callee，首次/常态/额度耗尽分别记录。HOST-UI.json、HOST-COST.json保存次数与计时。
- **独立解析器**：完整LF/CRLF、跨chunk、逐字截断/End、>22KB坏行（部分/完整及同坏行尾接假摘要）、完整CLI、坏版本/source/PID/init/magic/范围/hash/阶段、乱序/漏ordinal/重复/重载、未输出、预算terminal分开处理；9组针对性检查通过。PARSER-TEST.json、PARSER-COMPATIBILITY.json、PARSED-FIXTURE.json保存结果。
- **兼容性明确分界**：已有 opportunities 精确字段解析拒绝后缀记录，不能直接用它数r35；实际r32 GATE为前缀正则，原字段捕获一致。r30 KEEP/FAILURES/MARKERS在实际fixture分类一致，consumer/ready未改。新增字节会改变offset与serial量，未宣称调度或整个准入结果等价。
- **成本**：首次完整claim-failure wrapper原1/候选5次getpid（新增4），记录完成后不重置collector的常态原1/候选3（新增2）；bind ready后稳态新增1。原选中UI即使7条额度用尽仍新增2次查询，已实测。宿主getpid约百ns、输出/格式化有实际成本，详见COST；不外推guest、不推断原单个dprintf等于单个write。

本测试中的 native/视觉/物理mmap均不是原固件运行；没有真人看图或真实guest boot声明。原GPR/SIMD/NZCV/SP等probe保存恢复路径与机器指令审查不替代guest ABI自测。没有加入生产/alloc/consume全阶段ABI或改动未证路径。

## 交付与剩余

- 源：src/ 两个完整派生C及3个支持文件；osd-source.diff、ui-source.diff、support-source.diff；parse_r35.py独立离线读出。SOURCE-FREEZE.json固定实际源/测试/分析脚本；BUILD.json固定交叉产物。
- 验证：run_offline.py、各独立脚本与原始receipts；INPUTS-BEFORE/AFTER、补充输入和SHA256SUMS。
- 过程：初始SDK不导出pthread_atfork的失败回执及被替代草稿保留在receipts，最终实现无该新依赖；parser超长行及bind优先分类缺口均已修正，不将旧草稿标通过。
- 清理：只有已wait的宿主CLI/编译/fixture，实际fork已waitpid、pthread已join；ps精确核无自有fixture存活。未创建浏览器、服务、TCP端口、QMP或guest进程；EXECUTION-SCOPE.json记录边界。仅删除本目录可重建编译cache，未动任何历史。

下一步仅是独立包装/配置审查：让release ELF实际可装入固定布局，验证只改两helper成员并绑定固定runner与本run身份合同，再另行调度VM。真实时序扰动、是否有post-event日志机会、首次publication/bind的guest行为和连续菜单成功仍待验；不能延长180/20秒、移除门或增加VM碰运气来替代。
