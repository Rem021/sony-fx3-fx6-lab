# VDF 0x0152：peaking 同步配置合同

**可给有界软件配置后端的成功回复为 `0d2052110c00018000005900`：0x1152、12B、status32=`0x590000`，不归零。** 原 CP 路径为 wire0152→internal9d→旧2001/0202（`VdfSrvcCmdSetPeaking`）→内部f026（`DevCmdSetPeaking`），真实 device 子任务完成/汇总后才回旧1202；不能把收到请求等同硬件生效。此次捕获 `peaking=0`，保存的是关闭配置。（CP `1acaac→1ace44、1ab7a2→1abb60、1b5280、5f7ee4、5f803e、5ff8b0、1ada60、1adcda、5c9b4e`；AP83 serial **23895**。）

只写本目录 [audit_vdf0152.py](audit_vdf0152.py)、[vdf0152-proof.json](vdf0152-proof.json) 与本文；未修改原件/runtime/STATE/锁/Git，未启动 QEMU、运行 CP 或操作设备。AP 地址为 appFw.so ELF VA；CP 为 Thumb VA，文件偏移=VA−`108000`。下文 serial 按原文件 **LF** 编号，保留 CR/NUL；A=原码或直接捕获，B=有约束推断，U=未证实。代码结论由 proof 的原字节/反汇编与44项指令断言支持，运行结论逐行保存。

## 1. 实际请求和逐字段冻结

目的 `92840747`，source 为本次请求 metadata 的 `81cf61c2`（不得跨运行硬编码），16B：

```text
0d205201100001800300010000eb8080
```

| 运行目录（均在 menu-repair-01/runtime/runs/） | 原请求行 / 栈上下文行 | 结果 |
|---|---:|---|
| ap83ar4face-4cd8574a | **23895 / 23857–23896** | 16B如上，tid327；与tid339的0500交错，proof按FP范围分离9帧 |
| ap84amttcg-953a9d56 | **23586 / 23569–23587** | 相同16B、同原相对调用链 |
| ap84ar2native-4b70eab2 | **21718 / 21702–21719** | 相同16B，tid346；不能继承AP83的tid |
| ap84bicount0-b2028788 | **23769 / 23757–23770** | 相同16B；冻结至23770行的前缀，不把后续仍增长的日志纳入本审计 |

脚本把上述四个日志的长度/前缀SHA写在常量 `LOG_SNAPSHOTS`，重建时验证前缀；运行后续追加不会改动本次证据。前缀内未见1152 raw marker只表示有限观察器未记录它，不等于全局无消息证明。（AP83接收栈 **48527–48586**，特别是 **48576–48584**；AP `2de72fc..7320`。）

| 偏移 | 实值 | 已证含义、构造或消费 VA |
|---:|---|---|
| 0–1 | `0d20` | type200d；AP `2de9df4..9e04` |
| 2–3 | `5201` | command0152；AP `2de9e08..10` |
| 4–5 | `1000` | 长度16；AP `2de9e14..18` |
| 6–7 | `0180` | flags8001；AP `2de9e1c..20` |
| 8 | `03` | sel掩码，AP固定3（`2de9e24..28`）；CP旧请求保留3（`1b52b6..52f0`），原日志 `d87a4f`明写sel |
| 9 | `00` | peaking开关，本次关闭；AP初始化0，仅相应条件满足且输入+8为1才写1（`2de9dfc、2de9e2c..68`）；CP日志 `d87a66`；device `1e0e96..9e`仅1映射enabled=1 |
| 10 | `01` | level枚举1；AP输入+10的0/1/2映射为wire2/1/0（`2de9e6c..84、2de9fcc..fd4`）；CP日志 `d87a80`、validate `5f7f28..2c` |
| 11 | `00` | magnification；AP依赖输入+0/+4，构造0/10/40（`2de9e88..ac、2dea068..6c、2dea098..a4`）；CP原字符串 `1b5430`明确字段名 |
| 12 | `00` | color_type，AP固定0（`2dea074`）；CP字符串 `1b5450`、device `1e0ecc..ce`；不是padding |
| 13 | `eb` /235 | y；CP字符串 `1b546c`，device `1e0ed0..d2` |
| 14 | `80` /128 | cb；CP字符串 `1b5484`，device `1e0ed6..d8` |
| 15 | `80` /128 | cr；CP字符串 `1b549c`，device `1e0edc..de` |

