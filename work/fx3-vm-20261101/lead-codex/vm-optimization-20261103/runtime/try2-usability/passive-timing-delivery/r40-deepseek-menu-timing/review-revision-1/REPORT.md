# FX3｜DeepSeek菜单延迟分解（r40，只读）

**结论先行：r38 仍是 failed，不改判。** 本轮只分析原固件 r38 的 MENU 单键性能，不重试按键、不延长原 20 秒截止、不把“看到菜单”当作验收通过，也不涉及 FX6 实现。MENU 键（0x1ab）的原生 down/up/done 链成立；完整菜单内容（ring frame 200）在 guest `CLOCK_MONOTONIC` 70.286425 s 提交，距按键 up 接收 9.494934 s、距 down 接收 9.644837 s。在完成点序列上，9.494934 s 分布于三次 GPE 完成批次及其间完成间隔；由于日志只有完成侧标记，这不能作为 CPU 时间或因果归因，也不能排除间隔中已有命令在执行。最大动态队列调用 21.3 ms，最大 `SendDrawComp` 104.1 ms。主机侧原 20 秒 alarm 先到，pin 在 alarm 后 5.286 s 才进入；`obs1→obs2` 的 8.44 s 与 `obs2→pin` 的 11.59 s 是工具/调度空档，期间 guest 仍在推进，不能全部算作固件耗时。原始 20 秒截止没有放宽，r38 的“1 accepted / 0 pin / 0 confirm / 0 passed”保持不变。

**修订说明（review-revision-1）：** 本文件是 r40 初稿的修订；原 r40 封存文件未改。三项复核意见的处理、被删除的可执行建议、时钟措辞与 v1/v2 头绑定见 `REVISION-NOTES.md`，原报告到本修订的文本变化见 `REPORT.diff`。

---

## 1. 输入、只读边界与卷身份

- 外盘 `/Volumes/KAFU2T` 已挂载，`diskutil info` 读取卷 UUID 为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，与任务要求一致。
- 唯一写入目录为本次独占创建的 `.../passive-timing-delivery/r40-deepseek-menu-timing`（`mkdir` 成功，创建前不存在）。
- 未启动 VM/QEMU/浏览器/网页服务/QMP/guest，未做设备/USB/相机操作，未改 FX3 平台/默认入口，未运行任何现有项目模块；只运行本目录的纯文件分析脚本。未复制大镜像，只按 CPIO 成员偏移读取了 3 个成员切片做哈希/字符串核验。
- 输入分 4 组共 38 项：native run 9 项、host run 12 项、协调端 3 项、日志生产源码/绑定 14 项（含 `guest.cpio` 与 `source-index.json`）。输入前后 SHA256 清单逐项一致（`manifest_sha256 = e4db93f34d05c6c76740507ccb8b926eb8a6c5f6ec7242f15c16f4bd5b39b9f9`，38/38）。`guest.cpio` 453213884 B，SHA256 `49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff`，与 r36 `MANIFEST.json` 声明一致。
- 原始输入只读；读写前后清单见 `input-manifest-before.json` / `input-manifest-after.json`。

## 2. 时钟域、可用锚点与误差

**先给规则：guest `ns` 只在 guest `CLOCK_MONOTONIC` 内相减；内核 printk 的 `[N]` 不是同一域，未用于任何减法；host monotonic 与 guest 只分别列出，不建立确定的 guest↔host 换算，主要结论只用同域量。**

