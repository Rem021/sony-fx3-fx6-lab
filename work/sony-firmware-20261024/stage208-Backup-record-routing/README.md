# FX3 Backup 本地／CP记录选择

2026-10-29；经典 ILME-FX3 7.02；仅已有官方包的离线原件。

**官方 AP 模块的本地 Backup 读取使用记录0，取 CP 数据时使用记录1。** 这闭合了207轮留下的两记录歧义：经典模板的 AP 默认 SIO／GPIO 为 `0／4／2`，第二记录的 `5／4／30` 属于该 CP 数据路径。仍没有读取这台机身的当前 Backup；此结果是公开默认配置的角色识别，不是实际恢复成功。

## 静态调用链

原件均重新从官方7.02主系统 p15提取并核对，列在 [source-capture.json](source-capture.json)：`backup.ko`、`bk.elf`、`libbackup.so`、`libBackupManager.so`、`libInfraExtBackupCommunicator.so`。本轮实际跟踪的是前述内核模块和 `libbackup.so`；其余文件仅完成静态元数据盘点。

1. 用户态 `Backup_read_4Byte`（0x1E14）指定队列 `0x003E014D`、**操作号4**、一个属性ID参数。`backup_sync_msg`把操作号放入消息头，把队列交给 `osal_snd_sync_msg`。
2. 官方 `backup.ko::backup_osal_init` 在0x7934注册相同队列的同步回调；0x79D0的重定位指向 `.text+0x74E8`，回调转交 `backup_osal_call_func`。
3. 操作分派取 `command+1`，通过 `.rodata+0xA8` 的有符号半字表跳转。操作4的第5项为271，计算到0x7F58；0x7F60调用模块的 `Backup_read_4Byte`。
4. 该读取调用 `Data_SearchId`、`Data_GetSize`、`Data_GetDataPt`。这些函数与 `Data_init` 共同使用 `.bss+0x28`，`Data_init`把收到的未偏移首记录基址存入此状态，并由首记录+0x100建立表指针。
5. `backupfile_init`先读首文件头，从其首字取得保留内存地址，经 `arch_p32_to_p64`／`arch_phys_to_cache`形成基址；需要装入时将文件读到这个基址，然后原样交给 `Data_init`。这里不先跳过第一记录。
6. `backupfile_get_cp_data`则显式调用 `Data_GetHeader`后以索引1调用 `Data_getAdrs`与 `Data_getSize`。两个函数都用首记录 `dataOffset+dataSize` 向上对齐4096，定位下一份有效BK4，再准备 `pcidma_transfer_async`。

第6项公式在207轮保留的11份经典模板上全部定位到 `0xD2000`，与独立解析器的第二记录边界相符。因此不是按参数“看起来像A7 IV”挑第一组，而是官方模块中的两个用途已有对应。

证据：[调用／重定位与记录证明](record-routing-proof.json)、[原始函数范围](function-cuts.json)、[额外记录遍历范围](extra-cuts.json)、[代码与数据分开的切片](pins/)、[可复核脚本](prove_record_routing.py)。合计30个原始范围，部分重叠，不代表30次设备试验。没有应用重定位、加载内核模块或执行 Sony 指令；旧定位文本显示字面量为UDF时，只是反汇编数据的显示，不能当作真实执行路径。

## 对 FX3 适配的影响

已保存 [FX3默认配置候选](FX3-default-profile-candidate.json)：AP默认 SIO通道0、GPIO端口4、位号2、Open模式2。结合207轮对 GPIO 提供库的核对，它与 A7 IV 参考载荷在这些配置值上相符。候选是数据说明，不包含可执行载荷或实际接口后端。

这项进展缩小了硬件适配差异，但没有确认当前实机设置、当前p1库身份、引脚电平、SIO时序、MCU状态、ROM入口、恢复载荷能否启动、同机备份及逆写。尤其 MAIN 损坏后能否独立恢复仍未实测，不能据默认参数一致就发布刷写步骤。

下一项离线研究转向当前驱动中 SIO／GPIO 的调用合同及恢复载荷启动依赖，同时保留同机boot0/p1与独立恢复缺口。完整16项要求、真实1080p29.97 HEVC主录与长录验收保持原状态。

## 对前轮措辞的修正

207轮把用户态包装中 `w2=4`称作“4字节长度”。本轮已通过消息构造和实际分派确认：**它是操作号4**，分派到4字节读取函数；`w3=1`是属性参数个数。读取返回值确实是4字节，但不应把这个寄存器的含义写成长度。旧封存原件不改动，修正记录见 [analysis-refinements.json](analysis-refinements.json)。

195轮仅主机 root01 的具体批准仍待答；本轮未启动、未重问。没有新增 USB／缓存查询、管理员／驱动操作、认证、相机文件访问、载荷上传或写固件。持续目标保持 active，尚未达到刷入或救砖验收。

[核查回执](verification-receipt.json) · [实施边界](implementation-review.json) · [来源范围](web-source-review.json) · [封存清单](final-receipt.json) · [前轮模板与GPIO](../stage207-Backup-template-and-GPIO-config/README.md)
