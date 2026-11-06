# AP103：软件 LDEC 与原生菜单保存诊断

状态：**软件设备/真实 ioctl/菜单纹理恢复已证实；完整600秒和保存对照未通过，等待Lead处理原生完成队列交付失败。** 本报告不代表实机或硬件解码等价验收。Lead 授权 `msg_29cd3974555b`，基线 AP102-r3；旧 runs、旧 helper 和候选冻结。

## 设备实现与边界

新模块 `runtime/helpers/fx3-ldec-soft103-v1.ko` 通过原内核 `udif_cdev_register` 注册 `devno.ko` 原 `udif_devnodes+0x50`，节点 `/dev/ldec`，字符设备 251:205。UDIF 回调、cdev 成员位置取原模块重定位及原内核 `cdev_open/cdev_ioctl`，不是相邻机型的 ABI。原 `ldec.ko` 保留只读且不加载。

原裸命令为 `1`，参数固定 32 字节：u64 用户源地址、u32 源长度、u32 目的 p32、u32 输出长度、u32 块数、u32 通道、两个 cache bypass 字节和两个保留字节。命令没有 `_IOC_SIZE`/magic，也没有输出长度回写；不添加这些字段。文件私有身份与流类型单独验证。原代码 `.text+870`、`.text+918` 和 `.text+c38/cf4` 分别证明命令、32 字节用户复制以及参数错误 -22；复制/分配/硬件无效常见 -5。畸形压缩流的精确硬件错误映射尚未验证，本模型使用 -5。

新设备将用户源经 `__arch_copy_from_user` 复制到私有内存；源范围检查限定原 AP 用户 VA 域；输出在临时缓冲区完整解码后才提交。目的经原 `arch_p32_to_p64`、`arch_phys_to_va` 及首尾 VA→PA 回查，限原 AP102 Heap/Heap2/TextHeap 三段边界；不会任意 OR 高位。原调用者持有 bitmap WriteLock，模块不递归取该锁。提交后读回 FNV，若不符则恢复旧内容。成功0只在实际输出写完后返回，无 CP/UIPC/DMA330/IRQ 成功包。

核心直接编译 Lead 交付 `impl/ldec-lz77/ldec_soft.c/.h`，许可随样例交付，marker `synthetic_ldec=1 original_ldec_hw=0`。16MiB 限长是本软件安全上限；全资源双实现一致和样例可辨认不等于硬件逐位等价。

## 自检与候选

宿主 `check-ldec103-v1` 在 ASan/UBSan 下经同一 ioctl 回调包装完成三个指定样例逐字节对照；非法长度、跨池/越界、通道、保留位、源地址、复制/分配失败与错误命令均拒绝且目标保持不变，日志 `runtime/helpers/check-ldec103-v1.log`。

guest 测试程序通过真实 open/ioctl 与 `/dev/mem` 映射执行相同对照。新增 FDT 保留 `[0x41d300000,0x41d400000)` 1MiB，核对与所有既有 memreserve 不重叠；只供 AP 启动前自检，不借用真实纹理。样例 `.ldec/.raw` 和 NOTICE 进入新 CPIO；其他既有成员仅 init 改动，固件 ELF、资源、Backup 种子和其他设备模型不变。既有 AP102 的锁外纹理观测和≤500ms adapter 等待保持原样。

| 运行 | 结果 |
|---|---|
| `ap103v1ldec600-17a3b482` | 3.066s 提前停，无 AP/按键；注册/open 与九宫格33280B精确输出成功。测试把命令2用作未知命令，但它被内核通用 FIGETBSZ 路径处理，未进设备回调，测试返回7。QEMU退出0、reaped、输入不变、两锁实查可取。CP模型尚未加载，API未改。不能称600s或健康运行。 |
| `ap103r2ldec600-a7c9c32d` | 测试v2改用未知命令 `0x7fff0001`；真实 guest 三样例与各边界拒绝测试通过，继续观察原 AP。模块本体与v1相同。 |

运行目标：600秒、四核 TCG；先确认待机和 MENU 的图标、高亮、背景，再按真实可见焦点完成日期同值确认和一个普通开关，MENU关闭后待机≥60秒；全程每键前实际查看截图。原生文件代次、局部/全量同步和最终健康另外核验。

## 运行中已确认与宿主校准

`ap103r2ldec600-a7c9c32d` 已实际看到待机图标，以及 `ap102-menu-settled.png` 的 Principal1 主菜单：橙色59.94p选框、类别图标、灰色面板与分隔线均恢复。日期页选框也可见。该轮452.694秒因宿主已完成的只读状态请求在步号推进后仍被重复校验而结束，不能称600秒/健康通过；`run_candidate103_v2` 修复该请求的幂等性。最终 API16 文件逐字节等于原值，QEMU0/reaped/PID消失、输入不变、21断点清除且原字节一致、两运行锁可取均复核通过。此前 status 将cleanup JSON未列细项推为缺少API还原证据是错误推断，已经发更正。

该轮12次DOWN完成后曾依据旧提交1288截图怀疑日期页等待；随后实际查看新提交1290，焦点已在第四行日期格式，证明按键都被消费。不能把此前同步等待观测称为UI死锁。两次截图间确有提交延迟；截图不等于语义转换完成，之后按最新可见焦点纠正。

`ap103v3ldec600-4ad191d2` 运行278.255秒、12键，到Data/Hora橙色高亮后ENTER。宿主原逐步读取器从可变 framebuffer PA 再读像素，发现 SHA 不再等于上一提交快照，触发严格保护停下；无解码拒绝或新绘制拒绝。QEMU0/reaped/输入不变、API16原值已验证。日期确认尚未发生。

