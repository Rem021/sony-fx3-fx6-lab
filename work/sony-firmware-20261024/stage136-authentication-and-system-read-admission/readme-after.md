# Mac

2026-10-27：[开发环境与内盘实验资料整理](reports/2026-10-27-vm-experiment-consolidation/README.md) · [共用设备与资料存放规则](docs/shared-development-storage.md)。六份实验快照已迁移，下一批严格通过子目录待协调窗口；未通过原生等价的原件按用户选择保留。

Mac 系统优化、缓存清理、文件与 Agent 项目整理。

Codex 与 Orca 文件夹入口均已创建并固定。历史任务目录保留原位。

## 相机与固件研究

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

- [2026-10-22 Codex 语音入口恢复](reports/2026-10-22-codex-voice-fix/README.md)：修复默认 provider 被识别为自定义服务商导致的语音与听写入口隐藏，已完成窗口验证。

- [2026-10-23 Orca 设置优化与命名统一](reports/2026-10-23-orca-settings-naming/README.md)：核对 30 个项目入口与 75 个工作区，修改 13 个项目名、36 个工作区名和 35 个聊天标签；统一新分支与聊天模板，附设置前后值、命名规范和回退清单。

- [2026-10-19 ORCA 自动命名规则](reports/2026-10-19-orca-naming/receipt.json)：新聊天采用“项目名｜具体主题”，已通过设置界面保存并回读核验。

- [2026-10-19 ORCA 现有任务统一命名](reports/2026-10-19-orca-task-renaming/receipt.json)：36 个工作区及现有非空聊天统一为“项目名｜具体主题”，附前后清单和回读结果。

- [2026-10-20 ORCA 命名未联动诊断](reports/2026-10-20-orca-naming-diagnosis/receipt.json)：聊天规则仍有效；工作区使用独立的分支命名逻辑，当前标题已补齐，未来工作区自动命名尚未根治。

- [2026-10-20 ORCA 命名根因修复包](outputs/orca-naming-fix-20261020/README.md)：代码修复与 123 项测试完成；用户选择暂存，尚未安装，等待通知后重启验收。
