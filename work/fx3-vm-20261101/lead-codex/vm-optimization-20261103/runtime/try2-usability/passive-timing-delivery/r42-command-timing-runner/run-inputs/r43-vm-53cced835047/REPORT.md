# r43｜单次 FX3 菜单与 command 计时实测

**结果 failed：1 accepted、0 fixed snapshot、0 confirm，完整八步未通过。** 唯一 VM/Start 已结束；原回收协议及重复清理审计通过。诊断取得真实 entry 字段与有效阶段边界，不能将诊断成功改写为菜单通过或性能改善。

任务 `task_53cced835047` / `ctx_68625e416216`，工作会话 `orca_session_id:ed9ac183-dba5-46e8-b048-66c231e722b0`。本目录为唯一手工输出；原 runner 自然输出为 [v41timing-n64-r42-0f6139b2](../../../../runs/v41timing-n64-r42-0f6139b2/)。未写协调 ledger、旧 run、冻结源码或部署入口，未执行 FX6、相机、USB、SD 或刷写操作，未第二次 Start。

## 准入与实际平台

卷 UUID 正确，启动前双锁空闲且无冲突 runner/QEMU。r42 runner 84 项、package 30 项交付清单及 SOURCE43/CORE38 全部核对通过；包、源码清单、candidate、CPIO 和 GPE body/padded-slot 摘要匹配本派发 pins，CPIO 453213884B；129600B 新 body 加147384B零尾位于原276984B槽。成员名仍为 `simulation/fx3-gpe-observe-v7.so`，实际是 v26/backendv9+r41 入口观察候选。

按 prepare → 原完整 preflight → launch_prepare → start_and_wait 执行。`INPUTS-BEFORE/AFTER.json` 保留原输入协议：38/2/1/594/1/151/40/145/14/1 项分组，没有把旧离线测试矩阵重跑成新验收。当前 guarded runner import 七模块及既有实际40模块路径映射的当前 hash 核对分别留存；本轮28份运行源快照再核一致。读取前、原 preflight、随后 import/源码快照观测口径分别保留。

`ACTUAL-RUNNING-ARGV.json` 是运行中 PID99290 的实际 ps argv，核对了原 QEMU、kernel、DTB路径和新 r42 CPIO：4×cortex-a35、5120MiB、`tcg,thread=multi`，无 icount。`RUNNER-LAUNCH.json` 保存准确八分钟/32容量/N64/pre-input-step2/snapshot-tail/diagnostic argv；操作预算仍8accepted/10attempt/2恢复，没有放宽原20秒。

Start前读取 agent-browser 当前技能和 Node 工具说明，预载本 r42 `short_tool.mjs.bind(绝对独占runDir)` 到 globalThis，独立下一调用验证函数存在，并实际看到明确标为历史样本的PNG。一次准备调用错误导入被工具禁止的 node:process，发生于任何Start前，随后改用继承环境的 env executable；图像验证成功后才启动。每个菜单动作分别一次 Node调用、当次UUID返回、完整child原文和PNG；未从截断stdout或旧current-return补成功。启动等待外层工具300秒容纳原180秒启动及原失败回收，不改变任何 guest/按键期限；实际约47秒完成。

## 实际图像与失败边界

首个被保留 `evaluation_complete=true/qualified=true` 为Start后46.623秒，初始截图校验完成47.064秒。初始实际图像仅黑底橙色NO CARD，无菜单/对话框，独立 standby_review 如实记录；后续恢复新图已出现HD、Fixed59.94fps、AF-C、AWB等完整待机图标。

第1步第一次 planned click 是 PAGE 明确 `not_posted` / `preflight_identity_or_lifecycle_changed`、`mutation_called=false`，不是未知投递；服务端拒绝导出总数为0。按冻结链实际看取消前合格恢复图 → 独立 recovery_cancel → 实际看取消后新图 → 独立 recovery_review → 新nonce planned click；只用本步一次恢复。第一次alarm于11.9663秒取消，未向guest多发一键；没有捏造HTTP拒绝字节，原拒绝导出及HAR保留。

