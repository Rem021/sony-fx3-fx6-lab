# Mac

2026-10-27：[开发环境与内盘实验资料整理](reports/2026-10-27-vm-experiment-consolidation/README.md) · [共用设备与资料存放规则](docs/shared-development-storage.md)。六份实验快照已迁移，下一批严格通过子目录待协调窗口；未通过原生等价的原件按用户选择保留。

Mac 系统优化、缓存清理、文件与 Agent 项目整理。

Codex 与 Orca 文件夹入口均已创建并固定。历史任务目录保留原位。

## 相机与固件研究

- [FX3实施路线与当前进度](outputs/fx3-recovery-adapter/ROADMAP.md)：8个里程碑，当前在真机入口与可信退出；首刷前第2至6项共5个前置尚未完成。固定成果入口与后续交付/停止标准，原16项验收保留。

- [2026-11-01 FX3原厂SERVICE串号与三速配置](<work/sony-firmware-20261024/stage259-original-SERVICE-identity-and-speed-policy/README.md>)：确认原厂SERVICE关闭USB串号，与258候选的跨模式身份条件不兼容，旧包不能接机后直接运行。三速配置识别已补齐并验证；接下来修复受控切换关联，无相机命令或管理员操作。

- [2026-10-31 FX3首次Sony通信诊断固定包](<work/sony-firmware-20261024/stage258-fixed-Sony-communication-diagnostic01/README.md>)：具体认证、配置识别、固定88B读取和退出步骤及主机许可/启动器已写成；五组离线检查通过。当前缓存未见Sony相机，需要接机并固定新节点后才可启动；未暂存、未开Terminal、未运行root或Sony命令。

- [2026-10-31 FX3 SERVICE描述符识别与控制退出分支](<work/sony-firmware-20261024/stage257-service-descriptor-discovery-and-control-exit/README.md>)：配置发现、管道核对和不匹配时仅控制退出已实现；五组离线检查通过，真机退出仍待验证。缓存曾见相机在线且一卷挂载；下一步制作固定Sony通信诊断包，未发送相机命令。

- [2026-10-31 FX3主机入口整合与逐调用私有回执](<work/sony-firmware-20261024/stage256-root-service-flow-and-private-receipts/README.md>)：原生组件已接主机入口、独立通信范围和对象转交；80条人工管道原始回执与子进程私有日志一致，失败/中途停止保留UNKNOWN。完整候选编译，实际root/IOKit未运行；SERVICE发现与不匹配退出仍待补，真机入口关闭。

- [2026-10-31 FX3原生跨代通信与SERVICE分段接收](<work/sony-firmware-20261024/stage255-native-generation-and-service-stream/README.md>)：原生IOKit组件、两模式摘要/固定交换、12B头+88B受限接收和显式归还请求已写成并编译；9项自写C人工管道检查、最终静态分析通过。尚缺完整root/IPC与真实SERVICE配置整合，无设备操作。

- [2026-10-31 FX3普通应用资源交接与服务结束](<work/sony-firmware-20261024/stage254-normal-resource-handoff-and-end-callback/README.md>)：完整原路径已接通到资源42、两条信号量和结束回调；区分常驻监督线程与本次认证/服务线程。回调不提供逐线程主机回执，下一项落实跨MSC/SERVICE原生发送器；无新设备操作。

- [2026-10-31 FX3受限读取与初始MSC退出路径](<work/sony-firmware-20261024/stage253-level-gated-read-and-stop-unblock/README.md>)：原插件固定001F/read0的88B读取，A/B门控、C无，排除同命令80重置写入；17B/100B编解码检查通过。普通监督线程及STOP解阻塞路径已定位，初始MSC取消触发未闭合，停止仅挑战方案；无新设备操作。

- [2026-10-31 FX3 Sony通信阶段影响与退出准入](<work/sony-firmware-20261024/stage252-MSC-service-entry-impact-and-admission/README.md>)：4原函数39指令/7跳项核对，明确5/7完成分支及传输异常取消循环；新增结果判定器消费5个既存反例，握手结束不充认证成功。251实测通过保留，无新设备操作；Sony试验退出方案未齐。

- [2026-10-30 FX3第12号实机接管归还结果](<work/sony-firmware-20261024/stage251-authorized-owner-status12/README.md>)：单次实测HOST_RETURN_OBSERVED；root身份/live HELLO、私有原始回执、helper与观察器退出、独立MSC缓存及用户正常屏幕均完成。仅Mac接管归还子步骤通过，无Sony认证/读卡/刷写，下一步研究机内入口。

- [2026-10-30 FX3第12号修复诊断固定方案](<work/sony-firmware-20261024/stage250-corrected-owner-status12-package/README.md>)：修复101–109事件解析、先存原始回执及错误后观察器退出；新节点/单次材料和50文件包已固定，8项检查含原生编号夹具通过。生产USB范围不变；未授权/暂存/执行，11号UNKNOWN保留。

- [2026-10-30 FX3第11号单次诊断执行记录](<work/sony-firmware-20261024/stage249-authorized-owner-status11/README.md>)：已实际执行一次root/USB诊断；内核身份与live HELLO通过、helper退出、缓存MSC/驱动恢复且机身屏幕正常。主机解析器漏101–109子步骤，私有完成回执未保存，正式UNKNOWN；独立修复候选10项回归通过，无重试/刷写。

- [2026-10-30 FX3单次USB接管与归还诊断固定方案](<work/sony-firmware-20261024/stage248-fixed-owner-status-launch-package/README.md>)：原生帧/监督器、接管前缓存节点与私有HMAC绑定、root单次许可已接通；8项离线核验通过，50文件包c372c53f固定。仅状态控制，待新单次管理员与USB接管批准；未暂存/启动，无新缓存或设备操作，仍不能首刷。

- [2026-10-30 FX3主机回执与状态控制端整合](<work/sony-firmware-20261024/stage247-shared-host-transport-owner-status/README.md>)：复用246实测的主机传输代码，状态控制端8项整合/2项当前端口进程检查通过；一次授权缓存识别唯一FX3，端口适配0x01100000。原生工厂/同机绑定/单次包未就绪，入口关闭，无新管理员/相机命令。

- [2026-10-30 FX3 Mac管理员身份与回执实测](<work/sony-firmware-20261024/stage246-authorized-host-root01/README.md>)：按195本次授权实际完成两次root试验/回读，身份、自读握手、受保护归档和原进程退出通过，启动链返回0。第2项主机前置推进，授权已消耗；无USB/相机/固件操作，真机入口及恢复仍待验。

- [2026-10-30 FX3最小通信诊断与准入结论](<work/sony-firmware-20261024/stage245-minimal-communication-admission/README.md>)：固定4操作评审候选，START/STOP原控制头与停止其它驱动/事件路径对应，不满足不切状态保证；本路线停止同输入离线追加。195仅主机实测仍未执行，第2项未完成，无设备操作。

- [2026-10-30 FX3首次程序试验的通信路径判定](<work/sony-firmware-20261024/stage244-highcapacity-session-admission/README.md>)：补齐3条原命令表、同步队列和回调静态连接；共享DMM/路径及挂载边界未满足，现有文件回传候选保持不放行。路线第2项未完成，本批无需连接相机，无设备操作。

- [2026-10-30 FX3局部结果记录与主机回传合同](<work/sony-firmware-20261024/stage243-result-readback-original-command-contract/README.md>)：自写C固定RAM记录和外部摘要绑定解码，8检查/16ARM64实例/28拒绝变体及重复构建通过；12原函数56指令21分派固定GET2挂载/全局路径/忽略返回边界。只局部观察，真实回传/恢复未验；无设备/root，不能首刷。

- [2026-10-30 FX3构造入口与跨加载占位候选](<work/sony-firmware-20261024/stage242-DT-INIT-preparation-and-cross-load-claim/README.md>)：DT_INIT共享库接完整准备器与监管桥，计划2/IPC4绑定完整文件与运行ID；9检查44模型场景、重复构建和215引用1075核对通过。同命名空间保留式占位拒绝重载/换nonce，真实Sony加载/授权/回传及恢复未验；无设备/root，不能首刷。

- [2026-10-30 FX3新公开提交与首次入口接入复核](<work/sony-firmware-20261024/stage241-public-recovery-delta-and-first-entry-gaps/README.md>)：固定ZV-E10新HEAD575c707完整差分，仅文档新增764行；有仿真中断进展但末节仍零帧，无FX3救砖新实现。240的87成员核回；构造/准备/跨加载与回传待接，无设备/root，不能首刷。

- [2026-10-30 FX3运行时计划与匿名副本启动桥](<work/sony-firmware-20261024/stage240-runtime-plan-and-anonymous-clone-bridge/README.md>)：自写C创建/接收/监管接通，8检查27模型场景及重复构建、128地址引用640核对通过；外层SIGCHLD与内层clone0，旧映射移除仍运行。真实构造/准备/全局跨加载排他及恢复未闭合；无设备/root，不能首刷。

- [2026-10-30 FX3父端目录句柄接收与私有ACK](<work/sony-firmware-20261024/stage239-parent-SCM-anchor-receiver/README.md>)：父端C接收/验证/ACK后对象观察，9检查41场景及双端重复构建；44原字核对发现无CTRUNC也可能留未识别FD，保持UNKNOWN。真实创建/匿名代码/完整计划与两个来源/子域前提未闭合；无设备/root，不能首刷。

- [2026-10-30 FX3原对象句柄与非零退出标记](<work/sony-firmware-20261024/stage238-proc-anchor-and-nonzero-exit-sentinel/README.md>)：自传proc目录FD/exit42与原对象观察器，9检查39场景及双端重复构建；58原字核对固定权限滤零陷阱。父端接收/真实入口与两来源/子域反例仍未闭合，不充全任务或USB归还；无设备/root，不能首刷。

- [2026-10-30 FX3隔离监管与封闭子进程域核心](<work/sony-firmware-20261024/stage237-isolated-collector-child-domain/README.md>)：自写ARM64核心8检查22场景/重复构建，53原字核对与14父图；限定域拒绝外部PID复用，保留强行同父反例。真实隔离入口/监管者退出/完整采集未闭合，235准入仍失败；无设备/root，不能首刷。

- [2026-10-30 FX3保存内核的唯一退出接口](<work/sony-firmware-20261024/stage236-kernel-unique-exit-interface-audit/README.md>)：99静态检查/18代码范围固定291分派及单次wait对象引用；12调度1误认，3普通门控无误认但另4身份反例未解，提前futex通知不充最终退出/FD归还。转查封闭子进程域监管者，235准入仍失败；无设备/root，不能首刷。

- [2026-10-30 FX3单次加载集成与剩余身份反例](<work/sony-firmware-20261024/stage235-single-load-preparation-and-exit-observer/README.md>)：准备到启动/观察已合并，8检查24范围内场景及重复构建通过；完整计划SHA与连续掩码修复两处缺口。但当前父共享/收养模型仍误认exit68为0，安全准入失败，继续研究唯一内核退出凭据；无设备/root，不能首刷。

- [2026-10-30 FX3完整RAM计划准备程序候选](<work/sony-firmware-20261024/stage234-fixed-RAM-plan-preparer/README.md>)：7检查/27模拟场景及重复构建通过，私有0600完整计划复读、不覆盖发布、自采时钟，接原231自写START；修复发布/最终关闭过期误报。人工关联与自校验不充认证，准备完成准入/转换/回传/备份恢复未验，无设备/root，不能首刷。

- [2026-10-30 FX3内核UIPC接收槽分配](<work/sony-firmware-20261024/stage233-kernel-UIPC-callback-slot-assignment/README.md>)：驱动5切片/54核对/17分派固定共享回调FIFO与4任务槽，实际接收数未测；16条件调度运行原231自写ARM64，4同槽通过、12跨槽HELD48，保留退出身份保护。完整计划准备/入口备份恢复未验，无设备/root，不能首刷。

- [2026-10-30 FX3任务文件投放与接收线程合同](<work/sony-firmware-20261024/stage232-plan-writer-and-command-thread-contract/README.md>)：2原件/11完整函数及回调/4切片/46核对，发现包装器创建mode未建立、外部绝对路径加基目录；UIPC条件接收池不充同TID。转向完整RAM计划自生成和内核线程分配核对，现231保护保留；无设备/root，不能首刷。

- [2026-10-30 FX3构造启动与再次加载退出观察候选](<work/sony-firmware-20261024/stage231-constructor-noexec-child-and-reload-observer/README.md>)：14检查/22模拟场景及重复构建通过；匿名副本内clone抵御旧库映射失效，活线程proc锚/WNOTHREAD拒绝PID复用，私有DONE与精确退出联合观察，无GO限次退出。仅空操作，计划投放/同线程加载/真实备份恢复未验；无设备/root，不能首刷。

- [2026-10-30 FX3直接构造函数入口适配依据](<work/sony-firmware-20261024/stage230-constructor-child-entry-portability/README.md>)：3完整原函数/16调用证明两setter写后dlopen/dlclose且无dlsym，229完整对象ABI仅限脚本线程；固定公开A7CII/FX30构造子进程文本，转向受限构造启动器。现227仍只写内存标记，完成/退出/真机恢复未验；无设备/root，不能首刷。

- [2026-10-30 FX3服务插件接口与停止完成条件](<work/sony-firmware-20261024/stage229-Jiritsu-plugin-lifecycle-contract/README.md>)：8完整原函数/22调用/29ABI/4字符串核对，实际Create/Load/Run/DestroyScriptI对象及0x18f8上下文未适配；run排队/stop状态10或超时30不充线程结束，exit等待返回未检查即清句柄。父flash前置与5MiB子tmpfs分开，无设备/root，仍不能首刷。

- [2026-10-30 FX3实际加载上下文与公开恢复复查](<work/sony-firmware-20261024/stage228-real-entrypoint-portability-audit/README.md>)：13原指令/6切片/225记录绑定，常规APP/INFRA线程加载不证明候选主线程可达；三公开HEAD重核，新QEMU提交仅65行UI研究文档、SD恢复全程仍待实测。真实入口/同机备份/独立AP恢复及首刷仍缺，无设备/root。

- [2026-10-30 FX3零参数启动桥与看护交接候选](<work/sony-firmware-20261024/stage227-zero-arg-bootstrap-and-keeper-handoff/README.md>)：6检查/10模拟场景通过，自写三程序链及四窗口人工源组装、重复构建一致；FINISH0后exit89及外层im抢先回收均保持UNKNOWN。真实加载/重复调度/主机回传及独立恢复未验，无设备动作，尚不能首刷。

- [2026-10-30 FX3静态看护进程与父镜像v2合同](<work/sony-firmware-20261024/stage226-static-keeper-and-parent-image-contract/README.md>)：7检查/11场景通过，两自写静态程序_start至退出，独立看护自身SIGCHLD政策、512B任务与四FD父镜像SHA绑定；四窗口人工源完整组装，旧im父文件/协议拒绝。FINISH0后关闭失败退出89不充成功；真实加载交接/退出传输/备份恢复未验，16要求/195/正式包保留，无设备/root。

- [2026-10-30 FX3原厂im回收器与加载ABI缺口](<work/sony-firmware-20261024/stage225-im-reaper-and-loader-ABI-audit/README.md>)：6原切片/8调用核对及2自写ARM64时序确认，参考im可抢先回收普通子进程，同一224候选在DONE0/exit0后得ECHILD并保持UNKNOWN；exec重置SIGCHLD使clone0捷径无效，四参入口仍需桥接。转向独立看护进程与新身份合同；16要求/195/正式包保留，无设备/root/Sony执行。