`key_readback103_v1` 改为只读 native committed ring 的全局头和确切槽，复用已验收 TRY1 的 seq/epoch/映射/注册tuple/FNV guard，按原生租约内保存的像素副本导出PNG，不再重读正在被绘制的source PA。第三轮真实final ring回归测试证明输出逐字节一致，像素和token破坏均拒绝；没有放宽设备guard或改模型。`run_candidate103_v3` 第四轮沿用相同r2候选，继续完整600秒。

每步操作与选键理由在各轮同名 `runtime/<run>-visual-decisions.json`，逐步/补读PNG和身份哈希在对应runs；原始失败回执保留，未改写串口或历史runs。GPE/OSD/纹理全量聚合位于 `runtime/<run>-graphics102-v1.json`，包含交错导致的不完整记录，不能拿总日志缺项作负面证据。

汇总表：[逐步截图路径、画面描述、选键理由与未完成结果](ap103-visual-step-log.md)。

## 最新阻塞与严格收尾

第四轮 `ap103v4ldec600-71ce5752` 在151.445秒、3键后，原内核报 `alloc_msg() for unfetched dynamic queue QID[808261c0] size[4]`；原 `mpgpe::message::SendDrawComp(src,&status,4)` 返回 false，Flush seq437 result5/reason8、errno1018。seq436 的原生位图源/混合参数仍被既有后端接受，随后完成消息分配失败。与AP102-r2同类，不能归为LDEC格式/像素计算错误或普通内存耗尽；不添加回复、不强制fetch队列、不放宽guard。需要原SendDrawComp的接收队列创建/fetch/owner/线程退出生命周期证据与Lead合同。

| 运行 | 窗口/键数 | QEMU/输入/锁 | API16及结论 |
|---|---|---|---|
| v1 `17a3b482` | 3.066s，0键 | 0/reaped/PID消失，原输入不变，两锁可取 | 自检测试命令错误；CP尚未加载，无API还原读回。未完成600s。 |
| r2 `a7c9c32d` | 452.694s，13个宿主命令；12个完成截图 | 0/reaped/PID消失，原输入不变，两锁可取，21点原字节一致 | API16原值已还原；宿主状态请求幂等错误，日期未确认，未完成600s。 |
| v3 `4ad191d2` | 278.255s，12键 | 0/reaped/PID消失，原输入不变，两锁可取，21点原字节一致 | API16原值已还原；第12步可变PA截图与旧提交不一致，未完成600s。 |
| v4 `71ce5752` | 151.445s，3键 | 0/reaped/PID消失，原输入不变，两锁可取，21点原字节一致 | **API16读回仍是软件跳转 `5000005800021fd6bcfc4d0080ffffff`，不等于原值；restore_seen=0。严格收尾失败，QEMU已经退出。** |

v4只观察到既有own-reservation shutdown请求已写，3秒恢复等待结束时还原尚未确认；不能将request/restore_status初始0当完成，也尚不能判定模块卸载失败或其具体原因。下一轮宿主收尾应有界轮询原字节与restore_seen，超时明确失败；本轮已退出的guest不能补造恢复证据。原件始终只读，虚拟机内API跳转不会写回原文件。

后续独立修复：[API16确认收尾与两轮短guest证据](ap103-api16-acknowledged-cleanup.md)。旧串口BEGIN已证明请求被处理；新收尾等待guest ack与实际原字节同时成立，原候选1.57秒及受控延迟候选6.66秒均通过，第四轮历史失败不追改。

独立核验：[四轮review](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap103-runtime-review-v1.json)、[LDEC原生调用计数及三个样例](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap103-ldec-runtime-counts-v1.json)、[纹理四通道对照](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap103-texture-comparison-v1.json)。原串口交错使调用计数只是下界，不能用日志负面证明所有调用均成功。

## 图像证据与保存缺口

以下路径以 `R=work/fx3-vm-20261101/menu-repair-01/runtime/` 为根，实际查看过PNG：

- `R/runs/ap103r2ldec600-a7c9c32d/ap102-phaseA-before-SETUP.png`：冷启动直接待机，NOCARD/触控/AF-C/NFC等图标；取景区黑色，无传感器图像。
- `R/runs/ap103r2ldec600-a7c9c32d/ap102-menu-settled.png`：Principal1，橙色59.94p选框、各类别图标、灰色面板、分隔线、底部MENU/删除图标完整。菜单资源恢复的主要验收图。
- `R/runs/ap103v3ldec600-4ad191d2/ap102-step-11-settled.png`：日期设置1/1，Data/Hora整行橙色高亮，东京/首尔、2021-1-1、夏令时Off和A-M-D均可见。
- `R/ap103v3ldec600-4ad191d2-final-committed.png`：从冻结final ring验证seq/FNV/tuple后另存于R，旧run未改；最后提交是日期页绘制中的残帧，不能称已看到日期编辑对话框。

之前AP102同地址全零纹理现在有非零颜色/alpha：高亮地址410977d00的36像素crop中35个alpha非零；面板41059c400为194304/245760；图标41096aa40为22/36、41096bb00为2592/2592、41092c540为1571/2496。四通道完整直方图与源SHA在上述对照JSON。同地址跨轮比较不证明相同resource ID或bitmap epoch，但结合实际LDEC写入和菜单图片支持资源修复。

日期同值OK、全量SyncAll的新文件代次、普通On/Off及MENU关闭后≥60秒局部保存仍全部未验收。各轮native file最后代次2属于启动期局部保存，不能冒充这两个操作的持久化结果；没有直接调用flush、修改参数或借用成功回复。首选候选仍AP101-r4，TRY1基线未更新为AP103。
