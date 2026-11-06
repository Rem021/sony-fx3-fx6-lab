# r44｜60 秒整步审阅期限候选（离线准备与宿主验证）

**结论：候选已在隔离目录准备完成，并通过有限离线 fake-clock／宿主验证；没有启用新运行政策，没有启动 VM、浏览器服务、guest、QMP、部署、相机、USB、SD 或刷写。离线通过不等于 VM 通过，也不是固件绘图超时或性能改善的证明。**

任务：FX3 原固件宿主审阅流程的独立 r44 期限候选；不是此前被提供方拦截的 FX6 实现的重试，也未触碰 FX6 源文件。协调器验收后，才可由协调器向用户发起审批请求。

## 1. 输入与身份

| 项目 | 值 |
|---|---|
| 卷 | `/Volumes/KAFU2T`，UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`（已核实） |
| 项目根 | `/Volumes/KAFU2T/AI/Projects/Mac`（非 Git 仓库，未新克隆/整树复制） |
| 基线运行器 | `DEL/r42-command-timing-runner`；SOURCE43 `6f8d7e92…a89652`，CORE38 `07600354…1ba68` |
| 封存包 | `DEL/r42-command-timing-package`；candidate `857c2b7a…11806`，CPIO `59c5850a…3c63`，453213884 B |
| 固定 DTB | `5aa2beac…855b`；load address `0x440000000` |
| 基线证据 | `r42-command-timing-runner/run-inputs/r43-vm-53cced835047/REPORT.md`、`RESULT.json` |
| 输入前后 hash | `INPUT-HASHES.json`：dispatch sealed pins + 最终验证套件 start/end before/after（47 项，`content_unchanged=true`）；`INPUTS-BEFORE/AFTER.json` 是候选已存在后的 raw capture，不是编辑前快照 |

r43 的唯一运行 137.83 s，完整菜单 observe2 在 arm+17.56 s，20 秒 alarm 触发原 End，独立 pin 到 +33.486 s 才进入且被拒绝，1 accepted／0 pin／0 confirm，failed 保留，回收通过。该结果只说明 20 秒整步审阅窗口与工具链完成时间不匹配；**不能**据此声称固件绘图超时，也**不能**声称提速。候选不修改 r43 证据或其结论。

## 2. 候选范围与差异

候选根：`DEL/r44-review-budget-candidate`。只复制 r42 SOURCE43 所列的必要源码/数据，未复制历史 run、tests 矩阵或 CPIO；复用 r42 封存包，不生成新包。

| 清单 | 条目 | SHA256 |
|---|---:|---|
| 候选 SOURCE43 | 43 | `3ab27924f456209af961412b876cefa9d23b7f0230b10bc160103a8ef58d995c` |
| 候选 CORE38 | 38 | `b9d92bc251fb6da2577af7d7f50c2b646db9797000913b747327636c2e3999f1` |
| 输入 SOURCE43 | 43 | `6f8d7e926ae6a1387c42cb43f8e4c95ca74e3c51572a8dac1bee783868a89652` |
| 输入 CORE38 | 38 | `0760035499c8362eef3ee24c819d3b8f6cbed3bf156bf4ee8b09adc187b1ba68` |

- **13 个源码/数据文件改动**：12 个期限/身份/清理 guard 或 profile 绑定 + `return-tools/return_adapter.py` 的 `OPERATE_SHA`/`CORE_FREEZE_SHA` 自冻结 pin。
- **CORE-SOURCE-FREEZE.json 重新生成**，因此候选 SOURCE43 的 changed 条目共 14（含清单自身）；**29 个源文件条目逐字节未改**。
- 不是把所有 `20` 数字全局替换；r43 提到的原始 12 秒接收检查、20.0 秒 snapshot TTL、20 秒 API16 restore、180 秒启动、8 分钟总时长、8 accepted／10 attempt／2 recovery、arm+5 秒首观察均保留。
- 精确 diff：`receipts/r42-to-r44-source.diff`；机器可读差异：`CANDIDATE-DELTA.json`；逐文件改动原因：`CANDIDATE-POLICY.json`。

改动清单（完整 old→new hash 见 `CANDIDATE-DELTA.json`）：

| 文件 | 变更 |
|---|---|
| `operator-helpers/deadline.js` | `DEADLINE_MS` `20_000` → `60_000` |
| `operator-helpers/recovery_cancel.js` | 初次 alarm 身份、`elapsed`／event elapsed 上限 20000 → 60000 |
| `operator-helpers/snapshot_read.js` | `deadline_ms` 身份 20000 → 60000 |
| `operator-helpers/recovery_readonly.js` | alarm／cancelled receipt 身份与 due 差 20000 → 60000（5 处） |
| `operator-helpers/planned_navigation_click.js` | click 前 alarm document 预算 20000 → 60000 |
| `operator-helpers/postkey_read.js` | post-key alarm 身份与 due 差 20000 → 60000（3 处） |
| `operator-helpers/snapshot_confirm.js` | confirm alarm 身份 20000 → 60000 |
| `operator-helpers/recovery_observation.py` | `alarm_budget_ms` 60000；错误标签 `alarm_60s_browser_identity` |
| `runtime-wrapper/cleanup.py` | End 后 alarm 分类预算 60000（3 处） |
| `runtime-wrapper/operate.py` | arm 断言 `deadline_ms == 60000` |
| `prepare_run.py` | run scope／observe 模板文字标注候选 60 秒；无 timer 行为 |
| `r35_package_selection.py` | 新 profile/label、候选 `APPROVED_HOST`、r42 输入 SOURCE/CORE 硬 pin |
| `return-tools/return_adapter.py` | 自冻结 `OPERATE_SHA`／`CORE_FREEZE_SHA` 更新到候选；无行为改动 |

新 profile=`r44-review-budget-60s`，label=`v44review-n64-r44`；`r35_package_selection.py` 仅接受该候选目录和固定 r42 包，不提供任意包路径或缺包 fallback。

## 3. 60 秒整步语义

- 每个 attempt 一次 arm，`due_ms = armed_ms + 60000`；从 arm 起算，不由重复 arm、observe、recovery 或 confirm 延长。
- 20 秒时 alarm 仍为 `armed`；60 秒时只触发一次原 End，`sealed=true`，之后不再有第二次 End；
- 正确 nonce 在 60 秒前可 cancel；cancel 后原 End 不触发；
- 迟于 due 的 cancel 仍先走 expiry，expiry 赢，且只点一次原 End；
- 同一 nonce 重复 arm 不延长；不同 nonce 在 armed 期间被拒绝；
- 错误 nonce、document、launch 或 PAGE 身份在 arm／操作前拒绝；
- End 不可见或页面已进入 stopping/finished 时，expiry 记录拒绝，不会误点其他控件；
- `snapshot_confirm` 仍要求实际审阅固定图后独立 confirm；没有自动判断、自动 pin 或自动 confirm。
- 总运行 8 分钟包含启动与人工审阅；不保证 8 个步骤各用满 60 秒，预算耗尽仍按原逻辑失败，不自动延长。
- 归因未入队 → 独立 recovery observation → 取消 → 复核 → 新 nonce 新 attempt 的恢复流程保留；60 秒不重置也不替代该流程。

## 4. 保留边界（未改）

| 边界 | 证据 |
|---|---|
| native 12 秒接收检查及其调用 | `run_trial_r24_review_snapshot.py` 与 r42 全文件逐字节一致，SHA256 `1f8cf2b7…4fcd28`；函数源码与 r42 相等，调用点 1 处 |
| PAGE / server 与 `SNAPSHOT_TTL=20.0` | `trial_web_r24_review_snapshot.py` 与 r42 逐字节一致，`450d1e33…d5df2` |
| PAGE 身份 | `PAGE-IDENTITY.json` `7f4b2f3a…1a0a`；canonical script `852c83d6…55b`；`review_page_r24.js`、`confirm_page_r24.js` 未改 |
| API16 restore 20 秒 | 在未改的 `run_trial…py` 中保持 `timeout=20` |
| 启动 180 秒、总运行 8 分钟 | `runtime-wrapper/start_and_wait.py` 未改（`e62309eb…36d4`），`deadline=start_monotonic+180`；launch argv `--max-minutes 8` |
| 8 accepted／10 attempt／2 recoveries／每步 1 recovery | `NAVIGATION-PLAN.json` 未改（`4a695e1a…f02f`）；`runtime-wrapper/recovery_guard.py` 未改 |
| 首观察不早于 arm+5 秒；每 attempt 最多 3 次观察 | `postkey_read.js` 的 `wait.not_before_ms=wait.arm_ms+5000` 与 `review_tools` 计数逻辑保留 |
| End-first 与幂等回收 | `runtime-wrapper/cleanup.py` 仅改 alarm 预算常量；End 优先、单锁 owner、`already-cleaned`、dispose 前分类逻辑保留 |
| 严格身份与人工审阅 | nonce/document/launch/PAGE 校验保留；不合并审阅、不自动语义通过 |

说明：`SNAPSHOT_TTL=20.0` 是 pin 后服务端固定副本的保留期限，比 60 秒整步 alarm 更短；因此确认必须在 pin 后 20 秒内完成，而整个 observe→pin→confirm 仍受同一个 60 秒 alarm 约束。本候选**没有**延长该 20 秒 TTL。

## 5. 封存包与运行入口

复用 r42 包，不新增包：candidate `857c2b7a…11806`，CPIO `59c5850a…3c63`（453213884 B），DTB `5aa2beac…855b`，load address `0x440000000`。候选没有修改现有运行入口、固定 FX3 硬件配置、CPIO、内核、DTB、QEMU 或冻结旧输入；所有写入都在 `DEL/r44-review-budget-candidate` 内。

## 6. 验证回执

全部为离线 fake-clock／宿主测试；没有真正运行 runner、启动服务或 VM。

| 回执 | 用例 | 结果 | 证明内容 |
|---|---:|---|---|
| `receipts/fake-clock-deadline.json` | 14 | 14/14 | 安装 60000；20 秒仍 armed；60 秒一次原 End；60 秒前正确 nonce cancel；迟 cancel 先 expiry；重复 arm 不延长；错身份/页面/launch 拒绝；重装不重置；End 不可见/terminal 失败闭合 |
| `receipts/guard-behaviour.json` | 6 | 6/6 | 6 个浏览器侧 guard 以实际源码执行：60000 通过预算门，20000 被拒；`recovery_cancel` 的 60 秒 elapsed 上限拒绝 65 秒伪造回执 |
| `receipts/host-binding.json` | 10 | 10/10 | 43/38 清单与 13+1 改动/29 未改，CORE38 逐成员哈希；预算字面量无旧值；native12/snapshot20/PAGE/启动/8 分钟/8-10-2 保留；Python 预算函数接受 60000、拒绝 20000；operate 断言；selector/profile/package/CPIO 绑定；prepare→common→runner import-only；47 项输入在整套测试 start/end 采集且 content 不变 |
| `tests/python_pure_tests.py`（候选内补充套件） | 12 | 12/12 | 纯函数/静态边界复核；本轮实际复跑 |
| `receipts/VERIFY-RESULT.json`（顶层离线验证） | 12/14/6 | passed_offline_only | 汇总纯函数 12/12、fake-clock 14/14、guard 6/6；明确未启动 VM/browser/server/QMP/guest |
| `receipts/process/` | — | 完整 stdout/stderr | 仅 `prepare_run.py`、`common.py` import、`run_trial` import-only（审计 hook 阻断 subprocess/socket）；无 main 调用 |

Node v22.19.0；Python 3.14.6。`tests/fixtures/PAGE-script.txt` 是未改 PAGE 的测试提取，SHA256 等于 `852c83d6…55b`。

### 验证层级（不要把不同证据混为一谈）

| 层级 | 本轮实际证据 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| 静态字节保留 | `run_trial`／`trial_web`／PAGE／startup 等整文件 SHA 与 r42 相等；CORE/SOURCE 逐成员 hash | 这些文件未被候选改动 | 不能证明真实运行行为 |
| fake DOM/fake clock | `fake-clock-deadline.json` 14/14、`guard-behaviour.json` 6/6 | 实际 guard 源码在最小 fake DOM/定时器下的预算门与时钟语义 | 不是真实浏览器、真实 PAGE 渲染或真实工具往返 |
| 宿主绑定 | `host-binding.json` 10/10、`VERIFY-RESULT.json` | 清单、预算常量、Python 纯函数、selector/package、prepare/common/import-only 绑定 | 没有 server/VM/guest |
| 真实浏览器/VM | **未执行** | — | 未验证；离线通过不等于 VM 通过或提速 |

输入 hash 的采集边界也单独记录在 `receipts/input-hashes-before-after.json`：before 在整套测试开始前采集，after 在全部检查结束后采集；它不是“候选编辑前”快照，原始输入身份以 dispatch sealed pins 为准。

## 7. 未证明与限制

- **未启动 VM／浏览器／服务／QMP／guest**，因此没有真实渲染、真实工具往返、真实 60 秒时序或菜单通过证据；离线 fake-clock 通过不等于 VM 通过。
- 不能据此声称固件绘图超时、零帧根因、性能改善或完整八步通过；r43 的 failed 结果保留。
- `SNAPSHOT_TTL=20.0` 保留意味着 pin 后只有 20 秒可 confirm；这是用户审批时必须看到的真实边界，不是本候选的放宽项。
- `recovery_cancel.js` 的最终回执以 `first.deadline_ms==60000`、due 相等和 `elapsed<60000` 约束；它不单独比较 `receipt.deadline_ms` 字段（`recovery_readonly.js` 会）。本轮未改这一点，属于可选的后续加固，不影响当前 60 秒门。
- 本轮没有执行完整历史 11915 文件矩阵、旧 1398 项 preflight 扫描或真实 runner；只做了必要离线验证。未来真实运行仍须按 `POLICY-CHANGE.md`／`RUN-TEMPLATE.md` 的原协议执行。
- 候选目录中 `INPUTS-BEFORE.json`／`INPUTS-AFTER.json` 是候选已存在后的相邻原始采集（两次读取相隔约 0.0002 秒），只能证明该相邻读取一致；它们不是编辑前快照，也不能表述为“候选准备前后”覆盖。只有 `receipts/input-hashes-before-after.json` 的最终 host 验证窗口在整套测试 start/end 两端有覆盖（47 项，`content_unchanged=true`）。

## 8. 下一步

1. 协调器复核本候选、diff、清单、测试回执与保留边界；
2. 由协调器向用户发起审批请求（本 worker 不直接向用户请求审批）；
3. 用户明确批准后，才可按 `POLICY-CHANGE.md` 的未来命令在**全新** run-inputs 中执行；当前不得运行；
4. 未获批准则继续以 r42 为当前有效政策，r42 字节未被本候选改动。
