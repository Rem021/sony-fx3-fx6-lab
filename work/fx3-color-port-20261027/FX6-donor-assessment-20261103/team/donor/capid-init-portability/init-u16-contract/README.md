# Init u16：实际 writer 消费合同（2026-11-03）

**结论：不能把 FX6 的全局 Init u16 1440 原样搬给 FX3，也不能现在一律改成 780。** 此值在已闭合的路径中控制“到达可录制时间”通知的阈值，单位是分钟；它不是 writer 数组元素数量或分配字节数。关键差异在实际 writer：原 FX6 **Xavcs** initializer 忽略传入值，硬写 **780**；原 FX6 **Mxf** initializer 才保留 **1440**。原 FX3 此初始化路径构造 Xavcs，并直接保留传入 u16。

因此，**只有具体模式已证明走 FX6 Xavcs 构造器、目标仍是固定 FX3 Xavcs 时，这一个字段可有证地用 780 保持原 FX6 Xavcs 的比较阈值**。Init 阶段尚无实际 writer 选择证据，不能把该条件提升成全局转换。Mxf 路径在固定 FX3 上没有已证明的等价 writer 绑定，必须拒绝，不能静默退化成 Xavcs。1440 在 FX3 比较器中可表示、可计算，但其“可计算”不代表保持 FX6 Xavcs 行为。

本次是只读二进制分析及有界离线字节/符号计算，没有 ELF 整函数执行、VM、相机或可运行固件补丁。没有改动 QEMU、kernel、DTB、helpers、env、seed、CPIO、旧报告或固定输入，也没有重做 PowerOn/57 项表。

## 可复核入口

- [instruction-evidence.json](instruction-evidence.json)：每条摘录的 VA、PT_LOAD 换算后的 fileoff、little-endian 原字节、反汇编机器字；虚表/GOT 的原始 RELA 记录、符号值、尺寸和数据表。
- [fixture-results.json](fixture-results.json)：5 个原 initializer 输入、7 个时间比较案例、Mxf 隔行反例、7 个显式拒绝案例。
- [offline_fixture.py](offline_fixture.py)：只返回两个字节的条件转换；无 stub，不产生完整 Init 记录。
- [collect.py](collect.py)、[trace.py](trace.py)：固定 SHA 校验、摘录与指令核对；[receipt.json](receipt.json) 记录输入及交付哈希、旧报告不变检查。
- `fx3_mpr-full.txt`、`fx6_mpr-full.txt` 是只读输入的完整 objdump 索引；审查优先使用下述小段。objdump 的“最近导出符号+offset”**不等于真实函数名**，本文未据此命名匿名函数。

## 固定输入

| 输入 | SHA-256 |
|---|---|
| FX3 appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| FX6 appFw.so | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| FX3 libmpr.so | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` |
| FX6 libmpr.so | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` |
| 固定 fx3-capid-v49-touch100.so（仅校验身份） | `cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e` |

确切源路径见 JSON 的 `inputs`，沿用父报告原件。本报告列出的代码 VA 在对应 ELF 中均等于 fileoff；数据/GOT 不能照抄此规则，例如 FX6 GOT VA `0x108de78` 的 fileoff 是 `0x107de78`。JSON 按 PT_LOAD 逐项换算，无运行时装载偏移假定。

## 输入到对象：链条与布局

| 环节 | FX3 | FX6 |
|---|---|---|
| 已有 AP producer，只复核关键原字 | `0x2e58ee4 52806181`：mov w1,780；下一条 strh 到 Init 记录 +0x1f2 | `0x212f498 5280b400`：mov w0,1440；下一条 strh 到 Init 记录 +0x28a |
| MPR Init 取参 | `0xb7080 7943e663`：ldrh w3,[x19,+0x1f2]；`0xb7094` 调 IntegRecordMovieInit | `0x12bd30 79451663`：ldrh w3,[x19,+0x28a]；`0x12bd44` 调同语义入口 |
| Integ 保存 | `0xd603c 53003c79` uxth w25,w3，随后按每个 writer 传递 | `0x155db0` uxth w22,w3；`0x155de4 b9145676` str w22,[manager,+0x1454]，32 位容器保存零扩展的 u16 |
| 何时构造 writer | Init 内 `0xd60a8/0xd60c8` 两次固定 new(0x2c58)，各调 `0x11b9dc` | 延至 EnterRec，`0x157960` 读取 MovieRecInfo manager+0x27c，比较 **8** 后分派；其枚举名称及运行值本次未假定 |
| 字段如何进入 writer initializer | 局部参数记录 +0x18；主、副指针位于循环基址 +8/+0x148；两次直调 `0x11975c` | manager+0x1454 的低 16 位在 `0x1579b8/0x1579f0` 读出，写局部参数 +0x18；主、副指针为循环基址 +8/+0x168，调用各自 vptr+0x10 |
| writer 实际存储 | `0x1197c8 79403280` ldrh w0,[param,+0x18] → `0x1197cc 79004a60` strh w0,[this,+0x24] | Xavcs：`0x1b0f44 52806180` **mov w0,780** → `0x1b0f48 7900ea60` strh [this,+0x74]；Mxf：`0x194124 79403280` ldrh [param,+0x18] → `0x194128 7900f260` strh [this,+0x78] |