第二次 MENU 被接收，native 原文有一组 down/up/done，按住实测108.139008ms。第1张未固定图在arm+5.0054至5.0834秒取样，Setup>Area/Date菜单仍是过渡图，Area/Date/Time Setting尚未橙色选中；没有pin或confirm。第2张明确observe在+17.4869至17.5581秒取样，实际可见完整Setup>Area/Date 45/59，橙色Area/Date/Time Setting、Language English、NTSC/PAL和底部Page/Close；仍是未固定观察图，当时原deadline剩约2.4419秒。

alarm于+20.0031秒自动原End。下一独立pin入口在arm后约33.486秒，`postkey_flow.before_pin` 的owned-page guard失败，`pin_attempted=false`，尚未调用实际snapshot capture；没有新固定PNG、repin或confirm。工具往返/模型审阅/调度链未能在20秒内完成，不能由此判固件绘图超时；各自耗时无法拆分。完整child stderr和当次返回失败回执保留，随后立即明确调用原cleanup，未再按键。

| 项目 | 结果 |
|---|---|
| 明确 attempts / 恢复 / native accepted | 2 / 1 / 1 |
| 第1步目标完整观察 | 看过，但未固定、未确认，不计通过 |
| 第1步 fixed snapshot / confirm | 0 / 0，失败 |
| 第2–8步 | 未执行 |
| 完整八步 | failed |

详见 [VISUAL-AND-DEADLINE.json](VISUAL-AND-DEADLINE.json)、`step-01-attempt-01/02/`、各 `tool-return-UUID/`。模型收图、思考及调度时间保持unknown；无自动语义判断、稳定SHA判通过或自动confirm。协调器另行实际看过第2图，独立核对见 [COORDINATOR-OBSERVATIONS.json](COORDINATOR-OBSERVATIONS.json)：其同host域ring604记录早于文件写入/HTTP publish；不能称为浏览器准确可见时刻，其guest keyup→frame603 commit约4.590070秒也不能据此将与r38的差异归因r41。

## 回收

原 End 后runtime报告137.830秒，小于480秒。首次有效cleanup `5f9a1b44-c55e-4fd6-bc38-2adae0ced8e8` 状态completed；第二次明确cleanup `e5754610-6e73-4763-86cb-82f453300c57` 状态already-cleaned，均独占留存stdout/stderr/process/HAR/PNG/manifest/身份；没有覆盖首次完成引用。`CLEANUP-AUDIT.json` 和原audit_after均通过，原输入前后hash保持。

API16原字节 `000b00b4fd7bbba9fd030091f35301a9` 与guest ACK双证通过，原20秒内1.298489秒完成。QMP quit request/ACK id541；QEMU exit0并reap，runner99042/QEMU99290不存在、双锁free、端口60752关闭；网页finalACK acknowledged。独占browser close成功、session inactive、background PID99062不存在。未在运行中独立枚举并绑定每个Chromium child PID，因此逐个子进程PID身份/absence保持unknown；不以他人Chrome会话冒充本轮证据。原回收协议完成与此额外细粒度边界分开表述，均不能改变菜单failed。

## 离线计时

先核 [BOUNDARIES.json](BOUNDARIES.json)：startup-observation schema正确、saved/flush成功、errors为空、ready_incomplete=null；headers/ready/phases容量均未溢出、first_kind_omitted=0、evicted_transitions=0，全部offset在范围内。header读取294次：bad_magic101、valid_seq0 1、valid_positive192；request-ID、原始header、拒绝类型、14个首marker及谓词true/false/not_evaluated均在原文件。串口2078 chunks /11996148B，carry42B；边界均落完整换行后。

