# Init 回调入口合同：局部静态闭合与拒绝式离线子集

结论：本轮指定入口没有证明任何 **必然在 Init 调用线程同步执行的 FX6 AP 回调**；这不等于没有回调。`0x941c4` 与 `IntegEventInit` 实际创建原 MPR 线程，后者没有“等 Init 返回才派发”的门。已有 kind=1 事件可在 Init 返回前进入 `SendIssueEvent`，具体事件和时序仍未实测。本轮闭合了其中 **RecPbTime 的定时 producer → 60B 参数 → 间接回调 → FX6 AP 复制 → MPR 释放**，只实现“录像计时变化、其余字段零”的离线字节转换。尚不足以生成可运行的通用 Init adapter。

本目录只含 host 静态材料与 Python 字节模型，无 VM、原 ELF 执行、相机操作、成功 stub、库替换或固件产物。原 parent/callback-contracts/poweron-contract/init-u16-contract 的 337 个受回执保护文件均复核未变。未重做 count、u16、PowerOn 或 57 项表；这些旧结论与原有未知仍保留。

## 入口覆盖矩阵

地址均为未加运行 bias 的 ELF VA，精确 fileoff、原字节、指令和 RELA 在 [evidence.json](evidence.json)。只把实际指令当证据；objdump 的“最近导出符号+偏移”不作函数名证明。

| Init 路径 | 实际行为、实参和生命周期 | AP 回调结论 / 仍未闭合边 |
|---|---|---|
| `b6d78/b6e1c → b5628..b56e8` | 同步 OSAL 请求：分配 16B，目标 `0x94016a`；四个 u32 为 `{w0,w1,3,w2}`，source=`w4`。Init 实参分别为 `{0x940021/0x940022,0x11d,d,d}`，`d=[fp+5c]` 来自 dynamic-id 流程，`x3=fp+78` 是响应副本地址。仅 send 返回 0 且 x3 非零时复制 16B；分配成功后发送失败也释放，返回真实分配/send 的 w20。 | 完整本地函数没有 BLR，也没有传 AP 函数指针；不能因邻近符号显示 PowerOnMain 而视为 PowerOn。OSAL 接收者内部是否触发其他队列仍未证明。另一个 `b6dd4` 的 36B 同步请求目标 `0x4b024e` 也是独立外部边。 |
| `b6ff0 → 133554..133560` | x0=GOT `2faaa0` 所指静态 mutex `3b06e8`，x1=0，尾调用 pthread_mutex_init。 | 不注册、不调用 AP 回调；pthread 实现仍属外部依赖。 |
| `b6ff4 → 941c4..942cc` | 首次 flag `2ff0d1` 文件初值 1，先清零；循环 5 次建立 mutex/cond 与 worker。ThreadInfo id119，末 slot id120；info+10=94704，info+18=`36cb48+4*slot`，该静态 u32 写入 slot。`94278` 调用 create，结果未检查。 | 注册的是原 MPR worker，非 AP callback。真实创建结果、已有队列内容未观测；`94834` 才是 worker 的队列间接边。 |
| `b6ff8 → 12f5f8..12f8ac` | 调用 datasize::init `133494→1333a0`，建立 JPG/HEIF/RAW 静态尺寸表，再构造 36B 缓存记录；`1326f4` 查询原表，`12f5b8→12f4a8` 扩容/复制缓存。 | 本地块无 AP callback 槽读或间接调用。Backup_read/nread、分配器与尺寸辅助函数是外部/下层边，不能把本地排除扩大成所有传递调用都无副作用。 |
| `b6ffc → 129790..1297e0` | 循环 4 次，清零 `3aaec8/3aaea8/3aada8/3aadd0` 四组 8B 项与 `3aadc8` 四个 byte。 | 完整函数无调用；这些不是 Init 注册 AP 回调的全局槽，不能解释为清空 callbacks。 |
| `b70a4 → IntegEventInit b3d78..b3df0` | 在锁内检查 active byte；非 active 则 ThreadInfo id118，info+10=IntegEventMain `b521c`，handle 为 s_integEventHandle；**创建前**写 active=1，`b3dd8` create，结果未检查，解锁返回。 | 确切的异步注册边。没有 join/Init-return gate；active=1 不能当线程启动成功。线程入口忽略传入 x0，不能凭未显式写 info+18 就断言 arg=NULL。 |

