# FX6 `mpr::Init` 字段投影与拒绝边界

**结论（host 静态与真实快照重放）**：实测 FX6 `0x290` 参数的 `count=2`，四槽原字为 `0x1000,0x1010,0,0`，共有回调中 46 项非空，另有 10 项非空且没有 FX3 `Init` 槽。字段位置可投影到 FX3 `0x1f8`；**当前输入不能交给原 FX3 `Init`**：实际 writer 模式未观测，回调 ABI/生命周期及 FX3 侧初始化副作用未闭合。`convert_for_guest` 始终明确拒绝，`project` 仅返回诊断结构，绝不以 host 预览冒充 guest 适配。

## 固定来源与重放

`audit.py` 逐件核 SHA、从 ELF `PT_LOAD` 换算 VA/file offset、复核 57+75 项原回调载入/GOT 指令、枚举整个 FX3 `Init` 对 `x19` 的直接 load、核真实快照与 AP 调用字；`replay.py` 不重建输入，直接取原 `mpr-ro-b22ccc48/mpr-observation.json` 唯一 `kind=call` 的 `parameter_0x290_hex`。详细 VA/offset/机器字在 [audit.json](audit.json)，全部 57 项登记及拒绝原因在 [replay.json](replay.json)。

| 原件 | SHA256 |
|---|---|
| FX3 `libmpr.so` | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` |
| FX6 `libmpr.so` | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` |
| FX6 `appFw.so` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| 既有 `callback-fields.json` | `aef19dda30c2120538ad4ed66b536b25f01eb94c8326239658b0f5953ff660a5` |
| 历史真实 `mpr-observation.json` | `fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2` |
| 其中原 `0x290` 参数 | `585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1` |

旧实测 AP `VA 0x212f7b8` / file `0x212f7b8` 原字 `429fa797` 调用固定 FX3 MPR 后 `w0=3`。原 FX3 `0xb6870` / file `0xb6870` `60d241b9` 误把 FX6 `+0x1d0` 指针低字当 count；`0xb6874` `1f100071` 比 4，`0xb6878` `49030054` 走保护拒绝。此解释是原指令与实测参数组合的静态归因，历史记录未捕到 MPR 内部分支。

## `0x1f8` 真实读集及对应

以下 VA/fileoff 在这些代码段均相同，由脚本按原 ELF 段头核实。`audit.json` 列出 FX3 `Init` 内每条 `[x19,#...]` 直接 load；实际集合恰为 57 个 8 字节回调偏移 `+0x8..+0x1c8`、控制字段 `+0x1d0,+0x1e4,+0x1e8,+0x1f2`。此外原 `b68ec:77520791` 建 `x23=x19+0x1d4` 并间接读四槽，`b6f94:74b20791` 建 `x20=x19+0x1ec` 供两个 ID 构造器读取六字节。`DbgPrint` 的原实现 `a7600:c0035fd6` 是 `ret`；其他被调函数的全部深层副作用不由这个直接读集证明。

