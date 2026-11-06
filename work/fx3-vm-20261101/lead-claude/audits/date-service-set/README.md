# FX3 日期设置服务：AP97-r2 静态合同与等待点

**应补的是原 AP 时钟的跨芯片日期分发 consumer。原 AP `udate.ko` 已支持 set，也确实运行；AP97-r2 的 SeqQueueCommon 三次停在它的 distribution 完成信号量。** `0x80900141` 是 AP 原用户库注册的同步接口，它再调用 AP 内核 `0x0090013d`；不是直接发给 CP RTC 的命令。当前软件 CP public owner 接到 `0x909005c5` 后返回 0，却没有提供该分发协议的消费和完成通知，因此原 set 可以已经更新本地时钟，却一直不能返回。（用户库 `2ef4..3038、3eac..3ec8`；内核 `.text+668..6dc、c50..c88、17c8..184c、25f8..2714`；AP97 serial LF **1114–1115、26232–26235、54464–54467、81524–81527**。）

**必须更正前置审计的验收点：`2d7e6f4` 属于 remote 日期序列，不是 UI 的必经点。** 其 RTTI `394b880` 明确是 `model::sequence_set_date_time_by_remote`，vtable `46ee198` 指向 run `2d7e5dc`。UI 的日期提交走 `sequence_clock`，初次设置成功点是 **`2b72684`**，普通日期设置是 **`2b7298c`**；它们也会清 `1098`，随后走相同的 type5 daemon/Backup_write。因此本轮八个探针没有命中，不能单独推出“UI 日期序列没有排队”或“只有 remote return 才会清 force”。（AP `391d6a0、46e59f0、2b725c8..2738、2b728f4..2a5c、2b721b4..1fc、2b7250c..2570`；remote `2d7e5dc..7cc`；serial **8618、14137**，全日志 `FX3_DATE97_POINT` 数量为 0。）

## 范围、重建与证据身份

2026-11-02；完整阅读 COMMON-CONTEXT、PLAN 最近条目及 first-setup-persistence / first-screen-trigger 后，只读原 AP/CP、实际 guest.cpio、AP97-r2 日志与 Backup 导出。只写本目录 [audit_date_set.py](audit_date_set.py)、[date-set-proof.json](date-set-proof.json)、本 README；未改 runtime、STATE、锁、原件或设备，未启动 QEMU，未执行客体代码。A=原字节/保存运行直接事实，B=约束推断，U=未证实。AP/用户库地址是各自 ELF image VA；kernel 地址是 `udate.ko .text+offset`，**文件偏移须加 `0x68`，不是加载 VA**；CP 是 Thumb VA，文件偏移=VA−`108000`。（`proof.sources/code/guest_member_identity`。）

在项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/date-service-set/audit_date_set.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/date-service-set/audit_date_set.py --check
```

第一条退出 0 重建 proof，第二条独立提取并逐字比较、不写文件。脚本核卷 UUID、五份原 ELF/CP 字节、70 条指令、六组跳表、RTTI/vtable/GOT、actual cpio 内原模块与 helper 身份、serial 原 LF 行号、两 force 键。只读查询：`audit_date_set.py dis udate 2ef4 c8`、`dis udate.ko 25f8 11c`、`dis cp 49cc44 260`、`dis ap 2b725c8 170`。方法参考 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html)（2026-11-02 核对），它仅支持反汇编方法，Sony 私有语义来自本地固定原件。（`proof.instruction_checks/dispatch_tables`。）

| 核心输入 | SHA256 |
|---|---|
| appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| libosal_udate.so | `5a61d80cc95fbda9496bf3424c4a58fb77a3085f494e2401ba0eda91397a8df9` |
| udate.ko | `a3cbb9977915259a5a9d5e16e49adbb58f26c43d2ad2c63381c60e1103d205bb` |
| libosal_uipc.so | `09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3` |
| cpapp-b.bin | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` |
| AP97-r2 guest.cpio | `5dd10e134d8bd3a947d259f12269744fbef9361a8f94b61382ebae2e04cb52c7` |
| AP97-r2 serial.log | `3349b5c2a8d6da0485045328ec01fe30589c11a38e254bdb3701d15ec0f21c10` |
| AP97-r2 backup-after-setup.bin | `57982207d1a30964e2eb24764329b92267cca03d097839b5c6934e5b930edcd0` |

