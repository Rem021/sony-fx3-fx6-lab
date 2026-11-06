# FX3 7.02 typed builder 输入与主录目标门禁

## 1. frame、quality、color 究竟从哪些 typed model key 读取？

### Takeaway
已把普通主录 `format6` 路径的 typed model getter、全局槽、key ID、builder 输出和真实 MPR 枚举区分并关联。目标 `1920×1080 HEVC 4:2:0 10bit / 30000/1001 / 约16Mbps` 在这条原版 HS4K model 路径没有合法输入元组；此前合成的 setter 输入 `(format6,quality2,frame15,color0)` 不能改称一个合法 model/menu tuple。[原指令](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)、[受限执行](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Cited Findings
- 输入原件为官方 FX3 7.02 提取件 `appFw.so`，SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；libmpr 为 `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`。本轮没有联网下载、第三方源码执行、相机、USB、GUI、认证、模式切换、上传、WBI 或刷写。[本轮收据](../../work/sony-firmware-20261024/stage11-model/builder/source-receipt.json)
- builder `0x2beae8c` 的 getter 都是返回固定全局单元地址的原始 leaf 函数，随后 `LDR Wn,[X0]` 读值；`ModelType&` 并未作为这些 leaf getter 的指针参数。下表的 key 由 frame/quality 修改分发器中的显式立即数关联，未从 PRM 名称指针表间距猜算。[getter 原字节](../../work/sony-firmware-20261024/stage11-model/builder/model-leaf-accessors.json)、[key 路径](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)、[质量分发器调用](../../work/sony-firmware-20261024/stage11-model/builder/quality-dispatch-callers.json)

| model 属性 | key | 当前值 getter → 全局槽 | builder 中读取处 |
|---|---:|---|---|
| `setting_file_format` | `0x399` | `2bd0fb0→2934c9c→8319b68` | `2beaeac`，W19 |
| `setting_movie_rec_frame_rate_xavc_hs_4k` | `0x39c` | `2934d14→8319bac` | `2beaed4`，W27 |
| `setting_movie_record_setting_xavc_hs_4k_60p_50p` | `0x3a4` | `2934e54→8319c94` | `2beaedc`，W21 |
| 同族 `_24p` | `0x3a5` | `2934e7c→8319cc0` | `2beaee4`，栈 `+0xb4` |
| 同族 `_120p_100p` | `0x3a6` | `2934ea4→8319cec` | `2beaef0`，栈 `+0xd0` |
| `exposure_mode` | `0x77b` | `2bd0fe0→293d90c→831e9c4` | `2beb214` 起 |

- frame 修改分发器 `0x27c79c4` 的 format6 分支 `0x27c7aa4` 调用 `2934d14/2934d28`，并在 `27c7ac0` 写 key39c；三个 quality 分支在 `27c8b0c/27c8b34/27c8b5c` 写 key3a4/3a5/3a6。当前值 getter 与其紧邻另一槽 getter 的配对由同一分支直接显示；本轮没有执行这些修改器。[本轮原指令](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)、[独立菜单侧证据](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)
- `is_movie_exposure_mode` 的原始纯判定为 `0x2a4e6b0`，`is_still_exposure_mode` 为 `0x2a4e5e0`，`is_sq_exposure_mode` 为 `0x2a4e798`；本轮给 exposure 单元合成值5，执行原判定进入普通 movie 分支 `0x2bee8a0`。format6 经原表 `0x392f9ac` 进入 `0x2beb3f4`，因此选的是 HS4K 帧率与质量族，不是通过一个“HD”输入派生 HEVC。[完整 builder 反汇编](../../work/sony-firmware-20261024/stage11-model/builder/builder-disassembly.txt)、[原跳表字节](../../work/sony-firmware-20261024/stage11-model/builder/selection-tables.json)
- 原始 typed 名称表把 HS4K 帧率枚举2、3命名为30、25；HS4K quality 的枚举2命名为 `400M_420_10BIT`，枚举29为 `16M_420_8BIT`。该32项词汇表没有 `16M_420_10BIT` 项；名称存在本身不代表允许分支。[同原件名称/枚举表](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)

### Inferences
- “typed getter 枚举2”、“builder/setter 输入 quality2”和“MPR VQuality6”是三层不同的数值空间。负例注入 typed quality2 测到的是400M选项被该组拒绝，不能称为“16M被拒绝”；16M目标不可达的强证据是**全部允许 builder quality 输出经过真实 setter 与 bitrate helper 都没有目标别名**。[静态允许分支](../../work/sony-firmware-20261024/stage11-model/builder/builder-disassembly.txt)、[别名执行核查](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Gaps
- 原件中的名称表、key 和分发器证明模型身份及选择关系，未执行完整 model sequence、媒体限制、菜单可见性、保存/恢复或真实机身全局状态。这里只闭合普通 movie、format6 的本轮范围，不能宣称穷尽所有 sequence 或跨产品分支。[明确的执行边界](../../work/sony-firmware-20261024/stage11-model/builder/source-receipt.json)

## 2. 普通 HS4K 能否产出目标帧率、码率和色彩，是否有数值别名？

### Takeaway
没有29.97别名，也没有16M别名。HS4K 允许的五个帧率最终是59.94、50、23.976、119.88、100；质量允许集合的真实 bitrate helper 返回最小30000，目标 VQuality6 对应的返回值16000不在其中。[逐条原指令执行结果](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Cited Findings
- HS4K frame 跳表 `0x392f8a0` 原字节为 `00 1b 23 23 1d 1f 21`。typed getter0..6经 signed-byte×4 加到 `0x2beb414`：2、3均进入 `0x2beb4a0` 的原断言路径；其它值如下。每个允许 builder frame 又经真实 setter 原转换块及 libmpr `0x2c0de8` 转成有理数，排除了数值别名。[跳表原字节](../../work/sony-firmware-20261024/stage11-model/builder/selection-tables.json)、[原 setter 与 rational helper 执行](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

| typed frame key39c 值/标签 | builder/setter frame | MPR FrameRate | 实际分子/分母 |
|---|---:|---:|---|
| 0 / 60 | 20 | 7 | 60000/1001 |
| 1 / 50 | 18 | 5 | 50/1 |
| 2 / 30 | 断言路径 | 未产生 | 未产生 |
| 3 / 25 | 断言路径 | 未产生 | 未产生 |
| 4 / 24 | 10 | 0 | 24000/1001 |
| 5 / 120 | 22 | 9 | 120000/1001 |
| 6 / 100 | 21 | 8 | 100/1 |

- HS4K 品质/色彩分支在 `0x2bec4c4`（60/50）、`0x2bec59c`（24）、`0x2bec670`（120/100）。允许的 typed 输入与输出见下表；表内逐行映射来自原始比较、跳表与写入指令，未把所有12行分别做 guest 测试；其8个不同 builder quality 输出均独立执行了真实 setter 和原 `GetVideoBitrate` (`0x2c0ce0`)。[原分支指令](../../work/sony-firmware-20261024/stage11-model/builder/builder-disassembly.txt)、[typed 标签表](../../work/sony-firmware-20261024/stage11-model/capabilities/capability-string-index.json)、[8种输出别名核查](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

| typed quality 组/key | typed 值与名称 | builder quality/color | MPR VQuality | GetVideoBitrate 原返回值 |
|---|---|---|---:|---:|
| 60/50，3a4 | 8 / 200M42210 | 18/1 | 22 | 200000 |
| 同组 | 12 / 150M42010 | 16/0 | 13 | 150000 |
| 同组 | 16 / 100M42210 | 13/1 | 12 | 100000 |
| 同组 | 21 / 75M42010 | 10/0 | 35 | 75000 |
| 同组 | 26 / 45M42010 | 7/0 | 44 | 45000 |
| 24，3a5 | 16 / 100M42210 | 13/1 | 12 | 100000 |
| 同组 | 17 / 100M42010 | 13/0 | 12 | 100000 |
| 同组 | 23 / 50M42210 | 8/1 | 14 | 50000 |
| 同组 | 24 / 50M42010 | 8/0 | 14 | 50000 |
| 同组 | 27 / 30M42010 | 5/0 | 41 | 30000 |
| 120/100，3a6 | 4 / 280M42210 | 22/1 | 46 | 280000 |
| 同组 | 9 / 200M42010 | 18/0 | 22 | 200000 |

- `color0` 是该 HS4K 分支的420选择，`color1` 是422选择；真实 setter 分别写 VPC5、VPC7，均仍属于4K HS族。旧已核准的目标参数 VPC6/VQ6/Frame3 为另一层 HD HEVC 目标，不能与上表 model 选择混称。[真实 setter 分支](../../work/sony-firmware-20261024/stage10-mainpath/main/actual-main-setter-static.json)、[此前目标参数证据](../../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json)
- **stage10 旧控制标签更正**：旧文件中“HS420 59.94 100M”使用的是 model frame13；真实 setter 把13转成 MPR Frame2，原 libmpr 又把 Frame2 转成 **25/1**。旧标签错误不影响其“同一全局MOV修改覆盖其它帧率组合”的观察，但不能继续称其为59.94控制。目标 model frame15→MPR Frame3→30000/1001 在本轮也独立复核正确。旧产物保留原状，没有静默修改。[旧控制输入](../../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json)、[本轮更正的七项 rational 核查](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Inferences
- 原版不存在“把 HS4K 当前 model key 设成某个现成合法枚举就获得 HD29.97/16M42010”的元组。frame30/25被具体代码拒绝；即使另外设法到达 HS4K 品质选择，其允许输出也不能通过后续 alias 转成目标VQ6。需要一套新模式定义与门禁/查询/编码一致性改动，而非重命名VPC或把一个通用数字2跨层复用。[两级选择原指令](../../work/sony-firmware-20261024/stage11-model/builder/builder-disassembly.txt)、[输出别名核查](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Gaps
- `GetVideoBitrate` 保留原始返回值，不误标为 bit/s；此前目标16M映射的 raw 为16000。本轮没有扩大到编码packet或硬件录制验证。[此前16M链](../../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json)、[本轮 raw 结果](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

## 3. 本轮实际执行了什么，还剩哪个精确入口？

### Takeaway
完成9例纯 selection 受限 guest、7个帧率别名检查及8个质量别名检查；没有替身、固件代码修改、原生执行或完整 sequence 执行。下一个输入定义问题已可具体停在 setting_file_format 的新增模式语义及菜单/产品 allow-list，不能靠这份选择证据直接形成刷写候选。[可复现脚本](../../work/sony-firmware-20261024/stage11-model/builder/verify_typed_selection.py)、[结果](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)

### Cited Findings
- 原 builder 执行从 `0x2beae8c` 开始，LR 合成停止点 `0x12000000`；允许范围仅 builder 内部、已验证 leaf getter、三个 wrapper、三个 exposure 纯判定。原 ELF guest 只读；全局 model 页由 host 在运行前注入显式合成值，运行时不可写。guest 只可写合成栈和 builder缓冲区；未知PC、外部调用、SVC/HVC/SMC、非法内存访问立即停止。[白名单脚本](../../work/sony-firmware-20261024/stage11-model/builder/verify_typed_selection.py)
- 显式合成 model 单元为：`8319b68=6`（format）、`831e9c4=5`（exposure）、`8319bac=0..6`（HS4K frame）、`8319c94=12`（60/50品质）、`8319cc0=17`（24品质）、`8319cec=9`（120/100品质）；其它已识别 getter 单元合成为0。不是从相机读取的 model 快照；构造器未执行，仅显式供给已知初值 frame15/format6/quality24/color0。[每例注入记录](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)
- 7个帧率值中0/1/4/5/6返回，2/3停在原断言logger入口 `0x2f6fe3c`；另2例给60/50或24的 typed 品质单元注入2（400M42010），也停在同一入口。断言后的日志/等待/终止代码没有执行；负例中缓冲区保留的构造初值没有被当成成功输出。[9例轨迹与写入PC](../../work/sony-firmware-20261024/stage11-model/builder/typed-selection-results.json)
- 每次builder最多2000条指令、100000微秒；没有固件stubs、passthrough或假定getter返回。getter本身执行原始 ADRP/ADD/RET，读取的数值是明确标注的合成 model 数据。后续alias检查复用项目既有只读原setter转换块与纯 libmpr helper执行器；未再跑旧14例MOV诊断，也没有输出patch或修改ELF。[执行脚本](../../work/sony-firmware-20261024/stage11-model/builder/verify_typed_selection.py)、[依赖脚本哈希](../../work/sony-firmware-20261024/stage11-model/builder/source-receipt.json)

### Inferences
- 格式输入本身已经携带HS4K身份，帧率和品质key按该身份选择，setter再沿format6得到4K VPC；这解释了只改变底层VPC为何会留下 model/menu/查询不一致。实现新目标需在明确的格式定义、帧率与品质允许组合、容量/时间查询及编码输出之间建立同一模式身份。[format6 原选择链](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)、[builder原指令](../../work/sony-firmware-20261024/stage11-model/builder/builder-disassembly.txt)

### Gaps
- 本轮停止于有边界的输入选择闭合。产品/menu allow-list由并行研究负责；若继续实现，精确起点是 format key399 的设置/派生分支 `0x27c79c4` 所用format dispatch与 `0x2bee8a0` 的format5..12表，而不是全面模拟app。没有验证任何实机恢复入口、冷启动、硬件编码、文件码流、音画同步、长录或温度。[原始分发器](../../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json)、[执行边界收据](../../work/sony-firmware-20261024/stage11-model/builder/source-receipt.json)