startup取ready.first_kinds首个完整qualified事件offset **3559883**；交互截止严格取phases.first_kinds首cleanup的 **11965472**，没有替换成较晚 `serial_bytes_before_cleanup=11969341` 或最终11996148。清理尾30676B单列，不用尾部画面补启动。

封存r41 parser hash核对后，按准确 `serial --run-id v41timing-n64-r42-0f6139b2 --cutoff-byte <整数> --output <本轮新文件>` 运行。startup、precleanup以及明确标为含清理的全文件回放分别保存原参数/输出；统计只引用合法边界。按本轮host_launch_uuid、guest PID237、唯一观测的原GPE LIB_BIND base0x7f6c22d000、TID278/tpidr0x7f3cfff720及序列0..580绑定，没有跨run/重载拼接。命令行本身不含library base；库归属是本轮单次绑定、固定包及线程/序列的证据关联，不能推广到未观察实例。

| 阶段 | command记录 / unknown | 已知duration数；中位数 / p95 / 最大 | 段内已知gap数；中位数 / p95 / 最大 |
|---|---:|---|---|
| startup [0,3559883) | 82 / 8 | 74；15.481 /33.903008 /55.217008ms | 66；2.977992 /170.022992 /550.846992ms |
| ready后至首cleanup [3559883,11965472) | 499 /54 | 445；11.678 /36.611008 /121.418ms | 393；2.908 /630.744 /1876.966ms |
| cleanup-tail | 0 /0 | 无 | 无 |

完整precleanup为581条，519 known durations、460 known相邻gap，62条malformed/interleaved仍unknown；分段另排除1个跨startup边界gap。原始坏行字节、offset、间隔阻断与未知原因见 [SERIAL-EVIDENCE.json](SERIAL-EVIDENCE.json) 和 [TIMING-SUMMARY.json](TIMING-SUMMARY.json)。串口完全缺失的事件数未知，不把未检测到错误或tail快照当无丢失证明。r35冻结解析器另有2个完整导出、0个格式unknown；仅是当条log时普通BSS collector/publication/bind观察，不是End全局状态或完整7条采集证明。

时间含义仅限guest CLOCK_MONOTONIC：entry→原return标记包含适配器执行、锁/验证/绘图/完成调用及调度，非CPU或进入适配器前FIFO排队；返回标记早于格式化、串口完成和实际函数返回。连续同线程return→entry仍可含日志尾、原Main、调度、未观察活动，非纯FIFO空闲。无guest/host/browser强减。接口含义复核自[Linux man-pages clock_gettime](https://man7.org/linux/man-pages/man3/clock_gettime.3.html)，实际clock id仍以冻结源码为准。

本轮没有提速、零帧根因、60分钟、4096键、全菜单、录像、实机或FX6结论；r38失败和缺entry的历史不能补算。后续若继续菜单验收需独立新授权，本轮已结束。

## 交付索引

- [RESULT.json](RESULT.json)：任务最终failed、步骤/回收/边界与身份。
- [VISUAL-AND-DEADLINE.json](VISUAL-AND-DEADLINE.json)、`tool-return-*/`、`step-01-attempt-*/`：真实图像、动作和期限链。
- [BOUNDARIES.json](BOUNDARIES.json)、[TIMING-SUMMARY.json](TIMING-SUMMARY.json)、`COMMAND-TIMING-*.json`：只读计时解析；[analyze_r43.py](analyze_r43.py)只导出本轮分析，无控制VM/browser代码。
- [CLEANUP-COMPLETED.json](CLEANUP-COMPLETED.json)、`cleanup-calls/`、`cleanup-dispatches/`：首次有效及幂等回收原证据。
- [R43-PINS-AFTER.json](R43-PINS-AFTER.json)、[NATIVE-SHA256SUMS](NATIVE-SHA256SUMS)、[SHA256SUMS](SHA256SUMS)：冻结输入复核及完整本轮证据封存；哈希文件不含自身。
