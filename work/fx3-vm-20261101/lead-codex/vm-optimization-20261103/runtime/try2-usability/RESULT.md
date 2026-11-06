# TRY2 易用性修复阶段回执（2026-11-03）

**结论：未通过整体交付门。** 用户原试用的第 9、10 键已到原生输入队列，随后软件 OSD 真实提交全黑像素；新一轮 4 键运行复现了原生 `MODEL_POWER_OFF` 通知、`scr0039_shutdown` 开屏及清屏，因而黑图不是单纯浏览器加载问题。新独立候选移除了 30 键硬限，设为默认 4096 键及 60 分钟，并修复宿主按键等待与网页图片加载的可证缺陷。离线 31/32 边界通过；新增 v2 候选修复了一次真实触发的 media hook 近距映射分配失败，内部原生链逐键看图达到 Shooting 第 13 键且正常收尾。最新原生只读观察抓到固件关机对象 factor `0x11`，原表对应 `OFF_BY_APO1`；上游 UPM 命令与当前省电设置仍未知。浏览器控制宿主不可用，真实网页和 guest 第 31/32 键仍未验，现有 TRY2/Finder 入口未替换。

## 原用户会话的可复核链

- 源会话：`try2-delivery/runs/try2-70588c4c`，只读快照：`user-run-readonly-20261103/`。用户截图为 `Screenshot 2026-11-03 at 3.23.06 AM.png`；第 10 步处于 `Shooting > Image Quality/Rec`，当时网页显示等待。
- step 9（Right）和 step 10（Down）各有原生 down/up 接收及 `FX3_SYNTH_KEY ... result=0`。本地 step 9/10 回读仍是同一旧 frame 254、同一 PNG SHA `8e11552d...55a0e23`。frame 254 首次采样 host monotonic `288627.999`，两个宿主发送时刻分别 `288643.070` 与 `288667.530`；原版以 ring sequence 推断“画面已更新”，而序号或旧帧回读不能证明新像素。
- frame 255 在 host monotonic `288956.005` 才被采样（相对第 10 键宿主发送晚约 288.5 秒，**仅同一 host clock 相减**），token `0x401`、physical `0x43ae96100`，非均匀像素。frame 372 仍沿用源 255；frame 373 原生 OSD 提交 `0x1003`，token `0x402`、physical `0x43feb5100`，其前 GPE seq 1198 对该地址执行 640×480 `FillRect` 并在 seq 1199 `Flush`。host 首次采样黑像素为 frame 378，host monotonic `288969.956`。其原始 614400 字节全零；后续直到 frame 3078 的 `0x1005` 均保留像素源 373。上述逐项抽取见 `black-frame-trace.json` 和原 `osd-ring-readback.json`。guest `monotonic_ns`、内核 printk 时间与 host monotonic 未直接混算。
- 同一 host clock 下，以“该键发送至下一键发送”作为观测窗，steps 1–8 首次不同 PNG 的观测延迟依次为 0.126、1.700、0.926、1.494、2.420、1.902、2.383、2.296 秒；step 9 在 24.460 秒窗口内没有不同像素；step 10 后首次不同像素晚 288.475 秒。表见 `input-latency.json`。这是时间先后关系，并非证明每次变化由对应键引起；实际网页按钮解锁/浏览器绘制时延仍无完整数据。
- 适配源码 `helpers/fx3-osd-core-v4-frame.h` 的 `ho_commit` 只保存一个 retained frame；`helpers/fx3-osd-headless-v7-observe102.c` 对 `0x1003` 拷贝指定表面，对 `0x1005` 重用 retained 原字节。GUI 布局配置保存了字节与 hash，但未执行原 CP 多 plane 合成。该实现确实呈现全零 token，但**后续新证据显示原固件先进入 shutdown 页面并执行清屏**，不能把缺合成断言为这次关机的起因；原面板最终画面仍未验，也不能把旧非黑帧冒充实时画面。
- 原用户会话 916.447 秒后由时间上限结束，QEMU exit 0、PID 已回收、API16 guest ack 及原字节恢复、输入源 hash 未变、两锁释放；这是资源/协议证据，**视觉验收失败**。原报告的 `health_pass=true` 未覆盖黑图。

