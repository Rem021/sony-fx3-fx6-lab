# r30 后续运行准备模板

本任务仅离线完成。本文件不授权启动服务、VM或Start；下一轮须使用协调员另行派发的task/dispatch和次数预算，不能执行此目录离线prepared样例的启动/按键命令。

首先核对 `/Volumes/KAFU2T` UUID 为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，并按外部已接受的本交付SHA256SUMS核验本目录。填好真实参数后，以下仅创建新任务输入并运行无服务预检：

```sh
R=/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r30-startup-observation-candidate
# TASK_ID=task_<新派发ID>，DISPATCH_ID=ctx_<新派发ID>
# RUN_DIR须为DEL下新目录，名字含TASK_ID去掉task_后的完整后缀，不能指向已有目录
# SESSION须为fx3-deadline-前缀的独占名字
python3 -B "$R/prepare_run.py" --run-dir "$RUN_DIR" --task-id "$TASK_ID" --dispatch-id "$DISPATCH_ID" --session "$SESSION"
FX3_NAV_RUN_DIR="$RUN_DIR" python3 -B "$R/runtime-wrapper/preflight.py"
```

预检应有41项LOCAL、36项CORE，ACTUAL-DEPENDENCY-BINDING内startup_observation/trial_ring_cached/trial_log_v4_mss必须来自r30。`return-tools/short_tool.mjs` 按本目录相对 `tool_call.mjs` 绑定，Python adapter的FROZEN/OPERATE须来自r30，CORE pin=`3591a3fcbb79c2b1617ba47f4fa4de5b79f2057f717198393e433156f69dc5e9`。不要引用r28旧adapter或旧SOURCE-FREEZE。

后续获明确运行授权时，仍使用原runtime-wrapper内launch_prepare/start_and_wait/operate/cleanup流程；禁止另加Start、重试、键或改变180/20秒。完整stdout/stderr落本次文件，同工具展示当前真实PNG；等待5秒的原首观察、显式pin、独立看固定图confirm均沿用。

回收后根据该轮runtime.json的 `run` 找 `startup-observation.json`，先看flush状态/截断计数，再关联原serial与QMP：raw_16Q有效性不等于帧有效；marker到达不等于guest事件时间；unknown/not_evaluated不能补成ready。cleanup-only帧保持失败，不用晚图倒算通过。无诊断文件或写失败时报告证据缺口，不重启或重发。