| 域 | 证据（源码/原件） | 用途 | 误差/限制 |
|---|---|---|---|
| G：guest `CLOCK_MONOTONIC`（id=1） | `fx3-gpe-command-wait102-v1.h:11` `gpe102_now()` 用 `GPE102_CLOCK_MONOTONIC=1`；`fx3-complete104-observe-v1.h:11,17,23,30` 的 `ns` 均来自它；`fx3-osd-r35.c:26` `timing_ns()` 用 `clock_gettime(1)`，`:101` 打印 `clock_id=1`；`fx3-rm-empty-provider-v8-long-use-timing.c:12` `now()` 用 `clock_gettime(1)`，`:30` 打印 `clock_id=1`；`fx3-rm-key-gate-v6-long-use.inc:20` 的 `KEY95_STEP_DONE` 用 `now()` | GPE104/GPE102/KEY95/KEY96/OSD102 的 `ns` | 同一域内相减；分辨率来自 guest 时钟，未单独标定 |
| K：guest 内核 printk `[N]` | 本任务未取得可核对的 printk 生产源码 | 仅按 serial 行序判断先后 | 与 G **不是**同一域：17 个同字节行共存点近似为 `K ≈ 31.25×G + 10.79 s`，残差 σ≈0.13 s；只说明不能把 K 当秒，不能用于换算（成因未知） |
| H：host monotonic（`mach`/`time.monotonic`） | `osd-ring-readback.json` 的 `host_monotonic`；`tool-timeline.jsonl` 的 `host_ns` | 主机动作、ring 读回、工具空档 | 与 G 的逐帧差值 `d_i = H - G` 仅作记录：448200.871482 / 448200.852545 / 448200.772584 s；其 0.0989 s 变化是**差值变化**，不是 ring 读回延迟。条件区间 `[448200.588875, 448200.772584]` 仅当假定 H-G 恒定、斜率 1 且因果锚点成立时才是条件性的，**未校准，不用于换算/结论** |
| B：browser `performance_ms` | observation JSON 的 arm/due/observed 区间、`documentTimeOrigin` | arm、20 s alarm、两次观察窗 | 用 arm 的 wall UTC 在 host timeline 上线性插值：arm host = 448261.080321 s，插值括号 0.068 s；只用于主机窗口对照 |
| U：UTC | tool timeline 的 `UTC`、观察 JSON 的 wall UTC | 交叉核对 | 只用插值，不作为固件时钟 |
| UI 内部 clock 7 | `fx3-ui-r35.c:33` `now()` 用 `clock_gettime(7)`（BOOTTIME） | 仅内部状态，不进入本报告时间减法 | 本报告未使用 |

可用锚点及误差：

1. **帧对差值（G 与 H 独立列）**：frame 198/199/200 的 guest commit `ns` 与 ring `host_monotonic` 的差值分别为 448200.871482、448200.852545、448200.772584 s。三者跨度 0.0989 s 只说明这三个差值之间的散布；差值本身包含未知的跨域偏移与读回延迟，**不能**说“ring 读回延迟稳定在 0.1 s 量级”。
2. **按键差值**：host `sent_monotonic=448261.230463375` 减去 guest down 接收 `60.641588 s` 得 448200.588875 s；该值同样受传输/调度影响，只能作为一条条件性观察，不是校准。
3. 因此本报告**不建立** `H = G + 常数` 的确定映射；`[448200.588875, 448200.772584] s` 仅是“恒定偏移/斜率 1/因果锚点成立”前提下的条件区间，不用于把 guest ns 变成 host 秒或反之。主要结论分别使用 guest 同域量和 host 同域量。
4. browser arm 的 host 时刻 448261.080321 s 由 wall UTC 在 host timeline 上插值得到（括号 0.068 s）；alarm 的 host 时刻由 `original_alarm_End_elapsed_ms=20001.4` 得 448281.081721 s；两者之差即 20.0014 s，未被本轮修改。

## 3. key 与 GPE 标签语义（从生产源码与实际 CPIO 成员核验）

### 3.1 实际日志生产者的绑定

