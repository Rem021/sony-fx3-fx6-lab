# FX3 主录输入来源与真实 setter 转换块

## 1. 普通主录 setter 的输入由哪里产生？

### Takeaway
已把 `mpr_SetMovieRecParam` 上游推进到真实 model sequence 与带模板身份的输入 builder。现在有构造器、内嵌结构偏移、发送 wrapper 和实际 setter 的同文件调用证据；builder 内部完整产品／菜单门禁仍未执行或闭合。[调用与偏移摘要](../../work/sony-firmware-20261024/stage10-mainpath/main/main-path-summary.json)

### Cited Findings
- 官方 FX3 7.02 `appFw.so` 固定 SHA256 为 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`。当前原始 `.text` 对真实 setter `0x2e6e5d8` 仅有一处直接调用：`0x2ddaebc`，所属 wrapper 入口 `0x2ddae94`；对该 wrapper 找到12处直接调用，分别处于 boot、mode transition、movie format、movie rec param 等 sequence 上下文。[原始指令及调用扫描](../../work/sony-firmware-20261024/stage10-mainpath/main/actual-main-setter-static.json)
- `sequence_set_movie_rec_param` 路径构造时在 `0x2c5b5d0` 以 `seq+0x1e0` 调用 builder 构造器 `0x2beea04`；实际发送在 `0x2d94fb4` 以 `seq+0x210` 调用 wrapper。两者相差 `0x30`，与 builder 内部输入结构位置相符。[构造与发送原字节](../../work/sony-firmware-20261024/stage10-mainpath/main/model-sequence-builder-link.json)
- 该构造器在 `0x2beecb0` 尾调 `0x2beae8c`。后者的原厂错误上下文字符串明确为 `mpr_SetMovieRecParam_in_t_builder<ModelType>::determine_frame_rate_and_movie_quality_and_yuv_color_space`，模板 `ModelType=model::sequence_set_movie_rec_param::scoped_read_model`；身份字符串 VA 为 `0x39318b8`。[带类型的原厂字符串](../../work/sony-firmware-20261024/stage10-mainpath/main/model-string-evidence.json)、[字符串原始交叉引用](../../work/sony-firmware-20261024/stage10-mainpath/main/builder-string-xrefs.json)
- builder 的帧率、格式、质量、色彩字段分别为 `+0x40/+0x44/+0x48/+0x4c`，对应实际 setter 输入 `+0x10/+0x14/+0x18/+0x1c`。构造器先给 frame=15、quality=24、color=0 的初值；format 经 `0x2bd0fb0→0x2934c9c` getter 读取。随后 determine 函数会按众多模型值重选参数，这些初值不能当作最终菜单设置。[构造器、getter 与 builder 入口](../../work/sony-firmware-20261024/stage10-mainpath/main/model-builder-static.json)、[构造器字段原字节](../../work/sony-firmware-20261024/stage10-mainpath/main/model-sequence-builder-link.json)

### Inferences
- 后续应从 `0x2beae8c` 的真实模型访问器和分支继续查帧率／质量／色彩门禁，结合 setter `format` 分支形成同一套模式定义；只绕过查询 helper 或只改 MPR 的输入无法保证 model、菜单、剩余时间和最终编码一致。[已定位的两层入口](../../work/sony-firmware-20261024/stage10-mainpath/main/main-path-summary.json)

### Gaps
- 未闭合这组模型访问器对应的全部 typed setting key、产品能力表和菜单允许组合；未验证整个 builder 的真实运行状态或所有 sequence 分支。
- wrapper 的12处是当前原文件 `.text` 直接 B/BL 扫描结果，不能声称不存在其它间接调用。

## 2. 普通 setter 转换块能否由模型形状输入产出 HD HEVC 目标？

### Takeaway
14例受限 CPU 仿真已核准真实 setter 转换块对输入字段的处理；原厂目标形状输入输出的是 UHD HEVC VPC5。单条 MOV 常数的内存诊断能得到 VPC6／VQ6／Frame3，但同时误改其它 HS420 组合，明确不满足“可用补丁”。[完整结果与逐条写入PC](../../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json)

### Cited Findings
- 入口为实际 setter 内 `0x2e6ea58`，停止 PC 为 `0x2e6f040`；另只允许其帧率分支 `0x2e6f45c–0x2e6f494`。每例最多2000条指令、100000微秒；没有任何替身，未知代码／外部调用即停止，SVC/HVC/SMC 禁止。原 ELF 为 guest 只读，guest 只能写合成栈；没有设备、网络、host syscall 或 MMIO 转发。[可复现白名单脚本](../../work/sony-firmware-20261024/stage10-mainpath/main/verify_setter_conversion.py)
- 合成输入仅提供 format、quality、frame、color，及进入此块所需的 x24／x29／x19 指针；其它合成内存为零，不是机身 model 快照。实际 guest 指令在 `movieRecParam+0x170/+0x174/+0x178` 写出 VPC／VQuality／Frame，每例保存进入和停止PC、执行PC轨迹及这些写入的实际PC。[合成上下文及客体写入](../../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json)

| 输入控制 | 原版 VPC／VQ／Frame | 诊断内存覆写后 |
|---|---|---|
| HS420，format6／quality2／frame15／color0 | 5／6／3 | 6／6／3 |
| HD AVC，format8／quality2／frame15／color0 | 1／6／3 | 1／6／3 |
| UHD AVC，format7／quality13／frame15／color0 | 0／12／3 | 0／12／3 |
| HS422，format6／quality2／frame15／color1 | 7／6／3 | 7／6／3 |
| HS420，format6／quality13／frame13／color0 | 5／12／2 | 6／12／2 |

每行均运行原版和诊断各一次；额外4例无效 format／quality／frame／color 均停在未准许或断言代码，未伪造成功。表中“HD AVC控制”表示编码组合路径，不声称其16M质量组合已通过整机限制。[14例CSV](../../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-cases.csv)

- 诊断仅在 Unicorn 内把 `0x2e6ed04` 的 `a0008052`（MOV W0,#5）改为 `c0008052`（MOV W0,#6）；原文件前后 SHA 一致，没有输出修改后的 ELF、补丁或安装文件。59.94／100M 控制也被改为 VPC6，直接显示该点作用域覆盖全部 HS420，而非仅目标 HD29.97。[覆写范围与原文件回验](../../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json)

### Inferences
- 实际 setter 的格式分支是一个具体适配点，但 format 输入仍表达 HS4K，VPC 已变 HD；它与模型、菜单以及其它录像组合不一致。可用实现需要对目标模式有精确选择及全链一致定义，不能把本轮 MOV 定位诊断当成刷写候选。[原版分支与诊断差异](../../work/sony-firmware-20261024/stage10-mainpath/main/actual-main-setter-static.json)

### Gaps
- 只执行了 setter 的纯转换块，没有执行完整 builder、完整 app setter、MPR SetMovieRecParam、硬件 Open／Start 或拍摄。此前真实 MPR 参数包证据仍是另一份离线证据，不能合并成实际录制成功。

## 3. 对“1080p30可用”的结论改变到哪一层？

### Takeaway
新增的是从真实模型 builder 到 setter 的可定位路径，以及 setter 转换块的客体执行证据；未获得可刷功能。目标 Frame3 仍是 30000/1001（29.97），不能改称精确30.000。[既有真实帧率转换证据](../../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json)

### Cited Findings
- 本轮执行边界为 `bounded_guest_function_emulation=true`、`camera_native_execution=false`、`USB_or_GUI=false`、`persistent_camera_write=false`；没有创建 VM，没有原生执行 ELF，也没有相机接口操作。[执行边界摘要](../../work/sony-firmware-20261024/stage10-mainpath/main/main-path-summary.json)
- 所有本轮输入来自已固定的官方提取件和本项目历史证据；未下载新的第三方源码／二进制，未触碰旧证据。收据记录原件及本轮产物哈希。[来源收据](../../work/sony-firmware-20261024/stage10-mainpath/main/source-receipt.json)

### Inferences
- 下一个有边界的离线入口是 `0x2beae8c` 的产品／模型值选择与 typed setter key 映射，同时核对查询／菜单对同一目标参数的解释。这比直接扩大低层 VPC 改动更有助于形成仅影响目标组合的候选。[当前未闭合项](../../work/sony-firmware-20261024/stage10-mainpath/main/main-path-summary.json)

### Gaps
- 全部实机授权与验收门槛仍保留；硬件编码、实际码流、音画时序、长录、温度、同机恢复和冷启动均未验收。