- [2026-10-30 FX3受控启动器与完整镜像预核](<work/sony-firmware-20261024/stage224-controlled-launcher-and-preexec-image-pin/README.md>)：8检查/20场景通过，自写ARM64的clone分支/子FD清理/exec/静态_start与父端完成连通；全局会话先于暂存，镜像或启动失败不读源，四窗口人工源完整组装。真实Linux/加载传输/信号/机内备份恢复未验，16要求/195/正式包保留，无设备/root。

- [2026-10-30 FX3独立静态工作程序与FD合同](<work/sony-firmware-20261024/stage223-static-worker-and-scoped-job-descriptors/README.md>)：8检查/25场景通过，自写_start至退出与原父端联测，动态角色FD/镜像inode关联，保留全局防重复及四窗口人工源组装。实际fork/exec/继承/启动前镜像SHA/机内恢复未验，16要求/195/正式包保留，无设备/root。

- [2026-10-30 FX3父端C监管与双端ARM64联测](<work/sony-firmware-20261024/stage222-parent-arbiter-core-and-paired-ARM64/README.md>)：15检查/38场景通过，固定会话、私有完成、子退出和RAM复读共同放行；旧/新二进制对照修复损坏输出仍释放的问题，四窗口人工源完整组装。真实启动/继承/加载/root域/恢复未验，16要求/195/0.5保留，无设备/root。

- [2026-10-30 FX3自写ARM64私有许可入口](<work/sony-firmware-20261024/stage221-private-IPC-entry-gate/README.md>)：无GRANT/GO默认拒绝，256B handoff全绑定；10检查/44进入案例、5Linux头文件/35定义及布局核对通过，四窗口人工源完整组装。新13B空操作合同拒绝旧日期串；机内全局keeper/启动/真实凭据仍缺，16要求/195/0.5不变，无设备/root。

- [2026-10-30 FX3存活会话全局监管离线入口](<work/sony-firmware-20261024/stage220-live-session-global-arbiter-fixture/README.md>)：10主+2边界检查通过，23自写ARM64子进程及2真实所有者竞争；阻塞/迟到/不完整完成保持UNKNOWN，同会话boot0/boot1各4窗口完整组装人工源。219目标模块直接旁路仍OPEN，机内IPC/root/恢复未验；16要求/195/0.5不变，无设备/root。

- [2026-10-30 FX3请求绑定与窗口防重复候选](<work/sony-firmware-20261024/stage219-bound-handoff-and-request-claims/README.md>)：11项/50自建ARM64案例及2普通Mac进程通过，4窗口组装33,423,360B合成数据；两占用名先留位，部分失败后换nonce仍拒绝。最终并发反例确认不同任务可重叠，全局排他/可信完成仍缺；16要求/195待答/0.5保留，无设备/root。

- [2026-10-30 FX3固定shell进程过滤候选](<work/sony-firmware-20261024/stage218-fixed-shell-process-filter/README.md>)：首层/bin/sh -c的40字节argv已绑，UID/PID/主线程与自身/父程序文件SHA接入；11项/63夹具通过，无内层旁路导出或自动读取/exit。调用授权、全局claim、真实父进程与完成回执未证；16要求/195待答保留，无设备/root。

- [2026-10-29 FX3最小动态启动区模块候选](<work/sony-firmware-20261024/stage217-restricted-ET_DYN-boot-module/README.md>)：固定0.5源码PIC→ET_DYN，内存标记初始化、100代码字段/1相对重定位及RELRO，8项自建装载/ARM64检查通过；Sony装载器与专用子进程guard未验，无上传/preload安装/设备/root，0.5/16要求/195待答保留。

- [2026-10-29 FX3新公开救砖方案与模式解析差异](<work/sony-firmware-20261024/stage216-upstream-bootrom-collection-and-FX3-portability/README.md>)：24来源/23行、FX3两镜像847inode和4范围/16原字核对；Pico独立路线与SD待测分开，FX3局部解析无强制LF，不能抄修复字节。补相对写/绝对读、零写及漏尾约束；目标已由用户恢复active，0.5/16要求/195待答保留，无设备/root动作。

- [2026-10-29 FX3启动区采集工作器候选0.5](<work/sony-firmware-20261024/stage215-AP-boot-capture-worker-candidate/README.md>)：B0/B1动态容量及环境过滤已接入C/独立协议/本地组装，11新+47旧=58项离线测试通过；23文件源码包，旧p1/0.4保留。实际备份、访问归还及独立救砖未验；无设备/root操作，195待答。

- [2026-10-29 FX3启动区读取与访问状态](<work/sony-firmware-20261024/stage214-AP-boot-read-transfer-and-capacity/README.md>)：容量EXT_CSD226×128KiB和空解密上下文至控制器3处跳过已绑；读取可发CMD6选179访问位，特定失败panic，实际数据视图/恢复未验。24范围/5标准行，195待答，无设备/root/guest动作。

- [2026-10-29 FX3 AP启动区设备与动态容量](<work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/README.md>)：当前p3原驱动B0/B1节点252:126/127与容量u8×128KiB已绑，不能套4MiB/2MiB；启动区无软件crypt回调，低层完整视图未闭合。两旧包135/134清单及NOR4/4重核，6原件/11范围，195待答，无设备/root/guest动作。

- [2026-10-29 FX3官方启动属性与AP／CP写入边界](<work/sony-firmware-20261024/stage212-official-boot-backup-generator/README.md>)：更正当前NOR为CP路线，不能充AP救砖；-m/-c分选首/次记录，CP65项预测1088B而AP缺4项，1386比较+44独立拒绝；选中pformat丢弃返回码。7原件/15范围，195待答，无设备/root/guest动作。

- [2026-10-29 FX3运行时初始化与默认速率3](<work/sony-firmware-20261024/stage211-NOR-runtime-map-and-SIO-initialization/README.md>)：22默认记录速率3/154独立例及参考消费已核，离线候选3/0/4/2；C初始化先零7480B，当前后续装入/同机BKSB未证。15原范围；195待答，无设备/root/guest动作。

- [2026-10-29 FX3早期SIO与计时合同](<work/sony-firmware-20261024/stage210-SIO-clock-routing-and-divider-contract/README.md>)：当前事务/配置读点已绑，双方84B计时叶相同、CNTFRQ声明2MHz；101/1001非脉宽，SIO父频率/初始化未证。17原范围/7源码行；195待答，无设备/root/guest动作。

- [2026-10-29 FX3当前GPIO驱动与SIO速率差异](<work/sony-firmware-20261024/stage209-current-GPIO-driver-and-link-timing/README.md>)：当前GPIO布局/模式9四写及F1021000资源已绑；helper速率请求19与参考3不同，Hz/当前p1仍未证。16原范围/7源码行，195待答，无设备/root/guest动作。

- [2026-10-29 FX3 Backup本地与CP记录选择](<work/sony-firmware-20261024/stage208-Backup-record-routing/README.md>)：官方队列/操作4分派与首记录本地、第二记录CP已绑，AP默认0/4/2；11模板/30原范围/5原件核回。候选不可执行，实机设置与独立恢复未验；195待答，无设备/root/guest动作。

- [2026-10-29 FX3默认Backup双记录与GPIO参数](<work/sony-firmware-20261024/stage207-Backup-template-and-GPIO-config/README.md>)：11模板/22有效记录的两组配置不同，735515范围/66独立例通过；GPIO端口/位号和模式2已绑，7原范围。实际记录选择与救砖未验；195待答，无设备/root/guest动作。

- [2026-10-29 FX3 MCU读取分支与SIO配置来源](<work/sony-firmware-20261024/stage206-FX3-MCU-read-protocol/README.md>)：包内InitCom0x16/6字节头/120数据/回复已绑，公共MMIO与重复回复边界已查；3Backup来源、18原范围，CRC4608+5仅语义模型。195待答，无设备/root/guest动作。

- [2026-10-29 FX3恢复载荷硬件对应与看护字段](<work/sony-firmware-20261024/stage205-FX3-hardware-profile-differences/README.md>)：9资源/4USB时钟静态对应，参考布局只用SRAM；当前MCU计数表及3重装来源已绑，28行范围/10原切片。链路与实机恢复未验；195待答，无设备/root/guest动作。

- [2026-10-29 FX3适配用公开AP启动参考](<work/sony-firmware-20261024/stage204-public-AP-boot-reference/README.md>)：实际取得A7IV ROM/boot0/SRAM；190464字节全量绑定，模式3→p1启动文件已追到原码，8切片。仅参考，非FX3同机备份；195待答，无设备/root/guest动作。

- [2026-10-29 FX3 WBI恢复范围与早期启动原件边界](<work/sony-firmware-20261024/stage203-WBI-layout-and-early-memory/README.md>)：既有1399段按参考源码和原件复核；Linux恢复入口64字节吻合，eMMC交接区已绑定；未取得独立AP boot0，尾部完整保留。195待答，无设备/root/guest动作。

- [2026-10-29 FX3重启请求与恢复环境依赖](<work/sony-firmware-20261024/stage202-update-transition-and-restart/README.md>)：7.02 hot/cold已追至UPM队列接收/状态机；604脚本路径与历史p1重启11/3分开，18原范围/11编码核对；尚非AP独立自举，195待答，无设备/root/guest动作。

- [2026-10-29 FX3更新队列的实际接收者](<work/sony-firmware-20261024/stage201-updater-request-endpoint/README.md>)：7.02 libObj已绑定queue0x376实际回调，源码显示mode文件写入与5/7拒绝/超时掩盖；12切片/10编码核对，非AP独立自举；195待答，无设备/root/guest动作。

- [2026-10-29 FX3官方Darwin发送端与驱动依赖](<work/sony-firmware-20261024/stage200-official-Darwin-updater-dependencies/README.md>)：7.02原程序11/4构帧和参考p1 SIO32B/128返回已核，脚本OK不充状态确认；依赖AP运行环境，非独立自举；14原切片，195待答，无设备/root/guest动作。

- [2026-10-29 FX3 Darwin向量与条件更新回跳](<work/sony-firmware-20261024/stage199-Darwin-vector-map-and-update-entry/README.md>)：0x4200源映射及Cmd11/sub4→本地参数→Seton/Upd向量0/4已静态连通；19原切片，SVC交付/坏核心及AP恢复未验；195待答，无设备/root/guest动作。

- [2026-10-29 FX3 SPI固定交接与AP恢复边界](<work/sony-firmware-20261024/stage198-AP-CP-loaders-and-partition-selection/README.md>)：7.02另一加载器固定交接0x108000，与cpapp配置相符；DGU/MIS/Darwin原件已绑定来源，AP p1/p3入口和独立恢复仍未证；195待答，无设备/root/guest动作。

- [2026-10-29 FX3 SPI启动模式来源与远端边界](<work/sony-firmware-20261024/stage197-SPI-boot-mode-and-remote-boundary/README.md>)：命令1前缀+0x30到模式全局已连通，679指令PWD控制流经独立编码复核；真实p1/p3选择和独立恢复仍未证；195待答，无root/设备/guest动作。

- [2026-10-29 FX3 NOR文件回退与早期标志](<work/sony-firmware-20261024/stage196-early-FAT-and-boot-selection/README.md>)：原FAT-open118指令正常返回恒-408，原始位编码复核一致；UPDATE_MIRA采样写word已定位，真实按键/远端p1仍未证；195批准待答，无设备/root/guest动作。

- [2026-10-29 FX3研究root仅主机01固定方案](<work/sony-firmware-20261024/stage195-root-host-validation-plan/README.md>)：独立无IOKit/USB/固件后端程序；15项普通用户流程＋2项批准/映射检查通过，试验＋新nonce回读最多两次helper，待新的具体批准，root/作业/管理员/相机均未运行。

- [2026-10-29 FX3固定启动监督与程序自读握手](<work/sony-firmware-20261024/stage194-supervised-fixed-launch/README.md>)：16项完整假对象流程＋1项分段实流通过；修正协议时钟混用，relay不充helper，重启日志保持UNKNOWN；原生10关闭，root跨UID和真实恢复未验，无设备动作。

- [2026-10-29 FX3私有完成回执与存活握手](<work/sony-firmware-20261024/stage193-private-result-receipt-channel/README.md>)：38项整合＋20项回执检查通过；共享文件不能充最终结果，HELD不释放，原生09未发布/未运行，root跨UID、完整监督和恢复仍待验证，无设备动作。

- [2026-10-29 FX3跨实例排他与私有报告I/O](<work/sony-firmware-20261024/stage192-global-owner-fence-and-frame-IO/README.md>)：38项整合＋18项日志通过；死PID/UNKNOWN不自动放行，报告截断不释放等待中的owner；原生08未发布/未运行，可信回执与启动监督待补，无设备动作。

- [2026-10-29 FX3原生owner与有界通道整合候选](<work/sony-firmware-20261024/stage191-native-owner-channel-integration/README.md>)：32项进程整合＋55项底层回归通过；私有状态、同进程借用、peer身份和UNKNOWN保留已接线，原生入口未发布/未运行，启动监督与全局排他待补，无设备动作。

- [2026-10-29 FX3原加载器preload失败与冷启动边界](<work/sony-firmware-20261024/stage190-AP-process-launch-and-loader/README.md>)：补齐29个启动候选、103处直接分支；5组原错误消费检查确认局部非致命分支，/etc为持久文件，真实冷启动/WBI与救砖未验，无设备动作。

- [2026-10-29 FX3终端分派与固定库入口](<work/sony-firmware-20261024/stage189-TERM_MODE-consumer/README.md>)：30组原ARM64局部检查确认TERM_MODE拒绝及固定libJit的可写闪存挂载前缀；0.4工具保留，真实备份/救砖未验，无设备动作，持续目标active。

- [FX3恢复适配工具0.4](outputs/fx3-recovery-adapter/README.md)：静态ELF链接与ARM64假内核三窗口383块验证完成，47项本地检查通过；机身启动/传输及独立救砖未验。[188证据](<work/sony-firmware-20261024/stage188-static-ELF-link-and-explicit-entry/README.md>)。

- [FX3恢复适配工具0.3](outputs/fx3-recovery-adapter/README.md)：新增固定只读C工作器候选和输出解码，38项本地检查通过；AArch64仅编译对象，未链接、未上机，无独立救砖证明。[187证据](<work/sony-firmware-20261024/stage187-FX3-native-read-worker/README.md>)。

- [FX3恢复适配工具0.2](outputs/fx3-recovery-adapter/README.md)：新增定长读取／日志／逐块校验和本地后端，27项本地检查通过；真实机身采集、写回及独立救砖未验。[186证据](<work/sony-firmware-20261024/stage186-fx3-bounded-capture-engine/README.md>)。

- [FX3恢复适配工具0.1](outputs/fx3-recovery-adapter/README.md)：已实现本地p1检查/候选/逆还原，真实2.04/2.05原件闭环及13项检查通过；当前7.02机身和实际刷写未验。[185证据](<work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/README.md>)。

- [2026-10-29 索尼社区救砖与FX3独立服务](<work/sony-firmware-20261024/stage184-community-recovery-and-standalone-service/README.md>)：已核A7CII模式绕行、文件回退与改DAT/p1流程，以及A7IV/ZVE10早启恢复；FX3文件服务仍依赖im，下一项仅离线限定读取合同和当前p1库身份，无新增设备动作。

- [2026-10-29 FX3请求交接与独立恢复入口](<work/sony-firmware-20261024/stage183-request-consumer-and-early-entry/README.md>)：NOR早期mode条件消费者和独立sen进程已证；queue0x376仍停OSAL交接，下一项查独立sen命令与看护依赖，无新增设备动作。

- [2026-10-29 FX3恢复启动与版本准入](<work/sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/README.md>)：旧同版续行/跳版本与当前body写点已定位；7.02请求追至内核间接回调，整包无独立p1载荷，下一项查queue0x376登记消费者，无新增相机动作。

