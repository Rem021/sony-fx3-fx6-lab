当前状态：[TRY2 本机试用说明](../../outputs/fx3-vm-trial/TRY2-使用说明.md)和[交付回执](../../work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/RESULT.md)记录 English 固定副本、图标与橙色焦点的有界浏览器验收；独立标准 Ctrl-C 网页轮仍待验。历史 [AP104 轻量首错](ap104-passive-completion-trace.md)、[AP105 性能候选](ap105-offline-preparation.md)与[TRY2 方案](try2-ldec-performance-plan.md)保留；全部34步的旧截图路径、描述和理由见[画面记录](ap104-visual-step-log.md)。

AP103回执：[AP103软件LDEC与菜单资源恢复](ap103-software-ldec-and-native-save.md)：真实ioctl三个样例逐字节一致，原菜单高亮/图标/面板恢复；四轮均未完成600秒，最新阻塞为GPE完成队列unfetched，且该轮API还原读回未通过。首选仍AP101-r4；日期与普通设置保存未验收。

收尾缺口已单独修复：[API16等待确认](ap103-api16-acknowledged-cleanup.md)，宿主回归与两轮零按键短guest通过，其中受控延迟6.66秒完成；旧第四轮失败回执保留。

保存诊断：[AP102空闲局部保存观测](ap102-idle-save-observation.md)。本机试用工具：[TRY1](try1-local-ui-trial.md)，保留已冻结基线。

历史回执：[AP84三轮通过，四种配置均UI2/黑清屏，待OSD完成链合同](ap84-cpu-speed-clock.md)。

- [AP89 RAM重启与首屏](ap89-backup-replay-first-screen.md)：输入双SHA一致，原UUD返回0、mode1/option0，fa/2c7对象创建；77条GPE中3 Fill成功、73 Blit与1 Flush拒绝，315次物理读回均匀黑，无菜单像素。

- [AP88 CP Backup reset与原关机链](ap88-cp-backup-reset-shutdown.md)：两次原reset消费返回0，317+2项逐项默认值复核、UUD4/4和保存RAM哈希闭合；原关机后段另有28B0119断言未修复，正做已授权AP89 RAM重启验证。

历史回执：[AP84四核/原厂cpuset已通过，icount对照进行中](ap84-cpu-speed-clock.md)。UI仍2次更新/黑清屏，待OSD完成链审计。

历史回执：[AP83 DMM真实复制与GPE集成，最新AP83b健康=True](ap83-face-dmm-realcopy-gpe14.md)。菜单未验收。

历史回执：[AP83 DMM真实复制与GPE集成，最新AP83ar4健康=True](ap83-face-dmm-realcopy-gpe14.md)。菜单未验收。

历史回执：[AP83人脸DMM首轮失败，修正被动捕获后重跑](ap83-face-dmm-realcopy-gpe14.md)。健康基线仍为AP81，菜单未验收。

历史回执：[AP82第二拓扑/UUD路径已证实，后续DMM1d9 assert失败](ap82-uud-second-pin-dmm-1d9.md)。已停机；健康清屏基线仍为AP81，菜单未验收。

历史回执：[AP81 SKD不可用降级后UI恢复/首清屏](ap81-skd-unavailable-ui-clear.md)。健康运行通过，已有均匀逻辑PNG，菜单内容仍未验收；AP80c失败现场保留。

历史回执：AP80c原启动链/notify已证实，但SKD外部总线异常失败，已停机；[详见AP80](ap80-owned-pin-and-deferred.md)。

历史阶段：[AP80 软件图/尾段](ap80-owned-pin-and-deferred.md)。AP80a原四任务屏障已越过；菜单与PNG尚未验收。

# FX3 虚拟机续接修复回执

> 当前检查点：AP79 已消费 VDF/HDMI 八条新增回复和325，四任务自然完成；父线程仍在屏障前的 Dataflow getpin 等待，UI/首绘未通过。见 [AP79报告](ap79-boot-vdf-hdmi-tail.md) 与 [STATE](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)。


最新：[AP70亮度与OSD软件接受](ap70-lcd-osd.md)：0x111a消费释放0，0x159静默接受，TID334继续到BACK_LIGHT_MODE及无等待0429/0500；ADF032e/033d仍为最后观测等待点，无菜单/硬件验收。

此前：[清屏与后续启动协议解析](uniform-surface.md)：监看LUT mode0回复已消费/释放；空闲软件后端完成7次释放限制开关，当前等待音量设置及系统提示音缓冲区地址。仍无可用菜单；AP60清屏和CEC/时间码的既有回执保留。

此前：[图层配置、锁等待与首组绘图请求](plane-and-lock.md)：0147回复已被原应用消费；修正模拟层自旋锁等待，首次捕获GPE fill/flush但未写像素，仍无可用原菜单。

此前：[HDMI配置、远端DMM和显示查询](audio-display-dmm.md)：五次新原生运行；原音频/预设、两槽DMM和显示查询已越过，当前等待014c布局等；仍无原UI。

