# FX3 r21 独立看图恢复演练：failed

本次唯一离线演练 **failed**，未现场重试。两次原 operator_click 明确 MENU 完成（1 次原后台真实 409 未入队、1 次 202 接受），一次独立看图后的未入队 alarm 恢复成功；B 接受后的 bounded capture 因本轮 fixture 的状态合同错误退出 2，没有合格菜单截图、没有 explicit_confirm、没有 B 取消。实际 guest 输入 **0**，未启动 QEMU/guest、未改固定 FX3 平台或用户入口。

失败后先 End、取得原 finalACK，再关闭自有浏览器及服务，最后封存证据。`dispose` 因 B 仍 armed 明确拒绝，不能算成功；浏览器/服务退出与端口关闭已独立核实。协调端消息 `msg_cb4489e73594` 要求保留此失败轮、不得重跑，已遵从。

## 授权、依赖与准备

Task `task_4f29d582e690` / Dispatch `ctx_5ed8bdf1e673` 授权本次准备并执行一次离线真实浏览器＋受控后台演练，引用冻结交付 `msg_e1c9294f7a85`。本次只写本目录，未改冻结件、旧目录或其他资源，无代理、VM、产品部署。

卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 前后匹配；Mac 根不是 Git 仓库。四个指定固定 SHA 全匹配；SOURCE-FREEZE 40 项、INPUT-HASHES 11 项、固定输入 14 项、SHA256SUMS 145 项前后逐文件匹配。DELIVERY-MANIFEST 的 files 映射为 **144** 项，SHA256SUMS 为 145 项（含清单本身）；未混用计数。精确 pin、路径和 SHA 见 config、DEPENDENCY-*。

canonical PAGE SHA 为 `f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab`。最初本地准备 gate 误去掉 script 首换行，SHA 因此不同；修正为精确 textContent 后通过，见 PREPARATION-CORRECTION。该准备错误发生在服务/浏览器/arm/点击前，不是另一次计时演练，未改冻结件。

