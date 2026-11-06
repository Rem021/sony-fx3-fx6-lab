# FX3｜r38 r37诊断包单次真实八步验证

**failed。1 accepted / 1 attempt / 0 成功固定图 / 0 confirm / 0 通过步骤 / 0 recovery。** 第1步已实际看到完整菜单，但操作链没有在原20秒内完成固定与独立确认；原alarm先自动End，随后pin入口拒绝。第2至8步未执行。不能把看到菜单、原生接收、健康通过或捕获失败记为完整八步通过。

任务 `task_29076c7ba60e`，派发 `ctx_2ac7c24576fb`，worker `orca_session_id:74264f80-52fe-43e9-a13b-41ee69f50a6f`，独占browser session `fx3-deadline-r38-29076c7ba60e`。真实run为 [`v35diag-n64-r36-r37-4d245250`](../../../../runs/v35diag-n64-r36-r37-4d245250)，完整绝对路径见 [runtime.json](runtime.json)。仅一次真实VM/Start；无第二次Start、部署、FX6、相机、USB、SD或刷写操作；未写共享README或协调ledger。候选源码与平台保持原样。

## 实际启动、绑定与范围

卷UUID核对为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；Start前没有冲突runner/QEMU，双锁非阻塞probe空闲，未抢占或删锁。Mac目录不是Git仓库。prepare_run/preflight均指向本任务直属 `r37-diagnostic-runner-candidate/run-inputs/r38-vm-29076c7ba60e`，未沿用DEL顶层历史输出。

8个正式spec pins、172项交付、42项SOURCE、37项CORE核验匹配。1206项技术输入在本轮开始前及结束后真实计算hash/体积，1206/1206一致；实际preflight和原verify追加后检完成，未运行离线矩阵。r26、r27原目录未被执行或写入，但1206项集合不包括它们：本任务漏存这些旧目录的Start前独立快照；后检分别对历史manifest核对r26源1277/1277、r26 return169/169、r27 53/53匹配，**不能倒称取得本task前后快照**。该缺口见 [R26-R27-POSTRUN-MANIFEST-CHECK.json](R26-R27-POSTRUN-MANIFEST-CHECK.json)。

实际runner argv在 [RUNNER-LAUNCH.json](RUNNER-LAUNCH.json)，原始QEMU args在真实run的 `command.json`，运行中ps与QEMU hash在 [ACTUAL-RUNNING-ARGV.json](ACTUAL-RUNNING-ARGV.json)：

```text
python3 -B <r37>/run_trial_r24_review_snapshot.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2 --r35-diagnostic-package
```

实际label `v35diag-n64-r36-r37`；4×cortex-a35、5120MiB、`tcg,thread=multi`、无icount，kernel/DTB/QEMU摘要匹配正式spec。r36 candidate SHA `0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4`，CPIO 453213884B、SHA `49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff`。仅改变包选择，不声称零首帧根因已修复。

实际预检import-only确认runner、页面、ring reader、monitor日志、startup_observation来自r37，允许依赖来自r21，见 [ACTUAL-DEPENDENCY-BINDING.json](ACTUAL-DEPENDENCY-BINDING.json)。结束后另以拒绝process/socket的import-only复查24模块精确路径/hash，见 [POSTRUN-IMPORT-ONLY-24.json](POSTRUN-IMPORT-ONLY-24.json)；这是后检，不冒称运行进程内存中的模块dump。运行本身另保留 `observer-source/` 与receipt源摘要。

Node工具预载曾遇到 `process is not defined`、`node:process`不允许导入，均发生在Start前；改用既有child_process `/usr/bin/env`传递正确FX3_NAV_RUN_DIR，没有改冻结代码。最终`globalThis.r38one`绑定本r37的short_tool/bind，原cleanup函数同样绑定本runDir；下一独立调用确认两函数存在，并实际回传标明历史样本的旧PNG，见 [NODE-PRELOAD.json](NODE-PRELOAD.json)。历史图没有作为本轮待机。Start通过持久Node子进程调用原start_and_wait一次，输出完整保存 [START-TOOL-RESULT.json](START-TOOL-RESULT.json)。