此前：[CAPID共享表与地址转换](capid-and-address.md)：原CAPID初始化和一条SA转换已通过，下一处为VDF032d；原UI仍未运行。

此前：[蓝牙空记录与原生模块启动](bt-records-and-native-owners.md)：蓝牙原初始化、BusPower与Kikilog已越过，当前等待CAPID共享表；无原UI。

此前：[应用初始化、HDMI注册与蓝牙故障前移](app-hdmi-bluetooth.md)：原HDMI注册回复已被消费/释放；GPIO5原写入通过，当前最早失败为蓝牙配置读取，尚无UI。此前：[UPM原生回复与FX3日期初始化](scu-date.md)：受限SCU配置下原UPM已接通，原时区日期初始化/推进通过；appFw休眠78线程、无绘图请求。[GPE上一轮回执](gpe-boot.md)、[计时器/DMM回执](timer-dmm.md)保留；以下为AP11–15历史。

已恢复原交接上下文并继续五次真实本机 QEMU 运行。尚未正常运行菜单：最新原 im 有23线程、libMWF 已映射，但三次采样均为 T(stopped)，pending signal19，appFw 未映射，无原厂 UI 帧。

## 核验边界

外盘卷 UUID 已核对。Mac 目录不是 Git 仓库；本任务沿用现有 work 真实目录。原 Orca 会话和交接快照只读，未恢复、发消息或修改。启动前无遗留 QEMU。原内核、冻结 runtime 和原厂资源保留；新运行无 NIC、USB 或主机磁盘透传。

## 实际修复与观测

|候选|变更|实测结果|
|---|---|---|
|AP11|按上游十项名单清 IMDB mask低3bit；用FX3自己表项地址。派生库在 /simulation，原 /usr/lib/libIMDB.so 保留|越过AP10 usb_beets内核异常；原grm_init扫描/proc/modules找不到grm_ma后abort|
|AP12|仅增加同机原 grm_ma.ko 启动和RC门槛|insmod RC0，越过grm_init abort；原ResourceBluetooth+1454的c0104702 ioctl触发内核DABT|
|AP13|另加明确的FX3专属ResourceBluetooth硬件资源过滤|未见异常监视器；im23线程/libMWF映射；三次采样均stopped，未进入appFw|
|AP14|透明kill/raise/pthread_kill观察，仍调用原实现|停态复现，无命名观察事件；不证明没有内部或raw syscall信号|
|AP15|另观察abort/__assert_fail，原样委派|停态复现，无命名观察事件；没有强行CONT或抑制失败|

上游十项策略来自维护者固定提交 [prepare-assets.py](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/prepare-assets.py)。本轮重新联网核对了 [启动内存脚本](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-kernel-probe.sh)。蓝牙第11项是本机FX3差异，不冒充上游策略。

## 复核材料

- [五次原始运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/resumed-run-summary.json)：各run有不可覆盖的serial、QMP journal和receipt。五次host退出0、reaped、input SHA不变、observer无错误；这不是guest正常关机或菜单验收。
- [原库故障绑定](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap11-ap12-fault-proof.json)与[可复跑只读审计](../../work/fx3-vm-20261101/menu-repair-01/runtime/audit_ap11_ap12.py)：保留原指令字节、PLT名、原件SHA和实际地址差。
- [AP15历史候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap15-abort/candidate15.json)及[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)。构建脚本与派生mask回执在相应候选目录，原ELF及CPIO父目录顺序检查通过，guest loader verify/list/true门槛通过。

首次AP11构建因基线成员用data而不是file存储失败；第二次因直接替换原IMDB触发原ELF身份门槛失败。均未启动guest，失败目录保留。最终改为保留原件、显式simulation派生库并实际映射验证，未放宽审计。

## 后续边界

下一步先只读采集停止线程的syscall/stack及信号来源，解释SIGSTOP后再改变行为。LIRO仍有dmm_direct_call、dma330_mem_transfer_async、pciatu_map/unmap、interchip_transfer_async五项未解析；utimer/stream/DMM/upm/udate等与上游启动顺序尚未齐全。大initrd高地址放置仍未实施；AP10已经进入原AP，已核首个异常是USB，不能把它解释为initrd冲突。

原UI、按键到新帧、分钟级运行与guest正常退出验收均未完成。没有设备操作、固件刷写、假菜单或伪造ACK。

## AP71–AP73 运行链复核

- [AP70致命符号错误更正与原LCD结果](ap70-lcd-osd.md)
- [AP71原厂iCrypt可见性恢复](ap71-icrypt-load.md)：Has*原厂返回0，末次快照im存活。
- [AP72静音地址模型](ap72-adf-muted.md)：032e/033d消费释放0；0327后续等待，四任务屏障仍未通过。
- [AP73 GPE v13](ap73-gpe-v13.md)：绑定与宿主测试通过，80/240秒无guest绘制命令，动态绘制/读回验收保持开放。

- [AP74 提示音注册](ap74-beep-registration.md)：前9轮18包free0，后文件分支unit70817返回-3并assert；guest业务失败，等待完整文件/DMM合同。

