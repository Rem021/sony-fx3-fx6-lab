# r6 HOST_STOP_ONLY_OBSERVATION — one authorized start

- Task：`task_d2c1b15a7f63`
- Dispatch：`ctx_b9c3158207f7`
- Approval：`fx6-r6-stop-only-approval-20261105.json`（SHA `c4817287…`），用户此前批准一次；本次为额度内首次实际启动。
- Status：**ONE_START_USED; OBSERVATION FAILED; HOST CLEANUP OK; GUEST RESTORE UNKNOWN; NOT BOOT/MENU PASS**
- 上一轮 blocked 输出保持原样（`runs/r6-stop-only-20261106T0402`，starts_used=0）；本目录为新输出。

## 启动与时间

- Python/入口 PID：`76229`；QEMU PID：`77422`（均由本任务拥有）。
- `launch_start_utc`：`2026-11-06T04:04:38Z`；start epoch `1793937879.068748`。
- `/usr/bin/time` real：**158.78s**；CLI exit **1**；派生结束约 `2026-11-06T04:07:17.849Z`（`timing.json` 标注 derived；shell 因非零退出未写 `launch-end.txt`）。
- 只启动一次，零按键；未自动重试、未第二次启动。`launch-allowance.json` 已更新 `starts_used=1`。

## 实际结果

`cli.stdout`：

```json
{"status":"STOP_ONLY_INCOMPLETE","two_keys_observed":false,"host_cleanup_complete":true,"guest_restore_status":"unknown_not_attempted","boot_menu_passed":false}
```

原生 receipt `run/receipt.json`：

- `status=error`
- `error=TimeoutError('no current complete AppFw map before observation deadline')`
- `records=[]`；`two_keys_observed=false`
- `host_cleanup_complete=true`，`clean=false`
- `qemu_exit=0`，`qemu_reaped=true`，`lock_released=true`
- `breakpoints.all_removed=true`，`residual=[]`
- `inherited=not_attempted_stop_only`
- `guest_restore_status=unknown_not_attempted`
- `input_unchanged_after=true`；target/app after hash match；`verification_failed=false`

本运行没有取得当前完整 AppFw map，观察器没有进入两键 stop；没有两个键 entry/return 值或身份依据可报告。**不能**由 host cleanup 或串口文本推出 boot/menu 成功。

## 串口独立分析

使用已验收 `fx6-serial-fault-detector/detect_serial_faults.py`，新输出 `serial-faults.json`：

- status `asserts_detected`；`line_terminated=true`，`capture_complete=null`；
- **4 条 assert**（model_api 3147/3176、infra_wrapper 1075 两次）；**0 kernel fault**；
- screen markers 均为 0；不声明零像素/菜单/boot；
- serial SHA `bf5b667b…`，`run/serial.log` 3,812,875 bytes / 47,966 逻辑行。

## 清理/回收

- 自有 QEMU 已退出并 `qemu_reaped=true`、exit 0；
- 两个固定 FX3 锁在 postrun `lsof` 中无持有者，`lock_released=true`；
- 自有 PID 76229/77422 已不存在；
- 未触碰其他进程/锁；未做 guest 控制、代码或数据写；无 inherited callback。

## 输入/argv/锁

- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。
- 封存候选 manifest 337 项 / self `85d6097c…`，运行前后一致。
- target CPIO `3a08f89d…`、appFw `b1fe2274…`、baseline `854e58f0…` 前后一致。
- 34 argv；与 frozen baseline 的差异仅 **index20 serial** 与 **index31 3a08 CPIO loader**（`argv_diff_count=2`）。
- 原生审计：`run/command.json`、`run/receipt.json`、`run/serial.log`、`cli.stdout/stderr`、`runtime-pids.json`、`timing.json`、`postrun.json`、`serial-faults.json`。

## 结论/边界

这是已授权的一次 stop-only 观察尝试；observation **failed**（无完整 map/无两键），host cleanup 成功，guest restore 为 `unknown_not_attempted`。没有 boot/menu 通过结论，也没有第二次重试；不改变 r6 代码、平台、默认入口或政策。