补充返回边：`b70b0 → b68b0` 还会调用 `b56ec` 发送 8B 诊断记录，`b68c8 mov w0,w19` 后 `b68dc ret`。`b56ec..b5810` 是复制调用者数据到 OSAL 消息（正常目标 `0x8f013a`，错误支路同步目标 `0x8f0313`），不直接调用 AP callback；其 `b5758/b57cc→b5560` 和外部服务仍是有限未解析边。本报告不宣称所有 Init 分支返回 0。

对应原文：[同步请求](fx3_mpr-b5628-b5750.txt)、[同步调用者](fx3_mpr-b6d34-b6e30.txt)、[mutex](fx3_mpr-133554-133564.txt)、[广播创建](fx3_mpr-941c4-942d0.txt)、[数组初始化](fx3_mpr-129790-1297e4.txt)、[事件线程创建](fx3_mpr-b3d78-b3df4.txt)、[诊断发送](fx3_mpr-b56ec-b5818.txt)。datasize 的三个构表函数及其缓存 helper 保存在同目录的独立地址片段中，不重新输出全库反汇编。

## 两个线程边如何到达回调

**广播队列**：GOT `2f9438` 的 RELATIVE addend=`94704`；worker 从静态 arg 读 slot，队列为空则在 `94780..94798` 等 cond。取到记录后，`94828 ldr x1,[x22,#15d8]`，非零时 `94830 mov x0,x22; 94834 blr x1`。返回后推进记录、必要时释放队列块（`94838..94898`）。因此其参数是队列记录借用指针，不能跨消费完成保留；`+15d8` 是原 MPR 工作函数，不能直接套 AP 单指针合同。旧 PowerOn producer 可以把 PowerOnMain 放在这里，但本轮 Init 本体没有直接调用广播 enqueue `942d0`，无法证明该 producer 在 Init 期间发生。

**事件线程**：GOT `2fa250` 的 GLOB_DAT 符号为 `IntegEventMain`，默认定义 VA=`b521c`；active 位为 `3732d0`，hmsState 为 `372ca4`。这些是链接默认定义，运行时 interposition/GOT 仍需另一 worker 观测。

`GetIssueEvent` 非空队列通过 `b4420 GetEventParam(&kind,&event,&p)` 取出事件。state=0 且队列为空才无限 wait；state=0 遇 kind=1，在 `b5314..b531c` 直接以 w0=event、x1=p 派发。state=1 的 kind=1 在 `b5290..b5298` 同样派发。这里没有读取 Init 是否返回的状态。kind=0 才使 state=0 进入计时模式；state=1 计时差超过 99999µs 时走 60B timer producer。不能推断“创建线程后立刻有 timer”，也不能以约100ms间隔保证 Init 不会重入回调。

原文：[广播消费](fx3_mpr-94704-94880.txt)、[消费后的生命周期](fx3_mpr-94828-94898.txt)、[GetIssueEvent](fx3_mpr-b434c-b442c.txt)、[完整事件线程](fx3_mpr-b521c-b5410.txt)。

## 闭合的真实子边：RecPbTime，只限录像计时记录

### 注册、分派与所有权

复用旧 matrix 中已固定的 producer：FX6 AP `212f5f8` 把回调 `212b720` 写入 initParam+168；FX3 consumer 读取的是 initParam+130。`b6b4c ldr x1,[x19,#130] → b6b50 GOT2fa470 → b6b54 str x1,[x0]` 注册至 `gp_evtRecPbTimeFunc`，默认符号 VA=`373238`，size=8。所以未来 adapter 必须重排对应槽，不能整块复制 Init 参数，也不能用同名消除错位。

事件 `0x1022` 的旧 jump-table 项 `2cb43c` 原字节 `9b01` 选中 `b4acc`：经 GOT 取出 callback，非 NULL 才 `b4adc x0=x19; b4ae0 blr x1`。调用者 `SendIssueEvent` 的 x19 就是输入 x1=p；没有第二个稳定的 callback 参数。回调返回值不被使用，**C++ 返回类型仍未证明**，不可生成“全返回0”实现。`b4ae4` 转公共尾部 `b4488..b4494`，对原 p 调用 free。

timer producer `b5364` malloc(60)，随后逐项清零完整60B，`b5394 SetRecPbTimeEvent(p,false)` 在锁内写记录；仅 flags+4/+14/+24/+30 任一个非零或 endHms 置位才以 event1022/p 派发，否则 `b5408 free(p)`。FX6 原生相同 timer 分配60B（`129c2c`），但 header/event 为1029。这里只证明该 producer 来源的60B；其他调用者不能仅凭相同事件号推定长度。

