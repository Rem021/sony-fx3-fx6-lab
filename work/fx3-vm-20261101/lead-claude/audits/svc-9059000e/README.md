# 0x9059000e：VDF timecode 的跨 CPU 路径

结论：**阻断点已定位到 `model::sequence_boot::run_i()` 的 `vdf_srvc_set_timecode`，不是尚未返回的 license/beep，也不是前一个 TCUB sync。** 原 AP `2b66f28→2dd0754→2debbb4` 将 `2001/0205/28B` 业务消息装进 24B Dataflow 封套，发往 CP 的 VDF 服务 `9059000e`，随后在本次动态 reply queue（AP77 为 `81cf61c0`）无限接收。AP 内核缺少的是 **公共跨 CPU 发送回调**；报错中的 `0xe` 只是日志打印的低16位，不能解释为“AP 本地队列14没人接收”（AP `2debc48..64`；OSAL模块 `.text+3d78..3dfc`；AP77 serial:21318–21320、30422）。

**`tag2=a0a0a0a0` 是明确写入的 Dataflow magic，不是垃圾填充。** 真正未初始化的是封套 `+20..23`；AP77只记录前8B，没有整包52B，所以尚不能给出“已观测精确请求”的完整白名单。原 CP 成功业务回复已闭合为 `012005120c00010000000000`，可以构造规范36B软件回复；它是尝试排队 timecode 更新后的软件确认，不证明下游发送成功、显示、菜单或真实时间码功能实现（DF `32278..2a0`；CP `5f8158..81e8`）。

## 范围、复现与证据

仅写本目录三个文件：[脚本](audit_svc_9059000e.py)、[proof](svc-9059000e-proof.json) 和本文；不启动QEMU，不访问设备，不改原件、runtime、STATE、运行锁或Git。已完整读公共上下文、PLAN和启动屏障审计。VA是image VA；CP为Thumb，offset=VA−`108000`；ko地址必须带节名，不能把不同节中的相同offset混为一处。

