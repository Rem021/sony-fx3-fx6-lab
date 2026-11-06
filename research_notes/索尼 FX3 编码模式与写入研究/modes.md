# FX3 7.02 的 HEVC 模式和实际参数路由

核查日：2026-10-24 PDT。用户要 1920×1080、约 30p 的 H.265 独立主录；4K60→4K30只作定位对照。全程只读本机官方固件，不连接相机、不执行固件、不写入设备，也没有向服务上传固件。

## 60p 能编码是否支持继续研究 1080p30 HEVC

### Takeaway
支持，而且本轮找到的正面证据已超过“60p更重所以应当能30p”的推理：实际 FX3 `libmpr.so` 有具体 HEVC+1920×1080 参数映射，真正编码器 Open/Start 命令组装也调用主流/代理 codec 选择器。最小候选是复用既有 HD HEVC 管线与16/9Mbps配置，解决上层选择、主流路由和一致性，不是新增H.265编码器或跨刷整机系统；仍未证明主流能够接受完整组合并实际录像。

### Cited Findings
- 官方原FX3已提供1080 HEVC 4:2:0 10bit、16/9Mbps代理；主录HS4K列60/50/24/120/100，无30/25。两者是不同组合，60可用不能直接推出低帧率主录只差菜单开关。[Sony代理](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)、[官方主录表](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html)
- 从本次同一官方FX3 7.02包提取的 `appFw.so`：79,015,712B，ELF64 AArch64 ET_DYN，SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；`libmpr.so`：3,517,008B，SHA256 `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`。下列地址均是各模块相对VA，不是相机运行地址、刷机偏移或可迁移补丁。[本机路由证据](../../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)、[提取回执](../../work/sony-firmware-20261024/stage2/extraction/late-selected-manifest.json)
- `libmpr::GetVideoParamComb(VideoCodec,VideoResolution,ColorFormat,VideoBitDepth,GopStructure)` 真正函数入口 `0xc9e84`；`0xc9fa8..0xc9fc8` 接受 `(1,2,0,1,0)` 并选择 **VPC6**，`(1,2,1,1,0)` 选择 **VPC8**。独立格式化器将其分别命名为 `VPC_HEVC_1920x1080_420_10BIT_LONG` 和422版本。这是实际输入分支与返回映射，仍不是编码器运行测试。[函数反汇编](../../work/sony-firmware-20261024/stage2/modes/libmpr-codec-mappings.json)、[VPC格式化器](../../work/sony-firmware-20261024/stage2/modes/vpc-enum-name.asm)
- `mpr::g_videoParamComb` 实表位于 libmpr `0x2cb108`。VPC6/8的24字节条目均含 codec=1、分辨率字段 `0x04380780`（低16位1920，高16位1080）、bit-depth enum=1、GOP enum=0；色彩格式分别0/1。该表由 GOT `0x2f9a40` 的 `R_AARCH64_GLOB_DAT` 指向同名动态符号解析，未靠搜索字符串猜地址。[真实表项](../../work/sony-firmware-20261024/stage2/modes/libmpr-codec-table.json)
- `GetCodecInfoForCodec(VideoParamComb,StreamType)` 在 libmpr `0xcd40c`：对于HEVC，StreamType0返回 codec ID15，StreamType1返回18；这段选择器没有另按HD分辨率或fps拒绝。`EnqueueExecEncOpen(MovieRecInfo&)` 在 `0xd6748` 用主流 StreamType0、`0xd6784` 用代理1；Start、Stop、Close也复用同选择器，主VPC来自 `MovieRecInfo+0x1c8`，代理来自 `+0x1f0`。因此存在通向真正编码命令组装的调用关系，不只是调试枚举。[codec选择器](../../work/sony-firmware-20261024/stage2/modes/libmpr-codec-mappings.json)、[实际编码命令调用者](../../work/sony-firmware-20261024/stage2/modes/libmpr-codec-callers.json)
- MP4写入器 `XavcsMovieWriter::ConvertVPCToLevel`（libmpr `0x115e78`）将VPC6/8都派到 `0x115fb4`；已有quality enum6（官方16M代理对应）得到level5，quality26（9M）且FrameRate3（29.97）得到level4。这证明该层已有对应level表示，不代表任意更高码率或4:2:2硬件录像已验收。[writer分派表](../../work/sony-firmware-20261024/stage2/modes/libmpr-writer-vpc-routes.json)、[反汇编](../../work/sony-firmware-20261024/stage2/modes/libmpr-codec-mappings.json)

### Inferences
- 值得先研究“以现有16Mbps、420 10bit、29.97参数建立独立主流”，再讨论更高码率；先做HD主录比把4K60主流简单减半更贴近目标。
- 60p已有HEVC及HD代理使“没有HEVC硬件”的解释不成立。剩余工作仍可能涉及UI/设置合法性、主/代理数据流、编码器profile、缓存和MP4/音频元数据，不能由通量更低跳过它们。