原 PAGE/TrialState、deadline/capture/explicit_confirm/recovery/operator_click 均直接调用最终 r21 原件；没有导入 runner 的运行入口。计时前已准备所有操作命令、cleanup.py、独占路径、唯一 session/tab 验证、三份历史 PNG、初始网页截图和 6 项自有源码冻结。参考 r2 的退出码/精确 status/独占目录/普通非 symlink PNG/hash 校验及同钟计时；没有复用旧 PAGE 指纹。方法来源与 SHA 在 REFERENCE-INPUTS；[agent-browser 官方说明](https://github.com/vercel-labs/agent-browser)只核对 session/截图/close 工作流，r21 合同以冻结本地代码为准。

## 一次运行的实际工具与视觉判断

1. **计时前亲看** prepared-page.png：HD Fixed-59.94fps、AF-C 与底部图标可见，尚无菜单；MENU 可用、End 完整可见。保存判断后才 arm A、原 operator_click 一次 MENU。
2. **工具一：拒绝和只读接图。** 后台取得 `state.lock` 原 RLock，在同锁内通过原 publish 将帧211/gen1变为212/gen2，持续持锁重入原 submit。原 submit 返回匹配本 attempt 的 `409 accepted:false/enqueued:false`，原 rejection 记录 sha_mismatch、generation_mismatch、pending_count=0、steps=0。没有前端伪造 attempt/alarm，没有直接 POST。recovery capture 子进程 exit0、精确 `qualified_review_screenshot`；独占 recovery-review 新建普通 PNG/hash 验证通过，在同次 functions 工具结果实际展示。
3. **接图后亲看，再独立取消。** 实际看到 NO CARD 在画面上方，菜单尚未出现；右侧明确提示“本次按键未被接收”“网页不会自动重发”，计数0/8、帧212。保存真实判断后，下一独立工具调用只执行原 recovery cancel A：0 confirm、0 新键、0 重arm，原 due 不变，完整 cancelled event 匹配，elapsed **8367.100ms < 20000**。该工具返回取消后的新建 current-after-cancel.png。两张截图像素/hash相同，但属于两个新文件和两次捕图，未用旧图冒充。
4. **再亲看取消后的新图，独立决定 B。** 再次看到 NO CARD/拒绝提示、0/8、帧212，MENU/End可见，明确取消没有批准画面。另一个工具调用才 arm 唯一新 nonce B，再原 operator_click 一次 MENU。原 submit 202、pending_count=1；fixture 仅消费此假队列项，发布历史完整 Setup > Area/Date PNG，实际 guest=0。
5. **B 捕图失败即停止。** 同次工具调用原 bounded capture，exit2、精确 `no_qualified_screenshot`，reason=`Error: step_one_review_visual_state_unexpected`，screenshot_attempted=false。未展示旧图，未调用 explicit_confirm。准备时看过历史完整参考 PNG 不能替代此次接受后的独立接图；End 后截图仅作清理证据，不计入通过。

真实视觉判断在 initial-visual-judgment、rejection-visual-judgment、current-after-cancel-visual。模型实际接图和审完时刻没有仪器，均 **unknown**；落盘时间不冒充接图时间。

## 失败原因与原生产合同

**本轮 fixture 接线错误，未证明 r21 产品回归或 deadline 调度问题。** fixture_server.py 调用了 `state.require_visual_review(1,'visual_pending',True)`，使 review_required=true 与 visual_pending 同时存在。原 bounded_capture.js:82–83 要求审阅阶段为 `visual_changed` 或 `no_change_observed`；只在 review_required=false 的处理中允许 visual_pending，因此拒绝符合原合同。

原 run_trial_v25_diag_r3.py:604–606 在 visual_pending 时仅 update visual_state/input_received；607 仅在 visual_changed/no_change_observed 时进入最终审阅分支，629 调用 `trial.require_visual_review(host_step,visual.state,visual.visual_change_observed)`。pending_visual_v20.py 把 visual_pending 定义为 terminal=false、visual_change_observed=false；验收 test_helper_browser_integration.py:73 使用 visual_changed。精确行文、行号和 SHA 保存于 STATE-CONTRACT-COMPARISON。

完整历史图已在后台发布；bounded 首次状态为 accepted_menu_waiting_for_status，约 **83.7ms** 后拒绝，当时 B 原期限还余 **19787.900ms**。不是20秒预算用尽，也不是稳定 fixture 证明 VM 性能。另行授权的新任务应把 fixture 的完成发布接到生产一致的 `visual_changed` 审阅状态，保留原 helper 拒绝不一致组合的合同，不能改 helper 放宽条件。本轮脚本和 failed 不修改，不运行修正版。

另有失败清理接线不足：工具脚本导入 `run_action`，未经过 operate.py 的 __main__ 异常处理，故失败后操作员立即用下一独立工具发送 cleanup；并非脚本自动清理。下一任务应使用真实带异常处理的 CLI 入口，或把异常处理纳入实际被调用路径。本次未现场改写补跑。

## 身份、时钟、ledger 与 HTTP

自有 session `fx3-deadline-operator-r21-b83358633d9e-ccf2a6e7`，1280×1200，一个 tab，`http://127.0.0.1:51442/`；fixture PID33299。

| 身份 | 值 |
|---|---|
| launch | `bb9c2485-fe65-40d5-92d5-db1d5365fd86` |
| A nonce / attempt | `68a8332d-5712-481c-a333-03e298cd8a4f` / `c75de8c6-2738-41ff-998b-a35c8cce19da` |
| B nonce / attempt | `981ffb0a-f966-4fe3-bd97-289d70849308` / `40490ef1-0ef4-4311-8785-a879c5bac42e` |
| A performance arm / due / cancel | `10655.100000023842` / `30655.10000002384` / `19022.200000047684` |
| B performance arm / original due | `27933.80000001192` / `47933.80000001192` |

A 原 due 始终不变；完整取消 helper/events 在 recovery-cancel/cancel-result。B arm receipt 保留 A cancelled 和 B armed 事件；最后 bounded 诊断仍 armed，没有 B cancelled event，未臆造最终页内事件。关闭浏览器终止文档资源不等于成功 helper.cancel 或 dispose。

仅同钟域相减，不把 host_ns 与浏览器 performance 跨原点相减。原始工具边界/HTTP/fixture 和派生值在 OPERATOR-TIMELINE。

| 同钟时差 | 毫秒 |
|---|---:|
| A arm→cancel，performance | 8367.100 |
| 恢复图返回准备→下一 cancel 工具入口，host | 7769.955 |
| cancel图返回准备→下一 B 工具入口，host | 8819.719 |
| B bounded CLI 子进程，host | 148.287 |
| bounded失败返回→End HTTP响应，host | 3851.794 |
| End→finalACK HTTP响应，host | 216.815 |

返回准备边界位于图片编码/传输前，间隔混合工具传递、看图和下次调度，不能分解为模型纯思考耗时。模型实际收到/审完均unknown。

原 CLI 在 eval 前 fsync 预留两次 attempt 和一次 recovery；旁观线程实际捕获 reserved_unknown 与最终值，见 ledger-observations 的8条。最终 attempts=2，均 click_invoked（不能等同2个accepted），recoveries=1，状态cancelled_unqueued_alarm_only/confirmed_cancelled/delivered_requires_separate_operator_review，无未决预留。取消前后0新键、0confirm、0重arm。

HTTP-OWNERSHIP 按原 handler request/response id 保留精确请求body、原响应及归属nonce，记录 Host/Origin 等，不记录 X-Trial-Token。实际POST只有 browser-ready200、start202、key409、key202、stop202、final-ack200各一次，confirm-visual **0**。

PNG-IDENTITIES 单独保留固件fixture源图和浏览器整页截图身份：211/gen1 standby SHA `e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4`；212/gen2 NO CARD SHA `2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e`；213/gen3完整图 SHA `60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`。实际返回的两份恢复整页图 SHA均 `d1fd8dd6c74c43fee2e3fc94bb5e1a1dc1cc26ab0c0d88aaeef4bbf3bc79752e`。hash只核身份，不代替亲看。

## 清理、结果与下一步

End HTTP202：23:42:36.443977 UTC；原 finalACK HTTP200：23:42:36.660790 UTC。原 dispose 拒绝 `cancel exact nonce before dispose`，因为 B 仍 armed；未重试 dispose、未把拒绝包装成功。随后 browser close 成功，session active=false/pid=null；fixture SIGTERM 后 shutdown/server_close/join 完成，server_thread_alive=false、final_ack_seen=true。PID33299与自有后台PID33311均独立证实消失；127.0.0.1:51442 connect_ex=61（关闭）。fixture退出码因原准备parent已退出不可wait，记unknown，不声称exit0。

总计 **2明确点击、1拒绝、1接受、1未入队恢复、0独立接受菜单视觉确认、0explicit confirm、0实际guest、0重试**。RESULT逐项标failed/未执行；AUDIT-RESULT通过只表示失败证据自洽，不是演练通过。

仅证明本次 A 恢复子链、B单次明确接受和helper对不一致fixture的拒绝。8键VM、首帧稳定性、设备能力、API16/QEMU/双锁真实生命周期、FX6开机均未证明。协调端依据此failed另行安排修正fixture和下一轮，真实VM仍需单独安排。

## 交付索引

[分项结果](RESULT.json) · [完整时间线](OPERATOR-TIMELINE.json) · [HTTP归属](HTTP-OWNERSHIP.json) · [PNG身份](PNG-IDENTITIES.json) · [合同对照](STATE-CONTRACT-COMPARISON.json) · [失败记录](FAILURE.json) · [清理回执](CLEANUP.json) · [进程端口复核](PROCESS-EXIT-VERIFICATION.json) · [前后依赖核验](DEPENDENCY-AFTER.json) · [交付清单](DELIVERY-MANIFEST.json)。各 *-process.json 保存 argv、返回码、stdout/stderr 和边界；recovery-review/recovery-cancel 保存实际接图及原receipt，accepted-menu-capture 保存未捕图的失败receipt。
