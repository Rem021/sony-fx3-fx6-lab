# VDF0146 / Common 尾段与首绘等待审计

**0146 是触摸面板开关，捕获 ON=1 的精确成功回复为 `0d2046110c00018000005900`（1146/12B/status32=590000）。** 原 CP 的 `VdfInputCmdSetTouchPanel` **先确认旧1321，再下发设备f02f**；因此可提供明确的软件配置接受合同，不能宣称触摸硬件、显示或 live view 已完成。（AP `2d9e760→2dd0194→2deaa78`；CP `1a1b9c、5f5eba..5f5f62、5c9a06`；AP99 LF **14399–14414**。）

**首绘并未被证明在等待 Common 的0146；现有证据强指向另一个 Backup 同步完成门。** AppFw 三快照的 futex 地址 `7edbde4a88` 减本轮 app base `7ed2fb3000` = `8e31a88`，恰为原 `model_setting_value` 完成条件变量 **8e31a60+28**；原 pthread 的 PC `d5f0` 确在 `pthread_cond_wait`。同时 AppBackupDaemon 三快照均卡 `Backup_sync_all→backup_get_cp_data→osal_rcv_msg_tmo`。必须分别恢复 Common 配置与 Backup 数据同步，不能承诺只回1146就首绘。（AP `2b04674..2b0480c、2b2378c..23824`；pthread `d4d8..d5f0`；AP99 LF **21261、28644–28712、37642、44882–44950、54071、61314–61382**；因无 AppFw 用户LR，具体 wait 调用者仍为 B 强而非逐帧运行证明。）

2026-11-02，只读指定公共上下文、PLAN 最近记录、四份协议先例、原件与保存日志；仅写本目录 [audit_vdf0146.py](audit_vdf0146.py)、[vdf0146-proof.json](vdf0146-proof.json) 和本文。没有启动 QEMU、执行 CP、改 runtime/STATE/锁/原件、调用设备或做 Git 变更。A=原码/直接捕获，B=约束推断，U=未证实。AP 为 ELF VA，CP 为 Thumb VA（offset=VA−108000），backup.ko 是 **.text 相对偏移**（文件 offset 加68），pthread 文中范围 VA=文件 offset。serial 均按原始字节 LF 编号，保留CR/NUL；AP99/AP98 的完整路径见第7节。

## 1. AP sequence、字段、等待和失败

捕获 tid424/SeqQueueCommon 的原栈是 `2de7264←2deaae0←2dd01c0←2d9e764←2bd76fc←2f71ba0`。run **2d9e6c8** 的签名字符串 **3957340** 为 `virtual void model::sequence_set_touch_panel::run()`，源文件 **39572c9**；虚表 header **46f17d8**、run slot **46f17f8=2d9e6c8**，GOT **47977b8** 的原 RELATIVE addend 也绑定该表。注意 AP 第二 PT_LOAD 的 VA 比文件偏移大10000，不能把文件位置46e17f8当 VA。（proof.AP_vtable；AP99 LF **14399–14411**。）

run 比较 task+1b9（desired）与 +1ba（旧值），相同则直接返回；不同时依次：`set_touch_eventsw`（**2d9e72c**）、`vdf_set_touch_panel`（**2d9e760**）。ctor **2c4b004..171** 从 model getter2947d3c取得旧值，并按其他原条件计算desired；某些路径还更新 model102c。当前捕获直接证明 wire ON=1；task 内存、getter条件的当次读回未保存，不能把静态推导冒称捕获。（AP `2d9e708..768、2c4b040..16c`；字符串 **3957283/72a6/72ef/7314** 是两步各自 Success/Failure 日志。）

| 请求偏移 | 捕获 | 构造/消费证据 |
|---|---|---|
| 0..1 | `0d20` type200d | AP2deaa8c/aa98 |
| 2..3 | `4601` command0146 | AP2deaa9c/aaa0 |
| 4..5 | `0a00` length10 | AP2deaaa4/aaa8 |
| 6..7 | `0180` flags8001 | AP2deaaac/aab0 |
| 8 | `01` ON | AP2deaa80读u32输入，仅值1写byte1；CP1a1c00..32取开关 |
| 9 | `00` reserved | AP2deaa94先清半字；CP bridge仅读+8 |