- [2026-10-29 FX3改机失败恢复路线](<work/sony-firmware-20261024/stage181-recovery-first-research/README.md>)：按用户纠正改为恢复优先；已找到独立updater和7.02脚本桥接，下一项追启动选择与恢复续行版本门，无新增设备动作。

- [2026-10-29 FX3原生MSC请求通道](<work/sony-firmware-20261024/stage180-native-MSC-request-channel/README.md>)：C层单会话预算与20项真实进程夹具通过，含控制端退出时保留在途；root拥有者/身份/实际服务仍未整合，无新增相机操作。

- [2026-10-29 FX3同进程IOKit有界收发适配](<work/sony-firmware-20261024/stage179-bounded-IOKit-wire/README.md>)：55项自写SDK夹具和两条控制器模拟流程通过；原生仅编译，真实拥有者IPC/服务/备份恢复仍未接通，无新增相机操作。

- [2026-10-29 FX3归档修复整合与服务边界](<work/sony-firmware-20261024/stage178-integrated-user-receipt-controller/README.md>)：77项当前本地检查通过；原生收发仍需IOKit同进程适配，认证尾部写入/退出与整机备份边界重核，未新增相机操作。

- [2026-10-29 FX3屏幕确认与归档修复原型](<work/sony-firmware-20261024/stage177-user-owned-receipt-channel/README.md>)：用户确认05后USB/MSC正常；用户属主输出通道6项离线检查通过，原UNKNOWN和已耗05保留，未整合/启动新设备方案。

- [2026-10-29 FX3 05号接口实测与归还](<work/sony-firmware-20261024/stage176-owner05-after-port-return/README.md>)：共享原生结果0，接口0/IN81/OUT02/512B及归还走通，同机MSC/原驱动缓存恢复；正式UNKNOWN因root日志属主错误保留，待屏幕确认，未刷写。

- [2026-10-29 FX3同机与端口差异核对](<work/sony-firmware-20261024/stage175-owner05-after-connection-and-ejection/README.md>)：同机HMAC确认、MSC/6类驱动和推出状态正常；当前01100000与固定02100000不同，05未启动/未耗，授权保留。

- [2026-10-29 FX3 05号已授权待连接](<work/sony-firmware-20261024/stage174-authorized-Terminal-owner-trial-05/README.md>)：固定173方案已获一次批准；缓存未见原端口目标，未启动/未耗，等待恢复连接和手动推出，授权保留。

- [2026-10-29 FX3 Terminal启动与登录检查候选](<work/sony-firmware-20261024/stage173-Terminal-owner-launch-and-login-guard/README.md>)：64项本地检查通过，保留单次/ACK/阻塞监管；相机调用与04一致，新增05尚未授权执行，未刷写。

- [2026-10-29 FX3仅主机登录身份对照完成](<work/sony-firmware-20261024/stage172-authorized-host-login-audit/README.md>)：固定Terminal/sudo实测root保留audit UID501和GUI会话；主机单次授权已耗，无相机或隐私操作，尚不证明USB接口可用。

- [2026-10-28 FX3不接相机的主机登录对照候选](<work/sony-firmware-20261024/stage171-camera-free-host-login-audit/README.md>)：普通用户GUI/audit基线和独立权限门已验；Terminal/sudo主机只读身份对照已固定，未授权未启动，无USB或隐私变更。

- [2026-10-28 FX3 04号定位Mac隐私授权链](<work/sony-firmware-20261024/stage170-owner-trial-04-after-manual-ejection/README.md>)：接口枚举0、插件阶段103 NoResources；既有日志显示Start not permitted及同PID可移动卷TCC转发失败；稍后缓存/屏幕正常，04已耗，无刷写或权限变更。

- [2026-10-28 FX3 04号已授权待推出卷](<work/sony-firmware-20261024/stage169-authorized-owner-trial-04/README.md>)：固定168方案已获一次批准；当前PMHOME重新挂载，04未启动/未耗，等待手动推出后复核，同一授权不再询问。

- [2026-10-28 FX3接口子步骤与04诊断候选](<work/sony-firmware-20261024/stage168-claim-substep-diagnostics/README.md>)：原设备调用/参数/顺序不变，SHA绑定子步骤日志和34项本地检查通过；04未授权未执行，01/02/03保留，无新增相机操作。

- [2026-10-28 FX3 03号实际接管与归还观察](<work/sony-firmware-20261024/stage167-authorized-owner-trial-03/README.md>)：root身份/ACK与capture已通过，接口申请NoResources；归还后稍晚全部缓存驱动恢复、用户屏幕正常，原UNKNOWN保留；03已耗，无Sony命令/刷写。

- [2026-10-28 FX3跨用户身份读取与03候选](<work/sony-firmware-20261024/stage166-cross-uid-kernel-identity/README.md>)：现存root身份实测及36项本地检查通过，保留UID/微秒出生/路径ACK和错误日志；03未授权未执行，01/02保留，无新增相机操作。

- [2026-10-28 FX3 02号单次接管结果](<work/sony-firmware-20261024/stage165-authorized-owner-trial-02/README.md>)：内置复制及原生ready已到达，父身份ACK未放行，设备调用0；跨UID完整进程信息EPERM已在主机复现，正式状态UNKNOWN，02已耗不重试。

- [2026-10-28 FX3内置盘预复制接管候选](<work/sony-firmware-20261024/stage164-internal-staged-owner-launch/README.md>)：固定工作目录/私有预复制已实现，28项本地检查通过；新02编号未授权未执行，01失败记录保留，无刷写。

- [2026-10-28 FX3单次接管启动失败记录](<work/sony-firmware-20261024/stage163-authorized-single-owner-trial/README.md>)：已推出卷并启动一次；Mac管理员复制外置程序被拒，未确认helper启动/接管；前后同机MSC缓存及驱动关联一致，编号已耗，不重试，无刷写。

- [2026-10-28 FX3等待PMHOME手动推出](<work/sony-firmware-20261024/stage162-manual-ejection-blocked-audit/README.md>)：同一挂载前置条件持续，原生目标已blocked；单次接管授权保留、次数未耗，无存活接管进程，推出后可继续。

- [2026-10-28 FX3有界读取组件与服务入口盘点](<work/sony-firmware-20261024/stage161-bounded-read-import-inventory/README.md>)：532 ELF/168匹配文件、14原函数及11组前缀读guest；组件存在但可达续读未证，内部前缀读吞错误，无新增主动设备操作。

- [2026-10-28 FX3异常表与读取清理结果](<work/sony-firmware-20261024/stage160-LSDA-selected-read-error-and-close-review/README.md>)：6函数/46调用区间、12组原指令guest；关闭失败可保留open标志而数据回复成功，实际运行时及备份未验；已获接管授权仍等待卷推出，次数未耗。

- [2026-10-28 FX3单次接管授权与卷检查](<work/sony-firmware-20261024/stage159-authorized-owner-trial-preflight/README.md>)：用户明确批准156方案；缓存见FX3卷仍挂载，等待手动推出，接管次数未消耗，管理员/设备执行尚未开始。

- [2026-10-28 FX3原整文件读长度与备份准入](<work/sony-firmware-20261024/stage157-original-whole-file-read-length-and-status/README.md>)：26组原指令guest/5532进入，短读与外层0返回分离、64位stat到32位读取/分配及日志改读已验证；实际备份/异常展开仍未验，无新增设备操作。

- [2026-10-28 FX3固定单次接管与实际进程确认](<work/sony-firmware-20261024/stage156-hardened-owner-launch-and-ack/README.md>)：17项当前自写检查通过，含真实fixture父进程退出；root私有哈希staging/独立入口租约/ACK与记录观察已实现，真实管理员及设备仍未执行。

- [2026-10-28 FX3固定原生入口与独立缓存观察](<work/sony-firmware-20261024/stage155-fixed-owner-helper-and-independent-cache/README.md>)：13项固定fixture进程检查/37项C回归/14项观察器检查；一次已授权缓存采集，真实提权/接管入口仍未放行，无可刷包。

- [2026-10-28 FX3隔离接管监管与Mac时钟修正](<work/sony-firmware-20261024/stage154-isolated-owner-supervisor/README.md>)：14项真实fixture进程检查/35项C回归，超时保留同一在途进程；统一CLOCK_MONOTONIC，真实IOKit与提权入口仍关闭，无新增设备操作。

- [2026-10-28 FX3 Mac原生接管候选](<work/sony-firmware-20261024/stage153-Mac-owned-interface-trial/README.md>)：IOKit库编译未加载，共用C流程33项夹具；SDK补充MSC capture例外，真实入口因缺监管仍拒绝，无新增设备操作。

- [2026-10-27 FX3资源回调/线程失败与Mac整设备接管](<work/sony-firmware-20261024/stage152-resource-callback-and-thread-failure/README.md>)：14组原指令guest确认内部标志不充完成；固定Darwin源码区分capture重开和attach重新枚举，驱动返回另验，无新增设备操作。

- [2026-10-27 A7C II HEVC 25／29.97最新演示核查](<work/sony-firmware-20261024/stage151-latest-A7CII-HEVC-evidence/README.md>)：一手原帖及六张机内/播放器/菜单图，4K HEVC有作者实机证据；420、HD、原片独立解析及FX3可刷补丁仍待证，无新增设备操作。

- [2026-10-27 FX3普通协作者与NIN联合验证](<work/sony-firmware-20261024/stage149-normal-cooperator-and-NIN-checkpoint/README.md>)：五组原指令guest/590进入，错误摘要也可出最终回复并请求资源；内部状态不充实机模式或线程完成，无新增设备操作。

- [2026-10-27 FX3普通应用NIN动态入口](<work/sony-firmware-20261024/stage148-initial-MSC-handler-inventory/README.md>)：532个AP ELF盘点，原libObj回调接NinThread动态加载的12函数/24指令事实/3重定位；实际MSC协作者/摘要和恢复未验，无新增相机操作。

- [2026-10-27 FX3有界USB收发层](<work/sony-firmware-20261024/stage147-bounded-owned-handle-wire/README.md>)：借用句柄的control/bulk实现，78项自写C夹具检查及两条惰性流程通过；真实接管/归还/初始MSC认证及救砖未验，无新增相机操作。

- [2026-10-27 FX3原内核符号与控制分派联合验证](<work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/README.md>)：41269符号/6089导出对照、1007名称guest，11分派场景接原SEN回调；内部HALT/零值不充实际USB或排队成功，实机权限未增。

- [2026-10-27 FX3按模式摘要与控制请求边界](<work/sony-firmware-20261024/stage145-initial-MSC-native-route/README.md>)：MSC公开参考/服务原函数分开验证，103项检查及两条惰性流程；原模块返回THRU的副作用边界已定位，初始MSC实机认证仍未证。

- [2026-10-27 FX3单次USB描述符实测](<work/sony-firmware-20261024/stage144-single-Mac-descriptor-trial/README.md>)：明确授权后实际读取成功，MSC接口0/Bulk81与02/512B，后置缓存驱动链仍在；一次权限已消耗，无认证或刷写。

- [2026-10-27 FX3 Mac描述符传输候选](<work/sony-firmware-20261024/stage142-Mac-USB-transport-candidate/README.md>)：私有MSC限定构建/67离线例通过，缓存见1台；真实描述符读取尚未放行，无认证/刷写/恢复验收。

- [2026-10-27 FX3公开摘要与原认证校验器](<work/sony-firmware-20261024/stage141-public-auth-digest-and-original-verifier/README.md>)：三块材料逐字节对应，38原校验例/六轮惰性集成通过；真实USB/整机认证及恢复未验，刷写未放行。

- [2026-10-27 FX3单机会话控制器与47故障场景](<work/sony-firmware-20261024/stage140-bounded-service-session-controller/README.md>)：惰性状态核心/协议向量通过，未知与无重试/驱动物理证据分层已实现；真实USB/凭据/时限及实机恢复未验。

- [2026-10-27 FX3退出回调与队列返回反例](<work/sony-firmware-20261024/stage139-service-callback-bridge-and-queue-return/README.md>)：回调静态接通，8组原指令guest反例说明返回0未必排队、报错也可能已排队；首次会话约束已备，实机/刷写未放行。

- [2026-10-27 FX3原USB分派与Mac驱动归属](<work/sony-firmware-20261024/stage138-USB-stop-dispatch-and-Mac-ownership/README.md>)：原库setup与内核匹配/事件投递已对应；另有UU强制模式文件，Mac接管/复绑需独立验证，实机及刷写未放行。

- [2026-10-27 FX3服务退出与主机清理核查](<work/sony-firmware-20261024/stage137-service-exit-and-host-cleanup/README.md>)：原正常路径先join认证再启动命令线程；取消/回调/无超时等待及PMCA清理缺口已定位，实际退出与独立恢复仍未验。

- [2026-10-27 FX3认证完成与同机读取准备](<work/sony-firmware-20261024/stage136-authentication-and-system-read-admission/README.md>)：认证最终应答早于条件历史/日志结束；/tmp配置在闪存，两个固定库读取仅惰性草稿，退出/传输及实机备份未放行。

- [2026-10-27 FX3 Fastboot识别实测](<work/sony-firmware-20261024/stage135-Fastboot-entry-discovery/README.md>)：官方37.0.1实际枚举为空、前后FX3仍MSC；A7IV自制载荷/串口桥不能直接套用，当前仅有电脑，尚未执行进入或刷写。

- [2026-10-27 FX3备份读取范围与登记副作用](<work/sony-firmware-20261024/stage134-backup-reader-scope-and-service-extension/README.md>)：旧GET/hash/高容量会话未形成受限系统备份；条件.hasp历史写入已定位，认证不能统称零写入，实机/刷写未放行。

- [2026-10-27 FX5系统移植FX3核查](<work/sony-firmware-20261024/stage133-FX5-source-availability-and-portability/README.md>)：五个官方GPL包静态拆读，5.15/CXD90201与FX3参考平台不同；当前表无目标HEVC主录，完整FX5机身固件未取得，互刷未放行。

- [2026-10-27 FX3 救砖与官方接口](<reports/索尼 FX3 救砖与官方接口.md>)：官方失败分支、真实恢复/换板案例及维修/SDK/BootROM边界复核；双机仍无已验经典FX3独立救援，主动查询与持久写入未放行。[本轮登记](<work/sony-firmware-20261024/stage132-public-recovery-and-service-interfaces/README.md>)。

- [2026-10-27 FX3 Mac缓存盘点与备份读路径](<work/sony-firmware-20261024/stage130-backup-read-path-side-effects/README.md>)：明确授权后缓存确认1台054C/0DA1、接口08/06/50及MSC驱动；GET_FILE2待日志写分支/路径/容量假设收紧，主动文件/备份/刷写仍未放行。

- [2026-10-27 FX3正确AP配置与首次上机准备](<work/sony-firmware-20261024/stage129-AP-DMM-config-and-device-trial-plan/README.md>)：官方AP603单位、目标20全匹配且各1块；上机放行清单/Mac缓存工具离线自测完成，实际查询、备份/编码/恢复和刷写未验未放行。

- [2026-10-27 FX3 DMM模块与配置适用范围](<work/sony-firmware-20261024/stage128-DMM-provider-and-config/README.md>)：同包模块/配置重验，36原叶例确认长度回退非8块守卫、Open改计数；ipsxcp配置348单位与目标20单位零匹配，实际配置/分配/主录恢复未验。

- [2026-10-27 FX3 DMM回复边界与原节点生产](<work/sony-firmware-20261024/stage127-native-DMM-response-and-node-producer/README.md>)：140正式片段、17原节点接SetMemTbl；人工9/10块输入暴露布局重叠/复制边界，候选保守拒绝，真实分配/映射/主录与恢复未验。

