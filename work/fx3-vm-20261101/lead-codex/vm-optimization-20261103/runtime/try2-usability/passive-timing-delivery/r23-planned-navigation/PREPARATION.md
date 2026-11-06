# 后续独立真实任务的准备与调用

本目录是候选源码，不是一次运行目录；本任务没有起 runner/QEMU，也没有部署。所有实际运行输出必须在后续 taskID 的新独占准备目录内；旧 r21/r21c/r22 只读。

## 只生成准备材料

后续被派的操作任务用真实新 task/dispatch/session 替换以下占位符：

```sh
python3 -B /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r23-planned-navigation/prepare_run.py \
  --run-dir /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r23-run-NEW_TASK_SUFFIX \
  --task-id task_NEW_TASK_SUFFIX --dispatch-id ctx_NEW_DISPATCH \
  --session fx3-deadline-r23-NEW_TASK_SUFFIX
```

此命令仅核 UUID，独占创建 config、空 ledger、源码绝对路径 SHA 冻结和 `CLI-TEMPLATES.json`；不打开 browser、不运行后续命令。`evidence/PREPARATION-RESULT.json` 已验证这个真实入口及新 common 的源码冻结检查。

之后统一设置 `FX3_NAV_RUN_DIR` 为该新目录。wrapper 源固定在本目录 `runtime-wrapper/`，数据根由环境变量指定；每次导入 common 都核源码冻结、plan/config 一致及固定 runtime 根。不要复制整个 runtime，不在旧收尾目录执行新操作。

## 后续有真实 VM 授权时的调用顺序

1. `runtime-wrapper/preflight.py`：原固定输入/PAGE/server/QEMU hash 检查、CLI 参数检查、三个既有非冻结 runtime 输出的 before 原字节记录；只写本轮目录。
2. `runtime-wrapper/launch_prepare.py`：沿用 r21c 原 runner 参数与独占检查；这里只是未来调用说明，当前未执行。固定运行根仍为 `DEL/v25-r21-recovery-integration`。
3. `runtime-wrapper/start_and_wait.py`：只点原 Start 一次，装原 deadline，返回合格待机图。操作代理实际查看该图，再独立 `operate.py standby_review "待机实际判断"`。
4. 每步分别 `operate.py click N "固定计划后置目标"`，取得本 attempt 真实截图后实际看图；只有符合对应后置条件才另调用 `operate.py confirm "实际语义判断"`。8 个 click/confirm 命令模板已在 `CLI-TEMPLATES.json`，禁止循环自动执行 confirm。
5. 仅原 PAGE 归因未入队时，按原恢复链分别 capture（click 分支返回）、实际看图、`operate.py recovery_cancel "判断"`；再看其新图、`operate.py recovery_review "判断"`，随后由新的独立 click 调用创建新 nonce。helper no-click/unknown 不适用恢复。
6. 完成或失败后原 `cleanup.py`；核完整收尾原件，再 `audit_after.py` 只读核固定输入及复制三个授权 runtime 输出的 after。它不宣告八步菜单通过；操作任务还须核真实八步截图、原生收键及完整回收证据。

所有脚本通过 `python3 -B` 调用；`operate/later_capture` 自行显式 import sys，有真实 `__main__` 接线。每 attempt 独占 `step-NN-attempt-NN/`；reservation 在 eval 前落 ledger 并 fsync，未知保留。语义失败也走同一原 End 异常入口。

## 固定边界

CPU 4×cortex-a35、5120 MiB、MTTCG、noicount、原 kernel/DTB/N64 CPIO，以及实际 `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d` QEMU 不变；PAGE canonical SHA `f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab`。沿用 r21c runner `--max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2`；32 是保留第8键后原 confirm ready 门的服务配置，**新测试输入上限仍由冻结 plan、step 对齐和 helper 的 steps<8 限定为8 accepted，不能把32当新预算**。

三个既有例外仅 `preflight-aaf006610b0d2b6e.json`、`STATE-v24.json.tmp`、`STATE-v25-r3.json`；当前离线任务未写它们。其余冻结清单保持原样。仍未取得实时人工视觉、真实八步菜单、长时稳定性或 FX6 验收。
