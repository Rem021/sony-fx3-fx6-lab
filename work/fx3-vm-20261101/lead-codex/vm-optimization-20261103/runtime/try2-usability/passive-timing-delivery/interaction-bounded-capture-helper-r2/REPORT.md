# 原 FX3 第 1 键 MENU 有界取图 r2：离线修复

**结果：宿主离线候选通过，未运行 VM、未部署、未修改原 PAGE/固件/既有冻结辅助。** r2 在原 8 秒页内等待、原 20 秒闹钟和至少 8 秒确认余量内，容许已点击 MENU 后原 PAGE 的正常状态轮询过渡；仅当 step1 review、输入已收、已加载参考固件 PNG SHA+generation 与状态一致时返回待人工审阅截图。它不自动判断菜单、不点击确认、不取消闹钟、不发键。

## 失败事实与修复范围

上次唯一操作员 fixture 见 `../interaction-operator-rehearsal/REPORT.md`：模拟 MENU HTTP202 写出于 21:27:58.044962Z，v1 的 before eval 在 21:27:58.100Z 运行，先于下一次 `/api/status` 于 21:27:58.340667Z 返回；v1 页内 0.4ms 抛 `phase_or_input_gate_not_ready`，截图/确认/取消均为 0。该失败轮没有逐字段的 PAGE 变量采样，因此不能把某一个布尔条件冒充直接观测的唯一根因。原 PAGE 源码显示 click 先置 `awaitingStep=lastStatus.steps+1`，HTTP202 后只清 `busy`，后续 tick 见 `s.steps>=awaitingStep&&!s.busy` 才清 `awaitingStep`；这一顺序解释了为什么 v1 的即时全条件门过早。

r2 仅改派生 `bounded_capture.js` 的只读状态机及其后验确认按钮可用检查。`steps=0,awaitingStep=1` 且无拒绝/未知/错误时等待；step1 尚处理且 status busy 时等待；step1 review 已建立但 PAGE 尚在完成 ack handler、清 awaiting 或加载图时等待；其他 step、无待处理 key 的 step0、step1 无 busy 又无 review、明确 key 409、未知送达、render fault、原生/终态、nonce/due/document 改变立即拒绝。拒绝回执携带 `diagnostics` 的逐字段 PAGE/状态/闹钟快照；状态切换另记 `state_transition`，避免用组合 reason 猜具体现场。后验仍要求同 SHA/gen、原 due 与至少 8 秒余量；不宽容旧图或 A→B→A 新 generation。

## 定向验证

最终 `evidence/run-a5bee753/RESULT.json` 为 `passed=true`，6 项：v1 五场景（中间→参考、8s 无匹配、错 nonce、原 20s alarm 到期、截图时换图）和新增真实原 PAGE MENU 按钮 click/HTTP202 后的延迟状态场景。新增 fixture 初始 `steps=0,review=false`，**未提前 prepare review**；原 `TrialState.submit` 接收一次 key427，约 0.4 秒后发布 step1/review，约 7 秒后发布历史完整 PNG。捕图调用前实际 PAGE 快照是 `steps=0,awaitingStep=1,hostBusy=true,review=false`；r2 的页内轨迹先记 `accepted_menu_waiting_for_status`，后记 `ready_loaded_review`，取得完整参考图网页截图。模拟后端 key HTTP202 为 1，确认请求为 0；捕图辅助发 guest key、确认、闹钟 mutation 均为 0，原 alarm 仍 armed。这里的 0.4s/7s 是 fixture 指定延迟，不是 guest 性能值。

新增场景的同一 host monotonic：arm 411771.103441，MENU HTTP202 411771.120932，捕图调用 411771.128969，step1/review 发布 411771.531134，完整 PNG 发布 411778.146034，before eval 退出 411778.229909，截图 411778.230015–411778.283204，after eval 退出 411778.293189，CLI 返回 411778.294279；总捕图约 7164ms，后验仍剩约 12810ms。网页 `performance.now()` 与 host monotonic 未直接混算。已实际查看最终 `actual-menu-click/menu-reference-page.png`：fixture 显示 English 与橙色焦点的完整 Setup/Area/Date 菜单；固件图来自冻结旧 run `trial-final.png`，网页图文件 SHA 不能充当固件 PNG SHA，也不证明这次有原生 MENU 处理。

## 限制与交付

当前仅离线 host PAGE/TrialState/Chrome 验证。r2 没有重复上次真实操作员的“看图→独立调用原 `explicit_confirm_cli`→同 nonce cancel”链，更无 VM/原生 down/up/done、API16 或生命周期结果。8s 仅是页内等待上限，CLI/截图总耗时不作硬实时保证；调用方必须同时核退出码、JSON qualified 状态和本次截图路径存在，失败不可沿用旧图。下一操作员演练需单独修其包装器失败 exit0，并逐段记录人工看图/确认/ACK/取消时钟；不能把本 fixture 的自动发布参考图当自动确认。

精确变更见 `v1-to-r2.diff`；源码、输入与本目录交付哈希见 `SOURCE-FREEZE.json`、`DEPENDENCIES.json`、`SHA256SUMS`。保留全部失败 fixture 原件和本目录早期测试回执。
