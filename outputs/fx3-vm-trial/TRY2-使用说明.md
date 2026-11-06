# FX3 TRY2 本机菜单试用

**当前状态（2026-11-04）：以下是保留的历史入口说明。** 新入口 [FX3菜单.command](FX3菜单.command) 已独立部署，默认 4096 键／60 分钟，已通过单轮 32 键导航及 Finder 启动／Ctrl-C 退出验收；使用新版请看[当前说明](使用说明.md)。以下旧 TRY2 启动器未被替换，仍为 30 键／15 分钟，曾出现原生省电关机及旧健康布尔值漏掉黑屏的问题。两版均不能凭 `HEALTH=true` 推定全菜单或长时稳定性通过。[早期阶段记录](../../work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/RESULT.md)保留历史结论。

以下命令与使用过程保留供历史复核。

双击 [FX3菜单TRY2.command](FX3菜单TRY2.command)，保持启动的终端窗口开启，然后访问 **http://127.0.0.1:8765**。也可在终端运行：

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -B /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/run_trial_v4_try2.py --port 8765 --max-minutes 15
```

等待网页出现“固件已就绪”再按 MENU。一次只按一个键，并在实际画面更新后再决定下一键。七键持续 100 ms，单轮最多 30 键，最长 15 分钟。点击网页 **结束试用**，等待终端打印 `HEALTH`、`QEMU_EXIT`、`REAPED`、`API16_RESTORED` 和 `INPUTS_UNCHANGED`；关闭浏览器页面本身不会结束 QEMU。Ctrl-C 也进入相同收尾路径，但独立的标准 Ctrl-C 网页轮尚未完成验收。

本入口默认从已读回并固定 SHA256 的 generation 4 English Backup 副本冷启动，不覆盖原种子。2026-11-03 的实际本机浏览器轮已看到待机画面、完整菜单图标、橙色焦点和 English；按一次 MENU 后观察截图，再由网页结束，确认 guest 恢复确认、原 API16、QEMU 正常退出与进程回收、输入 SHA 不变和双锁释放。该轮不代表无限时长稳定性、拍摄、录像、实时取景或实体相机验证。其他会话占用双锁时入口会拒绝启动并给出中文提示；请等待占用者结束。

回退到保留的 [TRY1 启动说明](README.md#旧-try1-入口)，其画面图标和焦点较不完整。技术证据、各轮回执与截图见 [TRY2 交付回执](../../work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/RESULT.md)。本地 URL 仅在启动终端和 guest 会话运行期间可用，无需外网服务或实体相机。
