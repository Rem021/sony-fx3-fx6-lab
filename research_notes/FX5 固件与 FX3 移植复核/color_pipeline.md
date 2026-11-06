# FX5 与 VENICE 整套色彩链搬到经典 FX3 的可行性

## 能否把原厂整套链路同步到 FX3

### Takeaway
截至 2026-10-27，**原生整套搬运未证实，也没有可交付刷写方案**。可研究和验证的部分是明确输入域之后的颜色数学、部分解码算法、公开色域/Log与显示外观；FX3 自身的传感器读出、标定、ISP、内存与编码链必须保留并分别适配。把 VENICE/FX5 的表和库直接放进去，既不能补出另一颗 CMOS 的信号，也不能以相同 S-Log3 名称证明完整颜色相同。[FX5 官方硬件说明](https://www.sony.jp/pro-cam/products/ILME-FX5/)、[Sony 对 VENICE 传感器差异的说明](https://sony-cinematography.com/articles/your-venice-2-sensor-questions-answered/)

### Cited Findings
- FX5 官方说明为新 5K 堆栈式 Exmor RS 与 BIONZ XR2，具有三档 Base ISO、Dual Gain 等自己的采集链；这些是硬件/读出条件，不是 LUT 的名称。完整 FX5 专有 ISP、传感器寄存器表、每机校准和菜单程序未从目前取得的 GPL 源码中恢复。— [FX5 产品](https://www.sony.jp/pro-cam/products/ILME-FX5/)、[公开源码页](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)、[本轮整包复核](public_package.md)
- Sony 明确：VENICE 1 与 VENICE 2 6K 使用同一 6K sensor/OHB，VENICE 2 8.6K 是另一颗专用 sensor；原 VENICE 不能处理 8.6K 数据率，两个传感器的像素间距与 OLPF 设计也不同。Sony 把 8K 的颜色重现优化到与原 VENICE/6K 相近，不能反推底层代码和校准相同。— [Sony 官方问答，2021-12-02](https://sony-cinematography.com/articles/your-venice-2-sensor-questions-answered/)
- Sony 将 S-Cinetone 描述为受到 VENICE 色彩科学启发的外观；该描述没有声称将整套 VENICE 传感器/ISP 复制到 FX 系列。— [Sony S-Cinetone 说明](https://sony-cinematography.com/faqs/what-is-s-cinetone/)
- X-OCN 记录的是 16bit 场景线性的压缩 Bayer/RAW 工作流，可在后期调整 ISO/WB；并非把 s709 烘焙好的画面。FX5 官方也明确称其 X-OCN 是压缩 RAW。16bit 格式描述不等于 16 档实测动态范围或 16bit ADC 证明。— [VENICE 2 官方问答](https://sony-cinematography.com/articles/your-venice-2-sensor-questions-answered/)、[FX5 官方产品](https://www.sony.jp/pro-cam/products/ILME-FX5/)
- s709 的公开路径是先获得正确的 S-Gamut3.Cine/S-Log3 图像，再用于现场监看、样片与调色输出；RAW/X-OCN 需先按原始机型显影。这个显示后段可以共享，不代表前段传感器采集相同。— [Sony s709 工作流，2019-06-27](https://sony-cinematography.com/articles/sony-s709-look-up-table-workflow-part-three-of-four/)、[Sony LUT/ART 官方库](https://sony-cinematography.com/resources/luts/)

### Inferences
下表是工程推断与当前证据状态，**不是已经验证过的 Sony 固件移植合同**；Sony 没有公开全部内部阶段顺序。RAW 压缩记录分支与处理后 XAVC 分支也不能画成完全相同的一条直线。

| 层 | FX5/VENICE 直接搬到 FX3 | 可继续研究的受限路径与验收 |
|---|---|---|
| CMOS 时序、行列读出、ADC/增益、光学低通和 IR 滤光 | 不具备直接兼容证据；FX5/VENICE 与 FX3 传感器/处理器不同 | 继续使用 FX3 自身驱动；必须拿到 FX3 实际 RAW/采集模式，不把读取现成 X-OCN 文件当控制 FX3 CMOS |
| 黑电平、线性化、饱和白点、坏点与 PRNU/DSNU | 不能整表复制；这些数值与具体 sensor、增益、温度或个体有关 | 校准 FX3 自己的黑场/平场、模式和增益；不能把 PP 的 Black Level 美学控制当 sensor 黑电平校准 |
| 镜头阴影、色偏、畸变及呼吸补偿 | 需镜头/焦段/焦距/光圈与读出条件适配 | 保留 FX3 镜头元数据与补偿；独立验证中心/边角，避免 RAW/Log 已做过的补偿再做一次 |
| 解码与解 Bayer | 解码已录文件的 LLVC 可有独立软件实现；这不等于 FX3 RAW 采集/写 X-OCN | 有限 Sony 素材输入已有算法证据；搬到 FX3 实时链仍缺 buffer 布局、CFA/黑白点、HAL、吞吐与硬件验收 |
| 空间/时间降噪、坏纹理抑制、锐化 | 未恢复完整原厂链；sensor 噪声与运动/跨帧历史不可由静态 3D LUT表达 | 单独识别算子和时域状态，测噪声谱、细节、运动残影、延迟与长录热负载 |
| AWB 光源/场景估计、WB 增益 | 可研究控制/插值算法，不能将 VENICE camera RGB 的增益表无条件乘在 FX3 上 | 固定 FX3 输入和元数据，分离“估计光源”与“按已知 K/Tint 改增益”；先固定 WB 验证，再研究自动模式 |
| camera RGB → 标准 RGB 的矩阵/非线性校色 | 原厂 camera-specific 表不能盲搬；相同输出色域不表示相同 sensor 光谱响应 | 对 FX3 重标定并与目标做配对验证；后期矩阵/曲线/3D 变换可近似，需灯光与曝光留出样本 |
| S-Gamut3/Cine、S-Log3 | 公共颜色空间/传递函数可以实现；不需要据此替换驱动 | FX3 已具备这些记录域；固定 gamut、range、WB、EI/曝光与解码，避免双变换；公共数学相同不证明 camera RGB 相同 |
| s709、Signature、创作 LUT/CDL | 最容易共享的外观/显示层；仍须匹配输入/输出、范围和采样网格 | 可后期应用，或按 FX3 官方支持路径监看/烘焙；这是局部外观，不能完成整套颜色目标 |
| 色调、高光与 gamut mapping | 全球静态部分可由曲线/3D LUT表示，局部/时变部分另需算子 | 测灰阶、肤色、饱和光源与高光渐变；不能恢复 FX3 输入已剪切的通道/细节，也不能许诺复现目标传感器宽容度 |
| XAVC/HEVC/X-OCN 编码、缩采样、缓冲与文件封装 | 不由颜色表决定；缺原厂编码硬件/HAL移植与资源证据 | 另一个 H.265 主录任务继续验证 FX3 原生 encoder/DMM；颜色移植不证明 1080p30 HEVC 主录可用，更不证明 X-OCN 录制可用 |

实际值得推进的研究是：在 FX3 原系统和固定采集条件上，分别识别输入修正、场景颜色、显示输出，验证哪些全局响应可以匹配 FX5/VENICE。需要同场景、同光源、曝光阶梯、灰/色卡、肤色、饱和 LED 与高光的配对原片，并留出未拟合条件；单张相似或同一 LUT 不足以证明所有光源、曝光与运动下相同。此为建议的验证设计，本轮没有拍摄或拟合。

### Gaps
- FX5 全包未取得；VENICE 2 固件专有内层仍未解密。未得到可安装到 FX3 的完整 ISP/驱动代码。
- VENICE 1、VENICE 2 6K、VENICE 2 8.6K 必须分开记录。现有 GX-8 素材证据只对应固定原 VENICE 输入；CV8K 样片需结合真实控制头，不仅看机身字符串选表。
- 缺目标 FX3 的实际 RAW tap、实时 ISP 注入 ABI、整机校准、完整输入模式、内存/并发/热负载以及安全恢复验收。不能给整套原生移植定工期或成功概率。

## 本地 VENICE 研究现在实际到了哪里

### Takeaway
已核验路径存在且当前分支为 `codex/venice-color-fidelity`、HEAD `28f74ffe76ee845ec7b51cf4ae5229a56688a4bd`；历史报告中的旧分支名不能当当前状态。**固件本身只打开了外层，实质颜色/解码恢复主要来自 Sony RAW Viewer 的桌面显影库及固定原始样片**；一份完整输入在 iPhone 的历史成功不等价于 FX3 相机 ISP 移植。[本轮重验清单](color-local-evidence.json)

### Cited Findings
- Sony 日本当前仍列 VENICE 2 V5.00、2026-07、862,640,780 字节。本地 ZIP 完整重哈希与原回执相同：`04972a7e6635f33236443889727c580f833a02322d5b2c12df7e69d5533c7610`，没有重下大包。— [官方固件页](https://www.sony.jp/ls-camera/update/VENICE_2.html)、[本轮本地证据](color-local-evidence.json)
- V5.00 `.bin` 为 tar；本轮直接静态读取成员并核对 `BERLIN/DATA23213` 的长度 287,401,488 和 SHA256 `662a93a061d17691bf4d243788c94a4dff7b97c92b48e6eeddf87f4c3f5d0019`。property 明示 `enctype="type4"`；首 MiB 熵约 7.999852 bit/byte。没有用熵指定密码算法/密钥，也没有解密该内层。— [本轮复验](color-local-evidence.json)、[原解包报告](/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware/reports/venice-firmware-2026-10-23/REPORT.md:29)
- 历史研究从 RAW Viewer 6.0 的 `libSonyRawDev.dylib` 等恢复了部分 K/Tint、相对 WB、机型相关矩阵、去 Bayer、LLVC与输出算子；固定官方 VENICE `MPC-3610`/GX-8 `A006C010` 首帧链已有对应原函数/输出比较。它是桌面显影实现的局部恢复，不是已恢复 VENICE 固件全部 ISP/AWB。— [当前报告](/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware/reports/venice-firmware-2026-10-23/REPORT.md:52)、[固定源映射](/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware/reports/venice-firmware-2026-10-23/REPORT.md:231)
- 当前保留的物理回执记录 build497、原始 MXF→LLVC/packed→去 Bayer/颜色→输出/读回已通过；同时明确四个独立边界：显式曲线生成公式未恢复、仅一个固定 GX-8 首帧 profile、没有 iPhone sensor/ISP/AWB 或 Sony 相机等价证明、HDR/视频/性能/主观画质不在该完成门内。本轮只读取并重哈希该历史回执，未重跑设备。— [历史实机完成回执](/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware/work/venice-firmware-2026-10-23/llvc-physical-01/completion-audit.json)、[本轮摘要与哈希](color-local-evidence.json)
- 今天的组件合同也显式区分公共输出算子与 sensor-specific 输入校准，禁止将公共色域矩阵解释成传感器光谱/去 Bayer/曝光锚点，禁止将 s709 显示资源冒充完整 scene/ISP。— [2026-10-27 当前合同](/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware/reports/venice-photo-match-2026-10-25/VENICE-COMPONENT-CONTRACT-2026-10-27.md:54)
- 本轮另一研究分支已在 FX3 原件读到 appFw 画面/WB/PP 设置签名字符串、CP 的 MLUT/RAW黑电平/成像器校准日志、av-cam 的 VENICE/SLOG3/SGAMUT3/ACES 命名矩阵与1D/3D阶段描述。本分支已只读复核其笔记；它们是下一步追消息、数值表消费者与主录/监看分支的具体起点，未恢复表值、调用图或完整ISP，也不是“隐藏VENICE系统开关”。— [本轮FX3静态证据](fx3_local_chain.md)、[原件扫描回执](fx3-color-static-receipt.json)

### Inferences
- 可复用资产主要是已经明确数值合同的算法与输出阶段；Sony 的相机输入表必须匹配原始传感器域。将桌面 ARM64 Mach-O 直接搬到 FX3 Linux ELF/专有实时链也需要重新实现 ABI、资源和硬件接口，不能因都是 ARM64 就视为可加载。

### Gaps
- 没有完整 FX5/VENICE 自动光源估计、sensor 黑/白/PRNU标定与实时多帧降噪恢复证明。已知色温的 WB 数学恢复不等于 AWB 恢复。
- 现存 HEAD 的未跟踪 `work/venice-component-contract-2026-10-27/` 保留；本轮未编辑该工作树任何文件，所有新证据仅在本 Mac notes 目录。

## FX3 7.02 的 LUT 能力到底改变哪里

### Takeaway
不能笼统说 FX3 自定义 LUT “只能监看”，也不能把 `Embed LUT File` 叫“已烘焙”。**当前经典 FX3 官方指南确有 PPLUT1–PPLUT4 的录制像素应用路径；Log/Cine EI 的 Display LUT 与 LUT 文件嵌入路径则是另一组用途。** 两种方式都不复制 VENICE 传感器/ISP；本轮没有在用户机身上操作或读回验证。[FX3 Picture Profile](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000876510.html)、[Log 设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888942.html)

### Cited Findings
- `Display LUT` 明确用于拍摄/回放时显示预期调色效果；`Select LUT` 可选内置 s709 和用户表。FX3 已有 s709，并非必须刷入 FX5 才能取得。— [Display LUT](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888936.html)、[Select LUT](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888941.html)
- 官方元数据说明：Log/Flexible ISO/Cine EI 保留 S-Log3 素材；`Embed LUT File` 在文件中嵌入 LUT，并另存 `M4ROOT/GENERAL/LUT` 供支持软件恢复监看条件。这是文件/元数据行为，不能推导主录像素已烘焙。— [Sony 元数据说明](https://helpguide.sony.net/di/pp/v1/en/contents/TP1000756722.html)
- 当前经典 FX3《Picture Profile》原文明确 PPLUT1–PPLUT4 “Shoots and records movies with the user LUT applied.” 用户可把已登记表设为 Basic Look。因此存在官方说明支持的机内外观录制路径；不能沿用旧论坛结论排除它。— [FX3 Picture Profile](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000876510.html)
- 当前指南的 BIG6 页面把 Log Off 时的 PP Gamma/Color Mode 与 Log On 时的 Select LUT 分开显示。此为当前官方功能文档，未据此宣称用户7.02实机所有选择/介质组合均已验。— [FX3 home screen](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1002071061.html)
- 自定义表格式限定17或33点 `.cube`，输入选项为 S-Gamut3.Cine/S-Log3 或 S-Gamut3/S-Log3。VENICE `.art` 不属于该导入格式；官方 HDR/P3/Rec709 LUT 也必须按输出目标分别选择。— [FX3 Manage User LUTs](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888940.html)、[Sony 官方 LUT/ART 库](https://sony-cinematography.com/resources/luts/)
- HDMI 是独立输出路径：FX3 指南说 Log 或 PPLUT 下并行卡内录制时 HDMI 为1080，HDMI Only 或 RAW为相应4K例外；RAW不能卡内录制，RAW输出需Log不为Off。不能从 LCD 看到表就断言 RAW 数据被烘焙，也不能把外录与卡内主录当同一产物。— [FX3 HDMI 设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885432.html)
- 经典 FX3 7.02 官方更新页当前包含 BIG6、用户 LUT 优化、RAW HDMI外录 BRAW等历史改进；这些是原 FX3 功能，不能自动扩大为新 CMOS 读出、X-OCN编码或完整 VENICE 色彩链。— [7.02 官方说明](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)

### Inferences
| 路径 | 可判断的行为 | 对整套色彩目标的意义 |
|---|---|---|
| Log/Cine EI + Display LUT | 官方定义为监看预览 | 只改变显示/观察，不足以证明主录像素改变 |
| Log + Embed LUT File | LUT附件与独立文件/元数据，可供后期使用 | 不是像素烘焙或 ISP替换 |
| 普通 PP/PPLUT + Basic Look | 官方说明可把用户表应用到录制图像 | 可以研究机内“目标外观”，仍是 FX3 前端后的局部变换 |
| 非 RAW HDMI/外录机处理 | 输出模式与外录器决定实际编码画面 | 需独立抓取输出验证；本轮未证明所有 HDMI LUT组合 |
| HDMI RAW | 独立 RAW传输/外录工作流 | 不能把 monitor LUT当 RAW已带颜色；更不等于卡内X-OCN |

建议后续用同一输入/曝光分别保存原始Log、Display LUT On/Off、Embed On/Off、PPLUT与外部HDMI样本，独立解码实际像素/metadata再比较；Sony软件自动套嵌入表时须关闭自动处理另作对照。此项是待做的验收设计，没有以文档代替实机证据。

### Gaps
- 官方当前文档确证 PPLUT功能，但本轮没有得到用户7.02机身菜单和实际卡内成片读回；不将“可按官方功能验证”写成“已替用户完成机内直出”。
- **PPLUT最低引入版本本轮未证实。** 当前指南标题是 Ver.2 or later，章节未给出该功能的最低版本；不能把标题直接解释为2.00就具备PPLUT，也不能仅由当前网页推定用户7.02所有相关菜单/组合已运行验收。7.02更新页也未单独说明PPLUT最低版本。
- HDMI非RAW是否在每一组合带LUT，当前所核页面没有完整真值表，本轮保留此缺口；不以旧讨论替代当前精确输出验收。
- 原厂全链目标继续开放。公开LUT导入、PPLUT烘焙、后期颜色变换和完整固件/ISP移植必须单独报告。
