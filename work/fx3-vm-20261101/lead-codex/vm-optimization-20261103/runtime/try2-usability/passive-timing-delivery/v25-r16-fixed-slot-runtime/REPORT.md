# r16 固定 FX3 平台诊断候选

离线集成完成，运行验收待执行，未部署。继承 r15，新增 N1/N64 固定哈希选择；默认仍为原 r3。选择 N1/N64 必须启用 snapshot-tail，禁止与 procdiag 混用。CPU、内存、DTB、内核、MTTCG 及所有平台字段保持原 FX3 值。

修复串口 ACK nonce 前缀误匹配：期望 0x12345678 时拒绝 0x123456789，保留 CRLF 和分段行处理。17 项真实主机函数/runner AST 测试通过；其中候选选择测试只模拟卷查询，不启动 VM。

两幅真实 CPIO 各 453213884 字节，协调端独立全文件 hash 和逐字节比较通过；仅 [451339648,451398504) 的原 58856 字节诊断辅助槽位改变，其余字节完全相等。原 DTB 和平台字段一致。详见 GUEST-INDEPENDENT-VERIFY.json；guest 工件在相邻 r16-fixed-slot-guests，未复制或修改。

快照尾段仅在 End 原始读回后、API16 恢复前启用；有独立预算和暂停证明。它是非事务的自然探针检查点，不代表 End 时刻状态，也不计入启动性能窗口。原 API16 恢复和退出回收合同保留。

INTEGRATION-COMPLETE.json 取代历史 INTEGRATION-PENDING.json 的当前状态；保留后者作为过程记录。SOURCE-FREEZE.json 固定源文件，SHA256SUMS 固定离线交付物；运行时新建的 STATE/preflight 文件不在本次冻结范围。后续只批准单轮、零按键 N1 启动/首帧/快照/退出验证，N64 或交互另按实际回执安排。
