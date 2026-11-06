# FX3 显示目标、铰链与 AP85r4 停绘审计

**部分闭合：`0x243=2` 不能证明 VM 当前处于 `REVERSE_CLOSE`。** `0x243` 是方向枚举，`0x270` 才是 `panel_vali_angle_status`；原函数把 `REVERSE_CLOSE`、`REVERSE_OPEN`、`VALI_ANGLE`、部分侧开/低角状态都映射为方向2。原始 cache 未初始化的具体反例是四键全0→类别7 `VALI_ANGLE`→方向2，并非类别2 `REVERSE_CLOSE`。因此暂不据 enum2 改铰链，也不以它宣布 LCD 被关闭。（AP `2823890..2824118、2763048、2823ba4、2823d68、2823ecc`；AP85r4 serial **20781、20818** 只捕获方向，不含类别。）

**存在真实显示关闭策略，但其本次运行身份未闭合。** 原 `27ed7f4` 会把类别2/9、当前 `MONITOR=1` 改为 `NONE=2`；这支持 `REVERSE_CLOSE` 在原厂显示策略中代表朝内、不可见的闭合姿态。**物理朝向解释为 B 级强推断**，没有铰链实测或原机传感器角度 oracle；“朝内”不能仅凭英文 REVERSE 推导为 A 级机械事实。AP85r4 早期实际 0118 请求反而是 panel1/evf0，后来的当前显示目标、Widget 树/dirty 未保存，尚不能认定停绘由 LCD 可见性引起。（AP `27ed844..27ed888、27d776c..27d7850`；CP `1a8a90..1a8b0e`；serial **18671**。）

**0x400 是 SYS timecode TCMODE，同步阻塞 SeqQueueCommon，不能叫 LCD 初始化。** UI1360次更新、OSD1358次完成仍只有清屏/Flush与1005复用像素；两种候选——显示目标/Widget 可见性，以及被 SYS0400 阻塞的后续 sequence/observer——均缺完整动态因果边，不能选一个当已证根因。（AP `3960c90、2dcae38、2df26bc、2de72fc`；serial **21793–21809、21939–21973、59893、63282**；原 RAM 计数见下文。）

本轮只读原 AP/Obj/CP/input.ko、同型号模板与冻结 AP85r4，**未启动 QEMU、未改 runtime/STATE/运行锁、未写原件、未操作设备、未运行其他审计的 rebuild**；只写本目录三个文件。A=原字节/冻结运行直接证据，B=受约束推断，U=未证实。AP/Obj 为 ELF image VA；CP 文件偏移=VA−108000；input.ko 为 ET_REL `.text+偏移`；Backup 均为文件偏移。

## 重建与证据身份

