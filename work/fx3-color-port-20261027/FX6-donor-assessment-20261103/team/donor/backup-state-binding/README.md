# FX6/FX3 Backup 状态记录与电影事件生产边

2026-11-03。**本轮找到 `0x02ae0000` 的原 BK4 记录及长度，并闭合 `0x02ae085a` 的 AV 内部发送调用边。** FX6 五份 CHAPLIN 默认模板和 FX3 官方种子在两份记录中都把前者定义为**1 字节、默认 `00`**。FX6/FX3 原 `Data_SearchId`、`Data_GetSize` 各自以固定模板做了四组隔离 CPU 查找：命中、长度 1、子系统越界、unit 越界、无效指针哨兵均按预期返回，未运行完整 `Backup_nread`。事件生产者的字段和原发送函数也已由原指令定位；**当前相机 Backup 内容、真正写入者以及 MAIN/monitor 语义仍未闭合**。

## 原件与证据边界

| 原件 | SHA256 | 地址规则 |
|---|---|---|
| FX6 `nflasha15-files/kmod/backup.ko` | `0fe57e43eb9b868f7011c4ea02ad002f0860d9d10fc2a644c772a074fc7532e6` | AArch64 ET_REL；`.text` 文件偏移 = 节内偏移 `+0x68`；**无固定运行 VA** |
| FX3 `stage208-Backup-record-routing/originals/kmod/backup.ko` | `8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d` | 同为 ET_REL；`.text` 文件偏移 `+0x68`，须用 FX3 自己的节内地址 |
| FX6 `fat-files/nflasha3/av-cam.bin` | `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf` | 文件偏移 `p` 对应 VA `0xffffffc001000000+p` |
| FX3 `stage2/extraction/files/nflasha3/av-cam.bin` | `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf` | 独立按相同 ORIL 头映射，**不借 FX6 偏移** |
| FX6 `nflasha15-files/kmod/liro.ko` | `8a7cfcaef07ad18ca2a97847d44d31bb9152f57c0fcbccd96056ad683649f2e1` | ET_REL `.rela.init.data`，用于发送槽重定位核对 |

上述目录均在上一层供体或既有 `work/sony-firmware-20261024`；本轮只读。旧 `kernel-provider-binding/run-receipt.json` SHA `34dcdb0a682f42bf9ed78e8a49b4d6bf971489a3112d3cb7e6700d056a6acfb8`，其 LIRO 装载时从 `.init.data` 复制 provider 表的证据被复用，本轮另核对了发送相关的两个重定位。静态证据在 [static-receipt.json](static-receipt.json)，每段列原字节 SHA、偏移、FX6/FX3 AV VA、解码指令及 ELF CALL26/ABS64 重定位；ET_REL 节内地址没有冒称运行 VA。

## 记录来源、长度、默认值及写入边

FX6 `tree/0110_backup/MainDest.txt` SHA `51bc347fed1435a0afb93b4e694722aceea809751bd7748482432650bebd98f2` 指向 `SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin`。它和另四份 CHAPLIN 地区默认模板在目标 ID 上完全一致。`parse_bk4.py` 验证每个文件的 SHA、两份 BK4 的 checksum、所有 subsystem/property 边界和记录间零填充；[bk4-receipt.json](bk4-receipt.json) 列六个源文件的完整路径/哈希及具体属性偏移。

| 输入 | 记录0：属性表/值文件偏移 | 记录1：起始/属性表/值文件偏移 | 长度/默认字节 |
|---|---:|---:|---|
| FX6 五份 CHAPLIN | `0x31498` / `0x81b5a` | `0xd5000` / `0x108b50` / `0x1aab6c` | 两记录均 1 B / `00` |
| FX3 ALLLANG 官方种子 | `0x2bff6` / `0x8dd3a` | `0xd2000` / `0x1001c8` / `0x1a509c` | 两记录均 1 B / `00` |

表中十六进制偏移可直接与 JSON 十进制复算。FX6 记录0/1分别有 840 个 subsystem、40647/35088 项；FX3 为 819 个、35668/31197 项。`0x02ae0000` 分解为 subsystem `0x2ae`、unit 0。两版 `Data_SearchId` 均取记录首地址 `+0x100` 的 6B subsystem 表，再按 `{count:u16,index:u32}` 找 6B 属性项；`Data_GetSize` 读属性指针最高字节，在此为 1。两版 `Data_init` 都把收到的**首记录基址**存入 BSS 状态 `+0x28`，并建立两张表指针：FX6 `.text+0x4a38`（文件 `0x4aa0`），FX3 `.text+0x4d60`（文件 `0x4dc8`）。FX6 `backupfile_init .text+0x6218` 的 `+0x628c` CALL26 重定位调用 `Data_init`；FX3 对应 `+0x65b4`。这证明固定模板的 AP 本地查找优先记录0，不把第二份 CP 记录自动当 AP 当前值。旧 FX3 记录用途另见已封存 stage208 证明 SHA `13a62bcf7f6d1d0a7901922465a057d780fbdf22cc0e477582312ba7ab612f88`。

