# FX3 r21b 单次独立看图恢复演练：passed

本次授权的唯一离线完整链 **passed**：两次明确 MENU POST（一次原后台409未入队、一次202接受）、一次独立看图后的未入队恢复、一次完整菜单独立视觉确认及原explicit_confirm、实际guest **0**。A原alarm在 **8566.300ms** 取消，B在 **8521.700ms** 匹配历史ACK后取消；两个原20秒due均不变。没有重发、复用nonce或自动按SHA批准。

End/finalACK、原dispose、本轮浏览器与服务关闭全部通过，无清理错误；PID和端口独立核实消失。只证明这一次离线工具链，不证明8键VM、首帧稳定性、设备能力或FX6开机；没有QEMU/guest/设备操作或部署。上一r21失败轮原样保留。

## 授权、输入与目录边界

Task `task_2036cb0e6c75` / Dispatch `ctx_832894b219cf` 正式授权准备及一次离线演练，冻结交付消息 `msg_e1c9294f7a85`，前次失败回执 `msg_5a1e392b886a`。只在 interaction-operator-rehearsal-r21b 写新文件；只复用前轮6份源码，没有复制证据、once标记或ledger，创建新nonce A/B、新launch、新session及新端口。无其他agent。

卷UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 前后匹配，Mac根不是Git仓库。最终r21的指定4个pin、40源码、11依赖、14固定输入和SHA256SUMS的145项交付在准备与结束后全匹配。DELIVERY-MANIFEST files映射为144项，SHA256SUMS含其自身为145项；不混用计数。上一failed的88项交付及固定REPORT/SHA256SUMS均前后匹配，仍为failed，未改动任何文件。

| r21固定入口 | SHA256 |
|---|---|
| REPORT.md | `561408987f1b9ad98b7b0adce3c2134edfdd7d1a90044bf635c5e2bc45635443` |
| SOURCE-FREEZE.json | `31ee6b1d00fecfc5ac53e874b144230d2430208277c295d74c4a804fbe1135ec` |
| SHA256SUMS | `dcbbb11fc1942a480b8624e53d769e29b93fec3c884401811cc0599fea3b02ef` |
| DELIVERY-MANIFEST.json | `99bb474b8bcdfdcb9909e53f7b0608c6f0e203d3fd1168f8e06c1abce3162a90` |

原PAGE/TrialState、deadline、bounded capture、explicit_confirm、recovery与operator_click全从原冻结r21路径调用，源码未变；canonical PAGE SHA `f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab`。实际输入的绝对路径与SHA在config、DEPENDENCY-BEFORE/AFTER、BASE-SOURCE-INPUTS；本轮运行前8份源码冻结于SOURCE-FREEZE，运行后逐份匹配。finalize.py仅在清理后增加，用于读已有证据，不开服务或浏览器。

## 两项修正与计时前检查

1. **完成状态修正。** 本轮fixture接受B后先发布完整历史PNG，再由共享的 `fixture_contract.complete_review(state)` 调用原 `require_visual_review(1,'visual_changed',True)`，没有修改helper放宽条件。生产run_trial_v25_diag_r3.py:604–606只在visual_pending时update；607仅在visual_changed/no_change_observed时进入最终分支，629才调用require_visual_review。原bounded_capture.js审阅阶段也只接受后两种状态。精确源码、行号及SHA见SOURCE-CONTRACT-COMPARISON。
2. **真实异常路径修正。** `operate.run_action`本身包含try/except，CLI和import共用该路径；异常记录失败、调用cleanup回调、再重新抛出非零。未再只把清理放在__main__。清理读原alarm状态；若accepted/unknown alarm仍armed，不为dispose强行取消，记录后关闭自有document说明timer随文档结束。此次成功链已cancel，可正常dispose。

计时前只做两项定向检查，没有重跑整套r21测试。PREFLIGHT-FIXTURE-STATE用同一complete_review函数和原TrialState，在无server/browser/arm条件下确认review_required=true、visual_state=visual_changed、input_received=true。PREFLIGHT-EXCEPTION通过子进程调用实际run_action入口注入预期异常，清理回调用无browser测试替身，确认恰好调用一次End/cleanup回调且子进程非零；action、confirm、arm、key的测试替身记录均可复核。预期的子进程非零是该定向检查通过条件，不是一次计时演练失败；不会产生正式FAILURE或ledger。两项检查全部通过后才prepare浏览器。

