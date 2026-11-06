# AP81 第二次 pin 切换：UUD reset → face-all-deletion

**本次 option 6 是原厂开机 UUD reset 路径的强证据结果，尚不能判成虚拟拨盘、CAPID 或参数 243 出错。** 原栈已直接证明 `sequence_mode_transition::run() → enter_face_all_deletion_mode_proc()`；该分支唯一对应 desired option **6**。继续向上追得 `scr0039_boot::process_power_on → Backup[02cf1841] < Backup[02cf1842] → request option6`；官方公共 ALLLANG 种子两值为 **0/4**，AP81 原 RAM 快照为 **4/4**，恰与原代码在调度后更新前者的顺序一致。**没有 setter 当时的运行栈，故“AP81 必经这一 writer”的最后一步仍是静态链加前后状态交叉印证，不伪称逐指令动态捕获。** 不应预改 Backup 为4/4或强写 option0 绕过尚未完成的原厂清理（AP `238030c、28272a8..d4、27fd38c..3c0、27bec4c..68、2c245ec..f4`；AP81 serial **23353–23372**；Backup record0 offsets **9ce74/9ce78**，详见 proof `trigger`）。

本次选中 **`appFw+9ab2518 / flags0`**；相对已提交的 AP80 图只增加 **rows1/4/5，6 GET + 3 REQUEST_CONNECT，零 DISCONNECT**。保留原11边，新增唯一 owner **`90050004` = CP InfraImaging pin task**；需增加6端点，扩为28端点/9 owner/14允许边。新增首GET已发出并阻塞，后8包及任何新回复均未运行验收（AP `2ebe188..628、2e11138..113ec`；CP `3c6a00..6a4a、9b50c8..51ec`；serial **22237、23353–23373**；RAM `ui-gate-counters.bin+8a00`）。

只读原件、既有日志和快照；仅写本目录 [脚本](audit_pin_topology_2.py)、[proof](pin-topology-2-proof.json)、本文。未启动 QEMU、运行 guest/CP 业务、修改 runtime/STATE/锁/原件/Git或操作相机。AP地址均为 `appFw.so` ELF VA；CP为 Thumb VA、文件offset=VA−108000。serial按原LF计数；全部输入SHA及原指令字节保存在proof `sources/code/instruction_checks`。

## 1. option6 的来源及正确初始状态

| 环节 | 原代码与证据 | 能证明的边界 |
|---|---|---|
| 原始当前任务 | serial23359–23372保存14层原FP/LR；`2d2f408 bl 2d11dd4`，返回LR=`2d2f40c`；`2d11df8`引用字符串 `3937400` | 原函数名为 `void model::sequence_mode_transition::enter_face_all_deletion_mode_proc()`，不是shooting/live view |
| 唯一分派 | `2d2f0bc`读sequence+f6e0，`2d2f0d0`查 `3934144` 的16个signed halfword；仅index6→`2d2f404` | desired option=6由实际执行分支确定；本次没有完整24B新input/全部睡眠寄存器捕获 |
| 属性ID | `29301ec`返回 `821c538+a880 = 8226db8`；`27bec4c`用ID144，`27bec60`写该属性 | 参数 **144=desired system_mode_option**；145是current option，142/143是desired/current mode。不能把145或面板243当这个源 |
| sequence字段 | 原基类构造 `2c245ec→29301ec`，`2c245f4`将属性快照到sequence+f6e0 | 不是pin管理器自行改模式；随后`2d11e1c`读快照放入change_mode input+4 |
| 原厂写6者 | `27fd30c`进入mode请求：desired mode≠3则`27fd38c w1=6、27fd390 w0=2`；等于3则`27fd3bc w1=6`并保留mode3；均调用`27bee0c→27beb84` | 通常为still2/option6；若原desired是movie3则保留3。**本次不能仅据选表倒推mode一定为2**，因为option6已覆盖mode分表 |
| 自动上电调用者 | `238030c→2827348→2827290`；后者`28272a8/2b0`读1841/1842，`28272b8/2bc`做unsigned比较，只有前者小才`28272c4→27fd30c`；`28272d4→2ebfdfc`随后写1841=1842 | `3135972`原字串为`[scr0039_boot] uud reset`；正常UI上电可以自动调这个模式，不要求人按“删除人脸” |
| Backup源 | `2ebfde8`与`2ebfe44`原函数各读4B ID02cf1841/1842；官方种子SHA `bf3a9d85…d0e7a2` record0，两值0/4；AP81保存RAM同offset为4/4 | 默认模板本身就满足reset条件；4/4只证明版本被更新，**不证明后续异步清理已完成** |

