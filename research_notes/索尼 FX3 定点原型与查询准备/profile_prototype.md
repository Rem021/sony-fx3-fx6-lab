# FX3 7.02：仅 CPU 的实验目标 profile 桥接

## 1. 是否实现了真实选择与 setter 转换，而非直接填写预期参数？

### Takeaway
实现了一个仅存在于 Unicorn 客体内存中的定点实验桥：普通 movie、`setting_file_format=6`、typed HS frame `2` 这一组合，产出 builder `(frame15,format6,quality2,color0)`，再由实际 setter 转换块产出 `(VPC6,VQuality6,Frame3)`。它是**未接入现有菜单的实验选择器**，不是完整模式，也不是可安装补丁；目标与恢复验收仍未完成。[脚本](../../work/sony-firmware-20261024/stage12-prototype/profile/profile_prototype.py)、[执行结果](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

### Cited Findings
- 真实 builder 从 `0x2beae8c` 开始执行，在原普通/静态格式分发点 `0x2bee8a0` 分支到新建的 guest-only 页 `0x0a000000`。实验 guest 重新执行原 movie 判定 `0x2a4e6b0`，只接受 movie、format6、typed frame2；其它输入重放被替换的原 `SUB W1,W19,#5` 并返回原分发。该映射位于原 PT_LOAD 之外，**不是已核验的相机代码洞或部署地址**。[guest trampoline 反汇编与源范围](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 目标测试将 builder 的四个初值全部置为 `0xfefefefe`。guest PC `0x0a000028/30/38/3c` 分别真实写入 `frame15/format6/quality2/color0`，随后进入原 builder epilogue；因此目标未借用构造器预置 frame15 或质量值。原 constructor 与完整 model sequence 没有执行，所有全局 model 单元仍是明示合成输入。[experimental_target 的 stores、initial_builder_tuple](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 实际 setter HS420 点 `0x2e6ed04` 的实验分支逐项检查 `(format6,frame15,quality2,color0)`，仅此组使用 VPC6，否则重放原 `MOV W0,#5`。**最终三项仍由原 setter 指令** `0x2e6ec5c/0x2e6eeb4/0x2e6f03c` 写成 `6/6/3`；没有 Python hook 填写编码参数。[experimental_target_setter 的 stores](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 此处 setter quality2 是该层的16M转换输入，不能与 typed HS4K quality2（400M42010）混同。实验 frame2 固定得到16M42010，不从既有 HS4K 三个 quality key 中借用一个可选质量项。[上轮 typed namespace 核对](../索尼%20FX3%20目标模式与模型门禁/typed_builder.md)、[实验选择器定义](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

### Inferences
- 已有可执行的局部桥接证据，排除了“必须全局把 VPC5 改成6”的实现假设；它不证明现有产品/菜单允许这一输入，也不替代新增模式身份、查询和持久化设计。[精确分支与对照结果](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

### Gaps
- 没有定义可供用户选择的完整格式 enum、持久化结构或菜单项；当前菜单保持未接入。普通 movie+format6+frame2 只是本实验的明确入口，不被宣称为一套已自洽的完整产品模式。[未关闭门禁](../../work/sony-firmware-20261024/stage11-model/capabilities/candidate-constraints.json)

## 2. 实际 guest 输出是否进入真实 MPR 主录参数包？

### Takeaway
将实际 guest 产生的 builder 四元组复制到真实 setter 的合成输入结构，再将 setter 实际产出的三元组复制到原 MPR helper 输入。原 MPR 对 stream0 返回 main codec15，原 Open 参数准备代码真实写出 `1920×1080 / HEVC / 42010 / Frame3 / API quality22`，有理数 helper 返回 `30000/1001`，bitrate helper 原返回值为16000；没有执行 EncOpen、Start 或硬件编码。[完整数据传递与写入轨迹](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

### Cited Findings
- `GetCodecInfoForCodec` (`0xcd40c`) 的输入来自实际 setter VPC6，并显式使用 `stream_type=0`，返回15；基本参数 validator 返回0。这里确认的是局部 MAIN helper 语义，未执行 SetMovieRecParam 完整主录路由。[actual_guest_output_to_MPR](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 原 `SetEncOpenParam` (`0xd13f8`) 在 guest PC `0xd1518/20/28` 写出 codec15、1920、1080；`0xd1554/5c` 写 frame3/NTSC1；`0xd15a0` 写 API quality22；`0xd15f8/604` 写 chroma0/bitdepth1。输出参数包事前为零，仅输入元组和明确的 audio0 被 host 序列化；没有手工填写目标输出字段。[open_parameter_preparation 的 stores 与 fields](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 原 `ConvertFrameRateToNumerAndDenom` 返回 `30000/1001`；原 `GetVideoBitrate(VQuality6)` 返回16000，保留该 raw 单位，不在本轮将其改标为 bit/s。它与既有16M目标映射一致，但尚无实际文件码率。[本轮 rational/bitrate](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[已有16M链](../../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json)
- **显式日志适配器存在**：仅地址 `libmpr:0xc8c70` 可被拦截。它只读取并记录 guest 诊断包，再执行 `PC←LR`，不改 X0/其它返回寄存器、guest 内存或编码输出；不称“无 stub”或完整原生执行。本轮逐个保留调用指令原字节及返回后的真实指令、寄存器读写，证明日志 X0 在消费前被原指令覆盖；最后一个 packet 日志后仅返回，调用方未使用其标量返回值。[logging_adapter、logging_return_nonconsumption_proofs](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 严格关闭该 adapter 时，validator、main codec 与 packet 都在 `0xc8c70` 被拒绝，bitrate 与 rational 仍能直接返回。此负证保留，未执行其分配/发送日志的 IPC 依赖。其它未知调用仍会停止，不存在 encoder passthrough。[strict_no_adapter_negative](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- Unicorn 官方接口明确区分代码、无效内存和写入 hooks；本轮使用它们记录或停止未知操作，未将无效访问转发到主机硬件。[Unicorn 官方头文件](https://github.com/unicorn-engine/unicorn/blob/master/include/unicorn/unicorn.h)

### Inferences
- 这一证据比单独手工输入 VPC6 的旧参数包测试多闭合了两层：实验 typed selection 与真实 setter。它仍不能证明 writer/mux、硬件、设备菜单或媒体限制会接受该模式。[本轮真实输出链及未执行清单](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

### Gaps
- full model、derived format 分类、query/remain、持久化、完整 setter、SetMovieRecParam、EncOpen/Start、writer/mux、实录码流、音画同步、温度与恢复均未执行。不能从参数包生成推断可录制，更不能推断已具备故障恢复保障。[not_executed 与 goal_achieved=false](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

## 3. 原版合法组合、负例、执行边界与原件是否得到保留？

### Takeaway
19 个合法 HS4K 帧率/质量组合均完成 stock 与 prototype 对照，完整 builder 缓冲区散列及 setter 三元组保持一致；另有8个 builder负例/其它格式控制、8个 setter 控制保持原结果。typed 25p 仍停在原断言入口，原件及依赖的执行前后散列一致。[对照结果](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[源收据](../../work/sony-firmware-20261024/stage12-prototype/profile/source-receipt.json)

### Cited Findings
- 合法集合从 stage11 `builder-static.json` 的比较指令及 `selection-tables.json` 的原跳表导出，每条源指令/表字节又与 pinned app 原件核对：60/50 的 quality `{8,12,16,21,26}` 共10例，24 的 `{16,17,23,24,27}` 共5例，120/100 的 `{4,9}` 共4例。没有把 typed 名称表当作允许集。[source_allowed_sets](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- builder 控制覆盖 typed frame3/7、三个族的非法 quality2、still exposure、format7/8；均保持原断言停止和相同缓冲区。setter 控制覆盖 HD AVC、UHD AVC、HS422、其它帧率/质量、非法 format/color，均保持原输出或停止原因。原 typed frame2 也作为 stock 断言负证保留。[legitimate_HS_cases、builder_negative_and_other_format_controls、setter_controls、stock_target](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 每个 guest 调用最多2000条指令、100000微秒。目标 builder399条，setter58条；MPR validator53条、main codec56条、bitrate7条、rational15条、packet594条。合法组合中 builder最多465条、setter最多52条。未知 PC、未知 PLT、SVC/HVC/SMC、保护/未映射内存均停止；guest 写入仅允许合成栈与 scratch。[脚本白名单与每例 steps/PC/stores](../../work/sony-firmware-20261024/stage12-prototype/profile/profile_prototype.py)、[运行结果](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)
- 写入前核对卷 UUID 为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。app 原件 SHA256 为 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`，mpr 为 `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`，前后相同；stage4/10/11依赖也保持原散列。没有相机、USB、UI、认证、文件传输、module/driver、WBI 或 flash 操作；未导出 ELF、相机 payload 或 patchfile。[source-receipt.json](../../work/sony-firmware-20261024/stage12-prototype/profile/source-receipt.json)
- 复现复用现有 `.venv`，无需安装依赖或新建 VM：`work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage12-prototype/profile/profile_prototype.py`。新产物仅在本 profile 工作目录与此笔记；未下载或保留新的第三方原始源码。[脚本及依赖收据](../../work/sony-firmware-20261024/stage12-prototype/profile/source-receipt.json)

### Inferences
- 19组对照支持本轮选定普通 HS4K 合法域内的定点保留；不能将它扩大成整个 app 的所有模式或产品组合不受影响。[明确测试域](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)

### Gaps
- 实验入口尚未接入菜单，模式身份/查询/持久化门禁保持未关闭，静态代码洞和装载地址未验证；本轮只提供功能性的离线 CPU 证据。**实际 FX3 7.02 MAIN HD HEVC42010 约16M29.97 与 verified restore 目标仍未完成。**[本轮 status/goal_achieved](../../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[原候选门禁](../../work/sony-firmware-20261024/stage11-model/capabilities/candidate-constraints.json)