FX6 `Backup_nread .text+0x1ca8`（文件 `0x1d10`）把 `w2` 作为**读取容量**送到内层 `.text+0x700`；FX3 对应 `.text+0x1eb8` 与 `.text+0x760`。内层的原 CALL26 重定位到 `Data_SearchId`、`Data_GetSize`、`Data_GetDataPt`、`memcpy`。AV 请求的 `w2=4` 因此不是记录固有长度；固定默认记录只有 1 B。两版 AV 调用前先清零 `sp+0xc` 的 4B word，随后在返回值 `>0` 时读取它。若运行态确实仍是该 1B 默认值且 nread 成功，则低字节 `00`、余字节保持零；**该条件句不是自然运行读取回执**。

写入接口可定位到 FX6 `Backup_write .text+0x2518` → 本模块 `.text+0xd8`，其 `+0x130` 搜索 ID、`+0x188` 定位数据、`+0x250` 的 `memcpy` 使用调用者输入；FX3 对应 `Backup_write .text+0x2728` → `.text+0xd8`。这些是通用 API，**没有闭合谁以 `0x02ae0000` 调用写入**。有限负面检索在 FX6 AV 对齐 `[0,0x370000)` 找到 19 处单指令构造 `0x02ae0000`，均列在回执；在 FX6 AP `bin/lib/kmod` 中 363 个小于 20 MB 的可读 ELF 的可执行节内未见该**单一 MOV 指令形式**。它不能排除字面量、分步运算、其它镜像或动态调用，故不称已排除所有写入者。

## 历史 RAM 与原函数回放

两份**旧 FX3 VM 历史快照**：AP88 `backup-after-shutdown.bin` SHA `38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f`，AP89 replay `backup-reserved-ram.bin` SHA `ece9dbb93d3856705fdf1169c9730043e2e03fba5f3a3f0dd3cbcd20659d6d3f`。后者是前者的有条件重放，**不是两台机身的独立样本**；旧 AP89 运行回执 SHA `182dadd37511faa9120258469abcd1ee9d985777e9f506940274821215a46f67`。`inspect_history.py` 只读原文件，检查全表边界与 2580 B 零尾；两快照的目标字节仍为 `00`。两者首记录 checksum 均不匹配，第二记录匹配，回执保留差值而没有修复或把它们称有效持久化文件。详见 [history-receipt.json](history-receipt.json)。这仅说明**既有 VM RAM 的该字段**，并不能替代 FX6 当前状态或相机实际数据。

`replay_search.py` 仅把原两版 `backup.ko` `.text` 载入隔离 AArch64 CPU，并在**客体副本**按各自 ELF `R_AARCH64_ABS64 +0x28` 重定位 `Data_SearchId` 和 `Data_GetSize` 的 BSS literal；BSS 三个指针由上面已核验的固定模板构造，未运行 `Data_init`、模块装载器、`Backup_nread` 或内核助手。四例（两版 × 两记录）在 120 指令预算内返回原属性描述符及长度 1；12 个负例覆盖越界 subsystem、越界 unit、实际 `0xffffffff` 属性哨兵，均返回零。没有原函数内存写入，返回 PC 为哨兵 `0x50000000`，完整 PC/补丁/写集见 [search-replay.json](search-replay.json)。原件没有被 patch。**CPU 结果只是原查找函数加明确映射/状态夹具，不证明运行态初始化或读取成功。**

## `0x02ae085a` 事件生产者和字段

FX6 AV 原发送共用函数从文件 `0x2a7eac` / VA `0xffffffc0012a7eac` 开始：`0x2a7ecc` 经 provider `+0x3e0` 为队列 ID 分配 0x48 B；`0x2a7ef8` 复制调用者 0x48 B；`0x2a7f3c` 经 `+0x3a8` 发送；`0x2a7f8c` 经 `+0x3e8` 释放。FX6 LIRO 原 `.rela.init.data+0x398` 为 `osal_valloc_msg_wait`、`+0x360` 为 `osal_snd_msg`，按旧阶段已证的 `+0x48` 复制规则对应 provider `+0x3e0/+0x3a8`；`+0x3e8` 释放的真实实现见旧回执。本轮的原 `BL` 对齐扫描找到六处**直接**调用发送共用函数；FX3 AV 对应 `0x2c4cc8`，同样六处。这里证明软件消息生产调用，**没有声称发送/接收在 VM 或机身实际发生**。