上述源链的权重：**捕获分支=A；原代码属性/Backup路径=A静态；本次writer归因=B强交叉印证**。还存在人工UI调用同一`27fd30c`的入口（包装`27fd3d0`，如`233d568、23d0084、2404024`），以及通用参数恢复路径`29758e0..5990`可写ID144；本捕获没有setter的caller/参数记录，不能绝对排除它们，也不能把“未见按键marker”当作不存在输入的证明。

**“正常上电”没有一个应硬编码的mode表。** 本次首次启动原厂输入已是mode1/option0，表9ab1258（serial21610–21612）；使用当前未初始化公共种子时，原厂UUD reset选择option6是合理的初始化过渡。对于已完成初始化、不需要reset的状态，常规拍摄请求使用option0；mode2=REC_STILL→9ab2518；mode3=REC_MOVIE则依proxy/network选择9ab3a08/9ab41b8/9ab2068（例proxy1/network1→9ab2068），不能只为避开90050004把mode改成boot1。枚举原字符串在`39d2ffc..340b`，选择器在`2ebeaf4..2ebec88`；本审计未读到足以选定下一正常拍摄mode的实际拨盘/保留状态。

因此本轮**没有得到“模型默认值缺陷”的证据，不提出修改默认值补丁**。最小诚实处理是保留原厂reset请求并支持已证明的软件控制拓扑；如需核实唯一writer，下一次只读探针应记`27bee0c/27bec60`的mode/option/LR、`28272b8`的两个比较值与`2c245f4`快照值；这只是建议，本工人未添加或运行探针。

## 2. 实际表、当前图与完整差异

`ui-gate-counters.bin+8a00`头为magic31504f5447583346、index1、selected=`7f51c11518`、current=`7f51c0fd70`、tid327、flags0、changes3。用current−9ab0d70还原ASLR基址 **7f4815f000**；**selected50行和current50行全部逐字节归一化吻合原构造**，不是只看serial打印的三行。当前图由原初始shadow加11条已提交启动边重建；rows1/4/5原selected是state2“不要求”，未写入shadow，所以实际current仍是state0/destination=NULL（AP `2ebe344..36c、2ebe454..46c`；serial22237、23353–23357；proof `topology`）。

以下key顺序固定 `[owner,type,direction,index]`，数字字段为十进制，YC0/RAW8/SYSND3，IN1/OUT2：

| row | 当前shadow → 新表 | source → destination | 新表记录VA / 原构造写VA |
|---:|---|---|---|
| 1 | 0,NULL → 1,目的指针 | `[90050004,0,2,1] → [9284074a,0,1,1]` | `9ab2530`；`1694e18/28/2c` |
| 4 | 0,NULL → 1,目的指针 | `[90050004,8,2,0] → [9284074a,8,1,0]` | `9ab2578`；`1694e3c/68/7c` |
| 5 | 0,NULL → 1,目的指针 | `[90050004,3,2,0] → [9058003f,3,1,0]` | `9ab2590`；`1694e50/64/90` |

旧的rows **7、10、13、14、18、20、21、22、23、24、29** 连同两端peer全部保留；完整14边在proof `topology.selected_rows`，本轮不会再GET/CONNECT旧11边。第一遍只在current已state1且新destination改变或新state0时断开，本次无此项；第二遍flags0按row升序只处理destination变化的state1条目。每条调用`2e11138`：GET源→GET目的→REQUEST_CONNECT，**flags0没有启动flags1的“双端state0就跳过CONNECT”捷径**（`2ebe290..314、2ebe390..3a4、2ebe50c..628、2e1117c、2e112a4、2e11390`）。

## 3. owner90050004、PinMgr实例与新端点

CP **InfraImaging.cpp**（原字符串`deba12`）的接收入口 **3c6a00**，`3c6a3c..4a`以SID90050004、timeout−1调用Receive。接收manager **13ad6c4**，回复sender **13ad6c8**；六个通用DataflowInfraPin对象在 **f15380** 指针表中，原构造 **9b50c8..9b51ec** 将它们逐一绑定16B self descriptor并传相同sender，不能把SID当一个泛用“VDF别名”。原OSAL任务的人类可见名称未恢复，本文用入口VA标识它。

