# FX3 连续菜单网页 32 键单轮验收

结论：本轮 **32 个实际按键全部通过真实浏览器按钮发送、原生 down/up 接收、逐图目标焦点/类别变化及网页看图确认**；完整 health/protocol/render/lifecycle/diagnostic 门通过，正常 End、恢复与回收通过。第 31 键 Exposure/Color → Focus、第 32 键 Focus → Playback 均有清晰目标截图和独立原始接收记录。这是指定原 FX3 A/r3 候选的一次、约 11 分钟的导航验收，不能扩展为全菜单功能、实机、长时稳定性或零帧根因修复证明。

## 身份与边界

- 唯一运行：`v25diag-web-r6-8456422c`；runner PID **2741**、QEMU PID **2865**；loopback 网页 `http://127.0.0.1:50959`，独立 agent-browser 会话 `fx3nav32-b83358633d9e`，Chrome 真正加载页面并由页面自身执行 HTTP 请求。
- runner 创建 UTC `2026-11-04T17:02:45.524959+00:00`；浏览器 Start 请求 `17:03:14.378Z`、End 请求 `17:14:25.951Z`、final ACK `17:14:29.153Z`；runner duration **674.500792583 秒**。在 16 分钟观察预算内完成，没有第二轮或重试运行。
- 命令：`PYTHONDONTWRITEBYTECODE=1 python3 .../v25-r10-independent-diagnostics/run_trial_v25_diag_r3.py --max-minutes 20 --max-steps 4096 --port 0`；没有 `--review-procdiag-r4e`、`--internal-hoststep`、exit-phase 或零键 observer。4096 是配置容量，实际验收依据为逐步 32 键证据。
- SOURCE-FREEZE SHA256 `65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce`；runner SHA256 `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0`。
- 原 r3 CPIO SHA256 `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`，candidate `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`；QEMU `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`。固定 kernel/DTB/Backup、4-core MTTCG、无 icount 参数均由 [command.json](command.json) 和输入哈希回执保留。
- 操作仅 1 次 MENU 开菜单、其余方向键。没有确认键、值编辑、删除键、改省电设置、keepalive、重放、阈值调整、输入门变更或强行解锁；没有相机/USB/SD 设备操作、FX6 工作、镜像复制或默认入口部署。开始前看到完整待机图标；本轮未遇省电弹窗、原生未接收、无法判断目标超过 30 秒、黑帧或健康错误。
- 仅新 run 内写入本轮证据和报告，冻结源码/guest/平台及其他代理文件未改。第 2 键之前有一次本地点击被浏览器的 disabled 按钮保护拒绝，未产生 HTTP 请求或 guest 键；实际 HTTP key 请求始终恰为 32。

## 逐键人工观察与原始 ACK

每次只在已看到目标焦点变化后点网页“我已看清当前完整画面，继续”，再决定下一键。以下目标来自 worker 逐次实际查看的网页 PNG，不由 `visual_changed`、NO CARD 闪烁或任意像素变化自动推断。部分主类别切换帧的右侧详情更新较晚，本轮相应步骤目标只认清晰可见的主类别焦点/标题，不据此宣称完整右侧页面刷新成功。

[完整逐步数据](NAV32-STEPS.json) 含：请求/202 ACK body、原生 receive/send/STEP_DONE 的 LF 行号与字节偏移、原始行、目标描述、截图完整 SHA256、网页确认 200 ACK、native frame PNG SHA 及可用宿主延迟。[真实浏览器 HTTP 回执](NAV32-web-http-evidence.json) 保留 32 个 key 202、32 个 confirm 200、Start/End 各 1 个 202、final-ack 1 个 200；仅移除临时认证 header，没有脚本调用这些 POST。每步原生状态均有 1 down + 1 up、native_result=0、STEP_DONE one_down_one_up=1。看图确认的 `guest_input_written=false`，没有额外固件键。