日志固定于 `runtime/runs/ap97r2alpha600-cd3c48f7/serial.log`，按字节 LF 分行，共 472721 个 segment（含末尾空项），不使用 `splitlines()`。既有 acceptance 把唯一 date 标记记作 LF14139；原字节重算为 **14137**，本文采用重算值。原记录为 `phase=before event=1 bytes=32 captured=0`，**没有 raw 正文、tid、pointer、caller 或 after**；不能称为“已捕获完整 32B 请求”。（`proof.serial_evidence/observer_limits/acceptance_selected`。）

## 1. UI 提交 → model sequence：两条不同路径

下表是原静态调用链；AP97 当次具体 UI controller、排队 task 身份与每条调用的运行命中仍需补探针。日期格式变体不能仅凭页面截图选定。（AP 下表 VA；serial **14137、26232–26235** 未保留用户栈。）

| 层 | 原实现与字段 | 证据 |
|---|---|---|
| UI 日期提交回调之一 | `23c16c4` 从六个日期/时间 getter 取值，`23c1744` 调 `27d3acc`；事件绑定由 `1b40880..89c` 设置 `4a09` 并装入 GOT `4737a68→23c16c4` | AP `23c16f8..1748、1b40880..89c`；这证明原 callback 连线，不证明 AP97 的实际事件命中 |
| UI model 入口 | `27d3acc` 日志事务 `1989` 包装 `27d38d0`；后者写模型日期字段，然后 `27d3a9c` 放 option0，`27d3aac` 调 `273e100` | AP `27d38d0..3ac8、27d3acc..3ba8` |
| 请求入队 | `273e158→271b130` 分配 0x70B model 请求：command=`63`，option 在 `+10`；model handler 表 `4029590→2717874` 再到 `2c390e8` | AP `273e100..1ac、271b130..184、2717874..89c` |
| sequence 创建 | `2c3911c→2c38d40` 分配/初始化 `sequence_clock`；从实际 model getters 拷贝年月日时分秒、TD/DST，option存 task+1b8；vptr经 GOT `47aa4c8` 绑定 | AP `2c38d40..e7c、2c390e8..9144`，RTTI `391d6a0`，run slot `46e59f0=2b73510` |
| 初次设置 option0 | run 跳表 `391d698` 的0槽 → `2b73548→2b725c8`；构造 native date+timezone，`2b72680→2f724ec` | AP `2b73510..35d8、2b725c8..2684` |
| 成功后 clear | **`2b72684` 非0跳失败**；成功时 `2b721b4` 建1098事务，`2b726b8` 传0给 `2b72520`，该函数写 current/next；`2b7250c` 通知；同样将187设0 | AP `2b726a0..270c、2b72168..1fc、2b7250c..25c4` |
| 普通 option2 | run → `2b728f4`，日期无timezone版本 `2b72988→2f724f0`，成功点 **2b7298c** 后走同样的force/date清零 | AP `2b728f4..2a5c` |
| remote 旁支 | `sequence_set_date_time_by_remote` 的 `2d7e630/6f0` 也调相同服务，**2d7e6f4** 收返回，0才clear；它不是前述 UI run | AP `394b880、46ee198、2d7e5dc..7cc` |