- [2026-10-27 FX3 缓冲字段到原Open调用者](<work/sony-firmware-20261024/stage126-native-DMM-buffer-to-Open/README.md>)：8例160片段接原SetMemTbl/Enqueue与单流clear98构建，补特定旧值依赖；人工区域/元数据非物理分配，实录及恢复未验。

- [2026-10-27 FX3 前端与DMM模式一致性](<work/sony-firmware-20261024/stage125-native-frontend-DMM-consistency/README.md>)：固定前端接原参数复制/内存模式选择，16组声明输入前后一致、192片段；真实分配/资源16M编码与恢复未验。

- [2026-10-27 FX3 Close计数与清理结果](<work/sony-firmware-20261024/stage124-native-Close-counter-and-cleanup/README.md>)：18例108片段接原计数器与Close分支，剩余计数可跳过关闭；模式字清零非DMM释放证明，真实主录/全退出/恢复未验。

- [2026-10-27 FX3 回调结果与写入完成顺序](<work/sony-firmware-20261024/stage123-native-record-result-and-write-finish/README.md>)：22例86片段核对结果汇总、回调清除及记录释放/事件先后；零值或完成事件不充全退出，实际主录和恢复未验。

- [2026-10-27 FX3 回调记录与执行队列寿命](<work/sony-firmware-20261024/stage122-native-callback-record-and-execqueue/README.md>)：12例54片段核对384字节记录、8ea0任务复制及原worker分派；队列块和外部记录分开验，实际完成/回收/恢复未验。

- [2026-10-27 FX3 Start调用者与返回分层](<work/sony-firmware-20261024/stage121-native-Start-caller-and-return/README.md>)：22例106片段核对128字节参数、事件1003与错误回调记录；Start5c源为thumbnailId，局部API零返回不充硬件成功，主录恢复未验。

- [2026-10-27 FX3 槽位选择与状态来源](<work/sony-firmware-20261024/stage120-native-start-slot-publication/README.md>)：18例62片段确认状态字节早于本次编码排队、GetSlotID可登记映射；诊断排除副作用，真实编码/空闲及恢复未验。

- [2026-10-27 FX3 录制状态与锁配对](<work/sony-firmware-20261024/stage119-native-record-status-lock-contract/README.md>)：30例50个原片段区分状态读取/更新事务和参数锁，定位Set/Start/Stop共用API互斥锁候选；实际空闲/代次/编码恢复未验。

- [2026-10-27 FX3 参数通知与等待链](<work/sony-firmware-20261024/stage118-native-parameter-notice-wait/README.md>)：40例84个原片段核对通知键/promise和等待；参数加载就绪不充编码器启动、空闲或配置代次证据，主录/恢复未验，仅Mac。

- [2026-10-27 FX3 原音频/代理与前端配对检查](<work/sony-firmware-20261024/stage117-native-audio-proxy-admission/README.md>)：原helper/调用者与guest准入补强151阶段；局部返回非整组有效，完整配置/采音同步/编码及恢复未验，仅Mac。

- [2026-10-27 FX3 受限MAIN前端与外部参数寿命](<work/sony-firmware-20261024/stage116-scoped-MAIN-frontend/README.md>)：guest编译副本/原Set-Get外部共享别名及拒绝对照78阶段；真实前端/完整配置/编码和恢复仍未验，仅Mac。

- [2026-10-27 FX3 MAIN质量与码率身份分域](<work/sony-firmware-20261024/stage115-native-main-quality-domains/README.md>)：原质量6/FH名义16000与8/FF25000、SIDB16/25及通用VPC6来源130新阶段；实际前端/16M编码及恢复未验，仅Mac。

- [2026-10-27 FX3 消息释放与回调登记寿命](<work/sony-firmware-20261024/stage114-native-callback-release-order/README.md>)：原MPR释放请求/引用更新及不同finish分支110阶段；登记记录不是消息lease，真实MAIN实录/同机恢复仍未验，仅Mac。

- [2026-10-27 FX3 原UIPC映射与分发守卫](<work/sony-firmware-20261024/stage113-native-uipc-mapping-guards/README.md>)：原操作分发/归属/2MiB映射限制及独立指针正反转换112阶段；真实映射、寿命、MAIN实录与恢复仍未验，仅Mac。

- [2026-10-27 FX3 分配空间与回复尾标记](<work/sony-firmware-20261024/stage112-native-allocation-tail/README.md>)：原128B块/77777777尾标记解释声明条件下44→48复制，70阶段；实际池/用户映射/寿命及硬件恢复仍待验，仅Mac。

- [2026-10-27 FX3 单流调用与44字节回复](<work/sony-firmware-20261024/stage111-native-Open-reply-producer/README.md>)：原非空回复指针、Ack/完成事件身份与发送长度72阶段；44B发送到48B存储及实际硬件/恢复仍未验收，仅Mac。

- [2026-10-27 FX3 原OSAL封装与回复匹配](<work/sony-firmware-20261024/stage110-native-OSAL-envelope/README.md>)：原接收分类、长度边界与同步/其他回复路由74阶段；真实传输、锁、固定参数寿命与实机验收仍缺，仅Mac。

- [2026-10-27 FX3 原参数控制与外部参数寿命](<work/sony-firmware-20261024/stage109-native-ParameterControl/README.md>)：原虚表、MovieEncoder参数表、MWF存储及缺项对照62阶段；56B命令复制仍引用外部raw98，锁/分配和实机验收保持未证，仅Mac。

- [2026-10-27 FX3 原消息库与参数复制](<work/sony-firmware-20261024/stage108-original-Dataflow-copy/README.md>)：同固件原memcpy/memset、Dataflow复制/清理、截断对照和AV虚拟指针消费64阶段；硬件与恢复未验收，仅Mac。

- [2026-10-27 FX3 固定消息区与指针域更正](<work/sony-firmware-20261024/stage107-native-fixed-message-area/README.md>)：原类型2长度200、消息+8物理/+28虚拟、ViewId来源及容量前提92阶段；公开恢复证据复查仍未覆盖FX3，仅Mac。

- [2026-10-27 FX3 原MPR Open字段来源](<work/sony-firmware-20261024/stage106-native-MPR-Open-fields/README.md>)：声明候选由原构造/转换识别HEVC_MP4、HD42010、29_97、FH；280生产阶段复用+96接收阶段，原日志未执行。上游来源/16M资源/完整Open/实录恢复仍缺，仅Mac。

- [2026-10-27 FX3 原MAIN参数生产者缺口](<work/sony-firmware-20261024/stage105-native-main-parameter-producer/README.md>)：此格式转换32组无候选VPC6，通用检查结束分支不足以证明支持；108阶段，配置/编码Open来源继续追，实录与恢复未验收，仅Mac。

- [2026-10-27 FX3 共享movie事件与MPR介质录制启动](<work/sony-firmware-20261024/stage104-native-card-recording-start-routing/README.md>)：普通录制另有Prepare/RecStart链，原介质构包及检查前缀82阶段；共享事件不是编码器复用证明。目标主录/恢复未验收，仅Mac。

- [2026-10-27 FX3 推流Open与目标MAIN差别](<work/sony-firmware-20261024/stage103-native-streaming-open-profile/README.md>)：原HD29.97分支识别STREAMING_HEVC_BSF/QT18M/4208；10源配置/150阶段，帧率预期已校正。相同HEVC模块类别不是MAIN实例证明，实录/恢复仍未证，仅Mac。

- [2026-10-27 FX3 原应用码率请求生产与SRT范围](<work/sony-firmware-20261024/stage102-native-app-qos-producer/README.md>)：原16000输入生成16M/80字节命令，原字节接收及下层转发保持；14组/50阶段。现有调用者属推流，卡内MAIN/实录/恢复仍未证，仅Mac。

- [2026-10-27 FX3 接收参数副本与上层转换边界](<work/sony-firmware-20261024/stage101-native-qos-receive-snapshot/README.md>)：原48字节上下文副本/回复关联及复用范围，12对照加8原转换探针，共104阶段；当前原转换表无10a，真实MAIN生产者/实录/恢复仍未证，仅Mac。

- [2026-10-27 FX3 原QoS状态分派与请求寿命](<work/sony-firmware-20261024/stage100-native-qos-routing-and-queue-lifetime/README.md>)：32组/118阶段，原ROM选择排队或转发；指针出队0不代表请求完成。不同接口原指针已区分，MAIN策略/实录/恢复仍未证，仅Mac。

- [2026-10-27 FX3 现存缓存参数离线审计工具](<work/sony-firmware-20261024/stage99-offline-cached-argument-auditor/README.md>)：18项合成边界通过，区分JSON/WQL/原生argv、实例与硬件ID及tree参数；Mac缺私有源，真实零匹配/当前连接仍UNKNOWN。无新设备查询，仅Mac。

- [2026-10-27 FX3 原日志缓冲、实际MMIO边界及恢复范围](<work/sony-firmware-20261024/stage98-native-trace-buffer-origin-and-recovery-scope/README.md>)：12场景84阶段；原69项/62缓冲初始化，mode实际消费trace状态到计时MMIO前，CACHE未执行。公开A7CII/A7IV恢复范围核对，非FX3保证；仅Mac。

- [2026-10-27 FX3 实际owner构造与原模式分派纠正](<work/sony-firmware-20261024/stage97-native-owner-construction-and-mode-dispatch/README.md>)：12场景60阶段；纠正1352f0完整owner称谓，原managerf2c申请/12f21c构造→ROM索引0模式处理及历史记录，停trace前；完整模式/MAIN硬件恢复未证，仅Mac。

- [2026-10-27 FX3 原初始化表、管理器对象与选择路由](<work/sony-firmware-20261024/stage96-native-bootstrap-and-manager-routing/README.md>)：18场景62阶段；原manager后半段分配双类，两个原消息字段选择并独立路由至frame锁前。原boot表前缀有界执行；模式回调/正常启动/MAIN硬件未证，仅Mac。

- [2026-10-27 FX3 原控制对象构造、虚分派与锁回调边界](<work/sony-firmware-20261024/stage95-native-gop-controller-construction-and-dispatch/README.md>)：14场景232阶段；原vtable与堆构造、按类实际分派只在前置回调状态通过，原绑定锁回调后停RTOS，更新停引用。基类仅返回，非实际MAIN/编码恢复，仅Mac。

- [2026-10-27 FX3 原帧分配接原构造与恢复案例边界](<work/sony-firmware-20261024/stage94-native-frame-allocation-to-construction/README.md>)：原type5分配句柄→原caller地址转换→构造/header，5场景203阶段含耗尽；IRQ/MAIN/实际编码及FX3救砖仍未验。A7CII应用模式回滚反馈单列，仅Mac。

- [2026-10-27 FX3 原新帧、帧头与1080参数关系](<work/sony-firmware-20261024/stage93-native-frame-header-and-crop-reconciliation/README.md>)：原frame构造/header与crop4×2核对1088→1080，6帧/4裁剪44阶段；更新指针先赋后停GP引用前，非真实MAIN/SPS/视频/硬件恢复，仅Mac。

- [2026-10-27 FX3 完整几何返回与IRQ适用范围](<work/sony-firmware-20261024/stage92-native-geometry-builder-and-IRQ-scope/README.md>)：原几何完整返回接实际帧JAL，9例27阶段；内部1920×1088不代替可见1080，真实模式/帧头/MAIN/IRQ及硬件恢复未验，仅Mac。

- [2026-10-27 FX3 类型4与首次缓存缓冲](<work/sony-firmware-20261024/stage91-native-type4-first-cache-buffer/README.md>)：原128×512池/首次句柄/物理48字节复制、耗尽错误与归还重借，4例164阶段；注册/CACHE/IRQ有显式空缺，真实同步/MAIN/硬件及恢复未验，仅Mac。

- [2026-10-27 FX3 元数据布局、引用边界与原调用者](<work/sony-firmware-20261024/stage90-native-metadata-copy-and-caller/README.md>)：区分候选A4部分位复制与raw8c完整句柄复制；16例，非空停GP引用前，分开caller写119/67→120/68或绑定帧。真实生产/队列/MAIN与硬件恢复未证，仅Mac。

- [2026-10-27 FX3 待处理缓存的原初始化与转存来源](<work/sony-firmware-20261024/stage89-native-pending-cache-origin/README.md>)：原空8字节记录/已有缓冲分别验证，共20例66阶段；c90是帧参数缓存，不是编码成功ACK。真实元数据/所有权/调度/MAIN与硬件恢复未证，仅Mac。

- [2026-10-27 FX3 上游发布与GOP门控](<work/sony-firmware-20261024/stage88-native-frame-publication-and-gop-gate/README.md>)：声明事件经原发布/置gate/门控复制清位，12例32阶段；缺句柄停分配前。真实记录/公共虚回调/调度/MAIN与硬件仍未证，仅Mac。

- [2026-10-26 FX3 帧状态与命令位消费](<work/sony-firmware-20261024/stage87-native-frame-state-command-bit/README.md>)：声明句柄图原36→Frame4da→参数覆盖→原命令叶函数；20例100阶段，分析副本旧差异5降4。源gate/发布仍0，非正常分派/硬件，仅Mac。

- [2026-10-26 FX3 VUI标志与模式转换原帧](<work/sony-firmware-20261024/stage86-hevc-vui-mode-conversion/README.md>)：原VUI→caller/JAL→保留原帧转换，14例154阶段；GOP块旧值依赖7降5、gate仍0。frame4da覆盖仅静态，非硬件或恢复，仅Mac。

- [2026-10-26 FX3 HEVC分行布局与完整GOP构造](<work/sony-firmware-20261024/stage85-hevc-slice-layout-production/README.md>)：原32字节布局生成、零模式完整构造自然返回，10例80阶段；GOP块旧值依赖39降7、帧gate仍0，非硬件提交，仅Mac。

- [2026-10-26 FX3 HEVC主体与ROM查表](<work/sony-firmware-20261024/stage84-hevc-native-config-body/README.md>)：原裁剪/格式助手自然返回，16例94阶段；GOP块仍39字节或位依赖旧值。另9例校准CODE的取消延迟槽观察；非完整初始化/MAIN/硬件，仅Mac。

- [2026-10-26 FX3 HEVC初始几何与码率字段](<work/sony-firmware-20261024/stage83-hevc-initial-config-field-provenance/README.md>)：codec2c→配置84→声明GOPc8、块数119/67与边界；16例48阶段，三个独立入口非完整初始化/MAIN/硬件，仅Mac。