- GPE observer 的实际 CPIO 成员 `simulation/fx3-gpe-observe-v7.so`：276984 B，SHA256 `30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`，与 r33 `GPE-SOURCE-BINDING.json` 的 `actual_helper_sha256` 以及 `fx3-gpe-observe-v26-perf-ap105.so` 一致；该源码 `fx3-gpe-observe-v26-perf.c` 的 SHA256 `06f6d296...` 与绑定中的 expected 一致，`cache-v26.inc`、`resource-v26.inc` 也匹配。成员切片内实见 `FX3_GPE104_CMD_RETURN`、`FX3_GPE_NATIVE_TARGET`、`FX3_GPE_CMD op=`、`FX3_GPE_DRAW_INTERVAL` 字符串。该成员内嵌源码路径字符串 `menu-repair-01/runtime/helpers/fx3-complete104-observe-v1.h`，且未出现 `fx3-complete104-observe-v2-profile104.h`、`P104`/`pr104`/`profile104` 标记；因此实际绑定的是 **v1** 头，不是 v2-profile104。v2 文件存在但未被该成员引用。
- 按键 provider 的实际成员名为历史槽位 `simulation/fx3-rm-empty-provider-v3-setup.so`：57600 B，SHA256 `ff38874e128d517147b1712588bf68d24412dae781a390eaa8bd7d230c3c1707`，与 `mss-all-key-contrast/passive-timing-next/build/rm-timing.so` 完全一致；后者由 `fx3-rm-empty-provider-v8-long-use-timing.c`（SHA256 `7467449b...`，与 `source-receipt.json` 的 candidate 一致）构建。成员切片内实见 `wait_enter_ns`、`FX3_KEY95_STEP_DONE`、`FX3_KEY96_POLL`、`clock_id=1`。**成员名是历史槽位名，不能按名字推断内容**，以上以哈希+字符串为准。
- OSD 的实际成员 `simulation/fx3-osd-headless-v5.so`：109000 B，SHA256 `7adfef8f...`，切片内实见 `FX3_OSD102_COMMIT`、`clock_id=1`；其用户态时钟函数来自 r35 源码 `fx3-osd-r35.c:26`。

### 3.2 标签语义表

| 标签 | 生产者/语义（源码） | 时间字段 | 配对键 | 本报告用法 |
|---|---|---|---|---|
| `FX3_GPE_CMD`、`GPE_SCOPE`、`GPE_DRAW_INTERVAL`、`GPE_RAW_PARAMS` | `fx3-gpe-observe-v26-perf.c:159,253,254`；在 `command()` 完成侧打印；`seq` 是固件调用参数，不是观察器计数器 | **无 ns/tid** | `seq` + 行序 | 只用于 op/seq/形状与完成侧语义，不用其自身做时间 |
| `FX3_GPE104_CMD_RETURN` | `fx3-complete104-observe-v1.h:30`；`command()` 末尾 `:284` 调用；原 Main 返回后的适配器返回 | `ns=gpe102_now()`，`tid` | `tid`+`seq`+`op`+行序（**无 event id**） | 作为该 seq 的 guest 完成时刻；与 `GPE_CMD` 同 seq 一一配对 |
| `FX3_GPE104_DYNAMIC_ENTER/RETURN` | 同头文件 `:22`；`osal_dynamic_id` 包装，flags 0x2a/0x4a 进入观察 | 两端 `ns`，共享 `event`（全局原子序号） | `event` | 成对算调用时长；不跨 event 猜 |
| `FX3_GPE104_COMPLETE_ENTER/RETURN` | 同头文件 `:16`；仅 `async=0` 且 `src!=0` 时调用原 `SendDrawComp` | 两端 `ns`，共享 `event`；`seq`/`op` | `event`；另核 `seq`/`tid` | 成对算 `SendDrawComp` 时长；`result=1` 非零，源码调用方按“非零=成功”处理（`:284` 的 `!gpe104_complete` 才失败） |
| `FX3_GPE104_CB_ENTER/RETURN` | 同头文件 `:8`；内联原回调 | 两端 `ns`，共享 `event` | `event` | 本轮未见该标签 |
| `FX3_OSD102_COMMIT` | `fx3-osd-r35.c:101`；OSD ring 提交 | `clock_id=1 ns`，`frame`、`pixel_source_seq`、`copied_GPE_last` | 自身 `frame`；与 `copied_GPE_last` 关联 GPE flush seq | 作为“该帧已提交到软件 ring”的 guest 时刻 |
| `FX3_KEY_INPUT_RECV` | `fx3-rm-empty-provider-v8-long-use-timing.c:30`；UI 线程 `osal_rcv_msg_tmo` 返回后打印 | `clock_id=1 wait_enter_ns/wait_return_ns` | `step`+`key`+`status` | down/up 的接收时刻 |
| `FX3_SYNTH_KEY` | 同文件 `key_send`；host gate 写入后的合成键发送 | `monotonic_ns`（`now()`） | `step`+`key`+`status` | 发送时刻；与 receive 分开陈述 |
| `FX3_KEY95_STEP_DONE` | `fx3-rm-key-gate-v6-long-use.inc:20` | `measured_down_up_ns`、`elapsed_ns` | `step`+`key` | 只证明 one down/one up 与 hold 实测，不替代图像确认 |

