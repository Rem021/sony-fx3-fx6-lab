# 回调合同覆盖与启动 adapter 阻塞项

2026-11-03，静态研究交付。**57项已逐项列入矩阵，但0项完整回调合同通过，不能制作真实 mpr::Init adapter。** 本次超出旧producer/count报告的证据是事件分派参数/释放路径、FX6回调的原地址与首基本块字段读写、11个原始零槽、4个RET叶函数，以及u16参数在两代MPR内的不同保存路径。所有新文件仅在本子目录；原报告、二进制与固定平台未改，没有VM/设备/固件补丁。

入口：[覆盖表](COVERAGE.md)、[完整矩阵](matrix.json)、[事件跳表原字及调用块](events.json)、[同步直接调用调查](sync-graph.json)、[输入哈希](inputs.json)、[离线检查](checks.json)、[机器字映射/交付回执](receipt.json)。输入沿用父报告5份固定SHA，check.py重新逐份校验。VA/fileoff/原字在receipt，反汇编保留原指令；这里不重复已完成的producer/count证明。

## 同步初始化：明确能证明与尚不能证明的边

完整FX3 Init见fx3_mpr-init.txt，无BLR/BR回调调用；其57个GOT窗口是注册存储。经精确导出入口/PLT名字解析，向下深度5的直接调用调查覆盖85个函数；其中没有新增57个回调GOT窗口，**233个未解决边界（外部/未导出入口/深度截止）阻止“Init不调用回调”的结论**，间接调用、线程与动态绑定不在图覆盖范围。数量以sync-graph.json为准；这是一份有界候选图，不是完整可达性证明或实际执行记录。

已知直接同步调用包含UMID、UniversalGroupId、Codec、CAPID、IntegStatus/Setting/RecordStill/RecordMovie/RecordAudio/Play/Edit/Event等；后者可能创建线程，不能把异步事件说成同步回调。未定位到可证明在Init同步栈上调用的共有回调；此处结果是unknown，不是零调用。最优先应闭合未导出入口0xb5628（Init的0xb6d78、0xb6e1c），0x133554、0x941c4、0x12f5f8、0x129790，以及Init→IntegEventInit建立线程/队列的边，避免先扩张所有录制功能。

## 原始零槽与RET不是功能移植

父报告的FX6 producer先清零0x290，以下11槽没有对应写入（讨论范围是有效count≤4，非溢出输入）。这是FX6原行为，不是本任务清空回调。9项在FX3 SendIssueEvent对应事件分支有原码空指针保护，零指针走公共释放路径，故这些分支不会仅因零槽直接BLR 0；不能因此证明功能可省略或启动一定成功。

| FX6零槽 | 对应事件 | FX3空保护 |
|---|---|---|
| AudioRecStarted +e8 | 1019 | 有 |
| AudioRecStopped +f0 | 101a | 有 |
| InternalAudioRecStopped +f8 | 101b | 有 |
| AudioPbStartFinished +108 | 101d | 有 |
| AudioPbPauseFinished +120 | 101e | 有 |
| AudioPbPauseReleaseFinished +128 | 101f | 有 |
| AudioPbStopFinished +118 | 1020 | 有 |
| InternalAudioPbStopped +110 | 1021 | 有 |
| MovieRecReelNoUpdate +238 | 1033 | 有 |
| CheckDigitalSignatureFinished +248 | 未在该分派表定位 | unknown |
| GetDigitalSignatureInfoForMovieFinished +250 | 未在该分派表定位 | unknown |

四个FX6仅RET入口：PbGpsInfo 0x2128858、PbPauseFinished 0x212885c、PbPauseReleaseFinished 0x2128860、AudioWriteFinished 0x2128864，原字均d65f03c0。它们不解引用参数、不写返回寄存器，但**C++返回类型未恢复，不能标为返回0或功能完成**。反例：FX3 PbGpsInfo 0x2e62508在0x2e62568构造arg+4，0x2e62570设长度0x90，0x2e62574调用memcpy；FX6同名只RET。签名与功能等价须分开。

## 消费者参数、枚举与生命周期

FX3 SendIssueEvent 0xb442c..0xb4e74：0xb4440把传入x1保存为x19，w0减0x1000并限制≤0x38，以0x2cb3f8的57个有符号u16跳表定位事件块。events.json保留每项跳表原字、目标块、GOT符号、null guard及BLR；54个符号匹配到该表，其他仍unknown。多数块传x0=x19，先调用0xb3a78复制指定长度，再重新从全局加载回调并BLR；那个长度是复制长度，不是allocator或全结构大小证明。0xb3a78在0xb3af4以w19长度memcpy，见fx3-event-diagnostic.txt。

回调结果在该分派点不被使用；公共出口0xb4488重新x0=x19，0xb4494尾调用free。**这证明该调用点的借用期限止于返回；不自动证明所有事件的分配来源。** 不能保存输入指针供延迟使用。原回调转发到AP自己的消息系统，需另查新分配消息的接收/释放合同。