FX6 Xavcs 也在 `0x1b0f14` 读取 param+0x18，但只将它放进诊断记录；诊断返回后 `0x1b0f44` 重新定义 w0=780，随后存入真正被比较器读取的 +0x74。因此“log 见 1440”不能证明 Xavcs 有效值是 1440。

摘录：[FX3 Integ 分配及传参](fx3_mpr-d6004-d614c.txt)、[FX3 writer initializer](fx3_mpr-11975c-1198e0.txt)、[FX6 Integ 保存](fx6_mpr-155d78-155e04.txt)、[FX6 EnterRec 选择及调用](fx6_mpr-1578e0-157a34.txt)、[FX6 Xavcs initializer](fx6_mpr-1b0ed4-1b10e0.txt)、[FX6 Mxf initializer](fx6_mpr-1940b4-1942a0.txt)。

### 虚表分派不是同名推断

FX6 EnterRec 的输入记录保存在 x24 (`0x15760c`)，**x22 是管理对象**：`0x1576b8` 从 GOT[0x108e708] 取 s_movieRecInfo。`0x157914` 调 SetEnterRecInfo(input=x24, manager=x22)；原实现经 `0x146b7c` 调 GetMovieRecParam 到局部记录、`0x146b84` 校验，成功后 `0x146c64..0x146c70` memcpy(管理对象+0xa0, 局部记录, 0x8c8)。所以分派字段 manager+0x27c 来自 **movieRecParam+0x1dc**，不是 enterRecInParam+0x27c，亦不是 Init u16。其生产者上游本次收束于 GetMovieRecParam（PLT 0xf5a90），不假定实际值。只有 `[x22+0x27c]==8` 分支在 `0x15796c` new(0x3b28)，并于 `0x157978` 调构造器 `0x199de4`。否则 `0x157808` new(0x3948)，`0x157814` 调 `0x1b3284`。副 writer 总在 `0x15799c` new(0x3948)，`0x1579a8` 调 `0x1b3284`。

| 对象 | 构造器中的 vptr 写入 | RELATIVE 原记录所指 | 实际 initializer |
|---|---|---|---|
| FX6 Xavcs | `0x1b32b4` 存 GOT[0x108de78]+0x10 | GOT→0xf26028；vptr=0xf26038；vptr+0x10=0xf26048（fileoff 0xf16048）→0x1b0ed4 | 原常量 780 |
| FX6 Mxf | `0x199e1c` 存 GOT[0x108e420]+0x10 | GOT→0xf25ef0；vptr=0xf25f00；vptr+0x10=0xf25f10（fileoff 0xf15f10）→0x1940b4 | 原输入 u16 |
| FX3 此路径 | `0x11b9dc` 构造器设 vptr；Integ 直接调用 initializer | GOT[0x2fa3a0]→0x2f46f0；不需要猜测间接 initializer | `0x11975c` 直接保留输入 |

两版对象构造器先将时间成员清零：FX3 `0x11bb6c`、FX6 Xavcs `0x1b33f8`、Mxf `0x199ffc`。然后 initializer 覆盖为有效值；**不能把构造器零值当成合法“禁限时”协议**。FX6 会先经旧对象 vptr+8 释放再重建，主、副初始化失败均走现存错误分支 (`0x1579ec/0x157a28 → 0x15781c`)。本任务没有替换失败返回。

这些是 ELF 原码和重定位的静态绑定，运行时 GOT/对象身份仍要观测；Init 发生时后续 EnterRec 的实际模式并未由本报告确定。

## 时间作用、单位与通知

FX3 `0x11d178` 保存 this=x25，`0x11dbc8` 读取 writer+0x55c 的帧率枚举，调用原 `ConvertFrameRateToNumerAndDenom`，在 `0x11dbf0..0x11dc08` 形成 float32 的 `s8=numerator/denominator`。`0x11faa8` 调原 `GetEncStatusVideoFrameCounter` 得到 w0 帧计数。

FX6 Xavcs 保存 this=x26，`0x1b4f68..0x1b4f90` 同样形成 s8；Mxf 保存 this=x19，在 `0x198c5c..0x198c90` 形成 s8，另有下述隔行减半。

三条真正消费者均执行同一组算术原字：

