# FX5 平台 缓存 RAW 与整套专业菜单移植

## 公开源码范围足够代表完整 FX5 系统吗

### Takeaway
目前取得的是五个公开源码组件，足以看到板级内存、DMA、缓存维护、加密与解压接口，不包含已被认证的完整 FX5 启动镜像、机身应用与专有摄像链。用户已明确要 FX5 整套专业菜单与功能，不能以已有 BIG6 主页满足这个目标。

### Cited Findings
- 2026-10-27 本轮重新抓取的 Sony OSS 型号页共59个压缩包链接；已下载五包是 `linux-kernel`、`cemmc-init`、`cryptoram`、`ldec`、`sio`。其余主要是运行库、网络、系统工具以及 GStreamer、gst-plugins、SRT、RTMP、SoundTouch 媒体组件。名单和类别已逐项保存，未把全部59包都称为已解包。— [Sony FX5 OSS 型号索引](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)，本地 `fx5-oss-components-classification.json`、`platform_source_fetch_receipts.json`。
- 对已有 FX5 kernel 压缩包重新算SHA256为 `1e1cf32816e841462bd1d0f4e93c4897a44d0a9b95641387c74cafb6d6f44190`，长度151522353字节；完整成员盘点64942项。没有执行、编译或加载代码。完整成员清单在 `fx5-kernel-complete-member-inventory.json`。本轮对CXD设备树、`drivers/soc/cxd`、`drivers/misc/cxd`内163个普通文件逐一读取扫描，保存18个命中源码文件的原文与SHA；这是全面目录盘点加定向代码读取，不能称为完整机身固件全面解包。— [官方 kernel 包](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz)，`platform-gpl-static-review.json`。
- 前轮型号关联源码的Makefile分别为 FX3 Ver7.00参考4.9.337和FX5 5.15.179，设备树分别关联CXD90057和CXD90201/CXD90XXX；两侧都含ARM64。具体CPU、GIC、TEE差别的文件哈希和行号已有 `stage133.../code-portability-review.json`。这些是型号关联源码事实，尚不是FX3 7.02与FX5实机所选DTB/内核的精确测量。— [FX3 Ver7.00 OSS](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)、[FX5 OSS](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)。
- 公开索引没有以Sony摄像主应用、CMOS专用HAL、ISP固件、X-OCN编码器或专业菜单资源命名的独立包。GStreamer开源包适合研究媒体管线接口；它的名字和存在不能证明Sony已经公开整套专有处理与编码实现。— [FX5 OSS组件列表](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)。

### Inferences
- 本轮优先分析kernel内尚未细读的CXD DMA与cache源码，比把普通运行库全部下载更贴合目标。其余媒体组件将来可用于核对调用接口、容器和线程语义；在没有专有调用者与实际根文件系统时，下载它们不会闭合菜单或RAW移植证据。
- 整包二进制互刷需要跨板级适配。内核版本不同本身不证明每个用户态ABI必然不兼容；必须实际核对ELF解释器、依赖库、ioctl/IPC结构、固件协处理器与安全链，不能只凭同为ARM64承诺能运行。

### Gaps
- 尚无完整FX5机身包；未取得FX5实际boot、DTB、rootfs、专有ELF、DSP/ISP/编码器固件、菜单资源与安全启动依赖。
- 本轮只对五个已有包重新校验/读取，没有下载剩余54包；没有声称通过源码索引就排除了所有隐藏或捆绑的专有实现。

## 缓存芯片调用 CMOS RAW 与解RAW能同步到什么程度

### Takeaway
缓存应拆成DDR物理资源、摄像数据缓冲池、CPU cache/DMA一致性三层。FX5公开源码确实可查到第三层和部分地址映射，却不能直接给出第一层实机芯片料号、第二层完整摄像资源表，更不能当作CMOS与RAW链路已经同步。