### Gaps
- `GetVideoParamComb` 根本没有fps参数；`GetCodecInfoForCodec`也不是完整参数校验器。它们可表达HD HEVC主流，不等于上游所有条件或编码器微码接受该组合。尚未做硬件运行、样片解码、同步、分段、温度或恢复验收。
- 422类型、共享8K类型的存在不代表FX3支持这些全部功能；8K属于共享应用类型，不得写成FX3具备8K。

## 30p 缺失具体在哪一层

### Takeaway
已证明共享主录参数转换函数里30/25没有有效质量分支，且会进入错误通知；但该非模板函数的直接用途是查询录制状态/剩余时间，不得把它冒充最终编码器拒绝。真正设置路径已定位到具体builder、API和库入口；普通模式的完整model字段到编码配置的转换尚未全还原。

### Cited Findings
- appFw主格式的完整生成枚举数组在 `0x411f108`，0..13含旧兼容格式、HS8K、HS4K、S4K、SHD、SI4K、SIHD、SIDCI4K及invalid/all，**无HS HD主录枚举**。`0x2e68048` 的 `convert2MovieMainParams` 普通分派表 `0x398958c` 对5..11各格式选择处理块。无对应枚举是当前上层映射的缺口，不能证明无法通过专门改造新增路由。[只读复核输出](../../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)、[函数反汇编](../../work/sony-firmware-20261024/stage2/modes/main-params.asm)
- HS4K帧率标签数组在 `0x411f390`；该转换的实际 `ldrb` 跳表在 `0x39895ac`，基址 `0x2e691b8`，目标=基址+4×有符号字节。实际表如下；枚举标签与代码分派均来自本机包。[路由JSON](../../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)

| 输入枚举 | 标签 | 表字节 | 目标VA | 该转换函数中的路线 |
|---|---|---|---|---|
| 0 | 60P | 0x53 | 0x2e69304 | 选择60/50质量配置 |
| 1 | 50P | 0x53 | 0x2e69304 | 选择60/50质量配置 |
| 2 | 30P | 0x0a | 0x2e691e0 | assert/错误通知 |
| 3 | 25P | 0x0a | 0x2e691e0 | assert/错误通知 |
| 4 | 24P | 0x51 | 0x2e692fc | 选择24质量配置 |
| 5 | 120P | 0x00 | 0x2e691b8 | 选择120/100质量配置 |
| 6 | 100P | 0x00 | 0x2e691b8 | 选择120/100质量配置 |

- 独立的FrameRate格式化器 `0x2e54138`、跳表 `0x3989288` 将低层值3命名为 `FRAME_RATE_29_97P`、7为 `FRAME_RATE_59_94P`，因此不能把菜单30P当精确30.000。错误路线打印 `assert at %s:%d`、调用usleep后进入 `0x2ebf3b0`；其字符串标识 `lib::assert::notify_model_system_error()`，首次通知分支调用动态导入 `__assert_fail`，并非普通菜单灰显。受全局通知状态影响，不能声称任何一次走到此处都已实测崩溃。[独立帧率格式化](../../work/sony-firmware-20261024/stage2/modes/frame-rate-format.asm)、[错误例程](../../work/sony-firmware-20261024/stage2/modes/error-callee.asm)、[PLT符号解析](../../work/sony-firmware-20261024/stage2/modes/error-import-resolution.json)
- 以上转换仅有两个直接调用点 `0x2e6a1f0` / `0x2e6a8f8`，其下游分别为 `mpr::GetMovieRecStatus` / `mpr::GetMovieRemain`。这是必须同步处理的一致性限制，不是已证实“真正编码器拒绝30p”。[调用反汇编](../../work/sony-firmware-20261024/stage2/modes/main-params-callers.asm)、[下游导入名](../../work/sony-firmware-20261024/stage2/modes/mpr-import-resolution.json)
- 真正设置导入 `mpr::SetMovieRecParam` 在appFw PLT `0x15944f0`，调用点 `0x2e6f7bc` / `0x2e6f9b0`；实际libmpr定义位于 `0xf0ff0`。`sequence_set_movie_format` 的builder方法由诊断类型名标识在 `0x2bdf414`，构造器 `0x2be2f8c` 被 `0x2c58d04` 调用并尾调用该方法。builder有普通/慢快及model getter路由；慢快HS4K相关分派同样排除30/25，普通路径复用预构造字段，未完成每个字段的独立绑定和完整虚调用追踪。**不把这里的慢快分支换名为普通主录分支。** [真正导入](../../work/sony-firmware-20261024/stage2/modes/actual-set-movie-import.json)、[真实库入口](../../work/sony-firmware-20261024/stage2/modes/libmpr-entry.json)、[builder](../../work/sony-firmware-20261024/stage2/modes/actual-format-builder.asm)、[构造/序列调用](../../work/sony-firmware-20261024/stage2/modes/format-set-sequence.asm)
- 代理转换 `convert2proxyParams` 在appFw `0x2e50bf0`；`0x2e50d10..14`将VPC6写入代理视频输出，`0x2e50c64`直接 `str w3,[x6]` 透传输入FrameRate。直接调用者 `0x2e6a948` 属查询，`0x2e6f0a0` 位于真正设置wrapper。因此静态证据支持代理复用传入帧率；本机29.97样片仍待实录，不能把函数赋值当最终成片。[代理反汇编](../../work/sony-firmware-20261024/stage2/modes/proxy-params.asm)、[本机路由JSON](../../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)

