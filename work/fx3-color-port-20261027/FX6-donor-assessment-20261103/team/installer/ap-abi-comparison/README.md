# FX6 6.01 与经典 FX3 7.02：AP ABI 与色彩字段边界

**阶段结论：九个关键 AP 对象均为 AArch64 ELF，但没有一份完整文件 SHA 相同。** FX6 的 IMDB 仍用 `appFw.so`/`Application_System_Init` 条目，表项位置已由 FX3 的 143 移到 FX6 的 151。原指令闭合了一段 FX6 AP 输入结构中的 Colorimetry 枚举到 `dataflowInfraFramework.so` 字节字段的边；**未闭合 Cine EI/白平衡的菜单设置生产者 → IPC/AV 后端**，也未证明这段色彩字段等于 Cine EI 或白平衡。该限制直接阻止把本回执写作完整电影色彩控制移植。

输入：[FX6 供体说明](../../donor/README.md)及 `nflasha15-manifest.json`，用每条的 `stored_path` 读取，保留 9 组大小写冲突原路径；[FX3 原投影清单](../../../../../fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v5/projection-manifest-full-v5.json) 的 `payload_origin=projection-v3-original-bytes-reused`。 [只读脚本](audit.py)逐文件复算清单 SHA、解析 ELF64 AArch64 动态符号/依赖/重定位；[回执](receipt.json)含全部路径、SHA、统计和 VA。复现：在 Mac 项目根运行 `python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/ap-abi-comparison/audit.py > work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/installer/ap-abi-comparison/receipt.json`；实际 exit `0`。没有运行固件、VM、USB 或修改供体。

| 对象 | SHA 相同 | FX6 独有动态导入 | FX6 独有动态导出 | 判读 |
|---|---:|---:|---:|---|
| `appFw.so` | 否 | 215 | 0 | FX6 直接依赖多 `libexpat.so.1`、`libopus.so.0`、`libSoundTouch.so.1`；FX3 独有 `libInfraSKD.so`、`AdjChkConfig.so`、`libGOConnectionManager.so` 等 6 个直接依赖。 |
| `libIMDB.so` | 否 | 0 | 0 | 导出名相同不代表条目索引相同。 |
| `libmpr.so` | 否 | 216 | 1169 | 媒体参数 ABI 显著扩展，不可按相同类名直接替换。 |
| `libInfraSKD.so` | 否 | 2 | 6174 | 大量 FX6 独有导出，目标侧解析和消费者未证明。 |
| `libInfraAvbbc.so` | 否 | 24 | 79 | AV 桥接层差异。 |
| `dataflowInfraFramework.so` | 否 | 0 | 30 | 单个 Colorimetry setter 原 8 字节相同，但整个库不同。 |
| `libbackup.so`、`libosal_uipc.so`、`im.elf` | 均否 | 0 | 1 / 0 / 0 | 启动、设置与 IPC 依赖的整体文件不能混载。 |

数字是 **动态符号名称集合差**，不是 C++ 布局、调用约定、语义、依赖闭包或运行兼容性判定。`appFw.so` 的 FX6 新导入不能由 FX3 同名旧库默认满足；即便共同导入存在，也需逐项核对参数结构与输出。可复用的是 ELF 解析与 IMDB 取表的**分析方法**、该条目字段的结构候选，以及单个 `SetData_Colorimetry(unsigned char)` setter 的原指令语义；不能把 FX6 `appFw`、`libmpr` 或整个 dataflow 库混载进 FX3。

## FX6 原指令：有界 Colorimetry 字段边

FX6 `appFw.so` SHA256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。VA `0x20D1F64` 调用 VA `0x20FA4F0`；后者 VA `0x20FA500` 把输入 X0 保存到 X19，在 VA `0x20FA668` 从 `[X19+0x4C]` 读 32 位值，VA `0x20FA66C` 调 `0x20EE044` 对 0–7 的值做范围检查/枚举转换，VA `0x20FA678` 调 `SetData_Colorimetry@plt`（VA `0xB18160`）。FX6 AP `R_AARCH64_JUMP_SLOT` 位于 `0x2EF19B8`，解析到 `dataflowInfraFramework.so` 导出 VA `0x382EC`。该原函数以 `STRB W1,[X0,#0x1D]` 保存 8 位消费者参数；FX3 对应导出 VA `0x37968` 的这 8 个原字节相同。源结构字段的**上游菜单/模式语义**和此对象之后的 IPC/AV 发送并未绑定。

优先检查了 Cine EI/白平衡线索：FX6 AP 内有 `extern_BKID_APP_EXTERN_BASE_ISO`、`set_white_balance_adjust_each_value_temp` 等函数名字符串，`appFw.so` 与 `libmpr.so` 的动态符号表均声明 `setMetaData_WhiteBalance` 为未定义，但本次关键 AP 库集未给出它的实现或具体调用参数。Base ISO 函数名字符串 VA `0x25364F8` 的原指令引用在 VA `0x1A6845C/0x1A68464`，并于 VA `0x1A68470` 调 `0x2167784`；该边是**诊断字符串使用**，不是参数写入。**下一精确静态动作**：以该引用所在的原函数基本块为定位点，追实际 Base ISO 设置事件的模型写入调用，再核外发 IPC/AV 包的字段、长度与消费者读取指令；若转用白平衡，先找到 `setMetaData_WhiteBalance` 的真实提供者与调用点。CP/AV 内部分析留在别处，本目录不重复。

冷启动加载身份、WBI 选择、实际相机输出、可刷入性均未知；本阶段没有安装器或补丁窗口。
