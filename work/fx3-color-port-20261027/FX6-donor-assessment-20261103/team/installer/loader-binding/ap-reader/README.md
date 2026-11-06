# FX3 原 `im.elf` → `appFw.so` 静态装载边

**结论：闭合一段 FX3 自身原字节的静态边。** 原 `libIMDB.so` 应用表第 143 项保存相对库名 `appFw.so` 与入口符号 `Application_System_Init`；原 `im.elf` 取该表项，按类型 `0x20000004` 进入装载处理，传其库名给 `dlopen@plt`。这说明名字在 IMDB 数据表里，并非必须在 `im.elf` 里出现完整字符串。[脚本](audit_ap_reader.py)只读原文件；[运行回执](receipt.json)含逐项 VA、文件偏移、指令原字节、重定位、原件 SHA。

原件与对象身份：`im.elf` SHA256 `5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91`；`libIMDB.so` SHA256 `6ceaea432bc7c4645897c2f1272941b33b0c04115ec62ffa000b37faf3d8517d`，来自 FX3 p15 `/lib/libIMDB.so` 的[既有原字节投影清单](../../../../../../fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v5/projection-manifest-full-v5.json)；`appFw.so` SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。`im.elf` 的 `DT_NEEDED` 包括 `libIMDB.so` 和 `libdl.so.2`。

| 原字节节点 | 绑定 |
|---|---|
| `libIMDB.so` 导出 `imdb_raw` VA `0x1CD38`；`IMDB_get_entries` VA `0x9B1C` 返回 `raw+0x100` | 72B 表项第 143 项 VA `0x1F670`、文件偏移 `0xF670`，头 `kind=0x20000004`、`target_mask=0xFFFFFF9F`、`field14=0`。`+0x10` 和 `+0x18` 两个 `R_AARCH64_RELATIVE` 分别指向 VA `0xB95C` 的 `appFw.so` 和 VA `0xB965` 的 `Application_System_Init`。 |
| `im.elf` VA `0x406564` | `BL IMDB_get_entries@plt`；按 `0x48` 步长取条目。VA `0x4065F0` 到 `0x406374`，后者 VA `0x40639C` 调 `IMDB_find_entry@plt`。 |
| `im.elf` VA `0x4064A0` → `0x4061EC` → `0x406284` → `0x405E24` | 从找到的条目进入分派；比较 `kind=0x20000004` 后进入该类装载处理。 |
| `im.elf` VA `0x405E3C`、`0x405EA8`、`0x405EAC` | `LDR X20,[X0,#0x10]` 原字节 `140840f9` 取表项库名；`field14=0` 时 `CSEL` 将 X20 置于 X0；`BL` 原字节 `a9f0ff97` 至 `dlopen@plt` VA `0x402150`，其 `R_AARCH64_JUMP_SLOT` 在 `0x4190F0` 指向动态符号 `dlopen`。若打开成功，VA `0x405F0C` 通过 `dlsym@plt` 取 `+0x18` 的入口符号。 |

既有 FX3 VM 的 [AP94 日志](../../../../../../fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r3center-f3bba0ba/serial.log) 第 10269 行出现 `FX3_PROVIDER_CALLER module=/usr/lib/appFw.so`，是该 VM 中映射/运行的旁证；日志不提供同次完整映像 hash，也不证明当前机身冷启动选择、WBI 快照、真实相机运行内存与盘一致。静态条件分支是否在每次启动都选中第 143 项仍须按具体启动模式核对。

复现：从 Mac 项目根运行 `python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/loader-binding/ap-reader/audit_ap_reader.py > work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/loader-binding/ap-reader/receipt.json`，实际 exit `0`。本阶段没有运行原二进制、VM 或设备；CP 文件读取链未涉及。