- [2026-10-26 FX3 HEVC帧参数交接与旧副本](<work/sony-firmware-20261024/stage82-hevc-frame-parameter-handoff/README.md>)：目标字经原156+48字节交接进独立缓冲，源gate清零而副本保留；8普通/2顺序14阶段。非实际调度/码率算法/硬件或恢复证据，仅Mac。
- [2026-10-26 FX3 HEVC目标消费与清理边界](<work/sony-firmware-20261024/stage81-hevc-qos-consumer-and-release/README.md>)：原HEVC GOP消费两层更新位及目标字，清最后位仍未释放句柄；10消费/6清理22阶段，完整GOP/硬件/主录/恢复未证，仅Mac。
- [2026-10-26 FX3 待处理标志与尾参数转交](<work/sony-firmware-20261024/stage80-vcd-pending-and-timing/README.md>)：pending清零而后端更新仍在，完整尾参数复制；修正本机MIPS观察钩子影响，14例24阶段。硬件/主录/恢复未证，仅Mac。
- [2026-10-26 FX3 VCD侧QoS消费与缓冲转交](<work/sony-firmware-20261024/stage79-vcd-qos-consumption/README.md>)：原目标字进入声明状态/已有句柄缓冲，pending仍保留；12输入18入口，分配/硬件应用/主录/恢复未证，仅Mac。
- [2026-10-26 FX3 原启动参数与QoS尾字段](<work/sony-firmware-20261024/stage78-native-start-flags-and-query-tail/README.md>)：原登记查询接完整参数准备，区分16M预置与可选20M块，8例44段；完整Start/硬件优先级/主录/恢复未证，仅Mac。
- [2026-10-26 FX3 上游恢复与REA入口核对](<work/sony-firmware-20261024/stage77-upstream-recovery-boundaries/README.md>)：其它机型恢复不能替代FX3保障；A6700参考范围复算与REA入口限制已核清，未新增实际备份/恢复/主录验收，仅Mac。
- [2026-10-26 FX3 原重选与参数包寿命](<work/sony-firmware-20261024/stage76-native-reselection-and-packet-lifetime/README.md>)：独立重选后新局部包回默认24498176，旧16M包保持；原型再入OWNER13关闭私有gate并保留引用，3例29段。非真实并发/完整Start/主录/恢复证据；仅Mac。
- [2026-10-26 FX3 客体预置副本与原工作区分离](<work/sony-firmware-20261024/stage75-private-preset-storage/README.md>)：原COMMON+e010有原生用途；客体副本移至单控制器试验槽，16M/56字节返回容器/原区/其它owner/guard保持，7例40段复核。原选择指针同步与真实分配/主录/恢复未证；仅Mac。
- [2026-10-26 FX3 离线适配器返回结构修复](<work/sony-firmware-20261024/stage74-rate-result-ABI-fix/README.md>)：旧24字节声明覆盖保存返回地址，已隔离；新56容器覆盖原52字节跨度并保持保存槽，6例41段复核。仅客体修复，实际通道返回/主录/恢复未证；Windows延后。
- [2026-10-26 FX3 原释放消息与回复检查](<work/sony-firmware-20261024/stage73-native-free-message-path/README.md>)：Mac离线原释放4例、独立回复7例共55段；标志路径先依赖诊断消息和高ID稀疏查找，两分支均停在原内核锁前。局部确认不等于物理释放，主录/同机恢复未证；Windows延后。
- [2026-10-26 FX3 原管理退出与释放凭据](<work/sony-firmware-20261024/stage72-native-manager-teardown/README.md>)：Mac离线8例40段；外层返回0/描述符清空不保证实际释放，共享引用与最后引用分支分开核对。输出字段接到请求仅静态，真实消费者/物理释放/主录和救援未证；Windows延后。
- [2026-10-26 FX3 ROI记录队列与输出转交](<work/sony-firmware-20261024/stage71-native-buffer-record-fifo/README.md>)：原FIFO两组56段、独立转交两组16段；COMMON清12字节后输出仍保留指针。旧释放边界名细化为记录入队，缓冲来源/真实消费者/物理释放/主录和恢复未证；仅Mac。
- [2026-10-26 FX3原失败与条件Close范围](<work/sony-firmware-20261024/stage70-native-open-rejection/README.md>)：原FH失败至未执行回调仍有借出注册；3例28段，两个旧值Close到存储释放边界，原文件初值对照仅局部归还。Windows按用户要求延后，仅Mac；实机主录/回退/救援仍未验收。
- [2026-10-26 FX3私有16M进入原通道请求链](<work/sony-firmware-20261024/stage69-native-16M-callpath/README.md>)：客体新增调用处写入/原查询16M后进入原OSAL至内核锁边界，9例58段；原失败清理未证。Windows根补查零匹配，既有记录参数审计已传待代发，实机主录/救援仍未验收。
- [2026-10-26 FX3当前缓存身份与查询处理范围](<work/sony-firmware-20261024/stage68-current-USB-associations/README.md>)：新CIM快照1个同摘要USB根和3磁盘节点均在线正常；父子/驱动后续任务已传待代发。原查询处理函数40组RAM仿真通过，不能替代实际接口、刷写或救砖验收。
- [2026-10-26 FX3重新连接筛选与原USB身份模板](<work/sony-firmware-20261024/stage67-connected-native-pnp/README.md>)：精确当前ID筛选无匹配，厂商/型号交叉核对已提交待结果；原7件USB组件、3模板/5指针别名核对，通用INQUIRY不能代替固件版本和当前接口验证。
- [2026-10-26 FX3原生PnP缓存关联复核](<work/sony-firmware-20261024/stage66-native-pnp-cache-review/README.md>)：7条查询通过、10件脱敏回执取回；USB父节点与3磁盘子节点均断开，当前候选0；主录、当前绑定及恢复仍未验收。
- [2026-10-26 FX3 Windows缓存准备与原运行环境](<work/sony-firmware-20261024/stage65-windows-cache-and-runtime-readiness/README.md>)：UU交接和x64编译通过；PS1采集被策略阻止，原生PnP枚举待回执；原启动5指令与公开vendor ABI核对通过，完整Linux、硬件主录和恢复仍未验收。
- [2026-10-26 FX3 原OSAL离线链接与内核边界](<work/sony-firmware-20261024/stage64-osal-offline-link/README.md>)：3模块973重定位和原LIRO绑定/33段通过，请求到未执行IRQ锁、init到未执行驱动注册；真实Linux/硬件主录与恢复仍未验收。
- [2026-10-26 FX3 原资源消息与OSAL依赖](<work/sony-firmware-20261024/stage63-resource-message-boundary/README.md>)：原216字节消息到未绑定申请分支21段通过；47导入静态来源补齐，OSAL加载/初始化、缓冲区/回复、硬件主录与恢复仍未验收。
- [2026-10-26 FX3 原管理对象与factory队列](<work/sony-firmware-20261024/stage62-native-manager-factory/README.md>)：原manager、6+2构造/绑定及空闲队列21段通过，9次对象外隔离；请求进到未执行资源提供者，真实OSAL/硬件/主录与恢复未验收。
- [2026-10-26 FX3 原行选择到通道申请边界](<work/sony-firmware-20261024/stage61-native-row-channel/README.md>)：同客体queued/原静音诊断/匹配/预置和尺寸准备30段通过，目标独立查询16M；管理对象尚未绑定，未执行申请、主录或恢复。
- [2026-10-26 FX3 原内部诊断文本与时间边界](<work/sony-firmware-20261024/stage60-native-diagnostic-format/README.md>)：原实际va_list经内部格式化产146字节，20段含截断/零容量通过；完整日志停未读时间寄存器，硬件/同步/成片与恢复仍未验收。
- [2026-10-26 FX3 原诊断门控与连续匹配](<work/sony-firmware-20261024/stage59-native-diagnostic-gates/README.md>)：31段含6次原诊断早退条件下的完整matcher连续返回，参数为原字符串/标量；真实日志状态/开启后端/同步/硬件和恢复仍未验收。
- [2026-10-26 FX3 原调用点与临时参数栈帧](<work/sony-firmware-20261024/stage58-native-match-call-frame/README.md>)：一个客体BL接编译包装函数，临时视图被原matcher读取并经真实尾声返回原caller；25段通过，诊断/实际装载/同步/硬件与恢复仍未验收。
- [2026-10-26 FX3 保持FH身份的资源匹配原型](<work/sony-firmware-20261024/stage57-native-resource-alias/README.md>)：临时视图选MAIN386，严格原FH私有写者得16M，25原片段/33原型调用通过；真实hook/共享同步/完整硬件与恢复仍缺，Windows仅虚拟屏协作待连接恢复。
- [2026-10-25 FX3 空名称与结束资料原路径](<work/sony-firmware-20261024/stage56-native-stop-name-flow/README.md>)：同版原运行库支撑50段有界执行，空名进入StopCmp及MAIN资料；不据此判Open失败或全局无害，资源16M桥接、完整成片与同机恢复仍待验收。
- [2026-10-25 FX3 原封装元数据与HD分类](<work/sony-firmware-20261024/stage55-native-mux-identity/README.md>)：36段原执行生成HD29.97/raw16000元数据；原分类默认97、UHD对照命中，实际用途仍待追，质量桥接/完整启动/硬件与恢复仍待验收。
- [2026-10-25 FX3 原Open队列与匹配输入来源](<work/sony-firmware-20261024/stage54-native-open-matcher-input/README.md>)：24段原执行接通分配/登记/common到matcher入口，MAIN尾角色1已绑定；FH仍不匹配，改上层FF会改变码率查询，完整启动/硬件与恢复仍待验收。
- [2026-10-25 FX3 原标签生成与完整帧填充](<work/sony-firmware-20261024/stage53-native-frame-fill/README.md>)：112段原执行接通typed标签序列化/完整fill/独立几何消费；更正格式偏移+28，返回1不等整帧有效，真实MAIN、完整启动/硬件与恢复仍待验收。
- [2026-10-25 FX3 帧槽归还、队列与标签来源](<work/sony-firmware-20261024/stage52-frame-lifetime-and-fill/README.md>)：193段原执行区分queue0与槽归还，复借清记录；原标签复制生成几何，通知/代次/完整填充、硬件与恢复仍待验收。
- [2026-10-25 FX3 帧槽来源与两类事件](<work/sony-firmware-20261024/stage51-frame-slot-provenance/README.md>)：原40帧槽分配/清零及Start/逐帧包、标志准备62段验证，索引不当编码通道；更正旧表4项越界枚举，真实填充/归还/完整启动、硬件与恢复仍待验收。
- [2026-10-25 FX3 原编码输入几何生成](<work/sony-firmware-20261024/stage50-native-start-geometry/README.md>)：原通道索引/打包生成HD几何并通过配套原谓词，76段A64与6次MIPS验证；真实记录来源/MAIN登记/完整启动、硬件与恢复仍待验收。
- [2026-10-25 FX3 原VCD消费端校验](<work/sony-firmware-20261024/stage49-vcd-consumer-validation/README.md>)：71次原MIPS函数/路由验证，配置谓词不读码率字或52字节；配套基带块返回3006，需补原start-input生产者，真实硬件与恢复仍待验收。
- [2026-10-25 FX3 编码参数初值与旧值保留](<work/sony-firmware-20261024/stage48-codec-initialization/README.md>)：14次原对象构造/32段验证核对52字节的文件零初值与旧值保留，原COMMON清零已执行；真实复用/完整请求/硬件与恢复仍待验收。
- [2026-10-25 FX3 原装载器与内核清零](<work/sony-firmware-20261024/stage47-runtime-provider-binding/README.md>)：绑定LIRO导入和官方内核原内存函数，部分链接客体中两段原状态构造完成并返回；16段验证通过，52编码字节/真实同步/硬件与恢复仍待验收。
- [2026-10-25 FX3 新版恢复实现与故障案例复核](<work/sony-firmware-20261024/stage46-upstream-restore-audit/README.md>)：审计3.0原厂区域恢复/服务重接，18项原主机函数检查通过；新增条件性启动自述仍不能证明FX3视频链救援，实机备份/恢复待验收。
- [2026-10-25 FX3 STOP通知与输出状态队列](<work/sony-firmware-20261024/stage45-stop-notification-routing/README.md>)：原接收/回调路由进入输出事件，返回0时仍可排队；A/V停止有中间状态，相同包另有生产者，完整停止/硬件与恢复仍待验收。
- [2026-10-25 FX3 合法STOP、映射清理与完成通知](<work/sony-firmware-20261024/stage44-stop-unmap-and-completion/README.md>)：原STOP动作绑定PCIATU unmap，seq_id/forced标志与通道完成包已核对；局部清零不能证明底层完成，完整停止/硬件与恢复仍待验收。
- [2026-10-25 FX3 原事件构造与代码退出](<work/sony-firmware-20261024/stage43-native-functor-drain/README.md>)：原虚表/出队调用确认标志全清时代码仍可未退出；受控START正文沿原栈返回，真实线程/合法STOP/硬件与恢复仍待验收。
- [2026-10-25 FX3 编码状态事件与锁边界](<work/sony-firmware-20261024/stage42-encoder-state-and-lock-boundaries/README.md>)：本地参数归还后上层STOP仍可排队，包装真不等于READY/IDLE；原状态/事件名已绑定，真实锁/出队/硬件与恢复未验收。
- [2026-10-25 FX3 MAIN START结果与同对象周期](<work/sony-firmware-20261024/stage41-main-start-result-cycle/README.md>)：原START读者只还消息，消息缓冲原生再借用于STOP后归还四类参数；上层锁/状态/代次、硬件与恢复仍待验收。
- [2026-10-25 FX3 START/STOP类型与MAIN消息发布](<work/sony-firmware-20261024/stage40-response-types-and-publication/README.md>)：绑定type0 START_DONE/type3 STOP_DONE；MAIN14跳过其它流可选回调，原消息发布接通STOP清理，真实消息/代次/HAL与恢复仍待验收。
- [2026-10-25 FX3 原缓冲归还与消息清理](<work/sony-firmware-20261024/stage39-opa-return-and-reply/README.md>)：原四类缓冲归还/索引移除在客体通过；类型不符仍可返回0，部分失败留下混合状态，真实通知/代次/HAL与恢复待验收。
- [2026-10-25 FX3 扩展IMOLA参数与池缓冲登记](<work/sony-firmware-20261024/stage38-imola-parameter-copy/README.md>)：原448字节复制/索引保留16M，复选原预置不清副本；52字节初始化及真实消费/归还/HAL/恢复待验证。
- [2026-10-25 FX3 编译客体写者与在途参数登记](<work/sony-firmware-20261024/stage37-compiled-scoped-writer/README.md>)：A64原型自行复制/改值/发布，原封装读取16M；生产者或准备包在途时拒绝数据复原，真实同步/消费者/硬件与救援仍未验证。
- [2026-10-25 FX3 MAIN FF 私有16M数据候选](<work/sony-firmware-20261024/stage36-private-preset-data-candidate/README.md>)：原封装片段消费私有副本生成16M目标字段，其它字段/客体/原件不变；复选指针不清除旧参数包，原生写者、硬件与恢复仍未验证。
- [2026-10-25 FX3 HEVC 预置默认值](<work/sony-firmware-20261024/stage35-hevc-preset-defaults/README.md>)：原FF MAIN预置解码target24498176，代理FH才是16000000；绑定静态预置来源，默认查询不能当实际码率回读，硬件与恢复仍未验证。
- [2026-10-25 FX3 QoS 请求、确认与码率转换](<work/sony-firmware-20261024/stage34-qos-request-and-feedback/README.md>)：原数值路径可精确表示16000000并按trace上限限幅；一种确认在应用前构建，真实单位、FF默认码率、硬件与恢复仍未验证。
- [2026-10-25 FX3 IMOLA 参数匹配与质量边界](<work/sony-firmware-20261024/stage33-imola-format-matcher/README.md>)：现有FH主录目标未命中原表；原表存在HD29.97 HEVC42010 MAIN项，人工FF对照条件命中，真实码率、完整资源链与恢复仍未验证。
- [2026-10-25 FX3 编码资源描述符与原枚举](<work/sony-firmware-20261024/stage32-resource-open-descriptor/README.md>)：独立原片段保留HD/29.97/42010并区分HEVC_MP4与代理；质量转FH，原生依赖、资源接受、真实码率与恢复仍未验证。
- [2026-10-25 FX3 timing参数与写入所有权](<work/sony-firmware-20261024/stage31-timing-parameter-ownership/README.md>)：原Open动作保持目标包并构造输入组件请求，选择低帧率逐行分支；配置/Open整包覆盖同一存储，真实顺序与硬件/恢复仍未验证。
- [2026-10-25 FX3 前端消费与共同timing接收端](<work/sony-firmware-20261024/stage30-frontend-pending-consumption/README.md>)：原消费片段令前端计数归零时下游仍持有参数；Open和SET_REC_FORMAT共同句柄已定位，完整协调/资源/硬件和恢复仍未验证。
- [2026-10-25 FX3 主录前端排队与参数保留](<work/sony-firmware-20261024/stage29-main-frontend-open/README.md>)：原局部分支可排队返回1或保留目标0x98参数；SET_REC_FORMAT为另一路重建，29.97/精确30帮助函数结果不同，完整合并/硬件及恢复仍未验证。
- [2026-10-25 FX3 主录前端与动作接口](<work/sony-firmware-20261024/stage28-main-frontend-binding/README.md>)：原构造分支把索引0/0x805700f9接到ext-ISP前端，并将普通Open回调绑定timing_normal；前端参数转交、完整硬件接受及恢复仍未验证。
- [2026-10-25 FX3 Open状态机与待处理参数](<work/sony-firmware-20261024/stage27-encoder-state-machine/README.md>)：12例核对数值状态、忙碌排队和动作选择；待处理复制保留源参数指针，完整动作/硬件接受与恢复安全点仍未验证。
- [2026-10-25 FX3 MC Open分派与状态参数](<work/sony-firmware-20261024/stage26-mc-open-routing/README.md>)：29例核对转换CID/MID、原构造路由、状态选择、参数复制和DFS标量；真实注册/地址转换、完整Open/Start与恢复仍未验证。
- [2026-10-25 FX3 编码映像与地址模型](<work/sony-firmware-20261024/stage25-mc-image-map/README.md>)：在av-cam核对编码类、MC标识与局部地址引用；CPapp仅建部分候选映射，Imola日志分支为通道哨兵比较，实际MC接收、格式接受和恢复仍未验证。
- [2026-10-25 FX3 接收序列与掩码范围](<work/sony-firmware-20261024/stage24-receiver-dispatch/README.md>)：43个边界用例确认普通MAIN/proxy同选usecase1，格式掩码已绑定解码启动；MC编码校验及实际Open/Start仍未验证。
- [2026-10-25 FX3 MAIN与代理编码入口](<work/sony-firmware-20261024/stage23-encoder-boundary/README.md>)：原包与资源片段绑定MAIN/proxy外层身份15/18及单/双流分叉；核心视频参数一致，完整消息/能力校验和硬件Open/Start仍未验证。
- [2026-10-25 FX3 实验对象登记与代码退出](<work/sony-firmware-20261024/stage22-lifetime-registry/README.md>)：登记参考协议通过1194个有界模型状态及4个原析构片段；数据退出与代码安全点分开，原生门禁/恢复和实机主录仍未验证。
- [2026-10-25 FX3 构造与入队边界](<work/sony-firmware-20261024/stage21-admission-boundary/README.md>)：17个阶段及3个原判断对照显示队列外标记对象需单独观察；明确入口与整组停止边界，实际门禁、卸载及恢复仍未验证。
- [2026-10-25 FX3 工作线程与退出观察](<work/sony-firmware-20261024/stage20-worker-lifecycle/README.md>)：绑定当前对象的发布、任务调用和收尾顺序；21个边界片段及14个原等待判断通过，完整同步/退出及实机恢复仍未验证。
- [2026-10-25 FX3 缓存替换与等待边界](<work/sony-firmware-20261024/stage19-queue-boundary/README.md>)：刷新token不代表配置代次，wait集合命中可按条件放行；完善退出观察条件，尚无实机清空/恢复验收。
- [2026-10-25 FX3 剩余时间缓存身份](<work/sony-firmware-20261024/stage18-cached-remain/README.md>)：19组原缓存链对照准备目标GetMovieRemain输入；真实秒数未计算，缓存失效、统一代次及实机恢复仍待验证。
- [2026-10-25 FX3 捕获身份与退出边界](<work/sony-firmware-20261024/stage17-captured-profile/README.md>)：局部身份避免捕获后开关变化；定位model_lock和SQproxy字段，移除消费者负例明确在途清空要求，缓存/实机恢复仍未完成。
- [2026-10-25 FX3 查询传参、锁范围与字段更正](<work/sony-firmware-20261024/stage16-system-snapshot/README.md>)：两处原调用者76次局部对照；包0x81更正为逐行标志，记录锁不覆盖查询，硬件主录及恢复仍待验收。
- [2026-10-25 FX3 独立激活与配置一致性](<work/sony-firmware-20261024/stage15-private-activation/README.md>)：合法模型保留通过局部对照；开关与模式快照负例明确同步缺口，未形成上机或救砖方案。
- [2026-10-25 FX3 模型更新与生命周期边界](<work/sony-firmware-20261024/stage14-model-lifecycle/README.md>)：局部值槽位和17组合成上下文对照定位跨模式缺口；同值写仍标变更，菜单/持久化/实机验收仍未完成。
- [2026-10-25 FX3 查询参数与定点原型一致性](<work/sony-firmware-20261024/stage13-query-profile/README.md>)：guest查询helper与setter目标参数一致；30项原查找、19组合法HS、37目标查询及9组控制通过，完整调用者/菜单/实录与恢复仍未验收。
- [2026-10-25 FX3 定点原型与查询准备](<reports/索尼 FX3 定点原型与查询准备.md>)：受限客体原型接通实验选择、真实setter与MAIN参数准备，19组合法HS4K对照保持一致；最小MSC包仅完成离线审查，查询/UI、实录与同机恢复验收仍未完成。
- [2026-10-25 FX3 目标模式与模型门禁](<reports/索尼 FX3 目标模式与模型门禁.md>)：闭合普通HS4K typed选择及帧率/质量别名，区分外部HEVC HD表示并更正旧控制帧率；目标模式、实录与恢复验收仍未完成。
- [2026-10-25 FX3 主录设置与回复链路](<reports/索尼 FX3 主录设置与回复链路.md>)：闭合正常回复静态链，完成79MB目标长度的31项离线重组测试；定位主录模型输入并排除不合格常数替换，实机与恢复验收仍待完成。
- [2026-10-25 FX3 诊断协议与重载核验](<reports/索尼 FX3 诊断协议与重载核验.md>)：核准内部15–18处理器与WBI内核接口语义，交付纯字节codec及19项离线fixture；外层会话、当前backend及故障恢复仍未实测。
- [2026-10-25 FX3 服务方案适配评估](<reports/索尼 FX3 服务方案适配评估.md>)：对照通信、实际原生ELF和检查点恢复机制，明确可复用框架与FX3专用重建项；所有主动能力保持禁用，尚未建立救砖保障。
- [2026-10-25 FX3 7.02 独立诊断与恢复入口](<reports/索尼 FX3 独立诊断与恢复入口.md>)：用户菜单确认7.02；审计公开工具真实调用与本地文件处理链，分离认证、WBI写入和恢复证据，尚未验证故障后入口或放行持久写入。
- [2026-10-25 FX3 双机协作与 HD HEVC 仿真复核](<reports/索尼 FX3 双机协作与HD HEVC仿真复核.md>)：通过 UU 交接现有 Windows Codex，独立复现旧矩阵；新增 HD29.97 HEVC420 10bit 16M 的真实参数包证据，尚无硬件编码、成片与刷入验收。
- [2026-10-25 FX3 刷机失败案例与当前环境救援评估](<reports/索尼 FX3 刷机失败与救援研究.md>)：分阶段流程与三份官方原件核验完成；MSC只读快照已确认FX3 054C:0DA1及正常驱动绑定，尚未建立独立救援链或放行持久写入。
- [2026-10-24 FX3 HEVC 主录参数与局部写入研究](<reports/索尼 FX3 编码模式与写入研究.md>)：提取真实系统程序，确认 HD HEVC 主流参数与编码命令路由，审计服务加载、局部写入及恢复候选；未连接或刷写相机。
- [2026-10-24 Sony FX3、ZV-E1 与 REA 固件研究](<reports/索尼 FX3 ZVE1 固件研究.md>)：完成 FX3 7.02 官方包离线解密与目录校验；核对 HD HEVC 代理、现代 A7C II 补丁及跨刷证据边界，未连接或刷写相机。

