# FX3 本地缓存 RAW 与菜单证据

## FX3 已取得什么以及缓存调用究竟到了哪一层

### Takeaway
经典 FX3 7.02 的官方完整包和解密 FDAT 已在本地；本轮重新计算两者及五份所用文件 SHA256，全部与旧封存回执相同。现有研究已定位 DMM 资源选择、区域回复、缓冲表和编码 Open 字段链，但没有建立可与 FX5 同步的物理 DDR 芯片控制、训练参数或缓存一致性接口。

### Cited Findings
- 旧官方回执记录包源自 Sony 日本 7.02 发布页，最终下载端 `di.update.sony.net`；完整包 811,876,768 字节，SHA256 `f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854`。本轮实读文件重新计算一致。解密 FDAT 808,704,512 字节，SHA256 `694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768`，重新计算一致。来源认证沿用既有官方下载/CRC/块校验链，并非本轮重新下载。[官方7.02页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)；[旧下载回执](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/fx3-7.02-download-receipt.json)；[本轮实读回执](fx3-static-chain-receipt.json)。
- 本轮所用 `av-cam.bin` 为 13,348,560 字节、SHA256 `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf`；`libmpr.so` 为 3,517,008 字节、SHA256 `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`；`appFw.so` 为 79,015,712 字节、SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。均是固定更新包提取件，不是用户机身当前加载身份。[本轮回执](fx3-static-chain-receipt.json)。
- `libmpr.so` 导出真实定义：`GetDmmModeId` VA `0xcd5c4`/316字节，`GetDmmExtList` VA `0x2af498`/416字节，`UnitTypeTableSelect` VA `0x2af638`/472字节，`SetMemTbl` VA `0x2afb0c`/2128字节；本轮直接读 ELF 动态符号表核对。[脚本](inspect_fx3_static.py)；[回执](fx3-static-chain-receipt.json)。
- 既有阶段126记录原 `SetMemTbl` 向 Model `+0x278` 的 `0x760` 字节 BufferTable 写字段，原 Enqueue Open `0xd6700..0xd67b8` 将表复制入请求。输入地址/区域在当时是声明值，不是相机物理分配结果。[阶段126](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage126-native-DMM-buffer-to-Open/README.md)。
- 既有阶段128确认 `dmm.ko` 的普通/同步命令表将命令 `0x20` 指向 `.text+0x5488`，对应队列 `0x61003c`；阶段129绑定正确 AP `/setting/DmmCfg.bin`，66796字节、SHA256 `48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1`，603个单位中目标20个全匹配、各1个extent，全文件最多8个extent。本轮重新计算该配置及118336字节 `dmm.ko` SHA256一致。[阶段128](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage128-DMM-provider-and-config/README.md)；[阶段129](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage129-AP-DMM-config-and-device-trial-plan/README.md)；[本轮回执](fx3-static-chain-receipt.json)。

### Inferences
- 用户的“缓存芯片调用”需要分三层调查：物理 DDR/内存控制器和启动训练；DMM 给录制任务分配/映射的缓冲区；CPU cache 与 DMA 可见性。这三者不能用一个 `SetMemTbl` 或数字地址互相代替。现有强证据集中在第二层的配置/字段与有限原指令行为。
- 当前能交给 FX5 对比的有价值材料是 DMM 单位/模式/消息结构和各 BufferTable 消费者，而不是把 FX5 的缓冲地址常数复制到 FX3。即使单位名称相同，还要检查地址空间、对齐、分块、DMA映射、所有权、完成事件和释放寿命。

### Gaps
- 没有核实物理 RAM 颗粒型号/容量/总线、DDR控制器寄存器、训练固件、两机实际 DTB/reserved-memory、当前映射和 cache维护协议。本轮没有为不存在的实机证据补名词或常数。
- 既有 stage133 的 FX3 GPL 参考是 Ver7.00 发布源码，不代替当前7.02实机；同样 FX5 GPL 示例配置不等于实际出厂DTB。没有 FX5 专有 DMM/HAL/AP对象可做 ABI 配对。[既有平台比较](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage133-FX5-source-availability-and-portability/README.md)。

## CMOS RAW 读取 解RAW HDMI与内部RAW录制是否已经接通

### Takeaway
FX3 已有官方 HDMI RAW 输出；本地可见静态照片 RAW 导入/开发序列和 HDMI RAW 控制相关字符串。它们没有证明已恢复完整 CMOS 读出驱动、实时 ISP 或内部 RAW/X-OCN 编码器，更不能自动适配 FX5 新传感器。