按键语义：`trial-session.json` 的白名单明确 `0x1ab = MENU`；`KEY_INPUT_RECV` 的 `status=1` 为 down、`status=0` 为 up（源码把 `down` 参数原样写入 20B 消息，`key_send(...,1/0)` 成对）。本轮 `one_down_one_up=1`，`measured_down_up_ns=122838000`（122.838 ms），`requested_hold_ms=100`，`wait_result=0`；这是 host gate 的发送/保持语义，不是图像语义。

## 4. 方法与配对完整性

- serial 70468 个 Python 文本行、29525 条 FX3 记录；31 行出现多个 FX3 标签（内核行与用户 dprintf 交错），按标签起点切片，避免把后一个标签的字段读进前一个。
- GPE 命令：`GPE_CMD` 391 条、`CMD_RETURN` 391 条，seq 集合完全相等，范围 0–390，无重复、无缺失。其中 353 条 draw（`SCOPE`/`DRAW_INTERVAL`/`RAW_PARAMS` 各 353），38 条 Flush **恰好**没有 Scope（38 个 flush seq 与 38 条 `COMPLETE_ENTER` 的 seq 集合完全一致）。
- 104 事件：`DYNAMIC_ENTER/RETURN` 各 329 条，329 对全部按 `event` 配成，0 未配对、0 字段不一致；`COMPLETE_ENTER/RETURN` 各 38 条，38 对全部配成。两类 ENTER 的 event 并集为 367 个，恰好覆盖 1–367，无缺口、无重复。`CMD_RETURN` 无 event id，按 `tid`+`seq`+`op`+行序配对；391 条全部与同 seq 的 `GPE_CMD` 对上一一对应。
- 这些配对是“序号/事件/线程标识”的机械配对，不依赖中文名称或猜测。未配对/缺失为 0；但**命令起始时刻没有日志**，所以只能算完成间隔，不能算单条命令 CPU 时间。
- 不把重叠时间相加：动态队列调用、`SendDrawComp`、GPE 批次可能并行/嵌套，本报告只把同一 GPE 完成序列上的相邻完成点作为互斥分段；单次调用时长单列，不计入分段 walltime。

## 5. 实测分解（guest `CLOCK_MONOTONIC`）

### 5.1 MENU 键与本轮时间线

| 事件 | guest ns | 说明 |
|---|---:|---|
| MENU down 接收（UI 线程） | 60.641588000 | `KEY_INPUT_RECV status=1`；`wait_return_ns` |
| MENU down 发送（host gate） | 60.672946000 | `SYNTH_KEY status=1`；dprintf 在 send 之后，故可晚于接收 |
| MENU up 接收 | 60.791491008 | `KEY_INPUT_RECV status=0` |
| MENU up 发送 | 60.797203008 | `SYNTH_KEY status=0` |
| STEP_DONE | — | `measured_down_up_ns=122838000`，`elapsed_ns=160892992`，`one_down_one_up=1` |
| 首个变化帧 frame 198 提交 | 65.078217008 | 非待机像素，但无 PNG，**不能**仅凭哈希称“完整菜单” |
| 后续变化帧 frame 199 提交 | 67.860673008 | 另一版像素，语义未定 |
| 完整菜单 frame 200 提交 | 70.286425008 | 其 `PNG_sha256=60e9accc...` 与 obs2 画布一致；视觉上是完整 Setup > Area/Date |

