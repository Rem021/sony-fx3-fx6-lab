# FX3 检查点与局部恢复方案的适配边界

核查日：2026-10-25。仅静态读源码及既有本地证据，没有运行参考代码、编译或上传 worker，没有相机接口、GUI、USB、驱动、认证或刷写操作。本轮 GitHub API 复核 main 仍为 `b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d`，提交时间 `2026-10-25T06:17:50Z`；逐文件 URL、完整 SHA256 及字节数见[来源收据](../../work/sony-firmware-20261024/stage8-adaptation/checkpoint/source-receipt.json)。

## 什么可以迁移 什么不能只改型号后使用

### Takeaway

可以迁移检查点的安全设计，但必须重新定义 FX3 的恢复范围、身份绑定、文件与设置布局及重新加载验证。A7CII 现成 checkpoint 不是跨机型备份格式，不能通过改成7.02或替换PID变为FX3恢复器。

### Cited Findings

- `checkpoint.py` 固定两程序路径，另含68个名称资源、live/saved设置、2个固定CP key；`recipe_keys` 从A7CII固定AP偏移解析出总计56个AP外观字段。格式锁定2.01，`same_body` 强制ILCE-7CM2并比较共同存在的serial摘要。它保留初始存档、写临时ZIP、fsync、解压回读再发布，源码明确其范围不是全文件系统或校准重置。— [checkpoint.py L13–67与L113–122](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpoint.py#L13-L67)
- 恢复规划从可读的current到可信target逐页比较；长度不相等直接拒绝，4096字节页中的差异再划窗口，按载荷限制拆成多个worker。它没有要求current属于原版/成品两个固定整文件hash，但这不是允许任意机型或无身份目标。— [checkpointworker.py L5–51](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointworker.py#L5-L51)
- native worker 固定`/usr/lib/appFw.so`和`/cp/cpapp-b.bin`，校验普通文件、等长及inode/device；检查`/dev/nflasha15 /usr ext2`为ro，短暂重挂rw，复查现场后pwrite原inode，fsync并核对窗口或完整hash。该程序不负责设置或WBI。— [installer.c L38–149](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/installer.c#L38-L149)
- FX3目前仅有人读菜单确认7.02，没有实机程序哈希或唯一机身绑定；现有原件明确来自通用官方DAT及提取程序，不是这台机身的备份。— [菜单确认](../../work/sony-firmware-20261024/stage7-entry/menu-version-confirmation.json)、[恢复材料收据](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)

### Inferences

- **可复用方法**：修改前保存健康原件、同机绑定、完整长度与SHA256、归档后回读、禁止覆盖初始检查点、current→target差异、现场旧字节检查、逐阶段日志、全文件读回。
- **FX3必须重新实现的部分**：型号/固件格式门禁；合法的同机身份来源；拟修改文件白名单和真实挂载条件；必要设置字段、保存分组及未保存数据保护；worker ABI和执行权限；WBI条件及运行内容探针。不能只改`MODEL`、`VERSION`，更不能保留A7CII固定资源偏移和CP/AP属性key。上列具体硬编码来自[checkpoint.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpoint.py#L13)、[worker](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/installer.c#L67)。
- 初次HD HEVC研究应只覆盖实际拟修改文件及相关设置。若候选日后真的要改`libmpr.so`，这个A7CII两文件检查点天然漏掉该文件；应扩展清单而非假设AP/CP备份覆盖所有库。此处是按[两程序白名单](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpoint.py#L13)作出的适配要求，不表示已确定必须修改libmpr。
- 官方包可以是程序版本参考；它不包含这台机身修改前的live/saved设置和同机采集来历，不能冒充健康checkpoint。局部程序恢复不必一概要求全盘镜像，但更深层故障需要相应范围材料及入口。— [当前材料的实际范围与缺项](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)

### Gaps

- 当前FX3健康原件、相关设置布局和绑定来源均未采集；没有通过实机恢复建立“可信目标→读回→冷启动→基础拍摄”的闭环。没有证据将A7CII的68资源、56AP外观字段及2CP字段当成HD HEVC目标的正确恢复范围。

## rollback 能覆盖哪些失败 能否等同断电安全

### Takeaway

现有rollback是仍在执行的单个worker对本批窗口进行反向回写；不是跨全部批次、程序、名称和设置的原子事务。它能处理部分现场错误，但断电、进程消失或服务丢失后能否救回，仍取决于重新进入恢复通道。

### Cited Findings

- `installer.c`在`patch`或事后检查失败时调用反向`patch`，仅处理本worker编入的窗口；正常收尾关闭句柄、恢复/usr只读并写报告。— [installer.c L101–163](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/installer.c#L101-L163)
- `checkpointjob`先为所有batch做mode0，再依次mode1写程序，之后才做名称、设置、runtime和WBI；异常处理保存`NEEDS_REVIEW`并抛出，没有将之前已完成batch和已改设置整体倒序恢复的异常路径。— [checkpointjob.py L180–208](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L180-L208)
- WBI worker为独立程序：要求`image_mode`为`2`且`image_dev`为`*wbi4`，随后写sysfs `image_drop=1`、`image_mode=0`并查新日志。— [wbi.c L31–68](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/wbi.c#L31-L68)
- 冷启动后verify重新检查完整程序/名称及选定设置，并比较选定AP span的磁盘与内存；其收据明确CP RAM和真实行为仍需人工验收。— [checkpointjob.py L209–226](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L209-L226)
- 维护者在Mac #7确认等待0336发生在native恢复与WBI之前，但已发送认证/模式命令；缺少native记录及沿用的`normal_usb_returned`不能证明会话无操作或已正常退出。— [维护者2026-10-21回复](https://github.com/MDHan/a7c2-fl23-macos/issues/7)

### Inferences

下表是上述实现可覆盖范围的工程推断，不是FX3故障注入或恢复实测。

| 失败情形 | 现成设计可以做什么 | FX3适配后仍必须满足的条件 |
|---|---|---|
| 写前旧字节、长度或身份不匹配 | 拒绝该任务，不应删除门禁 | 正确FX3基线与同机身份；拒绝不代表做过零状态USB会话 |
| 单worker写中返回错误，进程与存储还工作 | 尝试反向写本批窗口并验证 | rollback自身也可能失败；此前批次和设置不会自动撤销 |
| 仅UU远程窗口断开 | 不能从远程断连推定worker退出 | Windows本地任务与相机USB可能仍运行；先核实日志与状态，不启动第二任务 |
| USB断开、主机退出 | 后续可重新读当前状态并规划等长修复 | 机内执行结果可能未知；服务须仍可达，不能直接重放首次计划 |
| 掉电、进程崩溃，留下等长混合程序 | 规划器允许current→可信target的差异 | 必须还能进服务并完整读取文件；fsync不是多文件原子提交 |
| 程序被截断、异长、文件系统不可读 | 当前程序差异器拒绝或无法读取 | 需要覆盖该损坏范围的另一恢复机制；不能放宽长度门禁解决 |
| 文件写好但仍运行旧WBI/AP镜像 | 独立WBI处理、冷启后内存/磁盘检查 | FX3自己的sysfs含义、目标镜像、清理和完整冷启动条件必须证明 |
| 主应用失效后服务不再枚举 | 文件级checkpoint无法开始 | 需要不依赖损坏组件的可达入口；更多主机或备份不能补出入口 |

依据：[native回写范围](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/installer.c#L101)、[等长与拆批限制](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointworker.py#L5)、[阶段及验证](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/looks/looktool/checkpointjob.py#L180)。

- FX3 `libsencore`向nflasha5写512B的显式分支，与A7CII sysfs/image_dev检查属于不同已观察路径；尚未建立控制层、语义或分区映射。既不能判定两者互斥，也不能拿任一路径原样作为另一机型的收尾。— [FX3调用点收据](../../work/sony-firmware-20261024/stage7-entry/firmware/wbi-caller-static.json)、[A7CII sysfs worker](https://github.com/QAQLeonard/a7c2-fl23-research/blob/b311407ac4ca5dd2460baee8f7d07a86a3bc9f2d/src/fl23/native/wbi.c#L31)

### Gaps

- 没有FX3主应用失效后仍可进入服务的实机证据；没有断电后的可重入恢复证明。单次no-op、正常状态能进服务、CPU仿真和“代码含rollback”都不能替代这些证据。

## 适配到什么程度 才能改变当前写入结论

### Takeaway

当前可推进为FX3专用恢复规范和离线检查，不能改变“尚未放行持久写入”的结论。先证明适配目标、健康状态材料与恢复入口，再谈HD HEVC功能写入。

### Cited Findings

- 当前菜单确认不包含程序读回、机身唯一绑定或相机接口操作；普通MSC缓存是连接证据。— [菜单确认](../../work/sony-firmware-20261024/stage7-entry/menu-version-confirmation.json)、[缓存PnP快照](../../work/sony-firmware-20261024/stage6-safety/windows-msc-inventory/sony-pnp-inventory.json)
- #31截至本次复核仍没有公开救回结局。10月25日另有两名评论者表达相似故障，其中一名明确取电池后无法启动及2-3-5灯序；未给完整版本和独立验收材料，不能据此计算故障率、独立机身数量或认定共同根因。— [#31完整原始线程](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)
- 当前恢复材料收据将实际程序指纹、同机健康checkpoint、服务认证权限、独立故障后入口及更低层材料列为尚未证明。— [本机材料收据](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)

### Inferences

建议FX3适配以以下验收项作为交付边界，全部是未来要求，本轮没有执行实机步骤：

1. **独立的FX3格式与资产范围**：明确ILME-FX3 7.02；仅纳入实际拟改文件/设置；完整源与目标hash、长度、旧/新窗口和反向结果；不借用A7CII偏移、UID、资源、属性及runtime span。
2. **可信健康点**：修改前从本机读取相应原件和必要设置并绑定身份；存档后独立回读；故障后抓取称为current/before-repair，不改称健康原版；官方包作参考，不能自动顶替。
3. **受限恢复器**：固定文件及命令白名单；静态审计编译产物、权限、挂载和现场检查；每一batch与设置步骤留意图及结果；未知状态重读current再计划，不伪造COMPLETE或直接清除needs_review。
4. **对应故障范围的实证**：FX3通道能恢复拟改范围的真实原字节并完整读回；冷启后磁盘、实际运行内容和基础拍摄一致。若承诺主应用坏后可救，另需该故障条件下可达的入口证据；不要求在主力机故意造砖。
5. **功能验收独立进行**：恢复闭环通过后，新HD HEVC模式还需硬件编码器、可解码码流、音视频时间、长录等证据；恢复规范本身不会证明1080p29.97 HEVC能拍成片。

这些要求来自上列现成代码的边界和[本机缺项](../../work/sony-firmware-20261024/stage3-recovery/environment/restore-materials.json)，属于工程推论。结论是“安全框架值得适配，原安装/Recovery包不可原样套用；当前还没有已验收FX3恢复器”。

### Gaps

- 当前缺第2和第4项实机闭环及第3项FX3成品。没有把公开A7CII成功或失败泛化为经典FX3 7.02结局。
