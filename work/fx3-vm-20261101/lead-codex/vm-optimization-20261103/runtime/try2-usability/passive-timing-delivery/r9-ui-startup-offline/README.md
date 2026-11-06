# FX3 UI 启动链离线定位

已完成现存 r3、失败 A、新成功 B 的消息链审查，根因未定。新增证据把重点推进到 UI 更新/timer 入口之前；原生产者以半字写 GUI 操作码，成功 B 的第9包高16位也非零。

- [报告：生产者、消费者、原条件、累计计数和最小下一观察方案](REPORT.md)
- [机器可核证据：输入哈希、LF行号/字节偏移、CPIO指定成员绑定、bank及反汇编参数](EVIDENCE.json)
- [本次离线分析脚本](analyze_startup.py) · [执行摘要](ANALYSIS-RUN.log) · [交付哈希](SHA256SUMS)

11份 `.txt` 是小段固定地址的原ELF反汇编。仅本目录有新增/修改；未改r7、其他helper、guest、平台或旧CPIO，未运行VM或历史测试。
