# FX3 交互缺口单轮验收：未通过

**本轮未补足 C4、OK、MENU 取消/关闭/重开的交互验收。** 真实待机已看到，但第 1 次网页 MENU 请求即被宿主画面身份门以 HTTP409 拒绝，未入按键队列，runner 实际键数 **0**；未重试，也未继续发键。113.466468 秒后本轮已 End 并正常回收，完整健康/恢复/输入完整性检查通过。功能验收失败、后续功能未知与清理通过分别记录，不能把成功捕获拒绝证据写成原生功能通过。

另有程序偏差：浏览器记录的 MENU 请求至 End 相隔 **47.543s**，超过任务要求的 30 秒停止界限；20 秒条件等待后继续核对 HTTP 和截图造成额外延迟。该项明确为 failed，没有隐藏或据健康通过抵消。

## 单轮身份

- 新自然 run：`v25diag-web-r6-b6209581`；runner **PID8729**、QEMU **PID8927**；网页 `http://127.0.0.1:56804`；agent-browser 独立会话 `fx3interaction-b83358633d9e`。
- 使用固定 A/r3 r10：`PYTHONDONTWRITEBYTECODE=1 python3 .../v25-r10-independent-diagnostics/run_trial_v25_diag_r3.py --max-minutes 10 --max-steps 32 --port 0`。实际最多 16 键政策保持，本轮 **1 个 HTTP key 尝试、0 个接受键、0 个宿主看图确认**；没有 internal-hoststep、procdiag、observer 自动 Stop、新探针、5000ms/QMP 时限调整或第二轮。
- runner 创建 UTC `2026-11-04T17:32:26.670518+00:00`；真实页面 Start 请求 `17:32:50.634Z`，首个 MENU 请求 `17:33:54.212Z`，End 请求 `17:34:41.755Z`，final ACK 请求 `17:34:44.555Z`。Start 202、End 202、final ACK 200 各一次。最初一个本地 Start 点击因 viewport 外保护未触达，滚动后实际页面 Start 仅一次，没有额外 HTTP Start 或 VM。
- SOURCE-FREEZE SHA256 `65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce`；runner `9b70b1281c130e909deb0ae7091cb8738c44f304d847db2162a4a21635ae2ba0`；CPIO `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`，candidate `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`。
- [command.json](command.json) 保存实际固定 QEMU/kernel/DTB/Backup、4-core MTTCG、无 icount 参数；[输入复核](INTERACTION-VERIFICATION.json) 结束后重新计算 **14 项 inputs 和 22 个冻结源**，全部匹配。部署入口 `outputs/fx3-vm-trial/FX3菜单.command` SHA256 仍为 `28c677bcce47e54acd9ec00909dde5c784df2e5a8b4fd84663f8effe1a10e3fb`；没有修改入口、README、ledger、冻结源码、guest、平台或运行政策，没有 FX6、实机、USB/SD 操作或镜像复制。

## 结果分项

| 项目 | 本轮状态 | 实际证据和边界 |
|---|---|---|
| 待机可见 | passed | 亲看原生待机图标；[待机网页 PNG](INTERACTION-standby-ready.png) |
| 首次 MENU HTTP 送达输入队列 | **failed** | HTTP409 明确拒绝，未到 202；runner key_steps=0 |
| 原生 MENU 打开 Setup > Area/Date | unknown | 请求没有进入本轮键队列，未测原生菜单处理 |
| UP 到 Language | unknown | 未发送，实际页面始终待机 |
| C4 菜单 Language 帮助 | unknown | 未发送 C4；没有进入 Playback/Delete |
| MENU 从帮助返回 | unknown | 未到帮助，无返回操作 |
| OK 打开 Language 列表 | unknown | 未发送 OK，未进入语言列表 |
| MENU 取消语言列表并保留 English | unknown | 未到列表，未选择或保存任何语言值 |
| MENU 关闭到待机、重开菜单 | unknown | 未到菜单，未发送后续 MENU |
| 30 秒目标未确认即 End | **failed** | 请求至 End 记录时间47.543s；等待后核对造成延迟 |
| 单轮、无键重试、无设置编辑 | passed | 一次 Start、一个409 key请求、一次End；confirm次数0 |
| health/protocol/render/lifecycle/diagnostic | passed | 冻结 runner 原始 [receipt.json](receipt.json)，并单独复核原始诊断与恢复 |
| API16、QMP退出/reap/PID/双锁/finalACK | passed | 详见下面原始文件与独立核验 |
| 输入哈希和限定存储窗口 | passed | 输入/冻结源/入口 SHA 一致；限定查询exit0无匹配，不能证明全面存储可靠 |
| **总体交互缺口验收** | **failed** | 仍缺全部指定的 C4/OK/MENU后续功能实测 |

