# CAPID 初始化移植：producer 已定位，AP→MPR 结构 ABI 不兼容

2026-11-03。**静态交付完成，不能发布运行补丁。** 新增定位是原 `libmpr.so::capidtbl::Init/SendCapIdTblCommand`、FX6 AP 的真实参数 producer、冷启动调用顺序，以及固定 FX3 `mpr::Init` 首个输入字段误读条件。两代 CAPID 初始化 opcode、五字表头和同步布局相同；主要已证差异在上层 `mpr::initInParam`，不能只挪 count，更不能给 helper 手写 initialized=1。

本次只读原件，只写本目录，没有启动 VM、写 CPIO/DTB/helper/init 或制作可运行 firmware。固定 FX3 kernel、DTB、17 helpers、QEMU、env 全不变；未来适配只能发生在 FX6 上层。项目入口与卷 UUID 已核对，Mac 根不是 Git 仓库。

## 复核入口与固定输入

- [receipt.json](receipt.json)：原件哈希、CPIO 成员身份、VA→fileoff/机器字、原串口行和字节偏移、直接调用和重定位调查、离线字段 fixture。
- `python3 analyze.py`：仅重做静态检查并写本目录；实际 CPIO 用内存解析，不提取/修改成员。
- `python3 fields.py`：[callback-fields.json](callback-fields.json) 与 [CALLBACKS.md](CALLBACKS.md) 给出 **57 个 FX3 输入回调、75 个 FX6 输入回调** 的原始 load 指令、GOT 地址和重定位符号；57 个 FX3 目标均找到 FX6 同名目标，FX6 另外18个。它们不是已验证的可执行转换表。
- `*-mpr-param-producer.txt`、`*-init-gate.txt`、`*-capid-init/send/map/sync.txt` 是小段原反汇编；两份 `*-init-field-consumer.txt` 保留完整字段消费范围。早期 `*-1003-survey.txt` 是排查材料，**同数字常量不表示 CAPID**。

| 原件 | SHA256 |
|---|---|
| FX6 AP | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| FX3 AP | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| 固定 CAPID helper | `cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e` |
| 固定 FX3 libmpr | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` |
| FX6 供体 libmpr（只比较，未替换） | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` |

固定三入口 CPIO `bb618bd2…` 内 `usr/lib/libmpr.so` 成员偏移 `0xa1c7d8c`、长度3517008，逐字节 SHA 与 FX3 libmpr 一致。最新 `ap-ro-f58ad0fb/serial.log` 确有 `/usr/lib/libmpr.so` maps；**映射存在不证明本轮 FX6 PLT 已解析并调用它**。二进制输入前后 SHA 一致。

## 原调用对象、顺序与 producer

FX6 原字符串 `0x25ac4c0` 为 `virtual void model::sequence_cold_boot::run()`，`0x25ac4f0` 为 `void model::sequence_cold_boot::init_hdmi()`，源字符串 `0x25ac49d` 为 `sequence/sequence_cold_boot.cpp`。原 `run` 地址 `0x1cd826c`，其 x0 保存到 x23，即 sequence 对象；读取对象 `+0x38`，`+0x18` 传给前置查询，结束时读取 `+0x10`，不擅自为这些字段命名。

原虚表地址点 `0x2ec5ef0`（file `0x2eb5ef0`）前有 offset-to-top=0 与 RTTI `0x2ec5ec8`；地址点 `+0x10` 为 `run=0x1cd826c`，前两项为析构入口 `0x1cd8074/0x1cd8088`。析构原码从 GOT `0x2ee45a8` 取虚表基址再加0x10写入对象 `[x0]`；具体动态 GOT 内容、调度器对该对象的本次虚调用未读回。

`run` 成功路径的静态顺序：

1. `0x1cd8580`（`1b161094`）→ `0x20dddec` wrapper → `0x20dde14` → `0x212f470` 参数 producer → `0x212f7b8` → `mpr::Init@plt 0xb174c0`。
2. 后续检查和调用成功后，`0x1cd86a4` → `init_hdmi 0x1cd80dc` → `0x1cd80fc` → wrapper `0x20d00bc` → `0x20f158c` → 原首个 `0x32d` 请求。

