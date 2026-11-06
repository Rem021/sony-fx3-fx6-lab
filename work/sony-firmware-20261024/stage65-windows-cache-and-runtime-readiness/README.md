# FX3 Windows 缓存盘点与运行环境核对

经典 ILME-FX3 7.02 的 1080p29.97 HEVC420 10bit 约16Mbps主录仍未达到可刷入或实机可用标准。本轮补齐 Windows 交接、编译检查和原 Linux 运行环境的部分证据；完整16项验收及相机“仅缓存PnP盘点”授权保持不变。

## Windows 已完成的检查

用户已恢复 UU，并允许电脑闲置时使用主屏。原 FX3 Codex 会话及本机系统 C 盘项目目录已核对；四件缓存盘点输入文件通过 UU 传入并传回，内容逐字节一致。旧四件输入及首轮八件材料在第二轮仍保持原样。

| 环节 | 结果 | 实际范围 |
|---|---|---|
| 第一次交接后启动 | JavaScript 封装解析失败 | 未启动编译、DryRun或采集 |
| 第二次 C# 编译与 x64 结构检查 | 通过，退出码0 | 只编译并检查结构；未调用 Collect |
| 第二次 DryRun | 执行策略阻止，退出码1 | PS1正文未开始，UnauthorizedAccess |
| 原缓存关联采集器 | 未运行 | Collect次数0，私有结果JSON未生成 |
| 相机接口及命令 | 未使用 | 未打开设备接口、未发SCSI或PTP命令 |

日志分别保存在 [首轮回执](from-windows-host-attempt-1/summary.txt) 和 [第二轮回执](from-windows-host-attempt-2/receipt-attempt2.json)。第二轮传回13件材料，四件输入与首轮八件材料均完成字节复核。

后续改用系统自带 PnPUtil 的设备、关系、服务、驱动和接口属性枚举。任务已在原 Windows Codex 会话中提交并观察到处理状态；最终盘点结果另行核对。此路线不运行被阻止的PS1，也不调整执行策略。微软文档将这些参数定义为元数据枚举；如普通权限执行失败则保留错误，不提权。[PnPUtil官方语法](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax)；[PowerShell执行策略](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1)。

## 原固件启动片段和公开源码

从原7.02 kernel Image 的文件偏移0x5b0188开始，在两个独立客体中各执行五条原指令，得到原启动栈 SP=0xffffff8008684000、SP_EL0=0xffffff800868c500。执行停在0x5b019c之前，没有运行异常向量设置、MMU建立、Linux启动、调度器或上轮OSAL请求的后续路径。原BSS清零范围的370796字节只核对了操作数，未执行清零。

索尼公开的源码页面标注 **FX3 7.00**。内核源码为4.9.337，与7.02原字节进行了选定字段和调用点的核对，不能据此认定整个源码包与7.02构建完全相同。[Sony源码页面](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)。

- 公开源码使用 SP_EL0 指向 task_struct；thread_info 位于任务结构首部。厂商 CONFIG_EJ 私有字段解释了原结构中的计数偏移0x10和栈指针偏移0x28，不能直接套普通上游4.9结构。
- 驱动注册入口接收 UDIF_DRIVER 指针数组；原内核随后从对象+0x38取ops，并把对象+0x40的data传给初始化回调。本次原对象data为0，与“回调收到驱动对象本身”不同。
- 注册过程创建并唤醒内核线程，然后等待完成。原优先级90和超时30000 jiffies与参考配置 MAX_RT_PRIO=160、HZ=100下的五分钟等待相符。这些线程和等待函数没有实际执行。

两个官方源码归档均校验完整大小、SHA256和服务端Content-MD5；12个选定内核成员的内容与引用行重新核对。源码只在任务work目录供参考，没有执行下载的代码。最初50MiB下载前缀与后续范围分片保留，完整内核归档是 `work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz`；同级旧文件名下的前缀不是完整归档。

这些证据完善了离线执行所需的结构和参数约束。实际线程、锁、内存分配、驱动初始化及硬件编码仍是下一层依赖；初始任务字节或一个伪造的返回值不能代替这些运行状态。本轮没有形成完整FX3硬件模拟器。

## 故障与恢复适用范围

截至2026-10-26重新查看的 A7C II 项目issue31，已有按流程操作后无法启动、2-3-5灯号及HID枚举的用户报告，也有切换到未受影响拍摄路径后恢复的自述。恢复结果未独立验证，且该案例涉及静态图像路径修改，不能保证修改视频链的FX3仍有同样入口。[原始故障讨论](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)。

当前仍缺同机健康备份、实机程序指纹、受限写入与回读、独立恢复入口及失败覆盖验证。Windows上线和缓存枚举成功也不能证明能救砖。未把A7C II补丁、USB身份、地址或恢复步骤应用到FX3，也未输出可加载Sony模块、WBI或改版固件包。

## 证据入口与后续工作

- [交接和回传](UU-transfer-roundtrip-and-dispatch.json)、[Windows任务原文](WINDOWS_NATIVE_PNP_PROMPT.txt)、[同代理复核](coordinator-observations.json)。
- [原启动片段证据](boot-context-audit.json)、[公开源码交叉核对](vendor-source-runtime-crosscheck.json)、[下载收据](runtime-source-downloads.json)。
- 后续先完成USB父节点与磁盘子节点/接口的缓存关系核对；实际查询相机接口须另有具体可审核方案和对应授权。
- 离线继续追真实内核线程、内存池、完成通知及目标16M资源/质量接合；主录输出、音画同步、长录、温度、冷启动及同机恢复保留全部实机验收要求。

本轮复核为同代理源码、原字节、哈希与回执检查，没有独立实机验收。持续目标保持active，goal_complete=false，persistent_write_release=false。
