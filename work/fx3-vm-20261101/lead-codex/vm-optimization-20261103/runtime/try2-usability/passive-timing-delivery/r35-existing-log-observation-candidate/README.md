# FX3 r35｜既有日志首次 publication/bind 离线候选

离线实现/host验证/交叉编译通过；**未集成，未运行VM**。当前调试ELF大于原slot，需要另行release包装与固定runner绑定。

- [结论与验证](REPORT.md) · [ABI与生命周期合同](CONTRACT.md) · [成本](COST.md) · [下一步范围](NEXT.md)
- VERDICT.json / SOURCE-FREEZE.json / BUILD.json / SHA256SUMS
- OFFLINE-RECEIPT.json及receipts完整原始回执；INPUTS-AFTER.json核371/371技术输入一致。
- 从项目根运行 `python3 -B <本目录>/run_offline.py` 只复现离线测试，不执行guest ELF或runner。宿主解析器 `python3 -B <本目录>/parse_r35.py <serial.log> --run-id <单轮host身份> --end-byte <原End消费截止>`，默认不推断未发生事件。

禁止将build下so直接写入旧CPIO或部署入口；原任务和协调修订见TASK.txt、COORDINATOR-REVISION.txt。全部新入口只在本目录，未改共享README/ledger。
