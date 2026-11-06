# AP102 语言保存与菜单纹理观测

按 Lead `msg_451e29d2c9b9`、`msg_7eb2cdbf663a`、`msg_2c7707dd92c8` 执行，基线 AP101-r4 的原生 Backup.bin 冷启动；不直接 flush、不补 DMM/Backup 回复、不写参数。主目标为：原菜单改语言后正常关闭MENU并静置≥60秒，观察原空闲子系统保存；未落盘时，再从原 Area/Date/Time Setting 以原值确认，观察原全量同步是否带入语言。图像资源加载另由 Lead 安排审计。

## 前置与观测范围

保存触发审计 `audit_save_trigger.py --check` 通过。新增12个AP原字节保护点及原框架寄存器保持自测，记录实际语言回调/队列/Backup_write返回、空队列等待、f24完整32位值、w19/w20、产品index和真实返回、2b22cc0原调用；原API wrapper记录Backup_sync_subsystem入口/返回。原backup模块实际.text基址从guest sysfs读取，QEMU TCG Z1断点表观测21个内核点，直接使用QEMU停下的CPU上下文，读取原寄存器和消息并执行恰好一条原指令后继续；没有修改该模块指令或原寄存器。断点暂停时间独立记录，不能把宿主墙钟全部称为无中断guest空闲。

GPE每条命令保留op/fmt/flags/selector/K/物理地址/result、原参数及可获得的对象/区间；selector1/K255/P73=1记录受原界限保护的source crop SHA和四通道直方图、目标写前后SHA。空clip继续不读像素。OSD每次提交记录1003/1005、FB/bitmap/entry/token/physical、原36B描述符与同一raster guard下所见最后GPE命令序号；不同FB或物理地址可能是双缓冲，不能据此命名为多个硬件层。串口交错造成的不完整记录单列保存。

## 校准轮与未完成轮

| 运行 | 结果 | 收尾 |
|---|---|---|
| `ap102v1observe600-e4ec68e8` | 55.92秒宿主观测器错误，零按键。QEMU初次连接查询`?`会清当前CPU断点，导致后续z1移除失败。 | QEMU0/reaped、输入不变、锁释放；断点清理错误又阻断API恢复，因此**原API16恢复证据缺失**，不能算健康轮。 |
| `ap102v2observe600-44a41282` | 53.36秒零按键停止。QEMU `qC`返回process第一CPU，使用它选Hg覆盖了真实断点CPU上下文，读到IRQ向量。 | 修正独立收尾后QEMU0/reaped、原API16逐字恢复、断点移除/21原字节不变、输入不变、锁释放。 |
| `ap102v3observe600-10fbf756` | 452.01秒、8步；原菜单Principal→Meu Menu→Configur./Área/Data，确认Idioma时出现原GPE_BUSY并停止。语言尚未修改，阶段A/B未完成，未满600秒。 | QEMU0/reaped、原API16恢复、断点移除/21原字节不变、输入不变、锁释放。 |

v3已有实际原空闲路径：f24=0、w19=1、product index6、产品函数返回0，进入2b22cc0和原Backup_sync_subsystem(2cf)。3次实际DMM op20/request unit1a3917均send0、receive0，reply status0、capacity4194304、实际PA非零；cache type18；局部load/save_file返回值已原样记录，文件内容代次2。这些发生在改语言之前，不能据此宣布改语言后保存成功。旧消息摘要曾将reply的offset4字段统称unit；reply原字节完整保留，新被动解码器区分request unit@4及reply raw word@4/@16，不借用请求布局解释回复。

v3首拒绝seq1517为BitBlit，src410cbaf00/fmt2/135×42、selector1/K255，reason5来自command_lock忙分支；下一seq1518是后续失败。未私自改flags或像素模型。完整数据：[GPE/OSD/纹理汇总](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap102v3observe600-10fbf756-graphics102-v1.json)，1540条GPE、3834条OSD提交、891条纹理观察，不完整串口行106条另列。Lead已据此确认多个高亮/面板/图标纹理四通道全零，安排资源加载审计；本报告保留实际采样与Lead结论来源，不以近似混合替代原资源内容。

v3退出后有一份未被消费的额外截图请求被误写入该目录；已仅将这份本轮自建请求移到runtime外层保留，恢复运行目录原状态，原receipt和所有实验数据未改。[操作回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap102v3-unused-request-relocation-receipt.json)。

## AP102-r2

Lead `msg_398ba0ce872e` 授权两项修正：SHA/直方图移到raster锁外，锁内只做最小像素拷贝；adapter command_lock忙时有界等待≤500ms，记录等待时长，超时才拒绝。GPE-v24沿用backend-v8全部像素数学、原资源/FIFO/callback/status/Flush规则；设备协议、CP/日期/Backup模型及原保存文件不变。仅适配层锁忙行为按本次批准调整。

ASan/UBSan验证：锁内拷贝后将原source/target设PROT_NONE，锁外SHA/通道统计仍正确；行padding排除、empty clip无像素读取、errno保持；20ms释放后取得锁和500ms超时拒绝均通过。原内核停下CPU读取/单步重装/模式恢复与实际DMM请求/回复不同字段布局测试通过。r2候选只相对v1替换GPE适配件，其余CPIO成员逐字相同，DTB只改initrd-end。

`ap102r2save600-e15f61fb` 正在执行，最终两阶段结果与健康回执待补。
# AP102 后续回执补记（2026-11-03）

AP102-r2 `ap102r2save600-e15f61fb` 在200.267秒、8键时遇原生 `alloc_msg() for unfetched dynamic queue QID[808261c0] size[4]`，Flush seq1091 交付返回-1018；已无 adapter BUSY/LOCK_WAIT，不能把它归为纹理哈希锁内开销。该轮未完成保存目标，收尾API还原、断点清除、QEMU0/reaped/输入不变及锁释放通过。

AP102-r3 `ap102r3date600-0bf2d64c` 完成606.397秒、14键28事件，无断言/GPE拒绝/unfetched；到达日期设置页，但未实际完成日期OK或普通开关。高亮不可见时曾把橙色值误判为焦点并多按一次DOWN，进入NTSC/PAL确认，立即MENU取消，未确认制式改变；随后UP、ENTER进入日期页。原始截图与决策保留，不能归咎于截图延迟。

该轮内核84条记录、暂停0.373218秒、21个断点移除且原字节不变，API还原、QEMU0/reaped/输入不变及锁释放通过。原串口唯一缺失的严格marker `FX3_DATE99_CONSUMER_BOUND` 被真实UART交错拆为 `FX3_DATE99_CONSUMER_BOUNFX3_BACKUP_CP_INSMOD_RC=0D`，故原始严格健康判定仍有缺项，不能改写原串口或回执。原文件代次1→2→3，语言仍32，局部SyncSub2cf有真实成功返回，无SyncAll/DMA；不得据此声称日期或普通设置保存验收完成。

Lead暂停AP102-r4，转AP103恢复可见图标/焦点，再合并完成保存诊断，见 `ap103-software-ldec-and-native-save.md`。

