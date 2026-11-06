# v23 host 终态文案修正（未运行 guest）

本轮真实运行结果见 `../../../runs/try2navreview-web-v22-c3aed1dd/MANUAL-BROWSER-RESULT.md`：待机后 0 键，原生关机，健康未通过；API16、QEMU 退出、双锁和最终网页 ACK 清理均通过。v22 的 `STATE-v22.json` 在实际 `phase=TRY2_COMPLETE_REVIEW_PENDING`、`current_run=null` 时仍留着“本机交互试用运行中”，属 host 状态展示错误，不是 guest 菜单完成或 v22 输入门失效。

此目录保存 v22 状态修正前的逐字副本 `STATE-v22-before-terminal-correction.json`（SHA256 `53bcf502e4283f4232d036a0f4e0166d16d13f1be490dd936b5df8361b4f41ef`）。仅将现行 `STATE-v22.json` 的 `next_minimal_command` 终态改为“试用已结束：观察到原生关机；本轮健康未通过，资源已回收”，附 `last_stop_cause=health_failure` 与重新运行需新授权；原 `receipt.json`、旧 runner、guest 候选均未改。

新 v23 runner SHA256 `9e63fb1e32b18f76843692fa3d49934af77669b19d8662ceac2c57fc44333368`，差分 `runner-v22-to-v23.diff`。它在写完不可变 run `receipt.json` 后，用纯函数 `terminal_summary(receipt)` 同时生成 checkpoint `next_minimal_command.status` 和网页结束文案：启动未成、收尾失败、原生关机、健康完成、其他健康失败分别处理。web/cache/pending 源码逐字等于 v22；所有 SHA 与测试回执在 `FREEZE.json`。

离线测试：实际 c3aed1dd receipt 得到“原生关机”，另测 native shutdown、健康完成、host failure、cleanup failure、startup failure 五种终态；生产 runner AST 确认调用同一纯函数。v23 启动早退 fixture 的端口占用、spawn error、early exit 三例通过；`--help`/Python 编译通过。**未启动新 QEMU，未做 v23 browser+guest 验收，未更新用户入口。**

避免首键前空耗的启动前就绪握手方案在该真实 run 的 `MANUAL-BROWSER-RESULT.md` 中列明，仍是设计建议，未在此 v23 代码中实现。下一次真实运行必须由唯一 owner 另获授权；不通过 host 文案修正推断 31/32 键或菜单验收。
