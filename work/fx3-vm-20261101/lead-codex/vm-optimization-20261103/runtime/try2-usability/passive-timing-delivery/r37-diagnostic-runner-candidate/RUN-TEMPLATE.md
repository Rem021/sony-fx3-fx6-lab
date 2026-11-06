# r37 准确模板与读出边界

**模板不授予VM/网页/服务权限，本任务没有执行launch_prepare/start/runner.main。** 后续协调端必须先验收本冻结、另行派发真实轮；新Task/Dispatch/session不得沿用本次离线身份。

## 宿主准备（后续填真实新身份）

从项目根使用绝对路径；输出必须是本r37/run-inputs的直接新子目录，名称包含task_后的真实suffix。勿覆盖本次任何预检目录。

```sh
R37_ROOT='/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r37-diagnostic-runner-candidate'
python3 -B "$R37_ROOT/prepare_run.py" --run-dir "$R37_ROOT/run-inputs/r38-TASK_SUFFIX" --task-id task_TASK_SUFFIX --dispatch-id ctx_DISPATCH_SUFFIX --session fx3-deadline-r38-SESSION_SUFFIX
export FX3_NAV_RUN_DIR="$R37_ROOT/run-inputs/r38-TASK_SUFFIX"
python3 -B "$R37_ROOT/runtime-wrapper/preflight.py"
```

这两步只准备/审查。填入真实身份后仍需独立运行授权，才可使用已有CLI-TEMPLATES中的launch_prepare/start_and_wait/operate/cleanup/audit_after；本文件不执行它们。`launch_prepare.py`已硬绑定本r37同名runner，准确计划参数为：

```text
python3 -B <r37>/run_trial_r24_review_snapshot.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2 --r35-diagnostic-package
```

不传任意candidate路径。新selector要求snapshot-tail/N64，缺包/错误摘要不回退旧N64；procdiag/N1/内部逐键拒绝。计划label为v35diag-n64-r36-r37；CPIO loader=0x440000000、DTB loader=0x400002000。CPU/内存/MTTCG/noicount与原相同，详见PLANNED-ARGV.json。该文件是实际构造器的离线结果，不是真实PID/argv证明，真实轮还须保留原ACTUAL-ARGV等回执。

观察/固定/独立确认、8步计划与尝试/恢复预算均沿原CLI-TEMPLATES；Node相对return工具仍在本r37，不增加读图间隙、自动点击/重试或延长20秒。当前“包可选择”不等于startup ready/首帧/菜单通过。

## 后续该轮的离线读出（End之后，仍不改准入）

r35解析器只使用原冻结版本`../r35-existing-log-observation-candidate/parse_r35.py`，不接ready/重试/End逻辑。参数形状为：

```text
python3 -B <DEL>/r35-existing-log-observation-candidate/parse_r35.py <该真实run>/serial.log --run-id <该真实host run身份> --end-byte <该轮原消费证据的字节截止>
```

截止必须来自该轮原startup-observation的cleanup阶段首次记录：`phases.first_kinds`实际为列表，先核schema、errors、first_kind_omitted及offset范围，再从列表选择`stage=="cleanup"`的首条记录并取其`serial_offset`（须为整数，位于该轮原消费范围及serial文件范围内）。不能按对象字段取值；first-kind缺失、被省略或证据不明确则unknown，不默认用最后文件大小、最终serial consumed或清理后的新增字节。串口offset属于host收到字节，不是guest事件时间。

历史r31：cleanup首次消费截止3819978，最终consumed3882426，相差62448清理期字节。这些不能回填为startup成功；这组数字仅历史示例，**不允许硬套下一轮**。r31原180秒零首帧失败保持失败。

若新轮确有成功待机，另保留首次qualified startup ready的原观察/原gate结果、FIRST-FRAME回执与返回图：必须同时`evaluation_complete`且`qualified`，并且`stage=="startup"`；核first-kind列表/省略计数，first-kind被省略时不能声称精确首次。其边界和cleanup/End边界分别报告，不能将首次token、随后完整记录、后续菜单/清理图合并成同一瞬间。首次publication/bind摘要最多证明截至某原日志点的捕获状态；缺导出、争用、初始化早期、截断和预算用尽可unknown，snapshot不是全局End原子状态。禁止用图像/零值/旧summary补证据。
