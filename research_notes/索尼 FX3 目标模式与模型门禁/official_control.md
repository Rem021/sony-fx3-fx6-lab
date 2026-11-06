# 经典 FX3 7.02 的 Sony 官方远控路径与目标主录模式

## 1. 当前 SDK / PTP 是否支持经典 FX3 7.02？

### Takeaway

截至 2026-10-25，Sony 当前公开版本是 Camera Remote SDK **2.02.00** 和 Camera Remote Command **2.02.00**，均于 **2026-06-10** 发布。经典 `ILME-FX3` 明确在支持名单中，但名单不代表所有属性、所有枚举或目标主录组合都能设置。[SDK](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)；[PTP Command](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html)

### Cited Findings

- SDK 将经典 FX3 标注为固件 Ver.2.00 以上，并要求使用前更新到最新固件；`ILME-FX3A` 单独列出，因此这里不是把 FX3A 支持套用到旧 FX3。当前版本公告为 2.02.00，2026-06-10；该版本新增机型是 ILCE-7RM6。[SDK 支持与公告](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)
- PTP Command 也单独列出 FX3 与 FX3A，并声明仅支持最新固件；逐机型的接口能力要看包内 README，具体命令能力要看命令参考，不能从总名单推出。当前版本同为 2.02.00，2026-06-10。[PTP 支持、脚注与公告](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html)
- 经典 FX3 当前固件页列 **7.02，2026-03-17**，更新内容是稳定性改善；7.00 的发布日期为 2025-08-26。该页的适用型号仅 ILME-FX3。[FX3 7.02 官方固件页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)
- SDK 的 Windows 11 支持脚注限定 Intel / AMD，排除 ARM 处理器；这是主机支持条件，与相机能否录制目标编码无关。[SDK OS 脚注](https://support.d-imaging.sony.co.jp/app/sdk/ja/index.html)
- PTP 公告提醒部分型号的 Camera Control PTP 2 命令从 2027 年起可能不能使用，具体型号需看包内 README；公开公告没有提供足以认定 FX3 就是其中之一的型号清单。[PTP 2026-06-10 公告](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/ja/index.html)

### Inferences

- 按当前两条官方条件与当前 FX3 固件页的交集，经典 FX3 7.02 属于官方远控工具的机型 / 最新固件适用范围；这只是支持资格判断，不是对本机连接、具体属性或目标组合的实测。
- `SDK 支持 FX3`、`某属性支持 FX3`、`该属性在当前状态允许某值`、`该值组合能生成目标主片` 是不同证据层。当前只闭合第一层。

### Gaps

- 未取得逐属性 FX3 7.02 功能表、逐状态 allowed-values 列表，也未进行连接或属性读取。本轮范围不含任何相机、USB、认证、驱动或 SDK 运行。

## 2. 官方主录表是否提供 1080p29.97 HEVC 4:2:0 10bit 约 16M？

### Takeaway

经典 FX3 的当前官方帮助指南没有列出该**主录**组合。它把 HD HEVC 10bit 16M 放在代理设置中，并明示代理伴随主片同时录制；这不能满足本任务的独立机内 MAIN 录制目标。[主录格式](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html)；[代理设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)

### Cited Findings

- `File Format (movie)` 的六个主录格式为 `XAVC HS 4K`、`XAVC S 4K`、`XAVC S HD`、`XAVC S-I 4K`、`XAVC S-I HD`、`XAVC S-I DCI 4K`；该页解释 HS 使用 HEVC，DCI 选项要求固件 3.00 以上。没有列出 HS HD 主录。[File Format (movie)](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html)
- 主录设置表中，HS 4K 分辨率均为 3840×2160，帧率组为 59.94/50p、23.98p、119.88/100p，没有 29.97p。S HD 的 29.97/25p 可选 50M 4:2:2 10bit、50M 4:2:0 8bit、16M 4:2:0 8bit；所以主录表里的“HD 16M”不能当作 HEVC 10bit。[Movie Settings (movie)](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)
- 代理表的 HS HD 为 1920×1080、HEVC/H.265、4:2:0 10bit、16 或 9Mbps，帧率仅写“最高 59.94/50p”；此表本身没有逐主片帧率给出代理帧率映射。开启代理的定义是同时录制，且相机不能回放代理；普通 119.88/100p 不可开代理。[Proxy Settings](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)
- Sony 日本经典 FX3 规格页也把 1080 HEVC 10bit 16/9M 放在“プロキシー記録（ビデオ）”行，与主片记录规格分行。[经典 FX3 官方规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)
- 三篇指南标题均限定 `ILME-FX3 Ver.2 or later`，不属于 FX3A 指南。HTML 未见明确“发布日期”或“最后更新日期”；版权元数据为 2022，不能据此称内容停留在 2022。本轮 HTTP `Last-Modified`：主格式和主录表均为 **2025-08-26 10:36:18 GMT**，代理表为 **2025-08-26 10:36:25 GMT**；这些是服务器元数据，不当作编辑发布日期。[三页 URL、正文 SHA-256 与 HTTP 元数据回执](../../work/sony-firmware-20261024/stage11-model/official/official-source-receipts.json)

### Inferences

- 已公布的官方用户模式不满足目标。当前没有公开 Sony 证据证明 SDK / PTP 能将菜单之外的 HS HD 设为独立主录；远控接口的存在不能自动绕过机型模式约束。
- 代理规格证明厂商支持某条 HD HEVC 编码用途；它没有证明同一管线在 MAIN 路由、29.97p、音频 / 封装 / 录制状态机上的完整能力。

### Gaps

- 未找到 Sony 对“SDK 可设置菜单未列出的 HS HD MAIN”的明确声明或 FX3 7.02 专用 allowed-value 表；也没有主片样本。这是尚未证实，不是硬件不可能的证明。

## 3. 公开 property / enum 能否与已恢复的带类型模型对上？

### Takeaway

当前只能做菜单语义与既有离线模型的对应，不能给出经过官方文档核实的 SDK 数值属性 ID、PTP property code 或 enum 值。SDK / PTP 细节包需要许可流程，本轮未接受协议、未下载包；这只限制官方接口证据，不妨碍固件离线分析继续推进。[SDK 许可](https://support.d-imaging.sony.co.jp/app/sdk/licenseagreement/en-US.html)；[PTP 许可](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/licenseagreement/en-US.html)

### Cited Findings

- 官方 SDK 页把 API Reference 列为提供物；PTP 页把 Command Reference 列为提供物，均引导到申请或许可入口。PTP 页还说明个人用户不能下载该工具资料。[SDK 提供物](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)；[PTP 提供物与 FAQ](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html)
- SDK 许可原文将下载本身视为接受协议：`DOWNLOADING, COPYING OR OTHERWISE USING THE SOFTWARE YOU ARE AGREEING TO BE BOUND BY THE TERMS OF THIS AGREEMENT`。PTP 许可同样覆盖协议、示例及文档的下载 / 使用。按本轮“不接受法律条款”的范围，停在公开 HTML；未绕过许可页，也未从第三方镜像拿受限包。[SDK 协议](https://support.d-imaging.sony.co.jp/app/sdk/licenseagreement/en-US.html)；[PTP 协议](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/licenseagreement/en-US.html)
- 可直接核实的官方语义是：格式由 `File Format` 选择；帧率、码率、色度采样和位深由主录设置控制；代理另有独立格式和录制设置。公开帮助指南没有将这些菜单项映射为 SDK 数值键或 PTP 属性码。[主格式](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html)；[主录设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)；[代理设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)
- 既有离线字符串包含 `convert_movie_file_format(setting_file_format_t, ...)`、`determine_movie_rec_frame_rate(...)` 及 `convert2MovieMainParams(...)`。后者带有分格式、分帧率组的强类型记录设置输入，例如 `setting_movie_record_setting_xavc_s_hd_30p_25p_type`；这属于本项目对固件的离线证据，不是 Sony SDK 文档。[既有模型字符串摘取及原文件哈希](../../work/sony-firmware-20261024/stage11-model/official/existing-model-semantic-comparison.json)

| 研究字段 | 可核实的官方菜单语义 | 本轮 SDK / PTP 数值证据 | 与现有模型的关系 |
|---|---|---|---|
| MovieFileFormat | 主录格式枚举，见上节六项 | 未取得准确 property ID / code / enum | `setting_file_format_t` 语义相关；未证明值域或数值相同 |
| FrameRate | Rec Frame Rate，按当前格式分组 | 未取得逐 FX3 allowed-values | 与分格式帧率类型语义相关；未证明直接透传 |
| RecordingSetting | Record Setting，绑定码率、采样和位深 | 未取得 compound enum 数值 | 与分格式、分帧率组 record-setting 类型语义相关 |
| YUV | 菜单将采样与位深放在记录设置中 | 未核实独立 YUV property 或 enum | 内部 YUV 参数不能直接当成公开可写属性 |

上表官方语义来源：[格式页](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html)、[设置页](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)；模型来源：[本次语义比较回执](../../work/sony-firmware-20261024/stage11-model/official/existing-model-semantic-comparison.json)。`MovieFileFormat` 等列名是研究问题的概念标签，**没有冒充已验证的 Sony API 符号**。

### Inferences

- 当前不能把公开远控路线认定为实现目标的已支持方案。按现有证据，若仍要推进独立 HD29.97 HEVC420 10bit 约 16M MAIN，仍需闭合固件 / 模型适配与真实主片验证；SDK 名单没有消除这些工作。
- 缺少公开数值表只说明本轮尚不能验证映射，不能推出芯片无能力、接口永远无法实现，或批准尝试未支持值。这里不生成猜测 PTP 命令、不建议枚举爆破。

### Gaps

- 仍缺四类接口证据：准确属性键 / 编码，值域与存储类型，FX3 7.02 的属性支持脚注与状态限制，MAIN 和 proxy 的独立属性映射。没有这些证据，不能将固件模型枚举写成 SDK 数值常量。
- 未获得实际机内 MAIN 成片、29.97 帧率、HEVC 10bit 采样、音频、长录和恢复验收；本轮无主动设备操作。
- 来源收据固定本轮页面 URL、抓取时刻、版本、日期、正文哈希及 HTTP 元数据。原始 Sony 网页仅在内存中解析，未保存原始第三方源码 / 安装包；既有固件和历史材料均保留。[来源回执](../../work/sony-firmware-20261024/stage11-model/official/official-source-receipts.json)