- [AP75 timer/首次绘制观测](ap75-timer-observation.md)：固定候选两轮240秒，关键时刻跳转完整，timer/指定配置/Fill入口均0；上游调用原因与修正未证实。

- [AP76 文件/DMM/用户态ICDT](ap76-adf-file-icdt.md)：最终v30全26包free0、四次完成消费，无abort；四任务屏障仍未证实，GPE/菜单未验收。

- [AP77 UI门控与四任务观测](ap77-ui-start-gate.md)：正常时钟客体自检通过；仅前三任务自然完成，第四未创建、屏障未进入；主循环第二条30072后futex等待，仍无首绘。

- [AP78 timecode抓包与boot链](ap78-timecode-boot.md)：AP78a冻结52B；AP78b timecode消费free0后到0165同步等待；同event/cv绑定，第四任务/屏障/UI恢复仍未通过。

- [AP79 VDF/HDMI启动尾段](ap79-boot-vdf-hdmi-tail.md)：8/8新回复和325消费free0，四任务自然完成；父线程在屏障前getpin等待，完整模式/双50行拓扑已读回。

- [AP85 软件 OSD 环与0152](ap85-software-osd-ring.md)：r4原完成1358次、UI更新1360次，0152/free0；仍均匀黑，新0400同步等待及后段1005待配对开放，未满300秒。

- [AP86 消息池与显示目标](ap86-osd-pool-display.md)：v2完成300秒，5199次完成、三队列原生收/free对齐、0400自然返回；missing空、im结尾存活，类别270=7/方向243=2；仍黑屏，Widget根/资源/dirty原因未闭合。

- [AP87 UUD队列与首屏](ap87-uud-queue-first-screen.md)：0402/0404与11项原生命周期通过，30086自然送达；300秒im存活，AppFw新等Backup内核服务，GPE/PNG为0、missing非空。

- [AP90：资源区间、fmt2与首张原厂文字](ap90-gpe-resource-fmt2-first-text.md)（77条命令成功，首张原厂槽1警告；输入未验收）。

- [AP91：合成按键到原输入链，警告未关闭](ap91-synthetic-key-input.md)（300秒健康；12事件接收；菜单反馈未验收）。

- [AP92：卡检测默认分支与原挂载失败](ap92-media-detection-mount-observation.md)（300秒健康；原超时0→1通知、两次open失败实测；等待RM无卡合同）。

- [AP93：软件空槽与首次设置交互](ap93-empty-slots-first-setup.md)（空槽链通过；语言页下/上原像素反馈已证；确定后新子块绘制待审计，尚非待机/MENU）。

- [AP94：离屏子块与首次设置（含受控拒绝及诊断续轮）](ap94-offscreen-child-stretch.md)

- [AP95：宿主逐步输入计划（准备；删除键审计待完成）](ap95-host-step-input.md)

- [AP95 删除/C4 与逐步界面测试](ap95-ui-test.md)：删除进入机身设置；补查发现原assert，生命周期通过与应用失败分开记录。

- [AP96 设置后RAM回放与输入线程诊断](ap96-setup-replay-input-diag.md)：600秒回放双SHA正确；退出设置原assert停止输入线程，已取证。

- [AP97 重复面板配置事务](ap97-repeat-panel-enum2.md)：重复panel事务修复后待机已证，MENU首轮遇K混合拒绝；部分菜单已只读导出。

- [AP97-r2 常量透明度与菜单导航](ap97-r2-menu-navigation.md)：待机、MENU和DOWN×2/RIGHT/ENTER像素通过；日期force未清零，严格600秒回执见报告。

- [AP98 日期服务只读抓包](ap98-date-readonly-capture.md)：完整32B请求与内核44B分发已保存，日期OK后原调用仍等distribution_done；不添回复或改模型。

- [AP99 软件CP日期分发consumer](ap99-cp-date-consumer.md)：原32B sync已返回0/原free0，boot force1原写读通过；后续新VDF0146等待使首绘未到，无PNG不发键，manual force0/待机/MENU仍待验。

- [AP100 原生首次设置与CP Backup同步](ap100-native-setup-backup-sync.md)：600秒健康，manual force0原写/读、待机/MENU浏览、真实原厂Backup.bin及原API恢复通过；高亮缺口与内层save返回未单独探针明确保留。

- [AP101 原生Backup文件冷启动首轮](ap101-native-file-cold-boot.md)：原loader数据逐字吻合，新增SHA观察门误用不存在的applet导致preAP早停；构造profile适配待Lead决策，600秒/待机/UI未完成。

- [AP101-r4 完整600秒与English RAM状态](ap101-r4-english-ram-save-pending.md)：health通过，原保存文件直启待机、原键UUD4/4/force0、MENU语言已改English并写原RAM；文件语言仍32，等待原厂普通保存触发，不直接flush。

- [TRY1 本机网页菜单试用](try1-local-ui-trial.md)：冻结AP101-r4模型复用，网页七键和约2fps提交帧；待机/MENU、网页结束及Ctrl-C收尾已通过。[启动说明](../../outputs/fx3-vm-trial/README.md)，自测已退出，需先执行启动命令。
