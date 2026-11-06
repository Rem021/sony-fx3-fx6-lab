# 图层配置、锁等待与首组绘图请求

仍不能打开可用的原厂菜单。此次续接越过了原生 `0x147` 图层请求；AP54 首次捕获原应用的 GPE fill/flush，但后端返回5、完成通知和像素写入均为0。AP55 修正模拟层锁等待后，图层回复正常消费，但该次没有捕获 GPE 调用，不能声称绘图可稳定复现。

## 当前核验

外盘 UUID 正确；Mac 不是 Git 仓库，沿用现有任务目录。交接快照及原 Orca 会话只读。启动前没有遗留 QEMU，所有新运行串行执行，结束后进程已回收、输入摘要不变、观察器无错误、异常标记为空；这些属于主机运行回执，不代表 guest 正常关机。未接入物理设备、主机磁盘或网络。

|运行|窗口|实际结果|
|---|---:|---|
|AP54 / ap54trace-3de8c54e|60秒|v14 仅加 entry/allocated/applied 诊断；0147提交、原1147消费释放0；原 Application_System_Init 返回；GPE fill/flush各1次，result5，无像素|
|原AP53 / ap53long-4c0b7971|110秒|旧v13未变，停在014c发送后；QMP快照落在 libc sched_yield，返回地址对应 osal_free_msg 获取全局自旋锁的循环；不是简单延长窗口即可解决|
|AP55 / ap55futex-0cc9b8df|70秒|v15将全局锁争用改为32位进程私有 futex 等待/唤醒；全部要求标记通过，0147提交及原1147释放0；该窗口没有 GPE 请求|

一次尝试在AP54仍占锁时启动AP53被现有非阻塞文件锁拒绝，未启动第二个guest；待AP54结束后才执行表中AP53复测。

## 改动与依据

AP53的图层模型保持原有24×32B验证、双768B配置缓存及pending f024计数。AP54未改模型或回复语义，只加三个阶段日志。AP55保留同一模型，把 `atomic_test_and_set + sched_yield` 改成 CAS acquire + FUTEX_WAIT_PRIVATE，解锁执行 release store + FUTEX_WAKE_PRIVATE。参考维护者的 [futex接口说明](https://www.man7.org/linux/man-pages/man2/futex.2.html) 和 [WAIT比较后休眠语义](https://www.man7.org/linux/man-pages/man2/FUTEX_WAIT.2const.html)。

AP53 QMP中的PC为 `0x7f808fc838`，LR为 `0x7f811b0658`；结合ELF PT_LOAD及原生maps，LR对应helper VA `0x14658`，位于 `osal_free_msg` 的自旋获取循环。高优先级接收线程使持锁线程饥饿是合理解释，但尚未独立测量调度优先级，不能视为完整因果证明。AP55通过验证说明改动可运行，不证明所有并发问题已消失。

v14与v15的ASan/UBSan主机传输检查均通过，覆盖原请求所有权、回复租约释放、发送及分配失败回滚、非法包拒绝。v15另用8线程执行24000次临界区，计数及等待/唤醒通过。主机并发检查用条件变量模拟Linux futex；Linux真实syscall由AP55 guest运行另行覆盖。

候选构建脚本沿用了AP53的scope/build文字，其中Aggregatev13不代表实际库版本：AP54实际嵌入v14，AP55实际嵌入v15；以各helper编译回执、候选CPIO和运行摘要为准，历史候选未重写。

## 下一处边界

AP54填充请求的首个64位值为 `0x43feb5100`，能关联到原DMM区段 `0x43feb5000 / 0x140000`，偏移 `0x100`。其参数包含640和480，但像素格式、步长、表面头、分配租约及flush完成协议还需原代码绑定；不能据此直接按RGB写内存或发送成功通知。

0147之后观察到未注册 `0x909c015b`，以及重复的 `0x86f` 目标警告；尚未证明它们与当前等待的因果关系，未添加回复。下一步从AP55线程栈和这些原生发送点继续定位，同时核对GPE表面布局。原菜单帧、按键到新帧、连续运行和正常guest退出验收均未完成。

## 回执入口

- [三次运行摘要](../../work/fx3-vm-20261101/menu-repair-01/runtime/plane-lock-run-summary.json)
- [锁等待PC与ELF绑定](../../work/fx3-vm-20261101/menu-repair-01/runtime/capid-lock-stall-proof.json)
- [首组绘图与DMM关联](../../work/fx3-vm-20261101/menu-repair-01/runtime/gpe-first-draw-observed.json)
- [v15主机传输及并发检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/vdf-futex-host-check.json)
- [v15编译回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-capid-v15-build.json)
- [当前可变检查点](../../work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json)
