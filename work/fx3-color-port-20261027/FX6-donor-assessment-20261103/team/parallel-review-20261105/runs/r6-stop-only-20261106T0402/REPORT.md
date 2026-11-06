# r6 stop-only observation — not started (backend busy)

- Task：`task_46e5c0154425`
- Dispatch：`ctx_844de979a86a`
- Status：**NOT_STARTED_BACKEND_BUSY**
- 授权文件：`fx6-r6-stop-only-approval-20261105.json`（SHA 记录在 `input-hashes.json`、`blocked-lock-busy.json`）。
- 候选 manifest：337 项，self `85d6097c…`；冻结输入 hash 已记录。
- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 已核。

## 未启动原因

预检双锁时发现两个固定 FX3 `.run.lock` 均被外部进程 `74505`（`run_fbinitset_once.py --run --seconds 60`）持有；其 QEMU 子进程 `74526` 正在使用另一个 CPIO `grmreal59` 和另一 run `cp-bind-dd94986e`。按授权“若忙不启动、不抢占其他 VM、不自行重试”，**未启动本 r6 run，starts_used=0**。

- 未创建 run root / serial.log；未调用 run_stop_only、QEMU、QMP、RSP、guest。
- 未操作/终止外部 PID 74505/74526；未释放其锁，未碰其 serial。
- 未运行本任务观察器，未产生两键 observation；没有 boot/menu 结论。

## 交付/证据

`authorization.json`、`launch-allowance.json`（starts_used=0）、`command.txt`、`preflight`/`blocked-lock-busy.json`、`input-hashes.json`、`REPORT.md`、`RESULT.json`、`SHA256SUMS`。原始候选未改。

## 后续

需等外部 FX3 QEMU/双锁释放后，由协调器重新安排**新的一次**授权；本授权的一次启动未消耗，不能自动重试或跳过占用检查。