**B 强：当前早期挂住的请求很可能是 boot 排入的 option1 force-setting，后来的 UI 请求排在它之后。** boot 在 `2380590→276de54→276de30` 排 option1，run 到 `2b72754`，通过原 `2f7251c` 取初始日期后在 `2b72808` set；成功后该分支还会把1098设 **1**，与 UI option0/2 成功清0不同。AP97 的 before 标记在首次 fa controller 初始化期间，三轮是同一 SeqQueueCommon 的 set 栈，符合这条解释；但没有保存其 task+1b8、用户 LR 或32B正文，不能升级为逐指令运行因果证明。（AP `2380580..598、276de30..de50、276de54..decc、2b7357c..580、2b72754..28f0`；serial **14086、14137、14155、26232–26235**。）

## 2. 谁接收 0x80900141、请求逐字节布局及同步等待

**A：AP 用户库有原 handler，不需要新建一个同 ID 服务。** `udate_open_uif@2fbc` 向原 OSAL 注册 `00900141→2ef4`（另注册 lock 接口0090013e）；`2ef4` 按 request 的 s16 op 分派，结果原地写 request+2。op0→`udate_set_date(...,w3=0)`；op4→同函数 w3=1，后者才追加用户层 type5 分发及 Backup_sync_subsystem(90)。op1/5为async变体，op2/3拒绝。`osal_snd_sync_msg` 不是另收一条 BB/VDF 回复，而是在原调用返回前一直保留本次 allocation；内核/用户回调完成后原调用者读取同一块状态并 free。（用户库 `2ef4..2fb8、2fbc..3038、3ef4..3f10`；OSAL `6458..6460、61e8..6348、6390..63ac、3a98..3bd4`；AP `2f72494..4c8`。）

原 AP builder 分配 **32B** 到 `80900141`；所有偏移均相对于消息 body，**不含 OSAL 私有头**：（AP `2f72354..24e8`；用户库 `2f2c..2f5c`。）

| 偏移 | 大小 | 值 / 语义 |
|---|---:|---|
| 00–01 | 2 | s16 op=0，同步 set |
| 02–03 | 2 | s16 status，初值0；handler写真实结果 |
| 04–05 | 2 | 年 u16 LE |
| 06 /07 | 各1 | 月 / 日 |
| 08 /09 /0a | 各1 | 时 / 分 / 秒 |
| 0b | 1 | datetime 保留，AP临时结构清0 |
| 0c–0d | 2 | 毫秒；用户handler在set前强制置0 |
| 0e–0f | 2 | datetime 保留，AP临时结构清0 |
| 10 | 1 | native时间类型：0 civil/local、1 running UTC、2未设、3表示无date指针 |
| 11–13 | 3 | datetime 保留，AP临时结构清0 |
| 14–15 | 2 | TD分钟 s16 LE |
| 16–17 | 2 | DST分钟 s16 LE |
| 18–19 | 2 | timezone有效判别；0有效，1表示无timezone指针 |
| 1a–1b | 2 | timezone结构保留；来自原8B拷贝，不另猜字段意义 |
| 1c–1d | 2 | reason/fact=1，原app wrapper固定 |
| 1e–1f | 2 | 尾部保留；builder **没有显式初始化**，不能以全0冻结白名单 |

若只有timezone，builder写type3；若只有date，写timezone判别1。实际 year/TD/DST 取本次模型，**本轮没有保存 wire32B，不能给它补一份“实捕2021/540”正文**。proof 的32B示例逐字节列出，仅为静态schema示例，保留位人为清0并显式标注非实捕。（AP `2f72464..4e8`；`proof.ABI.static_example_only`。）

AP 同步返回值先取 transport；transport0才读 message+2 的 signed16；之后原 free 也可能决定错误结果，最终经 `2f71fa0` 归一化到 model error。**成功要求观察 transport0、status0、free结果及归一化结果0，不能只回一个另分配的12B成功包。** 原代码还把特定 `-1018` 结果归0、分配失败分支本身也返回0，故记录真实服务及分配/free更有必要；不要拿这些错误兼容分支当软件后端的实现方案。（AP `2f72448..454、2f72494..4c8、2f71fa0..1ffc`。）

