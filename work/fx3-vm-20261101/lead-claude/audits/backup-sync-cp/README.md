# FX3 CP Backup 同步：op30 锁定 → 整块 PCI DMA → op30 解锁

**结论：当前等待要补的是 `op=0x30`，但 CP bank 数据不通过 UIPC 多页回复返回。** 原 `backup_get_cp_data` 先发一条 40B 锁定请求，收到回复后调用 `backupfile_get_cp_data`，以一个 PCI DMA descriptor 把整个 CP bank 复制到 AP 第二 BK4，再发另一条 40B 解锁请求。仅回复锁定成功会把程序推到尚未建模的 PCI DMA；不能宣称同步已完成。（backup `.text+2ba8..2c90、7030..7130`；CP `4986f2/4986f6、498832..498952`；AP99-r2 serial LF **28694–28704、44932–44942、61364–61374**。）

**另一处关键边界：原函数的最终返回值只反映末次解锁状态。** 第一次锁定返回非零只记录后继续 DMA；DMA 返回非零也只记录后继续解锁。因此 `Backup_sync_all` 返回0、daemon `notify_one` 或画面恢复，都不能代替数据复制/原文件写入的独立回执。（backup `.text+2be4..2bf0、2c20..2c90、3074..30f4`；AP `2b237b4..2b23824`。）