整包 **`0d2046010a0001800100`**，目的92840747/source **81cf61c3**（仅本轮动态source，不能后续硬编码），AP99 LF **14411**。wrapper清零12B reply槽，以10B input/12B output调用 `send_and_wait_cmp_i@2de70a8`；`2de72fc` timeout−1，`2de7300` OSAL receive，无有限超时或重试。LF **14414**直接记同tid/queue开始收包，后三快照仍在原收包路径（LF **23737、39980、56410**）；后续唯一等待归属是 B 强，未保存跨时刻用户LR/队列正文。（AP `2deaabc..aaf4`；proof.task_snapshots。）

共同封装固定 memcpy12、free reply，未核收到的header/实际长度或receive返回；wrapper只取reply+8经 **2de4574** 转换。590000→本地0，590001→6a，−1→69；裸0也接受，但保真回复应保留590000。run非0走Failure/断言诊断、100000µs sleep、**2ebf3b0**，有返回收尾分支；其外部错误观察者是否终止程序U，不能从helper名断言必杀。缺回复时结果判断尚不可达。（AP `2de7304..7320、2de46c4..cc、2de47d0..dc、2d9e7b0..934`。）

先行 `set_touch_eventsw` **不是同步业务**：`2ddfb34→2eabe58` 构造807b002b/12B `[op1,length12,on1]` = `010000000c00000001000000`，`2eace78→2eacea0` 调 `osal_snd_msg` 后返回，**没有接收，不得补成功reply**。当前run已走到0146，故该先行调用的本地成功分支已通过；其设备效果U。（AP `2eabe58..ebc、2eabfc8、2eace78..cf14`；AP99 LF14411栈。）

## 2. CP 两级映射、类与处理时序

| 层 | 原表槽→目标/操作 |
|---|---|
| wire TBH base1aca08 | **1aca94→1acdfc**，写internal90，后经1ad050..70排队 |
| internal TBH base1ab6a6 | **1ab788→1ab978**，r1=0调用 **1a1b9c**；该桥接失败由1ab99c直接回5c9a06 |
| 旧回复解析 | **1ad9ca**识别1321→**1adaee**写internal28b→1adb84/1adbd4 |
| reply TBH base1ac4ce | **1ac59a→1ac67e→5c9a06**，使用internal90的原关联source |

脚本读原表半字重算所有目标，不凭相邻函数猜映射。bridge **1a1b9c** 构造旧 **2001/0321/12/1**；+8取wire开关，其余三字节先清0。本例旧包 `012021030c00010001000000`，发往9059000e、source928407b9。分配/发送失败返回−1，internal handler直接交完成器；这里不经过旧回复的590000 OR。（CP `1a1bac..bd0、1a1c00..74、1ab994..9a0`。）

`VdfInputCmdSetTouchPanel`：RTTI名称 **b3d660**、typeinfo **b7e594**、vtable **b7e57c**，ID/Activate/Execute **5f5e98 /5f5ea8 /5f5eba**。Activate只设置内部处理状态，没有字段范围校验；Execute读payload首字节，**≤1产生旧1321/status0，>1产生status1**，在 **5f5ee8** 调结果发送槽，然后 **5f5eec→5f5ef6** 构造内部 **2001/f02f/12/1** 并复制原4B payload，再经1e8298以selector1分发device。回复动作在设备动作之前，因此本命令的AP完成不依赖设备结果聚合。（CP `5f5eca..ef4、5f5f14..5f5f62`；proof完整窗口含IT块，孤立指令检查5f5ed8未携带IT状态，条件以完整块为准。）

`DevPanelCmdSetTouchPanel`：名称 **b3eb60**、typeinfo **b80768**、vtable **b80750**；ID/Activate/Execute **60765a /60766a /60767c**，ID=f02f。device先通过subsystem+7d0（槽 **b819dc→6103f7**）将开关存到 `[subsystem+20]+6fdc`。再由+e4（**b812f0→60ef4d**）取模式：模式1跳设备动作，否则将开关映射0/1，经60c658→5df21c可向905f05f2发op8/9，另60c736→60c760向 **91010227** 提交8B设置。selector1只命中路由表b81088的第一项mask9/queue90590819；该queue对应的物理显示器名称未证实。（CP `607694..6d4、6103f6..3fe、5df21c..258、60c736..81c、1e82b4..da`。）

