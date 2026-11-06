# FX3 保存内核的退出接口与唯一对象研究

2026-10-30。**已从保存的官方7.02内核确认：一次wait4调用持有具体的内核PID对象，但反复WNOHANG轮询不会保留该引用。它提供了改造方向，尚未解决完整任务身份。235版本仍有误认退出码的反例，安全准入未通过，不能投放真机或刷写。**

本轮只在Mac读取保存的固件和公开源码，执行自写解析器及Python调度模型；没有执行Sony/Linux原指令、启动Linux进程、查询USB/相机、管理员操作、认证、上传或刷写。当前相机真实加载的内核未测。

## 保存的实际内核给出的约束

原Image SHA为`da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`。沿用146固定解析器重解41269个符号，与保存的完整列表一致；原字和Capstone独立核对选定调用目标。[静态回执](kernel-interface-audit.json)共99项检查、18个按相邻符号地址截取的代码范围、10段固定源码范围。相邻符号范围不是ELF函数长度声明。

实际`el0_svc`装入系统调用数291，对编号大于等于291跳出普通表分派。九个表项逐字对应wait4、waitid、clone、futex、robust-list、exit等命名地址。不能用表尾填充推算可用调用数。

现代通用ARM64编号中pidfd_send_signal=424、pidfd_open=434、pidfd_getfd=438，均超出该保存内核的普通分派上界。[Linux v6.1原始头文件](https://github.com/torvalds/linux/blob/v6.1/include/uapi/asm-generic/unistd.h)只用于核对现代编号；[三项对照](modern-number-crosscheck.json)不意味着FX3实现现代接口。实际waitid分支也只接收which 0/1/2；3走EINVAL。完整符号表没有pidfd名称，但这些证据不排除未发现的Sony专用等价接口。

## 单次wait能绑定什么

实际正PID分支在Image偏移`0x24c74`调用find_get_pid，`0x24c8c`把返回的引用放进wait_opts，`0x24c94`进入do_wait，返回后`0x24ca0`才put_pid。find_get_pid本身的原子引用增量也已核对。wait_consider_task在`0x2397c`比较任务的PID对象指针和wait_opts对象指针。

因此，**已锁定A对象的同一次等待不会因为编号复用而匹配新B对象**。但WNOHANG返回0后引用即释放；下一轮根据数字PID重新查找，仍可能锁到B。这直接解释235的剩余反例。Linux v4.9.337参考源码的find_get_pid/get_pid、eligible_pid、do_wait和put_pid与这些原指令结构相符；它们不是完整Sony源码或实机调用验收。

[自写有限调度模型](wait-reference-model-receipt.json)枚举12个未加普通退出门的排序，其中1个误认B的exit0；限制“内核已取引用后才允许A正常退出”后剩3个排序，得到A的exit68或ECHILD，没有误认B。这里只覆盖声明的有限模型。

**单凭该退出门仍不充分。** 模型另固定四种反例：首次轮询后引用丢失、用户态entered标志早于内核实际取引用、A在放行前被SIGKILL并回收、阻塞wait中断后重新按编号查询。不能把用户态标志当成已经进入do_wait，也不能把阻塞等待单独当作完整修复；阻塞还会影响服务请求时限。

## 提前通知为什么不能代替真实退出码

实际内核有exit_mm_release和exec_mm_release，它们分别调用futex_exit_release和futex_exec_release；二者都会进入futex_cleanup。保存代码与晚期4.9.337源码结构相符，较旧的纯v4.9源码中robust清理位置不同，不能直接据旧版函数布局推定当前实现。

robust列表由用户态登记；内核更新OWNER_DIED不携带最终正常退出码。[Linux维护者文档](https://man7.org/linux/man-pages/man2/set_robust_list.2.html)也说明通知可由终止或exec触发。参考退出顺序为exit_code、exit_mm（含该清理）、exit_files；原Image中的相关调用点已固定。故通知出现时仍可能有FD尚未释放。

模型保留3个生命周期：正常exit0、写下计划exit0后被SIGKILL、exec后进程仍存活。三者都可出现该通知；私有DONE加自写planned_exit=0也不足以区分。另有两个clear_child_tid条件样例：mm_users为1时不会按该分支清零，私有VM子进程不能无条件依赖它。**本轮没有把这些提前标记接入成功判定。**

## 下一步的具体适配范围

优先审查隔离监管进程：让它具有独立的线程/子进程域，只创建本次工作子进程，并证明不会收养或接纳无关后代。这样可以从父子关系的封闭性解决“同编号且同父的外国任务”，同时保留真实wait退出码。当前只是研究方向，创建/退出/外层回收、全部FD归还和有界服务返回尚未实现或验证；不能以放松父身份检查替代证明。

235的单次准备成功到启动门、完整计划SHA绑定、连续信号屏蔽和超时HELD保持。正式0.4/0.5及23源码保持，195的root01未批准、未启动；全部16目标保留。完整同机备份、独立AP救砖/恢复、MAIN1080p29.97 HEVC和exact30及音画长录尚未验收。

本轮源码范围核查第一次仅因pid.c行范围没包含call_rcu而失败；扩大参考范围后99项通过。初次错误日志保留，没有因此更改相机程序。目标仍active；[封存回执](final-receipt.json)登记前后入口和保留项。
