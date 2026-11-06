# AP97 重复面板配置事务

2026-11-02，首轮已按新绘制拒绝提前收尾；重复面板事务与拍摄待机OSD通过，原菜单部分可见，导航未验收。Lead msg_1866471baef3授权：重复接受冻结的enum2/28B配置，每次应用control3/osdRev0、generation++与读回，再向当次source单次回1119；其他组合拒绝。600秒重走设置、验证原assert消失与线程继续，之后MENU及逐图导航。

基线实际CPIO的capid44，升级为新capid48/panel-core-v2；原core已能递增generation，旧限制来自boot-only原观测上下文要求同tid、全局只准一个待释放panel reply，以及free要求全局最新generation。本版本按已批准固定wire合同准入，保留原进程/源/长度/每字节/原消息所有权；并发在原锁下序列化应用，每个原reply保留独立generation/transaction/tid/source租约，老代次按自身签发记录释放。失败回滚保留；未改原UI或业务代码。

宿主真实transport ASan/UBSan覆盖重复同包、四不同source并发、旧代次reply在新代次之后释放、foreign tid/目的/代次错误、alloc/send回滚、28个单字节反例/未知enum/长度/非法source/进程拒绝。交叉编译、CPIO逐成员比对和init语法通过；CPIO仅capid体与新只读进程/全线程观测段变化，其余AP96模型、v7输入诊断与固定Backup RAM保持。driver将assert at、Assertion、exception monitor、signal6列为应用失败，在下一键前停止。

新观测每秒读取进程status/stat，每10轮读取所有task/stat（由独立init执行），可在应用线程停止后继续取证；不改运行政策或发送SIGCONT。

运行和图像回执待本轮逐步追加；当前未验收待机/菜单，不提前把有界运行算健康通过。

## 首轮结果

`ap97v1panelrepeat-8003227c`请求600秒，实际297.597秒在MENU新绘制拒绝后受控停止；不是完整600秒通过。QEMU退出0/reaped/PID不存在/输入SHA不变/双锁FREE/missing[]，原assert/Assertion/signal6未出现。第二次面板配置source81cf61c4/generation2/transaction112的1119被原接收者释放0，worker持续poll，退出设置后不再stopped。

第10步后独立QMP与原committed ring一致的两个PNG完全相同，实际显示HD59.94p、+0.0等拍摄待机OSD，无真实传感器图像。MENU前Backup原RAM2232320B新SHA为`21591a392a5ba7647476b8ef1068f1ee524943e2e4474dbea29c4a79bac799b4`；force两键尚未核回为0，不把它当成可跳过设置的输入。

MENU第11步down/up已发送且原接收，原开始菜单绘制；seq998 fmt2/selector1/K128、seq999 fmt0/selector1/K65均result5/reason2，Flush1050继承前序raster_failed。未发送下/右/确定，无step11的+2秒PNG。最终冻结OSD槽seq3989经header/原FNV/rawSHA校验后只读导出至runtime/ap97v1panelrepeat-8003227c-final-frame/registered-frame.png，画面有Main > Rec Frame Rate、2/59、Main1、59.94p、ISO100、PP11与MENU Close；这是部分菜单，缺失元素与导航不作完整验收。旧run未新增或改写文件。

[最终部分菜单PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap97v1panelrepeat-8003227c-final-frame/registered-frame.png) · [导出校验](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap97v1panelrepeat-8003227c-final-frame/proof.json)。Lead msg_155b0cf9b5b7批准扩展现straight_over_v1常量K0..255并增加日期事务/force原路径被动观测后，换新GPE再跑600秒。
