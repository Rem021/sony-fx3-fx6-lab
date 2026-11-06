# FX3 第 1 键 MENU 只读取图 r3：原生 ACK 后等待状态修复

**结果：r3 仅是离线宿主候选，未启动 VM、未部署或修改原 PAGE/runner/guest/原闹钟。** 原 r2 在真实 run `v25gate-n64-r17-07c897a7` 中把合法 `steps=1,busy=true,visual_state=visual_pending,input_received=true,review_required=false` 当作错误，584.6ms 内拒绝；原始 `operator-step-01/capture/capture-result.json` 记录 0 截图、0 确认。现已同时读取该运行 owner 封存的 `MENU8-RESULT.md`，其明确将 8 步链记 failed；不能把该失败称为 guest 绘制故障。

## 源码状态图与证据层级

| 状态 | 源码依据 | r2失败轮直接观测 | 本轮fixture实际覆盖 |
|---|---|---|---|
| 原 PAGE click 后旧 status `steps=0,awaitingStep=1` | `trial_web_v22_navigation_review.py:391-395,372-374`，HTTP202 不立即更新 lastStatus | 是，raw capture `state_transition` | 是，原按钮一次 HTTP202 |
| `steps=1,busy=true,visual_state=input_pending,input_received=false` | `TrialState.submit:94-115` 置 busy；runner `:728-729` 原子 `trial.update` 置 step/visual/input | 是，raw capture `step_one_processing` | 是，延迟 0.4s 发布，PAGE 后续 status 消费 |
| `steps=1,busy=true,visual_state=visual_pending,input_received=true,review=false` | `pending_visual_v20.py:27-40` 在原生 down/up 后未满足后续帧条件时返回 visual_pending；runner `:606-607` 只更新 visual/input，未清 busy；`TrialState.update:54-57` 同锁写入 | 是，raw capture 最后诊断，r2 在此拒绝 | 是，模拟 ACK 于 2s 发布且保持 busy |
| `visual_changed` 或 `no_change_observed` → `review=true,input_received=true,busy=false` | runner `:608-628` 取得有效帧后调用 `TrialState.require_visual_review:117-125`；分类器 MENU 的 no-change 有 30s 上限 | 失败轮未达到，不能推定会达到 | `visual_changed` 分支实际覆盖；`no_change_observed` 只静态核对，未用 30s fixture 重演 |
| 原 PAGE 载入固件图并启用确认 | PAGE `showFrame:316-334`、`tick:338-380`、`enableKeys:274-279` | 未达到 | 实际浏览器完成图 SHA/gen 与按钮门 |

另核 runner `:491,502,507,600-605` 的原生关机/unknown ACK 会进入错误或停止；`:529` 在**前次无变化键迟到画面**可单独写 visual_pending、归因未知。r3 仅限定第 1 键 MENU，没有把这个其他路径的 visual_pending 无条件视为 ACK。原生 ACK 是队列送达证据，不能单凭此认定菜单处理完成。

## 修复

仅派生 `bounded_capture.js` 调整状态机：step1 未 review 且 busy 时，`input_pending/false` 和 `visual_pending/true` 两种与原 runner 写序一致的组合继续有界等待；其余组合逐字段拒绝，并记录 `visual_state` 诊断。到最终 review 仅接受 `visual_changed` 或 `no_change_observed`、`input_received=true,busy=false`，再等原 PAGE 加载的参考 PNG SHA+generation 与 frame 一致、原确认按钮启用，才截一次图。后验继续拒绝截图期间换图、nonce/due/document/step 变化或不足 8s 余量。明确 409、送达未知、原生/渲染错误、终态、异常步号均即时拒绝；仍固定原 8s 页内等待、20s alarm、8s 保留，不发 guest key、confirm/cancel/End，也不作菜单语义判断。

## 离线结果与限制

最终 `evidence/run-b20f5821/RESULT.json` 为 `passed=true`：原 5 类必要场景与原 PAGE MENU click 回归共 6 组；另在一组内逐项注入并验证异常 step、native error、render invalid、terminal 四个拒绝，共 10 份回执。新增真实浏览器 fixture 的原按钮 HTTP202 一次；首次页面是 `steps=0,awaitingStep=1`，继而经 `step_one_input_pending`、`step_one_visual_pending_native_ack`、`ready_loaded_review`，7s 才发布冻结完整参考固件 PNG，约 7586ms 返回一张合格网页截图，后验原闹钟尚余约 12396ms。辅助本身 guest key/confirm/alarm mutation 均为 0，浏览器关闭回执 `active=false,pid=null`；最终截图已人工查看，是旧固件 PNG 加离线 PAGE 的**fixture 图**，不代表新 VM 菜单通过。7s 发布和 2s ACK 均是人为 fixture 时序，不是固件性能测量。

r3 仍未做新的操作员“看图→显式确认→同 nonce 取消”演练；8s 只是浏览器等待上界，CLI/截图及人工判断会占原20s预算。上次包装器失败却 exit0 的缺口只在 `OPERATION.md` 明确集成方三门检查，本任务未修改其冻结脚本。精确 `r2-to-r3.diff`、`SOURCE-FREEZE.json`、`DEPENDENCIES.json` 和 `SHA256SUMS` 供复核；未动既有运行或候选。