## 项目与 GitHub 整理

- [2026-10-29 Orca 命名同步、旧工作树归档、设备/Git 巡检与 2T 外盘规则协调](reports/2026-10-29-orca-git-rules-organization/README.md)：重命名同步 69 个 Orca 工作区与 24 个聊天标签（不合规项清零）；归档退役 27 个已合并无聊天工作树及 1 个未入表目录（附 tar.gz、bundle、SHA-256 清单与同卷废纸篓原件）；巡检 406 个 Git 检出点与 2 台 iOS 模拟器，提交 7 处已完成交付并将 `Phayen` 主仓 138,241 个 `work/` 过程文件纳入 `.git/info/exclude`；同步 Codex、Claude、Antigravity（Gemini）全局规则与全部 20 个正式项目的 `README.md`/`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`。
- [2026-10-24 Orca 项目图标优化](reports/2026-10-24-orca-project-icons/README.md)：23 个项目、30 条关联登记统一使用项目图标，附预览、素材来源与回退记录。
- [2026-10-24 工作树、Git 与 skill 清理](reports/2026-10-24-worktree-skill-retirement/README.md)：退役 8 个已合并且无聊天/运行占用的工作树及旧本地分支，归档 54 份停用 skill 历史副本，处理两条失效 Git 登记；原件与恢复材料保留。
- [2026-10-23 整理回执](reports/2026-10-23-project-organization/README.md)：Git 链接修复、PR 分类、桌面截图归档与未完成事项。
- [项目与 PR 总览](outputs/project-workflow/project-overview.html) · [日常流程](docs/project-workflow.md) · [主入口与工作树工具](outputs/project-workflow/README.md)

## 日志与稳定性维护记录

- [2026-10-25 PosterBoard 反复弹窗修复](reports/2026-10-25-posterboard-fix/README.md)：修复唯一 iOS 模拟器内缺失描述标识的五条待机时钟配置，保留锁屏、应用和照片；附冷启动验证与回退原件。
- [2026-10-22 REA 与硬盘固件逆向调查](reports/2026-10-22-rea-drive/README.md)：实际检查 SANDISK 软件结构，发现桥接与 SSD 固件更新接口；后续官方实机页显示 3001 / Up to date。未刷写，掉盘根因仍待换线/换口对照。
- [2026-10-22 掉盘监测与固件后续](reports/2026-10-22-drive-local-followup/README.md)：补充 USB 会话重连观察和备份卷 UUID 校验；确认旧 Spotlight 异常对象已不存在，附具体 C to C 线材与官方/第三方固件适用边界。
- [2026-10-22 外置硬盘自动断开调查](reports/2026-10-22-external-drive-disconnect/README.md)：日志证实 07:11 USB 设备级断连；核对 SanDisk 同标识兼容记录、固件适用范围及换线/换口验证路径，根因与长期修复尚待验证。
- [2026-10-22 全面日志检查与修复](reports/2026-10-22-log-audit/README.md)：恢复 NAS 备份，修复 iCloud 备份脚本，完成真实备份和 358 个告警文件恢复校验；Spotlight 缓存告警及剩余系统/软件问题见报告。

## 空间维护记录

- [2026-10-27 内置盘占用盘点](reports/2026-10-27-internal-storage-breakdown/README.md)：只读拆解开发/模拟器约 159 GB、应用本体 61.6 GB、应用支持 55.5 GB 等；附 [可展开明细](outputs/internal-storage-20261027/index.html)。盘点中新增约 10.4 GB 安装包，收尾空闲约 24.8 GB。

- [2026-10-26 内置盘与剪辑缓存追加清理](reports/2026-10-26-internal-media-cache-cleanup/README.md)：内置盘实际净增 10.8 GB，可用 14.3 → 25.2 GB；清理 FCP、达芬奇衍生缓存及 30 个旧模拟器编译副本，另清外置 FCP 缓存约 9.35 GB。工程/素材/LUT 哈希与元数据核验保持，缺重建源的缓存保留。
- [2026-10-26 Mac 全面清理](reports/2026-10-26-mac-cleanup/README.md)：清除 975 项可重建缓存与重复更新副本（原分配空间 83.7 GB）；收尾时内置盘可用 15.1 GB、外置盘 284.8 GB，两卷较基线净增约 82.3 GB。22 个相关仓库状态不变，附保护核验、5 项跳过和访问限制。
- [2026-10-24 项目缓存继续收尾](reports/2026-10-24-project-cache-finalization/README.md)：逐文件确认 127 个 Cargo 解压目录与保留压缩包相同，另删 44 个旧编译对象/依赖图；追加约 80 MB，两个 Git 根状态不变。
- [2026-10-24 逐项目废弃文件与缓存复查](reports/2026-10-24-per-project-cleanup/README.md)：覆盖 20 个项目及 256 个关联入口，追加清理 14 项旧缓存约 868 MB；逐项目列明保留内容与误判复核。
- [2026-10-24 清理后的全面复核](reports/2026-10-24-final-cleanup-review/README.md)：追加清除 95 个旧编译/索引缓存（约 5.72 GB），复核 Git 登记、58 份在用技能与上一轮归档；附保留原因和访问限制。
- [2026-10-24 再次深度清理与卸载残留检查](reports/2026-10-24-deeper-cleanup/README.md)：追加删除约 9.7 GB（2606 项），包括 11 个空闲项目依赖、字节码缓存、Topaz 旧缓存及 5 项确认卸载残留；附 Git/锁文件核验、GitHub 规则来源、Pearcleaner 误报复核与访问限制。
- [2026-10-24 Mac 全面缓存清理](reports/2026-10-24-mac-cleanup/README.md)：删除约 75.1 GB 可重建缓存，实测两卷净增约 72.3 GB；内置盘可用 4.1 → 30.3 GB，外置盘 721.7 → 767.9 GB。24 个活动或近期变化目录跳过，附清单、保护核验和访问限制。
- [2026-10-22 二次深度检查](reports/2026-10-22-deep-storage-audit/README.md)：新增释放约 56.8 GB；附剩余可清理项目、45 组内容重复文件的核验清单及 NAS 备份可达性问题。
- [2026-10-22 全面空间清理](reports/2026-10-22-storage-cleanup/README.md)：清理经核验可重建的缓存，内置盘实际增加约 47.1 GB 可用空间，KAFU2T 增加约 58.3 GB；附删除清单、核验结果和权限限制。

## 已归类聊天