## 真实画面与20秒时序

时间以原始证据时钟分别陈述，下表UTC均为2026-11-05；本机PT日期为11月4日。原runner持续84.572939秒；从原Start wrapper计时到本轮待机截图pass为47.369222秒，满足180秒。实际新待机图为 [initial-standby/current.png](initial-standby/current.png)，已看到NO CARD、HD Fixed-59.94fps、AF-C、AWB、±0.0；随后独立standby_review，未把历史样本充作待机。

| 事件 | UTC / 原浏览器计时 | 实际含义 |
| --- | --- | --- |
| 原Start点击 | 07:41:53.689685进入，53.724472返回 | 仅此一次Start |
| 首个保留完整qualified ready | host monotonic 448245490926416ns；offset 3625023 | 原ready谓词完成且qualified，非browser加载时刻 |
| 已保留browserLoaded轮询 | 07:42:40.975355进入 | ready=true、loaded=true；更早poll同名覆盖，精确首次loaded未知 |
| 新待机图完成 | 07:42:41.059244 | 实际图已回传并审阅 |
| 独立standby_review | 07:42:50.265411 | 本轮待机语义记录 |
| arm | 07:42:55.677Z，performance 94010.6ms | due=114010.6ms，不重置 |
| MENU唯一发送 | 请求host monotonic 448261.174936791；发送448261.230463375 | requestID与attempt均为910d2df6-61a2-42c0-8a9f-ee4fb35204ba |
| 首次观察 | performance 99015.7–99093.2ms，即arm+5005.1–5082.6ms | 实际完整browser图仍是NO CARD待机；没有假定画面hash变化等于菜单完成 |
| 第二次独立observe | performance 107634.1–107690.7ms，即arm+13623.5–13680.1ms | 实际看到Setup > Area/Date 45/59、Language English、橙色Area/Date/Time Setting、NTSC/PAL Selector与MENU Close |
| 原alarm自动End | 07:43:15.679Z；performance 114012.3ms | elapsed=20001.4ms，state=expired；没有延长20秒 |
| pin工具入口 | 07:43:20.964502 | 已在alarm后约5.286秒；原guard失败，未创建固定PNG，没有confirm |
| 首次原cleanup | 07:43:21.015978进入、21.576137完成 | 原operate失败分支自动调用；errors=[]、valid_nonarmed、runner absent、port closed |
| 下一明确原cleanup | 07:43:32.502868进入、34.182617完成 | 遵循未知回包下一调用cleanup要求；原页已关闭，产生身份/lastStatus错误，并覆盖部分同名文件 |

首次观察按原r28 arm+5000ms安排，记录not_before_satisfied=true；第二观察applied=false，没有重复5秒等待。仅两张未固定观察，无自动重试、恢复重发、repin或额外按键。两个PNG及完整原child stdout/stderr、全部tool-return UUID目录保留。[ACTION-TIMING-AND-IDENTITY.json](ACTION-TIMING-AND-IDENTITY.json)同时保留run/launch/document/timeOrigin/step/attempt/nonce、帧sequence/content_generation及浏览器区间。launch=`5a7528c6-0c8f-4959-a493-4453c3615131`，document=`c528cf74-a131-4af3-99c2-8ca537df6984`，timeOrigin=`1793864481666.3`，nonce=`1790e347-38d7-45f9-8943-331393f9d642`。不存在snapshot/confirm身份，不能补造。

click child结束至observe child开始有8.379532秒；observe child结束至pin child开始有11.531242秒。它们是实际墙钟间隙；模型收图、审阅、思考与工具调度无法拆分，分别均unknown。本轮可证的是实际操作链未在20秒内完成，不能据此认定原生固件菜单失败或宣布性能根因。

[第1张实际观察](step-01-attempt-01/observation-1/observation.png)仍待机；[第2张实际观察](step-01-attempt-01/observation-2/observation.png)菜单完整，但它是historical unpinned browser capture，不是固定审阅图。第1步failed_at_pin_after_deadline；第2 UP、3 C4、4 MENU、5 OK列表、6 MENU取消、7 MENU关闭、8 MENU重开均not_attempted。详细机器表在 [RESULT.json](RESULT.json)。

