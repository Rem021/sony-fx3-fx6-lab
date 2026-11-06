# AP 暂存地址与 AP／CP 记录切换

2026-10-30；经典 FX3 7.02 原始默认记录 + 公开 A7 IV v2.00 AP 加载器参考。仅离线静态分析及受限 Unicorn RAM。

**补上了上轮的 `context+0x38` 来源：参考 AP 代码把 AP 记录的 `FA019A` 写入该字段，与 escape 文件装入公式使用的是同一属性。CP 目标范围则从第二份 BK4 记录取得，随后原代码恢复第一份 AP 记录。** 这修正了上轮“仅手动组合两份默认值”的证据限制：现在有原代码支持这种角色分工，但仍没有这台 FX3 的 AP boot0 或当前实机 Backup，不能据此宣布 FX3 已经完成同一流程。

还不能把 VENICE 全链路替换进 FX3 后正常刷入。本轮没有修改固件，没有文件实际装入、AP→CP 传输或设备操作，也没有把独立 RAM 片段拼接成一次正常启动。

## 原代码中的连接

| 位置 | 原代码作用 | 本轮核对 |
|---|---|---|
| `FE04EBC8` | 从 AP Backup 起点以索引1取得 CP 记录 | `Data_getAdrs` 原指令返回 `0x4040D2000`，与原 AP 记录尾向上对齐一致 |
| `FE04EC0C` | `Data_init(CP镜像记录)` | 全局当前记录指针切到第二记录；读取 CP 的 FA0080 与范围 |
| `FE04ECAC／ECD4` | 读取 `FA01D0／FA01D3` | CP 起点 `0x808730000`、终点 `0x809A21E00`，保存长度 `0x12F1E00` |
| `FE04EDF4` | `Data_init(AP原记录)` | 选中指针切回 `0x404000000` |
| `FE05017C／01A0` | 读取 `FA019A`，写入 `context+0x38` | AP 源地址 `0x412000000` |
| `FE0501A4／01C8` | 读取 `FA019B`，写入 `context+0x40` | AP 声明容量 `0x2A00000`；尚未证明完整容量检查 |
| `FE0501CC／01EC` | 读取 `FA01C7`，写入 `context+0x48` | 第二源地址 `0x414A00000` |
| `FE052B0C..2B24` | 取目标、源、长度，调用原传输函数 | 在 `FE05D884` 入口前停止：`X1=0x808730000`，`X2=0x412000000`，`X3=0x12F1E00` |

通用属性读取器的 mode=4 路径使用启动 BKSB 表；非零且非4的路径使用当前 BK4 状态。本轮显式声明 mode=3，原参考的 RAM 成功分支 `FE05B6E8..6F0` 确实写入3，但没有把该静态分支当作这台机身的当前启动状态。已有官方 FX3 AP 模块的记录0／记录1角色证据可参阅[阶段208](../../sony-firmware-20261024/stage208-Backup-record-routing/README.md)，它同样不能代替当前机身数据。

## 地址对应与内容完整性

上轮恢复的文件装入公式是：

```text
AP文件位置 = FA019A + CP描述符.start - CP escape起点
```

本轮绑定传输源后，对原始9个 class5 描述符独立计算：`CP escape起点 + (AP文件位置 - 传输源)` 均精确回到该描述符的原 CP 地址。DmmCfg 对应 AP `0x4132D8E00` → CP `0x809A08E00`。

这是地址对应，不是9份文件均已装入的证明。原更新包 p8 的 FAT 中仅有其中4条路径；5条未在该目录出现，不等于整包或实机中不存在。4份现存文件均核对了实际字节数与 SHA；DmmCfg 的描述符槽位为 **102,400B**，实际文件 **43,320B**，槽位剩余 **59,080B** 的初始化未证明。整个 escape 区域的空洞、其他槽位尾部和尚缺的文件不得填零后冒充原始 CP RAM 镜像。