2026-11-02，只读本地原件和保存运行资料；仅写本目录三个文件，未启动 QEMU、执行固件、改 runtime/STATE/锁/seed 或操作相机。A=原字节/保存直接观测，B=受约束推断，U=未证实。AP、CP、kernel 地址分别为 ELF image VA、Thumb VA、原内核 Image VA；backup.ko 是 ET_REL，本文 `.text+offset` 不是固定加载 VA。CP 文件偏移=VA−108000，内核文件偏移=VA−ffffff8008080000；proof 每个窗口保存完整 raw、文件偏移、指令及 ET_REL relocation。

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/backup-sync-cp/audit_backup_sync.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/backup-sync-cp/audit_backup_sync.py --check
```

第一条退出0重建 [backup-sync-proof.json](backup-sync-proof.json)，第二条重提取后逐字比较、不写文件。[audit_backup_sync.py](audit_backup_sync.py) 核目标卷 UUID、13份固定输入、82条指令、25条重定位、三份daemon等待、两侧跳表、BK4和内存包/复制向量。`dis backup 2ba8 f8`、`dis cp 498832 1c`、`dis kernel ffffff80083220c8 168` 可独立只读复核。serial 固定为 AP99-r2 `runs/ap99r2cpdate600-9391e358/serial.log` 前 **61400个LF行**，后续追加不改变本次 proof。

## 1. AP99-r2 的运行事实与边界

**A：AppBackupDaemon tid528 三次都等待 CP 接收。** 首份快照从 LF28644开始，堆栈为 `osal_rcv_msg_tmo → 匿名text+1524 → backup_get_cp_data+3c → Backup_sync_all+64`，另两份在 LF44936/61368重复。用原模块函数偏移拟合，`+3c` 正是第一次 `.text+2be4`，还没到 `backupfile_get_cp_data` 或第二次解锁。（serial LF **28644、28696–28701、44934–44939、61366–61371**；原 `.text+2ba8/2be0..2bec、3010/3070..3074`。）

**A：原 `pcidma` init 被禁用。** 命令行与blacklist确认 `__boottime___udif_init_pcidma`；当前只实现 reset 的公共 owner 对非op33走 UNHANDLED/no_reply/no_free。选定serial没有保存完整op30 raw/Q，不把本报告的静态构造包称为捕获包。（serial LF **52、57、824**；`helpers/fx3-cp-backup-reset-v3-date99.c:21`；backup `.text+2bd8/14f4/1520`。）

**A：AppFw tid368 在futex睡眠；B：精确归因至设置同步条件变量。** serial的内核栈只证明futex，协调者另给的用户栈归因是 `model_setting_value::sync_and_wait_comp(2b04674)` / `execute_sync_all_if_necessary(2b04738)`；本审计不把内核futex栈升级为独立用户PC捕获。原码确有两个等待循环，分别向daemon排类型13/14，再等相同busy字节与条件变量。（serial LF **21258、21310–21322**；AP `2b046c4..2b04700、2b04798..2b047d4`。）

日期链已有原 type2取钟与软件CP钟commit、force两次 `Backup_write` 实际返回1；它们写的值此时仍为1，不能当作“首次日期页事务完成且force归零”。本次只沿其后的同步门，不补造日期或模型完成事件。（serial LF **1121–1125、14287–14293、14420–14424**；AP 原同步等待 `2b04674/2b04738`。）

## 2. 请求与回复的逐字节格式

**A：两次都是 `op30`，目的 `903e0811`，各自独立生成动态回复Q。** 第一次实参 `(3,0,1)`，后一次 `(0,0,1)`；公共封装的第三项chip1参与目的ID高位，`803e0811 | (1<<28)` 得 `903e0811`。`osal_dynamic_id(2a,3e,...)` 生成本次Q，来包source亦为Q；第二次不可沿用第一次Q。（backup `.text+2bb0..2be0、2bf4..2c1c、1294..12b8、14e0..14f4`。）

**A：40B初始化消息，仅一页；header计数是1个scalar、1个pointer。** 不是reset33的2/0。本例pointer偏移、长度和内容元数据为0，40B由原 `memset` 清零；因此CP实际读到 `+24=0` 作为全子系统选择。这里不需要拼接数据页，不能看到pointerCount1就虚构附加页。（backup `.rodata+80` op30项→`.text+168c`；`.text+1690..16b0、1394..13bc、1418..14ac`；CP `498840/4988e6`。）

| offset | u32 LE值：锁定 / 解锁 | 原证据 |
|---|---|---|
| 00 | `00000030` / 同 | `.text+2bd8、2c10、13a0` |
| 04 | 初始0 / 初始0 | `.text+13a0` |
| 08 | `903e0811` / 同 | `.text+12b8、13a8` |
| 0c | 本次Q / 新一次Q | `.text+129c、13b4` |
| 10 | 1 / 1，页序号 | `.text+13a4/13b0` |
| 14 | 1 / 1，总页数 | `.text+12c0..12d8/13b0` |
| 18 | 1 / 1，scalar count | `.text+1694、13bc` |
| 1c | 1 / 1，pointer count | `.text+16b0→127c、13bc` |
| 20 | **3 / 0**，mode | `.text+2bb0/2c08、169c、13ec` |
| 24 | 0 / 0，CP作为subsystem=0 | `.text+2bcc/2c04、16a4、1468..146c`；CP `4988e6` |

静态模板，`QQ`是每次实际Q的字节；不是AP99实捕：（backup `.text+168c..16b0、138c..14f4`。）

```text
30 00 00 00  00 00 00 00  11 08 3e 90  QQ QQ QQ QQ
01 00 00 00  01 00 00 00  01 00 00 00  01 00 00 00
03 00 00 00  00 00 00 00     # 锁定；解锁改 +20 为 00 00 00 00
```

**A：CP跳表 `4986f6` 的op30目标 `498832`。** 先把+4状态清0，再读+20：mode3设CP primary `+9 SuspendComp=1`，mode2设0，两者将来包+20改成1后进入加锁；mode1直接加锁，mode0解锁。subsystem=0遍历256个锁，非零则取其ID的bits16..23对应单锁。加锁调用 `52ee34`，解锁调用 `52f17c`；本审计未独立绑定这两个下层原函数的符号名，不擅称为读锁或写锁。（CP `498832..49884c、4988dc..498952、a8544c..a8545a`。）

全锁后取CP primary指针 `*013eb2e8`，`a85482(root,1)` 返回 `header.dataOffset(+18)+dataSize(+1c)`，再 `540320(root,size)` 做交接前的数据维护。该调用形态符合cache clean/flush；下层函数硬件细节未独立闭合，只有地址/参数为A级。**解锁不把SuspendComp改回0**，不能自行清这个字节。（CP `498922..498936、a85434..a8543e、a85482..a85510、49893c..498952`。）

**A：原回复是另分配4096B、复制处理后的4096B、source=`003e0811`、dest=原请求+0c。** 对本例成功锁定，+4=0、+20从3变1；成功解锁，+4=0、+20仍0，其余初始化40B保持。原服务没有在这个回复里附CP bank；AP只取+4状态，free回复后释放Q。CP发送失败free回复，最后free来包。（CP `4989f4..498a56、498aa2..498ae2`；backup `.text+151c..157c`。）

UIPC receive timeout明确为 **−1**。通用封装虽计算页数，但本分支只有1页；若计算结果>1，在分配/发送前设置API状态−5并返回−1018，不存在本次事务的“按页回复直到末页”循环。opcode31/32另有固定4096B路径，是另一类接口，不应替代这里的DMA。（backup `.text+12a8..12ec、151c、19bc..19d8`；CP `49884e..49889a`。）

## 3. 完整 CP bank 的实际数据通道

**A：`backupfile_get_cp_data` 以 `Data_getAdrs(root,1)` / `Data_getSize(root,1)` 定位AP第二bank。** 首bank长d172c，4096对齐后为+d2000；当前第二bank长 **14e5ec（1369580）**，物理目的 **4040d2000**。本次保存RAM第二bank与原seed逐字一致，SHA为 `5dc5883fb86d87d14c1c3d530d4d65d903361c189a64edabcd1f636df289f5b7`；这是现有软件存储当前数据，不能称作已运行的原CP primary。（backup `.text+5988..5a58、7040..7070`；CP `a85482..a85510`；保存 `backup-reserved-ram.bin+d2000..2205ec`，proof.storage。）

原模块填写如下descriptor，再在**同一AP目的区**传输前后调用 `__udif_cache_ctrl(...,len,2)`。offset03为零初始化保留字节，+28以后是原驱动会使用的队列/线程私有区，不可把descriptor对象总分配长度误作40B。（backup `.text+7054..70e8`；kernel `ffffff80083220e8..ffffff80083221f8`。）

| descriptor offset | 原值 / 规则 | 原证据 |
|---|---|---|
| 00/01/02，u8 | `0 / 4 / 0` | `.text+7054..7060` |
| 04，u32 | 当前第二bank长度 `14e5ec` | `.text+7064..7070` |
| 08，u64 | CP header首word `04000000` 经 `arch_p32_to_p64` → `404000000` | `.text+7074..707c`；kernel `ffffff800839bb98..ffffff800839bbac` |
| 10，u64 | AP第二bank实际 `arch_va_to_phys` → `4040d2000` | `.text+7080..7090` |
| 18，u64 | 本次加载的 `backupfile_cb_getcp`，即模块text+5e30 | `.text+7090、7198` relocation |
| 20，u64 | context=0 | `.text+7088` |

**关键地址域：descriptor+08的404000000是PCI对端地址，不能去读AP自己的首bank404000000。** 数据读取方向由原 get_cp_data 路径、远端bank头地址和descriptor接线共同约束；kernel `dma_start` 把+08、+10分别写入两个DMA地址寄存器。软件CP应把对端404000000解析为它自己的当前backing **4040d2000**，不是按相同数字复用AP地址域。（backup `.text+7040..7090`；kernel `ffffff8008321ecc..ffffff8008321ef4`；现有 `reset-core-v1.h:4`。）

**A：成功提交DMA不是结束。** `pcidma_transfer_async` return非零直接返回；return0后等 `osal_wai_sem_tmo(803e090b,7530)`，7530为十进制30000的OSAL原超时参数，本审计未逐层证明时间单位换算。原DMA完成调用descriptor回调 `(status,context)`；`backupfile_cb_getcp`不读这两个参数，只signal `803e090b`。所以必须在真实复制验证后恰好回调一次，不能只返回0或空signal。（backup `.text+70bc..7130、5e30..5e48`；kernel `ffffff80083227d8..ffffff80083227f8`。）

**U：当前原PCI DMA没有运行验收。** 原init被禁用，内核API还会访问原channel队列并调用 `pcidma_start`，后者检查连接/启用字段；未初始化队列也可能提前失败，不能承诺“补完op30后只会等30秒”。本审计只关闭descriptor、copy和回调合同，没有创建DMA拦截点或启动硬件。（serial LF **52、57、824**；kernel `ffffff80083221b0..ffffff80083221f8、ffffff8008321ff0..ffffff800832201c`。）

## 4. 在现有第二 BK4 软件后端上的最小诚实合同

下面是供运行链实现的**静态合同，本worker未实现/安装/运行**。现有owner只处理op33 reset，`cp_setup()`首次使用时验证seed digest，然后用第二BK4作为独立软件CP profile；不要再注册第二个public owner或把每次sync重新加载seed。（`reset-v3-date99.c:15..21、46..49`；`reset-core-v1.h:3..5`；CP原入口 `4989d4`。）

1. **同一owner精确接op30。** 先保存实际40B、native message metadata/capacity、dest/src/Q；白名单校验上表十word（mode仅3/0），不猜动态Q。沿用reset使用的实际AP Q分配记账与原destination释放记账，成功发送才移交reply所有权；不越界读取40B来包尾部。（backup `.text+129c..12ec、13a0..13bc、14e0..157c`；现有owner `reset-v3-date99.c:20、31..42`。）
2. **锁定的状态先真实生效。** 初始化/验证现有CP backing，按同一锁/epoch冻结CP写者与reset；mode3把当前bank+9真实设1，再冻结快照。校验整bank、索引边界/长度并读回，允许由该原事务造成的checksum暂时不匹配；更新owner的expected_digest生命周期。现有reset的seed checksum/digest只适用于首次初始化；不能在header+9变化后继续要求初始seed digest。失败则回实际失败或保留重试，不先发成功。（CP `49884a/4988de..498936、a85456`；现有owner `cp_setup/expected_digest`，core `cp_validate(...,0)`。）
3. **锁定回复字节：** 分配4096B并清零；仅复制实际已初始化40B；+4写真实结果0，+20写1；source003e0811，dest本次Q，剩余4056B零是明确的软件差异。它仅代表该软件锁/快照已建立，不代表bank已传送；保存session/epoch供随后的DMA检验。（CP `4988e4、4989f4..498a24、498ab6..498ac2`；AP `.text+154c`；proof.packet_contract。）
4. **精确DMA路径真复制。** 仅接受来自原backup调用点、0/4/0、长度14e5ec、remote404000000、local4040d2000、callback恰为加载模块text+5e30、context0的descriptor。remote源解析到**同一个当前CP backing**，冻结完整原字节到有界临时快照，再复制到实际AP目的并逐字节读回；验证成功、可见性维护后调用原callback `(0,0)`一次。当前软件profile与AP snapshot地址相同，可用该实际快照进行重叠安全复制并标记 `source_alias_destination=1`；不得把这称为独立CP内存/PCI硬件传输，也不得从AP首bank复制或填零。（backup `.text+7030..7130、5e30..5e48`；kernel `ffffff80083220c8..ffffff800832222c、ffffff80083227f0..ffffff80083227f8`；当前bank proof.storage。）
5. **解锁回复与回收。** 原AP等待copy回调结束后自然发第二条op30/mode0；接受它时释放同一epoch的CP锁/快照，bank+9保持1。reply同样4096B，复制这次40B，+4=0、+20=0，source003e0811/dest这次新Q。失败/重试、并发reset和重复callback需有明确session身份，不能双free、把其他请求当解锁，或在复制失败后宣布成功。（backup `.text+2bf4..2c50`；CP `49893c..498952、4989f4..498ae2`。）

脚本只在host bytearray按上述规则生成两组包、对保存CP bank执行+9的唯一变化及完整 **1369580B** 真复制/读回；lock3 snapshot SHA为proof.storage中的实际值，其他字节保持保存原件。它验证字段和数据规则可构造，**不构成内核集成、allocator/callback/并发成功或原CP功能实现**。若运行链改为独立shadow存储，必须仍从这个当前backing初始化一次并维持同一生命周期，不能每次用seed覆盖变化。（CP `a85456`；保存bank+d2000；proof.storage/packet_contract/DMA_contract。）

## 5. 同步后 daemon、原文件保存与 notify

**A：文件保存发生在daemon notify之前，由原 `Backup_sync_all`直接调用。** 用户lib `Backup_sync_all+2294` 发本地3e014d/op10；kernel dispatcher `.text+7e68..7e74` 调原API。API先锁load/save及256个AP子系统读锁，调用 `backup_get_cp_data(3)`；最终return0才调用 `backupfile_save(1)`，随后释放锁并回用户态。（libbackup `2294..22c4`；backup `.text+3044..3078、30e8..30f8、309c..30e4、7e68..7e74`。）

`backupfile_save`依赖已初始化的 `Backup_bin_start/size`、原路径选择、CP第二bank、文件open/write权限和完整写入；它给CP+9设1并重算CP checksum，再写初始完整存储，更新AP count/+9、cookie/checkin及AP checksum后再写header。两条配置路径原值都是 **`/setting/Backup.bin`**。`5d40`底层 `filp_open→vfs_write→filp_close` 比对写入字节数，不完整写返回−5；成功分支还执行原 `backupfile_load(0)`。不能把RAM导出或checksum修补命名为正常文件save回执。（backup `.text+6800..6a84、5d40..5e20、6540..66a4`；路径 `.data+440/+480`，精确文件偏移见proof.native_files。）

当前profile是 `Backup_load=1 Backup_save=0`，**显式 `Backup_sync_all→backupfile_save` 仍无此flag测试**。模块init `.init.text+19c..1b0` 对save0只走提示字符串；不能引用这个参数就保证本次显式sync不会写guest文件。实际guest文件介质、文件内容/加载选择和保存结果仍须运行链读回；本报告没有触发任何文件保存。（candidate `init-reviewed.sh:102`；backup `.text+3010..311c、6800..6a60`；proof.module_init。）

**A：daemon类型13是子系统sync，类型14是sync_all。** 分派先type−1，再查 `3806ad0`；type14→`2b23804/2b23820→2ebf66c→Backup_sync_all`，type13→`2b2378c/2b237b0→2ebf650→Backup_sync_subsystem(2cf)`，并有原 `16f0bd0`门。二者返回后都汇入 `2b237b4`；请求wait字节非0才在mutex `8e5dbd8` 下清busy `8e29f20`，然后在 `2b237f8` 对 `8e31a60` notify_one。该收尾本身不校验保存成功。（AP `2b22ccc..2b22cec、2b2378c..2b23824、2ebf650..2ebf680`。）

**B：这能解释原AppFw的设置同步等待，但不能保证force已清零或首绘必出现。** 原wait循环检查同一个busy字节，原notify可自然解除这一个门；AP99已写的force当前值1仍需后续原日期设置事务改变。是否还有下一项VDF/CP等待、controller创建和新画面，要另以实际原栈和像素回执验收。（AP `2b046e8..2b04700、2b047bc..2b047d4、2b237e4..2b237f8`；serial LF **14420–14424**。）

## 6. 运行验证点与明确未证实项

以下只读探针供唯一运行链使用；本worker未安装。地址必须按本run实际模块基址重定位。（对应上文所有VA，proof.unproven。）

| 验证点 | 必须保存的独立回执 | 原位置 |
|---|---|---|
| 第一条op30 | 完整40B、metadata/capacity、动态Q/source、mode3、发送/接收/释放 | backup `.text+14e0/14f4/1520/154c/1568` |
| CP状态 | 同一epoch/锁、真实当前bank+9变1、快照摘要、所有其他字节 | CP `a85456` 对应软件backend |
| 真复制 | 实际descriptor、两地址域解析、长度、before/after/逐字节readback，alias明确标记 | backup `.text+70bc/70c0` |
| 完成 | DMA实际return、原callback `(status,context)`一次、semaphore wait返回 | `.text+5e30/712c/7130` |
| 第二条op30 | mode0、新Q、原消费、锁释放，不清SuspendComp | `.text+2c1c/2c20` |
| 原文件save | API和save真实return、filp_open/vfs_write实际字节数、原路径文件SHA/两bank checksum/count及下次加载读回 | `.text+30f0/6800/5d7c/5d98/6930` |
| daemon/UI | 类型14、wait字节、busy清零、原notify、AppFw wait返回、新GPE/画面 | AP `2b23820/2b237e4/2b237f8/2b047cc` |

**未证实：** AP99实际op30 raw/Q/页对象；独立用户PC捕获；原CP primary地址域和运行；DMA拦截点、内核所有权与并发/重试集成；实际copy/callback/semaphore/unlock和原文件save/readback；后续设置日期成功/force0、下一次开机及首绘健康、实机效果。**本任务的离线审计已完成；运行修复未实施。** 不能以最终解锁0/notify或host向量PASS跳过这些门。（backup `.text+2c20..2c90`；AP `2b237b4..2b237f8`；proof.unproven。）

方法仅核对 [Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)（2026-11-02）；公开工具文档只支持反汇编方法，Sony私有语义均来自上述固定本地字节和保存日志。