OPERATION已事先准备所有命令、捕图失败校验和失败清理。捕图原CLI与外层均要求exit0、精确合格status、此次独占新目录、普通非symlink PNG/hash一致；失败不展示旧图。SOURCE-FREEZE包含实际运行代码和两项preflight代码；本轮没有失败重试。

## 本次实际看图与独立工具边界

- **初始亲看。** prepared-page中HD Fixed-59.94fps、AF-C、底部图标清楚，0/8、帧211，无菜单，MENU可用、End完整可见。保存真实判断后才进入工具一。
- **工具一：A明确MENU→原409→recovery capture。** 原operator_click预留attempt后点击原DOM按钮；后台在原state.lock内publish代次变化211/gen1→212/gen2，并持续持锁重入原submit。原submit完整返回本request_id匹配的409 `accepted:false/enqueued:false`，原rejection为sha_mismatch+generation_mismatch，pending_count=0、steps=0。前端未伪造attempt/alarm，未直接POST。原recovery capture成功，合格新PNG在该同次工具结果真实展示。
- **接图后亲看，再下一工具仅取消A。** 实际看见NO CARD，无完整菜单；右侧“本次按键未被接收”“网页不会自动重发”清晰，0/8、帧212。保存判断后，工具二仅调用原recovery cancel A，0confirm、0新键、0重arm；原nonce/due与完整cancelled事件匹配，elapsed<20000。取消后另一个新文件截图在工具二结果返回，不能把取消算作视觉批准。
- **再亲看取消后新图，再另一工具B。** 再次看到NO CARD和拒绝提示，0/8、帧212，MENU/End可见；明确取消没有批准画面。工具三才arm新nonce B，再原operator_click一次MENU，后台202、原pending_count=1，受控fixture仅消费该假键并发布完整历史菜单。原bounded capture返回新的合格截图，在同次工具结果展示。
- **亲看完整菜单后，工具四才confirm。** 此次返回图中Setup > Area/Date、45/59、Language/English、Area/Date/Time Setting整条橙色焦点及右箭头、NTSC/PAL Selector、左侧工具箱、底部Close均清楚完整。知道这是fixture历史图后，才在另一次工具明确调用原explicit_confirm。原确认HTTP200匹配request_id/step/seq/gen/PNG、guest_input_written=false，当前原七键门ready，随后取消同一B nonce，due不延长。

四份真实判断分别保存在initial-visual-judgment、rejection-visual-judgment、current-after-cancel-visual、accepted-menu-visual-judgment。原helper的图SHA只约束身份，未由脚本替操作员做语义批准。两份恢复截图像素hash相同，但文件和调用均为新的；原CLI独占mkdir和外层普通文件/路径校验证明没有复用旧截图。

## 本轮身份、HTTP、PNG和ledger

| 身份 | 本轮值 |
|---|---|
| session / viewport | `fx3-deadline-operator-r21b-b83358633d9e-74ca3f17` / 1280×1200，单tab |
| URL | `http://127.0.0.1:52524/` |
| launch | `eaf767d2-d2fb-421f-a062-dc70cfb5de25` |
| A nonce / attempt | `c9c50d56-6b22-4834-bf04-9cfa9abfdd28` / `1ab761ff-1c75-485b-a24d-db9412ff4945` |
| B nonce / attempt | `5ddc8de6-3263-44e7-86af-da110ff3f9fc` / `e96e6a99-983a-4f64-a6d7-89480b5d1908` |
| confirm request_id | `d1d4d07e-f757-4070-8a56-ef85685f5591` |
| 确认的step / sequence / generation | `1` / `213` / `3` |
| 固件完整菜单PNG SHA | `60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292` |
| 返回的完整网页截图SHA | `3b7a1f330d4ce1412771b001ca85fc46bcfec4e025e40236d63eb08b47a8375e` |

原HTTP handler保留精确请求body和原响应，用同一HTTP记录id关联请求/响应，再以attempt绑定nonce；见HTTP-OWNERSHIP及fixture-events。记录Host/Origin等，排除X-Trial-Token。HTTP实际POST为browser-ready200、start202、key409、key202、confirm-visual200、stop202、final-ack200各一次；confirm不写guest键。接受后的input_received为fixture给出的受控状态，不是本轮guest执行证据。

PNG-IDENTITIES分别记录三份历史固件PNG源SHA、sequence/gen与四类浏览器截图身份，不混用：standby211/gen1，NO CARD212/gen2，完整菜单213/gen3。bounded截图前后身份稳定，原capture返回精确qualified_screenshot_for_operator_review；最终confirm的expected、HTTP200 body、当前frame与capture中的完整图SHA/step/sequence/gen一致。

