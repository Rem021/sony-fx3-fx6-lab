# FX3 OSD 发布、读租约与 6003/6005 完成通知审计

**部分闭合；未达到“FX3 原厂完整完成生命周期”的全部验收。** 已逐字节恢复 AP 的 1002/1003/1005 发布、实际 token 来源、bank/bitmap 身份及可用于快照的原读锁，确认 AP 的 6003/6005 回调不校验帧 ID、generation、状态或 payload 长度。指定 CP 入口 `4b3628→4b36fc` 的后级只处理 2000/2001/2002，收到字面 1003/1005 会直接返回；没有从这条边恢复出扫描提交或 6003/6005 原厂发送端。因此 **6003/6005 的原厂长度、完整 raw、状态值与 VSYNC 时序仍未证实**，不能交付一个冒充原格式的 ACK。（CP `4b3632..36aa、4b371c..3732、4b3874..387a`；Obj `f22f0..2310、f2238..22ec`。）

2026-11-02，只读原 CP/AP、指定公共上下文、三个前审计及现有本地 A7C2 参考；只写本目录三个文件。未启动 QEMU、连接 QMP、改 runtime/STATE/锁/原件/Git 或访问相机。A=本地原字节直接证据；B=明确约束下的推断；U=尚无证据。CP VA 的文件偏移为 `VA−108000`，Obj VA 为 `libObj.so` image VA；下面所有固件结论均给出 VA，完整 raw 与逐指令反汇编见 [proof](osd-completion-proof.json) 的 `blocks`。

## 重建

