# ADF 提示音注册：0x33d 后完整合同审计

结论：正常注册路径是 **13 轮 `0x327/40B → 0x32a/10B`，合计26个同步请求**，不是继续猜单个 opcode。清零的内置声音 backing 本身不会使原 CP 的这两条注册/音量命令报内容、格式或 CRC 错；原路径不读声音字节，只保存描述符和音量。后4轮仍依赖文件读取、DMM 与跨芯片传输成功，不能只补 ADF 回复就宣称四任务屏障完成。AP71/AP72 未提供 license_get_i、adf_get_func_i 的匹配完成队列证据，两项状态明确为**未证实**。

仅写本目录；原件、运行链、STATE、QEMU 和相机均未修改或操作。AP VA 为 appFw image VA，CP 为 Thumb VA，CP 文件偏移=VA−0x108000。逐指令字节与固定输入 SHA256、13项自动提取表、日志行号见 [proof](adf-beep-regist-proof.json)，复现脚本为 [audit_adf_beep_regist.py](audit_adf_beep_regist.py)。脚本成功是静态证据重建，不是 guest 或设备验收。

## 首包逐字段

AP72 `serial.log:13161` 原包：

```
0d202703280001800000a01d04000000000100000106010000000000000000000000000000000000
```

| 偏移 | 类型/值 | 来源与构造 VA |
|---|---|---|
| +0,+2,+4,+6 | u16 200d/0327/0028/8001 | `0x2dee8e0..0x2dee8fc` |
| +8 | phys64 LE `0x41da00000` | `0x2dee910..918`；调用结构+8；`0x2b613b8..3bc`；内置为0x33d返回base+表offset `0x2b61538..544` |
| +16 | size u32 `0x100`，不是条目count | `0x2dee91c..920` 截取调用结构+0x10低32位；`0x2b613c0..3c4`；表构造 `0x2b61a94` 与保存 `0x2b61954` |
| +20 | kind u8 `1` | `0x2dee900,908`；表record+1经`0x2b613ac..3b4`；初值`0x2b61aa0` |
| +21 | priority u8 `6` | `0x2dee924..928`；record+0经`0x2b613c8..3cc`；初值`0x2b61aa4` |
| +22 | register u8 `1` | `0x2dee90c..914`，调用结构首字节为真；注销时为0且仅保留kind（`0x2dee988`） |
| +23 | format u8 `0` | 调用结构+0x1c，`0x2dee940..948`；`0x2b61394..3a8` 清零；CP日志名format `0x1b1a58` |
| +24 | continuous u8 `0` | 调用结构+0x20，`0x2dee92c..930`；`0x2b613d8..3e0`由contLength非0派生 |
| +25..27 | 3B零padding | `0x2dee8d0..8dc` |
| +28,+32 | u32 contLength/contFirstLength `0/0` | `0x2dee934..944`；record+4/+8经`0x2b613d0..3d4,3b0` |
| +36..39 | 4B零padding | `0x2dee8d0` |

所以 `01 06` 不是单个0x0106格式/CRC字段，也不应把priority6解释成PCM编码。CP原字符串 `0xd87499/4b9/4cf/4e5` 分别称 phys64Address/size/kind/priority；bridge加载 `0x1b17da..800` 与上述偏移一致。源端 `0x81cf61c1`、公共 caller `appFw+0x2de7264` 只负责路由；真正构造为`0x2dee8b8`，AP72栈`13131..13132`回到`0x2b613f4/0x2b61de4`。

## 完整正常序列

每行依次发327后32a；全部同步等待：`0x2b613f0 → 0x2dd1054 → 0x2dee96c`，`0x2b6145c → 0x2dd1094 → 0x2dee9ec`，均进入`0x2de70a8`，`0x2de72fc`timeout=-1。循环`0x2b61dcc..0x2b61df4`恰好index0..12；成功后函数返回，业务worker才可投完成队列（前审计`0x2dcb9c0..0x2dcba04`）。327的register通常=1；例外是sequence_boot+0x1e4==1且index==6时首字节为0，发送注销（`0x2b61378..39c`），随后仍设置该kind音量。format=0，continuous为contLength非0；32a body为 **volume在+8、kind在+9**，volume来自下面的sequence_boot字节，而非固定常数。

