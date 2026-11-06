# v25 r5 宿主生命周期候选（离线，未运行 guest）

本目录与冻结 r4e 并列，仅复制宿主 `.py`，原 r4e、guest CPIO/DTB、Backup、默认入口不变。对应失败轮见 `../../runs/v25procdiag-web-r4e-6274aabb/MANUAL-BROWSER-DIAGNOSTIC-FAILED.md`。r5 只是可审候选，尚无真实 VM/Chrome 验收。

## 已证问题与修正

1. 冻结 runner 的异常 `finally` 首句恢复旧 cwd，旧 cwd 不可达时会遮蔽原错并跳过清理；原 InputGate 也依赖全局 cwd。r5 不改变进程 cwd，在 `/tmp/fx3-sock-*/r` 建指向单次 run 的短 alias，QMP `q` 和 GDB `g` 均使用短绝对路径。该 alias 不创建第二 guest。
2. r5 在建 run 后即创建 `RuntimeResourceGuard`，逐把登记已持有的锁，`Popen` 返回后立即登记唯一 QEMU，登记 QMP/InputGate。顶层任何 `main` 异常都走 guard；核心环、可选任务/vCPU、20 秒 API16、QMP quit 各自有异常边界，失败继续尝试回收，但**不能把缺失回执称恢复成功**。
3. guard 只有在 `Popen.wait()` 成功确认回收后才释放双锁。SIGTERM/SIGKILL 拒绝、wait 抛错或进程仍存活时写 `resource-guard-pending.json`，保留锁和 runner 进程；顶层每 5 秒继续有限清理尝试并输出待收尾文字，绝不 `sys.exit`。此分支需要人工处理外部不可杀进程，不能伪称有界成功。回收确认后写 `resource-guard-receipt.json`，正常路径有界退出。`cleanup_attempted` 防止重试时反复执行诊断/API16 写入。
4. 源码差异 `r4e-to-r5-runner.diff`、`r4e-to-r5-gate.diff`；新 guard 和测试的逐文件 SHA 见 `SOURCE-FREEZE.json`。现有原 5000 ms、guest 错误门、像素身份门、机型/CPU/RAM/GIC、种子与 API 逻辑均未改。

## 离线验证

- `python3 -m py_compile *.py`、`python3 run_trial_v25_diag_r3.py --help`：通过。
- `python3 test_resource_guard.py`：短 QMP/GDB alias 可连接，cwd 被移除时仍可回收真实 `/bin/sleep` 子进程，诊断/恢复异常后仍回收，已退出进程路径通过。
- `python3 test_runner_lifecycle.py`：真实 `execute_runner` 顶层对缺失 socket connect、日志目标为目录、未捕获错误回执目标为目录三个真实 I/O 失败，均在登记子进程和 flock 后触发，子进程回收且锁释放；原 `IsADirectoryError` 被记录为 `receipt_write_error`。wait 抛错测试确认锁保留至后续回收；独立 fixture 进程注入 SIGTERM/SIGKILL 权限拒绝与持续未回收，父进程确认 fixture **仍活着且 flock 仍被占有**，解除故障后确认退出和锁释放。此测试针对“仅 file.closed=False、顶层却已退出”的反例。
- `test_resource_guard.py` 另将最终 `resource-guard-receipt.json` 目标建为目录，真实写失败时 guard 仍完成子进程回收和释放锁，事件保留原 `IsADirectoryError` 及目标文件名；不会以 `name` 参数冲突遮蔽原错。
- 这些是宿主测试；不证明 QEMU、API16 或浏览器实际退出成功。未经协调端审核不启动 r5。

## 剩余

- r4e 触发 `ENOENT` 的首个操作与当时目录状态未知；没有故障瞬间的环/任务/寄存器快照。
- r5 尚需授权的单轮真实浏览器+guest 验证，尤其首次异常后的 API16 原字、PID 回收、两锁、frame 和最终 ACK；本任务不再启动 VM。
