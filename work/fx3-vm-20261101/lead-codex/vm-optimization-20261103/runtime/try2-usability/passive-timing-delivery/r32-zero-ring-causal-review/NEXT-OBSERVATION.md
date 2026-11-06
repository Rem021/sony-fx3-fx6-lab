# 下一次一次性因果观察设计（未实现）

选项：先离线准备一个小型、内存记账为主的guest观察增量，再由协调员决定是否占用下一次唯一授权运行；不重复盲跑、不增加Start/键预算、不延长180/20秒。不改4×A35、5120MiB、QEMU/kernel/DTB/MTTCG/noicount、FX3时钟、固件原函数/门禁、PAGE/server、provider返回、pin/confirm和清理。

r30新增的是host字节收到、header拒绝和ready短路证据。它既看不到ring为空前的publication/bind执行，也无法从已去重日志恢复同root各阶段结果、原生产调用者和观察I/O耗时。本方案只补这些明确缺口。

最少触点与独立事实：

1. **`fx3-osd-headless-v25-r3.c:121` 与 `:81`**：在现有eligible publication首次尝试/原hsend返回处保存独立见证（enabled/API/queue-owner条件、src/dst/op、原rc）；在observer_bind入口、每个负返回/成功返回处另记结果、mmap返回、拟物理地址/长度、magic写后读值。必须独立存储，不能再依赖尚未初始化的OSD ring；publication成功、bind进入、bind成功三者分离。只读记录原值，不补ACK、不强制bind、不重试。
2. **UI v15探针及确切原点**：producer函数入口0x16f1a48记录root和外部LR；0x16f1a74/consumer0x16f1d68区分“拟写”和“已越过原STR”，不能把前置探针称已提交。复用原决策寄存器记录signed counter/a12与gate7/8。只对同一PID/root和已证source830128/type150000关联；root变更、TLS关联不明、重入均标unknown。
3. **现有CAPID观察点限定5503e0原路径**（`:609/:682`）：关联同一producer调用，分别计alloc成功/失败、send进入/返回rc、消费source/type验证及减计数；记录有限消息指针+观察代数，防止地址复用造成假配对。其他目的地及FX6 provider分支保持原调用/尾调用方式，不能为记录状态改变它们的栈身份或返回。对现有dprintf和send_stats只采有限耗时样本，不能先删除开销再声称证明因果。

预算与交付边界：

- 目标额外导出≤2KiB，可考虑现有64KiB UI reserve内0x7000–0x77ff：当前v15显示boot记录到0x7000、change输入在0x7800，**必须先完成整个已装入布局/所有writer审计**，本报告不凭空授权这段空闲。若未证明安全则不生成候选，不扩大硬件保留区。可用8个guest clock1的30秒进度桶、固定4个producer槽、首个publication/bind见证和两条首次异常摘要；超范围/覆盖/竞争显式计数。桶是guest时间，不等于host180秒。
- 每hook上限：一次clock_gettime和最多4次64位原子记账、一次有界try-claim；不得循环等待、malloc、重调原函数或每消息新增文件/串口写。耗时只有限采样（每桶最多首8次），额外输出最多13行×256B；这些是设计硬上限，尚无实测成本保证。若达不到该边界，应缩减观察而非改原准入。
- 保留最多一次/每桶的独特literal摘要，复用r30原serial读取记录token及LF收到边界；在End前已完整收到的摘要可明确属于startup接收窗口，未收到/End后收到仍unknown。原已有暂停读回的UI64KiB可以顺带带回内存摘要，不增加QMP、暂停或guest命令；End→原暂停之间及后续tail必须独立标记，不算180秒内成绩。跨线程字段不是事务快照，附begin/end版本和drop计数，不能假称全局原子。

离线准入先验证：布局不重叠、原指令/寄存器/栈/errno/NZCV/SIMD保存；原alloc/send/consume/锁调用次数、rc、超时和gate表达式一致；匹配root、指针复用、漏/错序、负计数/回绕、并发drop、所有bind失败、零ring和写后覆盖、摘要截断/跨chunk/End边界；模拟日志阻塞只影响观察，不能变成自动重试/放行。做回调CPU与有限输出字节实测，超预算停止候选。通过这些离线检查也只允许另行调度的一轮观察，不构成boot/menu或根因修复通过。