项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/svc-9059000e/audit_svc_9059000e.py
```

退出0重建proof，写入前检查卷UUID。固定六份原图SHA256、56条精确指令、5处虚表绑定、PCIe注册重定位；完整保存目标区间540条指令及70次调用/24处分支，另保存协议辅助代码原字节、AP77/AP70 serial哈希和LF行号。`ap|cp|df|osal|ko|pcie VA:LENGTH` 只打印反汇编；`symbols IMAGE NAME...`查询原符号。ko/pcie默认`.text`，`.init.text`另列在proof，避免误用offset。

下文 `AP77` = `runtime/runs/ap77agate-f63dd39e/serial.log`，`AP70` = `runtime/runs/ap70lcd-f61554d9/serial.log`，相对 `work/fx3-vm-20261101/menu-repair-01/`。行号按原始LF分割，保留CR/NUL，不用`splitlines()`。工具依据是本轮核对的 [Capstone官方Python文档](https://www.capstone-engine.org/lang_python.html) 和 [Arm AAPCS64 2025Q1](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)；Sony语义全部取自原件，不由公共ABI文档推断。

## 运行事实

| 事实 | serial证据 | 限度 |
|---|---|---|
| 三次创建与返回句柄0/1/2 | AP77:21294–21295、21314–21318 | 同一sequence=`7f8819daa0`；函数指针分别绑定license/volume/beep |
| 三次自然完成 | AP77:21390、22104、22164 | handle1、2、0各一次；没有第四次get-func完成 |
| 第三次返回后发9059000e，内核丢弃 | AP77:21318–21320 | source/reply_id样值81cf61c0；观察器op4是OSAL发送ioctl，不是业务cmd4 |
| SeqQueueCommon随后接收睡眠 | AP77:30370–30430，尤其30422；43524–43584，尤其43576 | 内核栈本身没有用户栈；与原调用链、缺reply回调共同定位等待，不把快照独自当业务PC |
| get-func预创建、入口、屏障样本均0 | AP77全文，proof `gate_sample_counts` | 3次2b63224/3次2b634dc，0次2b67674/2b60208/2b6353c；这不是四任务屏障通过 |
| 早期同样发送 | AP70:20457 | tid322，同目的和两个tag；不能用AP70 TID替代AP77 TID |

观察器有去重/抢锁丢观察限制，`SEND_UNIQUE`不是每次发送的无损追踪。但这条发送和内核的NULL公共回调分支是正证据；不需要以缺少后续日志单独推断阻塞（AP77:21319–21320；原OSAL `.text+3d80..3dfc`）。

## 第三任务后至get-func：完整控制流

所属函数字符串为 `void model::sequence_boot::run_i()`（`391a718`；入口`2b638b8`），源码名 `sequence/sequence_boot.cpp`（`3917e8e`）。所有调用/分支逐条列于proof `sequence_complete_call_and_branch_inventory`，包括日志和致命路径；下面按业务段标注汇合点，并未省略异常分支。

| 调用点 → wrapper → 实现 | 条件/分支与下一步 |
|---|---|
| `2b66e28→2dd1d94→2df22d8` TCUB_TC_SYNC | 原实现只有`str wzr,[x1]; ret`；`2b66e30`状态0跳`2b66ee0`；非0走`2b66e34..edc`日志/致命路径到`2b66ba8` |
| **`2b66f28→2dd0754→2debbb4` VDF_SRVC_SET_TIMECODE** | 从sequence+1c4/+1c8复制两个u32入参（`2b66f10..20`）；实现向9059000e发送并等待；`2b66f30`状态0跳`2b66fe0`，非0走`2b66f34..fdc→2b66ba8` |
| `2b67020→2dd0554→2deb808` black-frame notify | 输入byte=1；构造200d/0142，走无回包发送器`2de66f4`（`2deb854`）；`2b67028`成功到044，失败02c到058；二者日志汇合`2b67058` |
| `2b6708c→2dd0594→2deb868` osd-mute notify | 输入1；200d/015a；`2deb8b4→2de66f4`；`2b67094`失败到`2b67238`再回`2b670ac`，成功也经0ac继续 |
| `2b670d8→2dd05d4→2deb8c8` shutter mute | 200d/0145，走`2deb924→2de83b4`；`2b670e0`失败到`2b67250`再回`2b670f8` |
| `2b67124→2dd0714→2debb2c` EVF temp event | 2001/020b，`2debb98→2e109d0`异步发送；后释放动态ID，无同步接收；`2b6712c`失败到`2b67268`再回`2b67144` |
| `2b67178→2dd0654→2deb9b8` panel color | 输入8；200d/011b，`2deba14→2de83b4`；`2b67180`失败到`2b67280`再回`2b67198` |
| `2b671cc→2ddfb74→2eabfd0` TP direction | 输入sequence+304；`2b671d4`失败到`2b67298..340→2b66ba8`，成功经`2b671d8..1ec`继续 |
| `2b67214→2dd06d4→2debacc` panel-out notify | 输入0；200d/0160，`2debb18→2de66f4`；`2b6721c`成功到344，失败220到358，二者日志汇合358 |
| `2b67384→2dd0694→2deba54` panel resolution | 200d/0165，`2debab0→2de70a8`同步路径；`2b6738c`非0到`2b6749c..544→2b66ba8`；成功经`2b67390..3a4`继续 |
| `2b673c4→2aa1ea8`、`2b673c8→294b8bc`、`2b673d8→2aa1ab4` | 取OSD layout入参；`2b673cc`读返回对象首u32并放入输入槽；这三个本地调用同样保留在逐条清单，无额外本区间分支 |
| `2b673e4→2dd0054→2deb504` osd layout | 200d/0150；`2deb574→2de83b4`；`2b673ec`成功到548，失败`2b673f0..498→2b66ba8` |
| `2b6758c→2ddfaf4→2eabcdc` touch sensitivity | 输入sequence+1f8；`2b67594`成功到644，失败`2b67598..640→2b66ba8` |
| `2b67674→2b63224` get-func创建 | `2b6765c..70`从GOT`47a6698`取业务入口2b60208；成功路径日志后到创建，`2b67678`保存句柄；之后才可能`2b67a6c`进四任务屏障 |

所有非0致命分支都会经成组`2f6fe3c/2f6be48`日志，最终`2b66ba8`打印`SEQUENCE FATAL ERROR assert at %s:%d(error:%08x)`并转`2b63bf0`；非致命通知失败只记录后继续。proof保留每一次日志调用与实际branch目标。**这张表是完整静态路径，不声称AP77已经执行timecode之后的任一段。**

## 请求逐字段与magic

AP wrapper先构造28B业务体：`2debbd0`清前16B，`2debbf8/bbfc`清后12B，然后写4个u16头与byte8=1。入参第二个u32先通过集合检查；第二入参属于0/9/15才进一步验证第一个入参0..5，第一个为3或5时将byte16写1，其余有效组合为0（`2debbdc..bc24`、`2debc90..bcc0`）。其他入参进原assert。字段的精确原枚举名未从独立定义恢复，本文保留`in+0/in+4`，不凭timecode函数名乱命名。

`2debc3c→2de7070`分配本次动态reply ID；`2e109d0`调用DataflowInfraMsg::SetDataflowMsg、SetReplyId、SetSrcId，再由DataflowInfraSender::SendASync发出（`2e10a0c/8c/9c/ab4`，DF `33e50..33f24`）。本例OSAL metadata source与封套reply_id均81cf61c0；它不是业务命令编号。

| OSAL payload offset | 长度 | 字段/本例静态值 | 原代码 |
|---|---:|---|---|
| 0 | 4 | reply_id：本次动态ID，AP77=`81cf61c0` | DF `32448`；AP77:21320 |
| 4 | 4 | **magic=`a0a0a0a0`，明确初始化** | DF `32280/284/28c` |
| 8 | 2 | message count=1 | DF `32398..3b0` |
| 10 | 2 | outer payload length=52（24+28） | DF `32368..3ac` |
| 12 | 4 | read cursor/首业务offset=24 | DF `3229c` |
| 16 | 4 | write cursor=52 | DF `323b4..3cc` |
| 20 | 4 | reserved/alignment：该构造路径未写，**AP77值未知** | DF `32278..2a0`无此store；`323b8..bc`从24复制 |
| 24 | 2 | business type=`2001` | AP `2debbc8/bbd4` |
| 26 | 2 | cmd=`0205` | AP `2debbd8/bbe4` |
| 28 | 2 | business length=28 | AP `2debbe8/bbf0` |
| 30 | 2 | flags=1 | AP `2debbb8/bbec` |
| 32 | 1 | body+8=1 | AP `2debbf4` |
| 33..39 | 7 | 0 | AP `2debbd0` |
| 40 | 1 | body+16：0或1，由上面的入参决定；AP77未捕获 | AP `2debbf8/2debcb8` |
| 41..51 | 11 | 0 | AP `2debbf8/bbfc` |

因此AP77已观测的仅为前8B `c061cf81a0a0a0a0`。proof给出两种**静态候选**业务体和填零padding的52B示例，均标为`STATIC_POSSIBILITY_NOT_CAPTURED_REQUEST`；不称为抓包、不直接用作已准入白名单（AP77:21320）。

## 9059000e由谁接收、谁注册

原 `libosal_uipc` 用 `ID&7fff`作队列索引，bit15=0进内核、=1进用户态队列（`5e6c`、`5eb8→6050`）。`9059000e` bit15=0，因此不能仅开AP用户线程并声明同名ID就接管原路径（该库VA）。

内核还先检查bit31；置位且`ID&70000000!=0`时走 **public/cross-CPU callback**，不会落入本地队列0xe查找（osal_uipc.ko `.text+3c5c→3d78..394`）。`3d84`取全局+458回调结构、`3d8c`取首个snd_msg函数；任一NULL跳`3de4`日志，`3df8`仍返回0。这精确解释“发送API成功但没有接收者，随后永久等回复”的组合（AP77:21319–21320；原模块VA）。完整高位module/domain枚举尚未恢复；这里只使用实际位测试，不把0x59硬译成某个Linux线程号。

原机AP **`pcie-if.ko`注册跨CPU转发**：`.init.text+20`调用`pcieif_reg_public`；后者`.text+3c88..ca0`调用`osal_reg_public`，入参为`.data+b8`操作表；该表首项重定位至`.text+3c70`，再调`.text+34c0`发送请求，涉及物理地址/消息源/PCIe send（`.text+3520..35b4`）。OSAL注册器`.text+3ba8..3bc0`保存结构到同一+458槽。proof保留`.init.text`及`.rela.data`，明确区分`.init.text+48 init_module`与`.text+48`，不以重叠offset冒认初始化。

原CP消费者是 **VDF::SubsystemApiExecMgr / SubsystemMain**：`5f1126..153`把`9059000e`传给`5f0fae`，保存到全局对象`102dff8+8`；虚表`b7dcc8`及RTTI`b3ccc0`绑定SubsystemApiExecMgr；任务入口`5f0f3c..56→1e8cc0`，后者`1e8d48`读取对象+8，以−1调用Dataflow ReceiveASync（`1e8d44/4c→5bb858→49f9b0`）。它剥封套、逐业务消息分发到SubsystemFactory（`1e8d74..1e8e14→610db4`），不是AP的某个libObj线程。**CP启动时创建/注册该OSAL队列的更上游函数尚未闭合**；不能将已找到的消费者构造器冒称为osal_init_msgq调用。

VM中AP77 init只显式加载既有osal、utimer、backup等模块，没有pcie-if；原PCIe平台initcall还被blacklist（`runtime/ap77-ui-gate-observe/init-reviewed.sh`全部insmod点，proof封存全文/哈希；AP77:46、49、695）。决定性证据是当前内核公共回调NULL分支的原日志，而非仅凭没有模块名。当前运行命令是AP `virt/cortex-a35`，不启动CP Cortex-R镜像（AP77 `command.json`，proof封存），所以既无真实传输，也无真正CP VDF工作线程。

## CP处理与回复

`N3VDF21VdfSrvcCmdSetTimeCodeE`（RTTI字符串`b3dc70`）的typeinfo为`b7ea3c`，vtable address point=`b7ea24`。`+c→5f80e2`匹配type2001/cmd0205；`+10→5f80f2`为Activate，`+14→5f8158`为Execute。原工厂初始化`5f74d6..4e8`将该虚表安装至`11cd0e0`；不是只找到一个同名字符串（原VA和proof虚表原u32）。

Activate读取业务body：body+20必须<3，body+8必须非0，body+9必须<2；不满足则回`1205`/4B status1并返回1（`5f8102..154`）。上面AP静态28B请求body+20=0、body+8=1、body+9=0，满足这些检查。正常分支调用原状态设置函数后返回0，未在Activate直接给成功回复（`5f8112..11e`）。

Execute `5f8158`先调`5f8180`：生成`2001/f033/28B/flags1`，复制原body+8起20B，向原VDF自己发送（`5f81a6..1dc`）。返回值没有条件判断；随后无条件把status32=0、cmd1205、payload length4交给MsgAccessor::SendResponse（`5f8164..178`）。所以这个成功是**尝试排队该timecode更新后的软件确认，连发送返回值也不纳入判定**，不能当成下游HDMI/时间码电路应用完成。

发送响应的虚表链已闭合：MsgAccessor vtable `b8113c+88→60ed16`，构造type=原2001、cmd1205、len12、flags=原1、+8=status；通过SubsystemFactory vtable `b81b90+2c→61103a`及`+30→611056`发送。后者SetDataflowMsg→SetSrcId（`61107a/0b6`）→`611858→5bbaa4`，OSAL source是Factory保存的本子系统ID9059000e（`610d98`），目的取原request reply_id（`60ed34..86`，getter`60ebd2`）。成功业务体严格为：

```text
01 20 05 12 0c 00 01 00 00 00 00 00
```

CP Dataflow builder同样写24B封套、magic、count/cursors；响应没有SetReplyId，outer+0=0（`5ba420..436`）。原builder没有单独写outer+20..23；软件模型可选清零这个保留字段，不能声称捕获了原CP运行值。规范36B回复见下一节。

## AP具体等什么与最小软件合同

`2debc58..64`从本次动态ID槽取queue，调用RecvAsync，目标业务槽12B。`2e10cc4`timeout32=`ffffffff`，`df+33998`调`osal_rcv_msg_tmo`。接收器检查magic，识别Dataflow封套，GetMsg用outer+12定位首业务并复制不超过请求槽12B（DF `33a78..a90`、`320e8..120`）。AP wrapper读取业务+8 status32，0由`2de581c→2de5940`映射为成功；父函数`2b66f30`才继续到`2b66fe0`。成功后释放本次动态ID（`2debc68`），不能保存旧81cf61c0供以后复用。

wrapper没有自行比较type/cmd，也忽略GetMsg返回值与读取的source（`2e10d48..74`）。这不是放宽软件合同的理由；过短回包还可能让原本清零的status槽保留0。应回完整规范封套和12B业务体，绝不利用这一宽松消费路径。

**可复核的候选回复**（OSAL payload，36B；source metadata=`9059000e`，目的=本次request reply_id；reserved padding选0）：

```text
00000000a0a0a0a001002400180000002400000000000000012005120c00010000000000
```

本任务没有完整52B请求捕获，因此**精确白名单尚不能激活**。运行链下一步仅需在原发送边界只读捕获`osal_msg_size`、完整52B、OSAL source和业务调用栈；交叉核对outer reply_id/source、上述所有常量及本轮dfmode后，将该真实52B（含padding）冻结为单个请求样本。若只按前8B或cmd0205放行，便不符合“只接受观测到的精确请求”的要求；本审计不提供这种宽泛兜底（AP77:21320；AP/DF构造VA如上）。

准入后最小实现可接已有preload发送分发：仅匹配`destination=9059000e/op4/本轮真实source/size52/整包白名单`，保持原消息所有权和释放合同；对每个活跃请求恰好一次分配36B，复制上述规范回复、设置source9059000e，调用原OSAL发送到该请求的动态reply queue。不能主动补包、重放旧queue、直接调用任务完成、强行越过屏障，也不因此声称原CP功能恢复。这里给的是软件合同，**没有实现或执行拦截器**。

若选择内核方案，最小注册入口是`osal_reg_public`的操作结构首项snd_msg，并需处理原消息分配域、所有权、释放和同步/其他回调；它是全局跨CPU入口，不能只为e号随意注册普通队列。实际PCIe路径还依赖CP、DMA、平台硬件；**不能仅为消除日志而加载原pcie-if**。已有preload内的精确请求拦截无需注册此全局回调，对其余远端消息的策略由Lead保留（OSAL `.text+3ba8..3bf0`、PCIe `.text+34c0..35b4`）。

## 与UI的关系与未证实项

这明确属于**VDF显示控制中的timecode服务**：AP原函数签名`39687a8`、CP类名`b3dc70`、VDF目的9059000e及f033事件相互绑定；CP中其他SendVDF路径也用同一目的（如`19eb24..26`、`5f2b80..88`）。它阻止SeqQueueCommon进入后续显示初始化/get-func创建，但不是libObj/Widget的1001/1004 timer通知，也不是GPE fill/flush协议；修好这条回复不能独自证明UI首绘或菜单出现（本区间路径和已有AP77:21318–21320）。

仍未证实：AP77整包52B与dfmode实际值；CP原全局队列创建/注册入口；f033之后物理timecode下游；回包后后续VDF/TP初始化、get-func、四任务屏障和首绘是否都能运行通过。上述规范回复是原消费链可接受的静态合同，不是guest消费回执或实机验收。本文没有新增QEMU、相机、声音或显示实验。
