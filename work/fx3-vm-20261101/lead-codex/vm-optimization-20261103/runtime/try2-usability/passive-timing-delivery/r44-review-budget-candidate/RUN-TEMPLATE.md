# r44 后续独立调度模板（本轮未执行，不含 Start 授权）

协调端另行分配真实 task/dispatch/session 和全新 run-dir 后，沿用原协议：prepare → 原完整 preflight → launch_prepare → start_and_wait → 逐键独立审阅 → cleanup/audit。**本轮没有执行以下任何一条命令。**

- 候选根：`/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r44-review-budget-candidate`
- profile：`r44-review-budget-60s`
- label / native run 前缀：`v44review-n64-r44`
- run-dir 必须直接位于候选 `run-inputs`，名字含新 task 后缀；不要复用离线 binding 目录。
- 包固定为 `../r42-command-timing-package`，不新建包、不降级回退。

```sh
export CAND="/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r44-review-budget-candidate"
export RUN="$CAND/run-inputs/r44vm-task_<新task后缀>"

python3 -B "$CAND/prepare_run.py" \
  --run-dir "$RUN" \
  --task-id task_<新task后缀> \
  --dispatch-id ctx_<新dispatch> \
  --session fx3-deadline-r44-<独占session>

export FX3_NAV_RUN_DIR="$RUN"
python3 -B "$CAND/runtime-wrapper/preflight.py"
python3 -B "$CAND/runtime-wrapper/launch_prepare.py"
python3 -B "$CAND/runtime-wrapper/start_and_wait.py"

# 之后按 $RUN/CLI-TEMPLATES.json 逐动作执行；不合并审阅、不自动确认。
```

`launch_prepare.py` 内含的准确 runner argv：

```text
python3 -B $CAND/run_trial_r24_review_snapshot.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2 --r35-diagnostic-package
```

动作模板（以生成的 `CLI-TEMPLATES.json` 为准）：

```sh
python3 -B "$CAND/runtime-wrapper/operate.py" standby_review "<实际看图后的判断>"
python3 -B "$CAND/runtime-wrapper/operate.py" click 1 "<NAVIGATION-PLAN 目标>"
python3 -B "$CAND/runtime-wrapper/operate.py" pin "<实际看观察图后的明确选择>"
python3 -B "$CAND/runtime-wrapper/operate.py" confirm "<实际看固定图后的判断>"
python3 -B "$CAND/runtime-wrapper/operate.py" observe "<看上一观察后的明确判断>"
python3 -B "$CAND/runtime-wrapper/operate.py" recovery_review "<看 cancel 后新图后的判断>"
python3 -B "$CAND/runtime-wrapper/operate.py" recovery_cancel "<看归因未入队新图后的判断>"
python3 -B "$CAND/runtime-wrapper/operate.py" reject "<语义不符或不确定，立即原 End>"
```

结束：

```sh
python3 -B "$CAND/runtime-wrapper/cleanup.py"
python3 -B "$CAND/runtime-wrapper/audit_after.py"
```

Node 返回路径：`return-tools/short_tool.mjs` 的 `bind(<新的绝对RUN>)`；每次操作读取当次返回，实际查看 PNG，再由人工填写语义判断。60 秒 alarm 不自动 pin、不自动 confirm、不重置；`SNAPSHOT_TTL=20.0` 保留，pin 后须在 20 秒内确认。

**审批前置**：本模板只在用户明确批准、协调器复核候选后使用；未批准时继续使用 r42。
