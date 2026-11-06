# 让 FX3 定点原型产出主录参数

核查日期：2026-10-25。**功能性离线原型已在合成上下文中，逐层验证实验选择、真实 builder、setter 转换和 MAIN 参数准备**：普通 movie、format6、typed HS frame2 经定点客体分支，实际生成 builder `15/6/2/0`，再生成 setter `6/6/3`，最后得到 stream0 的 HD HEVC42010 参数包。每层客体输出被衔接为下一函数的合成输入，未执行完整原厂调用栈或 SetMovieRecParam。这比手工注入底层编码枚举前进了两层，但尚未形成相机可选模式或可安装补丁。目标仍是经典 FX3 7.02 的1920×1080、约16Mbps、29.97fps独立主录，**精确30.000fps另列**，并须完成同机恢复、冷启动、成片、音画同步及长录验收。本轮完成的是受限 CPU 功能证据和 Windows 查询准备，目标仍未完成。([原型结果](../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[完整目标快照](../work/sony-firmware-20261024/stage12-prototype/goal-status-after.json))

## 定点分支已接通真实参数转换

实验分支只存在于 Unicorn 客体 scratch 页，精确接受上述普通 movie 组合；其它输入重放原分发指令。目标 builder 缓冲区先填哨兵值，再由实际客体指令写出四元组；setter 仅对该四元组选择 VPC6，最终三项仍由原指令写入。host 只把上一步真实输出复制为下一步输入，未填写预期编码输出。这里的 setter quality2 与 typed HS4K quality2属于不同数值空间，不能互换。**没有修改原 ELF，也没有导出相机 payload 或刷写文件**；scratch 地址不是已核验的机身代码洞。([实现与写入轨迹](../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[原件收据](../work/sony-firmware-20261024/stage12-prototype/profile/source-receipt.json))

真实 MPR helper 对 stream0 返回 codec15，参数准备代码写出 **1920×1080、4:2:0 10bit、API quality22**；帧率 helper 返回`30000/1001`，码率 helper 原返回值为`16000`，本轮不把其单位改标为 bit/s。唯一日志适配器位于`0xc8c70`，只记录诊断并执行`PC←LR`，保留 X0 和客体内存；24处调用均有返回值不被消费的原指令证据。关闭适配器后的失败负证也保留。因此不能称为无替身的完整运行；**EncOpen/Start、硬件编码与实际 SPS/码流均未执行**。([MPR 数据链、适配器及负证](../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json))

19组合法 HS4K 对照的完整 builder 缓冲区散列及 setter 三元组保持一致，另有8个 builder、8个 setter 控制；25p仍停在原断言。协调端静态审阅后另目录重放同一实现，约4.3秒通过，封存的4份原产物哈希不变；这属于独立运行，未声称独立实现。范围仍是合成模型上下文中的局部函数，并非完整菜单、sequence或全部模式回归。([对照摘要](../work/sony-firmware-20261024/stage12-prototype/profile/review-summary.json)、[另目录结果](../work/sony-firmware-20261024/stage12-prototype/profile-independent-20261025/profile-results.json)、[重放入口收据](../work/sony-firmware-20261024/stage12-prototype/profile-independent-20261025/reproduction-entry.json)、[协调端记录](../work/sony-firmware-20261024/stage12-prototype/coordinator-observations.json))

合法集合来自原比较指令和跳表，并与固定原件逐字节核对，没有把名称表全当作允许项。每次客体调用受指令数和时间预算约束，未知调用、系统指令及非法内存访问均停止，不转发主机硬件。官方提取的程序与依赖前后散列相同；这些保证只约束本轮实验，不能推成真实机身状态或全部产品组合都已验收。([允许集与执行边界](../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[源绑定](../work/sony-firmware-20261024/stage12-prototype/profile/source-receipt.json))

## 查询与派生身份仍各有明确缺口

原查询/剩余时间 helper `0x2e68048`仍将 HS frame2/3送入错误分支；本原型没有修复它，也未接通菜单、质量显示或持久化。新追到的113/14表用于支持列表及当前值描述，方向仍是内部状态向外报告，未建立反向写入主录模型的链路。内部 key、外部14和远程113均不能直接当成 PTP 命令或 SDK 属性值。([真实消费者](../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)、[一致性契约](../work/sony-firmware-20261024/stage12-prototype/consumers/consistency-contract.json))

format6固定产生的派生值5已追到 **HDMI definition/resolution** 消费者，按4K类处理；它不是编码器 setter，原始枚举 token仍未知。目标 MAIN HD是否要求 HDMI HD没有得到证明，不能强制5→1或覆盖独立 HDMI 用户设置。后续应闭合目标身份与 HDMI 兼容条件，而不能把分辨率分类直接当成实际编码尺寸。([HDMI 调用与分组证据](../work/sony-firmware-20261024/stage12-prototype/consumers/consumer-proof.json)、[详细笔记](<../research_notes/索尼 FX3 定点原型与查询准备/selector_consumers.md>))

当前格式身份仍写着既有 HS4K，实验入口也没有独立保存标记。目标若固定标称16M与十位采样，菜单就须真实显示固定质量或提供对应类型，不能继续声称旧质量选项生效。派生函数现有输入又没有实验标记，不能在其中凭空判断目标；必须先决定身份如何传递，再验证查询、保存和重新进入菜单时保持同一含义。([条件契约与未关闭项](../work/sony-firmware-20261024/stage12-prototype/consumers/consistency-contract.json))

## 最小 MSC 包已可审查 主动入口仍关闭

查询包通过43项本地源码、合成选择器及 clang Microsoft x64 ABI检查；**C#/PowerShell未在 Windows 编译或运行**。默认 DryRun在 Add-Type前退出；CachedAssociations仅编译使用 SetupAPI/ConfigMgr 的独立源码，没有 CreateFile或DeviceIoControl声明。主动方法隔离在未定义编译条件内，无公开 CLI；当前`ready_to_run=false`、绑定缺失、入口禁用。本包是准备材料，不是主动执行授权或当前审批请求。([离线回执](../work/sony-firmware-20261024/stage12-prototype/msc-probe/offline-verification.json)、[审查包](../work/sony-firmware-20261024/stage12-prototype/msc-probe/approval-packet.json))

拟议命令仅为一次`12 00 00 00 60 00`普通 INQUIRY，96字节、缓冲式 SPTI、超时字段3秒；未来句柄需 RW访问，使用现有 token且不自动提权。**3秒不是整次调用的墙钟保证，应用一条 CDB也不证明操作系统没有恢复或后台命令**。协调端另核对64位 detail 的 cbSize8、路径偏移4及缓存 API边界，9份绑定工件哈希均匹配；这不替代 Windows runtime 验收。([协调端记录](../work/sony-firmware-20261024/stage12-prototype/coordinator-observations.json)、[Microsoft API](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ni-ntddscsi-ioctl_scsi_pass_through)、[超时字段](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddscsi/ns-ntddscsi-_scsi_pass_through))

缓存关联选择器要求磁盘接口、设备节点和父链同时匹配，使用系统原样返回的路径，不拼接磁盘编号或取首项兜底；零个、多项或不完整候选都拒绝。路径及不透明标识仅存主机私有回执，公开报告只留哈希。即使未来唯一关联成立，对齐要求和运行时编译仍须另证；普通查询返回的修订字段也不能代替完整程序指纹或恢复能力。([缓存选择器与限制](<../research_notes/索尼 FX3 定点原型与查询准备/minimal_probe.md>))

另已封装仅4文件的缓存交接目录：原样包装脚本、缓存 C#源码、任务说明和散列清单；不含主动查询源码，尚未传输或派发。后续可在已核验 Windows 本机项目目录按说明复核、编译并采集缓存关联，私有 JSON仍留当地。([交接说明](../work/sony-firmware-20261024/stage12-prototype/msc-probe/windows-cache-handoff/TASK.txt)、[散列清单](../work/sony-firmware-20261024/stage12-prototype/msc-probe/windows-cache-handoff/sha256-manifest.json))

## 先补齐缓存关联 再推进模式一致性

当前实机授权仍仅 Windows 缓存 PnP。旧缓存缺 Disk接口和 USB父链关联，补采这些缓存元数据已在原授权内；两次 UU 检查均遇到连接/服务器错误并由应用显示设备离线，尚未传文件或执行 Windows UI任务，不能据此认定电脑已关机。这只是该步骤的外部依赖，**整个目标没有标为阻塞**。([协调端观察](../work/sony-firmware-20261024/stage12-prototype/coordinator-observations.json)、[旧缓存](../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json))

离线下一步仍可闭合查询、可选身份、固定质量显示与保存恢复。硬件 Open/Start、真实主片与音频、长录温度、冷启动和同机恢复继续作为独立验收；官方提取件哈希不能替代机身备份。本轮没有新增相机主动访问、原生执行、驱动、WBI或设置写入，16项要求与授权完整保留。([本轮回执](../work/sony-firmware-20261024/stage12-prototype/final-receipt.json)、[进度快照](../work/sony-firmware-20261024/stage12-prototype/goal-status-after.json))

**部署前推论，非实测：**原版会对 typed HS frame2断言；若将来把该实验选择持久保存，回退原程序前还须恢复原版合法设置，仅还原 ELF不会自动构成安全回退。`key39c`只是内部模型标识，实际持久字段与恢复顺序尚未证实，不能猜测备份地址。本轮没有持久保存该选择。([原版与实验对照](../work/sony-firmware-20261024/stage12-prototype/profile/profile-results.json)、[内部 key证据](../work/sony-firmware-20261024/stage11-model/builder/typed-key-evidence.json))
