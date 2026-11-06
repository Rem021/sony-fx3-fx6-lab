# FX3 主机入口整合与逐调用私有回执

2026年10月31日。**255的原生组件已接入完整主机入口候选，新增的原始回执、对象转交及异常保留逻辑已通过普通用户子进程整合测试。** 本轮实际运行的是不链接IOKit的自写测试程序，USB管道全部人工提供；管理员入口和相机后端仅编译，没有运行。

## 已经落到代码的整合

- [主机入口](owner_entry_main.c)连接同进程接管对象、已核对的父进程/Unix连接、新范围许可解析器、共享进度与逐调用私有日志。新范围使用schema4/独立scope、独立grant命名及FX3RCPT2最终帧，旧状态许可和旧最终帧不能直接套用。
- [普通接管端](owner_iokit.c)通过[原生委托](flow_native.inc)将已经打开的MSC650对象转交一次，并清空原指针。转交后，旧release/return/close回调只接受新流程的完成状态，不再使用旧句柄关闭设备或归还驱动。
- [实际C流程](service_flow.c)连接MSC交换、旧对象释放、新SERVICE绑定、SERVICE交换、固定read0、结束及新MSC归还请求。使用255的固定帧和显式分模式摘要，不增加任意文件、上传或固件命令。
- [回执写入](flow_journal.c)在每次控制、批量读写和对象释放前后记录原始结果：先写私有文件并fsync，再发送到已验证的Unix连接。每帧含helper身份、nonce、范围摘要、序号及摘要链；没有原串号、挑战、摘要材料或HASP原文。
- [父端](supervisor.py)先保存收到的原始512B帧，再由[新解码器](flow_receiver.py)核对身份、顺序、调用配对、同机标签、交换次数和88B读取范围。通信结果先存，后续清理不会覆盖它；最终帧还要与接管前的私有机身标签对应。

逐调用记录解决了255的last_call会被下一步覆盖的问题。另在每次真正原生调用前检查停止请求，因此认证批次中途收到取消后，不会继续启动下一次IN/OUT。失败或未返回的调用保留UNKNOWN和原实例，不重发、重置或强杀。

## 实际完成的验证

| 范围 | 证据与结果 |
|---|---|
| 最终候选构建 | [v4构建回执](build-receipt-v4.json)：native helper、无IOKit的ASan/UBSan测试helper、主机IPC库均编译；native helper SHA256为0b7cc928ab10f5211076c111635f35b3323b5c49e4f277cf6323566dbed2d47c |
| 正常整合 | [当前构建测试](current-scope-test-receipt.json)：真实普通用户子进程与内核识别的Unix连接走完整人工管道流程；80条父端原始帧与子进程私有日志逐字节相同；最终两个vendor范围标志均为1；旧清理回调没有再次执行 |
| 部分失败 | SERVICE第一次OUT返回人工STALL后，报告OWNER_RETAINED；不重放、不释放服务对象、不归还驱动、不标记完成。最终构建也验证了该状态 |
| 认证中途停止 | [取消回归](final-boundary-test-receipt.json)：初始MSC第一次OUT后设置停止请求；下一次IN、后续SERVICE、对象释放及驱动归还均未启动，原实例保持UNKNOWN |
| 来源与损坏记录 | [5组整合检查](integration-test-receipt.json)：错误self-image在接管前拒绝；nonce、出生身份、序号、摘要链、错配返回、改变调用对象、虚构证明及缺失调用链不能充成功；旧范围/旧最终帧/未放行factory拒绝 |
| 静态检查 | [分析回执](analysis-receipt.json)：5个当前相关C单元无诊断。源文件与最终构建摘要一致；测试程序没有IOKit依赖，没有运行下载或Sony/Linux原代码 |

测试按代码改动分批：早期5组、补逐调用取消后的2组、最终vendor标志和回执的2组。它们不是9次相机试验；测试中的取景/相机线程/物理录制均未验证。初次构建暴露的POSIX F_OK名称冲突已通过独立状态名前缀修复。早期核查脚本的一处guard字段偏移已按原结构改正，失败记录保留，没有重复已完成的初次正常子进程。

测试程序发生保留状态时，只使用其专有的人工退出门清理测试子进程；该门不出现在实际相机分支，不能当成真实阻塞I/O的终止或恢复方法。所有测试子进程均已确认退出，没有终止其它历史进程或观察器。

## 下一步与当前放行状态

**剩余主要代码缺口是SERVICE描述符发现、配置核对及不匹配时的控制退出。** [service_profile.h](service_profile.h)仍固定READY=0，没有把测试端点填进真机配置；实际入口在接管前停止。缓存节点、nonce和隐私材料也尚未固定到新试验包，native渲染/factory保持关闭。当前没有可执行的新批准包，也没有暂存、Terminal、sudo或相机命令。

这一项补齐后，再形成一次性的完整Sony通信诊断包，明确认证可能更新历史/模式、可选读取机身.hasp文件的范围及失败处置。不能沿用原“不认证、不读机身文件”的授权。首次Sony通信诊断仍与首次持久刷写分开。[准入结论](admission-decision.json)。

正常人工流程只报告HOST_RETURN_CAMERA_STATE_UNVERIFIED；全局相机状态仍写UNKNOWN。内部结束通知、USB返回与相机线程完成继续分别判断，不因整合测试通过降低G01至G16。12号真实Mac接管归还通过及11号UNKNOWN保留；完整同机备份、独立恢复、MAIN1080p H.265和最小持久化尚未通过，首刷未放行。[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)。

[基于原封存源码的差异](source-changes.diff) · [复制来源与摘要](source-copy-receipt.json)。原250/255代码、许可和所有历史回执保持原样。本轮依据的公开通信参考仍为[固定PMCA维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890)，不把公开参考族等同于FX3实机认证接受。
