# FX5 系统移植到经典 FX3：公开资料与源码核查

核查日期：2026-10-27。目标机身仍为经典 ILME-FX3、用户确认的 7.02；FX3A、FX5B 和其他机型不混用。用户本轮提出研究 FX5 最新系统能否刷到 FX3，并确认“没有，按公开资料继续”。原 1080p、30000/1001、HEVC420 10bit 约16Mbps主录及实机恢复目标保持。

**当前不具备安全直接互刷的条件。已经取得并静态拆读 FX5 官方 GPL 组件，但尚未取得完整 FX5 机身更新包，因此没有完成 FX5 系统镜像解包，也没有建立兼容刷写方案。** 源码显示需要跨板级平台适配；当前 FX5 官方录制表也没有现成的目标 HEVC 主录模式。

## 可取得的材料与版本边界

- [日本官方支持页](https://support.sony.jp/electronics/support/products/ilme-fx5)当前明确显示没有提供更新信息。已保存 HTTP 200 原始页面和去标记文本；页面没有给出可核验的最新机身固件版本。
- [美国下载页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)、[新加坡下载页](https://www.sony.com.sg/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)经网页检索工具读取，只列应用软件，未找到机身更新包。本地匿名 HTTP 抓取被返回403；403本身不作为“没有固件”的证据。
- [中国商城产品页](https://www.sonystyle.com.cn/products/professional-video-cameras/ilme_fx5/ilme_fx5_feature.html)有通用“固件下载”图标，本次未从该页取得 FX5 专属 DAT 链接。它不证明所有地区、维修渠道或非公开版本都不存在。
- [FX5 官方开源页](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)提供源代码组件。按其[下载说明](https://oss.sony.net/Products/Linux/notice.html)下载了 `linux-kernel`、`cemmc-init`、`cryptoram`、`ldec`、`sio` 五包；完整长度和服务器 Content-MD5 校验通过，并记录本地 SHA256。包所在的 `20260731_ILME-FX5` 路径不能当作机身固件版本。
- [官方发布说明](https://www.sony.jp/CorporateCruise/Press/202607/26-0722B/)中的 2.0 是2027年计划，不能当作当前已经取得的系统。手册的 `Vx.xx` 也是版本显示占位符。[Maintenance 手册](https://helpguide.sony.net/ilc/2630/v1/en/contents/maintenance.html)

抓取、错误与链接回执分别见 `public-source-captures.json`、`public-guide-captures.json`、`public-oss-captures.json`、`fx5-gpl-download-receipt.json`。未提交表单、凭据或产品序列号。

## 已拆读到的真实代码差异

这张表比较的是官方型号关联的公开源码，**不是两台实机当前选中配置的测量**。FX3参考包来自先前已校验的[Ver.7.00 GPL 页面](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)，不能替代用户7.02的实机程序指纹。

| 项目 | FX3参考源码 | FX5公开源码 | 意义 |
|---|---|---|---|
| 内核 Makefile | Linux 4.9.337 | Linux 5.15.179 | 内核/驱动不能按同一二进制接口处理 |
| Sony板级文件 | CXD90057 | CXD90201/CXD90XXX相关文件 | 需要型号专用启动、内存和外设适配 |
| 所查设备树CPU描述 | Cortex-A35／ARMv8 | Cortex-A53／ARMv8 | 二者包含ARM64，不能把代际不同误称为指令集必然不同 |
| 中断控制器描述 | GIC-400 | GICv3 | 板级初始化依赖不同 |
| 所查示例配置 | TEE未启用 | TEE／OP-TEE启用 | 这些是公开配置，不证明机身当前选中哪份配置 |
| 存储初始化组件 | 本轮未从FX3包作对应功能排除 | `cemmc-init`调用OP-TEE会话与初始化命令 | 不是已取得的救援工具、存储密钥或跨机身解密能力 |

FX5内核包中有31个名称含CXD90201的路径，名称含CXD90057的路径为0；这一目录事实不等于已经读出了FX5实机芯片型号。`cemmc-init`实际包含 `tee_client_open_context/open_session/invoke_func`、初始化和密钥设置参数处理；未调用这些函数，也未读取任何机身密钥。实际DTB、RAM容量、启动认证、TEE固件、存储加密布局和专有摄像机HAL仍未取得。逐条文件SHA与行号见[代码证据](code-portability-review.json)。

官方产品资料另外确认FX5采用新堆栈式传感器和BIONZ XR2；经典FX3为Exmor R平台。屏幕、电池、接口和音频配件也有差别。这些差别意味着需要独立的驱动和资源适配，不能通过改文件名或跳过型号检查来完成整机移植。[FX5规格](https://www.sony.jp/pro-cam/products/ILME-FX5/spec.html)、[经典FX3规格](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html)

## FX5是否已经具备原目标模式

已从官方HTML按 `rowspan/colspan` 展开全部52行XAVC主录组合，保留29.97和HEVC正向对照。结果见[录制表复核](fx5-recording-table-review.json)。

| 官方列出的组合 | 格式 | 与原目标的关系 |
|---|---|---|
| 29.97、1920×1080P，50/16/16Mbps | XAVC S-L 420，H.264 | 不是目标HEVC |
| 59.94、3840×2160P，150/75/45Mbps | XAVC HS-L 420，HEVC | 是4K、不同帧率 |
| HEVC 1920P 16M | Proxy Rec | 是代理，不当作MAIN |

当前公开表中，HEVC主录有10行，1080行和29.97行均为0。因此“换FX5系统就能获得1080p29.97 HEVC主录”没有现成功能依据。这个结论只覆盖已发布手册，不排除隐藏功能、将来的固件或尚未证明的硬件能力；不将表格缺项解释为硬件绝对不能编码。[主录组合原表](https://helpguide.sony.net/ilc/2630/v1/en/contents/video_quality_setting.html)、[代理设置](https://helpguide.sony.net/ilc/2630/v1/en/contents/project.html)

## 整包互刷与单项移植分别缺什么

- **整套系统**：缺完整FX5更新包、包头/型号/签名/分区证据、实际启动/TEE/驱动/专有应用依赖，以及FX3同机备份和独立恢复。没有可安全刷入文件。
- **BIG6与菜单**：可以继续研究布局和交互，实际移植仍需FX5应用/资源、显示与输入适配、内部控制接口和状态语义；画出相似界面不等于FX5系统已运行。
- **Open Gate、5K、Dual Gain、AI与音频新功能**：分别依赖传感器、处理器或音频硬件。FX3不能通过系统名称获得FX5硬件；内部X-OCN编码是否可独立移植仍缺编码实现、HAL、资源和吞吐证据，不能预先许诺。
- **原1080p29.97 HEVC MAIN目标**：保留FX3原系统内的受限功能研究。FX5当前表格没有提供可以直接搬来的目标配置；本轮没有用代理或外部转码替代主录目标。

后续若出现来源可核验的完整FX5包，先做离线识别、型号/版本/摘要固定，再审查外层格式和解包支持；取得实际boot、DTB、ELF、应用资源与HAL后再评估移植边界。现有FX3解包器不能未经验证就用于新平台，更不能据此生成可刷承诺。当前可继续推进FX3自身备份入口与受限恢复器审查。

本轮只执行公开HTTP下载、本地归档读取、源码/表格解析与证据登记。没有执行下载的Sony代码、构建/加载驱动、创建模拟器，亦没有设备命令、Windows/UU操作、认证、机身文件、RAM模块或持久写入。原16项验收状态保持；完整目标仍未完成，刷写未放行。
