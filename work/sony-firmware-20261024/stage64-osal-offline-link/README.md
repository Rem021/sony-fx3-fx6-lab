# FX3 7.02：原OSAL模块离线重定位、LIRO绑定与内核服务边界

本轮将原`devno.ko / osal_utm.ko / osal_uipc.ko`在声明的客体布局中完成973项重定位，核对分支范围、回算目标、未改字段及映射字节。原LIRO复制链把4个消息导入接到原OSAL函数；目标FH的A5／C3与原UHD请求实际进入原OSAL申请路径，停在原内核锁函数第一条指令前。

独立来源setter与两个模块初始化入口也完成了各自有界检查。正式结果共33段：7次原LIRO复制边界、18次原返回、3次通道入口暂停及5次内核服务边界。这里的链接与映射均发生在离线客体中，**Linux模块装载／驱动注册／IRQ锁／消息缓冲区／同步回复／硬件主录仍未验收**。

## 重定位覆盖

沿用同包固定哈希的原ELF、内核及真实导出记录。三个模块的54个去重外部提供者名在原模块导出或经邻接名称核对的原内核候选中逐项解析，不给缺失名字补函数地址或返回值。

| 模块 | ABS64 | PREL32 | CALL26 | 合计 |
| --- | --- | --- | --- | --- |
| devno.ko | 70 | 0 | 0 | 70 |
| osal_utm.ko | 57 | 4 | 30 | 91 |
| osal_uipc.ko | 326 | 56 | 430 | 812 |
| 总计 | 453 | 60 | 460 | 973 |

每项均保存原值、符号及加数、位置P、目标S+A和重定位后字段。`PREL32`检查有符号32位范围，`CALL26`检查4字节对齐、±128MiB范围和原BL操作码，并从编码回算目标；所有变化必须落在重定位字段。规则对应[Arm AArch64 ELF ABI](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst#573relocation-types)（2026-10-26重新读取）。

模块节独立按页布局并按标记映射R、RX或RW，没有RWX页。`NOBITS`只是该ELF布局的零值初始存储，不能当成Linux驱动、内存池、线程或当前任务已经初始化。两个位于内核文件覆盖范围外的数据候选仍只作地址来源记录，没有补成虚构的内核运行状态。

没有输出重新封装的ELF／Sony模块／刷机包。重定位后的节字节仅用于本地客体及哈希／字段复核；布局不是机身模块地址，也没有证明Linux实际模块装载器、结构ABI或当前机身版本接受它。

## 原LIRO到原OSAL的实际执行

按原LIRO的4个`ABS64`重定位记录，为其源向量绑定：

| 原符号 | LIRO `.init.data`偏移 |
| --- | --- |
| `osal_snd_sync_msg` | 0x368 |
| `osal_valloc_msg_wait` | 0x398 |
| `osal_free_msg` | 0x3a0 |
| `osal_set_msg_src` | 0x3c8 |

随后由原LIRO指令通过原内核`memcpy`复制整个导入向量，逐项回读av-cam槽位。原`memset`加上这4项共5个非零槽，其余导入保持0。

沿原manager／factory／队列前缀重新建立暂停状态，再从同一原请求继续：原资源元数据及216字节消息构造 → 原`+0x2f038`间接分支 → 原模块`osal_valloc_msg_wait` → 原内部申请helper → 原`osal_lock` → 原内核`_raw_spin_lock_irqsave`入口。

这次`+0x2f038`确实执行，目标为原模块导出函数，没有用观察器跳转、换返回码或补缓冲区。三组请求都读到该模型中client ID 0x3c的空入口，随后进入原查找／锁路径。这个空入口来自未运行驱动初始化的ELF零BSS，不能推断相机有故障，也不能据此保证相机的入口为空或有效。

原文件、源描述／common FH、既有唯一客体BL和logger输入逐项保持。所有模块节在执行后与重定位初值逐字节相同；在本轮内核停点前未发生模块数据写入。

## 内核停点的具体原因

原内核锁入口地址在该布局下为`0xffffff80084a3de8`，其开头为：

```text
mrs x3, daif
msr daifset, #2
mrs x2, sp_el0
ldr w1, [x2, #0x10]
...
```

本轮在第一条指令前停止。IRQ状态、当前任务指针和该任务的抢占计数没有来自真实Linux启动或同机观测的证据，不能为继续执行编造这些值。本轮也没有执行锁原子操作、调度器、页分配或中断状态修改。

该地址是固定原内核在模型中的地址；没有接触宿主Mac的内核、驱动或中断状态。

## 两项独立组件检查

原`osal_set_msg_src`只有两条指令，其中一条写入`payload_pointer−12`的4字节。两组值分别在明确提供的128字节前缀存储上独立运行并返回，核对仅这4字节变化。它验证来源字段的局部ABI，存储不是实际申请到的OSAL消息，也没有完成发送链。

原`osal_uipc.ko`及`osal_utm.ko`的`init_module`各自独立运行至原`udif_driver_register`入口。原代码在栈上建立一个驱动指针数组，X0指向该数组、W1为1，数组元素指向各自原模块data对象。没有把驱动对象本身误当成X0参数，也没有执行注册正文、回调或线程启动。

静态原数据还显示：UIPC驱动对象+0x38指向ops，ops首指针指向原无具名符号的`.init.text`回调；该回调的原`CALL26 +0x90`再调用`k_uipc_init`。它不是假设的某个直接函数槽。内层函数依赖原`__mutex_init`、`__get_free_pages`、`fblock_init`、字符设备注册、proc创建及`osal_create_waitable_thread`等。下一步应核对原启动上下文和这些回调参数／依赖，不能将注册入口到达视为初始化完成。

## 失败记录与复核范围

保留了三次本地复核失败：重建计划与JSON的数字字典键类型不一致；注册参数曾误按直接对象指针检查；静态回调曾误认一个直接槽。它们均根据已保存的原数据／原指令修正观察或检查方法，没有修改固件函数、补返回值或改变预期内核停点。正式结果另存，失败源码和回执保留。

完整启用日志的时间／输出、真实单例／锁域／owner代次／消费者完成、16M写入器实际调用接合、真实MMU／代码发布／缓存同步、主录HEVC文件／29.97及精确30.000单列／音频／长录／温度／原模式、同机健康备份／回读／冷启动／独立救援仍未通过。相机权限仍仅缓存PnP盘点；本轮没有操作UU、Windows或实机，没有释放持久写入。

- [重定位器](link_modules.py) · [重定位结果](link-run-20261026/module-relocation-results.json)
- [原执行脚本](native_osal.py) · [正式执行结果](native-run-pointer-array-20261026/native-osal-results.json) · [源哈希](native-run-pointer-array-20261026/source-receipt.json)
- [内核与回调静态边界](kernel-boundary-audit.json) · [审计脚本](audit_kernel_boundaries.py)
- [摘要](summary.json) · [复核记录](coordinator-observations.json) · [清单](final-receipt.json)
- [完整目标及16项验收](../GOAL_STATUS.json) · [上一轮未绑定消息边界](../stage63-resource-message-boundary/README.md)
