# FX3 Cetus 发送端检索与原 NOR 块加载边界（2026-10-29）

**本轮尚未定位 Cetus 完成标志的发送者，也没有取得可正常刷入 FX3 的修改固件。** 新证据明确了检索范围、若干同名线索的实际含义，以及原配置分支中的两个 CPAPP-B 块加载入口。两者都依赖尚未知的引导装载信息；有效的底层读取还缺原控制器状态。没有获得 DMM 配置内容、缓存像素或 RAW。

开始时核验外盘 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、项目入口和现有非 Git 边界，独立回读[上一阶段](../nor-backup-selection-20261029/README.md)33个封存文件，全部一致。上一轮以原代码确认 NOR 文件打开的固定失败边界，改变了下一步调查方向，属于 progress；本轮不重复将装载描述视为成功文件读取。

## 同名线索和指令构造分开核对

在固定 SHA 的 `/usr`、initrd 和 CP 三个文件系统中，对857个普通文件搜索 Cetus 大小写名称、CP 文件名和两个完成标志的原字节。

| 所在原件 | 命中内容 | 本轮能支持的含义 |
| --- | --- | --- |
| `mcmn_drv.ko` | `MIRA_CETUS` 媒体插入、电源、时钟、PCIe 诊断 | 平台／运行时驱动名称，未据此找到启动发送者 |
| `libSysDef.so` | `MIRA_CETUS2` 构建标识 | 构建配置标识 |
| `appFw.so` | `beep_idx` 对应的 CETUS DMM 申请／释放日志 | 这些具体命中是提示音缓冲调用，未连接到启动传输或 MAIN 像素 |
| `wlan.ko` | `COEX_MWS_CP_ESCAPE` | 无线共存命名，不能当作 CP 启动完成标志 |

随后在565个 AArch64 ELF 的可执行节、共 **68,616,928字节**中，查找最多8条指令范围内构造 `0x454e524b`／`0x50435345` 的 MOVZ／MOVN＋MOVK 序列；原内核 Image、AV 原 ORIL 映像另行扫描，CP 原件另用 ARM／Thumb2 的 MOVW＋MOVT 序列检查。内核与 AV 的完整原字节也核对了两个32位字面标志。

上述范围没有找到发送者候选。扫描确实能找到原 NOR 中两处已知的完成标志比较序列；另有已知 CP Thumb2 和 ARM 常量构造窗口作为校准。这些校准不证明覆盖了所有构造方式。未应用全部运行时重定位，原始映像的代码／数据也未一概认作可执行；**无匹配不等于全固件没有发送者**，仍可能涉及其他构造、启动阶段、处理器、引导输入或硬件传输。

原内核的41,269项符号目录只读复用已有阶段146的恢复结果，当前文件 SHA 与其封存记录一致；没有重跑旧 main、USB guest 或设备流程。它只用于原 Image 的静态坐标导航，不算本轮重新验证了所有符号或启动了 Linux。

## 配置分支实际调用的 CPAPP-B 块读取

原 NOR 仍为101,888字节的 `loader_nor.bin`，SHA：

`4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942`

原 `0xfe052f24` 和 `0xfe052f90` 的两个调用分别进入 `0xfe05a1b4`、`0xfe05a2b4`；原函数名日志为 `ospi_load_cp_app_b` 和 `ospi_load_cp_app_b_pre`。它们不是上一阶段固定返回失败的文件打开函数。

原代码读取引导信息表的第5项，表步长 `0x40`；相关三个原地址为 `0xfe040140`、`0xfe040144`、`0xfe040150`。前两个32位字段在后续偏移／长度计算中左移9位。前段读取长度 `0x500000`，后段从加上同一偏移的位置读取，长度依原字段计算；另有原回退分支。**没有把回退常量解释为本机真实长度、存储容量或 DRAM 容量。**

两个完整原函数前缀分别在有界 ARM64 RAM 中运行，都停在 `0xfe05885c` 读取未知 `0xfe040140` 的位置。没有提供装载表、时钟、控制器、块读取回复或镜像数据，也未执行实际 NOR 操作。

静态后续为原 `0xfe05a56c → 0xfe04fab0`。底层代码有内存映射分支，以 `0xd0000000` 加源偏移读取，再写入目标；其具体分支、控制器和映射状态尚未得到实机证据。块内是否包含 DMM 配置、它如何到达此前的目标地址，仍不能由函数名或参数推断。

## 返回值与数据传输量分开

对原 `0xfe04fab0` 四组输入执行原指令，没有提供控制器或闪存数据：

| 原输入场景 | 结果 | 非栈 RAM 写入 |
| --- | --- | --- |
| 源偏移达到 `0x4000000` | 原返回3 | 0 |
| 长度超过 `0x4000000` | 原返回3 | 0 |
| 零长度 | 原返回0 | 0 |
| 范围内、长度4 | 在原 `0xfe04faf0` 读取未知控制器字节 `0xfe061eea` 时停止 | 0 |

最后一例停止时的寄存器快照不是函数返回值。零长度返回0也不是读出一次数据的证明。两个64 MiB 检查仅是**这一个原函数的参数边界**，不能据此认定芯片容量或完整硬件能力。

本轮还修正了一处附加日志的采集偏移：原偏移落在前一字符串内部，已改为核对 NUL 分隔的原起点。旧脚本与旧结果保存于 `attempts/`；功能实验和搜索结果不变，原固件没有修改。

## 下一步及完整目标

下一步追引导装载表和 NOR 数据布局的生产者，再核对 Cetus 传输实际载荷是否包括 DMM 配置。当前仍缺这些输入和实际数据路径的证据。此前找到的文件装载描述和 CP 地址关系保持为原默认契约，实际配置装入、extent 分配及像素读取仍待证。

完整 FX5 私有供体、VENICE type3/type4 内层和实时 ISP、CMOS RAW／校准、专业菜单移植、FX3 主录绑定、目标修改包准入、正常启动与独立恢复，均未由本轮通过。联网检索的[日本官方 FX5 下载页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)搜索缓存显示该页暂无更新信息；本轮未取得新的完整私有包，这不构成全网不存在包的证明。

全程只读原件与有界 Unicorn RAM，没有执行原生 Sony 程序、相机／USB／手机／真实 IPC、硬件寄存器设置、签名密钥搜索、修改整包输出或刷写。另一 agent 的设备／恢复工具和租约未操作。持续目标保持 active，达到可正常刷入的证据门槛后停在实际刷机前。

## 复核

- [857文件标记检索](handoff-marker-scan.json) · [程序](scan_handoff_sources.py)
- [565个ELF与原内核的构造检索](marker-construction-scan.json) · [程序](scan_marker_construction.py)
- [AV／CP补充检查与校准](raw-marker-construction-scan.json) · [程序](scan_raw_marker_construction.py) · [原字面值检查](raw-literal-marker-check.json)
- [两组块加载严格边界](bulk-loader-prefix-results.json) · [程序](probe_bulk_load.py)
- [底层读取四组结果](NOR-reader-guard-results.json) · [程序](probe_reader_guards.py)
- [候选上下文、六个原窗口和符号目录来源](sender-source-review.json) · [采集程序](capture_sender_review.py)
- [验证与封存](validate_and_seal.py) · [最终回执](final-receipt.json)