关键差值：

- down 接收 → frame 198：**4.436629 s**；up 接收 → frame 198：**4.286726 s**。
- down 接收 → frame 200：**9.644837 s**；up 接收 → frame 200：**9.494934 s**。
- 因此“首帧变化”与“完整菜单”必须分开说；前者不能替代后者，后者也不能替代 pin/confirm。

### 5.2 从 up 接收到完整菜单的完成点分段（非 CPU/因果）

以下七段是 GPE **完成点**之间的互斥间隔；命令起始时刻未记录，不能把空档称为“无命令执行”，也不能把批次时长称为 CPU 时间。

| 段 | 区间/seq | 时长 | 占比 | 证据 |
|---|---|---:|---:|---|
| 首个 GPE 完成前空档 | up 60.791491 → seq 176 完成 62.688123 | **1.896632 s** | 20.0% | 期间没有记录到 GPE 命令完成（命令日志在完成侧，不能排除已在执行的长命令）；有 AP89 screen open/create 标记（60.84–61.32）与 3 次 MSS 队列标记（61.977–61.992），但其完整语义未证明 |
| 批次 A | seq 176–244 完成（62.688123→64.720493） | **2.032370 s** | 21.4% | 69 条命令：4 FillRect + 64 BitBlit + 1 Flush；中位完成间隔 24.4 ms |
| A→B 空档 | 64.720493→66.295142 | **1.574649 s** | 16.6% | 期间没有记录到新的 GPE 命令完成（不排除执行中的长命令）；不是把 A 的时长重复相加 |
| 批次 B | seq 245–314 完成（66.295142→67.555113） | **1.259971 s** | 13.3% | 70 条：4 FillRect + 65 BitBlit + 1 Flush；中位 16.7 ms |
| B→C 空档 | 67.555113→68.309768 | **0.754655 s** | 7.9% | 期间没有记录到新的 GPE 命令完成（不排除执行中的长命令） |
| 批次 C | seq 315–390 完成（68.309768→70.123367） | **1.813599 s** | 19.1% | 76 条：4 FillRect + 71 BitBlit + 1 Flush；中位 19.9 ms；max 179.8 ms（seq 349→350） |
| C flush → frame 200 提交 | 70.123367→70.286425 | **0.163058 s** | 1.7% | OSD ring commit 延迟（该段是 C 之后的单列项） |
| **合计** | up→frame 200 | **9.494934 s** | 100% | 七段严格闭合；未把动态/COMPLETE 时长另外加入 |

批次 A/B/C 的边界由三条 Flush（seq 244/314/390）确定；每次 Flush 后的 ring commit 延迟分别为 0.357724 s、0.305560 s、0.163058 s。frame 198 的 4.286726 s 恰好等于“pre 1.896632 + A 2.032370 + A flush→commit 0.357724”；完整菜单 9.494934 s 是上表七段之和。**这个分解只表示 GPE 完成侧的互斥分段，不是 CPU 时间，也不把并行线程的耗时重复累加。**

### 5.3 慢调用与“不是单点慢”

| 类型 | 数量 | 最大/最长 | 说明 |
|---|---:|---|---|
| `GPE104_DYNAMIC` 成对调用 | 329 对，0 未配对 | **21.273 ms**（event 170，tid 430，module 0x1cf） | 菜单窗口内最大仅约 15.3 ms；队列发送不是主因 |
| `SendDrawComp` 成对调用 | 38 对，0 未配对 | **104.066 ms**（seq 244，flush）；其次 93.418 ms（seq 58）、63.107 ms（seq 66） | 所有 `result=1`（源码调用方按非零成功）、`status=0`、`async=0`；仍不能替代视觉/confirm |
| GPE 命令完成间隔 | 390 个间隔 | 最大 **2.138303 s**（seq 175→176）、1.574649 s（244→245）、0.754655 s（314→315） | 这些是完成间隔，包含空档/等待；不能当单条命令执行时间 |
| `GPE102_LOCK_WAIT` | **0 条** | — | 本轮 serial 无该标签记录，无法判断锁竞争；不能写成“无锁竞争” |