已闭合一条同一payload的静态分配→调用→释放链（不是近邻猜测）：fx3 dispatch-callers.txt中0xb5110设60，0xb5114 malloc返回p，0xb5128保存p到x19；0xb5134以p调用SetRecPbTimeEvent；0xb5138 x1=x19=p，0xb513c event=0x1022，0xb5140调用SendIssueEvent；后者0xb4440保存同一p，经events.json的1022分支BLR到RecPbTime，公共free(p)。另0xb5194 calloc(1,60)→x20→0xb51b4同事件的链也可复核。未知是填充函数/FX6 RecPbTime的全部嵌套字段与延迟转发，不把这条链泛化成57项都已闭合；经GetIssueEvent取得的其他payload分配来源仍未知。

三个重点配对：

- **LoadStillFinished**：FX3分派1000在0xb4484传p，复制长度20。FX3回调0x2e52368/370与FX6 0x212956c/574均读取p+c的u32和p+8的u32，后者经cmp/cset变成“等于零”u8。FX6分配12字节并写+0=0x12e、+4=复制的u32、+8=布尔；FX3消息编号是0x105。局部字节投影相同不代表事件枚举一致、消息尾部填充可随意零化或投递生命周期已证。
- **PowerOnFinished**：FX3 0x2e6d224/250/258与FX6 0x213c084/b0/b8读p+0/+4/+8；后两字段分别写查询对象+0x3e4、+8。查询/虚调用目标、字段枚举和对象身份仍未闭合，因此它是启动后最优先的非空回调，不应按同名直接放行。
- **AllMovieWriteFinished / StillRecPriorityMediaChanged**：可见分别读取+4，及+4/+8，FX6生成AP消息0x1b/0x142，FX3是0x18/0x119；只允许描述字段复制，不把消息编号直接跨代映射。这些录制功能不是本轮为最小启动扩大验证的优先项。

所有57行均保存FX3 GOT调用候选窗口、双代目标入口/原指令、FX6首基本块输入读取观察、返回/枚举/生命周期的unknown。自动窗口可能包含相邻其他分支，near_indirect不是def-use证明；只有events.json的选定块和以上手工数据流被提升为明确结论。片段最多384字节并在已知下一回调/RET/恢复栈后尾跳截断，非完整函数证明；遗漏/分支后的字段保持unknown。

## 0x30c与0x5a0：消费不同，范围未闭合

FX3 Init 0xb7080 ldrh w3,[input+1f2]→0xb7094 IntegRecordMovieInit；FX6相应+28a，原producer数值分别780/1440，仅是u16可表示值。

FX3 0xd603c uxth w25,w3；每slot的两套记录分别在0xd60e4/0xd6110写入嵌套参数+0x18，0xd60f8/0xd6120调用0x11975c。后者0x1197c8读[x20+18]，0x1197cc写目标对象+0x24。整个入口片段不见对该字段作业务范围cmp；不能推出0..65535均有业务意义。

FX6 IntegRecordMovieInit 0x155db0 uxth w22,w3；0x155de4 str w22,[x19+0x1454]，保存为32位零扩展值，原Init段没有FX3的同一slot对象初始化循环。后续使用边尚未闭合；因此不能将5a0缩放为30c、按机型名字映射或只因u16宽度相同复制。两代原字见movie-init文件及fx3-u16-next-consumer.txt。

## 最小可转换子集与真实adapter阻塞短清单

当前没有获准输出完整Init记录的子集。仅对LoadStill局部已证字段提供[projection.py](projection.py)：输入严格bytes、长度20，输出两个具名标量观察值，不生成AP消息、函数指针或Init结构；不猜测opaque u32枚举。完整Init、未知回调、19/21字节及可变buffer请求均显式拒绝。该程序只证明“字节读取与zero-test”，不是固件适配。check.py验证4组边界值、5个拒绝反例，原件与父回执不变。

启动adapter仍被以下短清单阻止：

1. 同步Init调用边未闭合：优先上述非导出函数及IntegEventInit线程交接，确定哪些回调在返回前或第一事件时必须就绪；没有证据支持清空回调或跳过assert。
2. PowerOnFinished的p+0选择域、p+4/+8状态域及查找对象/虚表合同：下一边是FX3 0x2e57a90与FX6 0x212d524，以及随后0x2e6c7a0/0x213b870的结果对象。
3. 原11零槽中2个数字签名回调的其他消费者尚未定位；已有9个空保护只解决空BLR问题，功能缺省是否符合启动合同仍未知。
4. u16的FX3对象+24后续读取与FX6管理对象+1454后续读取/范围尚待追踪；禁止默认替换常量。
5. Init scalar数组元素/UMID方法/嵌套对象域尚未闭合（父报告保留未知）；不因本次局部回调证据而升级。真实绑定和运行回执仍由runtime另行安排，平台保持固定。

复核顺序：python3 survey.py → python3 refine.py → python3 events.py → python3 check.py。它们只写本目录、不执行ELF；survey/refine是有界调查工具，输出不得自动作为适配通过清单。静态方法沿用父报告引用的Arm ELF规范，无新增外部运行依据。
