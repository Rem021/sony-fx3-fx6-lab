# AP89 fmt2、通用绘制与资源内存审计

2026-11-02。**AP89 的 73 条完整被拒 BitBlit 需要三项扩展：有来源与生命周期的资源内存登记、fmt2 文字蒙版候选模型、以及真实存在的缩放路径。只加入 fmt2 或放宽 545 地址门不能完成这批请求。** 原指令重放得到 **28 条 fmt0→0 通用图元、36 条 fmt0→0 StretchRotateBlit、9 条 fmt2→0 通用图元**，没有命中 `b234` 快路径或 `b578` 纯转换路径。逐条原始参数、尺寸、地址、颜色、flags、分派和寄存器写入均在 [proof](gpe-fmt2-proof.json)；例见 AP89 serial LF **21880、21884、21888、21963**，原分派 `libgpe 0xcf2c–0xd144`。

文字路径支持“8bit 字形覆盖度，加前景色后混合”的 **B 级语义**，不支持把任意 fmt2 宣布为已证实的硬件 A8。硬件码 `0x21`、颜色运算码 `14`、混合因子和精确舍入仍缺硬件像素 oracle；下文给出可明确标记的近似候选，不冒称逐位规格（`libgpe 0xbd28–0xbe84`，`libObj 0x5c710–0x5c81c、0x10e944–0x10e97c`）。三块资源池有原厂启动日志，但保存的 extent 快照不覆盖它们，**真实资源 uhdl/type/generation 未恢复**，不得按这三个地址区间注册（serial **8572、8583、8594**；615 条保存的 extent 行见 proof）。

## 复现与交付范围

