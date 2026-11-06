# FX3 AP 启动区身份、容量与历史载荷检索

2026-10-29（本地日期）；经典 ILME-FX3 7.02；本轮仅 Mac 现存文件和公开来源。

**已将 `/dev/nflashaB0` 从脚本中的名称追到当前官方主系统的启动区设备表及驱动。** 它和 `nflashaB1` 是单独的启动区块设备；容量由驱动运行时字段计算，不能照搬公开 A7 IV 的 4 MiB，也不能把官方 formatter 映射的 2 MiB 当成完整备份长度。底层传输／加密路径尚未全部闭合，当前没有真实机身读取、备份或恢复验收。

## 历史原包重新核对

Sony [3.00 官方说明](https://support.d-imaging.sony.co.jp/support/ilme/products/ilmefx3/update/v300/ja/win/index.html)确认过渡安装器会选择 2.04 或 2.05。它面向旧版本升级，不是允许 7.02 降级或改包救砖的说明。本轮复用已经保存且来源固定的两份原始 DAT，没有重新运行安装器。

| 原包 | 原文件 SHA-256 | 重新枚举的外层成员 | NOR 内层普通文件 |
|---|---|---:|---:|
| 2.04 | `774982ecfbeae1cd9d822a2da6599cc390438ae4012b3f9ba8c43e75ec4e9068` | 135 | 4 |
| 2.05 | `dc411c1e1ea77e1c8614d6045a345d85553e46f60ec9105e6236299a3620740a` | 134 | 4 |

两份原文件的完整 SHA、UFU 外层 CRC、FDAT header CRC 均核回；从密文重新读取 tar header 并枚举成员，与前轮清单完全一致。各实际访问的 262 个明文块也通过块校验。**没有声称已重新解密检查全部明文块。** 当前检索的外层名称和 NOR 内层成员没有 `loader_emmc`、`nflashaB*`、`boot0` 或 `0200_loader` 载荷。这不证明所有历史公开包都没有 AP 启动组件，也不对未解读的其他内部内容作全局缺失结论。

主机只加载既有脚本中审查过的 AES 包装函数和 FDAT／tar 读取类，跳过旧脚本的网络日志写入及入口函数。公开格式常量固定 SHA 后仅在内存使用，没有打印或保存其数值，没有执行 Sony 程序或改写历史材料。[原包回执](historical-AP-asset-recheck.json) · [重查脚本](recheck_historical_assets.py)

## 当前主系统的启动设备表

从官方 7.02 的 p3 `initrd.img` 重新提取原模块：

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `emmc.ko` | 341,024 | `14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d` |
| `crypt-emmc.ko` | 14,592 | `521589c8eac8b851f1cab29f95f449c7bbaf31639a01331d3bf0ca8866b488b8` |
| `devno.ko` | 6,344 | `cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23` |

原 `insmod_drv1` 先列入 devno，再列入加密模块和 emmc。这里只读取脚本，没有执行装载。

`devno.ko` 的 `udif_devnodes` 原数据和名称重定位解析得到：

| 项目 | 类型 | major | first_minor | nr_minor |
|---|---|---:|---:|---:|
| `pnflasha` | 块设备 | 252 | 0 | 32 |
| `nflashaB0` | 块设备 | 252 | 126 | 1 |
| `nflashaB1` | 块设备 | 252 | 127 | 1 |
| `cnflasha` | 块设备 | 252 | 128 | 32 |

eMMC 初始化代码引用 `udif_devnodes+16`、`+32`，分别对应 B0、B1；选中分支设置内部类型 1、2。公共初始化复制名称和设备号，设置起始扇区为零；后续将 major、first_minor、名称及容量填入 Linux gendisk 并注册。

这些是**官方主系统包的静态设备定义**。没有查询相机节点或证明当前机身 p1 更新环境使用同一批模块。后续采集不能只看到名字相同就认定身份一致。[原表](devnode-table.json) · [模块与脚本提取](driver-source-capture.json) · [设备表补充提取](devno-source-capture.json)

## 容量与读取分派

以下位置均是可重定位 ELF 的**节内偏移**，不是已安装机身的运行地址。

- `emmc_seq_get_boot_capacity` 的 `.text+0x145A0` 读取状态结构 `+0xDC` 的无符号字节，左移 17 位，即以 128 KiB 为单位返回容量。当前字段值没有从相机取得，不能填入固定 4 MiB。
- 容量分派 `.text+0x7F40` 对类型 1／2 调用该函数，再减去起始扇区乘 512；对应初始化路径把起始扇区设为零。gendisk 使用字节容量右移 9 位作为扇区数。
- 启动区描述符初始化将 `+0xC8` 的软件加密回调指针清零。通用读取函数在该指针为空时直接调用 `emmc_seq_read`，传入分区类型和空的可选参数。
- `emmc_seq_read` 在传输前比较／切换分区，再把该可选参数交给下层数据函数。**本轮没有闭合更下层 DMA／加密处理，不能把“绕过这个软件回调”泛化成所有数据均为明文或已经证明完整原始视图。** 启动容器中还可能有按组件加密的数据，属于另一个层次。

这些代码收敛了未来采集的目标身份与容量来源，但不等于已经取得启动区内容。没有执行原驱动或使用模拟结果替代机身结果。[11 个原始范围及重定位](AP-storage-contract-proof.json) · [核查脚本](prove_AP_storage.py)

## GPL 的适用范围

Sony [FX3 Ver.7.00 GPL 页面](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)对应的已固定源码归档提供 `UDIF_DEVNODE` 结构和 Linux `gendisk` 定义，用于解释字段布局；当前 7.02 原指令向 gendisk 字段的赋值也单独核对。

该归档的 mach 设备表是另一份 `__udif_devnodes` 定义，与当前原模块 68 项 `udif_devnodes` 表不同。**没有用 GPL 参考表替换当前设备号或声称取得专有 eMMC 驱动源码。** 文件名检索没有找到 eMMC 专有实现，也不拿文件名零匹配证明整个源码归档不存在相关逻辑。[布局来源](GPL-source-capture.json) · [UDIF 来源](GPL-devnode-source-capture.json)

## 对恢复适配的实际影响

[启动区采集合同候选](AP-boot-capture-contract-candidate.json)只是一份数据说明，明确关闭可执行载荷、新设备后端及相机操作许可。它要求：

1. 先核对实际执行环境与同机身份，不能把主系统 p3 模块当作已安装 p1 的证明。
2. 按实际报告容量保存整个目标区；缺失、零值或不一致时拒绝，不能回退为 A7 IV 的 4 MiB 或 formatter 的 2 MiB。
3. 分别记录驱动身份、读出视图、完整长度和内容摘要；继续核对下层加密处理，避免“保存了文件但不能正确回写”。
4. 内容读回、独立恢复入口、回写及故障后冷启动分别验收，不能用节点表或驱动函数的存在替代。

下一项沿下层数据调用和启动配置来源继续核对，再决定如何接入既有受限采集工作器。当前同机启动区／p1／完整配置备份、独立 AP 自举、逆写和真实 1080p29.97 HEVC 主录及长录验收仍未完成，16 项要求不变。0.4 发行物未改动，未产生可刷镜像。

本轮没有相机、USB、缓存设备查询、管理员、驱动操作、认证、机身文件访问、上传、切模式或刷写。195 轮 root01 的具体问题保持待答，未启动或重问。

[核查回执](verification-receipt.json) · [执行边界](implementation-review.json) · [来源审查](web-source-review.json) · [封存清单](final-receipt.json)