| native key `[owner,type,dir,index]` | self descriptor VA | Pin实例VA | 本次注册 |
|---|---|---|---|
| `[90050004,0,2,0]` | f15320 | 13ad6cc | 否 |
| `[90050004,0,2,1]` | f15330 | 13ad704 | **是** |
| `[90050004,0,2,2]` | f15340 | 13ad73c | 否 |
| `[90050004,0,2,3]` | f15350 | 13ad774 | 否 |
| `[90050004,3,2,0]` | f15360 | 13ad7ac | **是** |
| `[90050004,8,2,0]` | f15370 | 13ad7e4 | **是** |

六个original ctor调用点：`9b5128、5152、5174、5196、51b8、51da→5ba9ac`；GET `3c6c1e..c88`遍历六对象并逐32bit比较type/dir/index，未找到回 **−32**；成功从对象读取state/self，在 `3c6eb0..ee8`填32B。REQUEST_CONNECT `3c6d84→5ba9f4`，REQUEST_DISCONNECT `3c6fc4→5baeb0`，仍走前任审计的通用双端状态机，不能收到AP请求就伪造内部0100/8100完成。

另外三个新增端点是已有owner的新key：**InfraBB `[9284074a,0,1,1]`、`[9284074a,8,1,0]`；ADF `[9058003f,3,1,0]`**。InfraBB native descriptor分别在`efa4e4、efa554`，接收manager11cbe14、21对象查找`1bd2cc..34c`；ADF通过原manager的10对象查找`5aa350..3ac`接受完整key，失败e002。本次没有第二个新增owner；其它六owner保持前任合同。

## 4. 九包顺序与诚实32B回复

这是**显式扩展软件图且每步成功后**的条件投影，仅#1 request与AP81实捕一致；所有reply均为未集成的软件示例。顺序为row1的#1–3、row4的#4–6、row5的#7–9；**本次没有DISCONNECT包**（AP调用点见第2节；native GET构造CP `3c6c1e/3c6eb0`、CONNECT完成`5badd0..5baeac`）。

业务回复32B字段，四个LE16 header=`1000,8000|cmd,32,2`：

| 业务offset | GET / 8000 | CONNECT / 8001，DISCONNECT / 8002 |
|---:|---|---|
| 8、12、16 | **已登记self** type、dir、index | 已登记self type、dir、index |
| 20 | 实时CP state：0已连接、1断开、2转换中 | self owner SID |
| 24 | self owner SID | signed completion status |
| 28 | signed status | reserved0 |

新注册端点确实存在且断开时，GET state1/status0；完成双向peer、空有界队列提交后CONNECT status0。未知key回−32且不创建对象，状态冲突/转换中回原有−25/−24，type/dir不符回−23/−22，失败保留原图。**GET的−26/−25/−24被AP当作特殊可继续状态，不能作“端点不存在”通用拒绝**；用−32/e002等原依据错误并保持合法封套（AP `2e10eb4..f94`；CP `3c6c84、5bab0a/5baba6、5bb0f0、18f420/440`）。

外层24B+业务32B=56B：magic a0a0a0a0/count1/total56/read24/write56；reserved+20软件选择0。**新增Imaging GET和InfraBB GET的outer+0必须是provider SID；ADF GET是0；通用8001/8002是0。** Imaging原代码`3c6f0e→5ba598`设置ReplyId90050004，`3c6f1c→5ba5e6`设置source，`3c6f2e→5bbaa4`投递；这点必须扩展AP80只有InfraBB/OSD的分支。OSAL元数据source=真正provider，destination=**本次request.outer+0的活queue**；#1恰为81cf61c2，不能存成跨edge/运行常量（AP `2ebe5d8/5f4、2e109d0`；CP `3c6f06..2e、5ba420..436`）。

逐包精确业务字节如下；proof另给每包56B规范封套、source/目的规则与实时图条件。

