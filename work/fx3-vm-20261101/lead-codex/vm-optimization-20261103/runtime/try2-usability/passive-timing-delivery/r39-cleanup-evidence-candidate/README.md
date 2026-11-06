# r39 宿主 cleanup 证据候选

仅离线通过，未 VM/未部署；r38 菜单轮仍失败，菜单延迟、零首帧及 FX6 开机均未修复。

- [REPORT.md](REPORT.md)：范围、已验证结果、输入口径与未验项。
- [RUN-TEMPLATE.md](RUN-TEMPLATE.md)：新身份准备、收尾结果读取和禁止旧证据 fallback。
- [r37-to-r39.diff](r37-to-r39.diff)、SOURCE/CORE 冻结：9 个原文件变化、1 个新增模块，32 个原文件不变。
- `OFFLINE-CHECKS.json` / `CLEANUP-TESTS.json` / `BOUNDARY-TESTS.json` / `RETURN-TESTS.json`：最终离线回执与脚本 hash；原始流在 receipts 和各 fixture 调用目录。
- `INPUTS-BEFORE.json` 是本轮观察的 192 项；`TECHNICAL-INPUTS-BEFORE.json` 合并继承 r37 的 1206 项历史 pin，1398 项当前复核一致，并非全为本轮 fresh snapshots。

本目录可使用 `python3 -B run_offline_checks.py` 复现宿主 mock 检查，只创建本目录内独占新 fixture。原始通过项已完成，不需在未改源码时再次跑。`freeze.py` 仅重新生成本目录冻结/差分；`implement.py` 是只读 lineage 校验，不是启动器。

不要把旧 fixture、被替代预检或 mock 图片当真实运行。固定包仍为 r36，后续真实轮必须由协调端单独派发。