### Cited Findings
- FX5 `drivers/soc/cxd/udif/dma-mapping.c:34-57`将scatterlist项的物理地址放入DMA地址并做`__dma_map_area/__dma_unmap_area`；`udif/cache.c:32-40`包含`dcache_clean_poc`。`drivers/misc/cxd/dma/cdev.c:47-80`接收`DMA_MEM_TRANSFER`、复制用户参数并排队，`dma_core.c:169/190/211`导出异步内存/外设传输和复位接口。源码证据已复制到新目录 `gpl_platform_sources/`，哈希与行号见JSON。— [官方FX5 kernel源码](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz)。
- FX5 `cxd90xxx.dtsi:87-100`存在地址`0x640000000`、长度`0x20000000`的memory/reserved-memory描述；同包有3G/4G/6G/8G多个memmap样例。`cxd90201_set.dts:35`包含`memmap-4G.dtsi`。这不证明量产FX5只有4GB，也不证明这段512MiB就是RAW缓冲区。实际被bootloader选择、修订后的DTB及内存训练信息尚未取得。— [官方FX5 kernel源码](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz)。
- 已查FX3参考DTS的MDMA节点为PL330/PrimeCell（`cxd90057.dtsi:788-820`），FX5所查DTS的MDMAC节点使用Synopsys AXI DMA兼容字符串（`cxd90xxx.dtsi:424-520`）。物理地址、时钟、reset、中断和硬件寄存器约定需要分开核对；不能复制一个函数地址就通用。— [FX3源码入口](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)、[FX5 kernel](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz)。
- FX5 `ldec/driver/src/ldec_drv.c:139`明确标注LZ77DEC，寄存器族为`LZDECOMP_*`；它支持压缩流解压相关传输，不能因名称含decode就当CMOS Bayer/X-OCN解码器。`cryptoram`有AES/ChaCha20相关算法与crypto ioctl；它是加密引擎接口，不能当摄像DDR缓冲分配器。— [ldec官方包](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/ldec.tar.gz)、[cryptoram官方包](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/cryptoram.tar.gz)。
- 本轮163个CXD平台文件按不区分大小写查询`IMX510/BIONZ/X-OCN/BIG6/Bayer/demosaic/SensorRaw/ALCIN_UUD/MovieEncoder`均无匹配。kernel仍含通用IMX/V4L2驱动，目录存在不代表FX5在用的传感器型号与驱动。此为有限搜索结果，不能据此宣称整个Sony系统没有这些模块。— [官方kernel包](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz)，本地JSON记录扫描范围。
- Sony明确说明FX5使用新开发5K全画幅堆栈Exmor RS、BIONZ XR2、机内16bit场景线性X-OCN及Dual Gain；经典FX3使用Exmor R和BIONZ XR。FX3 7.02官方更新页说明RAW经HDMI向外部录机输出，可外录Blackmagic RAW。— [FX5官方特长](https://www.sony.jp/pro-cam/products/ILME-FX5/feature_1.html)、[FX3官方特长](https://www.sony.jp/pro-cam/products/ILME-FX3/feature_1.html)、[FX3 7.02更新](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)。

### Inferences
- RAW读取指传感器时序/ADC/行列布局→DMA帧；解RAW通常还指黑电平/坏点/去马赛克/色彩处理；HDMI RAW是输出链，机内X-OCN又需要压缩与容器链。四条链不能用“RAW已支持”相互替代。
- 现有材料可同步成“接口对照表”，无法同步为FX3可加载的FX5驱动。应保留FX3传感器、电源、clock/reset、DMA与存储驱动，用实际资源生产者和cache协议适配上层功能。FX5的传感器读出速度、5K原生尺寸、Dual Gain不能靠搬菜单或寄存器常量赋予FX3；具体能做的FX3模式需要目标硬件证据。
- 机内X-OCN是否能在FX3独立移植尚属未知：现有公开资料没有证明纯软件可实现目标性能，也没有证明必然需要FX5独占硬件。缺专有编码实现、输入布局、HAL、吞吐、温控和存储预算，不能先断言可行或绝对不可行。
- 所查UDIF helper直接处理物理地址不等于FX5全系统没有IOMMU；本轮不推断IOMMU硬件是否存在或当前启用。

### Inferences 补充色彩科学边界
- 用户新增“尤其FX5或VENICE整套色彩科学”的范围，需要把RAW归一化与传感器校准→黑电平/坏点/镜头补偿→去马赛克与降噪→白平衡/色适应→色彩矩阵/相机色彩空间→色调与高光/肤色处理→S-Log/S-Gamut或Look输出分别查证。上述为需要逐环节对照的分析框架，不声称Sony采用唯一固定顺序。
- 当前kernel平台代码解决地址、传输、缓存一致性和设备控制基础，163文件范围未发现Bayer/demosaic/SensorRaw/X-OCN等目标词；没有得到可认证的FX5/VENICE整套ISP、AWB、传感器特征化/校准参数。因此不能把kernel DMA工作或一份公开LUT称为整套Sony色彩科学已移植。更全面的全包与专有模块扫描由取得完整镜像后的证据决定。
- 即使取得FX5/VENICE色彩矩阵或Look，输入也要适配FX3自身光谱响应、黑/白电平、增益与噪声、曝光域和RAW布局。跨传感器照搬参数可能产生偏色，纯RGB LUT无法替代RAW前端；能否达到参考机输出必须由真实FX3原素材、参考机配对素材及输出测量另验。此为工程推论，未做FX3画质实机试验。

### Gaps
- 两机DDR厂商/料号、训练/时序、有效容量、真实带宽、摄像保留区、DMM生产者与ISP协处理器共享内存协议均未通过本轮实机取证。
- FX5专有CMOS寄存器表、时序表、黑电平/坏点/增益校正、ISP微码和X-OCN实现仍缺；这是不能“全部同步”的实质证据缺口。

## FX5 整套专业菜单与功能移到 FX3 的路径是什么

### Takeaway
用户要的整套专业菜单不只是六格主页。当前可做完整功能清单与FX3原生能力映射；真正移植需菜单应用→控制消息与状态→HAL→驱动/硬件逐层闭合。没有可刷成果，保留FX3底层的选择性移植比整系统互刷更值得进一步验证，但仍是研究判断。

### Cited Findings
- FX5 full menu有10大类别：Shooting、Project、Paint/Look、TC/Media、Monitoring、Audio、Clip Operations、Technical、Network、Maintenance；长按MENU进入。包含Scene File/Base Look、Black/Gamma/Knee/Detail/Matrix/Multi Matrix、32bit float WAV、Exposure Assist、Test Signals、Hours Meter等。它们是实际功能、状态与持久设置入口，不只是图标素材。— [FX5完整菜单](https://helpguide.sony.net/ilc/2630/v1/en/contents/menu_list.html)。
- FX5显示系统可在视频监看与信息显示两模式间用HOME切换，LCD和HDMI外屏的画面路由有专门规则，信息显示模式可用Direct Menu Priority调整操控。需移植的还有输入、显示、HDMI路由和状态模型。— [FX5显示切换](https://helpguide.sony.net/ilc/2630/v1/en/contents/swiching_screen.html)。
- FX3 7.00以上已有BIG6：Mode Settings设Fixed/Variable，在Custom Key/Dial Set里把HOME分配给支持的自定义键，电影模式按该键进入，再按返回。它与FX3 Main列表均不等于FX5十类full menu。Main列表为MENU内Main页，可另绑定Display Main Menu。— [FX3 HOME官方手册](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1002071061.html)、[FX3 Main官方手册](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888898.html)。

### Inferences
| 层/功能群 | 当前判断 | 真正需要闭合的证据 |
|---|---|---|
| 十类菜单组织、字体图标、触控/按键、页面布局 | 原理上软件层可重建；尚未完成FX5原资源或代码移植 | FX5资源与应用ELF、FX3 UI框架、焦点/按键/触摸语义、显示性能与录制中交互 |
| FPS/ISO/快门角、WB、LUT、TC、代理、媒体状态等FX3已有能力 | 可以先做能力映射，尚无FX5 IPC与FX3 API兼容证明 | 每个设置的Get/Set/通知ID、单位/枚举、锁/事务、录制中准入、参数保存/重启恢复 |
| 场景文件、Paint/Matrix、细节/降噪、曝光辅助等潜在软件功能 | 需逐项判断FX3是否有原生处理器节点，不能界面出现即算实现 | 算法/ISP节点、控制范围、图像域、输出成片与显示路径对照；可CPU实现的还需负载与延迟预算 |
| 新5K传感器模式、Dual Gain、XR2 AI、配套96kHz/32bit float音频 | 搬菜单不足以获得新硬件能力 | FX3原硬件能力、sensor/AFE/音频前端能力与校准，不复制FX5硬件专用寄存器 |
| 内录X-OCN、完整RAW工作流 | 目前未知，不能承诺，不能把HDMI RAW当已完成 | 编码实现与加速器/HAL、FX3可用输入、带宽/缓存/存储、温控、音画同步、损坏片恢复 |
| FX5内核/驱动/分区整套替换 | 现有材料不支持实际互刷 | 完整包身份与分区、启动安全链、FX3板级适配、同机数据/校准保全、独立恢复实证 |

功能层移植建议：先把十类菜单逐项标记为FX3已有、可能软件实现、硬件依赖、未知；为已有能力保留FX3底层，用一条真实Get/Set/通知/持久化通路证明UI与状态接通。单靠整页重画不会满足本任务。取得完整FX5包后先离线生成ELF依赖与IPC结构对照，再挑一个不影响录制的数据查看/已有参数设置做封闭验证。

### Gaps
- 无FX5应用ELF与资源，不能完成真实二进制依赖解析、控件/菜单树提取、消息ID匹配或ABI映射。
- 无FX3上的功能输出与交互验收；本轮未访问相机、USB、Windows、服务认证、RAM加载或持久刷写，也未改变现有FX3 agent的工作文件。
- 将来整包取得后应先确认官方型号/版本/长度/哈希→容器/签名/分区→boot/DTB/rootfs→应用/资源与动态依赖→菜单状态/API→HAL和协处理器→离线边界实验。实机测试与可恢复写入是之后独立的授权和验收步骤，离线解包不会自动放行。
