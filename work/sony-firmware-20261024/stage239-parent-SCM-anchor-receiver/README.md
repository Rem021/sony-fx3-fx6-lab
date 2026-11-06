# FX3 父端目录句柄接收与私有ACK核心

2026-10-30。**父端C接收器、目录验证、私有ACK和原对象观察器已联通；监管者现在收到有效ACK后才创建内部空操作工作器。9项检查、41个显式模拟场景通过，两个来源/封闭域反例保留，整体准入仍未通过。当前程序不能投放相机或刷写。**

本轮仅Mac编译自写C、Unicorn执行自写ARM64，以及读取/反汇编已保存固件和公开Linux源码。进程、VFS、socket、FD安装、凭据、时钟和回收全是明示模型；没有实际Linux进程、相机/USB/缓存、管理员、认证、上传或固件写入。

## 接收、ACK与观察已连通

[parent_receiver.c](parent_receiver.c)先核对调用者UID/EUID与输入socket形状：Unix未命名数据报、CLOEXEC、PASSCRED已启用、SO_PEERCRED对应创建该socketpair的父进程。它以DONTWAIT和CMSG_CLOEXEC接收，核对完整256B HELLO、恰好一个凭据和一个权利FD，再验证收到FD的CLOEXEC/procfs/目录属性、稳定inode及相对stat中的PID/PPid/单线程/起始时间。

只有上述检查通过、对象仍处于运行/睡眠状态且请求未过期，父端才发送一次ACK。它随后关闭自己拥有的通道，把验证后的动态FD和刚读取的起始时间传给238的对象观察器，不再使用固定anchor编号。观察器继续只接受原对象Z/10752及之后task脱离，不进行数字PID wait。

[collector-ack.c](collector-ack.c)在发送自己的proc目录FD后等待精确ACK。消息错误、凭据错误、未收到ACK或过期均不进入内部监管核心，因而不会创建内部工作器。双方协议升为FX3ISOCOLLECT2，绑定相同的绝对截止值；ACK发出前后以及接收后都检查期限，旧v1消息被拒绝。**父PID、起始时段和关联值仍是人工夹具，绝对截止也是固定仿真值，不是真实准备计划或授权。**

已执行[9项/41场景](runs-receiver-verified/receipt.json)：正常链及控制条目顺序/末尾无padding、socket前置拒绝、旧消息/短包/错PID UID GID/缺失或重复条目、253个权利FD、截断与负返回、错误ACK/关闭失败、ACK过期后继续运行对端、等待超时、原工作器exit68/强杀及监管者死亡。父端C实际解析模拟内核复制来的控制区并关闭识别出的FD，ACK发送事件先于内部worker创建。

## 错误清理有明确边界

普通拒绝消息中的已识别权利会逐一关闭，不自动重试close。复制失败或无法解释的控制区仍可能留下未识别FD，状态6表示UNKNOWN，不能声明全部清理，更不能作为整条任务或USB已归还的凭据。

[44项原字核对](SCM-contract.json)绑定保存内核的3个SCM范围、5个系统调用表项和6段Linux v4.9.337参考源码，确认253上限、CMSG_CLOEXEC路径、get_file/fd_install及先安装再写头的结构。**参考代码中，当全部FD已安装但仅控制头写入失败时，CTRUNC并不一定出现。** 实际原指令也固定了安装循环、头写入及基于计数决定CTRUNC的分支；未在相机观察或触发该故障。因此接收器对条目计数异常也保留UNKNOWN，不能只凭flags判定清理完整。

模型保留“头写入失败且无CTRUNC”的案例：FD已安装但没有可解析的权利条目，接收器不猜测FD编号、不误发ACK，并明确保留未关闭资源。Linux文档对[recvmsg接收标志](https://man7.org/linux/man-pages/man2/recvmsg.2.html)及[Unix控制消息](https://man7.org/linux/man-pages/man7/unix.7.html)作了接口说明；本轮额外限制来自固定源码与原字。

## 来源和实际启动仍未证明

SCM_CREDENTIALS的PID/UID/GID检查是关联检查。参考和原内核都具有CAP_SYS_ADMIN路径，具有相应权限的发送者可指定其他PID；本轮未测目标能力，不能将凭据当作完整创建身份。

两个反例继续登记：先将原A强杀并回收，再显式输入复用PID、起始时间不同的外国B消息/目录对象，接收器会捕获B的新起始时间并可能观察其exit42；破坏内部封闭子进程域时，原worker68仍可被误作外国0，监管者因而错误产生42。前者明确假设外国发送者曾继承端点，并丢弃原A的HELLO后发送匹配格式的新消息；A先脱离，B才活跃，**不是两个活进程同时占用同一PID，也不是声称内核把真实A的SCM_RIGHTS变成了B**。这不是相机已发生的事件。没有真实创建与端点独占/请求绑定，结构验证不能排除这类来源条件。

下一步把创建socketpair、创建前屏蔽信号、独立clone、匿名代码持续存活、真实PID与完整准备计划接入现有入口；同时核对接收错误时的FD所有权和Sony服务返回时限。当前仅有两个独立静态执行载体及条件模型，并未接到Sony构造函数或实机装载器。

当前父端ELF SHA为`075f36d60f11ba537f6ef2b0515989805407b3dc11c146175501e927c58f25f7`，监管者为`919b38fd7d8ab14b3433579e596fe309a1e2f37ab0328d464d63f10d496b3c5b`；各262144B，[重复构建](reproducible-build-verified-summary.json)一致。早期模型漏初始化时钟、测试报告字段和来源反例设置问题，以及期限协议/无CTRUNC错误清理的修订均保留于[source-revisions.json](source-revisions.json)，未覆盖旧结果。

235原候选仍未准入；正式0.4/0.5及23源码、195 root01未批准未启动和全部16要求保持。完整boot采集/同机健康备份/独立AP救砖恢复/目标HEVC主录与长录均未实机验收。前一轮238封存89成员，是实际准备进展；目标active，首刷未放行。[封存回执](final-receipt.json)。