## 30 键与 15 分钟来源及改动

| 层 | 原限制 | 新独立版本 |
| --- | --- | --- |
| 网页状态机 | `TrialState.max_steps=30` | 启动参数 `--max-steps`，32..4096，默认 4096；一次只留一个 pending |
| 宿主 gate | `gate_input101.valid_command` 第 30 步截止 | `gate_input_usability.py` 同一配置上限；白名单、100ms、顺序、观测画面门保留 |
| guest 输入 | `fx3-input95-hoststep-v1.h` 和 `fx3-rm-key-gate-v5-diag96.inc` 30 步截止 | 新 guest member 上限 4096；control page 仍为单条 12 字节命令、32 位 step/done，没有 30 项记录数组；RM 的 `jobs[32]/leases[32]` 是其他资源结构，未改 |
| 会话 | runner 1..15 分钟，默认 15 | runner 1..120 分钟，默认 60；仍有故障早停、日志/退出门 |
| 等待与网页 | 普通键像素不变最多等 20 秒；`image.onload` 无失败/超时出口 | 普通键收到原生 up 后最多等 6 秒并明确报“像素未变”；MENU 保留 180 秒；比较 PNG SHA 而非 frame sequence；图片加载 8 秒超时/onerror，轮询在 `finally` 重排。6 秒只是 host 确认无像素变化的等待，不是固件绘制完成保证。 |
| 黑帧 | `ready` 仍可能为 true | 仍显示真实全黑图及诊断，输入暂停；不回放旧画面，不假造完成，资源/视觉状态分列 |

候选 `vmopt-20261103-try2-long-v1/candidate.json` SHA256 `d3bb8f938144d8a59b77d6168aff846880977a429c701ad8d207de36d199a114`；只替换 CPIO 成员 `simulation/fx3-rm-empty-provider-v3-setup.so`，成员新 SHA `6acb0e52e610cb0d13721f38fcf1c7c27b0e5a48e687d7a4feda5fde9f9bcd14`，DTB 仅调 initrd end。保留原 English 固定 seed、OSD timer/GPE perf/原厂 5000ms、原两锁、原 TRY1/TRY2 文件。旧新主要源码 SHA 与 diff 在 `source-sha256.json`、`source-diff.patch`；本目录新文件 SHA 在 `new-files-sha256.json`，构建约束在 `src/guest-build.json` 与候选 `build-receipt.json`。

## 验证边界

- host core 覆盖 1..4096 顺序、七键、20 字节 down/up、100ms、4097 拒绝；guest worker 代码在宿主桩环境离线执行到第 31/32 键、每键一次原生 down/up、无命令不发送、未知键拒绝；输出见 `src/check-long-use-worker.log`。Python 编译、JS `node --check`、host `TrialState` 31/32/单 pending/黑帧禁止新键通过。以上是离线验证，不代替 QEMU 第 31/32 键。
- v1 零键运行 `runs/try2long-a2a3177f`：25 分钟测试上限（产品默认仍为 60 分钟），106.869 秒达原生待机，真实 PNG `trial-standby-ready.png` 已看图：English、NO CARD、待机图标。随后因浏览器控制接口连续返回 `The browser access host is unavailable` / native pipe startup failed，按协调要求不通过 HTTP 伪造点击，零键 SIGINT 收尾。`receipt.json`：`stop_cause=Ctrl-C`，QEMU PID 25606 exit 0/reaped/absent、API16 在 20 秒窗内 guest ack 与原字节恢复、输入 hash 不变、两锁 free、无 observer/serial 错误；`lifecycle_pass=true`。`health_pass=false` 因人工早停时 `FX3_DATE98_KERNEL_OBSERVE_READY` 尚未出现，不升级为全轮通过。收尾后独立再次核验两锁 free、无 QEMU/runner PID。
- 浏览器 Shooting 路径、无变化键、真实第 31/32 键、新前端视觉/按钮解锁、Finder 入口及长时稳定性均未验证。修复前普通无变化键 20 秒、新代码 6 秒；**修复后实测点击到显示时延 unknown**，不能用代码常量代替运行数据。黑帧的原 panel 语义与正常恢复路径仍未解释；停止继续盲跑或推广。