后三字节来自AP颜色表 `39635fc` 的索引分支：输入0/1/2/3分别得到 `(81,90,240)/(210,16,146)/(29,255,83)/(235,128,128)`；本次匹配索引3分支 `2dea134..144`。**YCbCr字段名是原字符串事实；“白色”是按235/128/128作出的颜色解释，原UI枚举名称及色度标准未证实。** AP输入结构本身未捕获，不能把代码反推字段说成另一次内存readback。（AP `2dea078..94、2dea0a8..bc、2dea104..144`；serial四处请求行如上。）

## 2. AP调用者、等待、检查和失败后果

**A：本次来源是独立的 `sequence_set_peaking::run`。** AP83九帧为 `2de7264 ←2dea0e4 ←2dcfcc0 ←2d95a18 ←2bd76fc ←2f71ba0 ←libosal_utm1184 ←pthread7020 ←libc c8dbc`；四份捕获均匹配前六帧。字符串 `3953db8`为完整run签名、`3953d96`为源文件、`3967ae0`为vdf_set_peaking签名。静态绑定：`2d95948`入口→`2d95a14`调用`2dcfc94`→`2dcfcbc`调用`2de9de4`→`2dea0e0`调用`send_and_wait_cmp_i(2de70a8)`。（serial **23857–23896**及表中AP84栈范围。）

run将sequence输入 `+1bc/+1c0/+1c4/+1c8/+1cc/+1d0/+1d4/+1d8`搬到wrapper输入；其中mode不在2..3时把第三输入清0。该操作不是直接读live-view帧，wrapper也不要求一个传入像素缓冲区。（AP `2d959b8..2d95a10、2d95a68..6c`。）

wrapper在 `2dea0c8..e0`指定destination92840747、request16B、reply12B，清零本地reply槽后发送；共同封装在 `2de7264`检查send返回，在 `2de72fc`设timeout−1，`2de7300`调用导入`osal_rcv_msg_tmo`。**无有限超时/重试；无回复会使该业务线程停在收包。** AP83末次327快照确在该内核收包路径；“具体队列仍为这一请求”的归属由原同步栈与末快照共同支持B，快照没有另存用户LR/queue参数。（serial **48576–48584**；原send栈 **23857–23896**。）

返回后共同封装固定 `memcpy(...,12)`并在 `2de7320`调用`osal_free_msg`，没有检查收到的command/header/实际长度，也未检查接收函数返回。wrapper从reply+8读status，经 `2de4574`转换；`590000`在 `2de46c4..cc`转本地0，裸0也被接受，但保真reply应保留590000。旧1→590001→本地6a、旧5→590005→6e，桥接发送失败−1→本地69。（AP `2dea0e4..f4、2de7304..7320、2de4574..4810`；CP `1adcda、5c9b8e`。）

run仅status0走 `2d95a20..34`的Success日志，失败走 `2d95a70..2d95b44`的Failure/断言诊断、`usleep(100000)`和 `2ebf3b0`错误处理，然后有回到run收尾的分支。**不能仅凭这些调用就声称必杀进程**：helper自身有返回路径；它的一次性错误通知及上层处理是否终止程序不在本次验收内。缺回复时，成功/失败两条后续路径都尚不可达。（字符串 `3915e04、3915e25`；AP `2d95b38..48、2ebf3b0..444`。）

## 3. CP两级表、类和真实执行生命周期

第一级TBH（decoder `1ac9ee..aca04`）基址 `1aca08`：wire0152槽 **1acaac→1ace44**，case写internal **9d**，`1ad052..70`入桥接服务队列。第二级TBH（decoder `1ab68c..b6a2`）基址 `1ab6a6`：internal9d槽 **1ab7a2→1abb60**，handler `1abb62`调用 **1b5280**；不是靠相邻代码猜映射。（proof.tables直接读取表半字并重算目标。）