### Cited Findings
- Sony 官方经典FX3规格列 Exmor R CMOS、视频有效约1030万像素；RAW 输出经 HDMI，4264×2408，16bit，含29.97p等帧率。页面还分别列静态 ARW 和内部 XAVC 格式，概念本来不同。[FX3官方规格](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/specifications)。
- Sony FX3 HDMI 帮助将 RAW 输出定义为送往 RAW 兼容 HDMI 外部设备，并写明 RAW movies 不能记录在机身存储卡；此链接是早期手册，应与后续版本手册交叉阅读。Ver2+ Log 设置帮助依然明确将 RAW movies 的路径描述为 HDMI，并要求 Log Shooting 非Off。[HDMI原手册](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000284740.html)；[Ver2+ Log设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888942.html)。
- 本轮在 `av-cam.bin` 的文件偏移 `0x433109` 找到 `StillMP_Sequence_IMPORTANDSRW_PACKED_RAW_IMPORT`；`0x433139` 为 `...UNPACKED_RAW_IMPORT`，`0x4331a6` 为 `...UNPACKED_RAW_IMPORT_AND_DEV_AND_FILL`。这是静态字符串和序列命名线索，本轮没有执行这些序列或追出完整数据流。[回执](fx3-static-chain-receipt.json)。
- `libmpr.so` 文件偏移 `0x2cf03d` 有 `app_dmm::alloc_and_open( app_dmm::STILLMP_BUF_RAW_UNPACKED, &dmm_raw, true )`。它支持继续调查静态照片 RAW 缓冲链，不能改写成“电影RAW持续采集已实现”。[回执](fx3-static-chain-receipt.json)。
- `appFw.so` 文件偏移 `0x391b62a` 起有 HDMI `SET_DEFINITION(RAW)`、`SET_RESOLUTION(RAW)`、`SET_OUTPUT_FRAME_RATE(RAW)` 日志字符串；`0x391c190` 为 `sequence_change_hdmi_resolution::set_raw_output()` 名称。既有AP镜像完整盘点另记录 `/scenario/CAMERA_SCN_EXTERNAL_RAW_RECORD.so`，13856字节，SHA256 `4ce5ae6a30f590b9da6eb313c8acf5b2dcd28927501854c99cd3a1bda75db6bc`。本轮未提取或执行该场景。[本轮回执](fx3-static-chain-receipt.json)；[旧532个ELF盘点](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage148-initial-MSC-handler-inventory/AP-handler-inventory.json)。
- `appFw.so` 文件偏移 `0x311a7cf` 的 `No35_Imagersensorreadout` 仅是名称命中，本轮没有关联到寄存器写入、传感器型号或实际读出模式。[回执](fx3-static-chain-receipt.json)。

### Inferences
- 应当画成分开的路径：传感器配置/读出 → RAW缓冲 → 图像处理/去马赛克 → YUV/HEVC；RAW缓冲也可能走 HDMI RAW 或专用压缩RAW编码/封装。把 HEVC 编码器配对成功当作 CMOS RAW/ISP 已同步，会跨过关键未证环节。
- “解RAW”可能指打包解码、黑电平/缺陷像素/增益处理、去马赛克，或压缩RAW解码。现有字符串只提示 packed/unpacked 导入与开发序列，不能声称四者已恢复。

### Gaps
- 尚缺传感器寄存器/时序表、读出驱动和协处理器固件；DMA传输/帧完成事件；RAW packing/CFA/stride/black level/坏点/温度与镜头校准；ISP调度与参数；内部压缩RAW编码器、码率/吞吐/容器和回放链。没有取得一帧真实 RAW 内存或验证帧时序。
- 未建立 FX5 RAW 数据结构与 FX3 的可逆映射；传感器模式和成像参数不能仅依名称同步。内部 X-OCN 移植可行性仍待FX5专有实现和硬件依赖证据。

## 电影菜单移植与下一阶段应怎样拆分

### Takeaway
用户已澄清目标是 **FX5整套专业菜单与功能**，不是BIG6外观。当前没有FX5实际UI应用/资源、完整菜单树和后端专有对象，因此还不能做整套菜单/功能移植。经典FX3 7.02 的 `appFw.so` 自身包含 `big6` 控件名称，只是本机UI框架可供复用的一个小线索，绝不构成目标完成或FX5菜单隐藏存在的证明。

### Cited Findings
- Sony 经典FX3 Ver2+ 手册已有 Main1/Main2电影快捷页、直接触控修改与分配快捷键；同页注明 Ver6+ 在角度模式下显示快门角度。因此 Cine EI/Main menu/快门角度不能当作必须刷FX5才得到的功能。[FX3官方Main菜单](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888898.html)；[Log设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888942.html)。
- 本轮在FX3 `appFw.so` 文件偏移 `0x2fc80c8` 找到 `s_allocate_tp_button_01_for_big6(...)`，`0x2fd4ae0` 为 `26view_tp_button_01_for_big6`，`0x2fd4b5c` 为源文件名 `view_tp_button_01_for_big6.cpp`。名称/类型/文件名三种相邻线索都存在，尚未反汇编其调用者和屏幕注册。[回执](fx3-static-chain-receipt.json)。
- 既有源码对照表明 FX3参考内核4.9.337/CXD90057关联，FX5公开源码5.15.179/CXD90201关联，CPU与中断控制器描述也不同。两者均包含ARM64源码，不能偷换成“完全不同指令集”，也不能因同为ARM64断言应用可运行。[平台源码审计](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage133-FX5-source-availability-and-portability/code-portability-review.json)。