| 步 | 键 | HTTP / 原生 | 实际看到的目标变化 | 网页 PNG / SHA256 前12位 |
|---:|---|---|---|---|
| 01 | MENU | 202 / down+up+done | 待机 → Setup > Area/Date，Area/Date/Time Setting 橙色焦点 | [NAV32-01-MENU-target.png](NAV32-01-MENU-target.png) `d14d7c0d8f98` |
| 02 | DOWN | 202 / down+up+done | Area/Date/Time Setting → NTSC/PAL Selector 橙色焦点 | [NAV32-02-DOWN-target.png](NAV32-02-DOWN-target.png) `6fc3699b0084` |
| 03 | LEFT | 202 / down+up+done | 条目列 → Area/Date 子类别橙色焦点 | [NAV32-03-LEFT-target.png](NAV32-03-LEFT-target.png) `e53aaa0cf37a` |
| 04 | DOWN | 202 / down+up+done | Area/Date → Reset/Save Settings 子类别焦点 | [NAV32-04-DOWN-target.png](NAV32-04-DOWN-target.png) `87b20cfbf64c` |
| 05 | DOWN | 202 / down+up+done | Reset/Save Settings → Operation Customize 子类别焦点 | [NAV32-05-DOWN-target.png](NAV32-05-DOWN-target.png) `fbf9b3780de6` |
| 06 | DOWN | 202 / down+up+done | Operation Customize → Dial Customize 子类别焦点 | [NAV32-06-DOWN-target.png](NAV32-06-DOWN-target.png) `fb9687ffaeb6` |
| 07 | DOWN | 202 / down+up+done | Dial Customize → Touch Operation 子类别焦点 | [NAV32-07-DOWN-target.png](NAV32-07-DOWN-target.png) `2c6737ab4b4c` |
| 08 | DOWN | 202 / down+up+done | Touch Operation → Monitor 子类别焦点 | [NAV32-08-DOWN-target.png](NAV32-08-DOWN-target.png) `d4d040c5f7d6` |
| 09 | DOWN | 202 / down+up+done | Monitor → Display Option 子类别焦点 | [NAV32-09-DOWN-target.png](NAV32-09-DOWN-target.png) `3ffb5c84f0ce` |
| 10 | LEFT | 202 / down+up+done | Display Option 子类别 → Setup 主类别图标焦点 | [NAV32-10-LEFT-target.png](NAV32-10-LEFT-target.png) `d2b0ed22635a` |
| 11 | UP | 202 / down+up+done | Setup → Network 主类别焦点与标题 | [NAV32-11-UP-target.png](NAV32-11-UP-target.png) `a4725baec5cd` |
| 12 | UP | 202 / down+up+done | Network → Playback 主类别焦点与标题 | [NAV32-12-UP-target.png](NAV32-12-UP-target.png) `f6fbbda1b151` |
| 13 | UP | 202 / down+up+done | Playback → Focus 主类别焦点与标题 | [NAV32-13-UP-target.png](NAV32-13-UP-target.png) `868f458332a0` |
| 14 | UP | 202 / down+up+done | Focus → Exposure/Color 主类别焦点与标题 | [NAV32-14-UP-target.png](NAV32-14-UP-target.png) `9cbfd300e7c2` |
| 15 | UP | 202 / down+up+done | Exposure/Color → Shooting 主类别焦点与标题 | [NAV32-15-UP-target.png](NAV32-15-UP-target.png) `378f91107a5b` |
| 16 | RIGHT | 202 / down+up+done | Shooting 主类别 → Image Quality/Rec 子类别橙色焦点 | [NAV32-16-RIGHT-target.png](NAV32-16-RIGHT-target.png) `91c38e48c07b` |
| 17 | DOWN | 202 / down+up+done | Image Quality/Rec → Media 子类别焦点 | [NAV32-17-DOWN-target.png](NAV32-17-DOWN-target.png) `4c0338e0a24c` |
| 18 | DOWN | 202 / down+up+done | Media → File 子类别焦点 | [NAV32-18-DOWN-target.png](NAV32-18-DOWN-target.png) `c338abcc386a` |
| 19 | DOWN | 202 / down+up+done | File → Shooting Mode 子类别焦点 | [NAV32-19-DOWN-target.png](NAV32-19-DOWN-target.png) `185b1d5a841b` |
| 20 | DOWN | 202 / down+up+done | Shooting Mode → Shutter/Silent 子类别焦点 | [NAV32-20-DOWN-target.png](NAV32-20-DOWN-target.png) `66b43b1de032` |
| 21 | DOWN | 202 / down+up+done | Shutter/Silent → Audio Recording 子类别焦点 | [NAV32-21-DOWN-target.png](NAV32-21-DOWN-target.png) `56ad920017fd` |
| 22 | DOWN | 202 / down+up+done | Audio Recording → TC/UB 子类别焦点 | [NAV32-22-DOWN-target.png](NAV32-22-DOWN-target.png) `9ec3cf65627d` |
| 23 | UP | 202 / down+up+done | TC/UB → Audio Recording 子类别焦点 | [NAV32-23-UP-target.png](NAV32-23-UP-target.png) `73f3fbbb6020` |
| 24 | UP | 202 / down+up+done | Audio Recording → Shutter/Silent 子类别焦点 | [NAV32-24-UP-target.png](NAV32-24-UP-target.png) `c4e1b470d282` |
| 25 | UP | 202 / down+up+done | Shutter/Silent → Shooting Mode 子类别焦点 | [NAV32-25-UP-target.png](NAV32-25-UP-target.png) `7359a05969ba` |
| 26 | UP | 202 / down+up+done | Shooting Mode → File 子类别焦点 | [NAV32-26-UP-target.png](NAV32-26-UP-target.png) `0ba1133968f9` |
| 27 | UP | 202 / down+up+done | File → Media 子类别焦点 | [NAV32-27-UP-target.png](NAV32-27-UP-target.png) `13c4f0c16848` |
| 28 | UP | 202 / down+up+done | Media → Image Quality/Rec 子类别焦点 | [NAV32-28-UP-target.png](NAV32-28-UP-target.png) `408a8eec4ba5` |
| 29 | LEFT | 202 / down+up+done | Image Quality/Rec 子类别 → Shooting 主类别图标焦点 | [NAV32-29-LEFT-target.png](NAV32-29-LEFT-target.png) `d855db1122b3` |
| 30 | DOWN | 202 / down+up+done | Shooting → Exposure/Color 主类别焦点与标题 | [NAV32-30-DOWN-target.png](NAV32-30-DOWN-target.png) `dd124d8306db` |
| 31 | DOWN | 202 / down+up+done | Exposure/Color → Focus 主类别焦点与标题 | [NAV32-31-DOWN-target.png](NAV32-31-DOWN-target.png) `5ab81a69c570` |
| 32 | DOWN | 202 / down+up+done | Focus → Playback 主类别焦点与标题 | [NAV32-32-DOWN-target.png](NAV32-32-DOWN-target.png) `02aa033160dc` |