## 原生接收、结束与覆盖缺口

`trial-input-events.jsonl`保留唯一HTTP按键请求身份、门写入/读回与host时间；[NATIVE-DOWN-UP-DONE-EXACT.json](NATIVE-DOWN-UP-DONE-EXACT.json)导出serial原字节、offset及display：一条native status=1、一条status=0、两条原send result=0、一条STEP_DONE，one_down_one_up=1，measured_down_up_ns=122838000。guest ns是guest clock，不换算为host/browser时间；native接收与done不替代图像语义确认。

首次原清理链的关键结果成立，见 [CLEANUP-PROOF.json](CLEANUP-PROOF.json)：API16在20秒预算内1.534985秒取得guest restore_seen=1且末16B逐字节为 `000b00b4fd7bbba9fd030091f35301a9`；QMP quit id307有原return ACK，QEMU exit0、process_reaped=true、PID_absent=true，双锁释放；网页原 `trial-web-final-receipt.json` acknowledged=true、browser_ack。首次cleanup stdout原文完整保留在 `FAILURE-CLEANUP-DISPATCH.json`，不是从后续状态反推。[ended-page.png](ended-page.png)仍是首次cleanup图（mtime及append-only timeline可核），实际审阅显示“试用已结束：本轮健康检查通过，资源已回收”、按键1/32，固定对象finished；它没有证明八步成功。

**收尾证据不完整，不能把所有清理验收项统称全通过。** 第二cleanup重新进入已关闭browser文档，报owned_page_identity、lastStatus not defined、deadline专用tab不符；`CLEANUP.json`及多个同名process.json被第二次覆盖。这些错误不能倒推首次cleanup失败。第二次HAR-stop又把traffic.har覆盖为空220B、entries=[]；首次HAR-stop的exit0仅见append-only timeline，原全部HTTP记录已缺失，允许范围内没有恢复来源，未补造。首次End/ended-state/browser session info的完整过程返回也被覆盖；原browser精确PID现在unknown。首次终态PNG、runner finalACK、alarm状态JSON、首次cleanup聚合stdout和整个append-only timeline仍保留。原pin guard的具体browser stderr由冻结review_snapshot_cli内部丢弃，仅剩generic error；不能杜撰精确拒绝文本。

第二cleanup后独立只读检查：runner12067、QEMU12681、Start wrapper12671和第二browser daemon13745均absent，端口56971拒绝连接，双锁free，无专用session匹配进程；agent-browser最后session info active=false。见 [FINAL-RESOURCE-CHECK.json](FINAL-RESOURCE-CHECK.json)。没有再调用browser、cleanup或Start取证。[OVERWRITE-AND-MISSING-EVIDENCE.json](OVERWRITE-AND-MISSING-EVIDENCE.json)逐项列明保留与遗失；本次缺口不能由成功捕获失败代替通过。

拒绝导出原件在真实run `web-key-rejections.json`：304B，total=0、records=[]、truncated=0，SHA `ec33b49e36f1edf98af14fd018cea0b83d65bd53c18b27c427780d6b84ae1d07`。零拒绝也是原始导出结果，无未入队恢复。

## startup观测及r35分阶段读出

[STARTUP-OBSERVATION-VALIDATION.json](STARTUP-OBSERVATION-VALIDATION.json)校验原native `startup-observation.json`（21999B）：schema=`fx3-startup-observation-r30-v1`，file容量262144B、header recent48、ready32、phase8、每stream first-kind32；flush_attempted/saved均true，文件与receipt errors={}，无serialization_truncated，first_kind_omitted均0。175次header读取：bad_magic89、valid_seq0=2、valid_positive84；原请求id递增、读取前后host时间、raw16Q和原拒绝原因均保留。首次bad_magic读到16个零属于该次原头观测，不推广成系统状态。