因此这条原冷启动路径**先 MPR 初始化再 HDMI**；不是现有证据支持的“把顺序交换即可”。另有3处直接调用 HDMI wrapper，本轮故障究竟从哪条动态路径进入仍需同次栈证据；不能仅用函数地址顺序认定运行路径。

## AP 参数的具体错位

以下 AP 代码均在 `PT_LOAD offset=VA=0`，VA 等于 fileoff；所有列出代码原字见 receipt/反汇编。FX3 producer 为 `0x2e58b98`，x22=`x29+0x38`；FX6 producer 为 `0x212f470`，x20=`x29+0x20`。二者都是栈上普通输入记录，此位置没有 vptr 写入，不能把其第一个 qword 当作 sequence 虚表。

| 字段/动作 | FX3 | FX6 |
|---|---|---|
| 记录尺寸 | 0x1f8 | 0x290（`212f478:025280d2`） |
| 参数基址 | `2e58bcc: x22=x29+0x38` | `212f488:b4830091`，x20=x29+0x20 |
| count u32 | +0x1d0 | +0x268；`212f74c`读原输入[0]，`212f750:a08b02b9`写[x29+0x288] |
| count后四个u32项 | +0x1d4..+0x1e0 | +0x26c..+0x278；循环按实际count拷贝 |
| 后续u32 | +0x1e4 | +0x27c；两代从原输入+0x14复制，业务域未证 |
| UMID构造method u32 | +0x1e8 | +0x280；从输入+0x18 byte非零条件设1，否则保留0 |
| UMID六字节输入 | +0x1ec | +0x284；两次重叠u32拷贝，源+0x19/+0x1b |
| IntegRecordMovieInit第四参数u16 | +0x1f2，producer常量0x30c | +0x28a，producer常量0x5a0；不能直接套用机型语义 |
| 尾部u32 | +0x1f4 | +0x28c；从输入+0x20归一化为0/1/255，Init直接消费未定位 |
| 头部保留区 | +0..+7 | +0..+7；producer清零，不凭此赋予vptr语义 |

最关键三字：FX6 `0x212f698:60000090` adrp x0,0x213b000；`0x212f69c:00803791` add x0,#0xde0；`0x212f6a0:a0fb00f9` str x0,[x29,#0x1f0]。故 **param+0x1d0 是回调 `bias+0x213bde0`**，consumer 的 GOT 符号证明它属于 `gp_evtSetEssenceMarkInPlayFinishedFunc`（FX3对应+0x198）。

固定 FX3 libmpr `0xb6870:60d241b9` 从输入+0x1d0取w0，`0xb6874:1f100071` cmp #4，`0xb6878:49030054` 仅≤4跳至正常分支；否则该分支置w19=3后返回，尚未到 `0xb7014` 的 capid 初始化调用。若上述原 producer 确已执行且该 PLT 解析到固定 FX3库，页对齐 bias 下 callback 低12位0xde0保证被读count>4。**这是条件性原码推导，不是本次实测 Init返回3，也不是实测音频返回-1021。** FX6 AP 在调用后直接退栈，没有本地检查/保存 mpr::Init 的返回值，wrapper随后调用日志函数。

## 实际 CAPID 原码合同逐字段对照

已有 `runtime/capid-file-candidates.json` 与 `capid-mpr-full-proof.json` 已指出 producer 在 FX3 libmpr，原 AP candidate为空；本轮据此扩展到 FX6 libmpr及AP参数，而没有重做已完成的发送断言分析。

| 项 | FX3 libmpr | FX6 libmpr |
|---|---|---|
| Init | 0x13250c | 0x1c9ca8 |
| SendCapIdTblCommand | 0x13133c | 0x1c8b34 |
| GetTblAddr1000 | 0x13255c/560 | 0x1c9cf8/cfc |
| StartAccess1001 | 0x132580/584 | 0x1c9d1c/d20 |
| table header写入 | 0x132590..5a4 | 0x1c9d2c..d40 |
| sync op1 | 0x1325b0→0x12fb28 | 0x1c9d4c→0x1c75cc |
| StopAccess1002 | 0x1325b8/5bc | 0x1c9d54/d58 |
| InitEnd1003 | 0x1325c8/5cc | 0x1c9d64/d68 |