### 第 31/32 键专项

- **第 31 键 DOWN / 0x30**：HTTP 202 body `{"accepted": true, "next_step": 31, "key": "0x30"}`；目标 **Exposure/Color → Focus 主类别焦点与标题**。
  - 原始串口 LF488746 / LF488817 分别 status=1/0，LF488834 STEP_DONE；两次 wait_return_ns 分别 `636304636992` / `636423948000`，clock_id=1，native_result=0。send return=0 与 recv return=0 是分开的证据，不当作 downstream handler 完成。
  - 目标网页截图 SHA256 `5ab81a69c57068573c62a046942d526ab4daa4d72d43235e5c1180f9b1d9dc93`；已验证 native frame sequence=7746，PNG SHA256 `d125861615f010495de255c5e7498db6d17bdc782cc0d584144f61fbc2379c6d`。网页看图确认 200，observed_sequence=7927，content_generation=70，PNG SHA 与该 native frame 同值。
  - 宿主 gate send → 首次观察原生 up **0.238593s**；gate send → runner 首个变化帧抓取 **0.960915s**，不是经过语义判定的目标页面延迟。
- **第 32 键 DOWN / 0x30**：HTTP 202 body `{"accepted": true, "next_step": 32, "key": "0x30"}`；目标 **Focus → Playback 主类别焦点与标题**。
  - 原始串口 LF499967 / LF500081 分别 status=1/0，LF500088 STEP_DONE；两次 wait_return_ns 分别 `650347838992` / `650462548992`，clock_id=1，native_result=0。send return=0 与 recv return=0 是分开的证据，不当作 downstream handler 完成。
  - 目标网页截图 SHA256 `02aa033160dc8e8ad8aa6adcdc8138f619c8b4568257cc87ce158f84db103102`；已验证 native frame sequence=7947，PNG SHA256 `655e518e290c3add897c360ca8e84cb3a42ff648c2a07078e41b82f000d06928`。网页看图确认 200，observed_sequence=8202，content_generation=71，PNG SHA 与该 native frame 同值。
  - 宿主 gate send → 首次观察原生 up **0.182418s**；gate send → runner 首个变化帧抓取 **1.366130s**，不是经过语义判定的目标页面延迟。

