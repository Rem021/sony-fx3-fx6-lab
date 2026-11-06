# Base ISO 未注册路径：dirty 位到首个真实读取者

**终局结论：FX6 固定原件证明 `0x3662` 在未注册路径写入两张 dirty 位图，且聚合调度器确实读取其中一张并清除它；未证明调度器的运行时索引列表含 `0x3662`。** 因此这条 Base ISO 研究线在 IPC/消费者处收束为**未闭合**：没有可核的序列化字段、长度、setter 参数或另一侧读取，不能用日志或位图地址替代通信证据。全部为文件静态证据，未运行 VM/设备。

## 固定输入与复现

FX6 `team/donor/nflasha15-files/lib/appFw.so` SHA256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`；FX3 原 `work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so` SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。脚本先核两个完整摘要，再按各自 ELF `PT_LOAD` 作 VA→文件偏移映射；[回执](receipt.json)逐点列出 39 条 FX6 指令和 5 条 BL 的 VA、文件偏移及小端原字节。执行：

```sh
python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/ap-abi-comparison/base-iso/dirty-consumer/audit.py > work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/ap-abi-comparison/base-iso/dirty-consumer/receipt.json
echo "audit exit=$?"
```

实测 `audit exit=0`。[audit.py](audit.py) 只读两个本地原件；反汇编复核可用 `xcrun llvm-objdump -d --start-address=0x10f5824 --stop-address=0x10f5948 <FX6 appFw.so>`、`--start-address=0x10f5a88 --stop-address=0x10f5bec`、`--start-address=0xde35c4 --stop-address=0xde3634`、`--start-address=0xdfa618 --stop-address=0xdfa648`。本报告所列 FX6 代码 VA 恰与文件偏移相同；**这不是整个 ELF 的通则**：前阶段 `.init_array` 槽 VA `0x29113A8` 对应文件偏移 `0x29013A8`。前阶段列出的 11 个 `ADRP` 加八指令内 `LDR` 只是**候选引用模式**，未逐条排除目标寄存器被中间指令改写，也不构成完整别名/写入覆盖。

## 模型到首个真实读取者

| 阶段 | VA、原字节与参数/偏移 | 静态结论 |
|---|---|---|
| 模型写入 | 既有 `base-iso/receipt.json`：`0x1A683C8 BL 0x1A682D0`，W1 为 800/4000/12800；模型 ID `0x3662`，`0x1A6831C STR W20,[X0]` 写主值 | 数值写入已在前阶段核，非日志。 |
| 未注册判定 | `0x11346A0 CBZ X0,0x11346F8`；`0x1134728 LDR W0,[X29,#0x3C]`；`0x113472C MOV W1,#1`；`0x1134730` 原字节 `d6 04 ff 97`，`BL 0x10F5A88` | 在固定初始表没有 `0x3662` 且无后续插入的条件下，传 `W0=0x3662,W1=1`。 |
| 位计算 | `0x10F5A98 MOV W19,W0`；`0x10F5AAC SDIV W0,W19,#64`；`0x10F5AB4 SUB W1,W19,W0<<6`；`0x10F5AB8 LSL X2,1,X1` | `0x3662` → 字索引 217、位 34、掩码 `0x400000000`。 |
| 位图 A 写 | `0x10F5AC0 ADD X1,#0xB08`（页 `0x4DA5000`）；`0x10F5AC4 LDR X3,[X1,X0<<3]`；`0x10F5AC8 ORR X3,X3,X2`；`0x10F5ACC STR X3,[X1,X0<<3]` | 写 VA `0x4DA61D0` 的 bit 34；这是全局内存位图，非包字段。 |
| 位图 B 写 | `0x10F5AD4 ADD X1,#0x108`（同页）；`0x10F5AD8/ DC/ E0` 读、OR、写 | 写 VA `0x4DA57D0` 的 bit 34。W1=1 还使 `0x10F5AF0` 的非零分支执行通知/标记函数，但这些调用未给出线格式。 |
| 首个已证实聚合读取 | `0xDE3614 BLR X1` 从对象虚表 `+0x20` 取指针，`0xDE3618` 原字节 `ab 48 0c 94` 调 `0x10F58C4`；后者 `0x10F58E0 LDR W1,[X2,#0x9C8]` 取动态字索引，`0x10F58EC` 读对象位图，`0x10F58F0` 读全局 A 位图，`0x10F58F4 TST X5,X1` | 确实消费 A 位图与对象位图交集；运行时列表中有无字索引 217、对象位图 bit 34 是否置位均 unknown，不能说 ID `0x3662` 已被消费。 |
| 调度与清除 | `0xDFA618 LDR W0,[X20]`，仅等于 2 时 `0xDFA628 BL 0xDE35C4`；结果非零才 `0xDFA634 MOV W0,#1`、`0xDFA638 BL 0xDE4244`，后者仅更新一全局状态整数；`0xDFA63C BL 0x10F58B0` 用 `memset` 清零 A 位图 `0x9C8` 字节 | 聚合检测后的状态更新与清理；不证明 Base ISO 专属处理、setter 或 IPC。B 位图不由此处清零。 |

另一个真实读取入口 `0x10F5838–0x10F5858` 对传入的单个 ID 读取 B 位图并返回 1 bit；`0x102EA2C` 调 `0x10F585C` 测试同一 B 位图的动态字索引及掩码，循环至 `W21=0x390`。其调用实参来自运行时记录，不是常数 `0x3662`，不能当成该 ID 的消费证明。`0x10F590C` 可以按运行时对象的索引列表清 A 位，但本轮没有把它绑定到 Base ISO 事件。

## 精确阻断与范围

最早无法闭合的读取边是 `0xDE3614 BLR X1`：X1 从运行时对象虚表 `+0x20` 来，返回的对象在 `0x10F58C4` 提供 `+0xEAC` 的索引数量及 `+0x9C8+4*i` 的动态字索引；固定文件不能证明其中包含 217，更不能证明对象位图 bit 34 为 1。后续 `0xDFA628` 的聚合返回值和 mode==2 也属于运行条件。下一次若获准进行运行时研究，所需最小证据是在原 FX6 运行实例或受控等价环境中记录该虚调用返回对象的索引列表、对应对象掩码、A/B 位图和一次 `0x3662` 状态变动，再从实际被激活的回调追 setter/IPC；**本阶段没有这些证据，不继续把假定的命中路径或字符串扩成移植结论**。

FX3 摘要仅用于锁定对照原件。前阶段已见 FX3 的 Base ISO 资源名及不同的 ID 注册结构，本轮没有发现可将 FX6 dirty 位图地址、调度对象布局或线字段搬到 FX3 的字节证据；兼容性保持 unknown。