项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/display-target-hinge/audit_display_target.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/display-target-hinge/audit_display_target.py --check
```

第一条退出0重建 [display-target-proof.json](display-target-proof.json)，第二条独立提取后逐字比较、不写文件。[脚本](audit_display_target.py) 核卷 UUID、原件 SHA、32项指令断言、AP/Obj/CP连续字节及原 input.ko 段、128组静态分支组合、原模板键/物理配置、日志 LF 行和双 bank 原 RAM；不执行 ARM/Thumb 指令。命令 `dis ap 2823890 88c`、`xref ap 293285c`、`strings ap 'panel'` 为只读辅助；xref是局部 A64 branch/ADRP+ADD 搜索，不是完整数据流证明。

| 输入 | SHA256 |
|---|---|
| appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| libObj.so | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |
| cpapp-b.bin | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` |
| 原 input.ko | `d9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057` |
| CX95900_ALLLANG Backup 模板 | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` |
| AP85r4 serial.log | `c493986a68c7dc4d8f05e24167c9eee3808e99a2087a01d92f370921b7306d8e` |

proof 的 `sources` 保存完整真实路径及本轮其他输入哈希。serial 指 `menu-repair-01/runtime/runs/ap85r4osdring-5dcb8371/serial.log`，行号按 LF 计数而非将 CR 当换行。前审计 [panel-reverse-enum2](../panel-reverse-enum2/README.md)、[post-clear-idle](../post-clear-idle/README.md)、[osd-completion-6003](../osd-completion-6003/README.md) 均已完整阅读；本轮结论重新读原字节，不继承旧“方向2必为闭合”的扩大解释。

## 1. 方向243与面板类别270必须分开

`28254cc` 初始化读取五个物理键缓存，写 `d72..d76`，再调 `2823890`。该函数读取 V/H/C/S/hinge 后，经 `2763020→282383c` 写 **类别270**，再在 `2823ba4..2823bbc` 写 **方向243**。对应getter：`293285c→822c9f4`、`2932154→822c71c`；启动构造器 `2c210f8..1100` 仅快照后者到 sequence+304。字符串注册 `41783a0..41783b0` 明确270名为 `panel_vali_angle_status`，不能把243称为同一个类别。（以上全部 A 静态；完整raw在proof。）

文件初值 model index=`8 @47ce0a8`，原getter `16f0ca8` 读表 `2f99ce0`，该槽为类型2；**这不是当前 VM 内存采样，未排除后续写者**。按该类型，V/H/C/S 的代表分支如下；128组 proof 还独立覆盖类型0..3与hinge两值，previous方向取0。LOW_ANGLE的保持旧方向规则仍见原 `2823b6c..b7c`。（AP `16f0ca8..0cbc、2823c28..3ed0`。）

| V/H/C/S | 类别270 | 方向243 | 原码 |
|---|---|---:|---|
| 1/0/1/0 | 0 NORMAL_CLOSE | 0 | `2823c28..c5c→2823f90..fac` |
| 1/0/0/0 | 1 NORMAL_OPEN | 0 | `2823c60..c90→2823ce4..d0c` |
| 0/0/1/1 | 2 REVERSE_CLOSE | 2 | `2823c94..cd0→2823acc..b24` |
| 0/0/0/1 | 3 REVERSE_OPEN | 2 | `2823d10..d6c` |
| 0/0/0/0 | 7 VALI_ANGLE | 2 | `2823e70..ed0` |

**正常展开位置有原输入表达式，不需要硬写243。** 若明确把虚拟面板定义为 NORMAL_OPEN，可由原输入四键提供 V1/H0/C0/S0，类别和方向自然更新为1/0；这只是规定的软件姿态，不是声称真实相机上电必处于此位置。当前 enum2 可以来自多种状态，故原 Lead“不为凑enum0擅改铰链”的决策仍适用。（AP上述表及 `2823b80..bbc`。）

## 2. 输入来源、未初始化缺省与 VM 缺口

启动路径明确是 **原物理输入cache→模型参数→类别270/方向243**，没有在该初始化函数直接读 Backup243，也没有从0119回包生成铰链状态：`28254f8/5538/5578/55b8/55f8` 调 `275f9f4`；后者经 `16ef200→InfraInput::GetPhyKeyStatusCache @Objc9c08`。UI键先按 AP表 `2f8f8d8` 转 InfraInput码。原模板的逻辑行 `0x587f0/58820/58850/58880/58970` 绑定 source `00410025`。（AP `16ee3b8..3f0、16ef260..27c`；Obj `c9bb4..c9c58`。）

**下表是更正后的准确映射：close与horizontal不共享bit。** `0x01120000` 同型号模板 record1 GPIO 类别2的四行如下；record0和record1须区分，这些文件行不等于当前Backup driver已选该record的运行回执。（原64B raw、logical48B raw与 AP配对表均保存在proof；input.ko `.text+1f74..1f80` 从配置取bank/bit后调用GPIO读接口。）

| 状态 | UI键 | InfraInput码 | record1 GPIO / active_level | 模板文件偏移 |
|---|---:|---:|---|---|
| close | 1bb | 71c3 | bank7 / bit21 / 1 | `13d1cc` |
| vertical | 1bc | 71c4 | bank7 / bit19 / 1 | `13d0cc` |
| horizontal | 1bd | 71c5 | bank7 / bit18 / 1 | `13d04c` |
| sideway | 1be | 71c6 | bank7 / bit20 / 1 | `13d14c` |
| hinge detect | 1bf | 71cb | 这两份1120000表中无该行，来源U | logical `58970` |

这闭合了四个角度信号的**原配置逻辑来源**，不等于证明它们全部经某一SysCon器件/CP前端：原 input.ko 可以直接读GPIO并发送，CP也存在同型发送器 `49b8c8..49b94a`。PCB实际连线、SysCon/CP电气链、hinge71cb的最终来源仍U。原input发送使用OSAL20B，libObj `cb640..cbb60` 接 `807a0020` 再更新状态；不是Linux evdev键码。AP85r4 `I-InputRecv`确实在等此队列（serial **1970**），这只证明接收者存在。

原 cache构造先清零再把每条 status 写 `7fffffff`（Obj `c8850..88a0`）；`GetPhyKeyStatusCache`读 row+8；`275f9f4` 对无效状态范围经 `16ef284..29c` 判失败后，将返回两个word归零（`275fa34`）。因此“没有收到铰链初始化事件→cache哨兵→模型四键0→VALI_ANGLE/enum2”是**有原码的 B 级具体候选**，不是任意猜测缺省2。（原分支表全0反例见第1节。）

243也有其他写者，例如 `29810d0..2981168` 从参数map恢复当前/下一槽；本轮没有当前map或最终写者时间线，不能把所有243值都归因于上述cache初始化，更不能宣称它绝不经持久化恢复。该备选路径与未采到的活动Backup record一起保留U。（AP `29810d0..2981168`；本轮proof保存原字节。）

现有 `fx3_gpio_bank5.c:1–19` 明言不提供输入，input寄存器读被拒；它不是bank7铰链模型。AP85r4 launcher `init-reviewed.sh:59–84、156–192` 显式插入的模块中没有 input.ko；但本轮没有完整追踪所有后续加载者，不能将此升级成“绝无其他生产者”。**当前cache内容、d72..d76、类别270、实际模板record选择均无保存采样**，所以“具体哪个缺省/模型已导致本轮 REVERSE_CLOSE”的题设尚不能成立；不可把该候选写成 A 级运行根因。（原动态已知仅 serial **20781/20818** 的方向2。）

## 3. 原厂显示选择、LCD关闭与 EVF 边界

`model::get_active_display(bool) @27d74a8` 读取模式限制、finder/monitor设定、**eye_contact_state2f0**、**panel_tilt_state2ec**、类别270等。`27d7794..77b0` 用 mask `7ba` 作类别判定，随后日志分支原名为 Enable LCD / Enable EVF / No Display；**不要将eye_contact_state错称为EVF存在标志**。人工finder/monitor设置还走其他分支，所以不能把一个mask当全机型硬件存在表。（AP `27d74a8..27d78f4`；参数注册 `4178f40、4178fa0`；字符串 `379b0c7/0db/0ef`。）

其后 `27ed7f4` 更新真实 active display参数d22：如果类别是2或9，且计算/保留结果是MONITOR1，则改成NONE2，再由 `276503c→27bd074` 写参数并通知。原枚举名称表 `41381d0/1d8/1e0` 精确对应 **0 EVF / 1 MONITOR / 2 NONE**。NORMAL_CLOSE类别0没有该关闭特例，REVERSE_CLOSE类别2有，这是“REVERSE_CLOSE为不可见闭合、NORMAL_CLOSE为另一个可见闭合方向”的软件语义依据，物理朝内/朝外仍按B级表述。（AP `27ed844..898、2765064、27bd09c..0b8`。）

`sequence_display_setup::run @2b8bb30` 取sel、disp mode、monitor off，monitor off组合会把发送sel改为2；随后 `2b8bc50→2df3d08` 构造0118，+9为panel、+10为evf。**早期 AP85r4 serial18671 原22B是 `0d201801160001800301000000000000000000000100`，即mask3/panel1/evf0**，说明至少这个捕获并没有请求LCD关闭。它是no-wait提交，不是物理LCD已亮回执，也不能代替稍后d22/Widget状态；观察器去重/容量有限，不能从仅一条可见请求断言后面没有状态变化。（AP `2b8bbb0..bbf4、2df3e4c..e58、2df3f54..f98`；CP `1a8ab6、1a8ae6`。）

**FX3无内置EVF是已核实的官方机型事实；本轮未恢复出原固件完整物理设备存在描述符。** [Sony官方Cinema文章（2021-03-22）](https://sony-cinematography.com/articles/the-sony-fx3---what-s-it-all-about--a-brief-review-by-alister-chapman/) 明确说明去掉EVF，并说明LCD可翻开转向前方；2026-11-02联网核对。原件是共享多机型代码，存在EVF温度/brightness函数不能推翻机型事实。特别是本VM `fx3-display-info.c:5` 软件016a回复**人为同时给出panel/evf640×480、aspect1/1**，serial **18666** 自标virtual_geometry1/physical_display0，不能作为FX3 EVF硬件证据；是否影响后续布局选择仍需依赖者readback。（原显示选择/枚举VA如上；原机硬件描述符保持U。）

若无EVF而进入类别2/9关闭LCD的状态，已追到的原策略是 **MONITOR→NONE**，不会在此分支自动改成EVF。AP仍可维护逻辑OSD缓冲；HDMI是否显示OSD还取决于连接与输出配置，不能凭LCD关闭断言绘制“转去了EVF/HDMI”。本轮只证明到参数与0118配置层，没有完成CP多plane/scanout。（AP `27ed854..888、2df3d08`；无硬件替代输出回执。）

## 4. 为什么1005不等于有Widget绘制

原UI `16f1998` 依次processEvent、资源命令、notifyDraw、drawFramebuffer。Obj `1771f4` 先看WidgetSystem+8ac，零时不遍历候选；非零还要候选虚函数返回真才notify。**+8ac是候选/dirty计数类状态，不是已证明的LCD开关**：构造/状态更新在 `1755cc、176b84、176b94`；与本轮具体树的联系U。GRM在前置帧完成回调之后，经 `16ea58→128518` 看dirty，零走 `16eadc→15da80`，而不是发新GPE。（AP `16f19c4..1a1c`；Obj `175044、177208..268、16ea28..60、16eadc`。）

`f2fa0` 的有像素更新分支才换bank并发布完整descriptor；`f2638` 分出1003与1005。1005只有8B元数据，不提供新像素，其6005完成只归还发布闸门。AP85r4事实如下，不能继续沿用AP83a“UI卡在第二次update”的结论。（Obj `f2fa0..30a8、f2638..27d4、f22f0`。）

| 冻结事实 | 回执 |
|---|---|
| UI更新1360 | `ui-gate-counters.bin` header bank=1；`0x1100`起96Q，count[8]=1360；serial **59893**已出现n1000 |
| 唯一GPE为FillRect+Flush | serial **21939、21940**；后端原请求而非“猜测缺字体混合” |
| 早期完整1003、6003已走 | serial **21954、21973** |
| 完成计数1358 | `osd-ring-readback.json`最后final poll global_words[4:7]=1358/1358/1358；不是逐帧全payload历史 |
| 后续采到的1005持续复用source_seq1 | 原readback全部保留帧的pixel_source_sequence=1、update_id1005；serial **63282** frame1350/6005 |
| 原像素仍均匀零 | `osd-frame-000008.raw`与`osd-frame-001320.raw`各614400B独立全字节核零；ring采样有覆写缺口，未声称逐帧都保存 |

因此已证实的是“UI和发布握手能推进，但没有产生新绘图”，**未证实的是哪一个Widget/可见性/资源/dirty条件让它不画**。只在CP/物理输出层关LCD并不自动解释AP上游为什么没有GPE；须补上从d22/面板类别到具体Widget树或GRMdirty的那条边。（原路径VA与运行表如上。）

## 5. SYS0400与两种候选的判定

AP85r4 serial **21793–21809** 原栈为 `2de7264←2df26c0←2dd1f40←2dcae3c←2bd76fc`，10B为 `0d2000040a0001800000`。原名 `sequence_sys_set_timecode_tcmode::run @3960c90`，wrapper名 `3968a40`；`2df26bc→2de70a8` 的同步收包 `2de72fc` timeout−1。它阻塞SeqQueueCommon的当前任务，是另外一个实在缺口；其本函数正常尾部仅成功日志后返回。完整CP状态/完成详见并行 [vdf0400 proof](../vdf0400/vdf0400-proof.json)，本脚本不运行或重写它。（AP `2dcae08..e80、2df264c..26cc`。）

**当前判断：两者都不能升为已证停绘根因；“0400是显示初始化”的描述可排除。** 0400后队列任务/完成observer是否原本负责显示根Widget，未捕获；显示类别270/目标d22是否为关闭，亦未捕获。前者不能以“UI线程仍更新”排除，因为UI与SeqQueueCommon分线程；后者不能仅凭enum2成立，因为类别映射不唯一且早期0118是panel1。需要读真实状态来选择下一修正。（serial **18671、20781、21793–21809、59893**；AP/Obj门控链见第1、3、4节。）

## 6. 最小诚实下一步与禁止扩大结论

本轮仅提出方案，未实现/未运行。沿用Lead“不为截图改243”的决定，先在下一次获授权的运行链加**被动采样**：①`28254cc/2823890` 前后的五键cache、d72..d76、类别270、方向243及model index；②`27ed854..888` 的旧/新display与条件；③`notifyDraw`的WidgetSystem+8ac、root存在/可见/资源与GRM `128518` 返回值；④SYS0400任务的真实completion observers和队列next。采样必须带同一epoch/对象/线程，不能只打印“display off=1”解释自身假设。（精确入口VA均在proof `blocks`。）

若采样证明虚拟铰链没有初值，且虚拟硬件声明为正常展开，可最小支持**原输入协议**：目标807a0020、source00410025，20B `<key32,subkey32,status32,exinfo32,from_type32>`，V1/H0/C0/S0，分别用71c4/71c5/71c3/71c6。proof逐条生成raw示例；四个实际GPIO输入可选择在原bank7输入层建模，或声明为软件物理键consumer后通过原OSAL送状态，**二者只能一个owner**。未知hinge71cb不编造状态，NORMAL_OPEN分支本就不依赖hinge。先读back原cache/270/243、原0119/TP方向的自然更新；现有0119软件后端只接受enum2，变更姿态后需另审计enum0事务，不能把新包静默塞入旧白名单。（AP表 `2f906b0..6d0、2823c60..d0c、2dec02c..128`；Obj `cb640..cbb60`；模板逻辑/物理表见第2节。）

这项修正只证明“软件面板状态得到诚实表达”，不承诺解决当前停绘。不得直接写270/243/d22、强行Widget visible/dirty、伪造SYS0400完成observer或把6005当新像素；也不应仅因FX3无EVF就把016a EVF几何改0，因为原字段0值/不存在语义及其全部消费者尚未闭合。（原参数/发布/sequence边界见上述VA。）

仍开放：实际VM五键与270/d22值、Backup活动record与初始输入的动态来源；SysCon/CP与hinge71cb电气链；FX3原件物理设备存在描述符；真实Widget树/资源/dirty到显示目标的完整门控；0400后任务依赖；新输入自然消费、连续非黑1003/GPE与MENU反馈。**脚本PASS只验收离线证明可重建，不关闭这些运行/物理门槛。**
