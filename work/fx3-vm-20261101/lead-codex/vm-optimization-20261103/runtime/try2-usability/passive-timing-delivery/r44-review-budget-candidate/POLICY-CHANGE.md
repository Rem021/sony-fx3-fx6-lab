# r44｜整步审阅期限政策候选变更（未生效）

**状态：仅离线候选；未启用、未部署、未运行。** 本文是可供审批的变更说明，不是运行授权。当前项目运行政策仍为 r42 的 20 秒；只有用户明确批准且协调器另行调度后，才可按本文第 6 节在全新 run-inputs 中执行。

## 1. 变更摘要

| 项目 | 旧（r42，当前有效） | 候选（r44） |
|---|---|---|
| 整步操作员审阅期限 | 20 秒（`DEADLINE_MS=20_000`） | **60 秒（`DEADLINE_MS=60_000`）** |
| 起算点 | 每次 arm | 每次 arm，单次 60 秒 |
| 重复 arm | 不延长 | 不延长 |
| 恢复／observe／confirm | 不重置期限 | 不重置期限 |
| 到期动作 | 一次原 End | 一次原 End |
| 取消 | 正确 nonce 在期限内 cancel | 正确 nonce 在 60 秒内 cancel；迟 cancel 先 expiry |
| Pin 后固定副本 TTL | 20.0 秒 | **20.0 秒（保留，未延长）** |
| native 接收检查 | 12 秒 | **12 秒（保留，未改）** |

60 秒只扩大“整步人工审阅”的外层 alarm；pin 后固定副本仍只有 20 秒 TTL，因此 confirm 必须在 pin 后 20 秒内完成、且整个动作仍受同一个 60 秒 alarm 约束。没有把 20 秒 TTL、12 秒 native 检查或任何其他边界改成 60 秒。

## 2. 精确改动范围

候选根：`DEL/r44-review-budget-candidate`。共 **13 个源码/数据文件改动** + **CORE-SOURCE-FREEZE.json 重新生成**；r42 SOURCE43 中其余 **29 个条目逐字节未改**。完整 old→new hash 与逐条原因见 `CANDIDATE-DELTA.json`、`CANDIDATE-POLICY.json`；完整 unified diff 见 `receipts/r42-to-r44-source.diff`。

### 2.1 期限与 guard（12 个文件）

| 文件 | 具体范围 |
|---|---|
| `operator-helpers/deadline.js` | `const DEADLINE_MS = 20_000` → `60_000`；`status().deadline_ms`、`current.deadline_ms`、`due_ms=armed_ms+60000`、setTimeout 均随常量 |
| `operator-helpers/recovery_cancel.js` | `first.deadline_ms !== 60000`；cancel 回执 `elapsed < 60000`；event `elapsed_ms < 60000` |
| `operator-helpers/snapshot_read.js` | alarm `deadline_ms === 60000` 身份检查 |
| `operator-helpers/recovery_readonly.js` | alarm `deadline_ms`、当前 `deadline_ms`、`due-armed`、cancelled receipt `deadline_ms`、输出 `alarm_due_exact` 共 5 处 |
| `operator-helpers/planned_navigation_click.js` | `alarm_document_matches` 的 `deadline_ms === 60000`；注释同步为候选 60 秒 |
| `operator-helpers/postkey_read.js` | post-key `deadline_ms`、`due-armed`、错误 JSON 的 `alarm_due_exact` 共 3 处 |
| `operator-helpers/snapshot_confirm.js` | confirm 前 alarm `deadline_ms === 60000` |
| `operator-helpers/recovery_observation.py` | `alarm_budget_ms == 60000`；失败标签改为 `alarm_60s_browser_identity` |
| `runtime-wrapper/cleanup.py` | End 后 alarm 分类：顶层 `deadline_ms`、`due-armed`、`current.deadline_ms` 三处 60000 |
| `runtime-wrapper/operate.py` | arm 断言 `arm['deadline_ms'] == 60000` |
| `r35_package_selection.py` | profile=`r44-review-budget-60s`，label=`v44review-n64-r44`，`APPROVED_HOST` 指向候选；新增 r42 输入 SOURCE/CORE 硬 pin |
| `prepare_run.py` | 仅 scope/observe 模板文字标注“候选 60s”；无 timer 或动作行为改动 |