### Inferences

| 单项 | 现在的真实起点 | 所需FX5材料或下一步 | 可行性结论 |
|---|---|---|---|
| 整套专业菜单与控制 | FX3已有appFw控制框架、Main页与控件线索 | FX5全部菜单树/页面注册、资源ID、属性模型/校验、状态机、消息接口；FX3显示/输入/持久化及后端逐项适配 | 缺donor专有程序；尚不能形成整套可移植实现 |
| DMM/缓存分配 | FX3模式表、GetDmmExtList、dmm.ko、正确AP配置 | FX5对应单位表/分配器/HAL/消息与缓冲消费点；实际映射/寿命约束 | 可做结构比较；当前没有FX5对象供配对 |
| 物理DDR/CPU cache | 尚无对两机硬件控制的完整证据 | 启动/DDR训练、DTB、MMU/DMA/cache协议 | 不具备同步基础 |
| CMOS RAW/ISP | FX3静态照片RAW及HDMI RAW线索 | 两机专有传感器/ISP驱动与模式/校准/协处理器固件 | 不能用GPL内核或日志字符串替代 |
| H.265主录 | 另一agent推进FX3原生MAIN链 | 保留该研究边界；FX5公开表本身无现成目标模式 | 此分支不修改H.265工具，也不把代理录制当MAIN |
| 整包刷入FX3 | 完整FX3官方包可验证；未取得完整FX5专有系统 | 型号签名/启动/分区/TEE/外设/应用ABI与独立恢复 | 当前没有可验证的移植包或可刷结论 |

### Gaps
- 整套菜单不仅是图标/控件：必须逐项对应FX5设置的读取/写入、状态依赖、模式互斥、保存恢复与实际底层动作，并对新传感器、处理器或音频等硬件专属功能明确适配结果。现有FX3框架并不能自动提供FX5设置背后的实现。
- 本轮尚未反编译 big6 构造器或恢复屏幕状态机；它可能是共享控件、既有Main页或残留通用资源。下一步可在FX3原文件内先追注册/调用交叉引用，再与未来取得的FX5控件和控制模型比较，不能预设结果。
- 本轮仅执行公开网页读取及Mac离线文件哈希/ELF元数据/字符串扫描；没有相机USB、认证、机身读写、动态装载、原Sony代码运行、固件改包或刷写。既有阶段结果均标为历史回执，未冒充本轮重新运行或实机验收。原研究目录/README/GOAL状态未修改。

## FX3本地色彩科学链实际上恢复到哪层

### Takeaway
按用户新增的“整套FX5或VENICE色彩科学移入FX3”重点，追加了三份本地原件的有界扫描。现在确实有可用于后续反向追踪的 **AP设置封装、CP校准/MLUT控制、av-cam的矩阵/1D/3D阶段与VENICE命名look** 线索，但还没有恢复完整AWB算法、RAW前处理、去马赛克、传感器CCM/校准、降噪或整条实时ISP实现。VENICE名字出现在FX3原文件里尤其不能当成VENICE ISP已经存在或可以启用。

### Cited Findings
- 先读既有FX3色彩/RAW相关报告，未找到本项目已经复原整条色彩链的回执；本轮没有重复全包哈希、执行原代码或改H.265工具。扫描脚本仅复用本轮先前核对的av-cam/appFw身份，以及旧提取清单内 `cpapp-b.bin` 的15980568字节、SHA256 `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` 记录；CP未重新计算哈希。[追加脚本](inspect_fx3_color.py)；[追加回执](fx3-color-static-receipt.json)；[CP提取清单](/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/extracted-manifest.json)。
- `appFw.so` 是AArch64 ELF；本轮读到803项动态符号，所用色彩名称模式没有命中ELF命名符号。下表所列appFw接口都是原文件中的函数签名/日志字符串，而非本轮解析到的导出函数地址。`av-cam.bin` 与 `cpapp-b.bin` 均无ELF文件头；本轮没有据此自行指定它们的加载地址、DSP类型或重定位规则。[追加回执](fx3-color-static-receipt.json)。