用户库 `udate_set_date@3f64` 会取原 Backup 的日期下限、检查年份/TD/DST、等待原 mutex语义的sem `009082e8`，并向 middleware请求资源。资源取得可能等 `009082e9` 1000ms；no-resource分支可直接到 `udate_set_date_nr@3c44`。后者校验锁/时间状态后发 **48B direct** 到内核 `0090013d`：direct前缀16B，op+10、status+12、date+14、timezone+24、reason+2c（均十六进制偏移）。成功状态仍是原地 s16=0。AP97 的实际阻断已到其下方内核分发等待，因此不能把 `udate_set_resource` 的 NODEV 警告当作本轮尚未越过的唯一门。（用户库 `3f64..4210、3c44..3f10`；内核 `.text+15a8..1760、17c8..184c`；serial **14146、26232–26235**。）

## 3. 原 set 的真实工作，以及 BY_BOOT 为何不能代替普通 set

**A：原 set 先更新内核运行时钟，再等待分发完成。** `.text+a28` 验证date type≤2、timezone reserved+4=0、TD/DST各在[-1440,1440]或7fff sentinel，reason1/2走 `.text+c50/cdc`，必要时将civil减 `(TD+DST)*60000` 变UTC（`.text+258`），可向本地 `00900140` 请求资源RTC set。资源不存在 `-1020` 时原实现有明确忽略路径，不能捏造真实RTC已写。（内核 `.text+a28..ad0、b10..b78、c50..c88、cdc..cfc、258..2d4、308..418`。）

共同 commit helper `.text+668` 在 `.text+6ac→0` 写真实date16B、单调时基+10及timezone8B到原内核clock backing，保存前后localtime并发通知；`.text+6cc` 发 distribution ready，`.text+6d8` 才 wait。`udate_get_localtime` 原生按 UTC base + monotonic elapsed + TD/DST 返回当前civil。软件合同应保留此状态与进位，不应只改一个“已设置”位。（内核 `.text+0..f8、450..654、668..6ec`。）

**A：seed-date-clock-v3 调的是这个现成的原内核服务，reason=4/BY_BOOT。** 实际 cpio 的 `usr/kmod/udate.ko` 与本次原件逐字节相同，`libosal_udate.so` 也一致；seed原API读冷态type3、原默认2021-01-01/TD540，转UTC后op0/reason4，再延时读回两秒进位。BY_BOOT 的原 `udate_wait_for_distribution_done` / `done_notified` 在reason4直接跳过，CP也在reason4不发type4；所以seed成功、date187变0都不能证明普通UI set的分发完成。（seed源码 `set16(+44,4)`；kernel `.text+2600..2614、26b0..26c8、2748..275c`；CP `49cd86..cd8e`；serial **1105–1123**；`proof.guest_member_identity`。）

## 4. 真正缺的 CP 日期分发协议

**A：AP kernel有跨芯片分发线程与peer slot。** 原 `.data+1b8` 两个8B槽为 `(chip0,sem0)、(chip1,sem0)`；发送时跳chip0，chip1目的为 `809005c5 | 1<<28 = 909005c5`。发送ready前分配动态sem并先wait一次，把计数降到0；调用者随后在这个sem上timeout=-1等待，type4到达才sig。不是固定timer延迟，也不是给UI发完成事件。（内核 `.text+2390..24d8、25f8..26ac、2740..27c4`；`proof.kernel_initial_distribution_peers`。）

分发 **44B** body逐字节区间如下。type1/4未读字段不可当作必须为0的原协议约束；只在软件自身新分配的回复中清零以避免未初始化数据。（kernel `.text+2448..2480、1b98..1c0c、1df0..1dfc`；CP `49cd04..cd2e、49cdd0..cde8、49cf24..cfb0`。）