```text
FX3 0x11fac8: 79404b22  ldrh w2,[x25,#0x24]
FX6 Xavcs 0x1b679c: 7940eb42  ldrh w2,[x26,#0x74]
FX6 Mxf   0x199494: 7940f262  ldrh w2,[x19,#0x78]
后续六个机器字（三版相同）:
92800761  mov x1,-60
52800780  mov w0,60
9ba20400  umaddl x0,w0,w2,x1
1e281821  fdiv s1,s1,s8        ; s1先由帧计数转换为float32
9e230000  ucvtf s0,x0
1e202030  fcmpe s1,s0
随后 b.lt 跳过通知
```

故有限、正帧率且本次到达比较点时：`elapsed_seconds = f32(f32(frame_counter)/fps)`，`threshold = f32((60*effective_u16-60) mod 2^64)`。分钟单位来自帧数/每秒帧数与乘 60 的数据流，另有 FX6 `0x151580` 读取 manager+0x1454 后使用只读字符串 VA/fileoff `0xcc9eb9`：`recordableTime: %u\n` 支持该命名。780 的阈值是 **46,740 秒（12:59:00）**，1440 是 **86,340 秒（23:59:00）**；它是提前一分钟触发通知的阈值，不是已经完成停止的实测时刻。

触发前还有已通知标志为零、writer stream 字段为零、s8>0 等条件；FX3 读 writer+0x444，FX6 两类读 +0x494。本报告按实际数字条件描述，未凭机型名称赋予 stream 枚举名称。

达到阈值后，三者都调用保存的 callback，实参为：

```text
x0=initializer 参数+8（slot token）
w1=0x40000005
w2=0, x3=0, w4=0
x5=initializer 参数+0x10（此分配路径设0）
```

FX3 指针来源是 initializer 参数+0 → writer+0x38；`0x11fb3c` 调用后存已通知标志。FX6 Xavcs 对应 +0x88、`0x1b683c`，Mxf 对应 +0x90、`0x199514`。静态 GLOB_DAT 分别指向 `CallbackPointForMovieWriter` FX3 `0xda760`、FX6 `0x15d730`。FX3 `0xda860..0xda868` 直接分派到 `RecvWriterEvtReachRecordableTime`；FX6 jump table VA/fileoff `0xcc9b54` 原 halfword `003f`，由 `0x15d7c8+0x3f*4=0x15d8c4` 到达同语义分派。

后续不是空通知：FX3 [0xd6ac4..0xd6c28](fx3_mpr-d6ac4-d6c2c.txt) 创建内部 stop slot 列表，成功才在 `0xd6be0` 调 `EnqueueExecEncStop`；失败走原分支。FX6 [0x15d564..0x15d72c](fx6_mpr-15d564-15d730.txt) 同样创建 stop 列表，但会按 manager+0x9f0 分支至 `EnqueueExecEncStop` 或 `EnqueueExecClipClose`，另按两个 writer 状态筛选列表。FX6 阈值点还比 FX3 多调用 `0x1832cc`、w1=8：它在非空、活动对象上写对象+8，并可能取走+0x10 callback 后调用。**本次只闭合到这些请求/回调边，不宣称两版停止生命周期、通知副作用或硬件完成完全一致。**

摘录：[FX3 比较与发事件](fx3_mpr-11faa8-11fb48.txt)、[FX6 Xavcs 比较与发事件](fx6_mpr-1b6778-1b6850.txt)、[FX6 Mxf 比较与发事件](fx6_mpr-199470-199550.txt)。

## 范围、内存及反例

| 项目 | 原码所能证明的边界 |
|---|---|
| 输入表示 | Init 从 u16 读取、Integ uxth；表示域 0..65535。未在这条保存/initializer 链发现 u16 的业务上限检查，不能推成整个录制系统认可全部值 |
| 阈值算术 | 正值 1..65535 的整型秒阈值为 0..3,932,040；均低于 2^24，转 float32 的阈值精确。帧计数先转 float32，高帧计数精度会变化；不是整数时间比较 |
| 零值反例 | 64 位 umaddl 的 -60 使 0→2^64-60，随后转 float32；并非普通有符号 -60。fixture 不给零值转换许可 |
| 1 的反例 | 阈值为0；其他 guard 满足、到达比较点时零帧也可触发，不能把任意 u16 当等价配置 |
| writer 内存 | FX3 两个 new 大小各0x2c58；FX6 main按构造器为0x3948或0x3b28，secondary为0x3948。选择由 manager+0x27c 分支决定，不由本 u16 决定 |
| 局部循环 | FX3 分配循环按常量1..4、stride0x1ac0；FX6 EnterRec 按1..2、stride0x1c40。仅为本处分配代码事实，不重新解释已交付的通道/count合同 |
| 相关列表容量 | FX3/FX6 Xavcs initializer 的三个 BaseList 实参来自独立 param+0x1c/+0x20/+0x24（此生产路径10000/10000/100），不是 param+0x18。每个 BaseList对象new(0x20)；FX6另外数组new(0x627)、new(0xc8)也为常量 |
| 排除边界 | 上述已追踪分配/参数路径无由本u16控制的数组索引或分配尺寸；不把立即数检索宣称为全程序别名证明 |

