# 原厂计时器、DMM 与图形入口

本轮新增4次实际QEMU观测（AP16–19）。原厂hwtimer初始化0，utimer、stream、stream2、DMM、grm_ma加载均0；原im已越过原DMM等待/递归问题，进入MPGRM_GPE0硬件访问。最新仍在libgpe+dc88写硬件寄存器时signal7，原厂UI未显示。

## 证据与因果边界

AP16逐线程采样修正了“全进程都停止”的简写：主线程及多数线程T(stopped)，THREAD_INFRA0却R，内核栈为grm_ma/ma_dmm_open_impl/osal_rcv_msg_tmo。此前没有kill/raise/abort命名观察事件，不能推断SIGSTOP来源。未发送CONT，也未抑制原错误。

AP17加入同机原DMM和DmmCfg；使用FX3 kemco中非tmonitor的memrsv和5GiB guest物理覆盖，initrd经显式loader放440000000，chosen起止同步。原udm_dmm在dmm_timer_GetSyscnt→osal_snd_sync_direct递归，触发真实kernel stack overflow，失败原始记录保留。

上游固定提交的 [qemu-menu-probe.py](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/qemu-menu-probe.py)与[qemu-sony-native.patch](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/source/qemu-sony-native.patch)给出utimer在DMM前及独立hwtimer模型。本轮只提取157行timer模型，未引入catch-all外设、crypto成功桩、USB、键盘桥或warmboot别名。Sony FX3 7.00 GPL参考源码确认f1042000和非FPGA IRQ_TIMER_BASE232（QEMU SPI200）；该源码不冒充精确7.02构建。

AP18原7.02内核hwtimer cpu0–cpu3检查和init返回0；stream/stream2也0，但生成的init没有真正插入utimer，DMM仍溢出。AP19修正最终init插入位置，实际串口UTIMER/STREAM/STREAM2/DMM/GRM_MA各RC0。cpu0–cpu3日志是原驱动测试输出，本次QEMU仍smp1；未验证多核和定时中断到期语义。

AP19原MPGRM_GPE0线程在原libgpe+dc88的`str w2,[x0,x1]`触发signal7。原库SHA、实际装载基址、指令字节和模块门槛已独立绑定；这是图形层执行证据，不是像素或菜单验收。

## 复核入口

- [4次实际运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/timer-dmm-run-summary.json)
- [逐线程读回](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap16-thread-readback.json)
- [GPE故障绑定](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap19-gpe-fault-proof.json)与[审计脚本](../../work/fx3-vm-20261101/menu-repair-01/runtime/audit_ap19_gpe.py)
- [timer模型来源与改动](../../work/fx3-vm-20261101/menu-repair-01/runtime/timer-model/model-receipt.json)、[构建结果](../../work/fx3-vm-20261101/menu-repair-01/runtime/timer-model/build-result.json)、[二进制与依赖绑定](../../work/fx3-vm-20261101/menu-repair-01/runtime/timer-model/binary-bind-receipt.json)
- [最新候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap19-utimer/candidate19.json)、[当前状态](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)

四次host QMP退出均0、已回收、输入SHA未变；新增QEMU直接依赖摘要事后仍匹配。guest异常如实保留，host退出0不等于guest启动成功。新timer模型仅任务目录编译，冻结outputs运行包未变，无实机、USB或主机盘透传。

构建前两次准备失败（Python生成文本转义、DTB start/end不一致断言）未运行guest；失败目录保留。首次ninja缺少既有PATH未成功再生成；复用已记录构建环境后2041项完成。后续应使用timer-model记录，原build_qemu_display.py的“仅Pixman”旧源摘要门槛有意不再适用于该派生源。

高initrd位于原CP大保留段内；其生命周期为Linux展开前资源，不能据此声称与未来所有CP/DMM所有者不重叠。启用新的物理消费者时仍须核对实际分配和租期。当前不执行原CP。

下一步以FX3自己的动态符号重定位和参数布局接入受限软件GPE，保持原回调/队列顺序、像素范围及生命周期；禁止用A7C2绝对偏移或仅回成功绕过原绘制。电源/日期/音频和CP显示consumer也尚未完成。无原UI、按键闭环、分钟稳定或guest正常关机验收。
