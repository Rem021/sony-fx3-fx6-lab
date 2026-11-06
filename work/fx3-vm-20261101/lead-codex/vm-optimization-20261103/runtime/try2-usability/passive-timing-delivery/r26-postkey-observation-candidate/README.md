# FX3 r26｜先观察再固定审阅

仅离线宿主候选，未部署、未启动真实VM。原r25真实8accepted/7confirm整体失败保持。

- [合同](CONTRACT.md) · [报告](REPORT.md) · [真实VM操作模板](VM-OPERATIONS.md)
- [实现前设计及修正记录](DESIGN.md)
- runtime-wrapper/operate.py新增observe、pin、reject；confirm保留原精确snapshot协议。
- operator-helpers/postkey_observation.py、postkey_read.js和runtime-wrapper/postkey_flow.py提供只读观察、持久预算与单次状态。
- [输入复核](INPUTS-VERIFICATION.json) · SHA256SUMS · CANDIDATE-SOURCE-FREEZE.json · MINIMAL.diff