两代控制请求均为目的0x9004015e、24B `{u32 0,u32 command,u64 0,u64 0}`；Get回复 `{u32 1,u32 command,u64 address}`，Start/Stop回复8B，InitEnd不等待回复。FX6 `0x1c8c10/14`构造目的，`0x1c8c94`发送，`0x1c8d34..70`校验回复并提取+8地址。Get/Start/Stop 非零均跳出初始化余下步骤。

两代先取得远端address，再分配0x4014本地shadow（FX3 `0x12fab4`，FX6对应map段），五个u32表头 +0/+4/+8/+c/+10 均写 **1024,1023,1023,1023,0**，entry区域从+0x14起为1024×16B。同步请求目的0x92850750，+0 u64为Get地址，+8 u32 operation=1，+c/+e u16=0，+0x10..+0x20为五个表头字；helper检查与接受该布局。这里未证明新entry的全部原始内存已清零，不把只写表头当作整个表清零。

**额外调用合同差异：** 固定 FX3 `mpr::Init` 在 `0xb7014` 直接调用 capid Init PLT；FX6 `mpr::Init 0x12b3dc..0x12bd80` 同位置 `0x12bccc` 已是 Backup读取，没有该调用。对 FX6 libmpr 全可执行section的直接 B/BL以及RELA addend扫描未找到 capid Init 0x1c9ca8 引用，也没有它的PLT项；不能扩大为“绝无间接/dlsym调用”。FX6仍保留完整capid函数，不能说opcode被删除。

## 最小适配方案与未决项

最小方向是 **FX6上层的窄 `mpr::Init` ABI adapter**，沿原冷启动调用次序转换输入后调用固定FX3原库，并传播真实错误；不修改平台，不提前伪造 CAPID 完成。

可先固定的结构字段只有上述count/四项数组/u32 method/六字节/u16的位置及取值来源；数组元素业务域、两个机型常量含义仍须确认。57个共有回调已有逐项符号偏移映射，其中早期+8..+0x128多数位置不变，后段多处移动（如RecPbTime 130→168、PowerOn150→188、SetEssenceMarkInPlay198→1d0）；**符号相同只证明角色标签一致，不证明函数签名或传入结构相同**。FX6额外18回调、未在Init消费的+0x1d8、保留头尾字段和callback nested ABI仍未闭合。

所以当前不能产可运行adapter，也不能只复制count、截断0x1f8、把全部回调原样复制、清空回调或忽略Init错误。下一静态任务应对57个FX3 consumer的调用实参和FX6 callback的读取字段逐项配对，特别是尺寸/所有权/枚举、回调生命周期；只对已闭合字段实现转换，缺少字段明确失败。若运行确认Init调用、GOT指向和返回并支持此ABI归因，再由runtime owner安排单次集成证据；之后还须真实1000/1001/sync1/1002/1003生命周期、音频发送返回以及新第一失败点，不能以host fixture替代。

## 运行证据边界

两轮FX6旧串口仍只证明1075发送非零；最新观察器未取得所需完整maps块而未读w0/model，虽然普通串口已有libmpr VMA。CAPID未初始化、音频-1021、MPR Init返回3、具体PLT绑定都没有本轮直接运行读回。离线fixture仅验证已知偏移错读，未执行ELF、未合成成功、未写initialized。

原FX3旧log行16079/16143/16147/16156/16206按1000/1001/sync1/1002/1003给出实际成功参考，完整行与字节偏移在receipt；不把这份旧运行复用为FX6成功。

方法参考：2026-11-03查阅 [Arm AArch64 ELF官方规范](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst) 的PT_LOAD/重定位规则；设备私有合同全部来自固定二进制与本地日志，未将网页当作运行授权。