bridge `1b528a..52b0`构造旧 **2001/0202/16/1**，将sel3以及其余7个字段复制进去；完整旧包为 `01200202100001000300010000eb8080`。`1b540a..541c`发往 **9059000e**，source928407b9；失败转换−1，经`1abb78..80`送同一1152完成器。RTTI名字VA **b3dc50**=`N3VDF20VdfSrvcCmdSetPeakingE`，typeinfo **b7ea10**，vtable **b7e9f8**；+c/+10/+14分别为命令ID/Validate(或Activate)/Execute：**5f7ee4/5f7ef4/5f7f90**。ID函数明确旧0202。（`1b52b6..5336、1b5420..28、5f7ee4..ef2`。）

Validate要求magnification属于 **0/10/20/40/80**，level≤2，selector **1..7**；不满足则构造旧 **1202/status1**，magnification非法还做诊断。本例3/1/0通过。该函数未检查peaking、color_type或三色分量范围；这不授权软件模型放行任意值。（CP `5f7f06..34、5f7f4e..88`。）

Execute是状态/事件驱动流程：初态设置下一态和内部结果事件 **0x32**，`5f803e`构造 **2001/f026/16/1**，复制8B payload；`5f80c2→1e8298`按selector分派device队列，后面等聚合结果。结果槽非零时回旧1202/status5，完成mask未齐时继续pending，mask齐且结果0才在 `5f8030..3c`回status0。**它不是纯粹“收到配置立即成功”，没有AP raw可用来替代device结果事件。**（CP `5f7f90..803c、5f8060..80ce`。）

selector routing表 **b81088**为mask/queue对 `9→90590819、22→9059081a、4→9059081b、40→9059081c、10→905908dd`（mask为十六进制）；当前3命中前两个。`1e8298`按掩码调用`1e80f4`构造/投递device命令。device类RTTI名字 **b3e250**=`N3VDF16DevCmdSetPeakingE`，typeinfo **b7f7d8**，vtable **b7f7c0**，ID **5ff8b0**明写f026、Validate **5ff8c0**、Execute **5ff8d2**。（`1e82b4..da、5ff8b0..d0`；各mask具体物理显示器名称U。）

device Execute先通过subsystem **vtable+518**（槽 **b81724→60fbd9**）保存全部8B到状态指针 `[subsystem+8]+19a8..19af`，再读取subsystem模式/选择器状态。模式和selector匹配时：模式0调用`1e0e5c`，模式1且peaking=0调用`1e0ef4`并接`1e10f0`；不匹配可跳过硬件动作。结果非零映射5，`5ff982`向9059000e发送event32、12B、selected-mask与result以参与上面的汇总。**保存shadow先于设备动作；保存本身不证明硬件已应用。**（`5ff8fc..97c、60fbd8..fc44、5ff982..9be`；selector判定 `5f8b6c、60f7c8`。）

## 4. 是否依赖sensor/live view

**配置可以在无live-view像素的显式软件后端保存，但原CP全路径不是无硬件依赖。** 旧请求、f026与Validate不包含帧地址，也没有“等一帧sensor”检查；device后续会读当前输出模式/selector。模式0路径用magnification/level表 **b7f080**把 `(0,1)`映射1，再将开关、color_type、YCbCr和目标选择传入 `60cabc→a5e3f2`；后者检查状态 `a66770`，并向 **906605a9**发op16/28B。失败回5。模式1关闭路径则经`60cae0`以及`1e10f0→60cd22→a5e17a`的设备控制，后者向906605d9发opbd/24B。（CP `1e0e5c..eee、60cabc..cade、a5e3f2..428、a66770..786、1e0ef4..f38、1e10f0..114e、a5e17a..1b2`。）

由这些原调用可证“真实输出状态/设备服务会影响原执行结果”，不能证明“没有live view必失败”或“必须先造一帧才能配peaking”。本次没有运行CP、原设备mode/selector状态readback或硬件结果，因此这些条件在AP83/84应走哪条device分支 **U**；本次仅可将软件后端状态保存/接受定义为自己的合同，始终保留 `pending_hardware=true`。（同上VA；运行只见请求，serial四处捕获行。）

## 5. 回复状态域与精确成功字节

旧 **1202/12B/status32@+8**经 `1ada60..6c`映射内部 **0296**；公共转换 `1adbd4`对2001分支读取旧+8，并在 **1adcda..de OR 590000**。reply TBH基址 **1ac4ce**、0296槽 **1ac5b0→1ac714**，`1ac71a`调用 **5c9b4e**。该完成器写1152/12/8001，**5c9b8e原样写status，没有590000→0分支**，最后`1aef1c`按原关联目标发送，metadata source92840747（`1aef68..72`）。