| 偏移 | 大小 | 语义 |
|---|---:|---|
| 00–03 | 4 | type：1 ready、2 get clock、3原Backup标志处理、4 done、5 Backup sync、6退出 |
| 04–07 | 4 | type2回复的 s32 result；0成功 |
| 08–0b | 4 | 是否需要回复；CP的type2请求=1 |
| 0c–0f | 4 | 本次动态回复Q；不可替代source/chip身份 |
| 10–1f | 16 | type2回复中的native datetime |
| 20–27 | 8 | type2回复中的native timezone |
| 28–29 | 2 | reason/fact；type4必须对应本次ready |
| 2a–2b | 2 | padding；AP done handler不读 |

原 CP 各步骤可独立从本机cpapp还原，**没有使用其他机型地址**：（CP以下VA；kernel对端见表。）

1. CP原线程 `49cc44` 收自己的 `009005c5`，读取真实message source。跳表 `49ce5e` 的type1→`49ce8c→49cc80`，读取原request+28 reason，分配44B发回**本次source**。它没有把ready包中的零date当作新时钟。（CP `49cc44..cc9a、49ce28..ce8e`。）
2. 构造type2/44B，+8=1；`49d090` 申请实际动态Q、在+0c写Q，`osal_set_msg_src`显式写 `909005c5`。调用 `49d090` 的receive timeout=-1，等 AP type2响应；响应的+4必须0。（CP `49cd04..cd34、49d090..d1a2`。）
3. AP分发线程type2→`.text+1e40`，`udate_get_localtime(+10,+20,1)` 写本次当前date/timezone，status写+4；若+8非0，`.text+1b98` **复制44B**回embedded+0c的Q。不是在 `80900141` 上补响应。（kernel `.text+1d00..1e8c、1b98..1bfc`，跳表 `.rodata+128`。）
4. CP取响应date/timezone，以 `a864f6` 更新真实CP软件时钟：civil转UTC（`a86288`），再将16B UTC base、原单调时基与timezone存 `00ef50e0`（`a8638a..c6`）；这里调用的是原CP功能，**本VM并未运行它**。拟议软件consumer需有自己的等价状态与读回，不可声称写了该CP地址或真实RTC。（CP `49cd68..cd82、a864f6..a8656e、a86288..a862f8、a8638a..a86432`。）
5. reason!=4时，CP另分配44B，显式source=`909005c5`，写type4、+28原reason，目的仍为**本次AP source**。原type4 **没有“status0”字段校验**，也不带新的generation token；reason4跳过这步。不能把静态type4的42个未读字节当原厂成功载荷。（CP `49cd86..cd8e、49cdaa..cde8`。）
6. AP收到type4，`.text+1df0` 取+28 reason及 `source>>28 &7` chipID；`udate_distribution_done_notified@2740` 对匹配peer的非0sem sig，原wait返回并释放sem，kernel/user/AP各层才自然返回0。（kernel `.text+1df0..1dfc、2740..27c4、25f8..26ac`。）

**A运行事实：当前 CP public owner 没有做以上消费。** actual init加载 `fx3-cp-backup-reset-v1.ko`，其binary与本地helper SHA一致；`cp_reset_send` 对非 `903e0811/op33` 的消息只记录后返回0。boot确实记录 `909005c5 / source809005c5 / logical_bytes44 / captured40 / no_reply1 / no_free1`；日志只保存了type1和前40B，**缺+28 reason及最后padding**。unknown日志有数量上限，后面没有同类记录不等于没发，不能由此数出UI轮次。（init **89**；serial **1114–1115**；helper `fx3-cp-backup-reset-v1.c:16–19、44–45`；`proof.guest_init_lines/guest_member_identity`。）

## 5. AP97-r2 的精确阻塞位置与证据等级