### 2.2 自冻结 hash 绑定（1 个文件）

| 文件 | 具体范围 |
|---|---|
| `return-tools/return_adapter.py` | `OPERATE_SHA` 更新为候选 `runtime-wrapper/operate.py` 的 `e0aca533…e5e`；`CORE_FREEZE_SHA` 更新为候选 CORE38 的 `b9d92bc2…9f1`。仅 hash pin，无行为改动；否则 Node 返回路径会拒绝候选 operate/CORE |

`CORE-SOURCE-FREEZE.json` 随候选文件重新生成（`b9d92bc2…9f1`）；`SOURCE-FREEZE.json` 为 `3ab27924…95c`。没有把候选 CORE 冒充为与 r42 相同。

## 3. 明确保留（不改）

- `run_trial_r24_review_snapshot.py` **整文件逐字节未改**：`1f8cf2b7…4fcd28`。其中 `native_input_deadline_error` 的独立 12 秒接收检查及唯一调用点原字节保留。
- `trial_web_r24_review_snapshot.py` **整文件逐字节未改**：`450d1e33…d5df2`。PAGE/server 与 `SNAPSHOT_TTL=20.0` 原字节保留。
- `review_page_r24.js` `26aaf20a…8e4a1`、`confirm_page_r24.js` `0bd31e9c…b37c72`、`PAGE-IDENTITY.json` `7f4b2f3a…a0a`、canonical PAGE script `852c83d6…55b` 未改。
- API16 restore `timeout=20` 未改。
- 启动 180 秒（`start_and_wait.py` `e62309eb…36d4`）、总运行 8 分钟、runner `--max-minutes 8 --max-steps 32` 未改。
- 8 accepted／10 explicit attempts／2 unqueued recoveries／每步 1 次 recovery 未改（`NAVIGATION-PLAN.json` `4a695e1a…f02f`）。
- 首观察不早于 arm+5 秒、每 attempt 最多 3 次观察未改。
- 严格 nonce/document/launch/PAGE 身份、独立看观察图→pin→看固定图→confirm、不自动判断/confirm、不合并人工审阅，全部保留。
- 原 End 优先与幂等回收（单锁 owner、`already-cleaned`、dispose 前分类）保留；`cleanup.py` 只改预算常量。
- 固定 r42 封存包复用：candidate `857c2b7a…11806`、CPIO `59c5850a…3c63`、DTB `5aa2beac…855b`、load address `0x440000000`；不新建包、不降级回退。

## 4. 逐项语义

1. arm 时记录 `armed_ms`，`due_ms=armed_ms+60000`，只创建一个 timer。
2. 20 秒时仍 armed；60 秒到期时 `expire` 只调用一次原 End，随后 `sealed=true`。
3. 正确 nonce 在 due 前 cancel：state=cancelled，不触发 End；之后不再触发。
4. 迟 cancel：若 `performance.now() >= due_ms`，先执行 expiry，expiry 赢；stale timer 不再二次触发。
5. 同 nonce 重复 arm：记录 `duplicate_arm_no_extension`，due 不变；不同 nonce 在 armed 期间拒绝。
6. 身份错误（nonce 格式、document、timeOrigin、launch、PAGE fingerprint、URL）在 arm 或动作前拒绝。
7. End 不可见或页面已 stopping/finished：expiry 记录 `expire_refused`／`already_stopping_or_disabled`，不误点其他控件。
8. confirm 仍须对固定图做独立人工审阅；60 秒 alarm 不使 confirm 自动化。
9. 总运行 8 分钟包含启动与人工审阅；不能保证 8 个步骤各用满 60 秒。预算耗尽仍按原逻辑失败，不自动延长。
10. snapshot 的 20 秒从实际 pin 创建起算，与 60 秒整步 alarm 相互独立；confirm 必须同时满足二者。本文没有把 60 秒写成快照 TTL。
11. 归因未入队 → 独立 recovery observation → 取消 → 复核 → 新 nonce 新 attempt 的既有恢复流程保留；60 秒不重置、不延长、也不替代该流程。

