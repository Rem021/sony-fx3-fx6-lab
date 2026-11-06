# UPM 原生回复与 FX3 日期初始化

AP27–31新增5次真实本机QEMU运行。受限SCU虚拟配置下，原厂UPM加载返回0、开机服务回读到原生数据；日期初始化和推进检查也已通过。最新im休眠78线程，appFw已映射，仍无GPE工作请求或原厂UI。

## SCU：明确推导范围，保留缺席的CP

从同机原UPM指令还原到f1388f54写101，以及f50/f5c/f58写入、轮询f60 bit8的路径。Sony7.00 GPL只给通用SCU DATA/SET/CLR间距，**不能证明这个请求组的完整握手定义**。本轮模型因此明确标为推导的虚拟AP请求寄存器组：物理f1388f50起20字节、32位访问、enable/request状态和set/clear约定；其它地址/位/访问返回事务错误，不扩展成完整SCU或电源模型。

模型绝不生成bit8的CP应答，AP试图置该位会被拒绝；没有CP中断或固件完成消息。独立QEMU qtest验证初态、AP置位/清位、拒绝伪造peer位和越界位。实际原UPM启动只观测到f54写101；更多寄存器语义仍未获机身证据。此模型是公开接口推导后的受限实验配置，不冒充Sony硬件规范或物理电源验收。

新增QEMU以独立SHA路径保存。构建时旧timer-only二进制先保留、最终恢复原SHA；既有AP18–26候选仍可引用原路径。裸build目录输出不能代替候选内的二进制身份。

## 原厂开机服务已接通

AP27原upm/udate均加载0；此前80924127的-1/1020已变为原生transport0。AP28增加只读返回采样，保持原结果和errno，并核映射epoch。8次开机因子回读前16字节为：

`11019200 02000000 01000000 01000000`

即00920111、mode2、boot_type1、eecap1。原UPM callback由注册点41c8重定位到text3278，匹配00920111/00920113并从原状态拷40字节到请求；本次只读回前16字节，不声称完整40字节或CP侧状态已验证。成功调用遗留errno1020不当失败；原819e0580仍有真实-1/1020。

## 日期：保留原时区，正确初始化UTC基准

依照维护者[seed-date-clock.c](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/seed-date-clock.c)先读当前、再读原默认值。AP29在UTC-only门槛返回6；AP30完整48字节证实当前clock未初始化（state3），原默认日期2021-01-01、TD540分钟、DST0、reserved0。两轮均在写日期前停止，失败保留。

同机原udate_open_kif注册90013d；udate_set_date允许有符号TD/DST±1440（或7fff保持值）、保留字段必须0；get_localtime在原running UTC基准上加TD+DST分钟。适配因而保留原540分钟时差，将初始本地2021-01-01 00:00换算成UTC2020-12-31 15:00，再走原BY_BOOT API。仅支持已观察到的UTC0或FX3+540默认，未知配置继续拒绝。

四项宿主纯日历检查通过：跨年、闰日、UTC不变、2000下界拒绝；未用成功RPC假桩冒充原驱动测试。AP31真实原API执行2/3/0/2/2，transport/status全0；读回本地2021-01-01 00:00:02、TD540仍在，推进检查elapsed2秒通过。这是虚拟固件默认钟，未用主机日期或真实RTC；不是墙钟精度、多核或CP跨芯片时间同步验收。

## 复核入口

- [5次原始运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/scu-date-run-summary.json)、[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)
- [UPM/SCU原字节与地址推导](../../work/fx3-vm-20261101/menu-repair-01/runtime/scu-model/upm-scu-proof.json)、[模型源码](../../work/fx3-vm-20261101/menu-repair-01/runtime/scu-model/fx3_scu_request.c)、[构建/原二进制恢复回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/scu-model/build-result.json)、[独立qtest](../../work/fx3-vm-20261101/menu-repair-01/runtime/scu-model/qtest-9125c0be/receipt.json)
- [原UPM回复合同](../../work/fx3-vm-20261101/menu-repair-01/runtime/upm-native-reply-proof.json)、[返回观察器](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/ioctl-trace-v9.c)
- [原日期模块ABI](../../work/fx3-vm-20261101/menu-repair-01/runtime/udate-abi-proof.json)、[适配源码](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/seed-date-clock-v3.c)、[宿主日历测试](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/check-date-utc.c)
- [最新候选AP31](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap31-date-zone/candidate31.json)

五次host QMP退出0、进程回收、输入SHA不变、宿主观察无错误。AP29/30门槛6和无应用启动如实保留；不把host0算成guest完整成功。所有运行无网络、真实USB/SD/主机盘透传，Backup_save0，源固件未改。

下一步依据AP31真实应用初始化/队列等待绑定CP启动消息及未实现端点，再使原系统提出绘图请求；GPE仍为诊断捕获、没有像素写入或完成回调。维护者[提示音native记录](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/report/system-sound-native.md)及源码已取作后续参考，尚未部署，也不能把A7C2的音频尺寸/地址或ready事件直接套到FX3。
