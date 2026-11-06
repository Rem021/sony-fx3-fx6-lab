# FX5 与 VENICE 如何移入 FX3

核查日期：2026-10-27（美国西海岸）。对象是用户现有的经典 ILME-FX3、已确认版本7.02；目标包含FX5整套专业菜单与功能，并重点评估FX5或VENICE整套色彩科学。另一agent的1080p约30帧H.265主录研究独立保留。

**当前没有取得来源可核验的FX5完整机身固件，也没有可交付的整系统或整套色彩链移植方案。** 已取得并复核的是五个FX5官方开源组件；它们能解释部分DMA与缓存接口，无法代替专有菜单、传感器驱动和图像处理程序。VENICE 2固件虽已取得，专有内层仍未解密。FX3原件则提供了白平衡、画面设置、LUT和VENICE命名矩阵的具体追查入口，值得沿原系统做局部适配。工程上更有依据的方向，是保留FX3采集和硬件控制，逐层验证能够重用的颜色处理与专业控制；这与把FX5/VENICE整包刷进去是不同工作。以下区分公开事实、离线发现和仍需验证的推断，未将界面、字符串或相似画面当作功能完成。

## 公开源码可读，完整FX5系统尚未取得

本轮日本官方支持页仍明确表示暂无更新信息；英国与亚太可读取的列表是Catalyst、RAW Viewer、Monitor & Control等配套软件。中国商城“固件下载”按钮进入通用下载中心，未给出FX5专用文件。美国、新加坡及pro.sony的部分读取遇到超时或403，中国动态型号查询也未完成，因此结论限定为**本轮公开检索未取得整机包**，不扩展为所有渠道都不存在。日本产品页当前列2026-11-20预定发售，Ver.2.00为2027年8月以后计划，二者均不能当作已下载固件版本。([日本支持](https://support.sony.jp/electronics/support/products/ilme-fx5)、[英国下载](https://www.sony.co.uk/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)、[日本产品页](https://www.sony.jp/pro-cam/products/ILME-FX5/))

Sony OSS索引共有**59个组件压缩包链接**。本轮复用并重算五包SHA256：linux-kernel、cemmc-init、cryptoram、ldec、sio，总计151,596,639字节；没有重复下载。对kernel的**64,942项成员完成目录盘点**，对163个CXD平台文件逐个读取，保存18份命中源码及摘要。其余54包未全部下载，也没有把成员盘点称为逐行审计，更没有称为机身固件全面解包。原始页面、分类和检查脚本均保存在[证据入口](<../research_notes/FX5 固件与 FX3 移植复核/README.md>)。([FX5官方源码分发](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html))

源码已有跨平台差异：FX3 Ver7.00参考包为Linux 4.9.337、CXD90057关联文件，FX5为5.15.179、CXD90201/CXD90XXX关联文件；两侧都有ARM64。**这不能单凭内核版本宣判所有应用都不兼容，也不能因同为ARM64认定能运行。** 实际移植仍须核对启动、DTB、库依赖、进程消息、驱动接口和协处理器固件。上述是型号关联源码，未测量两台机身当前选中的配置。([FX3参考源码](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)、[FX5源码](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html))

## 整套色彩科学受传感器和实时处理约束

用户要搬的是完整成像链。需要分别查证传感器读出、黑电平与坏点校准、镜头补偿、去马赛克、时空降噪、白平衡、相机RGB校色、Log/色域、色调与显示外观，以及编码输出；Sony并未公开全部内部顺序。FX5使用新5K堆栈式Exmor RS与BIONZ XR2，经典FX3使用Exmor R与BIONZ XR。VENICE也须区分原VENICE/第二代6K与第二代8.6K；Sony明确说明8.6K传感器的像素和光学低通设计不同，即使最终颜色被优化到相近，也不代表采集与标定相同。([FX5硬件](https://www.sony.jp/pro-cam/products/ILME-FX5/feature_1.html)、[FX3硬件](https://www.sony.jp/pro-cam/products/ILME-FX3/feature_1.html)、[Sony VENICE传感器问答，2021-12-02](https://sony-cinematography.com/articles/your-venice-2-sensor-questions-answered/))

| 色彩链层级 | 当前移植判断 | 必须补齐的证据 |
|---|---|---|
| CMOS读出、ADC、增益及黑/白/坏点校准 | 不能直接照搬另一传感器参数；保留FX3前端 | FX3模式、RAW布局、温度/增益校准、实际传感器响应 |
| 去马赛克、时空降噪、锐化 | 完整原厂实时实现未恢复 | 算法、帧历史、ISP接口、运动细节与负载验证 |
| AWB与相机RGB校色 | 控制和数学可研究，输入表须适配FX3 | 光源估计、WB增益、传感器矩阵及多光源配对数据 |
| S-Log3/S-Gamut3与全局颜色变换 | 公共数学和局部算法可复用 | 明确线性/Log、色域、量程、曝光与处理顺序 |
| s709、创作LUT、部分色调/色域映射 | 最容易共享的外观层 | 正确输入、输出目标及真实录制像素验证 |
| X-OCN或HEVC录制 | 与颜色表分开评估，当前无移植验收 | 编码器/HAL、缓冲、带宽、音画同步与恢复 |

表中属于工程判断。其含义是：相同S-Log3或S-Gamut3描述的是输出表示，不能证明两机在LED、混合光、肤色和高光下产生相同信号。静态LUT也不能表达跨帧降噪，不能补回FX3输入已剪切的通道。Sony将S-Cinetone称为受VENICE启发的外观，s709工作流也要求先获得正确的S-Gamut3.Cine/S-Log3输入；这些公开资源没有提供完整传感器ISP。([S-Cinetone官方说明](https://sony-cinematography.com/faqs/what-is-s-cinetone/)、[s709工作流，2019-06-27](https://sony-cinematography.com/articles/sony-s709-look-up-table-workflow-part-three-of-four/))

本地VENICE 2 V5.00的ZIP、tar格式bin和内部DATA23213本轮均重新核对摘要。**外层已经打开，type4专有内层尚未解密**，高熵本身不能确定密码或密钥。既有研究的实质算法成果主要来自RAW Viewer桌面显影库：部分WB、机型矩阵、去Bayer、LLVC与输出算子，以及固定VENICE/GX-8首帧的数值对照和历史手机读回。它没有恢复完整相机AWB、传感器标定或实时多帧ISP，也没有证明可加载到FX3。X-OCN是16bit场景线性压缩RAW工作流，解码既有文件与让FX3采集、编码X-OCN也需分别验证。([官方固件页](https://www.sony.jp/ls-camera/update/VENICE_2.html)、[本轮本地复验](<../research_notes/FX5 固件与 FX3 移植复核/color-local-evidence.json>)、[详细色彩边界](<../research_notes/FX5 固件与 FX3 移植复核/color_pipeline.md>))

## FX3已有色彩节点，下一步应恢复数值和真实消费者

FX3 7.02完整包、解密FDAT及主要提取件重新计算摘要，与封存回执一致。在appFw中发现画面、WB和PP设置签名字符串，包含色域、Log、LUT、色温和AWB优先级；CP区域有MLUT写入、RAW黑电平和成像器校准日志；av-cam有YC→RGB、矩阵、1D/3D阶段描述，并出现VENICE/SLOG3/SGAMUT3/ACES命名。这些是实际原件里的定位线索，偏移和脚本已登记。**本轮尚未提取对应数值表、恢复调用图，或证明其作用于主录而非监看、回放等分支。** 因此不能称为隐藏的VENICE系统或完整色彩开关。([FX3静态链笔记](<../research_notes/FX5 固件与 FX3 移植复核/fx3_local_chain.md>)、[色彩扫描回执](<../research_notes/FX5 固件与 FX3 移植复核/fx3-color-static-receipt.json>))

这里形成了具体的离线路线：追画面/WB消息结构，找到CP的MLUT表消费者，恢复av-cam命名描述引用的矩阵和LUT数值，再确定每段的输入域、运算顺序、插值及输出分支。取得FX5或VENICE相应实现后，才有条件比较哪段可重用、哪段需要FX3校准。桌面显影算法可以作为数值参照，不能把桌面库直接视为相机实时模块。

另一个实际入口是当前经典FX3官方指南中的**PPLUT1–PPLUT4：文档明确支持把用户LUT应用于录制画面**。需要分清三条路径：Display LUT用于监看；Embed LUT File保存随片LUT/元数据；PP/PPLUT支持录制外观应用。用户表为17或33点cube，需匹配S-Gamut3或S-Gamut3.Cine/S-Log3输入。不能笼统说FX3 LUT只能监看，也不能把嵌入附件说成像素烘焙。([Picture Profile](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000876510.html)、[Display LUT](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888936.html)、[嵌入LUT说明](https://helpguide.sony.net/di/pp/v1/en/contents/TP1000756722.html)、[用户LUT格式](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888940.html))

**PPLUT最低引入版本本轮未证，用户7.02的实际菜单与卡内成片也未验证。** 当前手册的Ver.2+总标题不能证明该功能从2.00就存在。即使后续确认PPLUT可用，它完成的仍是FX3前端之后的一段外观变换，不能作为整套FX5/VENICE色彩链迁入的验收。

## 缓存和RAW要按硬件、资源与数据域分别适配

“缓存芯片调用”包含三层：物理DDR及启动训练、摄像DMM缓冲池、CPU cache/DMA一致性。FX3已有GetDmmModeId、GetDmmExtList、SetMemTbl和正确AP DmmCfg的比较起点；FX5公开源码可见DMA异步传输、cache clean/map/unmap与地址转换。它们尚未组成两机统一的内存模型。参考设备树中FX3与FX5的DMA控制器描述不同，FX5又包含3G/4G/6G/8G多个内存样例；不能由某个样例推定量产RAM容量，或直接复制物理地址。([FX3本地证据](<../research_notes/FX5 固件与 FX3 移植复核/fx3-static-chain-receipt.json>)、[平台源码复核](<../research_notes/FX5 固件与 FX3 移植复核/platform-gpl-static-review.json>)、[官方kernel包](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz))

FX5的ldec源码明确是LZ77解压，cryptoram是加密接口；名称不能用来证明Bayer或X-OCN解码。FX3本地已有静态照片packed/unpacked RAW序列和HDMI RAW控制线索，官方也提供HDMI RAW外录，但这没有恢复CMOS寄存器/时序、实时帧缓冲、ISP调度或内部RAW编码。真正的数据链应分别核对传感器→RAW缓冲→图像处理→XAVC，以及RAW缓冲→外部输出或压缩RAW编码。物理颗粒、训练参数、实际DTB、共享内存和帧完成/释放协议仍缺。([ldec官方包](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/ldec.tar.gz)、[FX3 HDMI设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885432.html))

原H.265任务应继续沿FX3自身主录链验证。既有FX5官方录制表核查没有找到现成的1080p29.97 HEVC主录组合；HEVC HD代理不能替代主录，表中缺项也不证明硬件绝对不能编码。颜色节点恢复与内存接口比较不会自动证明目标编码模式可用。([FX5录制表](https://helpguide.sony.net/ilc/2630/v1/en/contents/video_quality_setting.html)、[既有表格复核](../work/sony-firmware-20261024/stage133-FX5-source-availability-and-portability/fx5-recording-table-review.json))

## 整套菜单需要功能后端，验证应从FX3原生能力起步

FX5完整菜单有Shooting、Project、Paint/Look、TC/Media、Monitoring、Audio等十类，包含场景文件、Matrix/Multi Matrix、降噪与音频等真实控制。用户要的是这些完整能力；FX3已有BIG6不能满足这一目标。移植必须接通页面→属性与状态→控制消息→HAL→驱动/硬件，并处理录制中准入、保存重启和LCD/HDMI路由。当前缺FX5专有应用、资源与接口，无法完成逐项二进制配对。([FX5完整菜单](https://helpguide.sony.net/ilc/2630/v1/en/contents/menu_list.html)、[显示路由](https://helpguide.sony.net/ilc/2630/v1/en/contents/swiching_screen.html))

| 功能群 | 当前可研究路径 | 尚未完成的门槛 |
|---|---|---|
| FX3已有的FPS、WB、ISO、TC、LUT等 | 保留FX3底层，适配专业菜单控制 | 真实Get/Set/通知、单位、事务和持久化 |
| Matrix、场景文件、降噪等 | 逐项定位原生节点和算法 | 数值合同、处理域、输出与负载验证 |
| 5K/Dual Gain、新AI与音频能力 | 按具体硬件能力单独评估 | 菜单不能提供缺失的采集或处理硬件 |
| 内录X-OCN | 目前未知，不能给可行承诺 | 编码实现、加速器、资源和可靠成片 |
| FX5整系统刷入 | 当前没有可刷实现 | 完整包、启动/分区/板级适配及独立恢复实证 |

接下来的有效成果应是带输入输出合同的单个功能：离线恢复一个颜色表及消费者，确认其属于主录路径，再用FX3原片与目标机同场景素材做数值对照。灰阶、肤色、高光、饱和LED和混合光要包含未参与拟合的条件，固定曝光、WB、色域、量程并排除自动套LUT。之后才分别检验机内像素、长录、音画同步、温控和恢复。这样能明确测出局部迁移的收益和边界，而不把整套系统是否可搬的未知，转成未经验证的承诺。

本轮完成公开资料复核、原件哈希、归档/源码/ELF元数据和有界字符串分析；未操作相机、USB、Windows或手机，未运行Sony代码、改包或刷写。除新增报告、证据目录及项目入口链接外，既有H.265工具、旧阶段、GOAL和VENICE工作树均未修改。全部研究笔记与机器回执见[证据索引](<../research_notes/FX5 固件与 FX3 移植复核/README.md>)。