`fx3_mpr-24-all-direct-accesses.txt`、FX6 对应 `74/78` survey 是局部直接偏移检索的完整保留结果。FX3 的其他宽读取包含 vector 元素（`0x117670` 的 x19 来自 `[x1]`；`0x117050` 的 x20 来自 vector+索引）、initializer 参数容量 `0x119824`，以及 queued-record 字段 (`0x115bbc/0x119c74/0x11c880`)。已定位后者组包边 `0x11689c`（复制0x80字节并挂0x115b54）、`0x11c78c`（x19=x2，挂0x119bf0）；不凭同一偏移认成 writer 时间字段。若要证明“全程序绝无别名读取”，剩余范围是这两条 queued-record 入口 x2 的来源及其分发实参，不需要泛化成重新分析整个录制系统；这不影响上面三个已直接闭合的成员写入→时间比较反例。

### 已有 fixture 反例

1. 固定 FX6 producer字节 `a0 05` (1440) 分别执行原 initializer 的两条原指令：FX3 得1440，FX6 Mxf 得1440，FX6 Xavcs 得780。副作用仅写目标两个字节，前后哨兵不变。
2. 原帧率转换表 enum2 给25/1；在1,168,499帧尚未到780阈值，**1,168,500帧**时原FX6 Xavcs和FX3(780)触发，FX3(1440)不触发。这已否定“1440全局直传保持原行为”。
3. FX6 Mxf 额外隔行路径也禁止简单类推：`IsInterlaceFrameRate` (`0xcc0400`) 用 `(enum & ~2)==4`，即4/6；两版原帧率表enum4均给50/1。Mxf在`0x198c8c/90`乘0.5成为25，而FX3 Xavcs此处不减半。以同enum、同2,158,500帧为**条件案例**，Mxf(1440)到阈值而FX3 Xavcs(1440)未到；若只改u16并要求同一帧阈值，代数目标是720.5，不能由u16精确表示。这不声称真实系统两条路径一定共享同一个计数域。
4. 转换原型仅接受两个字节、源构造器0x1b3284、目标0x11b9dc、固定输入1440；对Mxf、未知源/目标、短/长记录、零及非固定producer值均抛错，无输出。它不是“先把所有模式改780”的实现。

原指令、表项和这些边界均由 [offline_fixture.py](offline_fixture.py) 读固定输入、核验机器字后进行计算。无外部函数stub，无假造的成功返回，无运行时分支被stub决定。浮点案例限定于有限正fps、round-to-nearest的float32转写；不模拟FPCR/异常，也未验证早期Init、编码器或异步运行。

## 适配判定与最小剩余条件

| 条件 | 该字段判定 | 当前动作 |
|---|---|---|
| 实际后续路径确认FX6 Xavcs，目标固定FX3 Xavcs；同帧率/帧计数域及guard | 用780保持此比较阈值。1440→780是FX6 writer覆盖规则的复现，不是分钟单位换算 | 只有离线两字节原型；尚不修改全局Init |
| 想在FX3 Xavcs主动采用1440上限 | 算术可表示且所追分配不依赖它，但会推迟事件，改变原FX6 Xavcs行为 | 不作为保行为适配放行 |
| 实际走FX6 Mxf（EnterRec时manager+0x27c==8） | 1440是原有效值；但FX3此Init路径不产生该writer，隔行比较和后续事件路径亦有差异 | 显式拒绝；不能默默选Xavcs，不能靠u16独立解决 |
| Init阶段模式/构造器尚未知 | 无法决定哪一个原生覆盖规则适用 | 保持原件，等真实MPR Init观测及具体模式证据 |

下一步应只收集与这条判定有关的边：真实 MPR Init 的 GOT/调用/返回与传入+0x1f2；具体模式 EnterRec 时manager+0x27c和实际构造器/initializer绑定；若要跨 writer 比较，再核对FX3 writer+0x55c、FX6+0x5ac的枚举、帧计数来源、stream字段及已通知标志。真实停止/clipclose副作用仍由对应事件路径单独验证。**本报告没有把其它任务的CAPID失败证据升级成完整Init因果，也不以此u16差异解释当前启动失败。**

## 复核

在本目录执行：

```sh
python3 collect.py
python3 offline_fixture.py
python3 seal.py
```

collect核验原字与输入，fixture执行现有案例，seal核验旧报告和固定输入并重建本目录回执；所有写入仅在本目录。当前结果见receipt：静态字段链及条件转换成立，真实adapter未获放行。