| # / row / 操作 | 目的owner | request业务hex | reply业务32B hex |
|---|---|---|---|
| 1 / 1 / GET_SOURCE | `0x90050004` | `001000001800020000000000020000000100000000000000` | `0010008020000200000000000200000001000000010000000400059000000000` |
| 2 / 1 / GET_DESTINATION | `0x9284074a` | `001000001800020000000000010000000100000000000000` | `0010008020000200000000000100000001000000010000004a07849200000000` |
| 3 / 1 / REQUEST_CONNECT | `0x90050004` | `0010010028000200000000000200000001000000040005900000000001000000010000004a078492` | `0010018020000200000000000200000001000000040005900000000000000000` |
| 4 / 4 / GET_SOURCE | `0x90050004` | `001000001800020008000000020000000000000000000000` | `0010008020000200080000000200000000000000010000000400059000000000` |
| 5 / 4 / GET_DESTINATION | `0x9284074a` | `001000001800020008000000010000000000000000000000` | `0010008020000200080000000100000000000000010000004a07849200000000` |
| 6 / 4 / REQUEST_CONNECT | `0x90050004` | `0010010028000200080000000200000000000000040005900800000001000000000000004a078492` | `0010018020000200080000000200000000000000040005900000000000000000` |
| 7 / 5 / GET_SOURCE | `0x90050004` | `001000001800020003000000020000000000000000000000` | `0010008020000200030000000200000000000000010000000400059000000000` |
| 8 / 5 / GET_DESTINATION | `0x9058003f` | `001000001800020003000000010000000000000000000000` | `0010008020000200030000000100000000000000010000003f00589000000000` |
| 9 / 5 / REQUEST_CONNECT | `0x90050004` | `0010010028000200030000000200000000000000040005900300000001000000000000003f005890` | `0010018020000200030000000200000000000000040005900000000000000000` |

如果以后实际出现DISCONNECT（cmd2/24B request），reply schema仍按上表8002；必须先停止提交、归还双方所有reply/resource/buffer lease，清互相peer/队列并置state1，才回status0；busy回−24，已断开回−26，未知回−32。**这只是后续合同，本轮不可额外发送/期待DISCONNECT。** AP原disconnect消费错误码较宽松，可能仍更新shadow，不能据AP日志充资源已释放（AP `2e11814..8c8`；CP `5baeb0..5bb00e、5bb1a2..27e`）。

## 5. 与 AP80 软件 pin 管理器衔接

现实现只登记22端点/8 owner/11边，`pg_owner(90050004)`直接不接管，正对应本次缺回复；原代码位置在`runtime/helpers/fx3-pin-config-v1.h:2–3`、`fx3-pin-core-v1.c:6、11–14、35–40`。**不能只加SID白名单或把未知GET按请求echo成功。** 建议在同一个受锁图中保留旧索引0..21、peer/generation/queue/lease，再追加本表六个新key及三条允许边；所有硬编码22/11容量、bounds、遍历、snapshot长度/版本必须一起核对，不新建一张冷图覆盖旧图（原状态机`5ba9ac..9e0、5ba9f4`；已消费旧11边的serial22237；proof `software_extension`）。

每对新key应由同一软件后端明确承担producer/consumer控制身份。GET读当前状态，CONNECT原子建立双方peer与各自容量有界、count0的队列后提交state0；只有两个受管端点都完成才允许替代CP内部握手。重复同边幂等仍须验证互相peer。旧对象generation、已排队reply、in-flight资源不能因注册扩容清零；新增后仍应 **pending_hardware=1、physical_output=0**（native state/peer/requestor布局`5ba9ac、5ba9f4..5bac2e`；AP80实现`pg_connect/pg_disconnect`；proof9项模型检查）。

运输reply lease与图像buffer lease分开：每个56B reply按真实分配域创建，绑定request queue/provider/sender线程/序号/generation；只有原waiter自然consume/free成功才记“消费”。扩容不能复用当前尚未归还的reply slot；发送失败只释放仍属于己方的对象并处理未提交事务。若图已经提交但回复投递失败，保留可核对的已提交状态供重试，不能单边回滚或重复释放（原AP释放queue`2ebe5f4`；现guest `FX3_PIN_CONSUMED`字段含sender/consumer/lease，serial21646..22237；前任运输合同见[pin-topology](../pin-topology/README.md)第5节）。

