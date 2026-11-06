# lifecycle-repair 入口

- [RESULT.md](RESULT.md)：根因、修复 diff、两次 guest 运行、性能、保存/重载及退出回执。
- [lifecycle-timeline.md](lifecycle-timeline.md)：旧 QID/OSD 时间线、marker 源码归属和时钟边界。
- [key-decisions.md](key-decisions.md)、[reload-key-decisions.md](reload-key-decisions.md)：每键所见 PNG、下一键理由、保存与静置读回。
- [lifecycle-osd-v2-to-v3.patch](lifecycle-osd-v2-to-v3.patch)、[lifecycle-runner-vs-save1800.patch](lifecycle-runner-vs-save1800.patch)：仅在本目录的新源码和 runner 候选改动。
- `vmopt-20261103-lifecycle-v1/`、`vmopt-20261103-reload-v1/`：新 CPIO、DTB、候选摘要与构建审计；`runs/` 两个唯一标签为实际运行原始回执。

未修改旧候选、原固件、原 Backup 种子、历史 runs/STATE 或 preferred；未触碰相机、USB、物理 SD。
