# AP93-r5 离屏资源子块与 seq217 审计

2026-11-02。**资源池子块作离屏绘制目标是原厂支持的用法；seq217 实际是 fmt0 的 29×29 → 116×116 四倍缩放覆写，不是同尺寸复制，也没有进入 `b234`。** 原 `cf2c` 重放得到 `d0b4(P74=0) → d124 → c878`，ZoomSprite 的两倍率均为 4.0，`467=0`、`760=0`（混合关闭）。因此 v19 需要同时补目标资源准入和 selector0/K255/flags0 的缩放覆写规划；不能把参数改成现有 selector1/P73=1 来绕过门禁（libgpe `cfac–cfb0、d0b4–d124、ca54–ca68、cd98–ce30、ce8c–cedc`；AP93-r5 serial **37068–37074**）。

**“完整 span 在活跃父 extent 内 + 有一个 bitmap 对象”只足以表达区间模型的有限承诺，不足以证明写到了仍属该 bitmap 的活跃子块。** 本轮可从保存日志重建两个成功 malloc 与后续 free 的顺序，但没有恢复这两个对象的完整运行时 BitmapImpl 字段、seq217 的 bitmap 指针或锁所有权；compaction 和排队 ABA 也未闭合。v19 可延续已批准的 `allocation_interval` 模型，必须保留这些未覆盖标记；若要增加“子块仍活跃”的准入保证，必须实际跟踪 child epoch、free/close/replace 和命令绑定，不能改 marker 就声称已 pin（libObj `f14fc、1035dc–1035f4、10364c–1036fc、f0a98–f0abc、103804–103964`；serial **16838、37065、37071、37108、37999**；resource-v3-target.inc **79、106**）。

## 复现、输入与证据等级

