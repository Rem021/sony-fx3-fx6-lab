# FX5 公开整机固件包复核

## 当前能否下载可全面解包的 FX5 整机固件

### Takeaway
2026-10-27 重新核查后，未找到来源可核验的 FX5 整机更新包；日本官方明确表示本页暂无更新信息，英国与亚太官方可读取的下载列表仅列配套应用。本轮没有获得整机镜像，因此没有完成 FX5 boot、分区、ELF、专有摄像机应用或传感器 HAL 解包。这个结论覆盖本轮列出的公开页面与检索，不能排除维修渠道、地区限定、尚未收录或私人持有的文件。

### Cited Findings
- 日本官方型号支持页与专门下载页均显示“現在、本ページで提供されているアップデート情報はありません。”本轮匿名 HTTP 实抓支持页为 200，原始 HTML、字节数和 SHA256 已留存。— [日本官方支持页](https://support.sony.jp/electronics/support/products/ilme-fx5)、[日本下载页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)
- 英国下载列表实际包含 Catalyst Prepare Plugin、Catalyst Browse / Catalyst Prepare、RAW Viewer V6.0、Monitor & Control，没有列出机身 System Software 更新。亚太支持页和菲律宾下载页呈现相同四类条目。上述是网页工具可读取正文；本地 UK HTTP 为 403，不能把拒绝访问当作缺少固件的证据。— [英国官方列表](https://www.sony.co.uk/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)、[亚太官方型号页](https://www.sony-asia.com/electronics/support/interchangeable-lens-camcorders-ilme-series/ilme-fx5)、[菲律宾官方列表](https://www.sony.com.ph/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)
- 美国型号下载页本轮网页工具直接打开超时，本地 HTTP 为 403；搜索索引可见的列表只有 RAW Viewer V6.0，索引标注约两个月前抓取，因此美国当前完整列表不当作已直接复核。新加坡直接 HTTP 同为 403，网页工具超时。— [美国官方列表](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)、[新加坡官方列表](https://www.sony.com.sg/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)
- 中国 FX5 商城页“固件下载”按钮的真实 data-href 是通用下载中心，未带 FX5 型号、机身版本或固件文件地址；这不是 FX5 DAT 已发布的证据。商城原始页与通用下载中心本轮 HTTP 均为 200，但本轮没有完成下载中心动态型号查询。— [中国商城页](https://www.sonystyle.com.cn/products/professional-video-cameras/ilme_fx5/ilme_fx5_feature.html)、[按钮实际目标](https://service.sony.com.cn/content/casch/download.html)
- 日本产品页的“本体アップデート情報”也是通用专业摄像机更新目录。目录当前列出 FX6、FX30、FX3A、FX3、FR7、ILX-LR1、FX2，未列 FX5；其中 FX3 等已标记迁往新支持站，故目录缺项只作辅助证据。— [官方更新目录](https://support.d-imaging.sony.co.jp/www/cscs/update/?cat=pvc)
- FX5 日本官方产品页本轮已显示日本预定发售日 2026-11-20；这比同日早先 stage133 的旧记录更新。该日期是日本销售安排，不能推导全球机身或固件不存在。产品页仍将 Ver.2.00 写为 2027 年 8 月以后的计划，中国官方发布文也称 ver.2.0 为未来升级。— [日本官方产品页](https://www.sony.jp/pro-cam/products/ILME-FX5/)、[中国官方新闻](https://pet.sony.com.cn/content/sonyportal/zh-cn/cms/newscenter/product/2026/20260724-1.html)
- 官方 pro.sony 产品入口可被网页工具短暂读取，但后续多次为超时，本地匿名 HTTP 为 403，未成功检查其完整下载区。— [专业产品入口](https://pro.sony/en_GB/products/handheld-camcorders/ilme-fx5)

### Inferences
- 目前无法执行用户要求的“FX5 整机包全面解包”，因为本轮没有取得整机包本身；不能拿 GPL 源码、RAW Viewer 或未来版本公告代替整机镜像。
- 网上包含 FX5 的通用 SteadyShot、Creators' App 更新文章，可能是共用支持内容的型号套壳，不能仅凭文章标题推导 FX5 已有特定版本更新包。

### Gaps
- FX5 当前量产机机身固件版本未取得可核验的官方发行清单，未将 V1.x 或预告 V2.00 当作实际已下载版本。
- 没有登录、发送序列号、提交表单或访问维修专用资料。US/SG/pro.sony 访问限制与中国动态型号查询缺口保留。
- 未获得任何可固定 URL、文件长度、摘要、目标型号与版本的公开整机更新文件；无法识别其外层格式，更不能假定是 FX3 的 BODYDATA.DAT/UFU 格式。

## 已公开材料是否等价于固件以及本轮实际保存了什么

### Takeaway
FX5 官方 OSS 页确有组件源代码，现有五份下载可复用，本轮重新计算 SHA256 全部与原回执一致；这些不是可刷入 FX5 或 FX3 的整机包。本轮增加的是公开页面实抓、访问失败回执和来源复核，没有重复下载、执行 Sony 代码或接触相机。

### Cited Findings
- 官方页面标明 Source Code Distribution Service，Model/Module 为 ILME-FX5，链接包括 Linux、cemmc-init、cryptoram、ldec、sio、GNU/Ubuntu/GStreamer 等组件，属于开源组件分发。— [Sony FX5 OSS](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)、[下载说明](https://oss.sony.net/Products/Linux/notice.html)
- 既有 `stage133-FX5-source-availability-and-portability/fx5-gpl-download-receipt.json` 记录五包共 151,596,639 字节及官方 Content-MD5 校验。本轮 `existing-gpl-hash-recheck.json` 对磁盘五包重新读取并计算 SHA256，全部匹配；没有重新下载五包。— [官方源码分发入口](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)
- 新增证据位于本 notes 目录：`public-http-refresh.json`、`public-http-supplement.json`、`public-pages/` 保存官方原始 HTML/头信息/字节数/摘要；`public-web-search-receipt.json` 保存网页检索范围、可读取的列表和访问缺口；`existing-gpl-hash-recheck.json` 保存五包哈希复核。— [官方日本支持源](https://support.sony.jp/electronics/support/products/ilme-fx5)、[官方源码源](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html)

### Inferences
- 先复用已有 GPL 源码进行跨平台差异审查是可重复的离线路径；若后续出现完整固件，必须单独固定来源、长度、版本、摘要，再识别容器与加密格式。

### Gaps
- GPL 页面不提供专有菜单应用、完整 CMOS/ISP HAL、机内 X-OCN 实现或实际启动分区；不能由其直接生成移植文件。
- 本轮没有任何相机、USB、Windows、UU、服务模式、机身认证、内存模块或持久写入操作。