FX6 回调 `212b720..212b804` 保存 p 于 x19，只读取它并复制 scalar；没有把 p 传入下层/保存到全局，没有 free(p)。录像分支创建自己16B消息，之后走原 AP `1a6f4ac` 队列路径。`1a6ede0` 实际是原 AP 池分配包装器（尾至222b1c4），不是可替换的 malloc；`1a6f4f8` 入队的是新消息指针。故原 p 只需活到回调返回，原 MPR 随后 free 正常；新消息由 AP 队列持有，最终释放路径本轮未追，不应由 adapter代管。

### 字段与对照

| 字段（LE） | FX3 producer / FX6 原生 producer | FX6 AP consumer | 本轮允许 |
|---|---|---|---|
| p+00 u32 | `b5028/1286c4` 分别写1022/1029 | 整个叶函数不读取 | 离线规范化为1029；仅调用此 AP 叶函数时，此改动不是必需的行为修复 |
| p+04 u8 | 编码 counter 与缓存不同才置1，原码 compare/branch 后更新缓存 | `212b730` 非零时创建录像消息 | 限精确1，不代造“变化” |
| p+08 u32 | recordingFramePerSecX10000；`b3e38/12844c` | 复制到新消息+4 | 原样保留32bit，不缩放 |
| p+0c u32 | imagingFramePerSecX10000；`b3e48/12845c` | 复制到新消息+8 | 原样保留32bit，不缩放 |
| p+10 u32 | GetEncStatusVideoFrameCounter 的 w0；`b3e24/128438` | 复制到新消息+c | 原样保留，包括0/回绕；不臆造帧计数范围 |
| p+14 u8；+18/+1c/+20 u32 | 播放变化标志、三个播放标量 | 标志非零时创建24B消息0xdf；计算 `frames*10000/rate`，rate=0 调用断言 | **全部排除**；以下原码差异使同尺寸不足以通过 |
| p+24/p+30 与相关数据 | 两个音频分支；本轮未追 | 此 AP 叶函数不读取这些音频字段 | 子集要求整个尾部全零；不以“AP没读”就吞掉未知事件语义 |
| padding +5..7、尾部未用字节 | timer malloc 后显式清零 | 不读取 | 保守要求零，不假设任意 padding 也是此 producer |

三个 scalar 的对应不是仅凭同名：双方原 `SetMovieRecTime` 均为 GetEncStatusVideoFrameCounter→与 u32 缓存比较→同一偏移写入，两个 FPS 字段均从 4B 全局读入；全部 GOT 原 RELA/符号 size、原指令列入 evidence。这里证明 **相同 primitive 状态输入的字节投影一致**，没有证明运行时两个 Codec 状态源已绑定为同一物理/软件状态。FPS 单位由原符号 X10000 与邻近播放消费的10000缩放共同支持；记录分支本身只复制，无除法、范围检查或枚举转换。

具体反例边界：FX6 `SetMoviePbTime` 在 `128564/128568` 减去 `0x15000+0xf90=90000`，`12856c..128580` 又按状态+1c选择是否减半；FX3 对应函数经原 Convert90kHzToFrameCount 路径计算。未证明这两个状态/时间基准等价，所以禁止对带 playback 标志的记录做无条件 byte-copy。这个缺口局限在播放 producer/状态源，不能泛化成必须先理解整个录制系统。

原文：[FX3录像写入](fx3_mpr-b3df4-b3e58.txt)、[FX6录像写入](fx6_mpr-128408-12846c.txt)、[FX3总记录](fx3_mpr-b5010-b50b0.txt)、[FX6总记录](fx6_mpr-1286ac-12874c.txt)、[FX6 60B分配](fx6_mpr-129c2c-129cd8.txt)、[FX6完整回调](fx6_ap-212b720-212b808.txt)、[FX3播放producer](fx3_mpr-b4ed8-b5010.txt)、[FX6播放producer](fx6_mpr-12846c-1285e8.txt)。

## 离线原型、原字门与反例

[record_subset.py](record_subset.py) 只接收 immutable bytes，要求长度60、header1022、record flag精确1、+5..7与整个+14..3b为零，输出新 bytes，仅把 header改1029。它不调用 callback、不创建线程、不写ELF、不发送AP消息。`project_fx6_record_message` 仅供核对原 AP 分支产生的 `{0xec,recordFPS,imagingFPS,counter}` 16B投影。

