# r34：原生资源边界审查完成，GPE 可写 parent 总问题仍为 unknown

**没有取得 UI64KiB 诊断存储准入，也没有找到真实 UI 覆盖的证据。** 本轮新增了实际原生调用链、独立物理映射 ABI、固定配置几何和原 kernel 的约束边界；分析交付完成不等于 r33 候选完成或运行通过。r33 保持正式 failed；本轮没有实现、编译或运行 helper，没有 VM/Start/服务/浏览器/QMP/guest命令/设备操作，没有改变FX6拒绝、硬件、运行策略或旧文件。

## 1. 实际成员和函数边界

CPIO `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9` 的1140个header已只读遍历；四个相关成员的header、名称、payload偏移、长度和SHA与r33 ACTUAL-MEMBERS及原文件逐项一致（`MEMBER-BINDING.json`）。仅抽取以下两个 ELF：

| 实际成员 | 字节 | SHA256 |
|---|---:|---|
| usr/lib/libObj.so | 2876600 | c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae |
| usr/kmod/dmm.ko | 118336 | 1e28a4921b36cd8866330a6670d72627d347c556dbea8568cd5b3ab60853e65a |
| usr/kmod/grm_ma.ko，仅比较/读原文件 | 36592 | 6b579c7632bb90a6fe8c97d037abe24f5eb6b840823aa3a0ac8fdbed61ceee12 |
| setting/DmmCfg.bin，仅比较/解析原文件 | 66796 | 48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1 |

实际 `.eh_frame` FDE 确认 `libObj [0x1031b0,0x1032f4)` 为324B，邻接 `[0x1032f4,0x103454)` 为另一个352B函数，映射辅助 `[0xf96f4,0xf97f0)` 为252B。反汇编中最近的导出标签 GetLogicalAddress 不是这三个私有函数的恢复名称，不借标签猜语义。下文 libObj 地址为 ELF链接VA；`.ko` 地址均是 **.text节偏移，不是运行装入VA**。

## 2. 已证的 normal native-open → MA → DMM 路径

`0x1031b0` **没有硬编码 type403 专用分支**；它读取cfg+8的32位type，原样零扩展保存object+38，再发同一种MA消息。type403的特定几何来自实际DmmCfg，不来自一个接受caller物理地址的参数。

| 段 | 原地址/字节证据 | 已证数据流和返回条件 |
|---|---|---|
| 状态/请求 | libObj 1031c0、1031d8–1e0、10320c–21c | cfg+8→type；要求object+20==1，否则返回-3；type写object+38、MA请求+8，cfg+10字节写请求+c |
| MA消息1构造/发送 | 1031ec→102c08，102cac，103254→1031a4 | 分配72B；消息首u16=1；目标/源0x14c0424；1031a4直接尾跳osal_snd_sync_msg，不是未解虚调用，也不是此处直接对/dev/dmm做ioctl |
| 内核MA分派 | grm_ma 68–7c、c4–e4、118–120 | 注册原sync queue callback；实际.rodata跳表 command1→text118→ma_dmm_open_impl，command3→138→ma_create_msp_impl，已按原字节解码 |
| 原DMM申请 | grm_ma 5c0–658→1d0、4a8 | MA读取unit，原40B op20发送到0x61003c，source0x14c0424、option1；失败原路返回；8020先检查signed状态，成功才从+18/+20/+c取得physical/size/handle并ma_list_add |
| 返回object | libObj 10326c–29c | 先检查MA响应status；成功把opaque memspace、uhdl保存object+10/+40，physical/size传f96f4；normal返回值来自MA status。**f96f4的映射返回没有在此改变MA rc**，所以rc0/state10不能单独证明logical非零；当前GPE另检查logical |
| 最终字段 | f96f4、103284–29c | object+38=requested type，+40=uhdl，+58=logical，+60=physical，+68=size，+20=state10；phys/bytes来自原返回，不是cfg任意physical字段 |

`MA-native-open.txt`、`libObj-message.txt`、`MA-dispatch.txt`及`MA-DISPATCH-TABLE.json`保存完整相关原字节/重定位。DMM op20实际处理含 `text5558–5560→dmm_unit_ctrl_Alloc`、`5648–5660→5280→dmm_unit_ctrl_Open`；option/status等原分支未跳过。原IPC的接收和内核回调成立条件不能用r33 mock native返回0替代。

## 3. 配置几何比r33更窄，但不是完整leaf归属证明

复用已绑定该DMM成员的既有80B组头/20B行/单位表解析法，独立解析实际CPIO的全部66796B且恰好消费EOF：

- unit403仅在文件`f508`引用extent545（0x545）。
- 545仅有两条候选规则：文件`16d0`和`1838`，同一组type34/selector10，原五字均`[0,12,0x545,0x140000,0x10f]`。12/10f保留原字段，不擅自命名对齐语义。
- root34行在文件`78`：`[30400000,00040014,00000022,0fc00000,1]`；AP原`GetExtentAreaInfo:text a09c–a0b8`明确读lo32+u16@+6<<32，得到 **430400000/0fc00000，尾端440000000**。与UI `[41dc00000,41dc10000)`不重叠。
- 十条静态root几何均不与UI重叠。此处0fc00000是原DmmCfg root大小，不能与VM另有的CFC00000 memrsv跨度混为一值。