在 Mac 项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/offscreen-subblock/audit_offscreen.py
```

退出 0，仅重建本目录 [offscreen-proof.json](offscreen-proof.json)。[脚本](audit_offscreen.py) 固定原库、AP93-r5 serial、v18/v3 源码与复用重放器 SHA；检查外盘 UUID；所有 bytecode 写入关闭。原代码在隔离 Unicorn 中执行到 `af30` 提交前截停，日志/描述符构造/完成账本均截获，没有 QEMU、Linux guest、硬件像素运算或相机操作。实际运行日志为 `menu-repair-01/runtime/runs/ap93r5frame-19bbfb81/serial.log`，行号统一按 **LF、1起算**，不按 CR 分行。

收尾连续重建内容一致，proof SHA256=`331cd0acab44d79634d297d7662cf0f46af0304add1f4071c2ee31455febb4a6`；包含35个原代码块、4164条原指令，libObj全部可执行section的xref扫描逐字节解码覆盖检查通过，12项人工宿主向量通过。目录内仅README、脚本和proof三份文件；这是本审计回执，不是v19后端测试回执。

| 等级 | 含义 |
|---|---|
| A1 | 固定 ELF 原字节、重定位、调用路径，以及原指令有界重放到提交前 |
| A2 | 固定 AP93-r5 serial 的真实参数、分配/释放与原命令观测 |
| B | A1/A2 共同支持的解释，运行时对象/栈仍未完整绑定 |
| M | v19 规格与人工宿主向量，不代表 v19 已实现或原厂像素 oracle |
| U | 未证实，不能静默填默认值 |

所有 VA 是对应 ELF 链接 VA；库均为 `original-uipc/ap-projection/regular-files/usr/lib/` 中原件。原库 SHA：libObj `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`；libgpe `363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464`；AP93-r5 serial `823a77ce7fc9946cc15ccb9f4627cd36424a7e846edbd00d8693a6e14a55aad3`。完整来源、块字节哈希、逐指令、参数每字节归属和宿主向量均在 proof。项目公共边界和既有三份指定审计已完整阅读，PLAN 已读至 AP93-r5 最近条目；未修改它们。

本轮联网查阅 [Capstone 官方 Python 文档](https://www.capstone-engine.org/lang_python.html)，仅用于反汇编 API；Sony 私有格式与语义全部取自原件与运行记录，不由公共 API 文档推断。

## 1. 两块子分配和父资源身份

父池是原日志的 `mpMemoryHeap2`：`0x410924000–0x410c64000`，大小 `0x340000`。它在成功原 malloc 后由 `malloc_parent_v1` 登记，**不是一个新屏幕对象，也不满足 native_open/type403 的旧目标白名单**（A2：serial **8536、16838**；v18 **184**）：

| 身份字段 | 本次真实值 |
|---|---|
| parent object | `0x7f50691c00` |
| opaque identity / uhdl | `0xffffffc11bc17e00` / `0x30303030` |
| type / state / 本地 epoch | `0` / `0x10` / `3` |
| logical / physical / bytes | `0x7ee375e000` / `0x410924000` / `0x340000` |
| vptr / 登记来源 | `0x7f9033ca48` / `malloc_parent_v1` |

这些字段来自 serial **16838**，偏移来自 libObj `10320c、10327c–10329c` 和既有 resource-extents 审计；本地 epoch 不是厂商 generation。不能把 `uhdl=0x30303030` 当作文字、句柄编码规律或屏幕 token（A1/A2）。

| 子块 | malloc / 释放观测 | logical / physical / bytes |
|---|---|---|
| FillRect 目标兼 BitBlit 源 | serial **37065** 成功，align=`0x40`；**37108** free 入口观测 | `0x7ee37704c0` / `0x4109364c0` / `0x780` |
| BitBlit 目标 | serial **37071** 成功，align=`0x40`；**37999** free 入口观测 | `0x7ee3770c80` / `0x410936c80` / `0x7400` |

按记录中的 malloc/free 顺序，两块在 seq217 时都尚未观测到 free，且均属于同一个已登记父对象（A2）。这不是无日志丢失证明，也不是未发生 compaction 的证明；free 行只保证进入原释放前已有观测，不能单凭它宣称原 free 返回成功（resource-v3-target.inc **75–82**；libObj `1036e8–1036fc`）。

### 分配者与 bitmap 类型

原 `103550` 的直接入口是 wrapper `102560`，在 `1025a8` 尾调用它；释放 wrapper `1025c4/102618` 在 `102600/102654` 尾调用 `10364c`。全原 `.text` 直接 xref 在 proof，**未发现把 `103550` 直接作为 bitmap 构造函数的依据**（A1）。

| 链段 | 原行为 / 原 VA |
|---|---|
| 公共 bitmap 创建 | `GRM_bitmapCreate fb1e8 → fb280/BMP_Create ee638`；ee638 分配 `0xb8` 对象，`ee6e0` 调构造器 `f12b4`，`ee704` 调 `f13a8 create(MemorySpace,...)`。另 `ee76c → ee83c` 为带额外对齐选项的同类入口 |
| 类型确认 | RTTI 字符串 `1dedd8=N3grm3bmp10BitmapImplE`；RTTI `252648`；vtable address point `252670`。构造器 `f12fc–f130c` 经 GOT `261c50→252660` 写 `+0x10` 后的 vptr；不是 BitmapComposite |
| 实际像素 malloc 调用者 | `BitmapImpl::create` 在 `f142c/f1448` 计算行/列对齐，`f1490–f14a0` 用 stride×allocatedHeight×bpp 算字节数；`f14f0` 输出地址指向 `bitmap+0x10`，`f14f8` parent=MemorySpace，**`f14fc → 102560 → 103550`** |
| malloc 返回和 physical | `1035dc–1035e8` 将 MA 返回 physical 经 `102bd0` 换为 logical 并写 out；`f1570–f157c` 经 `102718` 将 logical 换回 physical 保存到 bitmap 元数据 `+0x28`，`f15a4–f15b0` 清零本次已分配像素区 |
| 上层资源 Arena | `150f8c–150fa0` 从 Arena `+0x60` 取 MemorySpace 并调 `ee76c`，因此资源管理器也创建同类 bitmap；`ffb3c→102560` 另是分配整个 arena backing 的调用点，不能把所有 `103550` 命中都认成独立 bitmap |
| 释放 | bitmap 引用计数 `f0c80–f0cb4` 增加、`f1928–f19a4` 归零后 `f1984→f17d0 destroy(1)`；非外接物理模式 `f1918–f191c→1025c4→10364c` 归还像素子块 |

以上是 **A1 确认的具体调用者和类型链**。本轮两次 malloc 没有 LR/栈记录，也未保存两个对象的 vptr/metadata；因此“这两次确由 f14fc 发起且对象必为 BitmapImpl”仍是 **B 级拟合，未达到 A2 一对一绑定**。尺寸吻合：32×align2(29)×2=`0x780`，align16(116)×116×2=`0x7400`（A1 `f13f0–f144c、f1490–f14a0`；A2 serial **37065、37071**）。不以尺寸相同替代对象身份。

### 原绘制命令为什么可用离屏目标

`GRM_gpermFillrect 1017ac` 从目标 bitmap 取矩形、stride 和格式，构造 `CmdFillrect`；命令构造器 `100b88–100ba0` 保存 bitmap 到 `command+0x78`、加引用并持 write lock，执行时 `100c80–100cc4` 再从该 bitmap 获取 physical 并调原 GpermFillRect。析构 `100ad4–100b04` 才 write-unlock/release。**这里没有限定必须是 screen bitmap**（A1；serial **37066** 对应 CmdFillrect 指针 `0x7f50835bf0`，字段中的 bitmap=`0x7f50835970`）。

`CmdRectDraw` 则在 `100f98` 保存 source/destination bitmap 到 `+0x40/+0x48`，`100fe4–101034` 给两者加引用并分别 read-lock/write-lock；执行 `101108–101174` 在锁持有期重新取两边 physical、调 GpermBitBlit；析构 `100ebc–100f10` 解锁后释放。与上述 MemorySpace bitmap 分配链、实际 Heap2 目标命令合起来，足以确认**父资源池里的离屏子块绘制属于原厂合法路径**（A1/A2）。

须避免两处过度解释：`bitmap_read=1` 只是 timer observer 成功读了 `command+0x78` 的 **8B指针字段**，没有读完整 bitmap（observer v3 **42–43**）；`FX3_UI_FILL_RETURN result=0` 也不是绘制成功，因为 `100cc4` 后原命令没有把 Gperm 的错误码作为最终返回值，实际 GPE result5 仍见 serial **37068、37070**（A1/A2）。

## 2. seq217 全144B与原分派

完整原 hex 在 proof.commands，逐字段包括所有 reserved 字节，不采用 marker 的 `w=29 h=29` 作为目标尺寸。该 marker 显示的是源矩形尺寸（A2 serial **37073–37074**；后端字段消费者 A1 `cfa4–cfac、ce9c–ceb8`）。

| 偏移 / 类型 | 实值 | 原消费/说明 |
|---|---|---|
| 00 u64 | dst=`0x410936c80` | `c920–c92c` |
| 08/0c u32×2 | dst x/y=`0,0` | `ce8c–ceb0` |
| 10/14 u32×2 | **dst w/h=`116,116`** | `cfa4、ce9c` |
| 18/1c u32×2 | clip x/y=`0,0` | `c984–c994` |
| 20/24 u32×2 | clip w/h=`116,116` | `c998–c9c0`：inclusive 右下界=`115,115` |
| 28/2c u32×2 | dst adjust=`0,0` | `ce94–ceb0` |
| 30/34 u32×2 | dst stride=`128` pixels / fmt=`0` | `c930–c980`：reg21=`0x00800014` |
| 38 u64 | src=`0x4109364c0` | `c9e4–ca10`：reg462 低32位=`0x109364c0` |
| 40/44 u32×2 | src x/y=`0,0` | `ce70–ce80` |
| 48/4c u32×2 | **src w/h=`29,29`** | `cfa8、cea4` |
| 50/54 u32×2 | src adjust=`0,0` | 原路径坐标项，当前均零；不扩大其通用语义 |
| 58/5c u32×2 | src stride=`32` pixels / fmt=`0` | `ca14–ca50`：reg463=`32`、reg464=`0x14` |
| 60/64 float32×2 | bits=`0,0`，即 `0.0,0.0` | **P74=0 下不用它作倍率**，`ce98–cedc` 从尺寸得 `4.0,4.0` |
| 68 u32 | rotation=`0` | `cf8c–cfa0、ce98–cedc` |
| 6c..6f u8×4 | `00 00 00 00` | 写 reg741=0；color-op=0，不是“黑色 tint”依据，`cadc–caf0` |
| 70 u8 | selector=`0` | `cb08–cb10→cd98` |
| 71 u8 | conversion=`0` | srcfmt0，`ca7c–ca94` 跳过 fmt3 conversion |
| 72 u8 | K=`255` | `cd98–cda0→ce20`，reg760=`0` |
| 73 u8 | `0` | `ca54–ca68`，reg467=`0`；硬件采样意义 U |
| 74 u8 | `0` | `d0b4–d0b8` 进入缩放；`ce58–cedc` 使用尺寸倍率 |
| 75 u8 | color-op=`0` | `cac4–cad8`，reg740=0 |
| 76 u8 | `0` | `ca98–caac`，reg730=0 |
| 77/78 u8×2 | H/V=`0,0` | `ccfc–cd14` 原 cslChangeHVFlip 收到0/0 |
| 79 u8 | async=`0` | `cd28–cd4c、cee0–cf10` 要求同步完成 |
| 7a..7f bytes6 | 全0 | 未见消费，保持原 bytes |
| 80/88 u64×2 | callback / argument=`0,0` | `cf00–cf10` 完成账本 |

原分派顺序（A1，proof 原指令重放）：

1. `cf48` 检查 selector2 错误；本次 selector0 通过。
2. `cf8c` 检查 rotation=0；`cfa4–cfb0` 比较 **116/116 与29/29**，不等即走 `d0b4`，**尚未执行 flags 测试**。
3. `d0b4` 读 P74=0，`d0b8` 直接到 `d104`，`d124` 调原 StretchRotateBlit `c878`。
4. `ce98–cedc` 算 `116/29`，原 `ce50 cslMakeZoomSprite` 接收 `s0=s1=4.0f`；源矩形坐标保留0/0，目标0/0，原 H/V=0/0。
5. `cd98–ce30` 在 selector0/K255 下写 **reg760=0**，不配置 source-over 因子；`af30` 提交前审计截停。

因此该命令的窄语义是**同fmt0、无旋转/颜色运算/alpha混合的缩放替换**。同格式仅代表不需要格式转换，不代表尺寸相同。脚本另将目标宽高单独改为29/29做人工反事实，原分派进入 **`b578`**；`b234` 是另一组混合条件的快路径，不能把它称为本次无条件 memcpy 分支（A1 `cfd0–d094`；proof.same_size_counterfactual，明确不是捕获命令）。

`reg467=0` 对应的精确 filter、像素中心、边缘采样与硬件精度仍 U；本轮没有芯片 oracle。可沿用 PLAN 已批准 `nearest_v1` 作**显式视觉近似**，令 `sx=floor(x*29/116)=floor(x/4)`、`sy=floor(y/4)`，逐 pixel **原16bit值替换**。不得先做 straight-over、不得把零 color tint 到源色、不得声称 nearest 是已证实 Sony filter（A1 `ca54–ca68、ce50、cd98–ce30`；M 宿主向量）。

## 3. 为什么当前实现拒绝；span 与生命周期守卫

**FillRect reason4**：规划本身可支持 fmt0/selector0/K255，但 v18 的非 screen 目标必须同时 `native_open`、`type403`、已知 class vptr。Heap2 通过 malloc_parent 登记且 type0，故 `v18.c:184` 在目标资源门返回 GPE_STALE=4，先于映射/像素写（A2 serial **37068**；源码 evidence 已固定 SHA）。这不是 FillRect 的格式或大小错误。

**BitBlit reason2**：v16r2 后端沿用到 v18 的 `backend-v3.c:102–103` 将 P73=0 送入 legacy planner；**第80行**拒绝不同源/目标尺寸，返回 GPE_UNSUPPORTED=2，尚未到目标资源门。现有 AP90 缩放分支要求 selector1/P73=1，只支持该近似混合子集，未覆盖 selector0/flags0 这条真实原路径（A2 serial **37073–37074**；A1原路由 `cfac/d0b4`；fixed source evidence）。

完整 span 必须按各自 stride/bpp 和最后一行校验，不能用 `w*h*2` 连续长度替代（A1 libgpe `ca14–ca20、ce98–cedc`，libObj `102b98/102bd0`；A2 本次参数）：

| 操作 | 逐行跨度 | 包络，尾端不含 | 边界结论 |
|---|---|---|---|
| seq216 Fill 32×29 | step64 / line64 / rows29 | `[4109364c0,410936c00)`，`0x740` | 落在 child `[4109364c0,410936c40)` 的 `0x780` 内；剩64B不写 |
| seq217 source 29×29 | step64 / line58 / rows29 | `[4109364c0,410936bfa)`，`0x73a` | 每行3个padding像素不采样；实际读取1682B |
| seq217 dst116×116 | step256 / line232 / rows116 | `[410936c80,41093e068)`，`0x73e8` | 落在 child `[410936c80,41093e080)` 的 `0x7400` 内；每行12像素padding不写 |

两边物理包络不相交，即使 **same parent** 也无需按 overlap 拒绝。反过来，same parent 不代表允许物理重叠；原后端 overlap 规则应保留，未知重叠方向继续零写拒绝（M；本次 A2 地址与 A1 地址/尺寸消费式）。所有计算使用完整64位和溢出检查；不能把 libgpe 硬件描述符中的低32位用于 CPU mmap（A1 `c920/ca10` 的低32bit原硬件写法；原参数 A2）。

### 对“父 extent + bitmap存在”准入条件的回答

在 Lead 已批准的**区间级**模型里，唯一匹配、仍为state10、原对象身份字段/本地epoch一致的父 extent，加完整逐行 span、权限、已有 bitmap 命令来源与生命周期锁，可以把承诺限定为“本次物理读写在已登记父分配内”。**不能从这里推导 child 未释放、bitmap 仍指向该子块、排队参数未过期**（A1 `103454–10351c、10364c–1036fc、f0a98–f0abc`；A2父登记自身明确 `subblock_lifetime_unproven=1 queued_ABA_uncovered=1`）。一个存在的无关 bitmap 并不能授权另一个子块。

若 v19 要声称“写入的是对应活跃 bitmap 子块”，至少增加下列真实守卫；它们是 **M，当前实现未提供完整保证**：

- **实际 child 账本**：成功 `103550` 返回时绑定 `(parent_object,parent_epoch,logical,physical,requested_bytes,align,child_epoch)`；free `10364c` **入口前撤销 child**，close `103454` 撤销父和所有child，失败路径保守失效而非复活。仅检查父+24总分配数或记录 free 日志不足；相同计数/地址仍可发生ABA（A1 `1035dc–1035f4、1036f4–1036fc`；当前 inc **79** 明示 child_epoch_untracked）。
- **对应 bitmap 身份和原命令锁**：匹配 bitmap 的class/vptr、metadata、物理基址、stride/format/allocated尺寸与该child；引用必须从原 CmdFillrect/CmdRectDraw 加引用/锁处持续到GPE执行与完成。完整对象存在性、魔数或全局读锁计数都不能证明**该命令**持有锁；当前 A2 `37066` 只有指针字段，seq217 没有两个指针（A1 `100b88–100ba0、100fe4–101034、100ab4–100b04、100e9c–100f10`）。不要从GPE线程再次获取同一bitmap写锁而自锁。
- **排队身份**：沿已有 Gperm sequence/FIFO 绑定命令到 parent/child/bitmap epoch；出队前校验；无sidecar就保留 `queued_ABA_uncovered=1`。原 Cmd 持有引用/锁强烈支持标准路径存活，但不能据此宣称全部原始GPE调用都经过这两个类（A1 `101944/101524` 入原命令队列，`100cc4/101174` 调原Gperm）。
- **与释放/移动串行**：绘制前校验、内存IO和后验处于同一生命周期租约；新绘制在retiring后拒绝。malloc/free/close遵循同一锁顺序，避免持外部lifecycle锁等待原函数、而原函数又等待当前GPE完成的死锁；原callback/同步完成在释放软件租约后按原顺序交付（A1命令持锁链及 libgpe `af08、a110、a158`；当前模型仅保证已拦截事件的区间锁）。

### Compaction 不是“free账本顺便覆盖了”

新增静态证据闭合了独立移动链：

`ArenaImpl::compaction 150b9c → 150c04/102814 → 102844/103a40`；`103a40` 经 `103760`(MA消息11)、`103804`(消息12)、`1039a8`(fin) 执行。`BMP_AssocMemorySpaceForCompaction ef1ac` 在 `ef1e8–ef1f8` 装入回调并经 `10285c→103184` 保存；原 relative reloc 指定 begin=`ef638`、finish=`eff44`、replace=`efd0c`、对象查询=`efde8`（A1，proof.bitmap_impl_type.relative_relocations）。

replace 回调 `efd7c–efd90` 调 bitmap vslot `+0xd8`；BitmapImpl vtable `252748→f0a98`，后者 **`f0aa8` 改 bitmap logical 指针并在 `f0abc` 改 metadata physical**。这条移动路径不要求经过 `103550/10364c`，所以 malloc/free hooks 和父extent不变、总计数不变都不能排除子块已移动（A1）。

完整子块模型应在 compaction 起点阻止新租约，等现存租约结束，在 replace 成功后撤销旧child epoch、重绑新 logical/physical，再恢复；无法核实全过程就让该父的强子块准入失效。**本轮没有拦截、禁用或运行compaction，也没有证实AP93未发生compaction**；v19若仅延续区间政策应继续输出 `compaction_uncovered=1`（M；A1移动路径；当前注册 marker serial **2218**）。

## 4. v19 最小实施规格（给 Lead，未实现）

| 部位 | 最小改动 | 不可省略的验收点 |
|---|---|---|
| adapter 目标准入 | 在现有screen/native403路径外，新增**明确的资源离屏目标**：通过原malloc-parent登记、parent identity/epoch/state/class重验、逐行span完整在唯一父extent内；不要求伪造type403/native_open | 捕获的Heap2两块可分别作为目标。保留 `scope=allocation_interval` 和未覆盖标志；若启用child活跃保证必须按上节实际实施。来源serial16838/37065/37071，libObj103550 |
| source/dst同父 | 复用同一个父映射、同一个后端extent ref，分别验证src读span与dst写span；避免将重叠的“父extent+src child extent”重复注册到禁止重叠的gpe_register | 本次两个包络相离；same parent本身不拒绝。不能因父RW映射而给源/所有padding通用写权限（本次span表；backend-v3 gpe_register/raster） |
| FillRect | 复用现有精确fmt0高4bit pack、selector0/K255覆写，只扩充合法目标resolver | seq216写1856B `ff ff`，child尾64B不变；无近似blend（libgpe c400–c428；serial37069） |
| flags0缩放规划 | 在P73=0送入legacy前，识别 **fmt0→0、P70=0/P71=0/K255、P73..78全0、rotation0、同完整clip、坐标/adjust为本次已证子集**。初版可只开放等比整数4×；保留旧同尺寸/AP90分支 | seq217必须plan成功，源29×29/stride32、目标116×116/stride128，不伪改输入尺寸、P73或selector。未知变换/部分clip继续拒绝（cfac/d0b4/ce98） |
| raster | 复用已有nearest坐标采样循环，**`approx_stretch=1`、`approx_blend=0`、`approx_fmt2=0`**；直接写源fmt0原16bit值 | 透明源带非零RGB仍原值替换，零color不tint。不得复用AP90无条件`p->approx_blend=1`（reg760=0，cd98–ce30；现后端121/184行） |
| 提交与OSD分离 | 继续原GetInstance/Main/FIFO、callback→同步status一次完成；保持失败批次策略。离屏资源绘制resolver与frame_target导出resolver各守自身身份合同 | **不因资源写入成功把Heap2登记成screen/OSD**；不修改v18 frame_target_tuple的native403/token门。seq216/217自身均sync、无callback（serial37069/37074；libgpecee0–cf10） |
| 可复核marker | 保留全56/144B、原sequence/参数，另记dst/source parent object/uhdl/epoch、child匹配状态、各span、same_parent、`raster_mode=replace`、`approx_stretch=nearest_v1` | 当前P73=0缩放不会被旧approx-blend marker自动覆盖，需显式记录近似采样；**不谎报bitmap_pin/child epoch/compaction保护已实现**（serial2218/16838；当前inc79/106） |

如果只落实父区间扩展，按已批准模型可以继续做有界视觉实验，但最终回执必须明确“父区间写入准入”，不能变成全内存安全证明。若 Lead 选择强子块准入，则上节child/bitmap/compaction/排队身份属于尚待实现的条件；本审计没有把这些条件假定为已满足（A1/A2边界见第3节）。

### 宿主向量与预计读回

proof.host_vectors 含 **12项**：2个完整29→116像素模型向量（共26912个逐像素比较、每例2784B目标padding哨兵、源不变），10个拟议身份/边界准入向量。它们随脚本实际运行，**验证的是人工 nearest/replacement 期望与模型反例，不是新C后端、sanitizer或guest验证**（M）。

- **真实参数全白链**：人工src child为`0x780`，先模拟seq216只填32×29白；seq217应把src前29×29扩成dst116×116白，每行目标后12像素不变，源末行/分配尾/相邻子块不变。实际AP93-r5的Fill被拒，所以不能把这个预计白块说成该次已观测像素（serial37068–37074）。
- **非均匀/透明色链**：每个src LE16=`((x*37+y*53)^0xa530)&0xffff`，每格精确重复4×4；corner值与完整源/目标SHA在proof。包含alpha0且RGB非0，区别替换与source-over；src行末3像素/child尾哨兵不得进入dst（A1 reg760=0；M）。
- **边界反例**：last-row end恰为child末端可准入，越1B但仍在父区间内必须被强child模型拒绝；负坐标/溢出/stride不足/零高宽/源目标物理包络重叠/跨父extent，实际C实现仍须补零写测试。不能用本Python向量宣称这些C分支已经执行（M；原地址消费与上节span）。
- **生命周期反例**：父活着但child已free、存在无关bitmap、未持命令锁、同physical新epoch、compaction开始/移动中、free/close与写并发、排队参数ABA；强模型拒绝，弱区间模型保留未覆盖标签。需实测原函数仅调用一次、errno/返回值不变、释放前失效且无锁顺序死锁（A1 `103454/103550/10364c`、独立compaction链；M）。
- **回归矩阵**：73条AP89原参数、screen与native403目标、不同父/同父相离、旧同尺寸selector0复制、selector1/P73=1混合和fmt2文字保持既有行为；新4×/flags0不能扩大到rotation、unknown flags、fmt2目标或fmt1未经审计组合。后端通过后再由Lead独占运行链做原物理读回、原完成消费及下一页交互验收（M；原分派表 `cf2c–d144`）。

## 5. 完成范围和未证实项

本次完成：两份原参数逐字节解码、两个子块及父身份/分配释放顺序、BitmapImpl具体分配与Cmd生命周期静态链、独立compaction移动链、seq217原指令分派/4×/blend-off证明、当前拒绝代码定位，以及v19最小规格与可复算宿主向量（A1/A2；proof和本报告引用）。

仍未完成：**本次malloc的调用栈与两份运行时完整bitmap身份、seq217两对象/锁的运行绑定、完整compaction/排队ABA防护、Sony采样像素oracle、v19实现及后端sanitizer、guest读回与后续UI循环**。静态可达性、Python模型和UI_FILL_RETURN=0都不能替代这些验收（A1 `f14fc、f0a98、100cc4/101174`；A2 serial37066/37068/37070/37074）。仅写本目录三份文件；未启动QEMU、未改runtime/STATE/原件、未拿.run.lock、未操作设备。