### Inferences
- 最小实验不应把60P枚举改成30P后直接写机身。必须使上层模式、查询、真实设置、主流VPC/帧率/码率和writer level保持一致；否则即使UI出现，也可能在查询或设定时触发系统错误。
- 候选方向是保持现有HD AVC的传感器/缩放/29.97路径，在明确的独立选项下改为已存在HD HEVC主流配置，同时同步查询与元数据。是否可行仍需精确还原model字段和验证编码器/MP4接受；这里没有生成可安装的偏移补丁。

### Gaps
- 未完全恢复普通设置builder的model getter绑定、参数合法性、帧率与码率表、writer及CP微码的所有后续检查。未取得可启动、可录像、可恢复补丁。检查到的47种feature getter模式仅解析11个注册项，不能拿“这些项未见HEVC开关”推断完整feature表不存在该开关。

## 分析工具和复核方法

### Takeaway
本轮实际使用Python标准库、pyelftools0.32和Capstone5.0.6，读取ELF重定位、导出符号、跳表及少量候选函数反汇编。保留了不依赖第三方包的只读复核脚本；没有运行REA会话，也没有把REA名称当作分析深度的证据。

### Cited Findings
- 研究参考原作者 `appfw_elf.py` 与 `feature_manager_matrix.py`，固定commit `12582457829e34eae7211df5b0c599fa46b7e5e1`，来源及每份文件SHA256已记录。参考源码经阅读后仅用于静态读取，最终删除参考副本，保留来源；没有执行安装器。[原作者固定源码](https://github.com/leogenot/sony-a7iv-feature-research/tree/12582457829e34eae7211df5b0c599fa46b7e5e1)、[参考来源回执](../../work/sony-firmware-20261024/stage2/modes/reference-provenance.json)
- 固定原作者文档已经对比FX3 7.02，故可借其定位方法；本次所有地址/哈希都重新从用户研究包得到，而不是套A7IV地址。feature_manager解码仅47个匹配getter、11个注册项，属于该模式匹配工具的局部覆盖。[原作者PRODUCT_CLASS](https://github.com/leogenot/sony-a7iv-feature-research/blob/12582457829e34eae7211df5b0c599fa46b7e5e1/docs/PRODUCT_CLASS.md)、[本机feature输出](../../work/sony-firmware-20261024/stage2/modes/fx3-feature-matrix.json)
- REA官方固件模块以Binwalk/Unblob为外部引擎，首阶段验证Linux x64，ELF再交Ghidra；本机没有已装的REA/Ghidra分析器。核对REA已发布6.7.0包来源但未为名称额外安装重工具；专用容器已可解开，当前跳表和函数证据由本地工具完成。[REA固定固件说明](https://github.com/morluto/rea/blob/fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4/docs/firmware-analysis.md)、[工具来源](../../work/sony-firmware-20261024/stage2/modes/tool-provenance.json)、[Capstone官方API](https://www.capstone-engine.org/lang_python.html)、[pyelftools官方库](https://github.com/eliben/pyelftools)
- `inspect_mode_routes.py` 只读，先严格校验两个输入哈希；用标准库读取节和重定位、已审查的静态映射，再输出JSON。不访问相机、不执行ELF、不生成补丁。下列命令已实际运行成功。[复核脚本](../../work/sony-firmware-20261024/stage2/modes/inspect_mode_routes.py)、[JSON结果](../../work/sony-firmware-20261024/stage2/modes/routing-evidence.json)

```sh
python3 work/sony-firmware-20261024/stage2/modes/inspect_mode_routes.py \
  work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so \
  --mpr work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so \
  --output work/sony-firmware-20261024/stage2/modes/routing-evidence.json
```

### Inferences
- 目前最有价值的交付是可再生的具体模式路由与候选缺口，后续可据此验证最小功能改造；无需先碰整包重签/跨刷或把未经证明的UI补丁写入主力机。

### Gaps
- 未运行REA深度反编译、未模拟或执行目标ARM代码。静态地址映射、已表示的参数、驱动实际接受、实机文件与恢复能力是不同证据级别。
