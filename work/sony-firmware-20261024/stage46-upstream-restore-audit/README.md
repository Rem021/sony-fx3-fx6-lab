# FX3：新版恢复实现与故障案例复核

结论：A7C II Tools 3.0提供了值得借鉴的事务和恢复检查，但**没有因此建立FX3 7.02的救砖保障**。本轮重点是新版“无需旧备份恢复原厂”的实际代码，以及10月25日更新的故障讨论；不是把旧checkpoint功能重新计作新增能力。

当前公开HEAD仍为`ef7db116e13e37be91e9af20360dc9bba8d64a9b`，与stage39文档刷新一致。本轮固定并核验20份参考文件；其中7份旧checkpoint相关文件与stage8记录逐字节相同。GitHub API返回限流403后改用公开仓库页确认HEAD，所有失败记录保留，未使用认证或扩大权限。

## 新的故障信息：条件性启动路径

[A7C II issue #31](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)的最初报告是修改后无法启动、存取灯2-3-5循环及HID 054C:0D68。10月25日，一位评论者报告改用视频/P模式后能进入系统，再用仓库恢复功能还原。

这是一条社区自述，未由本任务复现，根因和恢复范围也未获独立验证。它支持继续研究“受影响模式之外是否仍有可启动路径”，不能证明所有相似故障都能恢复。更不能直接套用到本次FX3目标：我们研究的正是视频链，不能预设视频启动路径仍完好。USB显示HID本身也不足以判定故障层级或可用救援方式。

[macOS分支issue #7的维护者说明](https://github.com/MDHan/a7c2-fl23-macos/issues/7)另指出：等待服务身份失败可发生在程序恢复之前，但此前已经做过模式/认证操作；顶层状态可能沿用上次会话。因此，“没有本次native写入记录”不能等同于“USB完全没操作”或“会话已正常退出”。本轮未下载两个讨论中的诊断附件。

## 三种“恢复”不能合并

| 实现 | 实际范围 | 不能据此证明 |
|---|---|---|
| 初始checkpoint回退 | 同机程序、指定设置和名称资源 | 整机文件系统/校准备份、服务失效后的独立救援 |
| 新版factory恢复 | 从当前程序重建项目声明的原厂区域及指定设置 | 任意损坏修复、另一机型可用、同机历史内容恢复 |
| 重新接入已有服务 | 读取既有服务端点并核对记录的机身身份 | 从HID故障模式启动系统、重新建立失效的kernel/loader |

[checkpoint实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/checkpoint.py)限定ILCE-7CM2/2.01及同机标识，范围不含完整相机文件系统。[新版direct实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/direct.py)明确以新读到的字节规划目标，不创建完整机身备份；内置原厂区域只覆盖声明范围，设置恢复也有指定范围。[服务实现](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/camera_runtime/transport.py)中的RecoverySession重新接入已有0336会话，要求记录的A7C II机身身份，不是HID0D68加载器。

因此，可复用的是事务原则；机型、固件、USB身份、设置键、偏移、原厂区域、挂载及WBI常量均须为FX3独立验证。

## 实际代码提供了哪些检查

- [native installer](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/native/installer.c)核对文件长度/类型、inode及修改窗口，写后同步并回读。当前worker失败时可尝试反向写回自己的窗口；这不使主机端多个批次成为一个断电原子事务。
- [恢复记账](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/looks/looktool/factoryrecover.py)拒绝窗口内不属于旧值或目标值的混合内容，保留未知结果，不以临时目录为空直接认定执行完成；最新程序批次也不能借较早的程序报告证明完成。
- 新版direct流程在写入前记录计划和执行意图，分批操作后完整比较程序字节；恢复核验另查设置、只读挂载、启动身份和抽查的实际加载内容。写入结束、磁盘回读、加载检查和用户实机确认是不同阶段。
- [runtime worker](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/native/runtime.c)固定抽查6处AP区域、共218字节；它不是完整AP/CP/视频链运行内存核验。boot_id变化属于新启动身份，也不能单独证明物理断电过程和全部WBI行为。
- [WBI worker](https://github.com/QAQLeonard/a7c2-fl23-research/blob/ef7db116e13e37be91e9af20360dc9bba8d64a9b/src/fl23/native/wbi.c)限定`image_mode=2`、`image_dev=*wbi4`再执行自己的处理。FX3当前后端未被实机读取，不能复制这个常量放行。

“只读runtime检测”仍会使用主动服务会话、上传/执行模块并写临时结果文件；其只读范围是程序/设置用途，不是Windows缓存盘点。本轮没有运行这些设备路径。

## 18项主机端离线检查

本轮只从固定源码AST装入4个已审查函数，使用人工字节、事务header、journal和boot_id回复；没有导入第三方设备模块、编译或执行native worker、打开USB或使用相机。

验证了同机身份限制、旧/新完整窗口可识别、窗口内混合字节被拒绝、目录/长度不符被拒绝，以及空临时状态/旧启动身份不足以证明完成。另确认：窗口检查可能通过，而完整程序比较仍能发现窗口外差异；两者不能互相替代。

所有通过只覆盖这些主机判断。它们不验证实际写入、自动反向写回、断电、机内代码退出、启动或救砖。

首轮因本任务AST隔离环境未提供`hex`而停止，失败目录原样保留；补齐后在新目录通过18项检查。该错误属于测试环境，不计作上游故障。

## 落到FX3的下一步

[FX3适配与故障范围矩阵](fx3-recovery-adaptation.json)已更新：真实同机原件/备份、当前服务端点与退出、受限恢复器及全字节回读、所有消费者/代码退出、当前WBI后端/加载/冷启动、独立救援和实机主录验收仍缺。A7C II的两程序/名称资源清单也不能覆盖本次涉及的FX3 av-cam候选。

当前机身授权仍仅Windows缓存PnP盘点。恢复连接前不重试UU；主动身份查询、认证、机身文件、模块、WBI与刷写均未执行。目标规格及全部实录/音画/长录/温度要求不变。

## 证据与复核

- [源码审计及精确定位](upstream-restore-audit.json)、[当前公开案例](current-public-cases.json)、[18项结果](run-corrected-20261025/restore-check-results.json)。
- [检查脚本](restore_checks.py)、[源指纹](run-corrected-20261025/source-receipt.json)、[同agent复核](coordinator-observations.json)、[封存清单](final-receipt.json)。

参考源码的URL、提交号及SHA-256保留在`source-downloads*.json`。按项目第三方参考代码清理约定，本轮下载的20份副本在审计后移除；失败/通过回执、本任务脚本与人工fixture保留。若需复核，先按固定URL/hash在本任务work目录重新准备所需4份源码，检查本身不联网：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage46-upstream-restore-audit/restore_checks.py --source-root <已核对的参考源码目录> --output work/sony-firmware-20261024/stage46-upstream-restore-audit/run-new
```