协调端另已亲看 Focus/Playback 目标图、核 shownSHA/frame、串口 down/up/done 和清理；相关通知 `msg_7942cbe2293b`。本报告保留 [receipt.json](receipt.json) 的 `menu_verified=false`、`browser_visual_acceptance=null` 原值；`menu_verified` 是冻结 runner 固定字段（runner 897 行），独立人工导航验收在 [NAV32-VERIFICATION.json](NAV32-VERIFICATION.json) 的 `independent_visual_navigation_pass=true` 表达，未改历史回执。

## 延迟口径与剩余未知

- 网页请求入队 → gate send：32 步范围 0.002790–0.106435s，均用宿主 monotonic 同钟相减。
- gate send → 宿主观察原生 up：32 步范围 0.179566–0.473455s，均用宿主 monotonic 同钟相减。
- gate send → runner 首个变化帧抓取：32 步范围 0.757179–2.075371s，均用宿主 monotonic 同钟相减。
- gate send → runner 像素变化判定：32 步范围 1.194452–2.079976s，均用宿主 monotonic 同钟相减。

目标焦点的精确语义延迟没有探针计时，截图是之后的人工观察。guest `wait_enter/return_ns` 只在 guest CLOCK_MONOTONIC 内解释，不与 host monotonic 或 HTTP wall timestamp 直接相减。runner 的首个变化帧可能早于完整目标（例如第 1 键首个自动抓帧仍可能是待机/过渡内容），所以以本报告 `NAV32-xx-target.png` 逐图观察为目标完成依据；`downstream_handler_completed=unknown` 和 `pixel_attribution=observed_after_this_input_not_proven_caused` 保持不变。没有新探针、时序修改或消息跳过。

## 独立诊断、恢复与回收