| FX3 读域及原调用 | FX6 原生产域 | 本次实际值与转换判定 |
|---|---|---|
| `+0x8..+0x1c8`，57 个 `ldr x1,[x19,#off]` 后注册全局；原指令见 `audit.json` | 按原重定位目标符号匹配的 57 个偏移，另有 18 个 FX6 专有回调 | 57 共有项中 46 非空、11 原为空；专有 18 项中 10 非空。只能按符号匹配位置，不能原样传指针或清零非空项。|
| `+0x1d0` count：`b6870` 守卫，`b6ccc` 循环，`b7048/708c` 传参 | FX6 `+0x268`；AP `212f74c:600240b9` 从上游取计数，`212f750:a08b02b9` 存入局部记录 | `2`；保留 `2`。原 `0x1d0` 是 FX6 回调地址 `0x7ee3fb3de0`，不能用。|
| `+0x1d4..+0x1e3` 四个 u32；`b6d10:e14640b8` 逐项读 | FX6 `+0x26c..+0x27b`；AP `212f478:025280d2` 定总尺寸 `0x290`，`212f494:0fa0a797` 清零，`212f798:21100091` 在按 count 复制的循环内 | `[0x1000,0x1010,0,0]` 原样保留。msidconv 的 count 循环对尾两项改传 `0xffff`；但 `b7074` 的 Status 按源四项读，`InitStillStatus f42bc` 和 `InitMovieStatus f4358..f4394` 均只把 `0xffff` 视为空，因此两个 0 仍是**有效槽**。电影初始化按 count 只处理前两项。槽 ID 的硬件语义未闭合。|
| `+0x1e4` skip ID：`b6e68`,`b7054`,`b7088` | `+0x27c` | `0xffff`，逐字复制。|
| `+0x1e8` UMID 方法：`b6e6c`,`b6fac` | `+0x280` | `1`，逐字复制；方法枚举语义未扩展断言。|
| `+0x1ec..+0x1f1` 六字节 ID：`b6f94` 建指针，传 UMID/UniversalGroupId 构造器 | `+0x284..+0x289` | `ff:ff:ff:ff:ff:ff`，逐字复制。|
| `+0x1f2` u16：`b7080:63e64379` 传 `IntegRecordMovieInit` | FX6 `+0x28a`；AP `212f498:00b48052` / `212f49c:a0570579` 设置源初值 | `1440`。只有 **真实 writer 模式已证走 FX6 Xavcs 且目标仍是 FX3 Xavcs** 时，才可将有效阈值转为 `780`；本快照无模式来源，故无 guest 预览。Mxf 不能退化为 Xavcs。依据既有 `init-u16-contract` 原 writer 指令。|
| `+0x0..7` 与 `+0x1f4..7` | 头原字及 FX6 `+0x28c..f`，实际尾 `0` | `Init` 直接 `x19` load 集中没有这两域；诊断投影保留原字，不声称深层消费者无读。|

`count=2` 不表示另外两槽不存在：FX3/FX6 Status 都以 `0xffff` 为唯一空哨兵；本次四槽状态均为有效，而 `msidconv::Set` 收到 `[0x1000,0x1010,0xffff,0xffff]`。host 测试同时断言两种路径，既不把 0 造为 `0xffff`，也不把它们解释为真实设备已存在。

## 回调支持表与执行时序

`replay.json.callback_rows` 是显式 57 项支持表：每项带源原地址、源/目标偏移、原是否为空、策略；另列 10 个非空专有项。其中特别需要以下事件合同：

| 已定位角色 | 实测指针 | 原空指针保护 / 边界 |
|---|---|---|
| PowerOnFinished | `0x7ee3fb4064`，非空 | FX3 `b4b74:800240f9` 取、`b4b78:80c8ffb4` 判空、`b4b90:20003fd6` 调；只在 12B `0x1026→0x102d`、原 result=0 且 live waiter/key/echo/所有权经同轮核实时，未来专用 thunk 才能调用 FX6 原地址。FX3 dispatcher 拥有并释放原块，FX6 只能接临时副本；不得吞事件后称 PowerOn 完成。|
| RecPbTime | `0x7ee3fa3720`，非空 | `b4ad4:010040f9`、`b4ad8:81cdffb4`、`b4ae0:20003fd6`；已知 record-only 事件编号 `0x1022→0x1029` 的局部转换条件，播放及 nested ABI 未闭合，当前拒绝。|
| MovieWriteFinished | `0x7ee3fb4a24`，非空 | `b4658:800240f9`、`b465c:60f1ffb4`、`b4674:20003fd6`；已证 FX3 真实分配 32B，而 FX6 回调读到 `0x788`；录制禁用，不能靠空指针保护把它置空。|
| MovieRecAutoDivided | `0x7ee3fa59fc`，非空 | `b46dc:800240f9`、`b46e0:40edffb4`、`b46f8:20003fd6`；FX3 真实分配 32B，FX6 回调读到 `0x780`，同样禁用。|
| 其余 53 共有项 | 42 非空、11 原空 | 函数名映射已证，payload 和生命周期未证；非空不得直接传递，原空保持原空也不能推广为“置空安全”。|
| FX6 专有 18 项 | 10 非空、8 原空 | 没有 FX3 `Init` 槽；若 AP 路径依赖它们，必须在真正调用边界停，不能造空或返回成功。|

