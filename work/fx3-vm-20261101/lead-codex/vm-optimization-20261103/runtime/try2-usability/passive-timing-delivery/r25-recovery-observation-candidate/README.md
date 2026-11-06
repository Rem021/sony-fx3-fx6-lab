# FX3 r25｜恢复观察离线候选

仅派生修复恢复观察；真实八步尚待另行统一验收，未部署、未启动真实QEMU。

- [合同](CONTRACT.md) · [实现前设计](DESIGN.md) · [报告](REPORT.md)
- runtime-wrapper/operate.py：保持原CLI，恢复图使用独立命名schema和严格证据链接。
- operator-helpers/recovery_observation.py、recovery_readonly.js：真实截图区间观察与fresh/PAGE生命周期检查。
- test_recovery_browser.py：当前候选全恢复链，HTTP/native计数、A/B屏障和拒绝例。
- regression_test_server.py、regression_test_browser.py：原r24正常postkey历史快照确认必要回归。
- SHA256SUMS、CANDIDATE-SOURCE-FREEZE.json、MINIMAL.diff、INPUTS-BEFORE/AFTER.json：交付与只读输入复核。

prepare_run.py只创建未来独立run配置/ledger/源冻结/CLI模板；本任务只对evidence内fixture执行prepare、preflight和import，不调用launch_prepare。
