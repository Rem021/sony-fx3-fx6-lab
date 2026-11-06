# Sony 官方 FX3 恢复流程与独立救援边界

核查日期：2026-10-29。对象仅为经典 ILME-FX3／7.02；FX3A 的2.02资料不作替代。此次只读取公开资料和既有报告，无相机、USB、Windows／UU、管理员、下载运行或消息提交。既有报告为 `/Volumes/KAFU2T/AI/Projects/Mac/reports/索尼 FX3 救砖与官方接口.md`；本轮重新核对关键官方原文并收紧解释。

## 官方续行是否覆盖 MAIN 无法启动

### Takeaway

Sony 的卡更新失败续行是真实且值得追踪的恢复候选，但官方文本针对已经开始／失败的更新状态；没有找到“冷启动时未选择更新状态、MAIN 已损坏”的经典 FX3 7.02强制入口说明。**不能把没有公开说明解释成入口不存在，也不能把失败续行直接等同于任意刷坏恢复。**

### Cited Findings

- 经典FX3 7.02仍为官方公开版本，发布日期2026-03-17；正常流程从机身版本菜单启动，槽1根目录放 BODYDATA.DAT。页面另列5慢6快／7慢7快失败灯序和重新准备卡、重新装电池上电重试。— [Sony 中国7.02原文](https://service.sony.com.cn/content/casch/download/firm/00003048.html)
- 2026-06-10更新的卡更新FAQ把上述错误分支和重新上电后的每秒1闪分开：后者表示更新正在续行，仍无改善则送修。— [Sony 卡更新FAQ](https://support.sony.jp/electronics/support/compact-cameras-dsc-p-series/articles/00282342)
- 旧FX3电脑更新器页面列出黑屏超过30分钟后的重新连接／重启处理，范围是旧2.04／2.05→3.00过渡软件，不是7.02卡更新通用强刷法。— [Sony 旧Mac更新器](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280268)

### Inferences

- 优先研究官方更新状态的选择机制很合理：从“已经选择更新”到“更新器自行续行”的路径可能不必依赖正常拍摄应用。这个推断来自官方的失败后上电续行现象，尚不证明入口位置／选择标记或能否从未选择状态触发。— [Sony 卡更新FAQ](https://support.sony.jp/electronics/support/compact-cameras-dsc-p-series/articles/00282342)
- 应把场景至少拆成“更新进行中失败后续行”和“平时修改程序导致MAIN启动失败”。同一黑屏症状不证明同一启动状态；官方流程只直接支持前一种指定错误情形。— [Sony FX3 7.02错误处理](https://service.sony.com.cn/content/casch/download/firm/00003048.html)

### Gaps

- 没有找到官方公开的 FX3 7.02按键／USB请求／卡标记，可从未选择更新的故障冷启动进入独立 updater。
- 官方FAQ没有解释续行标记位于何处、是否持久保存、由哪一级启动器消费，或损坏MAIN后如何重新选择它。下一项具体离线工作应追该选择机制，而非再次验证卡文件名或增加主机程序测试。
- 其他研究者已向协调者报告旧版 updater initrd 的独立应用证据；本笔记未独立检查那些原件，不将其作为本人的静态核验结论。

## 同版重装和回旧版究竟被限制在哪里

### Takeaway

正常更新准入确有同版／旧版限制；官方失败续行分支是否采用同一版本判断，公开文本并未交代。研究应分开这两个入口，不能用正常菜单的限制提前否定恢复分支。

### Cited Findings

- Sony卡更新FAQ把同版本或更早版本DAT列为版本错误的原因，并另列错误机型提示。— [Sony FAQ版本错误段](https://support.sony.jp/electronics/support/e-mount-body-nex-5-series/nex-5rl/articles/00282342)
- 旧Windows 3.00更新器仅面向指定过渡版本，并明确当前为3.00时不需更新；目前页面要求2.04以上跳去7.02。它不能据此作为7.02降级工具。— [Sony旧Windows更新器](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00280265)
- Sony专业设备一般FAQ（2025-03-11）说用户不能自行回旧版，确需回退应咨询经销商／专业产品窗口；页面可读，但所列适用型号未取得，不把它写成FX3专用服务承诺。— [Sony S1110278001038](https://support.sony.jp/electronics/support/articles/S1110278001038)

### Inferences

- 保存官方7.02包可提供官方恢复数据来源；它本身没有解决“如何进入恢复更新器、其版本准入是否不同”的问题。离线应分别定位正常版本门与恢复续行版本门，而不只找GUI能否点更新。— [Sony正常操作及错误分支](https://service.sony.com.cn/content/casch/download/firm/00003048.html)
- 经销商咨询是追型号专用工位能力的有效线索，但不能推断Sony必然提供原板重装、降级或某个公开工具。— [Sony专业设备回旧版FAQ](https://support.sony.jp/electronics/support/articles/S1110278001038)

### Gaps

- 同版限制在恢复分支是否存在、如何判断版本，以及失败时是否允许重装当前版本，仍须原始 updater 代码／型号维修资料回答。
- 未联系Sony或经销商；若后续准备咨询，问题应具体到“经典ILME-FX3 7.02主应用不能启动，能否保持原主板、机身校准数据重装原版；是否需外部工位／夹具；是否有受控同版重装流程”。这轮没有替用户发送任何消息。

## 官方软件或维修资料是否已经给出救砖接口

### Takeaway

目前能核实的是官方常规更新与维修资料体系，尚没有得到适用于经典FX3 7.02的公开独立救砖软件。SDK支持FX3不等于逐API支持紧急恢复；下一步宜追恢复选择器和型号维修材料，不应把“有SDK”或“有Windows”当成救援入口。

### Cited Findings

- 当前 Camera Remote SDK 页面列出2.02.00（2026-06-10）、经典FX3及FX3A支持，Windows11 Intel／AMD和macOS条件；但公开“Remote Firmware Update”的1.13发布脚注仅明确ILX-LR1。当前逐API支持需API参考，不能由总表直接推断FX3更新或救砖。— [Sony Camera Remote SDK官方页](https://support.d-imaging.sony.co.jp/app/sdk/en/)
- Sony专业支持总入口明确有技术公告和维修手册订阅，并提供维修与零件入口；公开介绍未给出经典FX3 7.02工位程序、认证条件或早期刷写步骤。— [Sony Professional支持总入口](https://pro.sony/ue_US/support-services/all-support-services)
- 经典FX3中国支持页目前列出的机身更新仍为卡更新；FX3A另有其专用2.02页面和包，不能混用。— [经典FX3支持](https://service.sony.com.cn/products/di/ILME-FX3.html)；[FX3A官方更新](https://support.sony.jp/electronics/support/software/00378859)

### Inferences

- 对现有Mac／Windows，最有价值的下一项离线成果应是：把“正常MAIN触发更新”“已经进入更新后的续行”“MAIN损坏但未进入更新”三个状态的原始调用者／持久标记／版本门列成可检验表，再确定哪些区域的最小修改保留恢复执行路径。依据是官方明确存在两种不同操作流程，第三种公开入口仍缺。— [Sony FX3正常流程](https://service.sony.com.cn/content/casch/download/firm/00003048.html)；[Sony续行FAQ](https://support.sony.jp/electronics/support/compact-cameras-dsc-p-series/articles/00282342)
- 官方维修资料的价值是寻找型号专用维护入口，而非先假定必须全盘镜像或必需换板。对只修改某程序区域的实验，恢复设计应优先证明不依赖该程序的重写入口，并保留它不修改。此为研究设计建议，不是已证明的恢复方案。— [Sony专业资料体系](https://pro.sony/ue_US/support-services/all-support-services)

### Gaps

- 专业订阅详情页本次403，未进入登录／付费区域，也未取得FX3维修手册的逐型号覆盖。
- 未取得SDK最新FX3逐API表；没有文档支持把常规SDK更新当成坏MAIN的独立入口。
- 公开官方资料未解答维修站是否只需软件、是否有机身专用服务模块，或何种故障最终需换板。所有这些保持未知，不写成不存在。

检索记录：Sony日本部分页面的web正文抓取超时，使用同文号的Sony官方搜索全文结果复核；S1110278001038通过直接HTTPS读取全文成功（200），目标型号表仍缺。未引用Infineon/Cypress同名“FX3 SDK／Fail Safe Firmware Update”，那不是Sony ILME-FX3。