所以从完成点看，时间分布在“三次完成批次 + 两段完成间隔 + 首段到首个完成”，不是某一个 100 ms 级调用；104 ms 的 flush 相对 9.49 s 只占约 1.1%。但“空档”只表示没有记录到完成，不能排除其中已有长命令在执行；这只是完成侧观测，不是 CPU 或因果归因。

### 5.4 ring 数据、首帧与重复提交

- ring 读回只保留 62 帧，最大 sequence 287；serial 的 OSD commit 为 1–289，故到 287 的读回缺 225 帧（53 个 gap，`missing_count` 合计 225），288/289 在快照之后。采样不是每帧，不能从 ring 推断逐帧耗时。
- frame 198/199/200 的像素哈希分别为 `221beb3a...` / `94c8742b...` / `7161e977...`，PNG 哈希分别为 `abc20e41...` / `e3be3632...` / `60e9accc...`；三者不同，说明至少三次内容变化。198/199 没有保留 PNG，**不能**把它们判成“完整菜单”。
- frame 200 的 `host_monotonic=448271.059008875`，`pixel_source_sequence=200`，`width=640`、`height=480`，`PNG_sha256=60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`；obs2 的 `displayed_frame.PNG_sha256` 也是该值，画布内容一致。
- frame 201–289 共 **89 次**提交全部 `pixel_source_seq=200`、`copied_GPE_last=390`，其中保留样本（201、207、211、216、220、223、229、234、238、247、251、257、263、269、275、281、283、284、286、287）PNG 哈希均为 `60e9accc...`；未保留帧没有逐帧哈希，但都指向同一 GPE 内容。快照内这些重复提交的中位间隔约 86 ms，说明完整菜单后仍在以约 10 Hz 重提交同一全帧。

## 6. 与 host 工具调用、首次保留菜单、20 秒截止对照

| 事件 | host monotonic (s) | 相对 arm | 依据 |
|---|---:|---:|---|
| Start 按钮进入 | 448199.093510 | — | tool timeline；本轮仅一次 Start |
| arm | 448261.080321（估计） | 0 | arm wall UTC 插值；performance 94010.7 ms |
| MENU 请求/发送 | 448261.174937 / 448261.230463 | +0.095 / +0.150 | `trial-input-events.jsonl` |
| obs1 窗口 | 448266.085→448266.163 | **+5.005→+5.083 s** | performance 99015.7–99093.2；实际显示 seq 197（待机） |
| frame 198 ring 读回 | 448265.949700 | **+4.869 s** | ring `host_monotonic`；比 obs1 截图早约 0.14–0.21 s |
| frame 199 ring 读回 | 448268.713218 | +7.633 s | ring |
| frame 200 ring 读回 | 448271.059009 | **+9.978 s** | ring；完整菜单内容 |
| obs2 窗口 | 448274.704→448274.760 | **+13.623→+13.680 s** | performance 107634.1–107690.7；显示 seq 220（before）/223（after），画布 hash 60e9... |
| 原 alarm 到期 | 448281.081721 | +20.0014 s | `RESULT.json` 的 `original_alarm_End_elapsed_ms` |
| pin 工具进入 | 448286.367999 | **+25.2877 s** | tool timeline；**alarm 后 5.286 s** |
| 首次 cleanup 进入 | 448286.419453 | +25.3391 s | tool timeline |

MENU down/up 接收的 guest ns（60.641588 / 60.791491）只列在 5.1；本表 host 相对 arm 的数字全部来自 host/browser 域，未把 guest ns 换算成 host。

**两次工具空档（协调端原口径）：**