[test_subset.py](test_subset.py) 从固定原 ELF 的 MOVZ、STR/STRB 原字解码记录尺寸、header和写偏移，两个 producer 的同状态条件案例比较输出，再核对 FX6 consumer 的实际 LDR/STR 原字。零填充与 changed-counter 路径按已展示的原码转录；这是条件字节模型，不是模拟执行完整 ELF。没有 stub，也没有 stub 决定分支；fixture 明确给出 previous!=counter 前提。

4个正例覆盖普通帧率、不同两种帧率、counter回绕到0、u32全1边界；后三者不声明运行可达，仅验证原码无截断/强加范围。12个拒绝例覆盖长度59/61、mutable输入、错误event、flag0/2、padding、playback/audio标志、隐藏播放scalar及尾部非零。原输入哈希与逐字节结果见 [fixture-results.json](fixture-results.json)。字节模型无法证明活指针的映射、分配长度和来源；未来原生adapter必须先有该来源合同，不能盲读60B做“验证”。拒绝是 host 异常，不映射为 guest 成功或吞掉回调。

复核命令（所有输出仍只写本目录）：

```sh
python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/capid-init-portability/init-callback-entry-contract/audit.py
```

## 下一份可执行窄 adapter 仍缺的必要合同

1. **真正调用与绑定**：另一个 worker 的真实 mpr::Init 调用、GOT/返回、load bias证据仍是前提；不能由本报告静态定义替代。旧 count/u16与 PowerOn 条件合同继续沿用，不做新的默认取值判断。
2. **Init期间实际事件集合及来源**：只需先观测下面两个事件派发口和一个广播间接口，从 Init通过count门到真实返回，带线程ID/时间/调用深度/事件号/producer来源。已经能到达AP的非本子集事件，按真实目标逐个闭合。没有必要先补全57项；但当前也没有证据允许把其余回调清空、统一签名或延迟到返回后。
3. **同步外部服务重入边**：b5694、b6dd4，以及诊断发送服务的接收方/返回和是否排队尚未绑定；本地“没有BLR”不能排除它们触发事件。旧图中的 RecMovie/Audio/PlayMovie `SetCbFunc`（d6078/aa9fc/fca34）注册的是内部 Codec 回调，不能直接当FX6 AP回调；若观测显示它们在该时间窗产生AP事件，只追对应 producer 与 payload。
4. **新子集的 live provenance 与并发**：只对已证60B timer来源、目标确为212b720且数据在锁保护下稳定的录像-only事件使用临时转换记录；转换记录活到原FX6 callback返回。重入/concurrent callback 状态及 AP allocator/queue 是否已初始化尚未知。不能把 synthetic fixture当真实 event，也不能把原型升级成当前可部署 adapter。

不要求为了这个窄入口先闭合播放/音频后续全部功能。若窗口中出现那些事件，才需要补对应producer语义；若窗口中没有出现，也只能约束该次运行及其覆盖条件，不能证明所有启动路径都不存在。

| 最小观测点（未执行） | 需要记录什么 / 它消除的缺口 |
|---|---|
| `b5694` 与 `b5698`、`b6dd4` 的返回点 | 实际OSAL目标、16B/36B请求与响应、返回值；辨认外部请求是否引出callback/queue，不改变原返回 |
| `94278` 前后、`94834` | create实际结果、entry=94704/arg、threadID；间接目标x1与x22来源及slot；不能从entry猜AP签名 |
| `b3dd8` 前后 | entry/handle与实际创建结果，activeflag不能代替结果 |
| `b5298`、`b531c` | w0=事件、x1=payload、kind与queue producer、线程和相对Init返回时间；这是最小候选事件筛选点 |
| `b53f0`、`b4ae0`、`b4ae4` | timer来源确认、60B原记录、实际回调地址/返回完成；与malloc/free配对，验证本子集是否出现 |
| `b68c8..b68dc` | 真实返回w0与时间，与另一worker的Init调用绑定合并；不是把此处改成0 |

## 固定输入与交付索引

| 输入 | SHA256 |
|---|---|
| FX6 appFw.so | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| FX3 appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| FX3固定CAPID helper | `cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e` |
| FX3 libmpr.so | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` |
| FX6 libmpr.so | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` |

[receipt.json](receipt.json) 保存输入真实路径、旧回执哈希与逐文件复核、新交付哈希、测试计数和边界。[evidence.json](evidence.json) 保存所有片段逐指令 VA→PT_LOAD→fileoff→小端原字验证与关键重定位；本轮41个有界片段、2201个去重指令字。`trace.py` 只接受明确起止地址，默认拒绝全库反汇编。相邻函数尾部落入片段的内容不会被当成指定函数的行为。