在 `/Volumes/KAFU2T/AI/Projects/Mac` 执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/gpe-fmt2-resource-extents/audit_gpe_fmt2.py
```

退出 0，重建 `gpe-fmt2-proof.json`。收尾连续两次重建的 proof 完全一致，SHA256 为 `4ec69375e9ae338c1d9bfa5ac730b936b67f0559087823091b49edb282d3cf2f`，目录内仅指定三份文件。只写本目录的脚本、proof、README；未启动 QEMU、未改 runtime/STATE/原件、未拿运行锁、未操作相机。脚本检查目标卷 UUID，固定原件和 AP89 输入 SHA；复用已固定 SHA 的 `../gpe-blend-p3/audit_gpe_blend.py` 中 Image/Replay 类，关闭 bytecode 写入。它把 73 份参数逐一送入原 `cf2c`，并允许原调用转到 `c878`；所有日志、csl 构造器、完成账本均截获，在 `af30` 提交前停止。它验证**分派与命令生成**，没有执行原厂硬件像素运算。

| 等级 | 本次含义 |
|---|---|
| A1 | 固定版本原指令、只读表、重定位；有界原指令重放到提交前 |
| A2 | 保存 AP89 serial 的实际参数/日志/原 proc 行；行号按 **LF** 分行，不按 CR 或 Unicode splitlines |
| B | 多条静态链与运行参数交叉支持的语义；未捕获端到端生产者身份 |
| M | 拟议的软件模型与实现约束，不是对原厂行为的证明 |
| U | 未证实，不可静默默认或借后端自身输出证明 |

原件在 `menu-repair-01/original-uipc/ap-projection/`：用户库为 `regular-files/usr/lib/`，内核模块为 `full-v4/regular-files/usr/kmod/`。所有用户 VA 为各 ELF 链接 VA；`.ko` 的数值为 **`.text+offset`**，不是模块装入后的绝对 VA。源 SHA 完整记录在 proof.inputs：

| 输入 | SHA256 |
|---|---|
| libgpe.so | `363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464` |
| libObj.so | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |
| grm_ma.ko | `6b579c7632bb90a6fe8c97d037abe24f5eb6b840823aa3a0ac8fdbed61ceee12` |
| dmm.ko | `1e28a4921b36cd8866330a6670d72627d347c556dbea8568cd5b3ab60853e65a` |
| AP89 serial.log | `897dd55e283097e38fa70d286a3dce1bbd252d225c48cf78a5fb515d07ea1c5d` |

联网核对 [Linux DMA API 原文](https://docs.kernel.org/core-api/dma-api.html) 只用于“分配身份、大小、地址与释放必须对应”的通用术语；它不定义 Sony 私有 DMM、句柄编码或 proc 列，以下规格来自本地原件与回执。

## 1. AP89 实际命令与分派

输入为 `runtime/runs/ap89r2replay-a55f292d/serial.log`，并逐项与 `runtime/ap89-gpe-command-statistics.json.rejected_full_raw` 中 BitBlit 的 sequence/raw_hex 一致性核对。**全部 73 条**：dst=`0x43feb5100`、dst fmt0、selector `P70=1`、conv `P71=0`、K `P72=255`、rotation=0、async=1、callback/argument=0；每条完整字段在 proof.commands，不只统计 marker 中简写的源宽高。例 serial **21878/21880** 是 sequence2 marker/144B 原参数（A2）。

| 数量 | src/dst fmt | P73..78 | P6c..6f | 原分派 | 证据 |
|---:|---|---|---|---|---|
| 28 | 0/0 | `01 00 00 00 00 00` | `00 00 00 00` | `cf2c → d05c → bbcc` | 例 seq2，serial 21880；尺寸相等后 `cfb4–cfbc` |
| 36 | 0/0 | 同上 | 同上 | `cf2c → d124 → c878` | 例 seq3/5，serial 21884/21888；`cfac–cfb0` **先于 flags 判断** |
| 9 | 2/0 | `01 00 0e 00 00 00` | `dd dd dd ff` | `cf2c → d05c → bbcc` | 例 seq11，serial 21963；`bd54:464=21, bdd4:740=14, bdec:741=ddddddff` |

36 条不是“尺寸相同的 memcpy”：seq3 目标 `(86,65,468,6)`、源 `(6,0,308,6)`，原 `cslMakeZoomSprite` 取得 `468/308=1.5194804668f, 1.0f`；seq5 目标 `6×44`、源 `6×40`，比例 `1.0f,1.1000000238f`。原 `ce98–cedc` 在 P74=0 时从两边尺寸计算比例，**不使用 raw P60/P64 的零值作为倍率**；`ce50` 调 ZoomSprite，`cd14` 另调 H/V，最终仍在 `af30` 提交前截获（A1；原始 serial **21884、21888**；proof.commands.original_replay）。

`b234` 与 `b578` 均为零命中；不能把“BitBlit fmt0→0”直接等同于 v14 已支持的无 flags 混合。静态条件：selector2原错误；rotation/尺寸不等先检查；同尺寸任一 P73..78 非零进 bbcc；全 flags 零才继续快混合/复制判定（`cf48–cfd0、cfe8–d094`，A1）。

### P73 的更精确边界

| 字段 | 原行为与结论 | 原 VA |
|---|---|---|
| P73 | 同尺寸时非零强制 bbcc；**bbcc 内不再读它**。因此不能将它叫 H/V 翻转，也不能仅从该分支给它取“alpha enable”语义名 | `cfb4–cfbc`、完整 `bbcc–c150` |
| P73，尺寸不等 | c878 确实消费：`467=!!P73`。这里不是可忽略 padding；467 的采样/纹理硬件意义 U | `ca54–ca68` |
| P74 | AP89 全0；不把 src x/y 折进物理基址，保留纹理坐标；缩放比用目标/源尺寸 | `bce8–bd14、c0a0–c0d8、ce58–cedc` |
| P75 | AP89 fmt0为0，fmt2为14，写 `740=P75&15` | `bdc0–bdd4`；缩放 `cac4–cad8` |
| P76 | AP89全0，写 `730=0`；不能命名为已证实的 ROP/alpha 算法 | `bd94–bda8` |
| P77/P78 | 才是 H/V 参数，AP89全0；原仅 value==1置位 | `c0dc–c0e8`、前审计 `13e34–13e58`；缩放 `ccfc–cd14` |

P73 在缩放入口映射到467这一点补充了前次“bbcc内无读取”的局部结论，不能把后者扩大到全部 BitBlit（A1）。

## 2. fmt2 的文字语义、颜色来源和像素公式边界

**A1：** fmt2 每像素1B；通用硬件码0x21（`b1f4–b230`、表`151f8`、`bd28–bd54`）。源非fmt3时本路径不读 conv71，因此 AP89 的 conv0不是 palette索引，也不会调用 `af98` 固定矩阵（`bd78–bd90`）。这些事实本身不能区分 A8、L8 或索引纹理。

文字链的新增支持如下；不把“某条可行静态链”说成已经捕获该条 AP89 的生产者栈：

| 链段 | 确认内容 | 等级 / VA |
|---|---|---|
| ux TextLayout→TextRM | `15ab5c` 整理目标尺寸、stride、buffer，`15abcc` 调 `TextRM_drawText`；字体文件注册经虚槽0x10 | A1，`15ab98–15abcc、15e920–15e968` |
| TextRM 的灰度分支 | `text+24 !=1` 选 GrayImage(Buffer/BlockBuffer)，将目标 buffer交给原 glyph绘制；GrayImageBuffer_init按行stride建指针并逐行清0 | A1，`5c710–5c81c、5f970–5fa4c`；该TextRM同时有Color分支，不是所有文字强制灰度 |
| 字体/前景色到图元 | renderer的输入色取 `[source+0x24]`（保存到x23后+0x14），Color复制 `str w1,[x0]`；第4字节送Q2c→K，源图像kind8时设Q50=14、Q3c..3e=原色前三byte、Q3f=255 | A1，`10e918–10e97c、133644–133648` |
| Q→GPE颜色与方法 | Q28=2→P70=1；Q2c→P72；Q3c..3f原样→P6c..6f；Q50→P75；源bitmap枚举4→GPE2 | A1，`101b88–101bb8、101c74–101ca8`，跳表`1e2214` |
| 文字重着色条件 | TextSprite将资源格式8或0x304单独走字体前景色设置，再把资源交给ImageElement；这是“单通道文本资源+独立前景色”的另一上层支持 | A1结构、B语义，`16afa8–16b030` |
| 运行绑定 | 9条fmt2均来自命名`mpTextHeap`，全部颜色ddddddff、P75=14；同池另有1条fmt0（seq61），故**不能按池名决定像素格式** | A2，serial 21963/21989/22074/22164/22245/22324/22489/22491/22496；fmt0例22326附近，精确行见proof |

**B 强结论：这些 fmt2 文本最合适的工作语义是灰度字形覆盖度，经原前景色重着色，作为 alpha 蒙版合成。** 若直接把每个byte复制成RGB灰度，原厂专门传入的前景色与运算码14就无法解释；也没有在这条链恢复出 palette地址/长度或CLUT加载。**但仍未证实**格式0x21的通用硬件通道展开、opcode14的数学定义，以及每个运行buffer确实由此GrayImage分支产生；不应据此为任意fmt2打开通用A8/L8/索引转换（`bdc0–be00`仅写寄存器；上述TextRM/renderer链为局部静态连接）。

### 可供 v16 选择的明确近似模型（M，不是硬件公式）

只限 AP89 已观察的 `srcfmt2,dstfmt0,P70=1,P71=0,P73=1,P74=0,P75=14,P76..78=0,rotation0,同尺寸,Pcolor[3]=255`。令 `m=源byte`，`T0..2=P6c..6e`，`K=P72`，`D`为目标fmt0每个nibble乘17扩成8bit；按Lead既有`straight_over_v1`定义：

```text
R255(n) = floor((n+127)/255)
a8 = R255(m*K)                    // 实际AP89的K=255，故a8=m
Co8 = R255(Tc*a8 + Dc*(255-a8))   // c0,c1,c2分别
Ao8 = a8 + R255(Ad*(255-a8))
q4(v) = min(15, floor((v+8)/17))
O16 = q4(Co0)<<12 | q4(Co1)<<8 | q4(Co2)<<4 | q4(Ao8)  // LE16
```

颜色来自原参数，**不要硬编码灰色221，也不要对fmt0源一并乘`00000000`**。Pcolor[3]在该原renderer分支强制255，原色alpha已放K；擅自再次乘原色alpha会重复衰减（`10e92c–10e97c`、`101b94–101bb8`）。若未来需接受Pcolor[3]≠255，`As=R255(m*T3)`再乘K只是另一个待确认候选，本次不将其列入准入。

script中的16个人工向量只验证候选数学的可复算性：m=0/1/15/16/127/128/254/255，包含AP89灰色和一组非对称/半透明扩展输入；后者用于显示阶段舍入影响，**不代表该扩展输入已准入**。黑色不透明目标、T=ddddddff时，m=0得到`000f`，m=255得到`dddf`；中间舍入和fmt0量化是假设。marker应另写 `approx_fmt2=1 formula=a8_color_straight_over_v1_candidate original_fmt2_semantics_unproven=1`（M；硬件算术U，`libgpe bd94–c09c`没有CPU像素乘加）。

### fmt0→fmt0 是否就是 v14 的公式

**只能复用既有近似模型，不能称“已证实就是”。** AP89的28条同尺寸通用图元与36条缩放都设置 `760=1,770=05040501,771=0`，与selector1/K255快混合的原`B01=1,B02=05040501,B03=0`同形（`be04–be84、cb08–cb88、b2c8–b32c`）。按Lead的近似政策，可对采样后的fmt0源沿用v14的`a8=R255(As*K)`与上述Co/Ao式；无color-op时不附加tint。**硬件因子意义、4bit扩展/量化、输出alpha仍U**，而36条还缺reg467=1采样滤波oracle。v14自身明确拒绝P73非零、缩放与fmt2；AP89返回reason2/result5首先是规划unsupported，不能仅归咎于后面的单extent门（`impl/gpe-p3-approx/fx3-gpe-backend-v2.c:77–80`；adapter先`gpe_plan_blit`，成功后才`within/extent_live`；serial 21878/21880）。

## 3. 资源池、DMM身份与生命周期

### 实际归属和当前缺口

| 池 | 原启动日志范围，尾端不含 | 观测源地址 | 依据 / 等级 |
|---|---|---|---|
| mpMemoryHeap | `410524000–410924000`，0x400000B | `4105243c0 / 410537000 / 410549c40` | serial8572；3条fmt0，A2 |
| mpMemoryHeap2 | `410924000–410c64000`，0x340000B | `4109243c0 / 410924e00 / 410924f80 / 41092d1c0 / 410935400` | serial8583；60条fmt0，A2 |
| mpTextHeap | `410c64000–410e64000`，0x200000B | proof.source_addresses逐项列出10个基址 | serial8594；9条fmt2、1条fmt0，A2 |

三个池共覆盖73个输入基址，**只是与真实命名/范围的对应，不构成分配凭据或字节span安全证明**。保存的四次proc输出共615条extent行（包含启动时输出），没有任何行覆盖上述三个池；缺失原因（比如远端/静态DMM域）本审计未确定，不猜测替代句柄或高位换算。原厂启动日志和`/dev/mem`映射存在也不能替代生命周期（serial8572/8583/8594；proof.saved_proc_extents、source_addresses）。

屏幕“545”是历史适配器名称/`type`列，不是真实unit handle或extent id。原行：

```text
serial14741: 0081 0003 00000001 00000545 00000000 00000000 00000003 0000008c 43feb5000 (430400000+0fab5000) 00140000
serial14608: 0402 00000403 0002 01 01 00 01 00000003 43feb5000 00140000 0081 < 0003
```

即屏幕unit handle=`0x0402`，unit type=`0x403`；extent id=`0x81`，parent=`3`，extent type=`0x545`，relation=`3`，serial=`0x8c`。不得用固定`gpe_ref{0x545,1}`声称原厂句柄/代次；它只是旧adapter的内部标签（A2；原proc列定义下文）。

### 原 `/proc/udm/dmm_extents` 格式

原字符串与打印函数给出 **12列**：`id parent attr type table pict_id relation serial address (base+offset) size`。`dmm.ko .text+0x5d0`读链表；有parent时`6e4–72c`取记录id、父id、attr、type、table、relation、serial、base、offset、size；无parent走`820–878`。格式串在`.rodata.str1.8+0x1f8/0x248`，头在`+0x108`（A1；proof.kernel_original/kernel_proc_strings）。

解析要验证完整行、完整EOF、唯一身份、`address==base+offset`、非零size、无整数溢出；只选与当前有效unit/parent关系相符的最窄叶extent。不要因root覆盖所有DDR而注册整块root，也不要把type/pict/relation当handle/generation。`serial`提供原分配标识线索，但其位宽/重用/回卷保证未闭合；本地代次应另建单调epoch。两次相同快照不能排除中间释放再分配的ABA，也不能提供pin（M；字段来源为上述A1打印器，释放入口`dmm.ko b768–b79c`）。

### `GetDmmMemInfo` 不是查询：原分配链已闭合

| 步骤 | 原行为 | VA / offset |
|---|---|---|
| GetDmmMemInfo(x0,out) | 把x0写输入+8，new 0x118对象；随后执行分配和地址转换，输出physical/logical/size | libObj `101d84–101e28、102394–102430` |
| 建立memspace | 输入+8作为type，构造MA消息1，成功后保存opaque memspace、uhdl及映射；这是分配，不是“输入已存在handle” | `1031b0–1032cc、1031a4–1031ac` |
| 原内核MA | `ma_dmm_open_impl`发40B `op=20,+4=type,+14=req_id,+16=1` 到DMM队列61003c，source14c0424；收8020取+18 physical、+20 size、+c uhdl，再ma_list_add | grm_ma `.text+5c0–658、1d0–2d8、4a8–56c、11e0–1290` |
| 映射/身份 | libObj调用f96f4映射`/dev/mem`，建立physical/logical基址；成功object状态10 | `103278–10329c、f96f4–f97ec` |
| 内部malloc/free | MA消息9/10分配/释放子块，object+24为未释放分配计数；**不是绘制pin/unpin** | `103550–1035f4、10364c–1036fc`；grm_ma `a30–b0c、b50–be0` |
| 关闭 | 状态改2，等object+24归零，撤映射再MA消息2关闭；内核按引用计数释放memspace，最后引用才发DMM关闭 | libObj`103454–10351c`；grm_ma`6a0–740、1428–151c` |

因此不能在每次绘制主动调用GetDmmMemInfo，否则会分配/改变状态。原文件的函数名不足以推出纯查询语义。`grm_ma`另保留名为`ma_memspace_info`的只读proc输出，含name/refs/uhdl/physical/size；回调`.text+16a0/1708`和原字符串均在proof，但其本轮实际挂载路径/输出未保存，不能伪造读取回执（A1，尚无A2）。

### 可安全接入的登记方案（M，待实现/验证）

1. **首选原事件**：在原libObj `1032a0`成功支路被动记录现成object，不调用创建函数。要求`w22==0`、state@+20==0x10、完整读取；字段为`+10 opaque memspace identity`、`+38 requested type`、`+40 uhdl`、`+58 logical base`、`+60 physical base`、`+68 size`。这些偏移来自`10320c、10327c–10329c`和`f96f4–f97ec`，以库SHA+原字节守卫绑定。运行中取得的真实值才生成`(object,uhdl,type,local_epoch,phys,size)`，不能把上表三个池地址预填成允许列表。
2. **子分配也要观测**：原malloc成功`1035dc–1035f4`可取得本次返回逻辑指针及原size/alignment；按原`102b98/102bd0`区间换算绑定父memspace；free入口`10364c`必须在复用前使对应子块epoch失效。整个memspace仍存活不能证明子块未释放/移动；compaction须同样失效并重新绑定（MA消息9/10；grm_ma `a30/b50`）。
3. **释放与绘制串行**：关闭在状态2前置撤销新租约，等软件读/写租约清零再让原释放继续；free/compaction同理。不能只在原函数返回后删除表项。原object+24仅分配计数，adapter必须用已有bitmap读/写锁及共享生命周期锁保护真实读窗口；这份审计未证明已存在可直接调用的pin API（`1034a8–1034e4、1036f4–1036fc`）。
4. **只读proc候选**：若一个来源确实出现在原dmm_extents（或后续确认的ma_memspace_info），可只读读取并匹配完整身份/边界；前后快照均相同只是检测手段，仍须租约/释放拦截保证无TOCTOU/ABA。**本AP89资源池不满足proc覆盖条件，所以不能用当前快照注册它们。** 日后补采实际memspace/uhdl快照或原事件再开放（A2缺口如上）。
5. **源/目标分别登记**：GPE后端内部id独立于厂商type/uhdl；两者有自己的generation、read/write权限、逐行span和偏移。源只读映射、屏幕目标可写映射；mmap页对齐的前后padding不得成为可绘制span。屏幕+0x100头保护沿用原545合同，不要无依据给资源池套同样+0x100头。源行字节数用源fmt bpp，目标用目标fmt bpp，fmt2→0不能复用同一`line`（M；原stride/format `bc24–bd54`，原byte换算`b1f4`）。

## 4. v16 实施规格与宿主向量

表中“近似”须由Lead延续其视觉模型决策并输出对应marker；没有硬件oracle的项不得称原厂等价。失败仍走原Main一次失败完成，不给假成功；源/目标安全拒绝须在任何像素写前完成（原完成合同沿用`gpe-menu-draw`与v14；本次没有改变完成逻辑）。

| 子集 | 实现输入与动作 | 证据/验收门 |
|---|---|---|
| 资源适配层 | 原事件登记父memspace及子块；full64物理地址、真实uhdl+本地epoch、源读/目标写租约；释放/compaction先撤销再复用 | 上文`1031b0/103454/103550/10364c`；缺A2实际资源句柄，先只记录再验收 |
| 28条fmt0通用 | P73=1、P74..78=0、s1/K255、同尺寸；按完整clip、src/dst坐标与各自stride采样；复用v14近似blend，不对color00000000做tint | serial21880；`bbcc→be84`；`approx_blend=1`，新增flags子集明确放行 |
| 9条fmt2文字 | 上述严格字段白名单；读取1B覆盖度，颜色取P6c..6e，按候选式写fmt0；不引入CLUT、不将byte当RGB灰度 | serial21963等；`bd54/bdd4/bdec`，B/M/U边界如上；`approx_fmt2=1` |
| 36条缩放 | 目标/源尺寸不等，P74=0，倍率由目标/源尺寸得出；P73写467=1；源crop、clip、采样后再blend | serial21884/21888；`ca54–ca68、ce58–cedc`。采样滤波/坐标精度U，需单独显式近似政策或保持unsupported |
| 未观察组合 | fmt3/4、未知P75/76、fmt2目标、P74≠0、rotation≠0、未知conv/selector保守拒绝 | 不借本审计扩大到原厂全部ABI；`cf48–d144、bd78–be00` |
| 完成与发布 | 像素写入和内存可见性、释放租约后按既有单次callback→同步status顺序；Flush维持批次失败语义；输出保留原始参数、scope、epoch和近似标识 | 前审计`af08/a110/a158、9c34–9c4c`；仍需Lead运行链真实readback验收 |

建议宿主测试直接从 proof.commands重放全部73份原144B参数到规划层，不把73例改造成同尺寸假样本；实际绘制数据用人工缓冲，标注为模型测试。必要矩阵：

- **fmt2/颜色/量化**：m取0/1/15/16/127/128/254/255，T用独立R/G/B与dddddd，K取0/1/127/254/255；目标alpha0/部分/满值，透明源带非零色，验证不发生RGB泄漏。分开测nibble*17扩展和结果nearest17，原fmt0 Fill仍保持高4bit截断。16例候选期望在proof；不以它们证明硬件（M；颜色/原打包依据`10e944、c400`）。
- **源/目标不同bpp**：fmt2 source stride112、width106、height42的AP89 seq11，目标stride640；两边padding哨兵、最后一行越界、1B差边界、overflow、负校正、物理包络重叠、跨源extent分别拒绝零写。源readonly/目标write权限分别检查（serial21963；`b1f4、bd18、bc34`）。
- **实际缩放**：seq3 308→468、seq5 40→44、九宫格边界和单像素色条；比较nearest/linear候选、边缘clamp、alpha边缘，采样滤波未证实前不得使用“硬件正确”期望（serial21884/21888，原`467=1`）。
- **flags隔离**：同尺寸P73=0/1强制走bbcc的其他条件保持一致，原描述符应一致；缩放P73=0/1原467应分别0/1，P77/P78才改变H/V。P75=0/14各自处理，其他值不混进文本默认（`cfb4、ca54、bdd4、cd14`）。
- **生命周期**：相同physical被不同epoch重新分配、同uhdl复用、父池活着但子块free、绘制中free/close/compact、proc读取截断/重复/父root包住未知源、反复快照之间ABA；全部阻止过期写入/读取及假成功。验证原allocation计数不是绘制lease（`103454、103550、10364c、grm_ma1428`）。

## 5. 首个对话框身份与未完成项

AP89 serial **18258** 从scr0039_boot开scr0099_0001，**20215**明确`Caution [MOUNT_ERR_EXTMEDIA_SLOT1_FOR_AUTO_TRIGGER] appears`，**20217**随即`scr0099_0001 -> dlg_dbl021_base`。因此当前对话框关联**外部媒体槽1挂载失败自动提示**（A2），不能解释成日期/地区设置。appFw RTTI字符串VA`3035b40`、RTTI`42b6a20`、主vtable`42b6d08`确认generic `dlg_dbl021_base_controller`；`1c9bcdc/1c9bd58`处理两组选择状态，但这些静态结构不能单独确定本轮正文。**精确本地化字符串、按钮文案、完整资源ID仍未绑定**，未对该错误做屏蔽或回复（A1/A2，proof.dialog_static/runtime_evidence）。

本次完成的是可重建审计和实施边界。未完成的是：资源真实uhdl/type/代次的运行回读、子块与bitmap锁的完整连接、fmt2/op14与缩放滤波的硬件像素oracle、v16实现/宿主后端测试、guest执行及菜单画面/按键循环验收。**当前证据不够构成“全73条可按原厂精确执行”的完整规格**；它足以避免仅放开地址或fmt2的误修，并为明确标记的近似模型提供窄子集（原缺口锚点：`bd94–c09c、ca54–ca68、103454–1036fc`及serial资源日志与空匹配）。