14个白名单marker均有真实serial token byte offset和宿主首个完整token收到时间；逐一按serial原字节核验。比如SCREEN_OPEN offset1949676、host_received448229345717000ns，首个OSD102_COMMIT offset3073988、host_received448240223518250ns。这些是host已消费字节和收到时刻，不是guest发生时刻或全记录语义。原ready false/true/not_evaluated短路序列完整保留：初期replay false，之后screen false、ring false、quiet false，直到offset3625023全部13谓词true且evaluation_complete/qualified。后续phaseA_unobserved=false、其余not_evaluated但qualified沿已就绪保持，不替代首次全评估证据。

原观察器stage在首次ready后仍标startup，本报告只按保留的首次qualified边界划分分析，不改原文件。原phases.first_kinds列表为startup offset0、cleanup offset7101605、after_cleanup offset7124818。**pre-cleanup截止必须取7101605**；`trial-cleanup-phase.json`较晚的serial_bytes_before_cleanup=7102136没有用于替换它，相差531B。最终serial7124818B；cleanup-tail23213B不能回填startup成功。

结束后先保存 [ANALYSIS-PROVENANCE.json](ANALYSIS-PROVENANCE.json)真实run ID、candidate/serial SHA，再核冻结parser SHA `03313c7c83d0951a77500c9b2aeb27e41e85d197a846a00bf72d8d1fc28be393`，使用原CLI按实际字节前缀解析。完整原输出/argv/stdout SHA在r35-startup、r35-pre-cleanup、r35-full-including-cleanup-tail三组文件；[R35-PHASED-READOUT.json](R35-PHASED-READOUT.json)分开解释：

| 阶段与范围 | 原导出读出 | 限制 |
| --- | --- | --- |
| 启动 `[0,3625023)` | offset1417536 ordinal1：no_captured_attempt_as_of_log、no_captured_bind_as_of_log；offset3061859 ordinal2：original_send_returned_zero、original_bind_succeeded_magic_observed | 仅各条完整原日志当时的捕获状态，capture_loss=false、budget_terminal=false；不能说精确首次真实事件时刻或全局End状态 |
| 交互pre-cleanup `[3625023,7101605)` | 无新增完整r35导出 | unknown，不沿用ordinal2冒称当前状态，不补零 |
| cleanup-tail `[7101605,7124818)` | 无新增完整r35导出 | unknown，不能借用清理后的图/字节回填启动或交互 |

startup截止落在半行：offset3624829记录 `partial_line_at_End`。该前缀解析没有借用之后换行；另两前缀仅用于独立阶段分析。所有原r35v1行及字节offset/hex另存 `NATIVE-AND-R35-EXACT-LINES.json`。v5tail仍为nontransactional snapshot，绝不当全局End终态。

本轮诊断观测文件写出与分阶段读出完成；原首帧和菜单可见证据成立，但八步验收、完整HTTP/首次browser PID证据及r26/r27本task前置快照不完整，最终保持failed。r26b失败、r28 fixture和r31 180秒无待机失败均不被本轮覆盖；未扩大到60分钟、4096键、全部菜单、录像、实机或FX6。

## 交付索引与复核

- [RESULT.json](RESULT.json)：最终failed、每步状态与边界；[README.md](README.md)：仅本task入口。
- [FULL-INPUTS-BEFORE.json](FULL-INPUTS-BEFORE.json)、[FULL-INPUTS-AFTER.json](FULL-INPUTS-AFTER.json)、[R37-DELIVERY-AFTER.json](R37-DELIVERY-AFTER.json)：1206项与172项匹配，另有原INPUTS-AFTER分组。
- [ACTION-TIMING-AND-IDENTITY.json](ACTION-TIMING-AND-IDENTITY.json)、`tool-timeline.jsonl`、所有step/attempt/UUID目录与完整child原文；无截断stdout解析或旧current-return兜底。
- [SHA256SUMS](SHA256SUMS)、[EVIDENCE-MANIFEST.json](EVIDENCE-MANIFEST.json)：本task与真实run全部文件，原始run产物原位保留。
- 项目开始复核[QEMU官方MTTCG说明](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html)，仅作冻结MTTCG/noicount条件参考；真实argv和本地回执才是本轮运行证据，非官方稳定性背书。