- `click child end → observe child start` = **8.379532 s**（协调 `r38-coordinator-final-review.json` 的 `intercall_gaps`）；本任务 tool-stage 口径为 8.442112 s（click tool return prepared → observe2 entry），差约 0.06 s 是 child 进程边界与工具阶段边界的差异。该 host 空档内，ring 的 host 读回记录到 frame 198/199/200（448265.95/448268.71/448271.06）；guest 侧同段也完成了对应提交（两域分别陈述，不互相换算）。因此**不能**把 8.38 s 当固件耗时；它是“模型收图/审阅/调度”与 guest 进度的重叠。
- `observe child end → pin child start` = **11.531242 s**（协调口径）；tool-stage 口径 11.588929 s（observe2 return prepared → pin entry）。该空档从 obs2 结束（约 +13.68 s）跨过 +20.0 s deadline 到 pin 进入（+25.2877 s）；guest 侧记录显示该段只是重复提交同一 `pixel_source=200` 内容，没有新的菜单内容阶段（host 空档与 guest 提交分属两域，不互相换算）。故原 20 秒截止前 pin 未发生的主因是**主机侧调度空档**，不是这段时间的固件新增计算；但 r38 仍因未在 20 秒内完成 pin/confirm 而 failed，这个结论不变。

**首次保留菜单的边界：** 本轮没有 pin 成功的固定图；唯一保留的完整菜单画面是 observation-2 的历史未固定截图（页面 PNG SHA `339ae68e...`，画布 hash `60e9accc...`）。它不是 pin、不是 confirm、不是独立审阅快照。frame 200 是 ring 中的被动读回，属于软件 OSD 采样，不是原生 CP 合成层的像素因果证明（`CP_composition_panel_acceptance=false`）。obs1 在 +5.0 s 仍是待机，说明“+5 s 没有菜单”不等于“固件在 +5 s 还没开始画”：ring 在 +4.87 s 已有 frame 198，但浏览器到 +5.08 s 仍显示 seq 197，存在至少约 0.21 s 的发布/显示延迟，精确通道未知。

**20 秒对照：** 固件完整菜单提交在 up 后 9.495 s（down 后 9.645 s，guest 同域），按 guest 时钟早于 20 s；obs2 在 host 的 +13.62 s 也看到了完整菜单（host 域），距 deadline 还有约 6.34 s。两个数字分属不同域，不能相减或互相换算。但 pin 直到 +25.2877 s 才进入，晚于 deadline 5.286 s。**这只说明“原固件在单次运行中约 9.5 s 画出完整菜单”，不证明 20 秒内一定能完成 pin/confirm，也不允许放宽原 20 秒截止或自动语义通过。**

## 7. 归因分类：实测、调度、未知

| 类别 | 具体内容 | 数值 | 处理 |
|---|---|---|---|
| 实测（guest 同域） | 按键 down/up/done；frame 198/199/200 commit；三批次及其空档；动态/COMPLETE 单次调用 | 9.494934 s（up→frame200）；各段见 5.2 | 只做同域减法；分段互斥 |
| 主机调度空档 | click→obs2；obs2→pin；pin 晚于 deadline | 8.3795–8.4421 s；11.5312–11.5889 s；5.286 s | 与 guest 进度重叠，不计固件；不据此改 r38 |
| 未知/未证明 | 首个 GPE 完成前的 1.896632 s 内具体工作；A→B 1.574649 s、B→C 0.754655 s 的等待/工作比例；每条命令的起始时刻；为何是三次 flush/三版像素；kernel printk 时钟 31.25× 的成因；浏览器发布/合成延迟；CPU 时间 | — | 明确标 unknown，不用名称补语义 |

特别说明：5.2 的七段是 guest `CLOCK_MONOTONIC` 同域内的“完成点划分”间隔，互不重叠；动态和 COMPLETE 的时长是嵌套在其中的单次调用，**没有**再加到 9.494934 s 上。工具空档与 guest 进度是并行/重叠关系，也**没有**与固件分段相加。

## 8. 最多 3 个具体优化建议（本轮只给 2 条，不凑满）