## 5. 未执行的验证（避免误解）

- 没有启动 VM、浏览器服务、guest、QMP、部署、相机、USB、SD 或刷写。
- 没有真正运行 runner、server 或菜单八步；没有性能、延迟、固件绘图超时、零帧根因或菜单通过结论。
- 只做了离线 fake-clock、6 个 guard 行为、宿主绑定、prepare/import-only、纯函数/静态测试。离线通过 ≠ VM 通过。

## 6. 用户批准后未来确切调用命令（现在不得运行）

输入封存：dispatch sealed pins 为 r42 SOURCE43 `6f8d7e92…`、CORE38 `07600354…`、package candidate `857c2b7a…`、CPIO `59c5850a…`；最终验证套件的 start/end 47 项 before/after 见 `receipts/input-hashes-before-after.json`，内容一致。该 before 是最终验证开始时刻，不是候选编辑前快照；原始身份以 sealed pins 为准。

以下命令只用于**全新任务、全新 dispatch、全新 run-dir**；`<...>` 必须由协调器/new dispatch 填入真实值。`RUN` 必须直接位于候选 `run-inputs` 下，名字含新 task 后缀；session 必须匹配 `fx3-deadline-*`。不要把 `preflight-task_00000000-r44binding` 当作运行目录。

```sh
export CAND="/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r44-review-budget-candidate"
export RUN="$CAND/run-inputs/r44vm-task_<新task后缀>"

# 1) 只生成 run inputs；不启动任何进程
python3 -B "$CAND/prepare_run.py" \
  --run-dir "$RUN" \
  --task-id task_<新task后缀> \
  --dispatch-id ctx_<新dispatch> \
  --session fx3-deadline-r44-<独占session>

# 2) 以下命令设置 run 上下文并执行原协议
export FX3_NAV_RUN_DIR="$RUN"
python3 -B "$CAND/runtime-wrapper/preflight.py"
python3 -B "$CAND/runtime-wrapper/launch_prepare.py"
python3 -B "$CAND/runtime-wrapper/start_and_wait.py"

# 3) 按 $RUN/CLI-TEMPLATES.json 的固定模板逐动作执行；示例：
python3 -B "$CAND/runtime-wrapper/operate.py" standby_review "<实际看图后的判断>"
python3 -B "$CAND/runtime-wrapper/operate.py" click 1 "<NAVIGATION-PLAN 目标>"
python3 -B "$CAND/runtime-wrapper/operate.py" pin "<实际看观察图后的明确选择>"
python3 -B "$CAND/runtime-wrapper/operate.py" confirm "<实际看固定图后的判断>"
# 失败/结束时：
python3 -B "$CAND/runtime-wrapper/cleanup.py"
python3 -B "$CAND/runtime-wrapper/audit_after.py"
```

`launch_prepare.py` 内部实际 runner argv 固定为：

```text
python3 -B $CAND/run_trial_r24_review_snapshot.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2 --r35-diagnostic-package
```

Node 返回路径使用候选 `return-tools/short_tool.mjs` 的 `bind(<新的绝对RUN>)`；每次 `click`／`observe`／`pin`／`confirm` 必须逐次读取当次返回、实际看图，再由人工填写语义判断；不合并、不自动重试。profile 必须为 `r44-review-budget-60s`，native run 前缀必须为 `v44review-n64-r44-`，包必须固定 r42 封存包。

**本文件中的命令在本轮一条都未执行；执行前必须由用户明确批准并由协调器复核本候选、回执和边界。**

## 7. 审批与回退

- 审批请求只能由协调器在复核后向用户发起；worker 不在本轮直接请求用户审批。
- 用户未批准：继续以 r42 的 20 秒政策为准；本候选保持隔离，不写入任何运行入口、固定硬件配置或旧输入。
- 用户批准：按第 6 节在全新 run-inputs 执行，结束后仍按原协议取当轮原 End cutoff、保留失败/清理证据。
- 不做包降级或旧包回退；r42 原字节未被本候选修改。若候选验证失败，回退到 r42 即可，不需要改回任何已写文件。