| 保存栈文本 | 原件真实返回点 | 含义 |
|---|---|---|
| `udate_wait_for_distribution_done+74` | `.text+266c` | `osal_wai_sem_tmo(...,-1)` 刚返回的位置，当前在它内部睡眠 |
| `udate_get_localtime+28c/2a0` | `.text+6dc` | **匿名commit helper** 在wait后的返回；不是get-localtime函数本身卡住 |
| `udate_set_date+260/488` | `.text+c88` | reason1/2正常set分支调用上述helper之后 |
| `udate_proc_read_clock+4a0/648` | `.text+1620` | **匿名direct回调** 调set之后，还未写message status |

这些函数名由原模块 kallsyms 的前一个可见符号解释，因此显示size可大于ELF `st_size`，不表示 guest用了另一份打补丁的udate。脚本实际解开guest.cpio并与原ko逐字节比较，且 `.text+266c、6dc、c88、1620` 与三次栈完全对应。该栈在 `FX3_TASK_SNAPSHOT_427_BEGIN` 区域，task是 SeqQueueCommon；内核下方还有原OSAL同步 ioctl。**A：线程当时等待分发完成；B强：该等待使原date sync没有after、后续UI sequence排队；U：确切peer sem值、32B原正文和user task/run。**（serial **26174–26248、26232–26244、54464–54467、81524–81527**；`proof.runtime_stack_mapping`。）

原 `udate_set_resource` 警告只说明本地RTC resource接口不存在且原函数按NODEV忽略；当前栈已越过它到真实clock commit之后。应修已证实的distribution等待，不能先加“AP时钟模块缺set”的旁路。原模型在VM的实际状态为：**AP kernel/user udate存在且支持set；seed仅初始化；CP日期分发消费者缺失**，未证真实AP/CP RTC设备。（kernel `.text+308..418、6ac..6d8、c84..c88`；serial **1105–1123、14146、26232–26235**。）

## 6. 最小诚实软件合同（建议，未实现/运行）

1. **沿用原AP时钟set/get及已有唯一public owner。** 在现有 `cp_reset_send` 的目的分派增加 `909005c5`，不要再注册第二个public owner、截断原set、直接清force或改checksum。原set已经提交真实虚拟UTC基值/时基/TD/DST；恢复其真实等待即可。（kernel `.text+0..48、668..6d8`；helper `cp_reset_send`；serial **26232–26235**。）
2. **接受与处理要分开生命周期。** 对完整44B、本次source/reason建立有界记录，按实际OSAL allocation/source/accounting处理所有权；public send回调内不能重入阻塞等待自己驱动的分发链。用可串行消费的现有服务线程/延后工作处理type1→type2握手，保留事务身份到结束；重复/并发/队列满必须拒绝或明确失败，不能重复发done。（kernel `.text+2390..24d8、2664..269c`；CP `49d090..d1a2`；原CP owner 当前 `return0/no_free` 是缺口事实，不是正确所有权模板。）
3. **真实远端软件clock后才完成。** 从原AP type2取date/timezone/status，校验合法civil、范围、reserved/类型后转换UTC，记录原monotonic时基、TD/DST、generation和读回；软件remote读值应随时间进位并与AP允许的时间差相符。失败、未知type、未捕获reason或不支持profile不发成功；不把原RTC NODEV说成RTC写成功。（CP `49cd30..cd82、a86288..a86432`；AP原get `.text+450..654`。）
4. **只在本次remote clock已提交且读回后回type4。** reason!=4时另分配44B，source909005c5，目的取本次AP source，写type4与echo reason；未读slack显式清零并标“软件差异”，不修改原请求、不以status0伪包代替。动态Q只服务type2回复，不能拿固定Q/固定source或固定540/2021来凑。reason4保留原特例，不发type4；type2/3/5只在同一受限software语义下支持，否则拒绝。（CP `49cd86..cde8、49cf24..cfaa`；kernel `.text+1df0..1df8、2740..27c4`。）
5. **让原业务自己提交1098与Backup。** 初次设置看 `2b72684`，普通日期看 `2b7298c`，只有实际选remote时才看 `2d7e6f4`。随后原model通知→回调 `2a69a68`→`2ab9028` type5→daemon `2b23730`→`2ebfd30`，原 `Backup_write` 分别写 **02cf0014 /01070140**；成功大小应各为1，并由原Backup读取接口读回0。本轮导出两个键仍01（offset8eb51/6e7ac），日期02cf01b4已经00（offset9100c），不能用日期状态代替force。（AP上述VA及 `2ebfd40..6c`；`proof.backup_keys`。）