FX3 `Init` 守卫后 `b68e4..b6c94` 将回调登记全局，之后才在 `b6ccc` 做 count 循环、`b7014` CAPID 初始化及 `b70a4` IntegEventInit；`b6ff4` 还创建广播队列线程。故**异步事件可能发生在 `Init` 尚未返回时**。任何未来适配层必须在调用原 FX3 `Init` 前完成 thunk 表与原回调地址登记，并持有至少到所有分发/等待者退役的生命周期；不得依赖“Init 返回后再装 thunk”。`PowerOn` 的原 FX6 future 等待者以 key 查表、保留 echo、通知后 erase，必须验证注册先于事件、等待者仍活、未重复通知，否则拒绝。当前没有这些运行态观测。

## 下一步可构建的最小软件兼容层合同（未实现 guest）

1. 在**不改 QEMU/内核/DTB/Backup/固定 helper**的独立候选中，先解决 AP `mpr::Init` 调用处的受控 symbol interposition/veneer 装载方式，静态和运行态都要证明固定 FX3 loader 实际选择适配入口、原 MPR 仍被唯一调用。不能仅添加一个未加载的 `.so`，也不能全局关闭 identity/功能保护。
2. 在适配入口确认 AP ELF/PHDR/load bias 与 `0x290` 参数归属，拷贝 0x290 原字并生成 `0x1f8` 目标字段。保持 count=2、四槽原字、skip/method/node；**必须在 Init 前取得并证明稳定的实际 writer 模式**才能决定 u16。现有 FX6 `EnterRec` 才选择 writer 的指令发生在 Init 之后，单独事后观察其结果不能倒推 Init 时的模式；若没有可证的预先选择或另一个经原码闭合的延后更新接缝，就拒绝转换。槽 ID 语义与必要 FX3 side effect 合同也需独立通过，否则在原 FX3 Init 前拒绝，不提供假成功返回。
3. 对每个源非空共有回调保存原 FX6 地址，目标表填**事件专用 thunk**而非原地址。PowerOn 的 thunk 只在已证 12B/活等待者条件下构造局部 12B 副本，保持 echo/result，调用 FX6 原回调并把原 FX3 块所有权交还原 dispatcher；录制扩展仍拒绝。其余未闭合事件使用唯一可识别的 **non-returning unsupported-entry**：在进入未知 payload 解引用或回调前停止（例如专门的 trap + host 只读现场捕获），不得吞事件、返回 0 或继续启动。仅观察到 trap 不能称 Init 或系统运行成功。
4. 该 stop 必须在原事件分发前可定位且不依赖回调 ABI 参数解释：AArch64 入口处只记录 event/thunk ID、当前线程/PC/LR、栈和参数寄存器原值，host 识别后终止本次诊断。代码/地址身份、异常传递与进程归属须在固定平台单轮验证；若 trap 被 guest 处理或继续执行，判候选失败。[Arm AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst) 只支持基础寄存器传参约定，**不能**由此推断 Sony 的 callback 参数类型、所有权或线程安全。已证明原空的 11 槽保持原空，仅在对应 FX3 原空指针保护确证的事件上允许其原行为；不能推广到全部槽。FX6 专有 10 非空项需按 AP 实际调用边界另设同样的显式拒绝门。
5. 首轮成功标准只限“字段、装载、注册和第一个真实事件停点有记录”；FX3 `Init` 的 OSAL/Backup/CAPID/DMA 副作用、硬件状态、CP/AV/电影像素域均须后续独立验。录制扩展的生产尺寸及所有权未闭合，**不得启用录制**。

目前的第一个实际阻断是**Init 前缺少可证且稳定的 writer 选择**，并列的 guest 装载/事件 ABI 合同也未完成。最小只读观测应先追 Init 前的模式来源及后续变更点，再在同轮读取 `GetMovieRecParam` 返回后的 `movieRecParam+0x1dc`、FX6 `SetEnterRecInfo` 后 manager+`0x27c` 和实际 writer 构造分支，判断前后是否相符；另观测 PowerOn waiter map/回调发生顺序。由 runtime owner 在获批窗口安排，不能从 1440 推模式。若任一值和现有字段合同不一致，停止并保留现场。

## 复现

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/init-field-adapter
python3 audit.py
python3 replay.py
python3 -m unittest -v test_adapter
```

三命令只读原件，只改本目录的 JSON 回执；测试不执行任何未知 ELF，也不启动 VM。`receipt.json` 记录本轮源码/输出 SHA 与测试结果。