## 首个拒绝的原始链

1. 在 [INTERACTION-standby-ready.png](INTERACTION-standby-ready.png) 亲看待机后，真实页面 MENU 按钮只点击一次。[HTTP 原始回执](INTERACTION-web-http-evidence.json) requestId=`8760.239`，request body=`{"key":427,"observed_sequence":196}`，status=409，response body=`{"error":"当前画面已变化或不可用，请等待并查看最新画面。"}`；未收到 accepted=true/next_step。
2. [请求后网页 PNG](INTERACTION-01-MENU-target.png) 仍为待机、0/32。文件名中的 `target` 是采集时的预期标签，**不是目标出现或通过**；[该时状态](INTERACTION-01-browser-state.json) 仍 steps=0、review_required=false，没有可确认的 guest 步骤。没有点击宿主看图确认。
3. [冻结源码定位](INTERACTION-host-gate-evidence.json)：`trial_web_v22_navigation_review.py` SHA256 `3cf9544f08fbdf62dee46420170f5fb85dfae1c656b8a24c062c7b055d64fde1` 的94–115行，所收到错误字符串唯一对应101–104行 compound guard，早于113行 `pending.append` 和115行202。这证明拒绝发生在宿主 submit 的画面有效性/身份检查，不能归因于 guest Language 调用或原生接收失败。
4. 拒绝前浏览器 status 记录 frame196、generation30、PNG SHA `2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e`，之后记录 frame200、generation31、SHA `e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4`。帧/世代在邻近观察中变化，符合“已显示帧与宿主最新帧竞争”的假设；**拒绝点没有原子状态快照，不能判定 guard 中究竟哪项为真，也不能仅凭 NO CARD 闪烁证明唯一原因**。浏览器记录时间是宿主 wall 时间，不拿它与 guest monotonic 相减。
5. 完整 [serial.log](serial.log) **10,357,786 B**，SHA256 `a92831eb5428c1d0cd154023cbf8894adeae2cbb9f0bb6f59d8230f8a472df1e`；独立字节扫描 `FX3_KEY_INPUT_RECV `、`FX3_SYNTH_KEY step=`、`FX3_KEY95_STEP_DONE step=` 各0；没有 trial-input-events 或 trial-step 文件。原始 runner 也报 key_steps=0。这里记录“未观测到本轮输入”，不把缺 marker 泛化为任意原生调用绝对没发生。
6. 全日志字面 `-1018` 为0，runner serial_health_failure=null；这轮 **没有进入 Language**，因此没有复现或排除历史 Language `-1018`，也不能把它称为本次根因。没有重新发 MENU 来绕过拒绝。

[INTERACTION-ATTEMPTS.json](INTERACTION-ATTEMPTS.json) 保存唯一尝试的请求/拒绝、未分配 step、原生观测次数、目标结果和截图完整 SHA256。[INTERACTION-web-http-evidence.json](INTERACTION-web-http-evidence.json) 包含 key/start/end/final-ack 请求与响应 body、拒绝前后6笔 status；仅移除临时认证 header，都是回读真实浏览器记录，未脚本调用或重放这些 POST。

## 结束诊断和恢复