| 条件 | AP OSAL payload | AP本地结果 |
|---|---|---|
| 软件后端配置接受 / 原旧status0外形 | **`0d2052110c00018000005900`** | 0 |
| 原Validate拒绝，旧status1 | `0d2052110c00018001005900` | 6a |
| 原device结果错误，旧status5 | `0d2052110c00018005005900` | 6e |
| bridge旧请求发送失败−1 | `0d2052110c000180ffffffff` | 69 |

成功四个LE16为`200d/1152/000c/8001`，末LE32为00590000。这与0165保留状态域的形式一致，与011a/0119归零完成器不同，**本结论独立重读0152原完成器得出**。（CP `5c9b6c..94`；AP `2de4574..4810`；没有本次1152实际被AP消费的回执。）

## 6. 无live view的最小诚实软件合同与拒绝集

以下是脚本中可验证的纯软件合同，**未安装runtime实现**。限定 `headless_peaking_config` 后端、单一已归属原请求lease、destination92840747、完整16B捕获值；运行时source必须从当前请求metadata与其lease核对，`81cf61c2`只作本次证据。先stage完整8B配置（包括关闭值0、level1、magnification0与颜色三字节），记录 `software_config_accepted=true`、`pending_hardware=true`，返回上述12B。不得合成f026硬件结果、sensor帧、active peaking/overlay或OSD6003/6005通知。（软件选择建立在 `60fbd8`的真实配置保存与`5c9b4e`的原回复外形上；并不宣称执行了原device分支。）

实际adapter还须：分配自己的reply，metadata source92840747，投给**本次**request source；send成功后提交shadow，失败回滚stage、释放自有reply并保留错误。原request所有权不转移；已交付reply由AP `2de7320`自然释放。重复指针、并发重入、失去lease、source不符、分配/发送失败都不得报告成功。软件状态接受与硬件pending的两层含义必须进入marker，不能清掉pending来声称原CP完成。（CP `1abb78..80、1aef1c..ef7c`；AP `2de7304..20`。）

脚本验证 **22项拒绝**且拒绝后state不变：8个payload字节分别改变、截短、附加字节、8个header字节分别改变、错误目的、缺source、缺lease、非指定软件profile。它故意拒绝原CPValidate可能容许的其他selector/level/magnification/颜色/开关组合；未审计的功能和硬件状态不能从Validate宽松性推出。（原Validate边界 `5f7f06..34`；原字段消费 `1b52f4..5336、1e0ecc..de`；实现见proof.software_contract。）

## 7. 重建与未证实项

在Mac项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/vdf0152-peaking/audit_vdf0152.py
```

退出0重建相邻proof：固定AP SHA256 `545c5053…8290f`、CP `c90d00d8…6bcba`；44项关键指令、3处TBH映射、2类RTTI/虚表、subsystem槽、selector及magnification/level表、四次完整请求/原栈、AP83末次接收snapshot和22项拒绝全部核对。参数如 `AP:2de9de4:3f4 CP:5c9b4e:52`只读输出反汇编，不写proof。脚本仅写自己的proof并先核卷UUID，不执行前序审计的重建入口。

未证实：原CP完整event/完成mask生命周期的动态执行；原device模式/selector的运行值、实际sensor和peaking像素效果；selector各bit、level/magnification原UI枚举名称；底层OSAL−1取消/异常返回与全局关联规则；wrapper前AP输入结构readback；软件回复被原AP消费及业务自然完成；菜单、下一帧、按键与正常待机。**回0152至多解除一个独立业务等待，不构成OSD上一帧消费完成或菜单验收。**（CP `5f7f90..803c、5ff8d2..9be`；AP `2de7300、2d95a14`；serial **48576–48584**；独立OSD闸门见[post-clear-idle](../post-clear-idle/README.md)的Obj `f2210、f2448、f22f0`。）

本轮联网核对[Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)的`Cs`/`disasm`用法（2026-11-02）；它只支持工具方法，Sony协议语义均来自上述本地原件VA与serial证据。只读静态和纯软件合同通过，不充guest/CP运行、live view、可操作菜单或实机验收。