| 模块与位置（均为文件偏移） | 原件里的具体线索 | 当前能证明什么 |
|---|---|---|
| appFw `0x397ab90` | `infra_wrapper_imaging::detail::set_base_picture_setting_i`签名，参数含select_lut、user_lut、log_shooting、input_signal、gamut、picture_profile和`Camera::CamUserIf`消息类型 | AP存在基础画面设置的封装命名；没有证明底层色彩变换实现或调用已执行 |
| appFw `0x397d100` | `set_wb_mode_i`签名，含white_balance、AB/GM调整、color_temperature和priority_set_in_awb参数 | 可供追AP→相机消息字段；AWB统计/光源估计/增益算法尚未恢复 |
| appFw `0x397eb88` | `set_picture_profile_i`签名，含black_level、gamma、black_gamma_range/level等 | Picture Profile参数封装线索；不等同传感器黑电平校准算法 |
| appFw `0x3908d6a`、`0x3924b1c` | `model_user_lut_files read3DLUTFile`与`read3DLUTFileForCube result`日志 | 用户LUT文件读入/转换的追踪入口；没有提取数值表或验证实际应用位置 |
| CP `0x2a607c`、`0x326600`、`0x326640` | `CamCore 3D-Lut table Write Start`、`ddl_VfxSetMlutPre`、`ddl_VfxSetMlut ... l3d=... reg=...` | CP侧存在写LUT/寄存器数据相关命名与日志；尚无真实指针、表布局或硬件寄存器调用链 |
| CP `0x23b60c`、`0x2d7988`、`0x2edeb4` | `sjob_get_black_level_MON_RAW_new`、`ExecImagerCalibration`、`ImagerCalibrateADC`错误日志 | 可以把RAW黑电平与成像器校准列为独立模块继续追；未取得校准结果/ADC算法 |
| av-cam `0x38a274`起 | `MLUT_YC2RGB_ON`、L1D_A/B/C、MTX_A/B/C/D、EIGAIN、YR1D等开关标签 | 存在多阶段look控制描述；不能凭标签确定执行顺序/数据域或是否作用于主录 |
| av-cam `0xbe6ffc`、`0xbe7ed4`、`0xbf4784` | `MLUT_MTX_A_REG_VENICE_LMX0_SLOG3_SGAMUT3_ACES`、`MLUT_L1D_B_SRAM_R_VENICE_L1D0_SLOG3_SGAMUT3_ACES`、`MLUT_L3D_SRAM_R_0_VENICE_3DLUT_SLOG3_SGAMUT3_ACES` | FX3已有VENICE命名look/矩阵/1D/3D描述线索；未恢复对应表值、插值或传感器ISP |

以上位置、命中总数和每类前40条字符串均保存在[追加回执](fx3-color-static-receipt.json)。脚本的字符串窗口最多300字节，长C++签名可能被截断，不能用截断签名推导完整函数原型。未命中CCM/demosaic/debayer等名称仅是此规则/三文件范围的阴性结果，不证明固件不存在这些处理。

### Inferences
- 当前可据命名提出、但尚未以交叉引用证明的分层是：**appFw设置/用户LUT读入 → CamUserIf消息 → CP的画面/校准/MLUT控制 → av-cam/硬件阶段描述**。这仍不是恢复完成的函数调用图；各模块之间真实方向、数据域、同步/回调和当前录制路径要逐条验证。
- 若目标是把FX5/VENICE完整色彩链移入FX3，donor至少要给出与这些consumer对应的参数布局、LUT/矩阵数值和运算、RAW域与输出域边界、实时ISP调度；更底层还必须有FX3传感器适用的黑电平/坏点/增益/温度/光谱响应标定。只替换Log曲线、输出矩阵或look LUT，最多证明其中一段变换。
- 更窄且可复核的下一步是先静态恢复FX3的 `set_base_picture_setting_i`/`set_wb_mode_i`消息结构、CP的MLUT表消费者和av-cam中VENICE命名描述所引用的数值表，再与donor比对。即使这些表能读出，仍需确认是否监看、主录、代理或回放使用，以及YUV/RGB/线性/Log域，才有色彩意义。

### Gaps
- 当前没有AWB统计输入及光源/增益计算的实现证据；没有传感器专用CCM/黑电平/坏点/温度校准数值；没有去马赛克/降噪/锐化实际算法、顺序和参数；没有恢复完整RAW→主录色彩路径或用原始传感器帧做数值复现。
- 不能将这些三个文件统称为“已取得全部DSP firmware”：还需完整分区/协处理器/ROM分工和加载器证据。文件在手、名字存在，与可跨平台运行及相机输出等价，是独立验收。
- 当前资料不足以许诺FX3拥有FX5/VENICE传感器的光谱、读出噪声、动态范围或双增益行为；16bit输出/容器精度、S-Log3或S-Gamut3名字也不填补该缺口。
