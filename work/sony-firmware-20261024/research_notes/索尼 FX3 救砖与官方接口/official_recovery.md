# 经典 ILME-FX3 7.02：官方更新失败恢复与公开接口边界

核查：2026-10-27（America/Los_Angeles）。范围：公开 Sony 原始资料、只读研究；没有下载或执行固件/驱动，没有访问相机、USB、服务认证或维修商后台。本笔记仅由本研究者维护，不修改总进度或旧报告。写入前已复核目标卷 UUID 为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 且目录可写。

## 1. FX3 7.02 官方怎么更新，哪些黑屏/闪灯属于正常，哪些允许重试？

### Takeaway

Sony 对经典 ILME-FX3 公布的是可工作的机内更新流程，以及指定失败灯序下的卡更新重试；没有把它称为任意损坏状态的救砖。约六分钟黑屏、访问灯按 1→3→5 次反复闪烁，是正常进度，不能仅据此判断变砖。[Sony 中国 7.02 操作页](https://service.sony.com.cn/download/firm/00003048.html)

### Cited Findings

- **适用机型/版本**：美国页明确适用 `ILME-FX3`，最新文件为 `BODYDATA.DAT`、7.02、811,876,768 bytes，发布日期 **2026-03-17**。已是 7.02 的机身无需更新；≤2.02 必须先到 2.04/2.05，再到 7.02。[美国 7.02 下载与操作页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)
- **准备条件**：中国页要求先保全卡内资料、在相机中格式化卡，把对应固件以唯一 `BODYDATA.DAT` 原名放根目录；卡须在 SLOT1。使用充满的 NP-FZ100，至少三格电，避免过热，取下手柄；菜单依次为设置→设置选项→版本→机身→软件更新→执行。[中国 7.02 页，2026-03-17](https://service.sony.com.cn/download/firm/00003048.html)
- **正常结束证据**：自动重启并出现机身更新完成画面后，仍需在版本菜单确认 7.02；不能用“灯停了”替代确认。[美国 7.02 页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)
- **指定失败**：美国页列明两组灯序：5 次长闪（0.5 秒周期）后 6 次短闪（0.25 秒周期），或 7 长后 7 短。可能原因是未先到 2.04+，或固件复制错误。官方步骤是取出电池和卡、换卡，从保存固件到卡的步骤重做；同页列出目标机型不符的报错。[美国 7.02 页，If the Update Fails](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)
- **中文版重试描述**：取出电池，重新下载固件，存入格式化卡；卡插 SLOT1、装电池、开机后再尝试更新。中国页把一个文字提示写为更新文件版本不正确；美/日页对应位置写目标机型不符。因此诊断应记录实际完整提示，不能把两种报错当成同一原因。[中国 7.02 页](https://service.sony.com.cn/download/firm/00003048.html)、[美国 7.02 页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)

### 型号、版本、动作及边界表

| 型号/版本 | 官方动作 | 必要前提/可观察状态 | 限制 |
|---|---|---|---|
| 经典 FX3，2.04+→7.02 | SLOT1 卡更新 | 能到版本菜单执行更新；供电、卡、文件符合要求 | 正常黑屏约六分钟，1→3→5 闪；不是任意故障入口。[中国操作页](https://service.sony.com.cn/download/firm/00003048.html) |
| FX3 卡更新 5长6短/7长7短 | 去电池、换卡、重建更新卡后重试 | 必须先核对旧版本与文件 | 这是特定更新错误处置；不承诺修复改坏的 rootfs/启动区。[美国操作页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561) |
| FX3 ≤2.02 | USB 过渡更新至2.04/2.05 | 供电、MSC、对应电脑程序 | 不是7.02的强制USB重装；无须再跑3.00程序。[中国过渡页](https://service.sony.com.cn/content/casch/download/firm/00002966.html) |
| FX3/FX30 卡更新失败 | 换机内格式化卡，装电池开机 | 每秒1闪表示已续行 | 仍不改善，官方要求维修。[卡更新FAQ](https://support.sony.jp/electronics/support/articles/00282342) |
| 专业摄像机的电脑USB更新分支 | 15分钟无响应后断USB、取电池数分钟、重启电脑、MSC重试 | 原流程必须是电脑USB更新 | 不能把15分钟阈值或拔线动作套到7.02卡更新。[专业机失败FAQ](https://support.sony.jp/electronics/support/articles/00405391) |
| Creators' App支持相机 | 手机下载→传到机内卡→相机执行 | 正常连接、卡、电池、账号；最新时不显示更新按钮 | 手机是传送入口，最终仍机内卡更新。[官方App帮助](https://helpguide.sony.net/di-app/ca/v1/en/contents/CA_update_software.html) |

### Inferences

- 从机内菜单启动、文件版本检查、特定错误后续行这些证据，只能推导出**官方更新器在部分失败状态仍可能工作**。不能推导出“改坏主应用后插7.02卡必救”或“USB可见必能刷回”。[美国7.02页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)、[卡更新FAQ](https://support.sony.jp/electronics/support/articles/00282342)

### Gaps

- 官方7.02页没有公开完整错误码表，也没有给出无灯、完全无USB、无菜单、启动区或文件系统损坏时的强制更新按键/电气入口。本次未找到经典FX3 7.02经修改固件失败后由官方流程恢复的认证案例。
- 表中“限制”里关于rootfs/启动区的措辞是证据覆盖范围判断，不是Sony宣告这些故障一定不可修复。

## 2. 官方失败FAQ、旧USB更新器和公开软件接口，究竟能覆盖什么？

### Takeaway

官方资料把电脑USB更新与存储卡更新分开。卡更新FAQ明确拒绝同版/旧版文件，并在指定换卡重试无效时要求维修；这与公开“强制重装任意固件”不同。[卡更新FAQ](https://support.sony.jp/electronics/support/articles/00282342)

### Cited Findings

- **官方链路及日期**：日本7.02页末尾指向旧地址 `https://www.sony.jp/support/pro-cam/update/fail.html`；该地址现为迁移页，转到文书 **00405391**，标题为专业摄像机本体更新失败处理，最后更新 **2026-06-25**。该文卡更新分支明确写FX3/FX30使用槽1，并进一步链接文书00282342。[日本7.02页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)、[迁移入口](https://www.sony.jp/support/pro-cam/update/fail.html)、[00405391](https://support.sony.jp/electronics/support/articles/00405391)
- **USB失败处置的适用前提**：00405391中，黑屏且15分钟以上无响应后的拔USB、取电池等待数分钟、重启电脑、开机设MSC、重跑下载程序，全部位于电脑USB更新标题之下；问题仍存在则联系Sony专业产品咨询。美国通用文书URL00199250（页面显示Article ID00199711、最后修改2026-01-19）也给出同样USB步骤，并提醒仅适用于指定产品/系统。[日文专业机FAQ](https://support.sony.jp/electronics/support/articles/00405391)、[美文通用FAQ](https://www.sony.com/electronics/support/articles/00199250)
- **卡更新续行与送修门槛**：00282342最后更新 **2026-06-10**。对于5长6短，先排除FX3≤2.02未经过渡更新；其余该灯序及7长7短，换机内格式化卡、重存正确文件、重新供电后，每秒1闪代表更新续行，等其完成；无改善就需维修。短原文：**改善しない場合は修理が必要です。** [Sony卡更新FAQ](https://support.sony.jp/electronics/support/articles/00282342)
- **明确版本限制**：同一FAQ把同版或旧版DAT列为版本不正确的原因。故7.02卡能作官方版本材料，不等于Sony公开允许在7.02上同版重装或降级。[Sony卡更新FAQ](https://support.sony.jp/electronics/support/articles/00282342)
- **旧USB工具仍有正规用途**：中国过渡页发布日期 **2023-09-12**，限定≤2.02，`01_Update_ILMEFX3V20x.exe/.app`自动选择2.04/2.05；须先设MSC、取出存储卡。页面告诉用户过渡完成后直接去最新卡更新，**不需要**运行`02_Update_ILMEFX3V300`。英国3.00 Mac页（发布日期 **2023-04-12**）也明确当前已2.04/2.05就跳去7.02。[中国过渡更新页](https://service.sony.com.cn/content/casch/download/firm/00002966.html)、[英国3.00 Mac页](https://www.sony.co.uk/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280266)
- **Creators' App不是另一层救援系统**：帮助文说明先把更新文件下载到手机，再传到相机卡，最后相机执行；可在文件传完、执行前暂停，再从版本菜单继续。当前已最新时不显示更新按钮，执行后长短闪交替则要求初始化卡后重试。[Creators' App更新帮助，访问2026-10-27](https://helpguide.sony.net/di-app/ca/v1/en/contents/CA_update_software.html)
- **有官方SDK，但要逐功能看机型**：Camera Remote SDK公开支持FX3（2.00+），用于设置、快门、实时取景等控制。首页2024-10-16通知虽有Remote Firmware Update，但对应脚注*5仅列 **ILX-LR1**；同段FX3对应的是其他控制/预览功能。首页最新SDK为2.02.00、发布日期2026-06-10，本页未公布FX3的救砖功能。[SDK官方首页](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)
- **官方确承认过历史更新问题**：日本7.02页历史记录说6.00于2024-09-13停发、采取措施后2024-10-09恢复，已经成功升级且可开机的机身可继续用；6.02（2025-02-18）修复从带用户LUT的6.00升级6.01后不能应用LUT/录像/操作的问题；2.02（2023-01-11）修复2.01更新后不正常工作。它们证明存在官方更新故障，不证明底层恢复方法。[日本7.02历史记录](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243)

### Inferences

- **官方可证的恢复边界**：旧USB程序须匹配机型、旧版本、MSC与电脑要求；7.02以卡/App更新。不能把旧USB工具、普通MSC驱动或SDK“支持FX3”视为已验证的FX3 7.02强制重刷通道。[过渡页](https://service.sony.com.cn/content/casch/download/firm/00002966.html)、[7.02页](https://service.sony.com.cn/download/firm/00003048.html)、[SDK页](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)
- **修改固件后恢复是另一个问题**：上述Sony流程没有描述用户修改的文件/内核/启动区、服务认证、重建校准或恢复同机备份；因此不应把“官方更新失败后重试”写成“第三方改机后可恢复”。这是来源覆盖不足的判断。

### Gaps

- 定向查询Sony公开站点的FX3 recovery software、emergency firmware、リカバリー及中文恢复固件，没有找到独立FX3恢复/重装应用、公开DFU/BootROM/强制刷写规范或7.02同版重装开关。结论只限**本次未发现公开支持**，不是“Sony内部不存在”。
- 尚未审阅SDK全量最新API参考和机型功能矩阵；只能确认首页2024远程更新功能的适用脚注，不能绝对声称之后每个SDK版本都无任何FX3固件命令。
- 本轮不访问需认证的维修站/服务软件，不把第三方转载Service Manual当成Sony向普通用户正式提供的软件接口。
- 美国通用“Errors during a firmware update…”检索能找到送修导向，但网页抓取未成功；没有用它证明经典FX37.02操作。

## 3. 官方维修/支持怎么走，公开资料是否给出维修工位软件？

### Takeaway

公开官方路径是按症状重试、仍失败则由Sony或授权维修站检查；现有公开页面能确认咨询、报修和软件升级服务，不能确认维修工位实际使用何种刷写接口、密钥或载荷。[卡更新FAQ](https://support.sony.jp/electronics/support/articles/00282342)、[中国官方服务政策](https://www.sony.com.cn/content/casch/serviceinfo/servicepolicy.html)

### Cited Findings

- **中国大陆**：官方FX3支持页直接提供7.02说明、过渡更新说明及服务网络入口。服务网络按产品类别、地区/城市定位特约维修站；应让服务方确认承接经典ILME-FX3和对应购买地区。[FX3产品支持页](https://service.sony.com.cn/products/di/ILME-FX3.html)、[维修网络](https://service.sony.com.cn/service_station/index.htm)、[如何找维修站，最后修改2025-03-11](https://www.sony.com/zh-cn/electronics/support/articles/00188708?showHeaderFooter=false)
- **官方联系方式（只读取，未联系）**：中国顾客服务 **400 810 9000**；专业系统产品服务 **400 810 2208**，联系页均标注周一至周日9:00–18:00。咨询时应先报经典ILME-FX3、当前7.02、更新渠道、故障发生阶段、灯序及是否曾修改固件。[Sony中国联系我们，访问2026-10-27](https://service.sony.com.cn/content/casch/contact-us.html)
- **服务范围有软件升级，具体故障仍需检查**：中国政策列专业ILME-*维修项目、一级修理可含软件/固件升级，也列ILME系列保养中的软件升级；正常总费用按维修和零件形成，须预先报价并取得同意。不能据此预判只收软件费、必然更换主板或必然免费。[中国官方服务政策/收费标准，收费表标注更新2025-08](https://www.sony.com.cn/content/casch/serviceinfo/servicepolicy.html)
- **其他地区入口**：美国7.02页直接给Product Repair和Contact Support；日本00405391给专业产品电话咨询，00282342给经销商或维修申请。用户所在地、购买地区和保修条件需要由官方确认，不能把大陆条款套到海外机。[美国7.02页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)、[日本专业咨询](https://www.sony.jp/professional/support/inquiry_b2b.html)、[日本维修](https://www.sony.jp/support/repair.html)
- **公开手册的边界**：Sony亚太FX3产品页的Manuals区列用户Help Guide、Creators' App Help Guide和Startup Guide；本次该公开列表未列Service Manual、工位认证器或板级恢复软件。这里仅报告该列表内容，不宣称Sony从不向任何维修渠道提供维修资料。[Sony亚太经典FX3支持页，访问2026-10-27](https://www.sony-asia.com/electronics/support/interchangeable-lens-camcorders-ilme-series/ilme-fx3)

### Inferences

- 可向官方要求的具体判断是：失败处于哪层、能否按其工位流程重装现有主板、是否需要换板/校准、数据和设置如何处理、报价及保修依据。**询问这些项目不表示已证实工位支持某种接口。**
- 本研究只核实公开操作与支持入口；官方维修成功、第三方工具服务模式成功、用户机身真实恢复，是三个独立证据层级。

### Gaps

- 公开Sony页面未说明经典FX3维修工位的程序名、版本、认证硬件、传输命令或救援载荷；未公开承诺修复任意第三方修改、保留所有用户数据/校准或无条件保修。
- 未联系Sony、未提交序列号/维修申请、未登录维修渠道，也未做任何恢复测试；本笔记不能充当用户当前机身的恢复验收。

### 抓取与复核说明

- 所有来源访问日均为2026-10-27；上文分别标出官方页的固件发布日期或FAQ最后更新日。未显示发布日期的产品/联系/SDK帮助页只标访问日。
- `support.sony.jp`部分页面经Web抓取超时，但以公开HTTP读取并剔除脚本后复核了页面正文、文书号、最后更新日及公开链接；旧fail.html的迁移目标也直接读取确认。没有把搜索摘要作为唯一依据。
- 未将FX3A、FX30、A7S III或Infineon/Cypress EZ-USB FX3的恢复方法移植为经典FX3 7.02事实；FX30仅在Sony自身FAQ的共用分支中出现。
