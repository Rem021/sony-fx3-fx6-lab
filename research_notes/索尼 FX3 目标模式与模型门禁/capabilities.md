# FX3 主录格式、菜单枚举与外部格式门禁

## 1. 固件是否已有一组可直接选择的 HD HEVC 29.97 / 16M / 4:2:0 10bit 主录定义？

### Takeaway
固定的 FX3 7.02 原件中，主录格式枚举没有 HS HD，HS4K 的三个普通录像质量名字表也没有 16M 4:2:0 10bit。HS4K 帧率名字表虽然含 30P / 25P，真实 typed builder 会拒绝这两项；名字存在不能作为可选择模式证明。[原件表和字节](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[相邻研究的真实 builder 分支与受限执行](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Cited Findings
- 原始 `appFw.so` 为 79,015,712 字节，SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；本文所有 VA 均为该模块的相对虚拟地址，不是机身运行地址。脚本强制核对原件哈希，静态读取，不运行固件。[自写复现脚本](../../work/sony-firmware-20261024/stage11-model/capabilities/probe_capabilities.py)
- `setting_file_format` 的14项名字表位于 `0x411f108`：5=HS8K、6=HS4K、7=S4K、8=S HD、9=SI4K、10=SI HD、11=SI DCI4K、12=INVALID、13=ALL；没有 HS HD 主录项。该表只证明枚举命名边界，不代表所有产品都开放其中所有项。[`tables.format`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- HS4K 帧率名字表 `0x411f390`：0=60P、1=50P、2=30P、3=25P、4=24P、5=120P、6=100P、7=24.00P、8=INVALID、9=ALL。真正修改录像帧率的分发器 `0x27c79c4` 按格式5..11选择 getter pair；format6 走 `0x27c7aa4`，使用 `0x2934d14/0x2934d28` 并显式绑定 model key `0x39c`。这建立了主录 HS4K 帧率家族的独立调用证据。[`tables.hs4k_frame`、`snippets.frame_change_dispatch`、`snippets.hs4k_frame_setter`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- HS4K 的60/50、24、120/100三个质量名字表分别从 `0x4138aa0 / 0x4138ba0 / 0x4138ca0` 开始，各32项。其共同枚举29是 `16M_420_8BIT`，30=INVALID、31=ALL；没有 `16M_420_10BIT`。这些是广于实际允许组合的通用名字表，不可把32项全当开放菜单项。[`tables.hs4k_quality_*`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- 相邻 builder 研究使用真实 getter 和分支，HS4K 允许帧率值0/1/4/5/6输出 model frame20/18/10/22/21；经真实 setter 和 libmpr 帧率转换分别为60000/1001、50/1、24000/1001、120000/1001、100/1，没有29.97别名。2/3进入断言路径；全部是合成模型的受限客体执行，不能称相机菜单实测。[帧率逐例和 rational 映射](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)
- Sony 当前“Ver.2 or later”录制表列出 HS4K 的59.94/50、23.98、119.88/100及4K尺寸，HD16M一项是4:2:0 8bit；代理页单独列出 HS HD 的1920×1080 HEVC 16M/9M 4:2:0 10bit。两页于2026-10-25重新读取；帮助指南不是7.02每条内部路径的执行证明。[Sony Movie Settings](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)、[Sony Proxy Settings](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)

### Inferences
- 目标组合至少缺少普通主录的帧率选择定义、16M42010质量定义和HD HEVC模式身份；修改底层码率或解除一个查询断言不能补齐这些层。[枚举、分发器与builder证据](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[builder逐例](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Gaps
- 没有闭合全部产品能力/菜单启用条件表，未证明哪个完整模型初始状态会开放或隐藏每个菜单项。stage2早期feature matrix只有部分getter，不能当完整能力矩阵。
- flat PRM 名字表与 typed model key 不同序列，不能靠两个名字指针之差推 key。本文 key39c 来自真实分发器的显式立即数。

## 2. 外部枚举 XAVC_HEVC_HD 能否直接代表现成的主录 HD HEVC？

### Takeaway
原件确有 `extern_menu_mov_file_format_t` 的 HD HEVC 值14，并且远程事件输出表能把14映射为113；这只证明外部模型及事件有该表示。尚未建立值14能转换成可选择的普通主录 `setting_file_format_t`，不能把它当隐藏主录开关。[外部表、注册与远程事件mapper](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)

### Cited Findings
- 外部名字记录表从 `0x41a6a48` 起，16字节一项，共21项；每项有u32值、u32字符串长度及指针。`0x41a6b28` 是值14，名字指针 `0x41a6b30→0x3c119da` 为 `EXTERN_VAL_MENU_MOV_FILE_FORMAT_XAVC_HEVC_HD`；下一项值15是HEVC4K，16/17/18/19是XAVCS L HD/I HD/L4K/I4K，20是HS8K。[`tables.external_movie_format`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- `0x16cee28..0x16cee58` 先注册类型名字 `N5model29extern_menu_mov_file_format_tE`，随后将 `0x41a6a48` 交给枚举注册helper `0x1697fa4`。它与主录名字表是不同的表和类型。[`snippets.external_enum_registration`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- 远程事件块 `0x2e9b898..0x2e9b97c` 通过属性读取/允许值检查helper `0x2e91e94` 后，在 `0x3997e68` 的9项表查找输入字节；14→113、15→114、20→115。找不到值会进入带 `to_remote_event_file_format_movie` 名字的错误通知分支；代码没有在此调用普通主录setter。[`snippets.remote_event_file_format`、`remote_event_file_format_map`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)

### Inferences
- 外部协议/元数据命名空间比当前普通主录枚举更宽。外部14的存在值得保留为后续映射入口，但目前证据支持“有表示”，不支持“可设置并录制”。[两个类型的表与mapper](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)

### Gaps
- 未找到外部14到 `setting_file_format_t` 的逆向转换、产品开放条件或整套输入接受路径；也没有验证相机当前属性返回值或外部命令行为。

## 3. 一个最小且语义一致的候选必须同时覆盖哪些消费者？

### Takeaway
当前只能形成“目标模式定义和必需消费者”的候选约束，不能给出已闭合的最小补丁。候选必须有独立可选身份，把MAIN / HD / HEVC / 42010 / 16M / 30000/1001作为同一个模式贯穿模型、菜单、查询和真实setter。[本轮固定表与消费者](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[主录真实setter旧证据](../../work/sony-firmware-20261024/stage10-mainpath/main/actual-main-setter-static.json)

### Cited Findings
- 与MPR setter不同，`model::convert_movie_file_format` 的真实函数在 `0x2a50354`。其 `0x37fa3b8` 跳表对format5..11的固定结果分别为movie_format6/5/2/1/4/3/7；format6不查看所选录像帧率或质量就直接返回5。即使只改低层VPC，模型的派生格式分类仍沿原来的格式6路径。这一消费者也必须纳入一致性检查；本轮未独立给movie_format数值5命名。[`main_to_derived_movie_format`、`snippets.movie_format_derived_classification`](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- 旧阶段已确认查询helper `0x2e68048` 与真实普通主录setter `0x2e6e5d8` 不同；一次查询跳表改动不会改变后者的输入构建、派生格式或菜单选择。旧阶段单条HS420常数替换会波及其他帧率，不能作为目标模式实现。[实际setter和调用证据](../../work/sony-firmware-20261024/stage10-mainpath/main/main-path-summary.json)、[旧受限setter转换测试](../../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json)
- 旧阶段synthetic控制的 `frame13` 文字标签曾写为59.94；相邻本轮真实rational复核显示它是25/1。本说明采用本轮rational，不沿用旧控制标签。[本轮真实帧率复核](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Inferences
- 语义上最小的候选是一个显式、精确的目标模式身份：仅普通movie、MAIN stream0、1920×1080、HEVC Long GOP、42010、标称16M、30000/1001；代理/S&Q/UHD/其它帧率均各保留既有模式身份。该身份可采用新增主录枚举或独立分辨率/编码维度，但还不能选定哪种代码改动更小，因为完整消费者表未闭合。[已证明的主录与外部枚举边界](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- 必需的改动范围依次是：产品允许组合/菜单选择提供目标；typed model有对应帧率和16M42010质量；builder构成精确目标参数；派生格式分类识别目标HD；查询/剩余时间mapper与真实setter都映射同一目标；文件/编码路由保持MAIN语义。仅把现有format6改称HS HD、仅暴露已有30P标签、或复用外部14，均没有满足这组约束的证据。[本轮表和消费者](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[builder分支](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)
- 可进一步缩小研究为“已有HS4K的30P未开放tuple能否承载独立HD目标”，但这仍须显式处理格式名字、派生分类和全部消费者；本轮不把这个tuple认作可用候选，也不产出机器可执行补丁。[帧率命名与派生格式固定路由](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)

### Gaps
- 未穷举显示、菜单重入、模式恢复、外部控制、媒体/录制时长估算、文件命名、播放及下游所有消费者，无法声称已经确定字节数意义的“最小改动”。
- 本轮只有静态读取，没有guest固件执行、USB、GUI、认证、相机文件访问、驱动/模块/WBI操作或相机写入。相邻builder的受限guest证据也没有硬件Open/Start、真实码流、长录、冷启动或同机恢复验收。