pin descriptor始终是owner/type/dir/index，不是DMM地址或buffer handle。本次不创建任何图像buffer；已有OSD软件分配器若未来接管buffer，须另验domain/容量/producer/consumer、generation、引用计数、队列归属与恰好一次归还，跨断开保持lease约束。AP80的buffer注册仅允许OSD owner9080003b、domain545，**不能把新Imaging YC/RAW/SYSND端点加进来就授予任意物理地址的所有权**（`fx3-pin-core-v1.c:26–32`；wire `2e10da0..de8/2e10fc8..11010`不含像素地址）。

## 6. 图像数据流、无帧与菜单关系

**九包只配置控制拓扑，不足以宣称启动了YUV/RAW取景或DMA。** `enter_face_all_deletion_mode_proc`的完整函数`2d11dd4..2d11e8c`只组24B参数→change_mode→日志→return，没有帧等待、buffer分配、sensor start。CP REQUEST_CONNECT进入通用控制握手；另有数据分支，例如type1000/cmd0104在 `3c6b1e..4a→3c6dcc` 使用图像metadata并调用`44f0c0`，这一分支不由本次GET/CONNECT直接调用。连接图从Imaging接入InfraBB/VEF/VDF，**为后来的图像传递建立路线**，不等于有帧。九包是AP侧切换请求的完整条件清单，不是原厂CP内部0100/8100握手与数据包总数；软件事务只能在双端均明确受管时替代其控制效果（AP/CP以上VA及`5ba9f4..5bac2e`；proof `code`）。

在无摄像硬件VM中，此控制合同的最小诚实实现是**空队列、不产生帧、不伪造0104 metadata、DMA完成、VSYNC、sensor ready**。如果以后真正收到start/image-buffer/DMA请求，应再按原callee和实际软件资源闭合合同；未实现则准确失败/保留pending，不凭pin已连接回成功。只有另有来源、容量和lease的真实软件图像buffer才能传递；本审计没有给出或批准sensor/RAW/YC buffer地址与大小（原wire无这些字段，CP数据路径如上）。

**AP对完整模式完成后永久无帧的容忍尚未证实。** 当前新GET仍无限等待，因此看不到本模式余下控制请求和任何后续取景等待；`2d2f290..2c0`与`2d2f6f4..2d2f948`还有依未捕获mode/flag决定的控制路径，不能从“不在此函数等帧”推导“整个App永远不等帧”。业务GET拒绝可让当前edge停止后拓扑继续；transport缺回复则无限卡住（`2e10cc4 w3=-1、2e10f54..f94、2ebe628..694`）。

菜单有一个直接的独立性证据：**serial顺序实际为新GET23358 → UI FillRect26340 → Flush26378**，并非先完成首绘再发这个GET。GPE在tid289/231继续完成第一次640×480清屏与发布消息（`26364、26370、26372`），说明这一阶段UI清屏并不需要新增Imaging pin先连通或先产生摄像帧。新GET阻塞SeqQueueCommon/tid327；首绘来自其它线程。它仍可能阻止后续模式/初始化收尾，**清屏、发布与可操作菜单文字/取景是不同验收**，不能把九包回复当作“菜单一定出现”（serial23358–23373、26340–26378；AP调用栈如第1节）。

## 7. 重建与未证实项

在项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/pin-topology-2/audit_pin_topology_2.py
```

退出0重建proof；核对卷UUID、固定AP/CP SHA、原构造两次入口独立、AP81全部100行表读回、33个旧pin消费回执、14层栈、44处关键原指令、六CP原构造、Backup两字段前后值、9包条件投影和9项图/lease检查。脚本不会调用前任rebuild、写前任proof或生成`__pycache__`；附`ap:VA:LEN`/`cp:VA:LEN`只打印反汇编。Thumb长区间可能混有literal/跳转表；保留raw供复核，不把偶然译码当执行证据，关键路径另有44处指令断言。工具方法按[Capstone官方Python文档](https://www.capstone-engine.org/lang_python)核对；Sony业务结论取本地原VA，未把公共项目的型号/结果移植给FX3。

仍未证实：AP81写参数144时的精确caller栈/Backup两次实际读值；普通下一拍摄mode的硬件来源；全部九包真实发出/消费、扩展后28端点集成、并发取消及错误恢复；CP运行、sensor/YC/RAW/SYSND buffer、DMA、后续模式完成、无帧长期容忍、菜单文字/按键/取景可用。特别是 **Backup已4/4不充异步UUD reset或人脸删除成功**；本目录只给可复核审计和软件扩展合同。