在 Mac 项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/osd-completion-6003/audit_osd_completion.py
```

退出 0 重建相邻 proof：两份原二进制的 SHA256、全部选定指令区间、45 项精确指令断言、ELF 重定位恢复的 bitmap 虚表、逐字节字段覆盖检查、参考源 SHA，以及独立的未知项。脚本的 PASS 仅表示这份静态证明重建成功，**不表示 factory ACK schema 已闭合**。辅助只读查询：`.../audit_osd_completion.py cp 4b36fc 180`、`... libObj.so f2238 b8`；不会运行其他审计的 rebuild。

方法核对 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html)。本轮固定 GitHub blob 读取失败（cache miss）；A7C2 比较使用下述本地已有源码，没有下载替代二进制或执行它。Sony 语义全部来自本地固件，网页不是其证据。

## 1. AP 发布的精确字节与来源

`f2fa0` 的非零分支先 `f2ffc→f33d0` 换 on/off 指针，再读 `f3374` token、`f3414` 几何/格式、`f3368` bitmap，封为 40B **本地** msg1。`f2428` 在 `f2448` wait ExternalOSDIF 对象+48 的发布闸门；`f24fc` 向自身队列 8288076c 发送。`f2638` 消费 msg1，先发 1002，再发 1003 或 1005。本地 msg1 不能直接当作 CP 36B 描述。（Obj `f2fa0..30a8、f2428..256c、f2638..27d4`。）

以下均为小端 **bare body**，source=`8288076c`。1002 目标 `8280074d`，12B，构造器清零全部字节再写 ID/next：

```text
完整更新：02 10 00 00 00 00 00 00 03 10 00 00
元数据更新：02 10 00 00 00 00 00 00 05 10 00 00
```

1002 没有帧 ID、generation、状态或内嵌长度；它只声明随后要取哪类更新。（Obj `f1d90..1e18、f268c..2698、f2770..277c`。）

1003 目标 `8280084d`，36B，构造器清零后逐字段写入：

| body 偏移，字节范围 | 编码与意义 | 原证据 |
|---|---|---|
| +00，00..01 | u16 `1003` | `f1e94..1e98` |
| +02，02..07 | 6 字节零 | `f1e68..1e78` |
| +08，08..0b | u32 共享元数据地址 token；见下文，不能称递增帧号 | `f26e4..26ec、f3374..337c、f3194..3198` |
| +0c，0c..0f | u32 常量 1 | `f26f0..26f4` |
| +10，10..11 | u16 `(framebuffer 原格式枚举 == 2)`；**不是原格式枚举本身** | `f26f8..2708` |
| +12，12..13 | 2 字节零 | `f1e68..1e78` |
| +14，14..15 | u16 画布宽 | `f3024..3034、f2718` |
| +16，16..17 | u16 画布高 | `f3030..3038、f271c` |
| +18，18..19 | u16 更新矩形 x；本条普通发布分支为 0 | `f3050、f2734` |
| +1a，1a..1b | u16 更新矩形 y；本条普通发布分支为 0 | `f3054、f2738` |
| +1c，1c..1d | u16 更新矩形宽 | `f3044、f273c` |
| +1e，1e..1f | u16 更新矩形高 | `f303c、f2740` |
| +20，20..23 | u32 本地诊断/上下文字；正常分支为零，另一分支取 `fe38c` 返回值 | `f24d0..24f4、f2544..2554、f2744..274c` |

最后一项不是已证明的 CP 成功/失败 status，更没有 generation 意义。完整 fmt0、640×480 的**静态符号模板**为：

```text
03100000 00000000 TTTTTTTT 01000000 00000000 8002e001 00000000 8002e001 DDDDDDDD
```

`TTTTTTTT` 是本帧实际 token 的 4B LE，`DDDDDDDD` 是本帧诊断字，不能用 0 伪造未知 token。此模板不是运行实捕 raw；旧日志的 tag2 是 +4，不能据 tag2=0 认定 +8 token=0。1003 **没有** pixel physical64、stride、真实格式枚举、generation 或 bank 字段；这些必须在持锁情况下关联原对象，不能从 36B 凭空解码。（Obj `f1e1c..1ea4、f26e0..2750、f2fa0..305c`。）

1005 目标 `8280084e`，8B，精确为 `05 10 00 00 00 00 00 00`，source 同为 76c。它不携带新 token、几何或像素；“metadata 更新”是结合 GUI/config 与已保留像素来消费的解释，不表示收到 1005 就有新 framebuffer。实现须有本 epoch 已接受的完整帧，否则拒绝。（原字节 A：Obj `f1d04..1d8c、f2770..27d0`；保留像素策略为软件合同 B。）

### 1.1 token、物理地址和 bank 的实际关系

`f3374` 读当前 entry+10 的 **低 32 位**送往 1003+8。初始化 `f30ac` 中，每个 entry 经 `102394` 分配，`f3128→1028e0→103194` 取得 u32 allocation handle 到 entry+8；`f314c→10277c→102fd0` 得逻辑基址；`f3174→102718→102f58→102b98` 将逻辑地址按区间转换为物理地址，`f3194` 再加调用方 offset，`f3198` 保存完整结果到 entry+10。因此准确语义是 **low32(元数据 physical + caller offset)**，该 offset 的当前值本轮没有动态读回，禁止直接猜一个高 32 位还原地址。（Obj 上述 VA；`102b98..102bcc` 明确逻辑基址/物理基址/容量的区间换算。）

FX3 framebuffer 有两个 0x20 字节 entry，分别在 FB+18 / FB+38：entry+0 是 bitmap 对象，+8 是 allocation handle，+10 是上述元数据地址，+18 是独立像素物理地址。FB+60 指向当前/on entry，FB+68 指向另一 entry，`f33ec..33f0` 交换两者。尺寸/格式从 FB+8 的信息取得；不能把 0147 的 YUV layout bank 与这两个像素 bank 混用。**原消息没有 generation**，consumer 的本地 sequence/epoch 必须明确叫软件账本；bitmap object、allocation handle、地址、bank 和 epoch 都要一起核对，不能靠 32 位 token 防重用。（Obj `f30ac..31c8、f32c0..3328、f335c..337c、f33d0..3418、f3024..305c`；0147 边界见前审计。）

## 2. 指定 CP 消费入口的确切结果与缺口

CP `4b3628` 的断言串明确命名 `osdTrans::OsdTransferMsgCtrl::WaitAndExecuteUpdateExec`（串 `e156c8`，文件名 `4b36dc`）。输入 next=1003 时选 8280084d，1005 时选 8280084e；查询三个队列状态后，无限时接收，交 `4b36fc`，随后释放。上游 `a902b0` 从 Dataflow 逐 body 取消息，ID1002 时读 +8 调本函数。这解释“控制→选更新队列”的一部分，但尚未证明 bare 8280074d 注册/转入该 Dataflow wrapper 的完整桥。（CP `a902b0..90314、4b3632..36aa`。）

关键反例：后级 `4b36fc` 读 body ID，**只比较 2000、2001、2002**；字面 1003/1005 都在 `4b3732` 跳到 `4b3874` 返回，不读其几何/token，不扫描，不合成，也不发送完成包。所核对的 OSAL dequeue 快路径返回队列节点 body+18，没有在该快路径替换 body ID。（CP `4b3712..3732、4b3874..387a、49fa28..49fa3c`。）

2000 分支调用已注册的函数指针；2001 分支构造 7001 消息向 9281074e；2002 分支以对象中保存的 64 位地址查四段 extent，命中后作地址转换、取共享结构、可调用 callback。它们不能仅因相邻就当作已完成的 1003→scanout 链，尤其 `4b3736` 取的是对象地址，不是直接读 1003+8。（CP `4b3736..3776、4b3778..37fa、4b37fc..3882`。）

**本轮没有恢复 1003/1005→200x 转换或另一个消费者，也没有定位源为 8280074d、目的 8288076c 的 6003/6005 原厂发送器。** 这是指定分支的有界负结果，不是“整个 FX3 没有完成通知”的证明。扫描与合成提交、成功和拒绝路径、包分配长度/填充/status、完成与 VSYNC/fence 的因果边都保持 U；不能用 CP 其他日志码中出现的 6003 常量填补这个缺口。（CP `4b36fc..3882`；证明边界见 `CP_boundary/open_items`。）

## 3. AP 如何处理完成，是否检查帧身份

AP ExternalOSDIF 的 `f2820` 先经 Dataflow `GetReplyId/GetSrcId/GetMsgNum/GetMsg` 取 body：ReplyId 返回必须为 0 或 −30，GetSrcId 成功，GetMsg 成功。source 必须等于 `8280074d` 才进 `f22f0`；其他合法 source 有独立 handler。这里有**传输解析和 source 门控**，但没有完成 schema 的逐字段检查。（Obj `f2848..2864、f2880..28d8`。）

`f22f0` 只读 body+0 的 u16：6003→`f2238`，6005→`f22b0`，未知 ID assert。两回调均不读取 incoming payload：6003 在 `f2250` 已将 x1 改成栈地址，之后是本地 trace/时间状态处理，所有分支最后都到 `f2278`；6005 全函数不使用 x1。两者分别在 `f227c/f22cc→fd384→osal_sig_sem` 释放 ExternalOSDIF+48，随后调用非空 +50 callback 并清空。（Obj `f22f0..2338、f2238..22ec、fd384..fd3b8`。）

所以帧 ID、generation、status、请求是否仍 pending、重复/迟到 completion 都**不校验**；两条回调里也没有读取长度。底层 GetMsg 有自己的容量/解析规则，不能从回调无检查推导 OSAL 接受任意长度。AP 最少使用的前缀仅 `03 60` / `05 60`；它既不能证明厂包只有 2B，也不能证明厂包是 8B，后续 6 个零或 status0 都没有原发送端依据。（Obj `f28a8..28d8、f22f0..2310`。）

发送失败与消费者拒绝还须分开：AP 自己的 1002 send 返回失败，或 1003/1005 send 失败，会本地调用 `f2238/f22b0` 归还闸门；正常 send=0 不走该分支，而等异步完成。**拒绝/超时是否存在原 CP negative ACK 未证实**，不能仿造一个“错误 status”让 AP 释放。（Obj `f2698..26bc、f2750..276c、f277c..2794、f27b8..27d4`。）

## 4. 无头消费者最小诚实合同（设计，未实现）

原厂 completion schema 未证实，因此本合同的最终发送 gate 保持关闭。要实现“按原格式回”，还需先冻结该发送器分配/清零/字段 store、目的/source、实际 size/raw；**不存在已经可以给出的 FX3 原厂完整 6003/6005 hex**。下述顺序是可供 Lead 实现的受约束软件消费合同，不是 CP/面板等价声明。（依赖缺口：CP `4b3732→3874`；AP 信号影响：Obj `f227c/f22cc`。）

1. 先记录三个队列的 owner、pending 和启动 epoch，排除其他 consumer，不能重启后接旧包。保存 1000/1001/1004 的配置状态；source=76c、size=12、ID1002、next=1003/1005 才冻结该批配置。对同 source 的选定更新队列做有界等待，仅接受准确 36B/8B 和匹配 ID；token/epoch 仅本地配对，不能声称有 native generation。1005 还需本 epoch 保留完整帧。（原发布边界：Obj `f2638..27d4`；source/bare body 由 `f1d04..1ea4`。）
2. **先持原 FB 身份锁，再解析当前对象**：原顺序 `f3380` wait FB+88，再 FB+78；释放 `f33a8` 反向。OSAL ID 在 wrapper+8，故是 FB+90、FB+80。swap `f33d0` 遵守两锁；format 重建 `f3244` 遵守 FB+88。因此读者依同序持两锁可排除这两种身份变更。原 helper 用 timeout−1，不适用于“有界快照”；consumer 须针对核回的本对象 ID 调 `osal_wai_sem_tmo(id,0)`，总预算可配置，超时释放已持锁并拒绝，绝不操作 ExternalOSDIF+48 的发布闸门。（Obj `f3380..3400、f3244..3330、fd344..fd380`。）
3. 对实际 bitmap 验 vptr；本创建路径由 GOT261c50→vptr252670。AddRef 的槽 a8→`f0c80`；ReadLock 槽88→`f1174`，传 timeout=0 得 CPU bits；ReadUnlock 槽90→`f0f04`；Release wrapper `eeebc` 经槽 c8/b0。ReadLock 在 bitmap+38 mutex 下，无待写/写锁（+30/+34）才增加+2c；WriteLock `f1010` 检查读计数，读者存在时不写。这是生产者遵守的原读租约，**读取地址两次相等不构成租约**。（Obj `f12fc..130c、eee78..eef08、f0c80..cb4、f1174..12b0、f1010..1170、f0f04..f64`；虚表重定位在 proof。）
4. 持锁取原 bitmap 的 physical64、真实 format、row pixels 和 size，匹配 token→当前 bank→bitmap→活跃 allocation/extent。原接口 `GRM_bitmapGetPhysicalAddress fb594→eecf8→slot60 f0a64`；format slot50→`f0a3c`；row pixels `fb790→ef36c→slot30 f0e0c`；size `fb520→eec14`。不按 A7C2 地址范围或 token 高位补猜。所有物理别名/本轮软件 GPE writer 还须遵守同一 raster guard；**原 bitmap 读锁只证明互斥原 WriteLock，未证明现有软件物理写入器也遵守**，这项未核回前不能 ACK。（Obj 上述 VA；软件 writer guard 为接入条件，未实现。）
5. 只接受已验证格式/stride/尺寸与 extent。现存已观察例：type/handle545，extent `[43feb5000,43fff5000)`、size140000；pixels43feb5100，640×480，fmt0、stride640 pixels，span=614400B。此例来自前审计，不能替代本轮活跃身份。对 bpp=2/4，逐行验证 `span=((h−1)*stride+w)*bpp`、stride≥w、非零有界尺寸、不溢出且同一活跃 extent 完全包含；矩形 x+w/y+h 也校验。未知格式/alias/extent 拒绝；不从 0147 补参数。（来源前审计绑定 Obj `102b98、f16b0` 与 libgpe `c610/c61c/c664`；本轮没有新像素读回。）
6. 持所有租约/guard 做**一次有界 memcpy 到自有快照**并冻结配置、token、对象/handle、physical、format、stride、bank、软件 epoch/seq、hash。随后依逆序释放 raster、ReadUnlock、Release、FB+78、FB+88，核每个释放结果，再释放请求。PNG 编码/落盘可在自有快照上完成，无须占着生产者锁等待文件 I/O；导出明确 AP 软件像素/格式解释，颜色、alpha 和 CP composition 各有单独验收。（原租约释放：Obj `f0f04..f64、f33a8..33cc`；落盘时序为本软件合同。）
7. 仅在完整校验/复制/释放/持久化成功，且 **factory schema 另外闭合**后，分配其真实长度，逐字段按原格式，向 8288076c、source8280074d 发一次匹配 6003/6005。unknown schema、配对超时、拒绝、截图/PNG/释放失败均不 ACK；发送失败保留 pending ledger，禁止直接 sig_sem 或换 ID 猜重试。AP 不去重，正确 source 的迟到/双 ACK 可能释放新帧，所以只允许一个 inflight，并记录 ACK 入队/原回调消费/下一帧三个回执。（AP 不去重/信号：Obj `f22f0、f227c、f22cc`；原 source gate `f28c8..28d8`。）

### 完成节拍

未恢复 native VSYNC/fence→6003 的边，不能宣称固定 60Hz 或 30Hz 更接近 FX3。**就已证明的资源语义，软件 consumer 在本帧真实有界消费并归还租约后，事件驱动完成最直接**；PNG 文件提交可作为更强的软件消费准入。固定60/30Hz可作为单独标注的展示节流配置，但不是原厂时序。若后续证实面板退休/fence 才允许重用 bank，则软件 completion 应等软件呈现退休事件；当前不具备该证明。（Obj `f2448` 持发布闸门至 `f227c/f22cc`；CP `4b36fc` 尚未连接 VSYNC。）

## 5. 与 A7C2 一致和差异

现存源码在 `menu-repair-01/success-cases/source/runtime/analysis/headless-osd.c`，SHA256 `55c695ba7c85c719a0d0789d19c54cf45d411c54508c81e9df9c8ed020c7d582`；前回执标记 commit `b3d7c1fed349f1d918acc4259f1d2b3a7c52a500`。[固定上游入口](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/headless-osd.c)。`research/a7c2-latest/` 本身只有 README/在线回执，没有该 C 副本；本轮读取已有 success-cases 原地参考，没有复制/运行。

| 一致/差异 | 对照与边界 |
|---|---|
| 一致 | 1002 冻结批次→1003/1005、持租快照、释放后完成；A7 源149..226/284..365，FX3发布/锁 VA见第1、4节 |
| 一致 | A7 metadata复用 retained pixels，并明确 CP composition/panel 未实现；FX3 1005 原8B也不含新像素，不能叫新拍摄帧 |
| 差异 | A7 硬编码 format1、FB+68/+70、私有 manager/vptr；FX3 是 FB+60/+68，具体 bitmap vptr252670，1003+10只发格式==2布尔；FX3现有清屏 fmt0（Obj `f33ec、f2708、f12fc`） |
| 差异 | A7 把 token 命名 id；FX3本轮追到 `(translated metadata physical+caller offset)` 的低32位，不是独立 generation（Obj `f3174、f3194、f3378`） |
| 未可移植 | A7分配8B并 memset零、写6003/6005/source74d，这是 **A7软件模型选择**；FX3原发送器/长度/status未证实。AP两回调不读这些字节仅说明兼容前缀，不给8B原厂等价证明（Obj `f2238/f22b0`） |

## 6. 准入与后续准确入口

完整任务仍缺：①8280074d 注册及控制1002→CP wrapper；②bare1003/1005→200x或另一真正消费者；③扫描/合成提交和退休事件；④原6003/6005分配长度、逐字节字段/status/source/destination；⑤VSYNC/帧率关联；⑥活跃 token/bitmap/extent 与所有 writer 的共享租约；⑦同一 sem 对象、原回调消费、连续至少两帧/非黑菜单/按键反馈。原包完整 schema 未闭合前，不能把本报告转换成“已完成原厂生命周期”的运行补丁。（入口 CP `a902b0、4b3628、4b36fc`；AP `f2820、f2238/f22b0、f33d0、f3244、f1174`。）