| index | kind | priority | offset / physical来源 | size | contLength/contFirstLength | volume来源 | 表构造call VA |
|---|---|---|---|---|---|---|---|
| 0 | 1 | 6 | 0x0 | 0x100 | 0x0/0x0 | sequence_boot+0x23c | `0x2b61ae0` |
| 1 | 2 | 6 | 0x100 | 0xb80 | 0x0/0x0 | sequence_boot+0x23d | `0x2b61b14` |
| 2 | 3 | 6 | 0xc80 | 0xb80 | 0x0/0x0 | sequence_boot+0x23e | `0x2b61b48` |
| 3 | 8 | 6 | 0x6380 | 0x15c0 | 0x720/0x4e0 | sequence_boot+0x23f | `0x2b61b7c` |
| 4 | 7 | 6 | 0x5840 | 0xb40 | 0x0/0x0 | sequence_boot+0x240 | `0x2b61bb0` |
| 5 | 9 | 6 | 0x7940 | 0xb40 | 0x0/0x0 | sequence_boot+0x241 | `0x2b61be4` |
| 6 | 4 | 3 | 0x1800 | 0xe80 | 0x0/0x0 | sequence_boot+0x242 | `0x2b61c18` |
| 7 | 5 | 6 | 0x2680 | 0xd80 | 0x0/0x0 | sequence_boot+0x243 | `0x2b61c4c` |
| 8 | 6 | 6 | 0x3400 | 0x2440 | 0x0/0x0 | sequence_boot+0x244 | `0x2b61c88` |
| 9 | 10 | 4 | 独立remote DMM | fread返回值 | 0x0/0x0 | sequence_boot+0x246 | `0x2b61cc0` |
| 10 | 11 | 4 | 独立remote DMM | fread返回值 | 0x0/0x0 | sequence_boot+0x245 | `0x2b61cf8` |
| 11 | 12 | 6 | 独立remote DMM | fread返回值 | 0x0/0x0 | sequence_boot+0x247 | `0x2b61d30` |
| 12 | 13 | 6 | 独立remote DMM | fread返回值 | 0x0/0x0 | sequence_boot+0x248 | `0x2b61d68` |

内置物理值为`0x41da00000+offset`；末端0x8480，落在Lead的64KiB预留区内。后4项文件分别为：

- index9: `/usr/share/avsystemsound/Dslr_Emnt_High_SelfTimer_RemoteRelease.bin`。
- index10: `/usr/share/avsystemsound/Dslr_Emnt_High_SelfTimer_2sec.bin`。
- index11: `/usr/share/avsystemsound/Dslr_Emnt_High_Startup.bin`。
- index12: `/usr/share/avsystemsound/Dslr_Emnt_High_Shutdown.bin`。

文件分支先DMM申请`0x2b60a48/0x2b60aa8`、mmap `0x2b60cd4`、fread `0x2b60e28`、transfer `0x2b60fb0`、unmap/free `0x2b61120/0x2b61254/0x2b612a0`。长度来自fread out+8 `0x2b60f58..f68`，进入record size `0x2b6134c..350`；phys来自remote DMM结果`0x2b61354..358`。这些地址、字节数与音量不可静态写死。前置步骤失败可在尚未发327前进入`0x2b60c38..c50`致命处理；静音ADF合同不能替代文件/DMM协议。

## CP旧映射与逐条最小合同

| AP命令 | 旧ADF请求/完成 | CP语义与原状态 | AP精确成功回复 |
|---|---|---|---|
| 327/40B | 2004/0201/40B/0001 → 8201/12B | bridge `0x1abf98..fba → 0x1b17b4`按原body复制；`0x5b00c2`处理表，`0x18693c`找20个槽、复制描述符、换算物理地址，`0x1869e0`构造status32+8 | `0d2027130c00018000000000`，1327/12B/status0；bridge `0x5ca1e4..20c` |
| 32a/10B | 2004/0204/12B/0001 → 8204/12B | bridge `0x1ac010..032 → 0x1b1d08`，+8 volume/+9 kind；`0x5b0606 → 0x186c24`保存音量，`0x186c98`构造status32+8 | `0d202a130c00018000000000`，132a/12B/status0；bridge `0x5ca2da..302` |

旧完成精确成功字节分别`042001820c00010000000000`、`042004820c00010000000000`。所有回复回原请求source，目的/type/flags/长度及状态检查应严格限定；保存已注册kind与descriptor、相应volume、backing寿命，然后单次成功回复。在Lead明确静音且禁止播放的合同下，这两项可以只保存状态，不执行CP、不生成音频、不宣称原厂声音。