**原接受链没有帧地址、sensor帧或live-view等待。** 真实device动作会依赖模式及输入设备服务，但不在AP确认之前；没有证据说“必须先有画面才能回0146”。同样，AP已收到1146也不证明触摸输入启用、触摸样本有效、LCD/GPE首绘或原CP运行。（以上CP顺序；本次仅保存AP请求LF14411，无CP运行。）

## 3. 精确回复与软件合同

旧1321进入2001状态转换器：**1adcc4**读旧+8，**1adcda/de** OR590000；**5c9a46**把传入status原样放新reply+8，**没有归零分支**。完成器写200d/1146/12/8001，经1aef1c投原关联source。（CP `1adbd4..ce4、5c9a24..4c、1aef1c..7c`。）

| 来源 | 精确AP回复 | 本地结果 |
|---|---|---|
| 原旧status0 / 软件配置接受外形 | **`0d2046110c00018000005900`** | 0 |
| 原Execute非法值status1 | `0d2046110c00018001005900` | 6a |
| bridge发送失败−1 | `0d2046110c000180ffffffff` | 69 |

不是SYS0400的裸0合同，也不是面板0119归零完成器；差异由本次原码独立重读证实。软件profile限定 `headless_touch_config`、完整捕获10B、92840747、本次source及唯一owned lease/generation；stage desired ON1，分配自己的12B reply，以metadata source92840747投**本次source**，仅send成功才commit/完成lease。失败回滚stage并free自有reply，保留原request所有权；原AP自然free已交付reply。保留 `pending_hardware=true, physical_touch_verified=false`，不造f02f完成、输入样本、sequence token或首绘ready。（语义依据CP5f5ee8先确认；运输依据1aef1c及AP2de7320；这是拟议纯软件合同，不是runtime实现。）

脚本验证21项拒绝且state不变：10个byte分别改变、截短/加长、错误目的、无source/source与lease不符、无ownership、错误profile、分配/发送失败、同generation重放、非法generation。**不同合法事务重复相同ON1可再次接受**，不能沿用旧“仅一次”的面板合同。脚本的数字generation是有限证明域，真实adapter仍需原allocation身份、并发锁及故障验收；不把Python state当真实guest状态。（proof.software_contract；原AP caller每次等待12B，2deaadc。）

## 4. 日期返回后、首次设置期间的同步请求：顺序与穷尽边界

**同一个run已穷尽；动态队列不能从函数地址静态复原。** 完整run **2d9e6c8..934** 的所有直接call保存在proof，Success尾段 **2d9e76c..7ac** 只有两次日志与return。dispatcher在run前 **2bd76c8→1724ccc** 已调用pthread_mutex_unlock；不能误认它持queue+28锁跨0146等待。run返回后才遍历task+158/+160完成观察者，再取下一queue节点。（AP `2bd76c0..7788、2bd1ecc..2028`。）

| 次序 / 范围 | 同步请求全集、精确回复或缺口 |
|---|---|
| 0：已完成boot force日期 | 80900141/32B原地sync，AP99 LF14294实际result0；随后option1 force设1（LF14306），两Backup_write返回1且读回1（LF14421–14427）。不是UI日期clear，也不能用另发12B成功包替代；原option1路径2b72754/2b72808。 |
| 1：本touch run先行 | 807b002b op1/12B，**no-wait，不补reply**；2d9e72c/2eacea0。 |
| 2：本touch run当前 | **0146/10B→1146/12B `0d2046110c00018000005900`**；2d9e760/2deaadc，LF14411。 |
| 3：同run成功尾段 | **空集，已闭合**；2d9e76c..7ac。失败尾段有诊断/error helper，外部错误处理U，不伪造业务reply。 |
| 4：task observers及后续Common各节点 | **数量、顺序、命令、输入和全部回复未闭合**；task+158/+160 callbacks、queue+10节点链/+20计数/+88活动项均未保存。不得把另一轮0400/0152或邻近touch-sensitivity当“下一条”。 |
| 与2并行：AppFw / Backup daemon门 | 原model设置同步→daemon type13/14→Backup_sync_subsystem(2cf)或Backup_sync_all→原kernel backup_get_cp_data。三快照证明已到该等待；ko .text2bd8传operation **30hex** 给11c0（并非长度48），CP source/chip/body/长度及精确回复 **未闭合**，不造0 ACK。它与0146没有可证的全局wire先后序。 |
| 后续UI手动日期task（条件） | 初次option0在2b72680调用80900141，普通option2在2b72988；仍要求原transport/status/free/model返回0、真实时钟分发，随后2b72684或2b7298c原成功链清force。实际queue位置和年月日/TD/DST不同，完整32B及后续请求 **未闭合**。详见[date-service-set](../date-service-set/README.md)。 |

