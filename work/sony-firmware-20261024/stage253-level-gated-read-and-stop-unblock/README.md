# FX3 受限读取候选与初始MSC退出路径

2026年10月31日。**找到受认证级别限制的固定读取候选，并完成纯CPU编解码；退出缺口已定位到普通应用的取消/回收触发链。** 本轮全部离线，没有新的真机验收。12号Mac接管/归还通过仍保留，Sony完整进入/退出包尚未就绪。

## 已落实的读取候选

从固定官方nflasha15镜像提取原libpro00.so（6032字节，SHA256为771749c2397c48e9a3444a7562a8f8e2773abf59a262276c2b225cc415ac9403），只作数据解析。libsencore的ProductInfoFunc按libpro%02X.so与command%04X分派到command001F。

原pFunc表A、B有0x10 ProductInfo，C没有；onComplete分别将级别3、2、1映射至A、B、C，其它值清表。因此在这些原始绑定成立时，读取可用能区分A/B与C，不能单独证明最高级别3，更不是实机固件哈希或线程退出证明。

同一个0x001F命令包含两种不同效果：

| 参数 | 原处理分支 | 结果边界 |
|---|---|---|
| 0 | 分配88字节，调用Read_Hasp；按0x101000只读方式打开/setting/.hasp，读88字节并关闭 | 此读取函数没有直接write/fsync调用；成功返回1。不能扩大成整个认证会话零写入 |
| 0x80 | 调用Reset_Hasp | 0x101241写/创建/截断方式打开，实际调用write与fsync；必须排除 |

固定[候选计划](fixed-read-candidate-plan.json)只有一个17字节请求，内层为pFunc0x10、category0、command0x001F、单字节参数0；预期服务身份0336另须真实绑定。与[PMCA维护者readHasp实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L1013)的参数对齐，FX3具体分支和表门控来自本次原件核对。

[bounded_hasp_read.py](bounded_hasp_read.py)不含I/O或启动入口。它只生成/校验固定读取请求，拒绝重置参数和额外负载；返回帧最多100字节（12字节头和88字节数据），仅向调用者输出临时密钥HMAC与长度等信息，不输出原HASP内容，也不将回复升级为认证或退出成功。实际接入接收器时须另行保证原始服务记录的存储范围，不把这个CPU接口当作已部署的隐私保障。

[检查回执](bounded-read-test-receipt.json)通过：9种危险/变异请求、5种错误回复、4种无效序号和3种无效密钥均被拒绝；仅使用人工载荷，无机身读取。原始HASP可能包含服务身份/历史信息；这不是备份，也没有读取用户机身上的文件。

## 退出链的新定位

1. 原libObj普通协作者回调0xea128仅处理事件1，对其它事件直接返回。它与独立服务模式的WorkerThreadManager不是同一条取消链，实际机身的注册与所有其它取消来源也未测量。
2. 普通应用确有监督线程0xea750：在sem_wait之后调用0xec458取消NIN、0xec4bc等待；后续结束阶段通过0xea3e0处理工作线程。join包装器检查pthread_join返回并仅在成功时清句柄，但这两个已审查调用者没有消费其成功/失败返回值。不能凭状态推进或新PID认定回收完成。
3. 精确7.02 usbg_sen.ko的core_stop设置中断位2并唤醒队列；接收等待条件却是完成位1。完成回调才设置位1并唤醒。条件cleanup中的usb_ep_dequeue返回值未检查；唤醒与完成不能合并为一个事件。
4. 在已完成、被中断的接收路径中，内核count=-4被libInfraUsbCmn映射为内部-15，进入252核对的Serialize通用负值取消等待循环，并非-6/-4专用互斥锁释放分支。要结束仍需要正确的取消触发和回收。

这里形成的是带明确前提的反例：若选择普通协作者且没有其它取消者，只取挑战就省略完成/资源交接，而非事件1的回调又直接返回，则尚未建立谁来取消NIN；它可能留在等待取消的循环。**没有在真机制造或观察到这个挂起，也没有宣称不存在其它回收路径。** 此反例足以停止把“挑战次数更少”直接当作退出更安全的依据。

本轮还固定核对了gcore/gcw转发、DWC3 dequeue/giveback及usb_gadget_giveback_request等7个原内核符号范围。DWC3有直接giveback路径，也有局部返回0而未直接调用giveback的分支；实际端点绑定、请求状态和中断进度未测，不能据此宣布驱动缺陷。Linux v4.9的[原始API说明](https://github.com/torvalds/linux/blob/v4.9/drivers/usb/gadget/udc/core.c#L260)与新版异步说明不同，本轮使用版本对应参考，不用现代契约套FX3。即使一次dequeue按契约完成，也不能单凭该返回值证明用户态NIN已经join成功。

## 下一步与范围

停止推进仅挑战候选，不重复12号接管诊断。下一项转为普通应用完整进入/资源交接/服务结束的适配：把监督线程的信号量、资源回调及Senser结束回调接通，明确忽略cancel/join返回值时如何保留UNKNOWN，再固定完整的进入/退出范围。认证可能更新历史或模式状态，不能称作整个会话只读。

本轮核对17个原ELF完整函数、6段明确的模块代码范围、7个内核符号范围和56处指令；没有执行原Sony/Linux指令。[读取门控与普通监督路径](level-gate-and-normal-exit.json) · [精确停止/解阻塞审查](stop-unblock-audit.json) · [读取与重置区别](read-versus-reset-supplement.json) · [准入结论](admission-decision.json)。GPL参考仅作参考，实际7.02原字节与运行状态分别记录。

G01至G16及现有授权不变，没有新增USB缓存、管理员、Sony认证、机身读文件、上传或固件写入。完整同机健康备份、独立救砖、MAIN1080p H.265和最小持久化准入仍未通过，首刷未放行。