ledger由原CLI在eval前fsync预留；旁观线程保留8条变化，实际捕到两个attempt与一个recovery的reserved_unknown及最终值。最终attempts=2，均click_invoked（不等于两个accepted）；recoveries=1，cancelled_unqueued_alarm_only、confirmed_cancelled、delivered_requires_separate_operator_review；无未决预留。没有按键自动重发或多余恢复。

## 原20秒、工具时间与可测边界

浏览器performance原点 `1793836232863.8`。完整armed/cancelled/disposed事件在deadline-dispose、原辅助receipt和OPERATOR-TIMELINE。

| alarm | armed_ms | 原due_ms | cancelled_ms | elapsed_ms |
|---|---:|---:|---:|---:|
| A | 17719.800000012 | 37719.800000012 | 26286.100000024 | 8566.300 |
| B | 35478.600000024 | 55478.600000024 | 44000.300000012 | 8521.700 |

两个due始终等于对应armed+20000，无重arm/延期。完整事件仅installed1、armed2、cancelled2、disposed1，无expire/end_click/重复arm。

| 同域host边界时差 | 毫秒 |
|---|---:|
| A_return_prepared_to_cancel_tool_entry | 8132.355 |
| cancel_return_prepared_to_B_tool_entry | 9088.837 |
| menu_return_prepared_to_confirm_tool_entry | 7671.351 |
| bounded_CLI | 384.799 |
| explicit_confirm_CLI | 405.902 |
| End_to_finalACK_HTTP_responses | 219.649 |

只同钟域相减，不把host_ns与performance跨原点相减。返回准备边界是落盘校验后、图像编码/传输前的宿主点；与下一工具入口间隔包含工具传递、视觉判断和调度，不能拆成模型纯思考耗时。模型实际接图与看完时刻无仪器，均unknown，判断落盘时间不冒充实际完成时间。

完整PNG在受控后台立即发布，随后保持稳定，以隔离工具链时序；截图前后身份一致不等于VM首帧稳定或性能结论。此前刷新竞争专项测试没有在本轮重跑。

## End、finalACK和资源关闭

- /api/stop HTTP202 写出：2026-11-04T23:51:22.748241+00:00
- /api/final-ack HTTP200 写出：2026-11-04T23:51:22.967887+00:00

先End及原PAGE finalACK，再原dispose（B已cancelled）、browser close、仅SIGTERM本轮fixture，server.shutdown/server_close/join完成。CLEANUP errors=[]、final_ack_seen=true、server_thread_alive=false、phase=finished；浏览器session info active=false/pid=null。PROCESS-EXIT-VERIFICATION独立核实fixture PID34922与自有browser后台PID34925均消失，127.0.0.1:52524 connect_ex=61（关闭）。fixture退出码因准备parent已退出不可wait，记unknown，不声称exit0。成功dispose和browser/server关闭分别有证据，没有强行取消accepted/unknown alarm。

RESULT分项全部passed；总计 **2 key POST=1拒绝+1接受，1 recovery、1 confirm、1独立接受菜单视觉确认、实际guest0、重试0**。AUDIT-RESULT只审计保留证据，未再启动服务/browser/计时演练。前后依赖及本轮运行前8源均不变，上次failed仍保留。

## 适用范围与索引

结果只支持本次离线操作员链。真实VM最多8键、首帧稳定性、设备能力、API16/QEMU/双锁实跑生命周期、FX6开机均未由此验证；下一轮真实VM由协调端另行安排。本轮修正后未动原r21 helper或用户入口。

[RESULT](RESULT.json) · [时间线](OPERATOR-TIMELINE.json) · [HTTP归属](HTTP-OWNERSHIP.json) · [PNG身份](PNG-IDENTITIES.json) · [原confirm receipt](explicit-confirm-receipt.json) · [原A取消receipt](recovery-cancel/cancel-result.json) · [前后依赖](DEPENDENCY-AFTER.json) · [两项预检](PREFLIGHT-RESULT.json) · [源码合同对照](SOURCE-CONTRACT-COMPARISON.json) · [清理](CLEANUP.json) · [进程端口复核](PROCESS-EXIT-VERIFICATION.json) · [交付清单](DELIVERY-MANIFEST.json)。每份*-process保存完整argv、退出码、stdout/stderr及host起止时间，源码差异仅本轮脚本，见r21-to-r21b-local-source.diff。
