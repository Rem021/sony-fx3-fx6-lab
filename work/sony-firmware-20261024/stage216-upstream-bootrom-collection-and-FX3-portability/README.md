# FX3 恢复适配：新公开救砖案例、BootROM 路线与模式解析差异

2026-10-29；经典ILME-FX3 7.02；本轮仅Mac本地源码、镜像和指令字分析，无相机操作。

**本轮取得并固定了两个ZV-E10项目的当前源码，核对其恢复与验证实现；另从FX3原程序定位了启动模式解析，确认不能照抄社区的换行修复。** 新证据收紧了后续FX3恢复器的偏移、完整校验、源镜像健康和运行身份要求。0.5源码包保留，没有新设备入口或刷写放行。

## 哪些公开方案有参考价值

[dino2048/zv-e10-toolkit](https://github.com/dino2048/zv-e10-toolkit/tree/bd2b4ac03af71bd397f8b88162db1ec1671e222a)固定至2026-10-26的`bd2b4ac…`；[cokeenet/zve10-qemu](https://github.com/cokeenet/zve10-qemu/tree/48e649087cee915794b262ad676c1371d718c58e)固定至2026-10-29的`48e6490…`。另复查A7CII服务研究`1619f93…`。三个目录树分别152／919／5项，API均未截断，另重算133个Git目录对象并与提交的根树对应；24份选定文件逐项验证Git blob SHA-1、长度与SHA-256。没有clone、导入或运行上游程序。[目录对象核对](git-tree-object-proof.json)、[来源清单](source-capture.json)、[补取](source-retry-capture.json)、[后续源码](source-followup-capture.json)。

| 路线 | 新核对的实际边界 | 对FX3的决定 |
|---|---|---|
| Linux下导出BootROM | ZV-E10依赖可用的已认证终端；上传ARMv7 helper到tmpfs后用/dev/mem逐页读取 | 可以参考有界读取和双次比较；不能复制ABI、地址范围或终端开关作为FX3执行证明 |
| Linux失效后的独立救援 | 作者提供Pico串口注入、stage1→USB stage2及用户分区回读路线 | 需要专用硬件；用户现有Mac／Windows不能直接替代注入器 |
| 分区恢复脚本 | 只处理列出的用户分区；整片fetch后与备份比较，不覆盖boot0/boot1、分区表或硬件故障 | 可借鉴完整比较，不能称作FX3全故障恢复 |
| SD更新路线 | 文档从原脚本推导路径，但最后仍列有创建标志和坏机完整恢复等未实测项 | 保持候选；不把推导写成已救砖 |
| QEMU | 作者报告应用部分启动，显示链路未完成；目标为ARMv7/CXD90045 | 有仿真参考价值，不能验证FX3硬件编码器、USB启动或真实恢复 |

对应原文：[BootROM读取](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/linux/docs/bootrom-dump.md)、[硬件入口](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/hardware.md)、[恢复范围](https://github.com/dino2048/zv-e10-toolkit/blob/bd2b4ac03af71bd397f8b88162db1ec1671e222a/bootrom/docs/recovery.md)、[SD候选待测](https://github.com/cokeenet/zve10-qemu/blob/48e649087cee915794b262ad676c1371d718c58e/docs/incidents/SD_UPDATE_RECOVERY.md)。

## 事故复盘必须读最终更正

2026-10-28的[重启事故复盘](https://github.com/cokeenet/zve10-qemu/blob/48e649087cee915794b262ad676c1371d718c58e/docs/incidents/INCIDENT_20261028_LDSO_PRELOAD.md)在第0节明确推翻后文初步诊断：作者报告该次恢复中，先恢复/etc仍无改善，再恢复含换行的启动模式镜像后恢复。它也记录此前的坏preload事故及被误当成健康备份的测试镜像。

这属于该作者对其设备的恢复观察，不是FX3实测，也不是同条件单变量实验。不能把“相同重启症状”当成相同根因，更不能直接给FX3补一个换行或清掉某个目录项。

本轮重新核对FX3已保存的官方镜像：root与app合计847个唯一普通inode中，模式路径定位到init/init2、change_mode.sh及bootin.elf。原bootin为ARM64，SHA `dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2`。

选中的原函数打开`/setting/mode/dmode`，最多读30字节，以实际返回长度逐字节识别模式。`0x402504`比较ASCII 3，命中后选中原字符串地址`0x403A28`；LF经该分支的忽略路径继续。**该局部解析不要求ASCII 3后必须有LF；它不是“FX3写入单字节3就能正常启动”的完整运行结论。** 官方change_mode.sh的默认模式写法会输出换行，说明恢复应保留同机原字节，而非任意规范化。

[4份原范围和16项指令字／分支检查](portability-proof.json) · [847项定位范围](FX3-boot-mode-locators.json)。全文反汇编覆盖7952字节，7940为指令、12为明确跳过的数据，所选解析范围没有跳过字；未执行Sony代码或guest。首版核查将19字符路径的NUL长度少算一字节，断言已拒绝；修正与初稿均保留，没有放宽核查。首次封存因API按commit请求的响应sha不是根树sha而拒绝；随后从全部目录项重算Git树对象，直接匹配提交的根树，不以字段改名跳过来源绑定。

## 写入成功与恢复成功之间的三个漏洞

1. [上游写入脚本](https://github.com/cokeenet/zve10-qemu/blob/48e649087cee915794b262ad676c1371d718c58e/fastboot/host/flash_partition.py)用分区内字节偏移构造稀疏写入，读回则换算为绝对LBA。未传起点且无reference时存在默认零起点，不能用于FX3。恢复器必须显式绑定地址基准、单位和读出视图。
2. 同一脚本的差异列表仅比较目标与本地reference；两者相同且未选full时列表可为空。零写入不能冒充已恢复，更不能拿操作员提供的reference充当前设备读回。
3. [独立验证脚本](https://github.com/cokeenet/zve10-qemu/blob/48e649087cee915794b262ad676c1371d718c58e/fastboot/host/verify_partition.py)以`len(img)//65536`循环。对非整块或空输入，其“完全相同”输出不足以证明全部字节；这是静态代码边界，不是已观察到的相机故障。FX3适配必须验证正长度和完整尾部，采样结果另列。

这些文件只做AST与源码检查，没有为了复现而连接USB、启动Fastboot或执行上游工具。0.5的boot容量合同要求128KiB整倍数，组装器核对完整长度，不受上述任意尾部示例影响；它仍未成为真实恢复器。[适配决定](adaptation-decisions.json)

## 当前结果与下一步

本轮核对24份来源、23行关键源码、4个原始范围、16个原指令字／分支，以及两份FX3镜像和5份选出原件。没有新增运行测试，也未重复0.5的58项测试；不将静态核对计为实机验收。

持续目标由用户恢复为active，原生状态已复查；上一轮0.5代码和测试封存属于progress。本轮新资料与FX3解析证据也改变了适配决定，属于progress，阻塞审计从恢复后重新计。全部16项目标保持：真实认证和退出、同机健康备份、硬件HEVC主录／长录、故障外独立入口及写回／冷启动仍未完成。

接下来补FX3专用最小动态模块格式和受限子进程入口，先做不访问源分区的离线构建与装载合同核查；不能把0.5静态ET_EXEC当LD_PRELOAD库。195仅主机root01仍待具体批准，本轮未启动、未重问；不会从目标恢复推导管理员或相机授权。

[核查回执](verification-receipt.json) · [执行范围](implementation-review.json) · [原生目标](native-goal-recheck.json) · [封存清单](final-receipt.json)
