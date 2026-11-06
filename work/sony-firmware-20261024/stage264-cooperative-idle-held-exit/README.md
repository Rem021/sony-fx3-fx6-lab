# 仅空闲HELD的协作退出候选

**已接通原生provider、helper私有状态、新终态和观察器；八组普通用户进程回归通过。native入口仍关闭，未上机。** 本候选只处理本次262遇到的那类“旧MSC对象已处置、尚未获取SERVICE”的空闲HELD，不宣称覆盖所有异常，也不能热修复原程序。原程序已经按265另行批准的主机清理结束。

## 实际修改

- 原生owner_core真实返回HELD后，仅由同一主线程检查私有provider：设备/接口指针和打开标志均空，未使用旧runtime，流对象没有在途调用，旧MSC处置有返回，尚无SERVICE绑定、节点或调用。符合时只释放剩余的缓存registry引用和主机堆内存；不发USB请求、不尝试STOP、驱动归还或重置。
- 该分支关闭日志、join观察线程，并沿用global_guard写持久UNKNOWN。私有回执新增`IDLE_HELD_EXIT`，保留原UNKNOWN/retained结果，不伪造COMPLETE或正常机身归还。观察器核对源MSC完整交换/处置且无SERVICE调用的流证据，随后仍须确认真实helper已退出，才报告`HOST_IDLE_EXIT_CAMERA_STATE_UNKNOWN`。
- 五秒/50样本/100毫秒策略同时用于原生流程与解析器，仍受整体期限限制。真实进程测试发现日志/通信耗时会让窗口提前于第50样本到期；现已在查询前检查期限，并用单独64/65标记记录到期，不把它当成新有效采样。过期后不接受节点、不续期或重试。
- 在途调用、SERVICE对象/绑定、处置失败、日志异常或其他所有权不明时仍保留HELD。尤其SERVICE认证/STOP后的异常不属于本次可自动退出的范围；不能根据“数据调用返回”推断机身线程已结束。

## 有针对性的验证

[构建回执](build-receipt.json) · [八组真实普通用户子进程/IPC回归](test-receipt.json)。每个子进程及AF_UNIX peer是真实Mac进程并经内核身份核对，但USB对象、机身、拓扑及响应均为自写模拟，不是实机证据。

1. 实际等待五秒未见模拟SERVICE：helper以新终态自行退出，原流没有SERVICE打开、读取或STOP，持久journal为UNKNOWN。
2. 错误物理锚点：在旧MSC处置后空闲退出，保持机身结果UNKNOWN。
3. 模拟SERVICE交换失败且对象仍持有：继续HELD、不自动退出，只通过测试专用假对象门收尾。
4. 原模拟正常流程仍完整产生88B读取与返回证据；不误走空闲分支。
5. 只修改回执声明，不能覆盖仍持有SERVICE的流证据。
6. 前一个helper结束后，同一持久UNKNOWN仍拒绝新的owner；没有自动解锁。
7. 在途调用标志、清除retained、改标COMPLETE等四种重算摘要的保存字节伪造均拒绝。保存文件不重建活连接证明。
8. native授权、render、command、bootstrap全部拒绝；没有可运行原生上机包。

编译启用-Werror，进程fixture另启用ASan/UBSan。第一轮真实等待测试发现的“missing cache sample”及当时源码/构建记录保存在`history/`和旧runs中；最终结果对应`attempt02-*`。不增加通用模拟案例来替代实机结果。

## 当前放行边界

新grant仅是`fx3-offline-idle-held-264`测试标识，不是授权；native release为0，机身节点/物理锚点/nonce/key未绑定，没有新permit或原生工厂。未执行任何root、USB、Sony认证、机内程序或固件写入。

265已确认旧root helper和观察器退出，原全局journal字节未变、仍保留OWNED/UNKNOWN。[实际主机清理](../stage265-retained-host-cleanup-plan/runs/execution01/README.md)。因此不能把本候选直接用于下一轮：还须建立明确的“人工恢复后重新准入”证据链，保留原失败历史，不能把旧OWNED改写成原试验正常CLEAN，更不能另换锁路径绕开它。

后续先解决该主机准入及新的固定范围/目标，再安排实际SERVICE认证与退出；这次八组回归不证明SERVICE认证成功、机身线程退出、健康备份、独立救砖或MAIN HEVC。原G01至G16与首刷门槛全部保留，相机继续断开USB。
