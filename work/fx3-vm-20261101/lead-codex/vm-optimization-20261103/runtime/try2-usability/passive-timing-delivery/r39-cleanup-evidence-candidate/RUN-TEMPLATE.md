# r39 后续使用模板与回执读取

**模板不授予 VM、网页、Start 或部署权限。** 本任务只执行 prepare/preflight/import 和 host fixture。未来真实轮需新 task/dispatch/session，不沿用本轮离线身份。

## 只准备与审查

从项目根使用准确绝对路径，输出必须是 r39/run-inputs 的直接新子目录，名称包含真实 task suffix：

```sh
R39_ROOT='/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r39-cleanup-evidence-candidate'
python3 -B "$R39_ROOT/prepare_run.py" --run-dir "$R39_ROOT/run-inputs/FUTURE-TASK_SUFFIX" --task-id task_TASK_SUFFIX --dispatch-id ctx_DISPATCH_SUFFIX --session fx3-deadline-FUTURE_SESSION
export FX3_NAV_RUN_DIR="$R39_ROOT/run-inputs/FUTURE-TASK_SUFFIX"
python3 -B "$R39_ROOT/runtime-wrapper/preflight.py"
```

profile=`r35-diagnostic-r36-n64-r39`；相同 r36 candidate/CPIO、snapshot-tail/N64，准确 label=`v35diag-n64-r36-r39`，无任意路径或旧源 fallback。launch_prepare argv 构造未改：本 r39 同名 runner，`--port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2 --r35-diagnostic-package`。不在本任务执行它。

## 已授权真实轮的收尾（仅供后续调度使用）

显式 cleanup 仍使用 `python3 -B <r39>/runtime-wrapper/cleanup.py`。自动失败 guard 也只派发同一新源一次。每次调用创建 `cleanup-calls/<UUID>`，CLI stdout 是单个 JSON，准确副本在该目录 `return.stdout.txt`；完整子命令流与截图/HAR都在该独占目录，不再使用 run 根的 `traffic.har` 等旧固定位置。

| status | 含义/后续 |
|---|---|
| completed | 原 End 路径完成，绑定证明及资源检查合格；仍须独立 audit，原动作失败不变 |
| already-cleaned | 本次只复核此前强绑定完成证明与当前资源；引用 original_receipt，无 browser/End/HAR/dispose |
| busy | 当前有 kernel-lock owner；非 owner 未操作，不是 complete；不删锁、不自动重试 |
| unknown | 不足以证明完成，可能已有部分收尾；读本次回执，必要时由协调端明确处置，不能补键/Start |

`CLEANUP.json` 是 first/latest/completed 索引，不是完成证书；`CLEANUP-FIRST.json` 保留首次结果。`CLEANUP-COMPLETED.json` 的引用必须用 `cleanup_evidence.revalidate` 验证，`audit_after.py` 已这样处理。被中断/写入失败目录没有有效清单与完成引用时不能按里面的 `errors=[]` 或阶段 `completed` 字段跳过。公共 stdout 的 HASH sidecar 和每调用 MANIFEST 都须核验；清单不是防恶意签名机制。

坏完成引用会先原样归档。只有本轮独立 current run/process/page 归属成立才执行原 End-first 收尾；当前已关闭则不重新打开网页，当前归属不明则 unknown/End_required。恢复成功后兼容完成引用可更新，旧索引原文/原调用目录不可覆盖。没有按 PID 强行结束、不新增 QMP 或延长 20 秒。

return 工具的 `return_failed` 可能同时含 `cleanup.reported_status=completed`；这只说明本次失败 child 独立报告的清理结果，**不代表 pin/confirm/菜单通过**。未知退出、摘要缺失/错 action/错身份不会读旧 current-return，不返回图片，不追加动作。

## 诊断串口与历史截止边界

r35 parser 仍只离线读取，不改变 ready/End 或重试。沿用 r37 已验收边界：从该轮原 startup-observation 的 `phases.first_kinds` **列表**核 schema/errors/first_kind_omitted/offset 范围，再取 `stage=="cleanup"` 首条 serial_offset。缺失/被省略/不明确为 unknown，不回退最终文件大小或 consumed；不要复用 r31/r38 数值。

成功 startup ready 必须 evaluation_complete、qualified 且 stage==startup，并独立保留 FIRST-FRAME/图像；不得用 cleanup 后字节/帧/摘要回填。host 字节截止不是 guest 事件时间，snapshot 不是全局 End 原子终态。r38 的约47秒待机、20秒 alarm 到期、1accepted/0pin/0confirm 仍属原失败证据。
