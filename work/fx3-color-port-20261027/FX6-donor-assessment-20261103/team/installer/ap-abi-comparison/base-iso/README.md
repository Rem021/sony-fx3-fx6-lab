# FX6 Base ISO：模型写入到注册表分派的静态边

2026-11-03。**本轮闭合了 FX6 原 `appFw.so` 内一个 Base ISO 模型写入及其后续取值分派，尚未闭合 IPC 字段、长度或消费者。** 所有地址、字节和表槽来自固定 SHA 的 FX6 原件；这是文件静态证据，不是 FX3 VM、冷启动或实机身份/行为证据。没有运行原二进制、操作设备或制作安装器。

## 输入与复现

- 来源：同级 `team/donor/README.md` 的官方 FX6 6.01 BODYDATA.DAT 解包；`team/donor/nflasha15-manifest.json` 中 `stored_path=lib/appFw.so` 对应 `team/donor/nflasha15-files/lib/appFw.so`。本轮输入 SHA256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`，ELF64 little-endian AArch64。
- 在项目根运行（只读输入，输出仅本目录）：

```sh
BASE=work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team
python3 "$BASE/installer/ap-abi-comparison/base-iso/audit.py" "$BASE/donor/nflasha15-files/lib/appFw.so" > "$BASE/installer/ap-abi-comparison/base-iso/receipt.json"
echo "audit exit=$?"
xcrun llvm-objdump -d --start-address=0x1a682d0 --stop-address=0x1a68478 "$BASE/donor/nflasha15-files/lib/appFw.so"
xcrun llvm-objdump -d --start-address=0x1134678 --stop-address=0x1134758 "$BASE/donor/nflasha15-files/lib/appFw.so"
xcrun llvm-objdump -d --start-address=0x1537058 --stop-address=0x15370e8 "$BASE/donor/nflasha15-files/lib/appFw.so"
```

实际 `audit exit=0`；[receipt.json](receipt.json) 核对 39 条指令原字节、5 字节分支表、三个 ID 槽和它们的 `R_AARCH64_RELATIVE` 加数。`python3 "$BASE/installer/ap-abi-comparison/base-iso/audit.py" /dev/null >/dev/null; echo $?` 实测输出 SHA 拒绝并返回 `1`。脚本只读本地文件，不调用固件代码。ELF 首个 `PT_LOAD` 令以下代码 VA 等于文件偏移；表槽的 VA/文件偏移则分别列在回执中。`llvm-objdump` 对巨大未剥离区显示的统一符号 `Application_System_Init+...` 不是这些局部函数的函数名，本报告按原 prologue/return/分支恢复边界。

## 生产者、输入与真正的值写入

`0x1A68344` 是该局部函数入口（`a9b97bfd`, `STP X29,X30,[SP,#-0x70]!`），`0x1A683F0` 返回；后置 case 块延续至 `0x1A68474`，下一函数在 `0x1A68478` 以新 prologue 开始。函数没有从入口参数直接取 Base ISO 值：`0x1A6836C` 调 `0x14DE0A8`，`0x1A68370` (`b9400001`) 从其返回的全局指针 `[X0]` 读取枚举 W1；该指针计算为 VA `0x4DD7CB0`。`0x1A68374` 将其与 4 比较。`0x1A6837C–0x1A68390` 读取 VA `0x2535DAC` 的原字节 `25 00 10 18 25`，从 `0x1A68394` 按有符号字节乘 4 跳转：

| 枚举 | 目标 VA | 写入值 |
|---:|---:|---:|
| 0、4 | `0x1A68428` | W1=`0x320`，800 |
| 1 | `0x1A68394` | W1=`0x3200`，12800 |
| 2 | `0x1A683D4` | 本函数不执行模型写入 |
| 3 | `0x1A683F4` | W1=`0xFA0`，4000 |
| >4 | `0x1A6845C` | 诊断日志，随后清理，不写入 |

三个写入分支均调 `0x1517898`/`0x15178AC` 取得模型对象的两块全局值存储 VA `0x4ED22D8`/`0x4ED22E0`，把两指针放入局部对象 `[X29+0x50]`/`[X29+0x58]`，把模型 ID `0x3662` 放在对象 `+0x10`（栈位 `[X29+0x60]`），清 `+0x14/+0x15` 标志。共同边 `0x1A683C4 MOV X0,X19`（X19 指向该局部对象），`0x1A683C8` 原字节 `97ffffc2` 调 `0x1A682D0`，其中 W1 是上述实际 ISO 数字。

`0x1A682D0` 入口保存 `X0→X19`、`W1→W20`；`0x1A682E4` (`b9401001`) 读对象 `+0x10` 的 ID。`0x1A6830C` (`b9000014`) 将 W20 写至 `[ [X19+8]+8 ]` 指向的 32 位单元，`0x1A6831C` 同字节将 W20 写至 `[ [X19] ]` 指向的 32 位单元，并在 `0x1A68314/0x1A68324` 标记对象 `+0x15/+0x14`。这条边包含数值写入，不依赖诊断字符串推断。`0x1A6845C` 的引用字符串 VA `0x25364F8` 为 `static void model::model_extern::extern_BKID_APP_EXTERN_BASE_ISO()`；`0x1A68470` 调 `0x2167784` 是非法枚举分支的日志调用，不是设置调用。枚举全局值由谁写入，本轮未追到；故入口生产者只能确认为模型外部回调，不归因于特定 FX6 菜单动作。

## 后续取值、已解析表槽、未解析边

`0x1A683CC` 再令 X0 指向局部模型对象，`0x1A683D0` (`97f9204c`) 调 `0x18B0500`。后者读取 `+0x14/+0x15` dirty 标志；其 `0x18B0528` (`b9401000`) 从对象 `+0x10` 读取 ID `0x3662`，`0x18B052C` (`17e21053`) 尾跳 `0x1134678`。这个跳转是通知/分派链，不足以称为 IPC 发送。

在 `0x1134678`，W0 ID 被保存于栈，`0x113469C` (`97ff0849`) 调 `0x10F67C0` 查运行时注册表。命中分支的 `0x11346AC` (`94100a79`) 以原 ID 调 `0x1537090`。分派指令 `0x15370A4 LDR X0,[X0,#0x20]`、`0x15370A8 BR X0` 的表基 VA `0x29C7668`、步长 `0x30`；ID `0x3662` 的 `+0x20` 槽 VA `0x2A6A8E8`（文件偏移 `0x2A5A8E8`），原 8 字节 `94 1e 45 01 00 00 00 00`，`R_AARCH64_RELATIVE` 加数 `0x1451E94`。目标的 `0x1451E98 LDR W0,[X0,#0x2D8]` 读取 VA `0x4ED22D8`，正是上述模型主值。其同一 ID 的 `+0x10` 槽 VA `0x2A6A8D8`，原字节 `7c 1e 45 01 00 00 00 00` 指向 `0x1451E7C`，该函数在 `0x1451E88/8C` 将 W0 写到 VA `0x4ED22D8/0x4ED22E0`。这只是表中可解析的对应 setter；当前链没有证明它被调用。

**首个未闭合的运行时分派**：注册表命中与否取决于 `0x113469C` 的运行时结果。若命中，`0x11346CC` (`b9400660`) 从查得项派生的 X19 `+4` 读后继模型 ID，`0x11346D4` (`94100a7d`) 调 `0x15370C8`；其 `0x15370DC LDR X2,[X0,#0x10]`、`0x15370E4 BR X2` 用这个**运行时 ID**取表槽。原件固定了查表算法，却没有固定该注册表项的存在、后继 ID 或链中间的过滤分支，因此不能给 `BR X2` 唯一目标。未命中时 `0x11346FC` 走 ID `0x3662` 的 `+0` 槽（目标 `0x1476CDC` 返回 0），然后 `0x1134730` 调 `0x10F5A88` 标记 ID 位；这同样不能证明传出 IPC。

**IPC 字段、长度、消费者均 unknown。** 本链只证实 FX6 AP 本地 32 位数值模型、通知读取和一个条件性运行时分派；没有从 `0x15370E4` 闭合到通信 API，不能把全局存储偏移或 `0x3662` 直接当作线路字段。下一精确静态动作是追 `0x113469C` 注册表的 `0x3662` 项插入点，恢复其后继 ID/过滤标志，再按该 ID 的 `0x15370C8` 表槽继续查 setter，直至出现可核对长度、序列化字段与另一侧读取的真实 IPC 调用点。FX3 是否有同语义模型与消费者，需另行以其原字节核对。