- [receipt.json](receipt.json)：health、lifecycle、protocol、render、diagnostic_readback 均 true；host_observer_error=null、native_shutdown_after_ready=false、native_model_power_off_after_ready=false；stop_cause=end_trial_button、key_steps=32、visual_state_at_end=user_confirmed。
- 结束时 QMP stop ACK + query-status paused/running=false 后完整读取 [osd-ring-final.bin](osd-ring-final.bin) **16,777,216 B**，SHA256 `d3adc9cc2111c366bfcb7f65c12dfcb04e9afbd1182555c5629fff96ba733aa1`；[解析](osd-ring-final-diag.json) 有效，invalid_or_torn_slots=[]，total_accepted_events=65712，**dropped_busy_writer_events=1**，不宣称事件无丢失。
- 重新证明 paused 后，可选 10 秒预算内独立读取 [ui-gate-counters.bin](ui-gate-counters.bin) **65,536 B**，SHA256 `853fd64d47dd028113574d0b0561fd06d85fabdfdd18e2cb616f683c864480b6`，所有已声明 optional 区 complete、errors=[]。magic=0x3145544147335846、version=2、active bank=1、publication serial=233035；count4..11=`[32148,32148,22779,9369,8216,32024,32022,32114]`，gate_hist=`[346,704,8319,19623,2813,343]`，peak_gate=269、backlog_skip=22779、time_skip=1153、time_pass=8216、timer_dequeue=32022、a12/a13_nonzero=0、last_a18=1。是全程终态累计和逐字段原子镜像，不是启动专用、无损执行轨迹或跨字段事务一致快照。
- [API16 restore 回执](restore103-receipt.json)：原 20 秒合同内 **1.836909s** 完成 guest ACK + 原 16B 回读；最后 [raw](restore103-007-api16.bin) 为 `000b00b4fd7bbba9fd030091f35301a9`，SHA256 `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`；[header](restore103-007-header.bin) SHA256 `fc5563e2787ea0ddd29fc3986d24c7d335c5fa23ebceb1ee000b0e060fb82dc9`。独立解包 `<8s8Q`：F100FILE、shutdown_control=0x100c1ea9、restore_status=0、restore_seen=1；原生 unbind return=0，host 没有写原代码。
- QMP quit sent、QEMU exit=0、process_reaped=true、PID_absent=true；[guard receipt](resource-guard-receipt.json) 记 reaped 后释放锁。[独立复核](NAV32-VERIFICATION.json) 再 `ps -p 2741,2865` exit1/空输出，两把锁用非阻塞 exclusive flock 均 free，没有强行解锁。
- [网页 final receipt](trial-web-final-receipt.json)：acknowledged=true、end_reason=browser_ack；真实网页 final-ack POST HTTP200。保留 [结束页面全文](NAV32-final-browser.txt) 与 [完整网页图](NAV32-final-full.png)。

## 输入与存储窗口

- 启动前执行原 [ab_preflight.py](../../passive-timing-delivery/v25-r10-zero-key-review/ab_preflight.py)：UUID 正确、双锁 free、没有既有 QEMU/runner、冻结源和两臂 CPIO/candidate pins 通过；实际只启动 A。初始结果见 [NAV32-PREFLIGHT.json](NAV32-PREFLIGHT.json)。没有重跑历史离线测试。
- runner inputs_unchanged=true；收尾独立重新计算全部 **14 项 input_checks** 和 **22 个 SOURCE-FREEZE 源文件**，全部匹配；完整路径、预期/结束后 SHA 在 [NAV32-VERIFICATION.json](NAV32-VERIFICATION.json)。不是只检查静态 runner 支持的按键容量。
- [启动前存储](NAV32-PRE-RUN-STORAGE.json)：2026-11-04 **08:47:35–09:02:35 PST**，严格沿用上一轮 PRE-RUN-STORAGE.json 的 kernel USB/APFS predicate、timeout25s，exit0/no timeout/no matching event。
- [本轮存储窗口](NAV32-RUN-STORAGE.json)：**09:02:40–09:16:49 PST**，覆盖启动、输入、End 和清理；同 predicate/timeout25s，exit0/no timeout/no matching event。原 stdout、SHA、stderr 与 argv 均保存。仅证明该谓词在此窗口没有查询到匹配记录，不能当作存储全面可靠性证明。

## 可复核产物

- [NAV32-STEPS.json](NAV32-STEPS.json)：32 步完整 ACK、原生行/偏移、目标、PNG SHA、确认和同钟延迟。
- [NAV32-web-http-evidence.json](NAV32-web-http-evidence.json)：真实浏览器所发请求和响应 body；回读浏览器记录，未重放请求。
- [NAV32-VERIFICATION.json](NAV32-VERIFICATION.json) / [复核脚本](NAV32-verify.py)：只读已有原始证据与输入，验证后只在当前 run 写分析 JSON；不启动/控制 VM、浏览器或 guest。
- [NAV32-SHA256SUMS](NAV32-SHA256SUMS)：本报告、本轮派生证据、全部网页/原生 PNG 和关键原始串口/回执/诊断原始文件的哈希清单；不包含自身。14 项外部输入与 22 源文件的完整哈希另在 verification 中。

本轮指定导航验收已完成，没有待执行 VM 动作。全菜单设置功能、实机、20 分钟长时稳定性、偶发零帧根因、坏/全零 ring 的独立诊断运行分支仍未验证；没有把这些未验项写成通过。