- [Mac｜缓存与卸载残留清理](codex://threads/019f3797-261f-7062-b703-fba87e932777)
- [文件整理｜恢复硬盘重复文件核对](codex://threads/019f545b-2684-7f43-a7e1-aaa2b84237ee)
- [Mac｜分辨率与显示器设置恢复](codex://threads/019f5a03-730a-7322-aecb-baa4b1308a9f)
- [Mac｜Minecraft 与后期软件缓存清理](codex://threads/019f8855-fc71-7223-97df-02f25b178f49)
- [Mac｜可重建缓存清理](codex://threads/019ff9ed-e200-79a2-9a35-6e14bd7d3555)
- [Mac｜平台崩溃原因排查](codex://threads/01a04296-b40d-78e0-908d-b7f4de29ab17)
- [Mac｜系统整理与性能优化](codex://threads/01a0526a-00ef-7d02-a903-dce838e22be9)
- [Codex｜缓存文件清理](codex://threads/01a075f5-d5c4-7fd2-8c7d-9cb986f5216f)
- [Mac｜美国加州地区设置](codex://threads/01a07a6b-7ffa-7aa1-9164-550191e60aaf)
- [Mac 清理工具｜产品设计与开发](codex://threads/01a07e56-3ce2-7270-b742-5928383af609)
- [Mac｜大写锁定键失效排查](codex://threads/01a08a8c-8cef-7530-82ff-b9870fbf5ffe)
- [Mac｜空间与可清理文件盘点](codex://threads/01a0aa5e-b236-7960-a669-8cc97bc3791a)
- [Mac｜无用后台进程清理](codex://threads/01a0cc9e-e95a-7e01-bdb2-a6d47223a97f)
- [Mac｜清理软件比较与推荐](codex://threads/01a0ecac-a9f7-7ca0-80a6-106fb49c00b1)
- [Mac｜存储整理与 Codex 迁移](codex://threads/01a0ecc8-c357-79b1-af9d-8d6fb0053cf8)
- [Agent 文件｜指令优化与 Mac 存储整理](codex://threads/01a0ed6f-7c25-7d53-b5e2-2c43dab70055)
- [Mac｜推文清理方案核查与实施](codex://threads/01a0efde-b028-7f13-ba50-7d1e7500f71d)
- [Mac｜网站语言识别与系统语言设置](codex://threads/01a0f32a-2361-7382-9279-94088dd72925)
- [Mac｜虚拟机清理与单实例保留](codex://threads/01a0f33f-8b7b-71a2-b121-c414c53e1b14)
- [Mac｜后台启动项检查与优化](codex://threads/01a10578-370a-7743-b89e-4ddefef7af30)
- [Agent 文件｜Claude 与 Codex 项目同步](codex://threads/01a11b44-bd2e-7983-8a25-c302e9476a12)
- [Agent 文件｜文件与聊天备份方案调研](codex://threads/01a11bce-7f3d-7073-a871-9457d82cfc8a)
- [Agent 文件｜工作文件迁移与存储清理](codex://threads/01a11bd8-9ccd-7d41-89b7-f45280bb1fe8)
- [Mac｜磁盘休眠设置排查](codex://threads/01a11c72-c54d-7320-b763-66179cd0246e)
- [Agent 文件｜备份目录删除可行性核查](codex://threads/01a1253b-93ed-7863-8597-33bd53d1db3d)
- [Agent 文件｜NAS 备份与目录整理](codex://threads/01a12747-d42a-7ad1-82c0-515287d30279)
- [Agent 文件｜项目、聊天与文件整理](codex://threads/01a14abe-631c-7833-96c3-b9328bd3fe68)
- [Codex｜侧栏整理与对话命名](codex://threads/01a1505b-f3af-7d53-a545-6fb86b2be228)
- [Mac｜系统报错弹窗排查与修复](codex://threads/01a15064-4f7f-7793-b494-d53eabfff8e4)

## 受来源访问检查限制的聊天

这些聊天仍保留在原处；通过索引进入。应用返回 confirmation_required 或无法安全确定来源，没有扩展项目访问范围。

- [Mac｜终端流量与系统更新检查](codex://threads/019fee7a-97ae-77d1-b237-b7e0b008d58a)
- [Mac｜缓存垃圾清理](codex://threads/01a1025c-35eb-7fa1-b313-da68d2583b13)
- [Mac｜有线网络 IPv6 关闭](codex://threads/01a11c13-bc6c-7591-8113-75cd19cbac6e)
- [Agent 文件｜Claude 导入 A](codex://threads/01a130ef-5d52-7d40-84b1-db34a498bc95)
- [Agent 文件｜Claude 导入 B](codex://threads/01a130ef-5d6f-70e2-a6c5-200733cafd48)

## 设置维护记录

- [2026-10-29 Orca Claude 账号与周额度排查](reports/2026-10-29-orca-claude-account-quota/README.md)：原生聊天仍绑定已用满的 Max 账号，状态栏显示另一个 Pro 账号（5 小时 0%、每周 35%）；已用官方实时额度和会话绑定交叉确认，未迁移或重启聊天。

- [2026-10-29 Orca Homelab 本地 main 更新修复](reports/2026-10-29-orca-homelab-main-refresh/README.md)：主克隆安全快进；6 份本地草稿原样保留到独立工作树，固件研究目录留在原处。

- [2026-10-22 Codex 语音入口恢复](reports/2026-10-22-codex-voice-fix/README.md)：修复默认 provider 被识别为自定义服务商导致的语音与听写入口隐藏，已完成窗口验证。

- [2026-10-23 Orca 设置优化与命名统一](reports/2026-10-23-orca-settings-naming/README.md)：核对 30 个项目入口与 75 个工作区，修改 13 个项目名、36 个工作区名和 35 个聊天标签；统一新分支与聊天模板，附设置前后值、命名规范和回退清单。

- [2026-10-19 ORCA 自动命名规则](reports/2026-10-19-orca-naming/receipt.json)：新聊天采用“项目名｜具体主题”，已通过设置界面保存并回读核验。

- [2026-10-19 ORCA 现有任务统一命名](reports/2026-10-19-orca-task-renaming/receipt.json)：36 个工作区及现有非空聊天统一为“项目名｜具体主题”，附前后清单和回读结果。

- [2026-10-20 ORCA 命名未联动诊断](reports/2026-10-20-orca-naming-diagnosis/receipt.json)：聊天规则仍有效；工作区使用独立的分支命名逻辑，当前标题已补齐，未来工作区自动命名尚未根治。

- [2026-10-20 ORCA 命名根因修复包](outputs/orca-naming-fix-20261020/README.md)：代码修复与 123 项测试完成；用户选择暂存，尚未安装，等待通知后重启验收。


2026-10-27：[FX5 与 VENICE 移植 FX3 复核](<reports/FX5 固件与 FX3 移植复核.md>)：公开整包、缓存/RAW、专业菜单与完整色彩链的证据和边界；未取得完整FX5固件，未刷写。

- [2026-10-28 FX3 VENICE色彩表与原生装载链逆向](work/fx3-color-port-20261027/README.md)：恢复真实矩阵、1D及20³网格，原指令查询/70项DMA列表与设置入口离线复现；菜单和实际录像分支继续追踪，未操作相机。

- [2026-10-28 FX3正常色彩参数链与选择适配原型V2](work/fx3-color-port-20261027/route-20261028/README.md)：应用到CP原参数、跨处理器67项载荷比较、异步回调及新增选择原型通过离线验证；EC为相机采集控制域，主录像素归属仍待追踪，无设备操作。


### FX3 色彩采集字段与 EC 模式复核（2026-10-28）

- [复现说明与消费者证据](work/fx3-color-port-20261027/consumer-20261028/README.md)：执行 19 项原 EC 模式表的 9,728 组转换及分派，复核类型条件；原 CP 注册检查没有枚举范围拒绝，但新增外观值 12 在两项监看色彩元数据中仍走默认分支。四个脚本通过，保留原型及旧封存材料；没有相机／USB／完整固件修改，也未证明 MAIN 像素应用。


### FX3 原 VFX SDK 与 CP 色彩 DMA 链复核（2026-10-28）

- [资源组合、原 SDK 与 70 项 DMA 描述复现](work/fx3-color-port-20261027/resource-20261028/README.md)：七种资源组合可经原 CP 控制器和 SDK 构造 ID 22 命令，原分派器展开七份 70 项列表；所有权、忙碌、准备记录和提交／回调错误路径通过离线检查。正常录像的主录／监看资源绑定仍未恢复，无真实 DMA、像素或相机操作。


### FX3 原配置生产与 VFX 所有权绑定（2026-10-28）

- [原同步参数、资源申请与同对象色彩提交](work/fx3-color-port-20261027/binding-20261028/README.md)：恢复 acquire ID 的原生产者、默认资源节点与 ImageParam 配置号生成；原分配器替代预填 ID，30 组配置生产接入原色彩命令构造，另验证占用与句柄代次。正常主录／监看参数含义和像素归属仍未确认；没有可刷入包或设备操作。


### FX3 可刷入条件与更新封包研究（2026-10-28）

- [官方更新环境、CBC 重编码及原校验器](work/fx3-color-port-20261027/package-20261028/README.md)：用户指定可刷入时停止，持续目标 active；拆读 65 项更新环境和 11 库，六个孤立块重建原密文，17 组原 AP 校验器实验通过。尾部验证、完整准入及启动仍未恢复，无完整修改包或设备操作。


### FX3 原始过渡固件与 WBI 保护函数恢复（2026-10-28）

- [2.04／2.05 原件提取、页表与 SKD 静态恢复](work/fx3-color-port-20261027/tail-20261028/README.md)：独立 LZX 提取三份原成员，旧固件稀疏枚举及 13 处明文对照通过；从原 WBI 页表核对恢复六个 SKD 函数，验证 129 个加载器模块记录。15 组具体 RSA 尾部探测未匹配；实际输入校验、完整色彩链和可刷入包仍未完成，目标 active，无设备操作。


### FX3 SD 更新入口与官方尾签名（2026-10-28）

- [原更新引擎拆读及 RSA-2048／SHA-256 验证](work/fx3-color-port-20261027/input-20261028/README.md)：两份 19 MB 原更新分区通过 CRC32，初始化文件系统各 342 项／216 普通文件；取得真实 sdfileinput、接口库和官方公钥。三份原包验签确认覆盖完整密文＋IV，12 个改动样本不再匹配；宿主 OpenSSL 独立复核边界。完整移植及有效修改包仍未完成，目标 active，无设备操作。

### VENICE 原 ART 参数与 FX3 系数兼容性（2026-10-29）

- [原矩阵量化、分派与 type4 尾部研究](work/fx3-color-port-20261027/donor-20261028/README.md)：138 组矩阵、72 组分派和三组字节序检查通过，既有 FX3 VENICE 矩阵的九个系数字节匹配；三版内层新增统一尾长关系，尚未解密或完成完整色彩链／可刷入包。旧 2213 项封存核验不变，无设备操作，目标 active。

### FX3 历史 USB／文件输入验签（2026-10-29）

- [原 UFP／UUD 调用与依赖图](work/fx3-color-port-20261027/transport-20261029/README.md)：核对两版一致的四份原库，USB／UUD 写入处理也调用 SHA-256／RSA 尾签名验证，构造与等待虚槽已定位；CRC 文件 API 未证明可从所查入口到达。历史程序不是当前 7.02 机身读回，无设备动作或可刷入包，目标 active。

### FX3 当前 AP 旧文件更新链（2026-10-29）

- [原 crypter 调用者、格式和动态库加载条件](work/fx3-color-port-20261027/ap-input-20261029/README.md)：7.02 AP 全部 797 普通文件／532 ELF 定位 crypter 与模块登记；孤立旧格式重编码及八组原头部检查通过。候选链仍缺正常入口准入与实际加载证据，WBI 对应代码页不可读；无完整修改包或设备动作，目标 active。

### FX3 原应用更新入口与旧上传边界（2026-10-29）

- [原入口分派、镜头暂存限制和外部命令链](work/fx3-color-port-20261027/entry-20261029/README.md)：13 组有界原指令检查通过；机身更新请求与旧解包路径已区分，官方整包在镜头 helper 的 2 MiB 限制前被拒。追到原 USB 外部命令服务及驱动，尚无完整容器准入或可刷入修改包；无设备动作。

### FX3 旧加载链镜像选择条件（2026-10-29）

- [原镜像组装、预置镜像和运行标志分支](work/fx3-color-port-20261027/body-load-20261029/README.md)：原函数恢复 1,253,376 字节镜像并与独立提取、AP 预置镜像哈希匹配；两个原分支确认 IAMUPDATER 标志不存在时选择预置 udtrbody。真实运行标志、完整输入准入及加载仍未验证，无设备动作或可刷入修改包。

### FX3 旧更新库的输入文件与可选配置（2026-10-29）

- [原 TAR 解析、文本提取与配置虚槽](work/fx3-color-port-20261027/marker-20261029/README.md)：21 组有界原指令检查和 25 个原片段复核；原函数能提取无执行权限文本并在缺正文时失败，uconfig 加载槽已确认。WBI 缓存不充实时标志，完整 XML／正常准入及可刷入包仍未证，无设备操作。

### FX3 原 XML 读取、配置回调与插件分派（2026-10-29）

- [原 XML 到系统请求的局部链](work/fx3-color-port-20261027/xml-20261029/README.md)：当前 AP XML 原库已提取，10 组有界 guest、87 个原函数体和 23 个片段核对；有效补充配置经原收尾回调可生成调用请求，缺失跳过、损坏抛出原异常。均停在系统调用前，完整外部准入及可刷入色彩替换包仍未证，无设备操作。

### FX3 原 TAR 控制器时序与 crypter 模式（2026-10-29）

- [连续内存输入到原配置回调](work/fx3-color-port-20261027/controller-20261029/README.md)：8 组有界检查、135 个原函数体和 20 个片段复核；新编号组触发补充配置，同组文件不追溯触发。原 UFP 参数夹具经原 main 传入模式 0；启动脚本成功为显式替身，完整外部准入及可刷入色彩包仍未证，无设备操作。

### FX3 完整旧格式内存流与镜头类别门槛（2026-10-29）

- [1,235 块原解密消费与原 LENSDATA 预处理](work/fx3-color-port-20261027/legacy-stream-20261029/README.md)：9 组检查通过预期；完整内存流还原原镜像并继续到配置请求，提前结束可留尾随块。保留 FX3 机型字段时镜头入口在 IPC 前拒绝；合成类别变体停在 OSAL 请求，无回复伪造、固件文件或设备操作，未达可刷入条件。

### FX3 原 AP／CP 镜头状态与版本检查（2026-10-29）

- [原 CP 接收器与 AP 请求回复桥接](work/fx3-color-port-20261027/lens-state-20261029/README.md)：19 组检查；定位原 Lens FirmUpdate 处理器，原 CP 生成回复后由原 AP 比较机型／地区／版本，特定合成状态可触发原版本跳过标志。全部为内存通道与合成物理状态，匹配时停在下一项机身服务，未真实 IPC、刷写或取得可刷入包。

### FX3 原 UPM 电源状态与镜头准备门槛（2026-10-29）

- [原 AP／CP／UPM 三端代码与电源分支](work/fx3-color-port-20261027/body-state-20261029/README.md)：11 组离线检查；定位原内核服务接收器、电源读取回调及枚举诊断。合成镜头身份和 ACV／插口正常缓存使原准备函数返回 0，电池分支停在备份读取前。没有真实服务、内核装载、设备操作或可刷入修改包，完整色彩移植仍未完成。

### FX3 原处理阶段参数到色彩资源的生产链（2026-10-29）

- [原 GetInfo 记录、参数复制与向量构造](work/fx3-color-port-20261027/scene-binding-20261029/README.md)：7 组离线检查；补上两个资源配置输入字段的原生产关系，一组由原调用片段提供回调和参数，四组进入既有色彩 SDK、两组不申请 VFX。正常主录像素归属、完整供体和可刷入包仍未证；无设备操作。

### FX3 原色彩调用资源门槛与回调登记（2026-10-29）

- [原 71 项资源检查、状态清零和 MLUT 回调记录](work/fx3-color-port-20261027/frame-route-20261029/README.md)：11 组有界检查；补查原色彩调用前置条件，复现失败后跳过、原同步清零和回调记录构造。去掉 STP 成功替身后停在原分配器入口；实际队列、缓冲、MAIN 像素及可刷入包仍未证，无设备操作。

### FX3 原 STP 所有权与图像查询参数（2026-10-29）

- [原分配到固定地址读前、参数生产到查询入口](work/fx3-color-port-20261027/stp-buffer-20261029/README.md)：8 组有界检查，含 65,536 个模式输入的单项穷举，纠正类型 2 的错误预期。原 STP 写入 guest 句柄后停在 0xf5410828 读取前；独立缓冲试验停在原图像查询前，无寄存器值或查询回复伪造、设备操作或可刷入包。

- [2026-10-29 FX3 原图像记录表与描述符生命周期](<work/fx3-color-port-20261027/image-lifecycle-20261029/README.md>)：13 组原指令验证确认 240 条初始化、帧标记清理和描述符交接；修正“帧查询”解释，新资源仍停未回复句柄入口，未证真实像素/完整供体/可刷包，无设备操作。

- [2026-10-29 FX3 原输出控制器与 NRV 申请](<work/fx3-color-port-20261027/controller-route-20261029/README.md>)：12 组有界验证，补上原全局指针、控制器表登记/查找及 EE/SplitEE 类型检查前边界；正常 kind3 首个缓冲申请键 0x4af，仍停未回复句柄操作，未构造真实控制器、未证 MAIN/完整供体/可刷包，无设备动作。

- [2026-10-29 FX3 原动态 ID 与消息申请前缀](<work/fx3-color-port-20261027/dynamic-id-20261029/README.md>)：8 组原指令验证，识别 osal_dynamic_id 并执行原软件块池/位图分配；严格路径停 MPIDR 读前，带明确环境适配的 NRV 路径推进到 QID 0x61003c 的 216B 消息缓冲申请前，未发消息、未证像素/可刷包，无设备操作。

- [2026-10-29 FX3 原 DMM 申请报文与提交前边界](<work/fx3-color-port-20261027/dmm-request-20261029/README.md>)：7 组有界验证，原 512KiB 软件池和消息分配构造 0x4af 申请的 14 字节核心字段，停服务提交前；回复仅静态检查，接收端/真实图像缓冲/MAIN/完整供体及可刷包未证，无设备动作。

- [2026-10-29 FX3 DMM 接收端与完整目标复核](<work/fx3-color-port-20261027/dmm-service-20261029/README.md>)：原队列注册／独立回调前缀和0x20静态分派已证，4组有界案例；正常提交停在线程身份查询前。官方FX5两入口无更新信息，完整供体／MAIN／整包准入仍缺，无设备动作。

- [2026-10-29 FX3 原 CP DMM 配置与 NRV 单位](<work/fx3-color-port-20261027/dmm-config-20261029/README.md>)：原解析器消费完整43320B，165组头／1052记录／348单位与独立参照一致；0x4af对应0x62a两条配置记录。正常CP装载、真实缓冲／MAIN及可刷包未证，无设备动作。

- [2026-10-29 FX3 DMM 默认备份参数与原换算](<work/fx3-color-port-20261027/dmm-backup-20261029/README.md>)：22模板／44段校验通过，原查询从第二段导出配置源候选0x09a08e00；4组严格／适配前缀停在锁或映射边界，无文件读取适配器。正常装载／真实缓冲及可刷包仍缺，无设备动作。

- [2026-10-29 第一代 VENICE V6.30 供体解包](<work/fx3-color-port-20261027/donor-venice1-20261029/README.md>)：新取官方188874442B包并验ZIP／MD5，tar外层完整提取；内层type3仍未解开。两份GPL内核和四个接口仅源码证据，未恢复完整ISP或可刷包，无设备动作。

- [2026-10-29 VENICE V2.01 旧供体与封装反例](<work/fx3-color-port-20261027/donor-loader-20261029/README.md>)：档案页恢复官方地址，新取170041914B原ZIP并解外层；type3仍未解，V2.01反驳8字节关系通用化。FX3四文件系统866普通文件补查，未产出完整ISP／可刷包，无设备动作。

- [2026-10-29 专业更新组件与 VENICE 格式边界](<work/fx3-color-port-20261027/loader-host-20261029/README.md>)：实际解开官方SNC安装包，取得26组件及升级DLL；25字节原x86头检查9例通过预期，五份VENICE负载在该SVU分支拒绝。未恢复type3／完整ISP或可刷包，无设备动作。

- [2026-10-29 FX3原CP启动描述块与页表生产链](<work/fx3-color-port-20261027/cp-bootstrap-20261029/README.md>)：取得原380B配置；明确标志0的RAM片段由原指令生成4096项L1及6144B L2，原属性／指针三组查询成立。真实启动、完整MMU、配置装入／像素／可刷包仍未证，无设备动作。

- [2026-10-29 FX3原区域重建与未缓存配置链](<work/fx3-color-port-20261027/mmu-software-init-20261029/README.md>)：原软件初始化清除中间候选映射，19项原区域表／15次映射再建缓存属性；原memcfg解析请求0x20，严格路径仍缺缓存几何。明确关闭CPU维护的独立RAM投影才通过指针门，无配置内容／像素／可刷包，无设备动作。

- [2026-10-29 FX3原CP配置装载描述与NOR消费入口](<work/fx3-color-port-20261027/config-producer-20261029/README.md>)：22模板的FA0080表指定分区8的DmmCfg.bin及原地址／容量；原NOR两次读取9216B一致，消费到FAT挂载／打开边界，三文件与CP地址表对应。正常记录选择、实际读取／像素／可刷包仍未证，无设备动作。

- [2026-10-29 FX3原备份选择与NOR文件入口固定失败](<work/fx3-color-port-20261027/nor-backup-selection-20261029/README.md>)：44原模板头与选择模式分开；原RAM复用片段写状态3并复制9216B装载表。原文件打开118条指令的普通返回均-408，三组原执行一致；转查Cetus交接，完成标志／配置内容／可刷包未证，无设备动作。

- [2026-10-29 FX3 Cetus发送端范围与原NOR块读边界](<work/fx3-color-port-20261027/cetus-sender-20261029/README.md>)：857普通文件／565 A64 ELF及原始映像的限定搜索未定位发送者；区分提示音DMM／共存同名。原CPAPP-B两块加载入口停在引导表，底层四组边界区分零长0与有效请求未知，无配置数据／像素／可刷包，无设备动作。

- [2026-10-29 FX3 EXBL引导信息与MIS原读取格式](<work/fx3-color-port-20261027/boot-info-source-20261029/README.md>)：完整FDAT唯一明文EXBL证实为原比较字符串；原NOR确认MIS三项参数表，两组前缀区分缺失引导表与独立头识别。未取得真实信息块／DDR初始化／ISP或可刷包，无设备动作。

- [2026-10-29 FX3 DGU参数解释与串口硬件边界](<work/fx3-color-port-20261027/dgu-mis-consumer-20261029/README.md>)：5654条连续格式记录／18种原分派，六组原前缀区分缺失NOR上下文与串口相关硬件写点；DDR/Nanya注释不充实装芯片证明，未初始化DDR／恢复RAW或可刷包，无设备动作。

- [2026-10-29 FX3完整移植目标准入审计](<work/fx3-color-port-20261027/full-goal-readiness-20261029/README.md>)：三主仓库固定提交／各地区供体复查，三原包SHA与签名证据一致；未新增完整私有ISP或7.02修改整包准入方法。按首次无目标关键进展记录，目标active，未刷写。

- [2026-10-29 FX3完整移植条件第二次复核](<work/fx3-color-port-20261027/full-goal-recheck02-20261029/README.md>)：三公开主仓库及VENICE研究分支未变；阶段200及恢复0.4仍不构成AP独立恢复或可刷固件。供体／准入同一缺口第二次无关键进展，目标active，无设备动作。

- [2026-10-29 FX3完整移植目标受阻审计](<work/fx3-color-port-20261027/full-goal-blocked-audit-20261029/README.md>)：已审A6000新R9/R10与FX3阶段201，均未补齐完整私有ISP、7.02修改包准入或独立恢复。同一缺口连续三轮，无有效目标实施下一步；目标已回读blocked、未完成，无刷写。

- [2026-10-30 FX3 CP标志的AP发送端对照](<work/fx3-color-port-20261027/AP-CP-handoff-reference-20261030/README.md>)：公开AP原件两标志／地址与FX3 CP消费者匹配；两原行对照确认DmmCfg类别5跳过该普通转发片段、tomco类别7到查询边界。真实配置／RAW／可刷包仍未证，恢复后新进展，目标active，无设备动作。

- [2026-10-30 CP类别5配置的escape装载候选](<work/fx3-color-port-20261027/CP-escape-config-20261030/README.md>)：原参考分支选中DmmCfg类别5，默认参数投影到0x4132d8e00；六独立片段不充完整装载，CPIR500记录全量边界已核。p8只见9类5路径中4项，真实记录／源指针／RAW及可刷包未证，无设备动作。

- [2026-10-30 AP暂存源与AP／CP记录切换](<work/fx3-color-port-20261027/AP-staging-record-routing-20261030/README.md>)：原参考切CP记录后恢复AP，+0x38与escape装入同源FA019A；14原叶调用／26指令核对及9默认区域地址往返通过。全1值检查反例与DmmCfg槽尾未知保留；非FX3当前AP、非完整启动／RAW／可刷包，无设备动作，目标active。

- [2026-10-30 Escape原文件读取与槽位尾部](<work/fx3-color-port-20261027/escape-file-read-contract-20261030/README.md>)：8原FAT查询分支／22+7指令核对，DmmCfg请求84扇区加尾扇区、独立原复制只写312B，59080B槽尾哨兵保留。短读与文件错误处理限制、4562992B区域空洞及p3同名源已区分；整体初始化／目标AP／RAW／可刷包未证，无设备动作，目标active。

- [2026-10-30 WBI零填充分派与暂存区范围](<work/fx3-color-port-20261027/WBI-zero-staging-20261030/README.md>)：原64B记录到AP flag分派已绑，两原前缀停在诊断、独立后段停DMA初始化前；16原指令／1399记录与旧图核对通过。全部记录及82零填充均不覆盖三处默认AP暂存投影，该补零候选不能补齐源内容；目标AP／RAW／私有ISP及可刷包仍未证，无设备动作，目标active。

- [2026-10-30 完整移植准入复核01](<work/fx3-color-port-20261027/full-goal-refresh01-20261030/README.md>)：官方FX5／VENICE来源与4仓库重核；新Rust工具固定0f03359源码、6旧平台／121机型及guard路径未补FX3修改包准入。3原包SHA／8历史成员一致，VENICE合包仍392/410/500；225仍静态与自写模型。缺完整私有供体／目标AP／准入同一条件首次无完整目标进展，active、未完成，无设备动作。

- [2026-10-30 完整移植条件复核02](<work/fx3-color-port-20261027/full-goal-refresh02-20261030/README.md>)：4公开HEAD未变；新226仍自写ARM64／假Linux，未提供目标AP或实机恢复。FX5 RAW PR仅3行无样本占位，ARW6文件解码线索未补完整ISP／准入；前轮34封存复核，同一关键缺口连续2轮，active、未完成，无设备动作。

- [2026-10-30 完整移植目标受阻审计](<work/fx3-color-port-20261027/full-goal-blocked-audit-20261030/README.md>)：两前轮43封存及当前四HEAD／官方供体页／226报告已核；同一完整私有供体、目标AP与修改包准入／恢复缺口连续3轮。原生目标已回读blocked、未完成，原完整目标及历史保留，无修改包或设备／刷写动作；需可核验新输入解除。

- [2026-10-30 Sony公开固件目录与FX5供体查询](<work/fx3-color-port-20261027/Creators-public-catalog-20261030/README.md>)：12次匿名元数据请求及正对照验证，FX3 7.02/953与α7 IV 6.02/963成功，FX5/FX5B仍为空版本/ID和0字节；取得原厂下载URL并仅核对FX3前64字节，未取得完整私有供体或修改包准入，未达可刷入门槛，无设备动作。

- [2026-10-30 FX5与FX3的DMA地址及缓存协议](<work/fx3-color-port-20261027/FX5-memory-consumer-20261030/README.md>)：成对核对44份公开源码、20个原默认AP/CP范围和9个边界输入；UDIF参数头相同，但DMA32的DDR/ESRAM规则与SG缓存交接时序不同。未绑定实际7.02模块、未取得私有ISP或可刷包，无设备/cache/TLB操作。

- [2026-10-30 FX3原包DMA与缓存接口绑定](<work/fx3-color-port-20261027/FX3-runtime-DMA-binding-20261030/README.md>)：15原内核范围/10独立导出，565 ELF中22模块及1未解析共享库的217重定位；12有界案例/158原指令，5转换返回、4诊断调用前停、3缓存DC前停。DMM日志不充RAW像素，未证机身加载/完整ISP/修改包准入，无设备或缓存操作。

- [2026-10-30 Sony专业目录与FX5注册路径复查](<work/fx3-color-port-20261027/Pro-catalog-sources-20261030/README.md>)：12个匿名JSON请求验证中国目录，FX5/FX5B已登记但四次固件查询为空；FX6 6.01/FX3 7.02/VENICE2 5.00正对照成功。旧组合包仅目录及AXS头片段，ETag/412保留，已核解析器头条件不匹配；无完整私有供体或可刷包，无设备动作。

- [2026-10-30 FX3历史SD输入长度与验签数据对应](<work/fx3-color-port-20261027/SD-frame-admission-20261030/README.md>)：51原函数/29指令/9虚表及三包原区间核对；正常缓冲区合同不支持4GiB长度截断，同一ring静态连接验签与解密。明确2.04/2.05引擎不充当前7.02机身，短读/过短输入未证可利用；九项整体验收保留，无修改包、执行或刷写。

- [2026-10-30 AXS-R7完整原件与前部线性模型](<work/fx3-color-port-20261027/AXS-R7-donor-loader-20261030/README.md>)：官方6.00完整成员、6.01完整ZIP已核CRC/MD5；两版76+1024+主体+16结构相符，12段16阶模型/694留出位吻合，仅恢复1KiB候选头。主体和VENICE读取器仍缺，未套用type3、未试主体密码或生成修改包；九项整体验收保留，无设备/刷写。

- [2026-10-30 AXSM原始固件读取器与格式边界](<work/fx3-color-port-20261027/AXSM-host-reader-20261030/README.md>)：官方3.5.0安装包只读拆出6组件/439普通文件，75项XAR校验；5完整ARM64函数/5928B已绑，10原前缀/70指令验证UPDATE头判定，7对照匹配而2版R7及VENICE type3拒绝。仅排除该读取分支，目标内层和整包准入仍缺；无安装/设备/刷写，九项门槛保留。

- [2026-10-30 完整移植目标阻塞复核01](<work/fx3-color-port-20261027/full-goal-impasse01-20261030/README.md>)：508封存文件核回，3公开HEAD未变；最新231仅离线模型且不可部署，232核查时无终验回执。有限种子关系未形成新解码，完整私有供体/适用读取器与FX3准入启动恢复仍缺；本轮按无推进计1，保持active、不复用旧blocked计数，无设备/刷写。

- [2026-10-30 完整移植目标阻塞复核02](<work/fx3-color-port-20261027/full-goal-impasse02-20261030/README.md>)：前轮9文件核回，同一缺口未变；231仍不可部署/未实机恢复，232无终验回执。未重复下载、查询或研究测试，本轮无推进计2，目标active；完整九项要求保留，无设备/刷写。

- [2026-10-30 完整移植目标阻塞复核03与blocked状态](<work/fx3-color-port-20261027/full-goal-impasse03-20261030/README.md>)：第三轮同一条件无推进，唯一有界CBC布局未得到已验证主体；新232回执仍不可部署/未实机恢复。完整九项未完成，原生目标已设置并回读blocked；完整供体/适用读取器或经典FX3准入恢复新证据可触发恢复，保留原件/原目标，无设备/刷写。

- [2026-10-30 Mac 存储核查与清理](reports/2026-10-30-storage-cleanup/README.md)：pip 缓存清理及系统安装空间核查；大型保留资料未动，安装成功尚未验证。

- [2026-10-31 VENICE 色彩链与 Phayen 指定会话交接](reports/2026-10-31-venice-phayen-color-chain/README.md)：汇总 FX3 原生 VENICE/ACES 9系数、512槽1D、20³表和控制证据；八份核心原件封存匹配，明确私有ISP前段与像素连接缺口。指定会话消息已入队，未确认已读；未修改产品或操作设备。