**合同边界（不列为建议、不实施）：** 把第二次观察与 pin 合并、或预先绑定 pin，会消掉“观察图真实返回 → 独立视觉决定 → pin → 固定 PNG 再审 → 独立 confirm”的边界；它属于当前合同之外，本报告不实施，也不承诺可省 11.53 s。r27 短模板已明确每次只发起一个动作、不自动 pin/confirm；r37/r38 已使用预载与 +5 s 首观察，本报告不再把它们当新增方案。r27 的 12.773 s 只是单次历史回放，不是未来下界；成功 pin POST 尾段约 0.024–0.080 s，也不能与含前置等待的完整 capture 重复相加。

1. **guest 侧：为首个 GPE 完成前的 1.90 s 与两次批次间 1.57/0.75 s 增加“起始侧”标记（输入分发、screen open/create、presenter/队列调用），把等待与计算分开。** 依据：现有 GPE 日志只在完成侧打印，命令起始时刻完全缺失；1.896632 s 内仅见 screen open/create 与 MSS 队列标记，无法归因。该改动是测量而非改语义，先取得可归因数据，再决定是否优化；不改变原 20 秒截止、不自动判语义。
2. **guest 侧：核查三次全帧 flush 与完整菜单后 89 次同内容重提交，评估在不改变原生绘制语义的前提下合并/抑制重复提交。** 依据：frame 198/199/200 为三版不同像素，201–289 全部 `pixel_source_seq=200`（保留样本同 PNG 哈希，约 10 Hz 重提交）。这可能改善完整菜单后的持续开销和后续按键响应，但不保证缩短首菜单时间；必须新运行、保留独立视觉判断与 pin/confirm，不能自动通过。

以上 2 条都不改变原 20 秒截止，不重试本次按键，不把 r38 改成通过，也不涉及 FX6。

## 9. 未知、缺失与不可声称

- 单次运行，不能证明稳定性、全菜单、31/32 键、60 分钟、4096 键或 FX6 开机；本轮未启动 FX6，也未重试被提供方拒绝的实现。
- ring 采样非每帧（62/287，缺 225），没有 frame 198/199 的 PNG；不能逐帧断言菜单出现/消失时刻。
- 首次 HAR 被第二次 cleanup 覆盖、首次 browser PID 不可恢复（见 r38 REPORT/RESULT）；本报告不补造 HTTP 时序。
- 命令起始时刻、CPU 时间、内核 printk 时钟成因、浏览器合成/发布延迟均未知；`GPE102_LOCK_WAIT` 本轮无记录，不能推断锁竞争。
- `SendDrawComp` 的 `result=1` 按源码调用方语义是成功返回，但仍不是图像语义确认；`complete status=0` 也不能替代独立审阅。
- 不把 r38 的 failed 改判；不把 observation-2 的历史未固定图当作 pin/confirm；不把“看到菜单”当作八步通过。

## 10. 复算与交付

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r40-deepseek-menu-timing
python3 analyze_menu_timing.py manifest --out input-manifest-before.json
python3 analyze_menu_timing.py analyze --out results.json --data-dir data
python3 analyze_menu_timing.py manifest --out input-manifest-after.json
```

- `results.json`：完整机器可读结果（时钟域/锚点、key、MENU 分段、ring、host、慢调用、覆盖/未配对、归因、命令/动态/COMPLETE/OSD 全表）。
- `data/commands.csv`：391 条 GPE 命令（seq、op、完成 ns、间隔、scope/flush 标志、COMPLETE 时长）。
- `data/dynamic.csv`：329 对 104 动态调用；`data/complete.csv`：38 对 `SendDrawComp`；`data/osd-commits.csv`：289 条 OSD 提交；`data/ring-frames.csv`：196–205 的 ring 样本。
- `input-manifest-before.json` / `input-manifest-after.json`：38/38 输入前后 SHA256 一致，`manifest_sha256=e4db93f3...`。
- 交付哈希：`SHA256SUMS` 覆盖本报告、`results.json`、脚本、数据与两份输入清单；`SHA256SUMS.sha256` 给出 `SHA256SUMS` 自身的 SHA256（避免自指）。

**最终状态：r38 = failed（1 accepted / 0 pin / 0 confirm / 0 passed）；本轮只完成离线延迟分解，不改变验收结论。**
