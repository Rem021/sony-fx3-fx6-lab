# 人工恢复准入与完整私有回执集成

**266规则已接入264的完整helper入口、私有回执和观察器，并通过8组真实普通用户进程/模拟设备检查。** 新增3项保存字节的格式/混配拒绝检查。native入口仍关闭，目标/nonce/key未绑定，没有新上机许可；本轮没有root、USB请求、Sony认证或真实journal修改。

## 已接通的边界

生产分支固定使用私有的人工恢复policy和root缓存验证器，调用追加式恢复事务；不接受用户文件中的真假缓存声明。旧owner/observer、原nonce/grant、原机身HMAC与固定证据摘要由源码材料绑定；新的目标、端口及许可仍须由下一份固定包设置。缓存回调重查同机MSC、驱动、IOMedia/内核mount表及新鲜度，之后才允许owner开始。

回执提升为`FX3RCPT5`（仍1024字节），增加104字节私有恢复凭据：旧journal尾部摘要、新人工恢复记录摘要、源节点/物理端口/位置及原记录数。stage1表示只追加恢复事件，stage2表示随后的新OWNED也已追加。stage1不能声称owner已运行；旧RCPT4读者拒绝新格式。

正常、HELD和限定空闲退出均带上该凭据；观察器将它与固定目标、旧尾部及实际流的源节点/物理锚点/位置核对，继续分别观察真实helper退出。原共享frame ABI和672字节流帧未变。缺少新控制器策略时默认要求完整人工恢复凭据，不会因属性缺失崩溃或默认放行。保存字节不能重新获得活连接来源证明。

[此前恢复证据](../stage266-manual-recovery-readmission/README.md) · [本次固定的四份旧证据摘要](fixed-prior-evidence.json) · [构建及源摘要](build-receipt.json)。旧root journal和旧试验状态均未修改。

## 真实主机进程检查的适用范围

[test-receipt.json](test-receipt.json)中的helper、普通用户peer核对、父子进程、文件、flock、逐帧保存和退出均为真实Mac行为；机身、USB对象及缓存响应都是人工fixture。v1旧journal由封存264代码的自建子进程产生，不能外推为本机root文件已测试。

- 有效人工恢复后，完整模拟通信及正常返回携带stage2凭据；旧前缀保留，日志为旧OWNED→人工恢复→新OWNED→UNKNOWN。
- 有效人工恢复后，五秒无模拟SERVICE时，限定空闲HELD分支自行结束，带同一恢复链，机身结果仍UNKNOWN。
- 错误端口、过期缓存、卷仍挂载或旧owner活着：无新owner、无流调用、旧journal不变。
- 恢复记录后模拟中断：回执为stage1，owner未启动，留下阻止续接的恢复尾部，并单列`DENIED_OWNER_NOT_STARTED_RECOVERY_TAIL_RETAINED`。
- 四种恢复stamp结构伪造被格式解析拒绝。

另有[来源混配/旧版本拒绝](saved-binding-checks.json)与[缺控制器策略拒绝](default-controller-policy-check.json)：即使重新计算摘要，恢复source与流source不一致仍拒绝；旧RCPT4不能接收RCPT5；缺省控制器不能接受无恢复凭据的owner。这些只解析保存的自建fixture字节，不重建真实或模拟活连接证明。

测试启用ASan/UBSan与-Werror，无sanitizer错误。native生产代码仅编译、未执行，fixture专用sidecar解析器不链接进native程序。测试用的旧进程均通过本人的管道命令结束，没有向其他进程发信号。

## 下一份固定包必须完成

1. 生成新的单次grant、nonce、许可和新范围，明确真实host journal追加与原MSC/SERVICE认证/条件88B读取/STOP的副作用；不复用261或265授权。
2. 用当前缓存固定新的FX3节点、物理锚点和身份材料；新factory显式设置`require_manual_recovery=True`及预期source/port/location，不使用旧RCPT4控制器。
3. 保持同一全局journal路径，包含266/267的新reader与恢复事务，保留原记录；不能清尾部或改锁路径。真实root文件尚未应用这些代码。
4. 对新的材料/许可/工厂及完整流程作针对性核对，提供固定程序SHA和具体操作方案后，才请求一次新的实际通信。启动前仍须全部卷已安全推出，重新核对新鲜缓存。

目前native release为0、目标和许可未绑定，所有原生render/授权/command/安装入口均拒绝。本目录不是可执行上机包，更不是固件包；没有程序上传或固件写回。原G01至G16、健康备份、独立恢复、MAIN HEVC及首刷要求保留，SERVICE实际认证和正常退出仍待验证。