逐行地址、槽位与原 FAT 文件信息见 [default-span-roundtrip.json](default-span-roundtrip.json)。这些地址和范围仍不能识别实装 DRAM 芯片、带宽、CMOS RAW 编码或完整 ISP。

## 无效值检查的反例

参考 wrapper 的三处检查是 `MOV W9,-1` 后用 `CMP X2,X9` 比较。W 寄存器写入零扩展，因此比较对象为 **`0x00000000FFFFFFFF`**。CP 默认记录中的 FA019A／019B／01C7 为 **`0xFFFFFFFFFFFFFFFF`**，它们没有被该检查拒绝。

用原 CP 记录作明确的错误选择对照：

- 不提供 CP 目标上下文时，原指令先把三个全1值写入 `+0x38／+0x40／+0x48`，随后 RAM 未知读保护在 `FE052B0C` 停止。
- 仅补入已核对的 CP 目标起点与长度后，原 wrapper 到达传输入口前，源指针仍为 `0xFFFFFFFFFFFFFFFF`。没有执行该传输。

因此不能用“getter返回非负、wrapper走到了传输调用”证明源地址有效。此对照不是观察到相机实际选错记录，也不证明任何可刷入或恢复方法。

## 验证范围与原件

[prove_staging.py](prove_staging.py) 使用原始 AP 指令、原属性查找与原 memcpy；没有以 Python 函数替换 Sony helper，也没有编造文件读取或硬件回复。14次完整叶 API 调用执行6,489条原指令；CP 上下文片段6,102条，AP source wrapper 前缀417条。所有访问受原件范围、已知字节、可写 RAM 和代码窗口约束，遇诊断、传输、未知访问或特权指令即停。

`FE04ED6C..FE04EDEC` 的日志、分配与属性缓存注册循环未执行；其后的 AP 恢复是独立入口片段。后续 wrapper 使用前片段产生的已知 CP 上下文。本轮没有声称这些片段构成一条连续启动路径。

[verify_staging.py](verify_staging.py) 另核26条关键原指令与9行地址往返，并从固定 p8 镜像重新读取4个文件信息。[staging-proof.json](staging-proof.json) 保存调用边界、上下文字段和原范围摘要；[validation-results.json](validation-results.json) 为限定验证结果。`attempts/` 保留初始窗口过窄的保护停止，以及错误地预期64位全1值会被拒绝的初始断言；原件和历史封存均未改动。

输入摘要：

- A7 IV AP SRAM，190,464B：`2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74`。
- FX3 原默认 AP 记录：`33789a7a4d648c9a0bd74bd332de395500bdf0f363839f1d770393a3a3191da5`。
- FX3 原默认 CP 记录：`5dc5883fb86d87d14c1c3d530d4d65d903361c189a64edabcd1f636df289f5b7`。
- 前轮封存清单 `e68dd2e1596ab1b10f508ce658e2a796dcc9cebbe51ed8fe6e270b15c87e42e2` 的14个文件全部复核通过。

公开来源为 [DavidBuchanan314 的 A7 IV eMMC 说明，固定提交 e85e137](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/e85e137fc3b88b7cb26e69faa9f1304184678ff7/emmc_boot/README.md)，本轮2026-10-30联网复核。作者明确写明 boot0 来自 v2.00，相应下一阶段入口为 AArch64 `0xFE049000`。本轮只读取已取得的明文 SRAM 参考，不运行其解密／采集工具，不读取 ROM 秘密或寻找签名私钥。

## 余下缺口

下一步离线追踪文件装入器和暂存区初始化，确认文件槽位尾部及整个 escape 区域的字节从哪里来；同时保留 FX3 当前 AP 加载器、实际 Backup 选择、真实传输与 RAW／私有 ISP 的缺口。完整 FX5／VENICE 供体、FX3 7.02 修改包准入与独立恢复尚未满足，没有生成可刷固件。持续目标保持 active，未完成；达到可刷门槛后仍须停在实际刷机之前。
