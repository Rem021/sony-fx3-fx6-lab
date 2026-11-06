# FX3｜r32 零ring只读因果审阅

入口：[REPORT.md](REPORT.md) · [下一次最小观测设计（未实施）](NEXT-OBSERVATION.md)

证据：[COMPARISON.json](COMPARISON.json)、四份`*-ANALYSIS.json`、[BINDING.json](BINDING.json)、[CODE-EVIDENCE.json](CODE-EVIDENCE.json)；新导出的反汇编仅为所pin二进制的只读片段。重现：`python3 -B analyze_zero_ring.py`，只写本分析目录，不加载runner、设备或服务；写前仍按项目规则核卷UUID。

123项原件前后SHA无漂移；r31 raw serial含NUL，分析始终使用bytes。结论是因果证据不足以直接修复，非VM/boot/menu通过；所有旧候选与封存目录只读。
