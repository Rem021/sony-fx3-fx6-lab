# r17 诊断回执字段修正

基于封存 r16 的32源文件。仅删除永远为 false 的遗留 qmp_cont_sent 字段，初始化并保留 qmp_cont_attempted / qmp_cont_acknowledged 两个独立字段；运行标签改为 r17。没有修改 guest、DTB、平台、运行预算、QMP命令、输入、快照或退出逻辑。

r16 N1 实际回执同时记载 qmp_cont_sent=false、attempted=true、acknowledged=true 和成功 cont 回复，证明旧字段未更新。原始证据不改。r17 不以回复丢失推断未执行：attempted=true/acknowledged=false 时执行结果不确定，已有暂停恢复与清理逻辑照旧。

17 项主机测试通过，测试中所有capture情境均核对字段与实际QMP调用，涵盖成功、回复丢失、发送未知、请求失败、截止和协议错误；候选选择及r17标签测试也通过。构建脚本初次编辑因测试文件中锚点不唯一触发断言，在运行测试前停止；改用唯一锚点后完成，无VM启动或原件写入。

沿用相邻 r16-fixed-slot-guests 两份原包，SOURCE-FREEZE 固定32源文件，CHANGE.diff给出完整差异。运行验证待执行，未部署。上一轮N1结果见 ../.. /runs/v25gate-n1-r16-618bcb5b（相对路径说明：实际运行目录在 try2-usability/runs 下）。N1一次首帧成功不代表交互、长稳或性能优化已通过。
