# 后续单次测量的审查点（不是 Start 授权）

1. 对新命名的隔离包，只替换获准 GPE slot，核固定槽 body `19ca7de...`、必要零尾与原CPIO头/其他字节/DTB逐字节不变；不得改原 r36/r37/r39 或把 raw 277704B ELF 填入276984B槽。本任务没有生成该包。新runner必须精确pin新包，不能用任意路径或退回旧包。
2. 仍使用固定4×A35/5120MiB/MTTCG/noicount及原QEMU/kernel/DTB，原启动/20秒、单次动作、独立返回图审阅/pin/confirm/recovery/End政策保持；不能因本工具自动判语义、合并观察与pin或增加VM/按键预算。只有协调端另行派发才可运行一次。
3. 保留实际成员/源/编译依赖/启动argv以及run/host_launch_uuid/PID/TID/tpidr/库实例证据；不合并重载、重启或不同run的序号。实际CMD_RETURN应包含原完整字段及entry_ns；零值/缺失/交织仍unknown，单条自洽记录也不证明所有命令都被观察。
4. 从该轮原 startup-observation first_kinds 列表核 schema/errors/省略数与范围，再取原cleanup首记录截止；缺证为unknown，不用最终serial大小或清理后帧补startup成功。本轮legacy全文件回放只验证兼容unknown，不提供下一轮End cutoff。
5. 只在guest CLOCK_MONOTONIC内计算entry→return和同线程有序相邻return→entry；列明返回标记取样早于实际打印/函数返回，gap可包含日志/调度/原Main/漏事件。不得将其直接当CPU时间、纯FIFO等待、HTTP可见时刻或host时间；若需更细分，先评审新证据，不根据名称猜因果。
6. 记录新增字节及实际串口完整性/丢失/交织。host sink成本不是guest/QEMU测量，也不能据一次运行证明加速/稳定性。r38 failed 与 FX6未开机结论保持。
