# 锁定 FX3 主录目标缺少的模型定义

核查日期：2026-10-25。**普通 HS4K 的真实 typed builder 合法路径已闭合，其中没有目标输入元组，也没有后续数值别名。** 主录质量名称表比真正允许的选择更宽；外部 HEVC HD 枚举也未接成主录设置入口。目标仍是经典 FX3 7.02 的独立 MAIN：1920×1080、HEVC 4:2:0 10bit、约16Mbps、30000/1001（口语“30”，即29.97fps），精确30.000fps另列。本轮完成的是离线选择证据，没有新增可刷固件或实机录制成功；也不能据此断言所有模式或硬件均无法实现。([本轮 builder 收据](../work/sony-firmware-20261024/stage11-model/builder/source-receipt.json))

## 普通 HS4K 没有现成的目标元组

证据固定于官方7.02提取件，不来自用户机身的程序读回。原件哈希、指令地址、模型单元与每例轨迹均可复核；地址是模块相对虚拟地址。本轮合成模型状态只用于隔离选择逻辑，不能代表当前菜单、持久设置或机身启动后的全局状态。完整模型序列、媒体限制和所有产品分支仍未执行。([原件绑定与范围](../work/sony-firmware-20261024/stage11-model/builder/source-receipt.json))

真实分发器明确绑定格式 key **`0x399`**、HS4K帧率 **`0x39c`**、60/50、24及120/100三组质量 **`0x3a4/0x3a5/0x3a6`**；这些关联来自原指令立即数。以合成 model 单元执行原始 getter、builder及纯转换代码，9例受限 guest、7个帧率和8个质量别名核查均通过预设判据；没有 stubs，构造器未执行，初值显式供给。协调端仅作脚本及收据静态复核，未重跑旧矩阵或本轮九例。允许帧率最终为 **59.94、50、23.976、119.88、100**，标为30/25的 typed 值2/3走断言路径，没有29.97别名。([key证据](../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)、[逐例执行与边界](../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json))

上述key是**内部模型标识**，不是已经核实的Sony SDK属性ID、PTP property code或备份字段地址，也不能据此构造主动查询。九例包含七个帧率值及两个质量负例；负例停在原断言入口，未执行后续日志或终止代码。此时缓冲区残留的构造初值不算输出成功，“断言路径”也不代表真实相机拒绝或崩溃。([合成输入与停止位置](../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json))

必须分开三层数值：**typed quality 2名为400M42010；setter输入 quality 2转换成MPR VQuality 6，后者 bitrate helper 原返回值为16000。** 它们不是同一枚举。负例拒绝 typed 2不能写成“拒绝16M”；真正排除16M别名的是所有允许 builder quality输出，经真实setter及原helper均不到VQ6，原返回值最低30000。这里只保留raw值，不误标为bit/s。此前HD42010/16M参数链仍是独立离线证据。([本轮映射](../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)、[阶段4目标链](../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json))

## 名称与外部表示不能替代主录允许组合

主录格式14项名称表没有HS HD；HS4K三组各32项质量表没有16M42010，typed 29仅标为 **16M4208**，该标签也不证明可选。外部独立类型有HEVC_HD值14，远程事件输出映射14→113，但未找到它反向进入普通主录设置的接受链。**名称表不是产品能力表，外部表示也不是隐藏主录开关。**([固定原件表及调用指令](../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json))

新增消费者 `convert_movie_file_format@0x2a50354` 对format6固定返回movie_format5，不区分帧率与质量；本轮没有另给数值5命名。它与真实MPR setter不同，必须加入格式一致性约束。因此只换VPC、只开放30P标签或只改查询helper，仍不足以定义可用模式。([派生格式与菜单证据](../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[语义候选约束](../work/sony-firmware-20261024/stage11-model/capabilities/candidate-constraints.json))

主录格式、外部枚举与MPR编码参数各有类型和用途；把相同数字跨层复用，会同时跳过格式身份和合法组合检查。已恢复的是一段确定分支的关系，而非所有菜单项的开放条件。候选仍须回答：什么产品和状态允许选择、保存后如何恢复、重新进入菜单时如何显示，以及查询结果如何与真正送入编码器的参数保持一致。([能力与未闭合消费者](../work/sony-firmware-20261024/stage11-model/capabilities/candidate-constraints.json))

## 官方远控支持机型 尚未证实目标属性组合

Sony的SDK及PTP Command当前均为 **2.02.00，2026-06-10发布**，经典FX3与FX3A分别列出；按机型及最新固件条件，7.02具备支持资格。这没有证明具体属性、状态允许值或目标成片。数值property/enum资料位于许可包，本轮未接受条款或下载；缺少这些资料只限制官方接口映射，离线研究仍可继续。([SDK](https://support.d-imaging.sony.co.jp/app/sdk/en/index.html)、[PTP Command](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html)、[FX3 7.02](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00379243))

当前经典FX3公开主录表中的HS仅列4K，上述五种帧率没有29.97；HD16M主录是4208。**1920×1080 HEVC 16/9M 42010列在伴随主片同时录制的代理设置中**，不能代替独立MAIN验收。公开页面未提供SDK绕过菜单组合的证据，也未证明硬件不可能。指南适用“Ver.2 or later”，本轮抓取于10月25日；HTTP修改时间不是编辑发布日期。([主录设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)、[代理设置](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)、[URL与正文摘要回执](../work/sony-firmware-20261024/stage11-model/official/official-source-receipts.json))

## 更正旧控制帧率 继续闭合模式身份

**更正阶段10：旧“HS420 59.94／100M”控制实际输入frame13；它经setter成为MPR Frame2，真实rational为25/1。** 旧报告、notes与收据保留；“全HS420常数替换会波及其他组合”的观察仍成立，59.94标签停止沿用。目标frame15→MPR Frame3→30000/1001已独立复核，仍是29.97而非精确30。([旧报告](<索尼 FX3 主录设置与回复链路.md>)、[旧输入记录](../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json)、[本轮更正映射](../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json))

下一步从key `0x399`的格式定义及产品/menu允许表，闭合目标身份、typed帧率/质量、builder、派生格式、查询/剩余时间、真实setter与MAIN编码路由，并保留其他模式。`candidate-constraints.json`仅是语义约束，**没有可执行补丁或字节改写计划**。本轮有受限CPU guest执行，无相机原生执行、USB/UI、模块/WBI或驱动操作；实机授权仍仅Windows缓存PnP。硬件Open/Start、真实主片与音画同步、长录温度、对应范围恢复及冷启动均未验收，完整16项要求与未完成状态继续保留。([候选约束](../work/sony-firmware-20261024/stage11-model/capabilities/candidate-constraints.json)、[本轮固定进度快照](../work/sony-firmware-20261024/stage11-model/goal-status-after.json))

恢复也必须绑定同机原件和拟改范围：健康检查点、原字节回读、对应故障后的入口及冷启动结果分别验收，官方更新包不能替代。阶段4的参数包、阶段10的转换块及本轮选择执行各证明自己的范围，不能拼成一次实际录制。后续仍有明确离线工作可推进，本轮进度因此记为继续研究，目标不标完成，也不因缺少许可资料而把整个目标标为阻塞。([完整要求及下一步](../work/sony-firmware-20261024/stage11-model/goal-status-after.json))
