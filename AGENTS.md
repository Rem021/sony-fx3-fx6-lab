# FX3｜Sony FX3 / FX5 / FX6 固件与模拟器实验室

> 继承全局 `~/.codex/AGENTS.md`（并行改代码请在 Orca `FX3` Git 项目下开独立工作树，常规改动用 `agent-ship` 自动交付）。

- **核心模块**：`outputs/fx3-vm/`（FX3 Web UI 模拟器）· `outputs/fx3-vm-trial/`（FX3/FX6 v6.01 `gpe0` 128 页菜单运行器）· `outputs/fx3-firmware-lab/`（解包与 `ldec` 解码）· `outputs/fx3-recovery-adapter/` & `outputs/fx3-safety/`（恢复与硬件安全护栏，含 66 项离线与 Unicorn 测试）。
- **开源与合规红线（BYOF）**：严禁提交索尼专有固件镜像（`nflasha*`、`.cpio`、`appFw.so`、`cpapp-b.bin`）、`.qcow2`/`.img` 磁盘或 `>50 MiB` 大文件；保留 `Mac/work/...` 下被引用的本地 donor 二进制。
- **硬件禁令**：严禁对真实物理 FX3 相机执行跨机型整分区刷写或 USB/SD 烧录（BLOCKED / NO-GO）。
- **Orca 多 Agent 编排防排队与防误报守则**：
  1. **总控严禁挂 `schedule` / 后台轮询**：总控会话内残留任何 `schedule` 定时任务会锁死 ACP 回合（持续 `working`），导致所有 `worker_done` 积压在聊天排队框无法投递；PR 合并改用 GitHub 原生自动合入或独立 `orca automations`，总控处理完立即结束本轮等待事件唤醒。
  2. **控并发与按耗时混排**：单机同时运行支线控制在 **3–4 路**；单条命令耗时 >10s 的重测试 / Live QEMU 支线优先派给 `codex` / `claude` Worker（同步等待命令完成，避免 Antigravity 10s 自动转后台触发 `Worker stopped without reporting` 假警报）；情报调研与短测支线用 `antigravity`。
  3. **总控忽略测试期假 `escalation`**：收到 `Worker stopped without reporting` 时先核对 `Last output` 与 `worker-show`——若 `liveness=live` 且正在等后台测试完成，直接静默忽略、**严禁再 `send` 催促**（以免重置去重触发二次报警）。
  4. **批量合入、并行快检**：单次唤醒多路 `worker_done` 时连续合入后只跑一次 `make verify-coordinator-gate`（并行双模 `verify-milestone-375` + `clean-audit`），重型全量回归留在 Worker 与 CI。
  5. **闭环清理与 Run 轮换**：每合入一个支线后立即 `worker-release` 并执行 `orca worktree rm --worktree <selector> --delete-branch` 清理已合入子工作树；每 20–30 个任务轮换新的 `orchestration run-create` 与总控聊天，避免单 Run 与上下文无限膨胀。
