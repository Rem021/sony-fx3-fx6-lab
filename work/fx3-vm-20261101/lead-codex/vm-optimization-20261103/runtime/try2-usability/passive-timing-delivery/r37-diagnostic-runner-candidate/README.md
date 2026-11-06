# FX3｜r37 诊断包宿主接入候选

仅host集成/离线验证通过，未VM、未部署，零首帧根因未修复。

- [报告](REPORT.md) · [绑定图](BINDING-GRAPH.md) · [运行与离线读出模板](RUN-TEMPLATE.md)
- r30-to-r37.diff及r35_package_selection.py；SOURCE-FREEZE.json / CORE-SOURCE-FREEZE.json / SHA256SUMS。
- OFFLINE-CHECKS.json及receipts/final-*：7组通过；21项selector和11项实际边界拒绝；原CPIO准入通过。
- INPUTS-AFTER.json：1206/1206技术输入一致；ACTUAL-IMPORT-GRAPH.json、PLANNED-ARGV.json提供精确绑定。

从项目根运行`python3 -B <本目录>/run_offline_checks.py`仅做离线检查，预检输出为本目录run-inputs的独占新子目录。不能因本README或模板而执行launch/start；真实运行须另行授权，不修改旧r30/r35/r36/r10或共享ledger。