| 事件 type | FX6 直接调用文件偏移 | 原指令能确定的初始字段/条件 | FX3 对应调用 |
|---:|---:|---|---:|
| 0 | `0x2992c4` | `0x299204` 令 `w20=w1`（look）；仅上游状态 `w0=0` 且 look 非 0/30 才建包；`+0=0,+4=w20,+8=0,+0x10=x2`，`+0x18=0x02ae085a` | `0x2b60cc` |
| 1 | `0x29a5a4` | `+0=1,+4=0,+8=0`；还检查输入 `+8==0xbb80` | `0x2b73ac` |
| 2 | `0x299f68` | `+0=2,+4=30,+8=0`；上游状态为零 | `0x2b6d70` |
| 3 | `0x29a6c4` | `+0=3,+4=0,+8=0`；还检查输入 `+8==0x7c` | `0x2b74cc` |
| 4 | `0x29a804` | `+0=4,+4=0,+8=0`；上游状态为零 | `0x2b760c` |
| 5 | `0x29a8f0` | `+0=5,+4=0,+8=0`；本地没有相同状态零门槛 | `0x2b76f8` |

type0 的上游两处直接调用是 FX6 `0x29b5d4` 与 `0x29da08`（FX3 `0x2b83fc` 与 `0x2ba830`）：前者在输入命令字段等于 3 时，从输入 `+8/+0x10` 经原 `0xe420` 转换函数分别得状态与 look；后者在命令字段等于 4 时，按输入给的起点和数量逐个构造 look。这里**未绑定这些输入命令来自哪个实际 UI 模式**，也未证明 `0xe420` 转换函数对所有输入的语义。接收端 FX6 `0x2a72d0` 经 provider `+0x3c0` 取同一 ID，成功则 `0x2a731c` 分派，后以 `+0x3e8` 释放；FX3 对应接收调用 `0x2c40ec`。type0 生产包的 `ip=0` 是原发送方赋值，仍**不能只据数值称 MAIN**。还有可能存在其它镜像发送者或动态构造；上述六处只覆盖固定 AV 的直接 `BL`。

## FX3 最小接入契约与阻断点

可复用工程件是 `parse_bk4.py` 的版本受限 ID/长度/值解析器，以及上表字段级事件路径：FX3 自己的 `Backup_nread` 读同一 ID，FX3 自己的队列 API 使用同一 0x48 B 包布局，并由 FX3 本地回调/描述符地址处理。**不能把 FX6 事件包中的指针 `+0x10`、提供者函数 VA 或默认 `00` 当成可直接拷贝的 FX3 运行态代码；也不能把旧人工 word `0x30/0x31` 视为自然状态。** 当前无能以真实输入驱动 FX3 look22 的可安装适配器，故没有进行该分支的原码重放或伪造像素结果。供体侧能复用的是查找/事件 ABI 与调用条件，尚需适配并观察 Backup 当前值、状态写入者、实际 look/IP、callback 和后续控制路径。

给独占 VM 的负责人所需**最小只读观测**（若现有环境自然加载 AV；若没有则记录“未加载”）：

1. FX3 `backup.ko` 完成 `Data_init` 后 BSS `+0x28/+0x30/+0x38` 指针及所指 BK4 头、`0x02ae0000` 属性 6B 项和 1B 数据；核对模块实际装载节地址/哈希。不要修改记录。
2. FX3 AV `0x2b80cc` 的 `Backup_nread` 调用返回状态 `w0` 及调用者 `sp+0xc` 的 4B；同时抓一次实际写入此 ID 的调用 PC、ID、长度、源字节（若发生）。若无写入，明确报告未观测，而不从模板猜。
3. FX3 type0 发送 `0x2c4d58` 前的队列 ID、`x1` 所指 0x48 B、返回值；接收 `0x2c40ec` 后的返回值、事件指针与 `+0/+4/+8/+0x10`；再绑定一次能区分 MAIN/monitor 的**真实下游**状态/输出。仅数值 `ip=0` 或 look22 不够。

这是首个确切运行态阻断点。此目录没有启动 QEMU、取锁、注入、写相机/USB/SD、改固件或改旧回执。静态、隔离 CPU、旧 VM RAM 与实机证据不能互相替代。

## 复现

在本目录执行 `sh prepare.sh`，再依次运行 `python3 parse_bk4.py > bk4-receipt.json`、`python3 inspect_history.py > history-receipt.json`、`PYTHONPATH=.vendor python3 replay_search.py > search-replay.json`、`PYTHONPATH=.vendor python3 analyze_static.py > static-receipt.json`、`PYTHONDONTWRITEBYTECODE=1 python3 verify.py > run-receipt.json`。`prepare.sh` 只在本目录临时装固定版本 `pyelftools`、Capstone、Unicorn；离线脚本不连接设备或执行未知原程序。当前 [run-receipt.json](run-receipt.json) 为本轮实际 PASS，验证六个固定默认文件、两份历史 RAM、四个 CPU 正例与十二个查找负例；本地临时依赖已在回执生成后移除，重新运行可再装。
