# 提示音文件分支：DMM → 文件 → ICDT → ADF

静态链已贯通：**每个文件先分配本地临时 DMM，再分配 remote 保留 DMM，读文件到前者，经 ICDT 传至后者，释放前者，然后把后者的物理值和实际读取长度交给 327**。四轮 remote 目的缓冲必须同时保留，不能复用一个槽覆盖四个 kind。两份原厂配置都为 `0x70817` 提供 **6 个 50KiB 候选槽、单 extent**；原厂精确对齐位及区域地址转换尚未证实，下面 64KiB 对齐是软件模型选择，不冒称原 CP 对齐。

本审计只写本目录，不运行 QEMU、不改 runtime/STATE/原件。`audit_adf_beep_file_dmm.py` 退出 0 重建 [proof](adf-beep-file-dmm-proof.json)，包含原图 SHA256、逐指令字节、配置原始字段、文件 SHA256、模型回复字节与 AP74 日志快照。AP/CP 的 VA 是 image VA；**icdt.ko 为重定位模块，本文 `.text+offset` 不是装载后 VA**。工具 API 参考 [Capstone 官方 Python 文档](https://www.capstone-engine.org/lang_python.html)（本轮 2026-11-01 核对）；Sony 私有语义全部来自本地原代码。

## 时序与寿命

| 顺序（四轮各执行一次） | 原代码定位 | 请求/动作及等待 |
|---|---|---|
| 1 本地申请 | AP `2b60a2c..a48` → `2dda3b4` → `2e4f780` → `2e4efb8` | unit=70817，domain=0，open option=1，40B op20，目标 `0061003c`，同步收包 timeout=-1 (`2e4f150..15c`) |
| 2 remote 申请 | AP `2b60a90..aa8`，同一构造函数 | unit=70817，domain=1，目标 `9061003c`，同步；AP74 在此返回 -3 并走 `2b60b7c→2b60c50` fatal |
| 3 映射本地源 | AP `2b60cb0..cd4` → `2e50150` | 原 `/dev/mem` 字符串 VA `2f9eacc`；open 后 mmap：prot=3，MAP_SHARED=1，offset 对页向下取整，长度含页偏移 (`2e50224..25c`) |
| 4 读文件 | AP `2b60dfc..e28` → `2e50378` | fopen mode `r` (`3c00e9a`；Linux原字节读取)，每次最多0x80B fread 到本地映射，最多 advertised DMM size；EOF 正常，ferror 才报错；实际读取总长 out+8 (`2e503e4..444`) |
| 5 跨芯片 | AP `2b60f7c..fb0` → `2dd4734` → `2e15a18` | source handle+offset、destination handle+offset、size=**目的 DMM 容量0xc800**；不是 fread 长度 (`2b60fa4`)；异步底层、同步外层等待 callback 完成 |
| 6 unmap/free源 | AP `2b61100..120` → `2e50264`，`2b61244..254` → `2e4f9cc` | munmap/close，释放本地源，op23 option2；remote 此时不释放 |
| 7 保存目的 | AP `2b61344..358` | record+28h=remote handle，record+10h=实际fread长度，record+20h=remote phys64 |
| 8 注册与音量 | AP `2b613f0/2b6145c`，包构造 `2dee8b8..2deea04` | 327/40B → 32a/10B，均同步；327物理字段直接取 remote返回值，size取实际fread字节数 |
| 9 后续释放 | AP `2b616dc..6f8` | 32a失败先注销327再 op23 option2释放remote；正常注册成功后保留，销毁/注销前不可回收，正常最终释放入口未完全定位 |

步骤3映射的是本地源，**没有 mmap remote目的**。静音传输若不复制，应清零整个目的0xc800，保存真实 source/destination/容量/fread长度元数据；源可能只写了文件长度，其余字节不能假定初始化。保留原驱动路径会查询两端段表并实际走 DMA，不能用一条 ADF 成功回复替代。

## 40B DMM 请求与两个单元

捕获 `200000001708070000000000ffffffff000000000000010000000000000000000000000000000000`：

| 偏移 | 类型/值 | 原代码 |
|---|---|---|
| 0 | u16 op=20 | AP `2e4f0ac..b4` |
| 2 | s16 status=0，请求清零 | AP `2e4f0b0` |
| 4 | u32 unit type=70817 | AP `2e4f0b8` |
| 8 | u32 handle input=0，alloc不用 | 同清零 |
| 12 | u32 handle output sentinel=ffffffff | AP `2e4f0c8` |
| 16 | u32=0，请求预留 | AP `2e4f0bc` |
| 20 | u16 correlation/调用标签=0 | 请求清零；既有模型回复+6复制此值 |
| 22 | u16 option=1（allocate并open） | AP `2e4f0c0`；封装 `2e4f788` 固定1 |
| 24..39 | 零；回复段地址/大小区 | AP `2e4f0bc/cc` |

回复 op8020：+2 s16转换状态；+6请求标签；+8 u16段数；+10 s16原状态；+12 u32句柄；+16 u32 unit；+24 phys64；+32 size32；其余置零。AP读取状态 `2e4f1b0`、段地址 `2e4f23c`、容量 `2e4f244`、句柄 `2e4f24c`。每个回复发回原请求 source，消息分配/释放遵循既有capid lease，禁止重复完成。

`0x70817` 是 unit type，不是字节数或待分配句柄；其高/低位业务命名无可靠符号证据，不能把 `0x817` 当槽索引。两份原厂配置明确映射它到 extent **231/e7**，attribute=0。CP `b6edcc` 静态表列70817与72317，表所属 RTTI `d7df8f=13AdfMemMgrCtrl`，其虚函数 `5a9d56→4eda7c`；说明这是 ADF 内存管理使用的单元，不能称音频波形编码枚举。

| 配置 | unit表偏移 | 相关规则与原始行 | 结论 |
|---|---|---|---|
| AP `/setting/DmmCfg.bin` | e254:70817→e7 | group1acc(type1260,selector13)，1b1c..1b80共6行 `[0,7,231,51200,271]` | 六槽，各c800，单extent |
| CP `/DmmCfg.bin`（stage128原件） | 9564:70817→e7 | group1748(type33,selector11)，1798..17fc相同6行 | 同样六槽50KiB |
| AP 63a | 100f8:63a→700 | group22d8，24cc/24e0 `[0,7,1792,524288,271]` | 两槽各80000 |
| CP 63a | a854:63a→700 | group1748，201c/2030同上 | 两槽各80000 |

配置记录是候选规则，未执行原解析器/动态模式选择。`0x10f`、region/type7 的原始位保留，不擅自解为对齐；root 记录和选择分支仍需独立核查才能得到原厂物理区域/对齐。现有 `helpers/fx3-dmm-model.c` 仅接受63a，两个512KiB，地址41d900000；`fx3-capid-v27.c:387` 仍将9061003c委派该模型。AP74错误来自不支持unit，不是文件缺失或ADF CRC。新增单元应分离槽几何、共享句柄命名空间，保留generation/opens/错误状态检查。

## 四个文件

guest共同目录 `/usr/share/avsystemsound/`。并非都以文件名出现在 `regular-files`：full-v5 manifest 的 local_file 指向 full-v4/payloads 的内容寻址文件，脚本按 manifest 校验实际 bytes/SHA。

| index/kind | 文件名 | bytes/327 size | 开头（前16B） |
|---|---|---|---|
| 9/10 | `Dslr_Emnt_High_SelfTimer_RemoteRelease.bin` | 2752 / `0xac0` | `170000000000fadbc4d5f30206121c20` |
| 10/11 | `Dslr_Emnt_High_SelfTimer_2sec.bin` | 2752 / `0xac0` | `170000000000fadbc4d5f30206121c20` |
| 11/12 | `Dslr_Emnt_High_Startup.bin` | 9600 / `0x2580` | `17000000000000000000000000000000` |
| 12/13 | `Dslr_Emnt_High_Shutdown.bin` | 12160 / `0x2f80` | `17000000000000000000000000000000` |

这些不是RIFF/WAVE头；原读取路径不解析头、没有CRC。具体声音编码未证实。projection存在不等于本轮guest实际fopen成功，下一轮需只读捕获其结果。

## 最小软件合同与精确回复

建议独立预留 **41db00000/60000**（6×64KiB stride，各只暴露c800），避开41d800000/10000、41d900000/100000、41da00000/10000；集成前运行链仍须核对FDT、kernel reserve与实际RAM。CP协议域使用1db00000+i×10000；这沿用既有DMM模型的APbacking−400000000约定，不冒称原CP区域。remote句柄初代建议8402..8407（63a已有0/1索引），低10位索引、bit15 remote、generation递增并拒绝过期句柄；四个文件依次占2..5。

以下每条40B，correlation=0，对应当前捕获；其他correlation必须复制到+6，不能固定0。所有成功均为s16 status0。

kind10 / handle0x8402 / CP0x1db00000：

- 8020_40B_corr0：`2080000000000000010000000284000017080700000000000000b01d0000000000c8000000000000`
- 802a_40B：`2a80000000000000010000000284000000000000000000000000b01d0000000000c8000000000000`
- 8023_40B_corr0：`23800000000000000000000002840000000000000000000000000000000000000000000000000000`

kind11 / handle0x8403 / CP0x1db10000：

- 8020_40B_corr0：`2080000000000000010000000384000017080700000000000000b11d0000000000c8000000000000`
- 802a_40B：`2a80000000000000010000000384000000000000000000000000b11d0000000000c8000000000000`
- 8023_40B_corr0：`23800000000000000000000003840000000000000000000000000000000000000000000000000000`

kind12 / handle0x8404 / CP0x1db20000：

- 8020_40B_corr0：`2080000000000000010000000484000017080700000000000000b21d0000000000c8000000000000`
- 802a_40B：`2a80000000000000010000000484000000000000000000000000b21d0000000000c8000000000000`
- 8023_40B_corr0：`23800000000000000000000004840000000000000000000000000000000000000000000000000000`

kind13 / handle0x8405 / CP0x1db30000：

- 8020_40B_corr0：`2080000000000000010000000584000017080700000000000000b31d0000000000c8000000000000`
- 802a_40B：`2a80000000000000010000000584000000000000000000000000b31d0000000000c8000000000000`
- 8023_40B_corr0：`23800000000000000000000005840000000000000000000000000000000000000000000000000000`

`802a` 表是保留原ICDT驱动时的精确段查询回复：query40B仅op2a与+8句柄有效，reply+8段数1、+24地址、+32容量。驱动 `.text+2c8..428` 按handle bit15选本地8061003c/remote9061003c，同步等待802a/status0；实际source为驱动动态ID，必须回请求source，不固定81cf61c1。802a+12句柄原接收器不消费，表中保留用于诊断。

ICDT两种集成选一，避免双完成：

1. **推荐静音：在用户库入口/本机02820746消息处实现软件传输**。AP `2e15a38..88` 创建两个8B descriptor `{u32 handle,u32 offset}`，+d8长度来自远端容量、+dc mode=1、+e0 callback、+e8 context。用户库VA `990..a10` 分配48B给02820746，复制前40B并在send返回后读取+40 result32。精确布局为 `[src_ptr64,dst_ptr64,length32,mode32,callback64,context64,result32,pad32]`。两个指针不能保存到完成之后再解引用，应在同步send时捕获descriptor及字段；外层栈等待完成期间保持生存，但仍需管理取消/lease。
2. 校验源/目的句柄和代次、方向、offset+length≤容量，保存元数据，静音清零目的。将原request+40写 `00000000` 让 `icdt.so+9f0` 得到接受成功，**另发一次24B完成到0282078f**：`LE64(original_callback) || LE64(original_context) || 00000000 || 00000000`。这就是逐字节合同；前16B必须来自本次请求（ASLR地址），没有合法的全局常量完整hex。示例callback=0x1122334455667788/context=0x99aabbccddeeff00时为 `887766554433221100ffeeddccbbaa990000000000000000`，仅作编码示例，禁止照发。原库VA `940..98c` 读取callback/context/status，`97c blr x2` 调用AP `2e1574c` 完成future。外层 `2e15ad8..af4` 等待直到完成位，**仅回send成功会挂起**。
3. 若保留原 `icdt.ko`，用户消息处理 `.text+f40..fa8` 先分配24B完成消息、保存原callback/context，再调用 `.text+a50`；它在 `.text+b78/bc8` 依次查询两端DMM，构造DMA descriptor、cache维护，`.text+d90` 调 `pcidma_transfer_async`。DMA完成 `.text+d0..108` 调原回调；`.text+288..29c` 写status到完成+16并发0282078f。此方案还必须提供DMA完成语义，不能只添加remote802a回复。**本审计未实现/验证内核DMA替代钩子**。

最小链不要求额外CP音频传输服务：remote是DMM段服务，跨芯片执行者为AP的ICDT/PCI DMA。原路径仅复制字节、维护缓存和报告传输状态，所列指令没有声音header/CRC/内容校验；据此静音模型可保存元数据并清零，不意味着原CP真实播放允许任意格式。

ADF最终字段由 `2b61354..358→2b613b8..3bc→2dee910..918` 直接传递DMM返回phys64，**不要擅自给327字段加400000000**；APbacking映射与wire域是两件事。+16 size分别ac0/ac0/2580/2f80，+20 kind10..13，+21 priority4/4/6/6，+22 register1，format/continuous/lengths为0；音量仍取sequence_boot+246/245/247/248。327成功12B `0d2027130c00018000000000`，32a成功12B `0d202a130c00018000000000`，与前任合同一致。冲突/越界、重复完成、过期句柄不伪造成功；失败清理仍按原APfatal路径执行。

静音决策下不实现：波形解码、音频生成/播放、真实DMA/CP执行、CPcache一致性硬件、未知音频命令。仅能声称模型登记/容量/完成；不能声称原厂声音、四任务屏障或菜单验收。

## 复现与剩余门槛

在项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/adf-beep-file-dmm/audit_adf_beep_file_dmm.py
```

脚本离线退出0；检查7处关键指令、AP/CP固定图、两配置各6×50KiB、4文件hash、原ICDT DMA/callback relocation、精确回复模板。参数 `ap|cp|icdt VA:LENGTH` 只打印反汇编；`symbols`/`find HEX`供复核。不执行前任脚本主逻辑；读取其proof获取已确认文件路径/顺序。

明确未证实：原厂对齐/region标志位和最终物理区域、配置当前分支是否启用、unit高低位业务命名、正常生命周期最终释放入口、guest文件读取/传输/327实际消费、软件传输钩子的实际接口可用性、所有四任务完成及菜单输出。需要运行链集成后捕获每轮local/remote handle、fread长度、传输接收与callback、释放local、327/32a消费及屏障句柄；本任务不启动该验证。
