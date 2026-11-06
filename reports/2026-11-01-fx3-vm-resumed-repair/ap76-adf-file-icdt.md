# AP76 提示音文件 / DMM / 用户态ICDT

**最终v30运行`ap76corr-316e20b7`通过提示音注册软件链验收**：13轮26包327/32a全部由原应用消费释放result0；后4轮四次ICDT完成被原线程消费，随后本地DMM逐次释放并继续注册，无abort。qemu_exit=0、process_reaped=true、宿主PID消失、inputs_unchanged=true、missing_markers=[]、两锁实际重取释放、末次snapshot含im.elf映射。四任务屏障是否越过仍未证实，不能由注册通过宣称菜单恢复。

独立41db00000/60000（六个64KiB stride、每槽暴露c800）已核对FDT与memrsv全部旧预留不重叠，位于实际400000000..53fffffff RAM内，启动后完成独占claim与映射。remote索引2..7避开63a索引0..1；完整句柄与代次校验，拒绝过期、重复传输、越界或未完成时释放。正常路径保留4个目的槽，没有复用覆盖。四份CPIO内原声音文件逐一SHA核验，未改文件或波形。

| kind | native local → remote handle | 327 wire phys | 实际读长/327 size | volume | 327/32a free |
|---|---|---|---:|---:|---|
| 10 | 0x409 → 0x8402 | 0x1db00000 | 2752 | 6 | 0 / 0 |
| 11 | 0x40a → 0x8403 | 0x1db10000 | 2752 | 6 | 0 / 0 |
| 12 | 0x40b → 0x8404 | 0x1db20000 | 9600 | 7 | 0 / 0 |
| 13 | 0x40c → 0x8405 | 0x1db30000 | 12160 | 7 | 0 / 0 |

每轮传输length=51200（目的容量），源offset/目的offset均0，mode1；327 size是实际文件读取长度，不能混作传输容量。目的APbacking为41db00000/41db10000/41db20000/41db30000，wire phys保持1db域，未擅加400000000。实现清零目的长度并记录元数据，不复制原声音、不声称原波形；本轮没有独立QMP目的区回读，零写依据执行路径与宿主内存检查，不冒充物理回读验收。

ICDT真实入口由原库+800 PLT/GOT11020核对为**osal_snd_sync_msg**。同步调用时捕获两个descriptor及本次callback/context，校验live句柄、方向、代次和边界，仅写request+40=0；另发24B到0282078f，前16B来自本次原callback/context、后8B零，不调用内核DMA，也不直接调用callback。四次callback/context可因复用同一栈地址相同，按不同目的live句柄管理，未错误去重。原icdt_u_rcv在+97c调用callback后+988释放，4次原生free0及后续local free/327证明外层2e15ad8..af4已退出，而非只回接受成功。完整raw、用户栈、callback/context和lease在[最终回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap76_final-review.json)。

宿主ASan/UBSan覆盖六槽、generation递增、过期句柄、越界、重复完成、原8020字节oracle、动态完成包、发送失败的内存/元数据/request结果回滚；最终补测802a非零correlation0xa55a正确回显+6。802a本轮用户态方案未实际调用，格式为宿主验证，不冒称驱动查询验收。

| 四任务 | 证据及边界 |
|---|---|
| adf_set_volume_i | 032e原生消费free0；匹配完成句柄未直接观测 |
| regist_beep_signals_i | 全26包free0、四个文件读长/传输完成/本地释放；正常注册循环可返回（原码推断），worker完成句柄未直接观测 |
| license_get_i | 六次Has*原厂返回0；完成句柄未证实 |
| adf_get_func_i | 无325/8B或1325/28B样本；状态未证实，不能以32d替代 |

未直接取得2b6353c四个匹配句柄和计数到0的回执，故**屏障越过未证实**；没有可声称“屏障之后”的初始化时间线。0x11a后全部既有trace发送记录与四个同步48B raw均在最终JSON（保留原有去重/预算边界）。未观察到新的已定位同步阻断请求，未擅自补新协议。

保留AP75r3观测：本轮GPE_CMD、timer176fb4c入口、1004和8288076c发布事件均无样本；仍无首次FillRect或菜单像素。不能据此全局否定窗口外事件或宣称原显示功能。

历史与更正：首轮v28 `ap76file-c5303a3b`漏拦同步入口，op5返回-1/errno1020后assert，回执保留为失败；修正v29 `ap76sync-fe30bc21`同样26包/4次完成通过；最终v30仅补802a非零correlation允许/回显，`ap76corr-316e20b7`复跑通过。原v27/v28/v29及全部runs未覆盖。版本/依赖SHA见[来源清单](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap76-source-provenance.json)，[文件链摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap76-file-chain-summary.json)。当前无QEMU，等Lead决定屏障句柄观测或其它下一步；没有原声、播放、真实DMA/CP、物理显示或实机验收。