该表是**已闭合集合+明确未闭合集合**，不是“首次设置所有服务已齐”。完成动态清单所需最小只读采集：当前queue指针及+10链/+20/+88；每node+10 task的vptr、task+8 ID、+10 handle、+1b8后原输入；task+158/+160 observers；Common每次run entry/return的task身份及同期真实同步request。当前日志只有return-address栈，没有这些对象数据，无法合理推导固定后继顺序。（AP2bd7688..76f8、2bd1f04..10；AP99 LF14399–14411。）

## 5. 为什么AP98可先画，AP99却没有首绘

**A：Common队列完成不是首绘的普遍前置条件。** AP98日期sync before在LF **14183**，全冻结日志未记录after；此后UI仍多次config（**14260、47637、75250**），实际GPE draw interval/native target在 **48111–48113**。既有Lead目视为语言页，本审计不重复声称目视检查PNG。AP99日期after在 **14294**，UI仅一次config（**14374–14378**），随后Common0146收包；在同一冻结范围没有native-target marker。marker有界/去重，缺行不等于全局无包，但三线程快照支持持续阻塞。（proof.runtime、task_snapshots、backup_daemon_snapshots。）

**B强：差别是日期返回让新的model变更/Backup同步门成为可达，而不是UI硬性等待touch sequence完成。** 原UI更新调用点 **2191754→27395e8→2739620→2b04738**，后者名为 `execute_sync_all_if_necessary`（字符串3908568），按原flag8e5dc38条件发daemon14并等待；另 `sync_and_wait_comp@2b04674`（3908530）发daemon13并等待。两者设置busy **8e29f20=1**，等CV **8e31a60**，daemon完成后 **2b237e4**清busy、**2b237f8** notify_one。原pthread **d54c..558**明确futex=condvar+28+group*4；本次等待地址精确匹配group0。这个地址对应完成CV，**不是一个可直接命名为“mutex被0146占有”的地址**。（AP以上VA、pthread d4d8..d5f0；AP99 AppFw syscall LF **21307、37688、54118**，其快照起点分别21261/37642/54071。）

同一时刻原 AppBackupDaemon tid528 在 CP数据同步收包三次不动，kernel返回点 **backup_get_cp_data+3c** 映射 `.text+2be4`，即第一次 `.text+2be0→11c0` 尚未返回；原第二次发送/backupfile_get_cp_data尚未越过。`Backup_sync_all+64` 对应 `.text+3074`。daemon type13/14/自动flush具体哪条未保存用户栈，不能仅凭kernel函数名指定上层command；但它确实没有走到原清busy/notify。**首绘解释已从“Common某sequence屏障”收紧到“原Backup完成CV及其真实同步任务”**，精确触发分支、CP body与完整完成语义仍待采证。（AP2b2378c..23824、2b22cc0；ko.text2ba8..2c50/3010..311c；AP99 LF **28693–28704、44932–44942、61364–61374**。）

这里不承诺0146与Backup互不影响所有后续业务，只证明当前有两个独立等待点，且UI保存的等待地址与Backup CV吻合；没有造新屏障、改timer/sleep、跳过busy或主动notify。AP98原日期停在force处理前，AP99则force写1/daemon启动是新增可达事实；“这一次UI确由上述哪个call进入wait”的最后用户栈缺口保留为B强。（AP99 LF14294/14306/14421–14427；AP98 LF14183；上述VA。）

## 6. 运行链验证点