- [receipt.json](receipt.json)：duration=113.466467958s，health/protocol/render/lifecycle/diagnostic_readback=true，host_observer_error=null，stop_cause=end_trial_button；native_shutdown_after_ready=false、native_model_power_off_after_ready=false。`menu_verified=false`、`browser_visual_acceptance=null` 保留原值。
- QMP stop ACK + query-status paused/running=false 后完整读 [osd-ring-final.bin](osd-ring-final.bin) **16,777,216 B**，SHA256 `fb968e3aae686ba6bcc5c8c17e93b61fd15c7b2ab7d52b96fb00dd27dbe7acb9`；parse_valid=true、readback_complete=true、invalid_or_torn_slots=[]、dropped_busy_writer_events=0。
- 再证明暂停后，10 秒 optional预算内独立读 [ui-gate-counters.bin](ui-gate-counters.bin) **65,536 B**，SHA256 `cd98c97ecd1e72121e70d36545120162b8eba7221bc68e116c4daece9952f128`，所有已声明optional区 complete、errors=[]。magic=0x3145544147335846、version2、activebank1、publication serial29585；count4..11=`[4125,4125,3412,713,696,4101,4098,4125]`，gate_hist=`[1,10,702,2628,417,367]`，backlog_skip3412、time_skip17、time_pass696、peak_gate278、timer_dequeue4098、a12/a13_nonzero0、last_a18=2。是全程终态逐字段原子镜像，不能当作请求拒绝瞬间或跨字段一致事务快照。
- [restore103-receipt.json](restore103-receipt.json)：20秒原合同内 **1.309379s** 完成 guest ACK+原字回读。最后 [API16 raw](restore103-005-api16.bin) 为 `000b00b4fd7bbba9fd030091f35301a9`，SHA256 `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`；[header raw](restore103-005-header.bin) SHA256 `e8668d6dda28642898c97841bc9ae5d653e42b7924dc2a7675e5c6d6bb2e1cd6`。独立 `<8s8Q` 解包 F100FILE、shutdown_control=0x100c1ea9、restore_status=0、restore_seen=1；native_unbind_return=0，host 没有写原代码。
- quit_sent=true、QEMU exit0、process_reaped=true、PID_absent=true；[guard](resource-guard-receipt.json) 记正常回收。独立 `ps -p 8729,8927` exit1/空；两把运行锁用非阻塞 exclusive flock 均 free，没有强行解锁。
- [final receipt](trial-web-final-receipt.json) acknowledged=true/end_reason=browser_ack，网页真实 final-ack HTTP200；[结束文本](INTERACTION-final-browser.txt)、[稳定结束图](INTERACTION-final-stable.png) 和 [最终浏览器状态](INTERACTION-final-browser-state.json) 均保留。早期结束截图的图像区曾短暂空白，稍后稳定截图亲看仍为待机；最终 raw PNG 非全零、frame695/shownSHA 与 `trial-frame.png` 相同、renderFault=null，不能把该次网页截图空白认作已证 guest 黑帧。

## 外盘与输入

- [启动前预检原文](INTERACTION-PREFLIGHT.txt)：卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`、双锁 free、无既有 QEMU/runner、22源码与 A/B pins；只执行一次 A，runner 在 guest 启动前验证固定 inputs。
- [启动前存储查询](INTERACTION-PRE-RUN-STORAGE.json) 2026-11-04 **09:17:13–09:32:13 PST**；[本轮窗口](INTERACTION-RUN-STORAGE.json) **09:32:21–09:35:55 PST** 覆盖创建/Start、拒绝、End及清理。两次严格沿用 r10A 的 kernel USB/APFS predicate、timeout25s，exit0/no timeout/no matching event，stdout/stderr/argv/SHA完整保留；只排除该谓词下匹配记录，不证明整个外盘可靠性。
- [INTERACTION-VERIFICATION.json](INTERACTION-VERIFICATION.json) 保存14项输入与22源码的完整路径/SHA、入口未变SHA、原始API16/header验证、最后UIbank、ring、PID、锁和串口扫描。读取和分析没有触发新运行，也没有重跑历史测试。

## 官方预期与适用边界

读取日期 **2026-11-04**，来源均为 Sony **ILME-FX3 Ver.2 or later** 官方 Help Guide：

- [Using the menu](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867589.html)：方向键遍历树，中心键进入条目对应设置/执行屏，MENU可取消返回并退出菜单。
- [In-Camera Guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867604.html)：选中菜单/Fn条目后按Delete显示条目说明，是本轮预期 C4 帮助的依据。
- [Using the Delete button](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000844148.html)：播放图像上的删除动作和菜单中的说明用途不同；本轮没有进入播放删除、格式化或重置。

这些说明给出原厂操作预期，不证明本 VM 适配链能执行相同功能，也不授权写入设置。由于首个宿主请求被拒绝，本轮没有直接验证任何上述新增原生交互。

## 交付与未完成项

[INTERACTION-SHA256SUMS](INTERACTION-SHA256SUMS) 封存本报告、原始HTTP/截图、派生证据、串口/receipt/ring/UIbank/API16与恢复头等；[校验回执](INTERACTION-HASH-CHECK.txt) 记录每项结果。未改既有NAV32或部署入口。

仍缺：C4 Language可读帮助、OK Language列表、MENU取消/返回/关闭/重开的真实逐图验收；HTTP409 compound guard 的拒绝瞬间字段亦未知。没有改冻结源、解除输入门、制造keepalive或补跑；本次 worker_done 必须 outcome=failed，功能未验状态不改写为passed。
