# FX3 7.02：原内核符号及控制分派联合验证

2026-10-27。**本轮将上一阶段仅由7.00 GPL参考说明的条件边界，推进为7.02原内核分派片段与原SEN模块回调的离线联合执行。** 在声明的夹具下，原回调尝试排队后，原内核仍会调用EP0 HALT；排队失败后，后续回调返回0也可令内部流程正常结束。不能据此将USB报错解释为“没有生效”，也不能将正常返回充作排队成功。

这是原指令及参数边界的验证，不是实际Linux线程、事件队列或USB总线试验。本轮没有新增相机、USB库初始化、驱动、Windows或固件操作；阶段144的一次描述符授权保持消耗并关闭。完整1080p29.97 HEVC MAIN、同机备份恢复和独立救援等16项要求保持。

## 从原Image恢复符号

复用阶段47已经从官方固件FAT分区提取的 `vmlinux.bin`，6,610,952字节，SHA256为 `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`，没有重新解包209MB WBI。

[kernel_symbols.py](kernel_symbols.py) 从原 `kallsyms_lookup_name`、`kallsyms_expand_symbol.constprop.1` 的六个LDR64 literal操作数获取名称表、token表/索引、相对地址、计数和relative base。位置不取自参考构建。解析检查指针范围、token边界、计数、名称编码和地址排序，得到41,269项符号。[恢复回执](kernel-symbol-recovery.json)和[完整符号表](work/kernel-symbol-catalog.json)保存地址/类型/压缩偏移及来源SHA。

`setup_vendor_specific` 和 `delayed_setup_req` 没有保留独立符号，不能强行使用假定边界。实际 `delayed_setup_thread` 在原Image偏移 `0x2e7420`；其指令内命令跳转表第4项指向 `0x2e7548`，后续为vendor接收者和注册回调分派。两个静态函数在该线程中的对应逻辑已按实际分支核对。

首次按未带编译器后缀的 `kallsyms_expand_symbol` 查找被拒绝，保留在 `attempt-exact-static-name`；随后使用原调用目标和实际 `.constprop.1` 符号，没有放宽唯一匹配检查。

## 符号解析的独立对照

[verify_kernel_symbols.py](verify_kernel_symbols.py) 检查：

- 原 `__ksymtab` 的3,633项与GPL表的2,456项，共6,089对独立值/名称记录，全部与恢复的名称及地址一致，表内名称排序也相符。
- 在Unicorn中抽样执行原名称展开函数1,007次，包括首尾、长名称及本轮USB目标；名称、返回的下一压缩偏移、输出保护字节、SP及callee-saved寄存器均通过。
- 三项USB导出地址与阶段145基于原独立导出表和排序邻居得到的候选一致。

见 [执行回执](run-symbol-verification/results.json)和[逐项导出对照](run-symbol-verification/export-crosscheck.json)。没有将41,269个名称都在guest执行，也没有启动内核。一次错误的预期总数6,091在最后断言被拒绝，已按原表边界修正为6,089；原源码/中间结果保存在 `attempt-export-count`，当前通过回执对应修正后的执行源码。

## 原内核与原模块联合执行

[run_vendor_dispatch_guest.py](run_vendor_dispatch_guest.py) 使用两组固定原字节：7.02原内核，以及SHA256为 `1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2` 的 `usbg_sen.ko`。模块 `.text[0..0xc8)` 指令不修改；仅在guest副本中对literal数据实施声明的ELF地址重定位，导入调用由明确桥接器处理。START/STOP的16B控制头取自固定原 `libInfraUsbCmn.so`。

进入点在原线程内部 `0x2e7524`，已经提供声明的命令、gcore/driver链表、frame及锁参数；不是从线程入口或Linux启动执行。原kernel的vendor arm会通过真实间接调用进入原SEN回调，再返回原kernel回调结果判断与HALT分支。

| 声明场景 | 原分派路径结果 |
|---|---|
| START / STOP，SEN回调后全为THRU | 尝试排队一次，随后调用HALT桥 |
| 事件队列桥返回-12 | 原模块仍返回THRU，原kernel仍调用HALT桥 |
| 停止其他driver桥失败 | 不尝试排队，仍走HALT分支 |
| 控制头不匹配、命令表为空或driver列表为空 | 不排队，走HALT分支 |
| SEN之后另一个回调返回0 | 不调用HALT桥，清除内部EP0标志 |
| 排队桥失败后，后续回调返回0 | 同样不HALT且内部结果为0，不能证明排队成功 |
| 之前的回调已返回0或STALL | SEN回调被跳过，注册顺序会改变行为 |

11项检查通过，共11次原kernel分派片段进入、8次原SEN回调进入。执行源副本、轨迹和边界结果见 [run-vendor-dispatch/results.json](run-vendor-dispatch/results.json)。内部寄存器w19可以是HALT辅助函数的返回值0；它不是主机收到的USB成功状态。

以下均为明确夹具/桥：IRQ锁帮助函数、停止其他driver的结果、事件投递的结果、HALT、printk、memcmp和其他回调的返回值。没有运行真正的调度、线程队列、IRQ状态、driver停止、USB控制器或物理传输。guest写入只允许指定frame及内部标志，输入头和请求保持，结束时SP/frame检查通过。

一次执行前审查发现“不匹配控制头”夹具误改了recipient，已改为只改bRequest并保留Other recipient；原版本及审查说明保留在 `review-before-vendor-run`。没有扩大可执行guest路径来迁就错误输入。

## 对后续真实传输的约束

[汇总核查](completed-local-review.json)明确：原7.02这些条件分支已取代仅靠7.00参考的推测，但仍不证明本机实际注册顺序、排队/消费/线程完成或USB线上的STALL。真实后端必须保存原始传输结果，区分已结束STALL、仍在途、超时和设备丢失，不自动重试START/STOP，也不把内部分派0当成相机已进入或退出服务模式。

下一步完善真实收发与驱动归还的受限实现，并沿已恢复的注册/回调地址追踪初始MSC认证处理者。摘要的公开MSC参考与原SERVICE校验仍分开；没有以本轮分派验证替代初始MSC摘要验证、同机健康备份恢复或独立救砖。