1. 0146接收：冻结本次10B、tid/task/source/owned lease；stage软件ON1→独立reply1146/590000→原2de7320 free→2deaae4映射0→**2d9e764=0**→Success日志→2bd76fc返回。相同ON1的独立事务仍应逐次真实完成；无跨运行source硬编码。（AP上述VA；原请求LF14411。）
2. 同时采首绘门：在 **2191754、2739620、2b04674、2b04738、2b046f8/2b047cc、2b237f8** 保存caller/user栈、condition8e31a60、busy8e29f20、flag8e5dc38及daemoncommand；保留实际pthread基址/PC。先证明是哪个原wait，不能直接清busy或发notify。（原等待/完成VA；三AppFw快照。）
3. CP Backup同步：在原ko **.text2be0/2be4、11c0** 与现有唯一public owner捕获完整实际operation30报文、source/chip/动态Q、buffer extent/所有权和返回status；闭合原CP数据转移与AP导入/备份状态后才完成。当前合同未授权伪造一份CP snapshot或把AP bank当CP primary。（ko2ba8..2c50；三AppBackupDaemon快照。）
4. Common动态尾段：按第4节采queue/task/observer，在真实下一vtable的run逐项枚举同步，验证每条reply被消费并自然返回；首次设置日期走option0/2时看 **2b72684/2b7298c** 清force、两个Backup键独立读回0。option1写1不是clear失败。（AP2b72754/2b725c8/2b728f4；AP99 LF14421–14427。）
5. 最后分层验收：原Backup notify→UI wait return→后续config→GPE绘制/原帧导出；再输入→帧变化、日期force0、回放启动不重进设置。每一层保留原消费回执，不把1146字节或Python合同通过当菜单/持久化/实机完成。（AP2191754、2b237f8、2d9e764；原AP98 draw证据LF48111–48113。）

## 7. 重建、来源与未证实

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/vdf0146-common-tail/audit_vdf0146.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/vdf0146-common-tail/audit_vdf0146.py --check
```

第一条退出0重建proof，第二条重新提取逐字比较、不写文件。**76条指令断言、3处TBH、2类RTTI、AP GOT/RELA/vtable、同run完整调用集合、两冻结日志、6份UI/Common快照、3份Backup daemon快照、21项拒绝及独立重复事务接受**；不执行固件或先例脚本。只读查询例 `audit_vdf0146.py dis CP 5f5eba aa`、`dis AP 2b04738 d4`、`dis BK 2ba8 ec`、`dis PT d4d8 120`。（脚本CHECKS/BLOCKS与proof字段。）

| 原件/冻结输入 | SHA256 |
|---|---|
| appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| cpapp-b.bin | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` |
| 原libpthread-2.25.so | `7394f861930c45dd5076a700da5755faf0f6bed08544b0d60eadb85a14a7d592` |
| 原backup.ko | `8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d` |
| AP99前10468934B | `7d9e1c85022bd4b20926af19eabc32fd9e505fc4012bcc380befb431dcae36ea` |
| AP98前59304909B | `15fd1fb8118b5b229223aa1e2346b370745ba07efd022f606ef2f0ac7ea0179a` |

两日志分别为 `menu-repair-01/runtime/runs/ap99r2cpdate600-9391e358/serial.log` 与 `.../ap98datecapture600-b6f825f4/serial.log`；保存快照是 `runtime/ap99r2cpdate600-9391e358-no-frame-task-snapshots.json`，SHA另列proof.sources。读取原pthread作静态对照，**未新增actual guest.cpio内pthread身份逐字验收**；其模块相对PC由本轮捕获libpthread frame7020绑定运行基址推导，仍保留这项限定。（AP99 LF14407；proof sources/task_snapshots。）

明确未证实：原CP/device动态运行、真实触摸/显示/live view；实际1146消费及当前run自然返回；完整Common动态后继及第一次设置期间全部wire清单；AppFw用户栈确认具体Backup wait入口；CP Backup op30完整body/source/回复/数据传移和原notify；原持久化/文件save/回放以及本轮新菜单/实机验收。**静态审计通过不意味着这些缺口关闭。** 本轮联网核对[Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)（2026-11-02），仅支持工具用法；Sony私有语义均来自本文VA与冻结serial。