**不能直接据此宣布所有成功native-open均排除UI。** `GetExtentAreaInfo`提供root几何；实际`dmm_unit_ctrl_Open:text92b4–92d4`返回的是所持leaf的 `u64@+8 + u32@+10` 和 `u32@+14`。已看到root初始化`b508–b528`拆分高位/低位，以及递归分配helper `ab08–b318`中的重用、rule选择、递归和child/split构造（如af78–af84、b054–b068、b130–b138）；本轮没有形成覆盖所有成功/重用/合并支路的“extent545返回leaf必为root34合法后代且地址不回绕”的闭合不变量证明。**这个有限缺口是总判unknown的具体原因，不是要求穷举全部固件。** 没有发现已证的此类越界成功反例。

`CONFIG-403.json`保留原文件偏移和五字节组证据，`DMM-unit-open.txt`/`DMM-extent-core.txt`保留实际代码；静态候选表不冒充本轮选中模式、活跃parent身份或guest运行值。

## 4. 独立的显式物理 ABI 与当前GPE登记分开

邻接函数`1032f4`接收x1=physical、x2=bytes，而不是normal-open的cfg+8 unit。它要求state1、physical四字节对齐、bytes>0x400，先调用f96f4建立读写MAP_SHARED映射，logical为0就返回-3；随后才发送 **MA消息3**。grm_ma `ma_create_msp_impl:890–8d8`直接用请求physical/size调用ma_list_add（handle=ffff），不走DMM op20。

UI_BASE=41dc00000、65536B通过上述**本地地址/长度谓词**，也在f96f4第一允许物理地址带内；原默认文件flags为101002，映射prot3。相关五条原指令word已核对，七项Python整数谓词检查通过；没有指令仿真、native mock调用、分配或映射。实际open/mmap/MA成功返回及调用者仍未执行/采集，不能把“参数可接受”写成真实完整调用成功。

**此函数不是当前GPE所观察的native_open入口。** 实际GPE只在1031b0原调用rc0后以`native_open_return_v1`登记；显式物理入口不会因此自动获得native_open标志。原source还会按live identity/phys/bytes撤销变化，malloc补充路径只接受三个已绑定pool tuple，UI不在其中。因此这条独立ABI不能替代r33 mock，作为“UI已成为当前GPE可写parent”的证明。

但它说明**仅凭memrsv证明该地址对原生物理接口排他的诊断存储选址不合适**；当前不应批准空隙作为独占记录区。是否在实际启动路径以该ABI访问UI、以及是否能满足GPE完整登记条件，都没有证据，不在这里扩成漏洞/绕过研究。

## 5. 固定kernel的memrsv实际约束

复用官方FX3 7.00 GPL包（SHA `bb2d9cc6…56d0f`、版本4.9.337、来源Sony官方型号页），**它不是7.02整机源码/配置精确匹配证明**。本轮用既有恢复symbol catalog绑定实际7.02 kernel Image SHA `da4a66fa…4820c`，对8个相关函数逐字节反汇编，地址和file offset均在`KERNEL-EXACT.json`；没有运行Image。

- 实际 `parse_memrsv ffffff8008642370` 调用memblock_reserve（`…23dc`），记录保留列表后调用arch_memrsv_add（`…244c`）。`arch_memrsv_add …635c9c`解析uc等属性，转rmem_arm_add。GPL `mm/memrsv.c:77–102`和arm64/mm/init.c:578–599提供同构含义：Linux内存保留和属性登记。
- 实际 `mmap_mem …2f8228`依次做地址宽度检查、phys_mem_access_prot_allowed、phys_mem_access_prot、remap_pfn_range。这里没有“只要是memrsv便禁止用户映射”的分支。
- `phys_mem_access_prot_allowed …39bd48`读cxd900x0_mmap_debug；0直接允许，非0检查缓存属性/请求flags，可能允许、告警、拒绝或BUG。GPL同函数默认debug0；**没有采集本次live debug值**，不把源码默认当运行事实。memrsv本身不是该函数的排他所有权证书。
- `valid_mmap_phys_addr_range …0968c0`实际检查48位地址宽度；UI范围通过。Image中没有IKCFG_ST，故不宣称恢复了完整实际.config，亦不拿公开defconfig代替；本结论依赖实际编译函数控制流。
- DMM上述路径使用自己的配置/extent表；本轮所追踪成功字段来源没有发现把Linux memblock保留列表当作DMM parent排除表的调用边。**kernel保留不能自动补齐第3节的DMM leaf归属证明，也不能阻止第4节本地参数进入显式物理接口。**

来源原文链接：[Sony FX3 7.00 GPL型号页](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)、[已固定SHA的官方archive URL](https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX3_Ver.7.00/linux-kernel.tar.gz)。复用本地既有下载和跨核对回执，没有下载/执行代码；未借A7C2/FX5/FX6语义替代Sony FX3实际成员。

## 决策和下一步

**当前GPE UI可写parent可达性：unknown；UI记录区存储准入：未批准。** 正常type403配置几何排除UI、原生显式物理接口的本地地址门允许UI、当前GPE不自动登记后者，三件事同时成立，不能互相替代。未证明真实覆盖，也未证明所有相关成功路径绝无覆盖；r31零ring根因仍未定。

[NEXT.md](NEXT.md)只保留两个精确、有限的补证项：545成功leaf的地址/祖先不变量；若要把显式ABI算作实际writer，则需当前启动调用点与参数关联。本任务不设计BSS collector/probe、不更改诊断选址/平台/门，也不授权运行。

复现见 [README.md](README.md)。输入before/after只含必要技术材料，共享README不列冻结；结束结果见INPUTS-AFTER。全部输出含源清单、地址/字节、原反汇编、解析脚本和范围声明，SHA256SUMS覆盖清单本身以外的所有交付。
