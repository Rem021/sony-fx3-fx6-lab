# 后续独立调度模板（本轮未执行，不含 Start 授权）

协调端另行分配真实 task/dispatch/session 和全新 run-dir 后，沿用 prepare→原完整preflight→launch_prepare→start_and_wait→逐键独立审阅→cleanup/audit流程。目录必须直接位于本 r42 runner 的 `run-inputs`，名字含新 task 的后缀；不要复用 `preflight-926a20c9ff87`。

```sh
python3 -B <绝对r42-runner根>/prepare_run.py --run-dir <新的绝对run-dir> --task-id task_<新ID> --dispatch-id ctx_<新ID> --session fx3-deadline-<独占session>
```

设置 `FX3_NAV_RUN_DIR` 为该新目录，按其 `CLI-TEMPLATES.json` 和已批准运行政策执行。launch 包含的准确 argv 为：

```text
python3 -B <绝对r42-runner根>/run_trial_r24_review_snapshot.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2 --r35-diagnostic-package
```

profile必须 `r41-entry-timing-r42`，native run 前缀必须 `v41timing-n64-r42-`，package必须固定新r42。实际QEMU argv/源快照/manifest/CPIO/DTB/身份应与本轮计划和固定摘要核对；原20秒与8accepted/10attempts/2recoveries不因参数32放宽，32是原runner容量。

工具返回使用本目录 `return-tools/short_tool.mjs` 的 `bind(新的绝对run-dir)`，逐个 `click`/`observe`→实际看返回图→显式 `pin`→实际看固定图→`confirm`；具体语义判断由实际审阅填写。不可合并审阅或自动选图，不确定即原 End。失败不重发、不读旧返回；保留 r39 每次独占 cleanup 原始证据和失败清理回执。

结束后先取得**该轮原 startup-observation 首cleanup记录**的有效 cutoff（schema/errors/省略数/范围均核对），再只读使用封存解析器。已直接读取原源码 CLI，精确参数为：

```text
python3 -B <DEL>/r41-command-entry-timing-candidate/parse_command_timing.py <该轮serial.log> --run-id <该轮原run-ID> --cutoff-byte <该轮原有效截止整数> --output <该轮全新解析输出.json>
```

缺失 cutoff/字段/身份、截断/交织仍unknown。只在guest MONOTONIC域解释 entry→return及同线程有序相邻gap，不视为CPU/FIFO纯等待/HTTP可见或全局End原子状态。r35解析器仍只离线读出，不参与ready/End。
