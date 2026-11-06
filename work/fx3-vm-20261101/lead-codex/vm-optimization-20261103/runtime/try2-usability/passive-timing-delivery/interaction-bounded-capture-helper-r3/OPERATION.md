# 第 1 键 MENU 的有界只读取图辅助

**r3 差异：**r2 容许 `steps=0,awaitingStep=1` 后，原 runner 仍会依次报告 `steps=1,busy=true,visual_state=input_pending,input_received=false` 与原生 ACK 后的 `steps=1,busy=true,visual_state=visual_pending,input_received=true`。r3 在原 8 秒/20 秒闹钟预算内等待这两个明确状态，直到原 runner 建立 step1 review 且页面加载完整参考图。旧 r2 在后一状态过早拒绝；工具仍未部署。

此目录是未部署的离线候选。它只为**已经授权并武装原 20,000ms 闹钟的单个自有页面**等待已知第 1 键 MENU 完整菜单参考 PNG，然后做一次网页截图和前后身份核验。参考固件 PNG 来自既有 run `v25gate-n64-r17-c33f8c46/trial-final.png`，SHA256 为 `60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292`。网页截图文件的 SHA 是另一种身份，不能填进原显式确认工具的 `--png-sha`。

调用前按原 `../interaction-deadline-helper/OPERATION.md` 在自有唯一 `fx3-deadline-*` session 安装原辅助、武装当前 nonce，并通过真实页面**人工只按一次** MENU。不要因本工具的参考 SHA 自动推断菜单语义。命令必须使用当前精确 URL、launch UUID、nonce 和从未存在的输出子目录：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 bounded_capture_cli.py \
  --session 'fx3-deadline-<本轮唯一名>' \
  --url 'http://127.0.0.1:<本轮端口>/' \
  --launch-id '<当前launch_request_id>' \
  --nonce '<当前已armed闹钟UUID>' \
  --evidence-dir '<本轮新目录>/menu-capture-01'
```

成功仅返回 `qualified_screenshot_for_operator_review`，其新目录含 `menu-reference-page.png` 和 `capture-result.json`。辅助在原 r17 PAGE、同 document/launch/nonce/due、step=1 的 `visual_changed` 或 `no_change_observed` review、已加载图与状态 SHA+generation 一致、无错误/停止/未知请求时，至多等 8 秒找到参考图。原闹钟还须剩余至少 8 秒；截图之后再核一次，SHA 与 generation 不得变化，sequence 可随同内容前进。参考图**只触发取图**，不代表这次画面的语义已经由人验收。

Agent 须让**同一个工具返回**附上图像，而非等待固定 6 秒后再另开一轮取图。例如在 `functions.exec` 中先运行以上 CLI，解析其 JSON 后，**同时**核 CLI `exit_code===0`、`result.status==='qualified_screenshot_for_operator_review'`、本次 `result.screenshot_path` 存在，才调用 `await tools.view_image({path: result.screenshot_path})` 并 `image(view.image_url)`；再亲自看图。任一条件失败都传播拒绝状态，不打开旧图。旧演练 `capture_once.py` 即使 helper 失败也 exit0 属调用方缺陷，本目录不修改冻结脚本。这样一次工具调用包含 CLI 和图像返回，但最终语义判断仍由操作员完成。可读 `capture-result.json` 的 `timeline` 逐项比较 tab、等待 eval、截图、后验 eval、回执写入的 UTC/host monotonic 时间。**这不是 8 秒总耗时硬上限**：8 秒只约束浏览器内等待；CLI/截图可额外耗时，截图后若不足 8 秒余量，结果必须不合格，原闹钟不会被延期或取消。

亲看当前新截图中的完整固件菜单，核 `before_eval`、`after_eval` 与图像内容后，才另行显式调用旧 `../interaction-explicit-confirm-helper/explicit_confirm_cli.py`，且须使用本次已审固件 PNG SHA 和相同 nonce。当前辅助没有 arm、guest key、confirm、cancel、End 或直接 HTTP POST 接口；失败不会重试、改 alarm 或自动确认。失败时可能留下一个**不合格**网页截图，不可据此发下一键。若已出现错误/未知送达/过期，按现有人工 End 和清理规约处理。

即使本工具在本地 fixture 成功返回，也不保证真实运行能在余下 20 秒内完成“看图→人工决定→原显式确认→同 nonce 取消”。下一验收门必须用轻量 fixture 实际演练这一完整操作员流程，分别记录截图返回、人工看图、confirm click、ACK、输入放行、cancel 的 UTC 与 monotonic 时间；模拟自动确认测试不能替代。当前没有 VM 授权。
