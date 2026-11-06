# r23：planned navigation 离线 harness passed

**新命名 helper、wrapper、冻结八步合同及必要离线验证已交付；未启动 VM、未部署。真实八步菜单仍待验。** 仅写本目录，卷 UUID 核对正确；原 r21/r21c/r22、运行入口与协调 ledger 未改。

## 实现

- `NAVIGATION-PLAN.json` SHA256：`4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f`。八步不变：MENU / UP / C4 / MENU / OK / MENU / MENU / MENU；[CONTRACT](CONTRACT.md) 定义每步完整后置条件及停止要求。
- 新 `operator-helpers/planned_navigation_click.py/.js` 从 r22 最小派生，去掉旧审图 SHA/gen 的两项输入许可，其余21项准入保留；增加 plan/step、前一步历史确认、文档及原 alarm 对齐。摘要 await 后单同步片段绑定当前 loaded frame，再最多一次原 DOM click；原 PAGE/server 全字节保留。回执明确 scripted_navigation=true、visual_review_at_click=false，并记录 plan、step、previous_confirm、nonce/document/launch、click-time frame；不伪称当前已审图。
- `planned_prerequisite.py` 核历史截图/验证回执及原 confirm 的文件/hash、step、launch、nonce、精确 SHA/gen；下一动作不要求当前帧复用历史 gen。初次需另记实际待机审阅，后续每步需真实新图和独立原 explicit_confirm。
- `runtime-wrapper/` 复用 r21c 实际 __main__ 接线；mode 差分只有计划动作/历史证据绑定、独立数据根与源码冻结、confirm 后精确历史 gen 核验、恢复新图独立审阅及必要收尾 audit。`prepare_run.py` 仅创建后续独立任务的参数/路径模板、空 ledger、源码冻结；当前未执行 launch/Start/cleanup runtime 链。见 [准备说明](PREPARATION.md)、`MINIMAL.diff` 和 `SOURCE-REUSE.json`。

## 针对性证据

`evidence/DYNAMIC-RESULT.json`：同一独占 session、原冻结 PAGE/TrialState、2×2 PNG 动态 backend，**8组通过**。历史视觉前提是明确 mock 的协议 oracle，绝不作为真人/代理实际菜单语义通过；真实原 PAGE capture/confirm 的协议效果另外保留原回执。

| 验证 | 结果 |
|---|---|
| 原20秒 alarm 内实际等待8.26秒，按0.4–1.6秒间隔反复 A→B→A，再明确调用单步 | 新gen11仍同初始SHA，绑定当前真实 loaded frame；1click/1POST/1pending；旧gen不是许可 |
| 原 capture_review/capture_after + 原 explicit_confirm，再显式下一planned step | 历史confirm精确gen11；下一点击gen12，两个独立调用合计2click/2POST；无真实视觉语义声明 |
| nonce失配、停止、无效loaded图 | 各0click/0POST |
| click后server代际变化 | 1click/1POST，原409 SHA+gen门，0入队 |
| 执行后eval回包丢失 | unknown，ledger阻止再发，仍只有1click/1POST |
| 实际新helper __main__：错plan、错step、step2缺前步确认 | 均host preflight拒绝，0click/0POST |

`evidence/HOST-RESULT.json`：**3个实际 operate __main__ 用例通过**，未注入 sys、common不导出sys；严格标明外部协议替身。覆盖未确认step2先拒绝并走End异常入口、confirm实参及历史图gen3精确绑定（不采用回包较新current_frame gen999）、跨步confirm拒绝；旧capture schema的跨步反例也拒绝。fixture协议通过不充真实看图通过。

`evidence/PREPARATION-RESULT.json`：实际 prepare CLI 生成新task独占目录，common导入核当前源码冻结/plan/config/空ledger；0 browser/runner/guest。`evidence/SYNTAX.json` 记录必要 Python 编译和 JS node --check。

首次动态fixture断言过强，要求点击帧必与旧图同SHA；实际候选已click_invoked，原始receipt/空submit trace/失败stderr保留在 `evidence-attempt1/`，不追溯改判。修fixture为确定的观测间隔回放、保留不等待匹配的8.26秒后显式调用，原候选门未放宽；随后7组通过记录保留在 `evidence-dynamic-attempt2/`，补齐原capture/confirm承接后的最终8组通过在 `evidence/`。host初次预期拒绝的异常类型漏捕已在测试驱动修正，旧失败stdout/stderr及目录保留；没有为本任务泛跑旧集成矩阵。

最终自有server线程、服务PID、12个browser PID和port均关闭，外层再次核验见 `evidence/FINAL-CLEANUP.json`。原输入前后hash与冻结核对在 `INPUTS-*.json`，本交付全量清单在 `SHA256SUMS`；没有写三个既有非冻结runtime输出。

## 结论边界

这次允许的是**新的预定义脚本动作**，不是旧human intent复活。每个真实 accepted 键后，后续操作代理仍必须实际看本步合格新图、单独确认；语义不符/原生错误/unknown即原End，不按结果补键。job run-to-completion仅约束同一浏览器同步片段，不能升级为server/guest或原生input-context原子证明；依据为[MDN执行模型](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model)（2026-11-04回读）。

下一步由协调员另派唯一一轮真实八步任务，使用新task/dispatch目录；本任务没有提前启动。八步真实菜单、人类连续视觉体验、长时稳定性和FX6均仍未验。
