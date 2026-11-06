# AP103 API16 还原：等待真实完成确认

Lead `msg_45f1419f7e5e` 独立授权。只处理收尾，不修改GPE完成语义、原固件、CP/Backup/日期等模型，不推进完整菜单测试。

## 旧第四轮能证明什么

`ap103v4ldec600-71ce5752` 的控制头证明宿主已写入正确shutdown control；原串口有 `FX3_AP100_CONTROLLED_CLEANUP_BEGIN`，证明guest已接收请求并进入原清理脚本，不能归因“control未被处理”。退出时API16仍为软件跳转，`restore_seen=0`；没有原unbind helper的进入/成功完成记录或清理脚本END。旧guest已退出，没有脚本内部阶段字段，因此不能细分其停在pidof、STOP、sleep还是insmod前后，也不能补称写回函数已经失败。

冻结guest文件观察器仅在 `system(shutdown.sh)` 整体返回后写restore_status并置restore_seen=1；status初值0不代表成功。原清理脚本STOP所属im.elf、sleep1、加载既有unbind helper，再返回；helper通过主模块自己的 `fx3_sync100_shutdown` 调原生patch API恢复16字节并读回。原件不写。

明确的宿主缺陷是：正常收尾固定恢复运行3秒（异常路径5秒），不等待guest确认，也不根据API16结果决定收尾失败，就退出QEMU。即使脚本已经开始，仍可在其完成前截断。旧轮证据：[LF行号、原串口哈希、控制头与API16](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap103-restore-old-run-proof-v1.json)。这个确定的时序/完成判定缺陷与旧脚本内部具体耗时原因应分开。

## 修复

新 `runtime/restore_api103_v1.py` 与 `run_candidate103_v4.py` 替代两条固定等待路径。只发送一次既有8字节软件保留区控制请求，然后最多等待20秒，每250ms暂停guest，读取独立控制头和实际kernel API16，随后继续运行；**只有控制身份/请求值正确、restore_seen=1、restore_status=0、实际16字节逐字节等于原值四者同时满足才通过**。目标原值为 `000b00b4fd7bbba9fd030091f35301a9`。

逐次header/API16原始读回和时间保留在新run的`restore103-*`文件，最终条件写`restore103-receipt.json`并进入主receipt。超时、guest错误或ack/原字节不一致均作为宿主错误，使runner退出2；不把“请求已发出”、默认status0或单独原字节判成完成。观察窗口之后独立执行收尾，结束时guest暂停，再正常quit/reap；不由宿主写原API代码。

## 验证

宿主回归覆盖：4.5秒后才完成时旧3秒窗口失败、新20秒窗口成功；只有字节原值而无ack、只有ack而字节仍为跳转、guest返回错误均拒绝。只允许向既有控制区写一次8字节，所有其他操作只读；[日志](../../work/fx3-vm-20261101/menu-repair-01/runtime/check-restore103-v1.log)与[源码/命令哈希回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/restore-api103-v1-build.json)。

真实短guest第一轮：`ap103restore60a-f0a4d75c` 沿用未改的AP103-r2候选、四核、60秒、零UI按键。最初6次读回仍未确认；第6次（1.570秒）同时出现seen1/status0与原始API16，通过；QEMU0/reaped/输入不变。

第二轮：`ap103restore60delay-0ccbbf62` 的独立test-only候选仅在原shutdown脚本前增加5秒guest延迟，原脚本余下字节及所有设备/GPE/Backup模型保持原样。**3.077秒时seen0/API仍为跳转，6.664秒时seen1/status0/API精确原值，6.669秒完成收尾检查。** 这是真实guest超旧3秒期限的回归证据；人为延迟不代表旧第四轮具体子阶段的耗时原因。此候选不作为菜单或试用版本。

两轮均零UI键、QEMU退出0/reaped/PID消失、所有输入SHA不变、21个kernel断点移除且原字节一致、两把运行锁实查已释放。旧第四轮仍保留失败，不追改它的回执；本修复关闭的是未来收尾完成判定与等待缺口。完整AP103的600秒/日期/普通开关保存仍未验收。

[两轮独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap103-restore-runtime-review-v1.json)，各轮`restore103-receipt.json`包含全部原始控制头/API16路径和采样时间。后续使用`run_candidate103_v4.py`的有界确认收尾，生产基线回到AP103-r2；延迟候选仅作测试。接续AP104仅增加被动完成代次日志，按Lead `msg_b94a0dacc3e4`，不改完成语义。


## AP104 提前故障路径补充

AP104-v3 在 CP 已绑定、旧 file observer 尚未启动时发生宿主探针异常，收尾控制页尚无 F100FILE，最终 API16 仍为跳转；原先两轮短 guest 证明不覆盖这个窗口。新增 `restore_api103_v2.py` 对未绑定且原始字节/无待处理请求保持暂停退出；`ap104-r2-observer-ready` 先验证观察页初始化及活PID readiness，再允许 CP 绑定，原收尾脚本不变。

实际 AP104-v4 与 v5 收尾分别 1.550s、1.565s 得到 seen1/status0 与 API16 逐字原始，QEMU0/reaped/输入SHA不变、断点卸载及锁释放通过；这些是校准收尾证明，不是600秒UI健康验收。详见 [AP104被动观测](ap104-passive-completion-trace.md)。
