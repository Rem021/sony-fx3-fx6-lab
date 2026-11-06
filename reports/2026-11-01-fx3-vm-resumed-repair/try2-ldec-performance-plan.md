# TRY2 离线准备方案

当前仅准备，不启动QEMU、不占运行锁、不修改正在使用的TRY1入口/网页/候选。恢复时间由Lead在用户试用结束后明确通知；TRY2尚未交付。

基线为带软件 `/dev/ldec` 的 AP103-r2（candidate SHA `5d2155cb3e208ba182caa1c57e8c03f05b140e575ec9ea7c9b8e2743993aefe7`），沿用原厂保存文件冷启动、原按钮和原显示协议。已离线生成 `runtime/ap105-v1-gpe-perf/candidate.json`，CPIO仅替换 `simulation/fx3-gpe-observe-v7.so` 的内容为Lead接受的 `fx3-gpe-observe-v26-perf.so`，SHA `30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`；其他成员含init/软件LDEC/Backup/原收尾脚本逐字不变，DTB只更新initrd-end。

性能件保留v8像素结果和准入/拒绝/完成语义，采用backend-v9与对象/epoch映射缓存、已登记对象权威验证；生产关闭纹理SHA/直方图、callback地址缓存仍关闭。它与本工人的 `v26-profile104` 是不同产物；AP105首先使用原封不动的已接受perf二进制，不叠加未验收计时器。

恢复后先执行AP105：`run_candidate105_v1.py`，1200秒、4核MTTCG、0 GDB断点/寄存器读、30键兼容原guest上限。逐步目视待机→MENU→Setup→语言弹窗，核对橙色高亮/图标/面板；以用户态dynamic领取至完成投递的保守上界核对每个同步批次小于原5000ms，并核对释放顺序、无unfetched/断言/新绘制拒绝。此上界不冒充直接测得ReceiveDrawComp入口；若不满足或字段不完整，不宣称5000ms验收通过。

随后同轮完成English确认→MENU关闭并实际待机静置至少60秒→RAM/原厂Backup.bin代次、语言键与bank checksum；再逐图确认原日期值→观察原全量同步/新文件。仅从原菜单自然触发保存，不调用额外flush，不注入RAM。轻量轮不直接探针内核Backup_sync_subsystem入口，使用实际原UIPC/DMM请求和文件变化并标清缺口。可选开关仅在剩余时间、白名单键与已支持协议内选择，未知请求即停。

AP105通过后另建 `run_trial_v4_try2.py` 等新版本，保留TRY1 v3及历史runs。复用本机127.0.0.1网页、7键、100ms、最多30键、一次一个pending输入、原生immutable ring/epoch/FNV校验和网页结束/Ctrl-C/最长时长收尾；HTTP线程不访问QMP或guest。固定候选及源SHA，接口仍排他获取现有两把锁，不为试用新建模拟器实例。

TRY2收尾采用20秒guest确认+原API16双核验（restore_api103_v2），并单独验证启动前未绑定、已绑定尚未首帧、正常待机/菜单中的结束路径。AP105遵照“只换GPE”保留原init；TRY2若要覆盖绑定后观察进程未就绪的早停窗口，应在新试用候选复用已验证的file-observer-v2 readiness-before-CP-bind，并单独记录该观察接入改动及早停回执，不能把AP105正常收尾推广为所有启动阶段已通过。

交付前完成实际网页显示/按键/结束及Ctrl-C测试；每轮QEMU退出0、reaped/PID消失、输入SHA不变、guest ack/API16原字一致、两锁释放。当前原始固件、原厂保存文件及既有候选保持只读；不自动把试用中的RAM设置作为下一轮种子。若改用新原厂文件作为默认seed，另做原loader和AP/CP bank字节/校验及CP profile冷启动验证。

AP105运行验收、保存闭环、TRY2网页与早停测试目前均待执行；宿主字节等价和当前离线CPIO审计不替代这些门。