**合同不是已实现回执。** 当前可证明无physicalRTC、无running CP，也没有新consumer的线程/内存/所有权验证；以上类型及回复来源均从原发送/接收路径推导，具体动态Q、完整44B reason、peer sem及分配capacity仍需运行链先捕获。若选择更小的“直接模拟AP set”合同，也必须实际更新原AP clock并保持原分发/通知/锁语义；直接在80900141回0会漏掉当前已经卡住的原set线程，不能作为本轮首选。（kernel `.text+c84..c88、2664`；serial **14137、26232–26235**。）

## 7. 交给运行链的验证点

| 阶段 | 被动观测点 | 验收 |
|---|---|---|
| UI提交/排队 | AP `23c1744、27d3aac、273e158、2c38d70` | 同task/command63/option和实际年月日时分秒/TD/DST；排队与进入run分别保存 |
| 原日期sequence | AP `2b73510、2b72680/684、2b72808/80c、2b72988/98c` | 区分option0、1、2；**option1成功设force1**，不可误判为clear失败 |
| 用户接口 | AP `2f72494/498`，user `2ef4、2f5c、3eb8/3ebc` | 原caller/tid、实际32B before/after、transport/status/free；池内peek失败不能伪称捕获，需原有效读租约/可达内存机制 |
| 本地clock commit | kernel `.text+6ac、0..48、6d8` | 原set先提交；op2真实读回新civil/TD/DST并随monotonic进位 |
| 远端分发 | owner收完整44B `909005c5`；kernel `.text+249c、24cc` | 捕获reason+28、source、实际allocation/canary、动态peer sem；不再只打印前40B |
| type2取clock | CP模型发送→AP `.text+1e40..1e78`，原embeddedQ响应 | Q与source各归其位，type2/status0，date/timezone源自本次原AP；无猜测常量 |
| type4完成 | 模型remote clock commit/readback→AP `.text+1df0、27b8、266c` | source chip1匹配本次peer、reason正确、恰好一次sig；wait真实返回 |
| 原成功链 | kernel `.text+1624`→user `3ec4/2f5c`→AP `2f72498`→manual成功点 | 原status0、原free完成、model return0；remote点只作旁支 |
| force与持久化 | AP `2b72554/55c、2a69a84、2ab9028、2b23730、2ebfd5c/70` | current/next1098=0；type5真实消费；两个原Backup_write各返回1，再独立原读回0 |
| 重放/重启 | 记录新Backup RAM bytes和SHA，再按既有时机回放 | force两键0、date实际已设、boot `2380464` 不再因force选首次设置；UI/menu另验 |

RAM导出与有效文件持久化分开：当前 `Backup_load=1 Backup_save=0`，本任务只证明RAM键值，尚无原daemon drain/磁盘save/checksum/count/cookie/下一次文件加载成功回执。修复后应先验原日期和force两键，再做原有RAM回放；不能把新导出改名为“原正常关机持久化完成”。（init **102**；前置持久化审计绑定的backup `.text+3010..311c、6800..6a60`；本proof的 `backup_keys`。）

**仍未证实：** AP97 具体UI日期controller/command命中、当前早期task的option和32B、完整44B的reason/peer sem、原CP队列注册运行、拟议consumer实现及原wait解除、手动成功0/force0/type5写0、文件持久化与连续开机、RTC/实机精度。脚本PASS表示本审计原字节与冻结运行事实可重建，不表示日期修复或VM运行验收通过。（对应上表VA、serial **14137、26232–26235** 与 `proof.unproven`。）
