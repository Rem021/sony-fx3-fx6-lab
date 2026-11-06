# AP99 软件 CP 日期分发 consumer

**CP 日期分发已实际解除启动日期等待；首次设置、force0、待机与MENU尚未验收。** r2在日期完成后遇新VDF0146同步等待，无GPE/OSD/PNG，因此保持零按钮。Lead已派`audits/vdf0146-common-tail`，要求本轮600秒只读收尾后待命；未补猜0146回复。

## 实现与宿主验证

基线AP98，Lead msg_fa0d4b6ae7b5。原唯一kernel public owner增加909005c5的受限type1/44B consumer：实际source809005c5、原zero-ready profile、reason1..8；callback只入有界8槽队列，不在原send栈重入等待。独立原OSAL waitable线程串行创建本次AP-accounted动态回复Q，type2+reply_requested1+embeddedQ送回实际AP source，显式source909005c5；原AP内核产生type2响应。验证其status/date/timezone后提交软件CP UTC基值、TD/DST、单调时基和half-RTT补偿并读回，然后另分配type4/44B、source909005c5、echo原reason给原AP源。reason4不发type4，未设日期在BY_BOOT中诚实保留未知。

同一活allocation重复仅归并一次；新的相同字节请求允许新事务。source/长度/profile错误、满队列拒绝且不抢原消息所有权；分配/发送/原AP状态失败不发done，必要时回滚软件clock；原request按目的909005c5释放一次。其他目的保留原CP Backup行为，不直接在80900141回成功，不改原AP udate/force/Backup业务。所有软件slack清0并标synthetic_cp_clock=1/original_CP=0，不称运行了CP原固件或写入真实RTC。

100个独立Python datetime整数参考向量覆盖Gregorian闰年/世纪、UTC与TD/DST、毫秒进位与half-RTT；真实线程transport覆盖原type1→type2 fixture真实回复→clock→type4、reason4已设/未知、8槽、重复、错误source/长度、type2/type4发送失败与AP错误状态回滚，57次分配全部释放一次；原CP88全回归与新user Backup_nread观察均ASan/UBSan通过。native OSAL动态队列/信号量/等待线程ABI按固定原osal_uipc/utm模块导出和udate原描述符核对。

软件clock与四阶段原44B副本位于既有软件保留区41df08000/1000，14个256B记录含本次动态Q、原ready/type2 request/AP reply/type4、释放和完成状态；不触碰输入前4K或原CP地址。32B同步before/after沿用AP98独立观察页41df01000/6000。早期BY_BOOT物理副本会被原provider初始化清页，相关原日志保留；AP阶段记录QMP独立核回，不宣称串口全局无损。

## 两轮与观察ABI更正

|轮次|状态|作用|
|---|---|---|
|`ap99cpdate600-da98cc9f`|112.609s，退出0，strict health=False|启动日期往返通过，但observer把kernel式Backup_read三参用于user两参接口，额外读返回-1；未发键即受控停机。|
|`ap99r2cpdate600-9391e358`|601.093s，退出0，strict health=False|仅换为新observer v3，原user Backup_nread(key,buffer,1)实读返回1、值1；Common转新0146等待，无图不发键。|

初轮ABI错误是本worker新增观察代码的问题，未归因原固件。原user `Backup_read(key,buffer)`两参，`Backup_nread(key,buffer,n)`三参；原app getter2ebfd1c正是后者key/buffer/1。新版本与新候选保留旧run/helper，未改原API或把-1记成成功。`Backup_write(service,key,buffer)`成功实际返回字节数1，独立nread成功也返回1；目标是实际数据值0，不能将这些1归零。原字节证据在`runtime/backup99-user-ABI-proof.json`。

## 原生运行证据

两轮均实际见reason4 type2往返→软件CP clock提交→不发type4→原ready free0；普通reason1使用动态Q0x809061c2，原AP reply44/status0，clock generation2，再送原chip1 source的type4，原ready free0。原32B sync的原transport返回0、body s16 status0，原2f72498结果0、2f724b4 free结果0。boot option1经2b72520传1，原type5 daemon及两次Backup_write返回1，r2的原nread均返回1/值1。**这是boot强制设置保留force1，不是manual clear失败。**

新增native kthread使本轮pid/tid变化：im229、SeqQueueCommon424；验收按实际线程身份，不硬套AP98的pid228/tid427。r2的Common已经离开udate_wait_for_distribution_done，转在81cf61c3接收；AppFw368在futex。

原AP type2响应分配器未显式设置source，实际日志见a5a5a5a5；原CP49d090也不校验该source，consumer按本次专用动态Q、type2/status0和echoed embeddedQ校验，没有将未初始化header source臆定为809005c5。请求及type4的显式chip1 source始终909005c5。

## 首绘的新等待

完整原请求：destination92840747/source81cf61c3，10B `0d2046010a0001800100`（VDF0146，value1）。Common原用户栈 `2de7264 ← 2deaae0 ← 2dd01c0 ← 2d9e764 ← 2bd76fc ← 2f71ba0`，随后原osal_rcv_msg_tmo(queue81cf61c3)等待；UI AppFw futex，GPE0、OSD0、PNG0。fa controller init/presenter已返回只是创建证据，不算可见语言页。

无本轮PNG，因此没有宿主按键或后续manual sequence输入；2b725c8/2b72680/2b72684、force current/next0、两个原键0、backup-after-setup-v2.bin、待机/MENU均未验收，不借AP97-r2图补证。AP97-r2已经独立验收的历史菜单结果保留。

## 收尾与复核

r2请求600秒，实际601.093秒；QEMU0/reaped=True/PIDabsent=True，输入SHA全部一致=True，双锁free=True，assert=0/CP模型REJECT=0、GPE拒绝=0；missing=['FX3_GPE_SCOPE', 'FX3_OSD_FRAME_TARGET_VALID', 'FX3_GPE_DRAW_INTERVAL', 'const_alpha=']，early_stop=None。

最终原RAM键：{'force02cf0014': 1, 'force01070140': 1, 'date02cf01b4': 1}。完整600秒不等于UI/全部健康通过，strict health=False；CP日期往返通过与后续0146合同未闭分开记录。

完整原日志/LF、两轮QMP解码与readback结果：`runtime/ap99-runtime-evidence-v1.json`；0146精确原包与栈：`runtime/ap99r2cpdate600-9391e358-VDF0146-wait.json`。原件及完成run均不改写。

单调软件时基使用架构计数CNTVCT和频率CNTFRQ，[Arm官方说明](https://learn.arm.com/learning-paths/servers-and-cloud-computing/arm_pmu/assembly/)支持两寄存器换算方法；此处是VM软件时钟，不代表Sony CP或RTC精度。QMP取证沿用[QEMU官方文档](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html)。Sony私有type1/2/4及force/Backup语义来自本地固定原件和[日期服务审计](../../work/fx3-vm-20261101/lead-claude/audits/date-service-set/README.md)。