## 后续真实首错修复与内部逐键轮

第二次 v1 零键启动 `runs/try2internal-e37d1915` 于 21.584 秒触发 `FX3_MEDIA_BIND_REJECT module=M reason=install point=0x9c98 result=-3`，立即早停并按原 20 秒 API16 规则干净退出。`fx3-media-observe-v3-uipc.c` 的 M 列表首项就是 `0x9c98`；此时静态 `pool_M` 尚未使用，`used+128>8192` 分支不成立，故 `-3` 落在 `allocate_pool`。原实现以 64KiB 间隔试 `mmap` hint，接受距 hook ±120MiB 内的地址。失败后的同进程 maps 快照显示该范围内仅 `0x7f60000000..0x7f60007000` 28KiB 空洞，旧 hint 格点没有落入其中；`near-gap-diagnosis.json` 给出 PC `0x7f60026c98`、范围与计算。旧搜索每次 `mmap` 的实际返回及 errno **未被记录，保持 unknown**；这份失败后映射快照支持但不能单独证明全部失败机制。

新 `fx3-media-observe-v4-near-gap.c` 在原搜索前读取本进程 `/proc/self/maps`，用每个空洞的 4KiB 对齐起点作普通**非固定** `mmap` 提示，核对实际返回仍在原 ±120MiB 跳转范围内，否则 `munmap` 并回退原搜索。没有 `MAP_FIXED` 或硬占已有映射。guest Linux `4.9.337-scel+` 不具备 Linux 4.17 才引入的 `MAP_FIXED_NOREPLACE`，所以未使用该标志；[Linux mmap 手册](https://man7.org/linux/man-pages/man2/mmap.2.html)明确普通地址是提示且可能另择地址，亦说明固定映射可覆盖既有范围。原码字匹配、原分支范围、GPR/SIMD/NZCV 自检及失败早停未放松。v2 候选 `vmopt-20261103-try2-long-media-gap-v2/candidate.json` SHA `67eb81401a457bf7ffecb21f7367e7819b5bf3e13aef39dd8a4c9001ce408417`，从 v1 仅替换 CPIO 的 media observer 成员，旧 SHA `ba65b611...`、新 SHA `179c74c3...`，审计/DTB 回执在候选目录。新 guest 日志实际记录三个 `FX3_MEDIA_POOL_MAPS_GAP`，其中 M 的 hint/actual 均为 `0x7f34000000`，随后 `FX3_MEDIA_BOUND module=M ... points=9` 与 D `points=27`；这验证了本轮绑定成功，不保证所有 ASLR 布局无限稳定。

v2 内部原生运行 `runs/try2gapinternal-13b47129`，`--internal-hoststep --max-minutes 15 --max-steps 40 --port 0`，**未启动网页服务**。请求由单个本地文件门进入原 InputGate；每键先拷贝不可变 `internal-observe-NN.png` 并用图像工具查看，随后记录当前页与选键理由，原生 100ms down/up 逐键一次；共 13 键/13 份回读，全部原生 `FX3_KEY_INPUT_RECV` down/up 与 `FX3_KEY95_STEP_DONE` 各一次，均为非全黑像素。第 9 键完整橙焦点下打开 File Format 弹窗（`trial-step-09-key-1af.png`）；第 10 键只移动高亮到 XAVC S-I 4K，原选中圆点仍在 XAVC S HD（`trial-step-10-key-030.png`）；第 11 键 MENU 取消回列表，File Format 仍显示 XAVC S HD；第 12/13 键进入 Movie Settings 子页（`trial-step-13-key-1af.png`）。没有确认格式变更。观察图和决策文件均在该 run 内，`trial-input-events.jsonl` 与 `trial-step-readbacks.json` 可逐项对应。期间未出现黑帧，但只说明这 13 键的该次路径。

v2 轮 662.410 秒在 900 秒上限前主动停止输入，预留 240 秒收尾；QEMU PID 30252 exit 0/reaped/absent，API16 guest ack/原字节恢复，输入源 hash 未变，两锁释放后独立复核 free；无 observer/serial 错误。原件 `lifecycle_pass=true`、`health_pass=false`，字面 `FX3_DATE99_CONSUMER_BOUND` 未出现；后续精确检查发现并发串口写入把该行拆成 `FX3_DAT` 与 `9_CONSUMER_BOUND`，成功绑定由独立原生事件证明，原 receipt 保留不改。该次同一 host monotonic 观测窗内第 9/10 键首次不同像素分别为 3.743/2.471 秒（逐键全表 `internal-latency.json`）；与用户旧轮的 step 9 在 24.460 秒内无不同像素、step 10 后 288.475 秒才首次不同像素构成**不同运行条件的对照**，不能归因于近距映射补丁或宣称已修复历史黑帧。网页显示/按钮解锁时延仍 unknown。

## 新轮：原生关机先于后续按键

`runs/try2gapinternal-47e2924a` 使用相同 v2 guest、独立 v7 内部 host-step、30 分钟硬上限/36 键上限/末 240 秒收尾预留；本轮没有网页服务。待机图已实际查看。第 1 键 MENU 后取得 Setup > Area/Date 非黑 PNG；待机图、每键前不可变 `internal-observe-01..04.png/.json` 和四份输入理由、各键后 `trial-step-01..04*.png` 都在 run 目录。第 2/3 键 Left 与第 4 键 Down 均有原生 down/up 与 STEP_DONE，但图仍停在旧 Setup 橙焦点。按未知即停门，不发送第 5 键；其后原生 ring 首次采到黑帧。QEMU PID 34144 exit 0/reaped/absent，API16 1.552 秒完成 guest ack/原字节恢复，输入 hash 不变，双锁 free。旧 v7 `health_pass=true` **错误地漏掉 render**，同份 receipt 同时明确 `render_valid_at_end=false`、`black_after_ready` 非空、`render_observation_ok=false`；原件保留，不能引用其 health 布尔值作可用性通过。

`shutdown-trace.json` 以原始串口字节定位：用户旧轮在 byte 17774589 收到 `MODEL_POWER_OFF` 原 28B (`raw=2c000300...`, source `0x830128`, 发送返回 PC `0x2eacd4c`)，在 byte 17840149 原厂打印 `open screen: scr7001_1005 -> scr0039_shutdown`；新轮分别在 byte 21730929、23494893 收到同型通知与 `scr7001_1003 -> scr0039_shutdown`。新轮 shutdown 进入发生在第 1 键之后、第 2 键之前，因此后面三键无新像素不能当常规菜单无变化键。两轮随后均有 `AP89 id2=0x2af` 和 `scr0039_shutdown` controller/presenter 原生创建返回；原 screen 名表见 `reports/2026-11-01-fx3-vm-resumed-repair/ap87-uud-queue-first-screen.md:44`。这是**原生 shutdown 业务进入**，不等于机身实际关机或其上游自动省电原因已证。

`black-transition-compare.json` 逐一保留两轮 OSD/GPE：旧轮最后采样非黑 frame372、GPE 1198 的 640×480 FillRect 及 1199 Flush、新源 1003/frame373 token402、首采黑 frame378；新轮最后采样非黑 frame1310、GPE 717 同规格 FillRect 及 718 Flush、新源1003/frame1311 token401、首采黑 frame1314。两轮全零 raw SHA256 同为 `34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f`。旧轮 host 采样间隔 3.161 秒，新轮 409.009 秒，**都不是 GPE 指令本身耗时**；串口指令没有同一 host monotonic 戳，不能跨钟作精确耗时。原生 GUI `1000/1001/1004` 收据和 ring `config_hash` 可见，raw 配置字节仍 unknown；尚不能断言 CP 最终合成效果。

本候选 CPIO 有 `liro.ko` 和 `setting/Backup.bin`，无 `av-cam.bin`。当前串口仅见 LIRO 的 `pciatu_map/unmap` 未解析符号，未见 LIRO Live/AV 自然装载；FX6 所需读点当前不可用。可供 FX6 只读参考的 FX3 VM 文件为本轮 `backup-native-load-before-AP.bin`、`backup-reserved-ram.bin`、`Backup-native-file-final-before-shutdown.bin` 及 `file100-*.json`；不代表 FX6 或相机实时状态。

## 新观察门与下一因果缺口

新源码 `trial_log_v3_usability.py` 的 DATE99 字面命中仍逐字记录；若串口交错导致缺字面，只在 `WORKER_READY`、`DATE98 consumer99` 成功注册分支、`CP_PUBLIC_OWNER result=0`、同 transaction/reason/generation 的 `ACCEPT → CLOCK_COMMIT valid_UTC=1/readback → RETIRED result=0/native_request_free=0` 全齐且无 REJECT 时恢复语义门，并在新 receipt 写各项原始串口 byte range 与原文。原生产者 `fx3-cp-backup-v4-sync100.c:51` 只在 `osal_reg_public` 成功分支打印 DATE98；`fx3-date99-consumer-v1.h:27-31` 的 commit 可在随后失败时回滚，故还必须有成功 retired。`date99-marker-evidence.json` 固定旧轮字面断行和新轮完整字面；`src/check_date99_semantic.py` 覆盖缺任一项、owner失败、截断commit、事务不匹配、REJECT、跨 poll 分片。

新 `run_trial_v8_long_boundary.py` 将 `lifecycle_pass`、`protocol_pass`、`render_pass` 分开，ready 后已证原生 shutdown 与未知语义全零像素分别早停；曾黑后恢复仍不能算 render pass。`trial_health_v2.py` 与 `src/check_health_v2.py`、`src/check_shutdown_monitor.py` 的正负例通过。这是**诊断和故障停止修复**，未经过新 guest 回归，更不是画面修复，不替换既有入口。

最早尚未闭合的上游条件是 `MODEL_POWER_OFF` 的原 UPM/InfraNotify 输入、shutdown factor/type/next reboot 与实际省电设置。原 `appFw.so` `0x2a8aa10..aa20` 构造 `0x3002c` 通知，既有 `boot-screen-controller/README.md` 将其经 manager/boot handler 接到 shutdown 选择；当前 `FX3_BOOT_QUEUE_SEND` 只抓事件，没有 UPM 原 payload 或 factor。现按键适配 `fx3-rm-key-gate-v2-setup.inc` 只把 20B down/up 送原 UI 队列 `0x807a0020`，明记 `original_cp_key_detection=0`，是否复位原电源活动计时**未证**。索尼 [FX3 原版帮助](https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000267857.html)说明无操作时省电、可通过半按快门等操作返回；这支持检查真实活动通知但不证明本轮就是省电到期。官方默认 5 分钟仍不能替代**当前固定 Backup 的值**，该 ID/运行态读回尚未定位。下一次只应有界观察原 `0x3002c` 的 UPM 输入及 factor、实际省电选项和原键活动路径，在合同闭合后修适配，而不屏蔽 shutdown、改原厂超时、循环 keepalive 或把黑图换旧帧。

新增只读 `src/trace_poweroff_precursors.py` 与 `poweroff-precursors.json` 逐字核对固定 `appFw.so` 名表和两轮原始 serial：两轮早期各有原生 `MODEL_MEDIA_EJECTED_INITIAL_SLOT2/1`、两组 `MODEL_BATTERY_REMAIN_CHANGED/SUB_BATTERY_REMAIN_CHANGED`，之后分别在 byte 17774589、21730929 出现 `MODEL_POWER_OFF`；两轮 `FX3_AP89_UUD_DECISION` 均是 `native_update_return=0`，与旧 AP87 的 UUD return1 场景不同。28B `POWER_OFF` 消息除事件 ID 外为零，未带 factor。串口字节顺序只能证明这些日志的先后，不能证明电池事件、省电、媒体移出或 UUD 是这次关机原因；仍需原 UPM 输入与实际电源设置读回。

### 新独立一键原生因子观察

在仅新增只读 appFw observer 的候选 `vmopt-20261103-try2-power-observe-v1` 上，`runs/try2powerinternal-6a05c56b` 于 English standby 看图后只发 MENU 一键，原生 down/up 各一次；首个不同像素 PNG 于 host 发送后 0.346 秒被采样，过渡图与随后 Setup > Area/Date 橙焦点完整图均用图像工具实际查看。第二键未发。两处原 appFw hook `0x2a8a884/0x2a8aa10` 抓到同一 TID 383 对象的前 12B `520000001100000002000000`，原固件表 VA `0x41172f8` 第 17 项将 model factor `0x11` 对应到 `OFF_BY_APO1`/UPM factor `0x08`。第 1 键首次 `done=1` 到第一 hook 为 **300.867582 guest monotonic 秒**，符合五分钟无操作省电的可能情形；不能据此断言合成键未复位活动计时。原 UPM 请求、对象 +12、当前固定 Backup 的设置值和旧两轮实际 factor 仍未知。原 `MODEL_POWER_OFF` 后 runner 立即早停，未等黑屏；故该轮最终 `render_pass=true` 也不等于长期可用。详细逐钟表与源码/官方设置契约见 `power-off-time-and-contract.md`、原始 `power-off-run-evidence.json`，截图见 run 内 `internal-observe-01.png`、`trial-step-01-key-1ab.png` 和 `post-menu-current.png`。

该 run 原件 `receipt.json`：434.298 秒、QEMU PID 62331 exit 0/reaped/absent、API16 在 20 秒门内 guest ack/原字节恢复、输入源 hash 不变、两把锁 free，`health_pass=false`。本轮内部 host-step 没有网页，网页显示与按钮解锁时间仍 unknown。索尼 FX3 原版帮助明确自然路径 `MENU → Setup → Power Setting Option → Power Save Start Time`，选项 Off/30 Min/5 Min/2 Min/1 Min/10 Sec；若要改变省电行为，只能在看图确认当前值后走该原生 UI 路径，不能预写 seed 或注入周期 keepalive。`Auto Power OFF Temp` 是不同设置。下一门为活动计时原生产者/消费者和当前设置 ID 定位，随后才可设计最少两次人工单键的复位对照；用户原黑屏与本轮可能合法的闲置省电分列。

原 `upm.ko` 只读反汇编进一步确定 `k_upm_Backup_read_mss` 的两个候选 Backup 读 ID `0x00920000/0x0092002d`，`k_upm_mss_apo_cb` 在消息条件符合时发 `0x00920141/factor8`，`k_psave_api` 另读 `0x00920085`；原 `appFw.so` 有 `sequence_mss_reload` 及 MSS start/stop 字符串。它们仍未与固定 seed 的 UI 值和真实物理键活动路径完成语义映射，不能把静态 ID 当已测当前配置；指令和未知项逐项记于 `power-off-time-and-contract.md`。

协调者另授权的一次 FX6 Image-only 早期启动与本 TRY2 菜单修复相互独立；固定 FX3 平台基线及逐轮资源回执见 `fx3-platform-frozen-baseline.json`、`fx6-image-only-fixed-platform-review.json`。首轮 `fixed-fx3-0b8eaf59` 在 QMP `cont` 前因 macOS Unix socket 绝对路径过长失败，串口0B，非内核证据。修正宿主相对 `q` 连接后，`fixed-fx3-9581d529` 保持 QEMU/完整 DTB/453MB CPIO/模型环境/加载地址及预启动PC、x0、4核一致，只有 kernel Image 改为固定 FX6 文件；0.323秒首串口早停，470B串口含 `Linux version 4.9.337-scel+`（u24-002），QEMU PID58280 exit0/reaped/absent、两锁空闲。该回执仅证明 FX6 内核在既有 FX3 模拟器上进入早期串口输出，AP/AV/CP、菜单、颜色与实机均未测；runner `linux_version_marker=false` 只因它检查**第一行**而版本在第二行，原始串口已单独核对。

同一固定 FX3 平台、只换 FX6 kernel Image 的首模块有界轮 `fixed-fx3-c72ee0b9` 使用 runner SHA `527c789e...`、180 秒上限，2.515 host 秒被 `FX3_INSMOD_RC_/kmod/devno.ko=0` 标记停止；轮询前串口又自然到 `osal_utm.ko=0`、`osal_uipc.ko=0`，不可声称在第二模块前停住。串口 SHA `034552e3...`、65464B，未见 kernel fault/CPUSET_NOT_READY/AP guard；QEMU PID 68544 exit0/reaped/absent、两锁独立复核 free。完整回执 `fx6-first-module-fixed-platform-review.json` 与 donor 目录 `early-kernel/runs/fixed-fx3-c72ee0b9/run-receipt.json`。本轮不触及旧 FX3 helper 的硬编码 pcidma VA；该 VA 对 FX6 Image 已有静态不匹配证据，绝不能为后续绿灯放松 helper 检查。FX6 AP/AV/CP/菜单/颜色/实机均未通过。

## 可复核启动与下一阻塞

未改用户现有 TRY2/Finder 链接。旧实验 `run_trial_v6_media_gap.py` 有已证 `health_pass=true` 而 render 失败的误判，**不再建议启动试用**；新 `run_trial_v8_long_boundary.py` 仅完成宿主源码与正负例验证，尚未 guest/浏览器回归，同样不作为用户入口。`--internal-hoststep` 只用于受控内部研究，不能作为浏览器验收。现有本机 URL 只在旧会话运行时有效，当前无服务/guest 长跑占锁。

下一步在已抓到的新轮 `OFF_BY_APO1` 因子之上，继续追原 UPM 请求、固定 Backup 的省电设置实际读回，以及原物理键活动计时复位合同；只有证明异常才决定最小适配修复。五分钟后自然 APO 与用户轮早发黑图不可自动等同。GUI `0x1000/0x1001/0x1004` 原字段及 CP 面板合成仍需独立核对。浏览器控制恢复后，另做真实网页逐键 Shooting、无变化键及按钮解锁/显示时延验收。之后在画面正常、每步可见且资源可收尾的条件下，另开有界内部轮验证 guest 第 31/32 键，再做网页正常结束、Ctrl-C 和 Finder 入口回归。FX6 Image-only 已到原首模块边界；后续软件 helper/模块/AP/AV/CP 要用独立候选审计，不与本菜单候选混用。

## 追加：27 键连续操作与 FX6 pre-CP（2026-11-03）

最新受控 FX3 轮已逐图进入原生 Setup 省电页，实际只读值为 `Power Save Start Time 5 Min`；27 个键全部原 UI 队列 down/up 接收，最后一个键释放仅 11.870847008 guest 秒后，原 appFw hook 收到 `OFF_BY_APO1`。因此此前单键后约五分钟 APO 的“正常闲置”解释不能覆盖这次连续操作。第 28 键未消费/发送，31/32 边界继续挂起；原物理键到 UPM/MSS 复位合同未闭合，暂停下一轮 FX3 及用户入口提升。FX6 Image-only pre-CP 短轮到固定 FX3 CP helper `binding_failure/-7`，原 LDEC/FILE observer 前序通过，PID 和双锁正常释放；未宣称 FX6 CP/AP/AV 通过。完整逐键同钟表、截图 SHA、原生静态指令与两轮资源证据见 [`continuous-operation-apo1-and-fx6-precp.md`](continuous-operation-apo1-and-fx6-precp.md) 及 [`continuous-27key-apo1-evidence.json`](continuous-27key-apo1-evidence.json)。

## 追加：原生 MSS 被动定向轮（2026-11-03）

新单轮只替换被动观察 so，原 `sequence_mss_reload` 在启动时两次执行并调用目标 QID builder；两次 MENU 开/关均逐图完成，但未再触发该原 app 序列。原生 `OFF_BY_APO1` 对象在第2键 up 后 **300.198700992 guest 秒**出现，runner 健康早停（非通过）；QEMU/API16/输入哈希/两锁完整收尾。原消息 16B 堆字节和 UPM consumer 仍未观测，不能把 `send_sync=0` 判作 timer reset，也没有足够证据改适配行为或提升试用入口。详见 [`mss-targeted-result.md`](mss-targeted-result.md)、[`mss-targeted-run-evidence.json`](mss-targeted-run-evidence.json)。
