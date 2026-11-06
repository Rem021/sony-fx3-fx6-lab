# FX3 定点身份的 selector 与派生消费者

## 1. external HEVC HD 14、remote 113 能否反向进入主录 setting399？

### Takeaway
本轮找到两张同时含 113、14 的真实格式描述符表，并闭合它们的允许值列表/当前值构造调用；它们仍是输出描述符消费者，不是反向输入 mapper。external14→setting_file_format/key399 的接受、转换与事件写入链仍未建立，不能把 113 当作属性 ID，不能把14写作主录选择值。[描述符表和代码](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)

### Cited Findings
- 基准为官方 FX3 7.02 解出原件 `stage2/extraction/files/nflasha15/lib/appFw.so`，79,015,712字节，SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。所有 VA 是模块相对地址。仅静态读取；写入项是本任务研究工件。使用既有 pinned venv，无安装、虚拟机、固件原生或客体执行，无相机/USB/UI/认证/机内文件/driver/module/WBI操作。[复现脚本](../../work/sony-firmware-20261024/stage12-prototype/consumers/probe_selector_consumers.py)、[来源及工件回执](../../work/sony-firmware-20261024/stage12-prototype/consumers/source-receipt.json)
- 外部14的原类型是 `extern_menu_mov_file_format_t`；主录 `setting_file_format_t` 的6是HS4K、8是S HD，未有HS HD项。key399是内部typed模型key，与外部枚举14、事件表示113分属不同命名空间。[既有完整类型表](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[实际key399 wrapper](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)
- 新表 `0x3120278` 八行、`0x31202f8` 九行，每行16字节。包含 `[9,30,113,14]`、`[10,30,114,15]`，第二表另有 `[11,30,115,20]`。字段不能仅凭相邻数值命名为输入/输出；实际代码将第三列交给允许值检查，将第四列低字节加入描述符枚举列表。[`descriptor_tables`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)
- 函数 `0x2318720` 在 `0x2318794/0x23187a4` 构造两表地址并复制到栈上，按当前模型条件选8或9项，调用 `0x23184b8`。后者读取行+4的30与行+8的远程表示，经 `0x22e8d7c/0x22e8de8` 过滤，再把行+12低字节填入描述符列表；这不是把外部14转成主录6。[`external_descriptor`、`external_allowlist`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)
- `0x23187f8..0x2318828` 调用 `0x23067c0` 获取当前外部格式，再把构造后的结构交给 `0x170e6d4`。`0x23067c0` 调用 `0x22e8784`，成功时写描述符+8；`0x22e8784` 经 `0x22e4b78`、`0x26fcc24` 和跳表 `0x311f09c`，可返回外部10/11/8/9/14/15/20。方向仍是内部状态→当前外部值，并未出现key399 setter。[`external_current_value`、`external_current_converter`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)
- 原有 `0x2e9b898`、表 `0x3997e68` 的14→113是远程事件输出。新找到的描述符路径补上“外部14还参与支持值和当前值表示”，没有补上输入接受与主录选择。[旧远程事件字节](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[本轮新描述符证据](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)

### Inferences
- 外部14有完整一些的报告/描述能力，不能因此认定 classic FX3 当前产品门禁开放它；逐行通过哪些gate、当前状态能否产生14均未受实机或完整模型验证。[实际gate调用](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)

### Gaps
- 尚缺：远程输入事件解析器、值113/14的入站验证、转成主录setting值的函数、key399写入事件以及由此触发的sequence。此次对原已知外部/派生入口做一次定点静态追踪后停止，没有全UI遍历；“未闭合”不是证明固件绝无此路径。
- 没有产生PTP命令、SDK属性编号或相机操作。不能从描述符头常数或内部key生成可发送报文。

## 2. derived movie_format5 的真实语义和消费者是什么？

### Takeaway
现在可以把5称为“该原件中由主录HS4K产生、被HDMI消费者按4K类处理的派生值”，比单纯沿用字符串标签更强；原始C++枚举token仍未恢复。它不是VPC5，也不是外部15，不能擅自给目标HD HEVC分配已有派生值1。[来源路由](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[实际HDMI消费链](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)

### Cited Findings
- `model::convert_movie_file_format` (`0x2a50354`) 对 setting5..11的固定结果依次是6/5/2/1/4/3/7。主录6不读取HS帧率或质量即返回派生5；主录8返回派生1。所有直接BL/B引用扫描仅发现两处调用 `0x2b6dd54`、`0x2d20f58`，不排除间接函数指针引用。[原始路由表](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[直接调用索引](../../work/sony-firmware-20261024/stage12-prototype/consumers/selector-index.json)
- 第一处把返回值保存w25，在 `0x2b6de28` 存入临时结构+0x10，然后调用wrapper `0x2dd1354`；第二处在 `0x2d210a4` 写相同结构字段后调用同wrapper。wrapper进入 `0x2df7948`，日志原文为 `hdmi_set_definition`。不能把此路径写成编码参数setter。[`derived_*caller_packet`、`hdmi_definition_wrapper`、`hdmi_definition`和`log_strings`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)
- 在相应系统/曝光条件分支，`0x2df79c0` 读取结构+0x10，位掩码 `0xb4` 将派生2/4/5/7分入输出字节2，`0xa` 将派生1/3分入输出字节0，派生6分入输出字节3。结合来源分别为S4K/SI4K/HS4K/DCI4K、S HD/SI HD、HS8K，这是实际HDMI definition消费的分辨率分组证据。[`hdmi_definition`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)、[setting到derived映射](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- 两条调用链还将相同结构送 `0x2dd1294→0x2df6d8c`，日志为 `hdmi_set_resolution`，后者把派生值作为w3送入 `0x2de5594`。此函数还消费独立输出格式w2，并对派生7有DCI专门分支。因此HDMI输出设置有自己的覆盖维度，不能把派生分辨率类直接等同实际编码尺寸。[`hdmi_resolution*`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)

### Inferences
- 若新离线profile仍由setting6承载，而只修改builder/setter的HD HEVC参数，派生仍固定返回5，菜单/HDMI身份没有随之成为HD目标。这是具体身份不一致，不等于已经证明硬件录制失败或HDMI必然输出错误。[固定返回及实际消费者](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)
- 不可全局改6→1：派生1现由S HD产生；该值是否只表示分辨率、是否还有codec敏感消费者尚未完整穷举。目标需要精确条件下的HD语义和独立可识别身份，兼容已有HDMI用户选择。[派生路由与HDMI覆盖条件](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)

### Gaps
- 缺原始movie_format_t枚举定义/token，不能声称源代码名为HEVC_4K或已找到HEVC_HD枚举。现有“HEVC4K派生5”是以实际来源与消费者交叉确认的语义别名。
- 未穷举间接调用、保存/恢复、所有菜单重入与所有派生格式使用点；未证明可以安全复用派生1或新增哪个数值。

## 3. format6 + typed HS frame2 + 固定16M42010 的条件原型还要满足什么？

### Takeaway
这是一个仅供离线原型验证的条件身份，不是已有相机可选模式。即使相邻原型让builder和真正setter产生MAIN HD HEVC目标，查询helper、派生HDMI分类、菜单允许项/质量显示及恢复身份仍必须同步闭合。[条件契约](../../work/sony-firmware-20261024/stage12-prototype/consumers/consistency-contract.json)

### Cited Findings
- 查询/剩余时间转换helper `0x2e68048` 的原始签名是 `convert2MovieMainParams(...)`，接受typed格式、各格式帧率/质量、S&Q/代理状态，输出VPC、FrameRate、VQuality。直接调用点为 `0x2e6a1f0/0x2e6a8f8`；与实际普通主录setter `0x2e6e5d8` 是两个函数。[签名及调用点](../../work/sony-firmware-20261024/stage12-prototype/consumers/selector-index.json)、[旧真实setter](../../work/sony-firmware-20261024/stage10-mainpath/main/actual-main-setter-static.json)
- 普通movie路由在 `0x2e68fcc` 通过表 `0x398958c` 分派，format6进入 `0x2e69198`，再次通过 `0x39895ac` 按typed HS帧率选择。frame2仍进错误/断言区，不会因为builder新增该frame就自动返回目标查询参数。表的每个frame分派目标随原件字节保存在本轮proof中。[`ordinary_query_format6`、`ordinary_query_hs4k_frame_dispatch`、`ordinary_query_format6_entry`](../../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)
- 已有菜单表把format6命名HS4K，把HS帧率2命名30P，质量三家表没有16M42010；内部key399/39c/3a4/3a5/3a6各属于typed字段，不是SDK/PTP属性编号。[既有表与dispatcher](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[typed key证据](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)

### Inferences
- 精确契约：仅ordinary movie、MAIN stream0、format6+typed frame2且显式profile标记满足时，builder必须输出model frame15/format6/目标quality/color；查询与真实setter均必须解析成VPC6/FrameRate3/VQuality6和1920×1080 HEVC42010、16M、30000/1001。任一既有UHD、其它帧率、S&Q或代理不得被该predicate截获。[契约工件](../../work/sony-firmware-20261024/stage12-prototype/consumers/consistency-contract.json)
- 在该profile里若质量被固定16M42010，旧质量菜单不能继续宣称可选的60M/100M/200M等已生效；需要目标专属固定显示/锁定或等效真实typed质量身份。仅改变标签不能满足typed模型、查询、setter一致性。[既有质量表](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[条件契约](../../work/sony-firmware-20261024/stage12-prototype/consumers/consistency-contract.json)
- 派生函数只收格式等五个值，当前参数中不含HS typed frame2或profile标记；要按新条件区分必须传递可识别身份或扩展输入，不能在原函数里凭frame2猜测。[函数签名与代码](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)

### Gaps
- 尚无实际输入selector/菜单产品允许项、保存恢复标记、已验证的query target branch或完整HDMI配置兼容方案。
- 本轮不交付修改后的固件、可发送控制命令、刷写流程或功能发布结论。相邻受限guest原型也不能代替硬件Open/Start、真实码流、长录、冷启动和同机恢复验收。
