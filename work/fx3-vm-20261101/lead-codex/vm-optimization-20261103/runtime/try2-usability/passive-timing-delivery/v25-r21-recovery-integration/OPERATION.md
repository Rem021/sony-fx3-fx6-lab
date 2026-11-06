# r21 离线候选操作合同（尚未获 VM 授权）

仅限单个独占操作员、一个 `fx3-deadline-*` 自有 tab 和每轮唯一持久 `ledger.json`。本候选复用 r18 runner；后续真实测试仍须 coordinator 另行批准。测试预算：最多 8 个已接受键、10 次显式点击尝试、每个 guest step 最多一次未入队恢复、全轮最多两次恢复。`operator_click.py` 在调用原 PAGE 按钮前按当前状态/步数核 8 键门，先 fsync 保留 attempt 槽，再执行一次 DOM click；不直接 POST，不自动 arm。任何调用回执未知或 ledger 预留未解即 End，不尝试新键。

1. 启动现有候选并安装 `operator-helpers/deadline.js`、以唯一 nonce `arm`。操作员亲看当前完整图后，显式运行 `operator_click.py` 并传真实已审 `--reviewed-sha`、`--reviewed-generation`、目标说明、唯一 receipt 和同一 ledger。旧 SHA/gen 会拒绝且占用 unknown 槽，应 End。
2. 只在 `fx3KeyAttemptOutcome()` 对本次 attempt 给出 `not_posted` 或 `explicit_rejected_unqueued` 后，将它的 attempt/document/launch/key/base_step/expected_step/点击帧/nonce 按 `recovery_tools.check` 格式保存为独立 `binding.json`。若是 accepted 或 unknown，保留原 20 秒看图确认/End 流程；绝不走恢复。
3. `recovery_tools.py capture` 在 `step-N/attempt-ID` 的唯一输出目录保存当前只读图和前后身份，供操作员**实际亲看**。这是未入队审阅图，绝非菜单成功或许可。
4. 操作员另一次明确调用 `recovery_tools.py cancel --review review-result.json --target <非空说明> --ledger <同一ledger>`。CLI 在已预留恢复名额后调用同页 JS，先只读 GET 状态并重核 attempt、原 nonce/due、当前有效已加载图和本地资格；只取消对应的原测试 alarm。审阅图可已成历史，此时结果标 `historical_review_not_current`；取消后产生新的当前截图，但它**未获视觉批准**，必须由操作员另行亲看，之后另起显式 `operator_click.py`，装新唯一 nonce。该 CLI 不 confirm、不重 arm、不发 guest 键。
5. 任何拒绝、未知、原生错误、End、当前图无效、截图丢失或 ledger `reserved_unknown` 都按失败合同 End。已取消但当前截图失败也不得发下一键。GET 只是瞬时快照，`server_atomic_permission=false`；取消不能证明随后任何新键可用，下一次仍受原 SHA/gen server gate。

脚本化 fixture 的 `target` 文字和截图是测试数据，**没有真实操作员语义看图**。三原辅助继续保留旧 20 秒/8 秒截止；`deadline.js` 除 PAGE 指纹外未改。旧失败运行与原“409 即 End”合同不回溯。