327原处理在`0x5b00d2..de`复制**消息内描述符**，不是声音内容。`0x18697c..9be`将phys64在4个映射记录（`0xb54eb0`，stride0x20）中换成本地地址；没有对该结果所指声音的解引用、文件头/格式/CRC校验。地址不在映射时`0x1869aa..9b4`记录错误并存本地0，仍以status0完成；模型应自行保证保留区与边界，不能把原路径的宽松处理用于越界。零声音内容不会触发这条链的错误。+28/+32原厂日志名为contLength/contFirstLength（`0x1b1a00/0x1b1a1c`），不能把它们误称为起止偏移；index3的0x720/0x4e0应按该名称保存。

327原可见错误是：相同kind、相同descriptor返回3并成功（`0x5b01f6..26c`）；相同kind但descriptor不同返回2，经`0x5b01be..1ce`报`0xe004`；register值既非0也非1也报`0xe004`。注销搜索kind，无匹配仍成功（`0x5b0176..18e`）；20槽满则`0x186958..95c`直接返回，未走completion，可能留下AP等待。正常13项新表不占满20槽，但CP历史状态必须由模型管理。

32a只接受volume<8，`0x186c28..c30`；>=8返回`0xe002`（`0x186c50..c5a`），`0x5b0616..620`将任何非0归一为该状态。kind0更新全部，kind无匹配仍status0；完全不读取声音地址。清零音频不会造成失败，零音量本身是合法值。

## 失败序列也一次列全

- 首次327失败：`0x2b613f8 → 0x2b61548`，先发**注销327/40B**（仅+20 kind，body其余零，`0x2b6156c..578`），再原样重发注册327（`0x2b6157c..588`）；注销状态不单独判定，重发成功则继续32a。故单项可出现327、327注销、327重试、32a共4包。重试仍失败，经`0x2b61594..61694 → 0x2b60c38..c50`进入断言/致命处理。
- 32a失败：`0x2b61468 → 0x2b61698`，发同kind注销327（`0x2b616b0..6d8`，其余body全零），有文件则释放DMM，然后`0x2b61794 → 0x2b61680 → 0x2b60c38..c50`致命。不能把原错误当成可忽略的静音回退。
- 注销的成功回复与注册同为`0d2027130c00018000000000`。未知播放命令不在允许集合；上述错误路径没有播放请求。

## 四任务屏障与日志边界

AP72静音绑定在serial行13082，33d commit/native-free为13084/13086，32e为13150/13152；说明两份回复已释放，且327栈/请求证明提示音线程已消费33d。AP71只有33d等待栈，没有本轮静音提交。AP72尚停首个327，未到32a，提示音注册任务没有完成。

完成全部26包（含index6条件注销）且4个文件前置操作都成功，足以让**regist_beep_signals_i的正常注册循环**返回；音量任务32e已有消费证据。仍不得据此宣布四任务完成：`adf_get_func_i`实际发的是325/8B、等待1325/28B（`0x2b60264 → 0x2dec778/0x2dec7a0/0x2dec7e4`），不是日志中的32d（HDMI格式）。AP71/AP72没有捕获325请求/回复，也没有license_get_i（入口`0x2b61efc`）的完成句柄；缺少日志不是完成证明。四个句柄必须在`0x2b6353c`内匹配减计数到0（`0x2b63628..678`），调用点`0x2b67a6c`；当前没有这一运行回执。

未证实：真实播放、声音编码、原CP映射值与backing生产者；4个文件的运行时地址/大小/volume；license与get_func任务完成及屏障后的菜单。`adf_get_func_i`还包含非ADF初始化调用，不能由325回复可构造推断整个任务完成。

## 复现

项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/adf-beep-regist/audit_adf_beep_regist.py
```

退出0重建proof：固定两份固件哈希、12处精确指令检查、自动提取13行/26包、首个40B请求解码、AP71/AP72只读日志快照。可用参数`ap VA:LENGTH`或`cp VA:LENGTH`打印只读反汇编。使用方法核对[Capstone官方Python说明](https://www.capstone-engine.org/lang_python.html)（2026-11-01）；官方资料仅支持工具用法，Sony私有语义全部由本地VA证据推导。
