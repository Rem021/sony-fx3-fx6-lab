# v25 r4e Chrome + FX3 诊断轮：失败回执

- 本轮唯一 QEMU 运行：`v25procdiag-web-r4e-6274aabb`，Chrome 本机 URL `http://127.0.0.1:49192`，runner PID 83023，QEMU PID 83787，最长 30 分钟、配置上限 4096 键。浏览器点击了 Start；未获得首个完整待机画面，实际按键 **0**，因此没有 MENU、FILE100 故障现场或第 31/32 键证据。
- 冻结 runner SHA256 `775ec6f742869f77743c00e7c7f73882c33db5f13462459ce16ec9f2e2ba72bd`；候选 manifest `ced1644fbcecc542c3d90f16be2a461876e7f3af92ff639c793742f090136d22`；CPIO `439f9089d3e36b6a5ee0d3f16a170a608761f315a4a2169d1d859cb0f66952db`。原输入的 14 项 SHA 在 `FINAL-RESOURCE-CHECK.json` 全匹配。
- 约四分钟后网页显示“网页画面或状态读取失败 / Failed to fetch”。runner 控制台报 `Stopped: [Errno 2] No such file or directory: '<r4e 源目录绝对路径>'` 并以 code 2 退出；当时 QEMU PID 83787 仍存在、PPID 1。原 runner `finally` 首句 `os.chdir(previous_cwd)` 可因原 cwd 不可达而遮蔽初始异常，并跳过后续 API16/QMP/回收；**初始异常及该目录当时为何不可达未知**，目录事后存在不能证明当时状态。
- 紧急清理仅针对已核身份的孤儿 QEMU。`emergency_cleanup.py` 持双锁后尝试 QMP，因绝对 Unix socket 路径 147 字节触发 `AF_UNIX path too long`，其 finally 对该 PID 发送 SIGTERM。原 `emergency-cleanup-receipt.json` 内 `errors=[]` 和刚发信号即采样的 `pid_gone_final=false` **不是完整清理成功证明**；该脚本没有等待/回收孤儿的权限或回执。
- 独立后查 `FINAL-RESOURCE-CHECK.json`：runner 和 QEMU PID 均不在，双锁可非阻塞取得，卷 UUID 正确，14 项原输入 SHA 不变。本轮没有 `osd-ring-final.bin`、KEY93 任务槽、vCPU 暂停快照、API16 ACK/原字读回、网页 final ACK 或干净 QEMU exit/reap 证明。不能声称 API16 已恢复、guest 诊断通过或网页可用性通过。
- `host-stderr.log` 留有早期 SCU/GPIO 原样输出；历史 native Backup 周期读及 serial 均保留。未覆盖旧候选、原种子或默认入口。结论为 **failed**，禁止用此轮支持卡顿修复结论。
