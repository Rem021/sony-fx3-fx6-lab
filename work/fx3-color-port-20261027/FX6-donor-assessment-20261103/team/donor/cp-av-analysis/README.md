# FX6 6.01 CP/AV 映射与 MLUT 消费者限定分析

2026-11-03。**本阶段已从固定原件建立 CP/AV 静态架构和镜像内部映射，闭合 FX6 AV 指令→look 表→矩阵描述符复制三条内部数据边，并完成一个原字节、无设备的 CPU 查表函数重放。** 没有证明传感器 RAW 输入、黑电平/去马赛克/降噪、MAIN 视频像素输出、FX3 兼容性或机身运行状态。

## 输入和边界

仅读上层封存的 FX6 `fat-files/nflasha8/cpapp-b.bin`（17,952,816 B，SHA256 `60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668`）和 `fat-files/nflasha3/av-cam.bin`（12,939,512 B，SHA256 `56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf`）。FX3 7.02 对照为既有 `stage2/extraction/files/nflasha3/av-cam.bin`（SHA256 `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf`）及 `extraction-results.json`、`descriptor-index.json`、`initializer-guest-results.json`、`look-consumer-guest-results.json`；全部在脚本中固定 SHA。另核对 FX3 CP SHA256 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`。本目录以外没有写入。

## 架构与映射：先从 FX6 自身推导

| 镜像 | 原始证据 | 推导 | 限度 |
|---|---|---|---|
| CP | 文件 `0x0` 的 ARM little-endian `ldr r1,[pc,#4]`、`add r1,#4`、`mov pc,r1`；`0xc` 字面量 `0x0010800c`；`0x380–0x390` 另有相近绝对地址 | 文件偏移 0 对应 `0x00108000`，首跳转 `0x00108010`；非 ELF 的 ARM32 平坦代码 | 仅代码自引用映射，未证实 CP 运行时内存/IPC ABI |
| AV | 文件 `0x0` 指针 `0xffffffc001000058` 指向 `0x58` AArch64 入口；`0x8` 为 `ORIL`，入口有实际 AArch64 指令、`BL` 和内部指针 | 文件偏移 0 对应 `0xffffffc001000000`；非 ELF 的 AArch64 平坦镜像 | 仅镜像内映射，未证实活动像素路由 |

两边完整入口指令和 SHA 见 `mapping.json`。同包 `partinf.conf` 把 `nflasha8` 标为 CP Data 分区，`tomco.txt` 列出四个 `memcfg` 段和监测区地址；逐行与 SHA 见 `config-evidence.json`，这些配置**没有**直接给出 `cpapp-b.bin` 装载地址。FX6/FX3 CP 的前 `0x20000` 字节相同，此后不同且总长度不同；AV 在 `0x84` 起不同。**没有从 FX3 借用基址**，两份 FX6 基址先由各自头与启动代码推导，之后才做对照。

## FX3 与 FX6 的表、配置和消费者差异

- 两者各解析出 612 个具有有效镜像内数据指针、寄存器偏移、字数和零填充尾的 MLUT 描述符。583 个同名条目的寄存器偏移、字数及完整数据 SHA 均相同；其中 30 个 VENICE 命名条目全部相同。另 29 个 FX6 `...V1_1` 与 FX3 `...V1_1_V1_1` 是 Vintage 组，配对后的 29 份数据 SHA **全部不同**。每一条的名字、偏移和 SHA 见 `descriptor-diff.json`。
- FX6 VENICE 命名矩阵的 13 个原始字为 `[1,0,0,0,75487,516574,522051,521632,79077,513403,523481,475,65868]`，与 FX3 完全一致；同镜像 `MLUT_MTX_A_REG_SG3TOAP1_0` 数据也与它逐字节一致。矩阵源数据偏移 FX6 `0xbb1dec`、描述符 `0xb83218`；FX3 原矩阵数据 `0xc15aa8`。这属于固定的色彩表数据，未证明像素域执行。
- 29 项 FX6 look 表在 `0x36fdf8`，名称和每项描述符数量与 FX3 的既有 CPU 查表回执一致。FX6 入口 `0x2a650c` 的 `0x2a653c ADRP` + `0x2a6540 ADD` 指向该表；随后读取索引并把命中的 32 B 记录复制到输出。第 22 项 `MLUT_LOOKNAME_SL3SG3_TO_ACESREC709` 在 `0x370098`，指向 70 个描述符的数组，具体原字节和逐条指令见 `consumer-edge.json`。
- FX6 三个初始化入口候选为 `0x29e0d8`、`0x29f2d8`、`0x29f508`，各自开头 16 B 与 FX3 对应入口一致，但后续地址操作数不同。FX6 原指令在 `0x2a2dec`、`0x2a2fa0`、`0x2a35e0` 均调用镜像内 `0xd80`、长度 `0x98` 的复制例程，源描述符均为 `0xb83218`，目标分别为 ACESCCT 第 15 项 `0xaa1b68`、ACESPROXY 第 15 项 `0xaa2878`、ACESREC709 第 63 项 `0xaa5208`。指令中目标基址、增量、源地址、长度和分支都列于 `initializer-edges.json`；这是**静态代码/数据引用闭合**，未运行 FX6 初始化器。
- FX6 `0x29f2e4–0x29f2f0` 可见把值 2 写向 `0xa87ff0` 的配置路径；仅确认这一条静态写入，不能外推整个配置状态。FX3 既有回执在纯 CPU guest 执行过其初始化器，不能冒充 FX6 执行或相机 DSP 写入。

## 纯 CPU 实测

`replay_lookup.py` 只在 Unicorn 的隔离内存运行 FX6 `0x2a650c–0x2a6598` 的原字节函数，函数段 SHA256 `e782906894cdd55292e589ba0f7d73dbc547a1cad398754dfdd2055a425793ca`；PC 被限制在这段代码和终止哨兵，写入只允许栈与 32 B 输出。输入 `-1,0,1,16,22,29,30` 七例均返回与原镜像 look 表相符的记录或拒绝值，栈指针和输出哨兵保持正确，见 `cpu-replay.json`。这证明**查表函数**的 CPU 行为，不证明初始化完成、DMA 提交或像素变换。

## RAW/ISP 边界与下一步

`libmpr.so` 的 `RawInfo` / `stillrecord` 命名家族只列为**静态照片支线候选**，不能作为视频 RAW/ISP 证据。本阶段识别的是 AV 的 MLUT 表装载与 look 消费者；尚没有从传感器输入/校准到 MLUT 上游的像素缓冲区、调用链或固定 RAW 输入输出，也没有给 CP 像素处理器/IPC ABI 下结论。CP 虽有 ARM32 启动映射，后续跨核地址、共享内存和调用约定未闭合。

**下一最小离线重放目标**：先静态列出 FX6 `0x29f508` 初始化器的全部写入范围和被调函数，再只在限定地址域执行这一入口与原 `memcpy` `0xd80`，逐字节核对 ACESREC709 第 63 个 152 B 描述符 `0xaa5208` 是否来自 `0xb83218`；任何越界代码/写入立即停。之后才能以它的实际初始化输出测试 `0x2a7978` 的 DMA 列表构建，仍需独立确定 MAIN 视频上游像素输入和真实 MMIO/IPC 消费者。

## 复现

在此目录执行 `sh prepare.sh`，再执行 `PYTHONPATH=.vendor python3 analyze.py` 和 `PYTHONPATH=.vendor python3 replay_lookup.py`。脚本只读固定 SHA 原件，只写本目录 JSON；`prepare.sh` 暂装 Capstone 5.0.6 和 Unicorn 2.1.4 到本目录，运行后已移除临时依赖。没有 VM、设备、相机、USB、SD 或原程序本机执行。
