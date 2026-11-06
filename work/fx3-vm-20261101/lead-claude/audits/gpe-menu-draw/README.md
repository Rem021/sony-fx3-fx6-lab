# FX3 AP 菜单 GPE 绘制静态规格

2026-11-01。已恢复 AP 队列封装、矩形/位图参数、寄存器写描述符、完成路径和资源位置；未实现后端，未运行 VM/相机，也未证明菜单实际发出哪一种 BitBlit。所有 VA 均为对应 ELF 的链接 VA（运行地址 = 库加载基址 + VA），小端 AArch64。只读原件，输出仅本目录。

## 复现与证据

在 Mac 项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/gpe-menu-draw/audit_gpe_menu.py
```

退出 0，重建 `gpe-menu-draw-proof.json`。脚本依赖该既有 venv 的 capstone/pyelftools 和系统 c++filt，无网络、无固件修改、无 QEMU。JSON 含源 SHA256、完整导出函数清单（含 mangled/demangled 名称、VA、长度）、逐指令原字节、私有范围、资源头/哈希及校验锚点。它是静态提取与有限锚点校验，不是软件后端正确性测试。

AP 原件根为 `menu-repair-01/original-uipc/ap-projection/regular-files/`，以下资源路径相对 guest 根；库位于 `/usr/lib/`。工具用法参考 [Capstone 官方 Python 文档](https://www.capstone-engine.org/lang_python)（本次查阅；仅用于反汇编 API，不能证明 Sony 协议）。固件语义全部来自本地代码。

## API 与菜单调用链

只找到一份 `libgpe.so`。完整对外已定义 STT_FUNC API 列表在 JSON `libraries.libgpe.so.exports`（不能把 undefined imports 算成导出）。按调用层次：

| 层 | API / VA | 用途 |
|---|---|---|
| 菜单图形适配 libObj | `GRM_gpermFillrect` 0x1017ac；`GRM_gpermRectblit` 0x101970 | 从 bitmap/subrectangle 构造 GPE 参数；Rectblit 在 0x10197c 分配 0x90B 参数，0x1019cc/0x1019e8 写 stride，0x101b94 起写 flags |
| 入队 libgpe | `GpermFillRect` 0xa430；`GpermBitBlit` 0xa514；`GpermStretchRotateBlit` 0xa5f0；`GpermDrawVariousFrames` 0xa6cc；`GpermFlush` 0xa768；`GpermFinish` 0xa83c | 拷贝参数、分配序号、同步等待或异步提交 |
| 工作线程 | `Gperm::Main` 0x9ba4；`InitializeDraw` 0xc1d0；`ResumeDraw` 0xc28c；`TerminateDraw` 0xc304 | 原 FIFO 解包并调具体绘制；Main 保留锁和错误通知 |
| 工作实现 | `FillRect` 0xc30c；`BitBlit` 0xcf2c；`StretchRotateBlit` 0xc878；`DrawVariousFrames` 0xd148；`Flush` 0xc760；`DoCallback` 0xc800 | 硬件描述符生成；BitBlit 按参数选快路径、转换路径或缩放旋转 |
| 消息 | `SendDraw` 0xd814；`ReceiveDraw` 0xd84c；`SendDrawComp` 0xd888；`ReceiveDrawComp` 0xd89c；`SendWaitIntr` 0xd8b4；`ReceiveWaitIntr` 0xd8ec | 原生 OSAL 队列消息 |
| 完成/队列 | `CMF::SetCallback` 0x9f64、`DoCallback` 0xa158、`SyncCallback` 0xa110；`CommandBuffer` / `CallbackFifo` / `RingBuffer` | 生命周期、顺序与回调，不是像素操作 |
| 低层 | cgl*、csl*、Intr*、GpeInit/GpeSus/GpeRes | 寄存器/FIFO/图元描述符；所有名字/VA 见 JSON 完整清单 |

`libObj` 导入 `GpermFillRect/BitBlit/Finish`，这证明菜单图形适配存在路径，尚不是 AP66 菜单运行时命中证明。`Gperm::Main` 无文字/glyph/CLUT 独立 opcode。文字先由 AP 文本层栅格化再进入 bitmap 路径是实现方向推断；glyph→具体 GPE 调用链尚未闭合，不应自行增加文字 opcode。

## 队列二进制格式

所有绘制消息头 16B：`u32 opcode @0, u32 sequence @4, u32 completion_source @8, reserved32 @12`；参数自 +0x10 开始。来源：0xa4cc、0xa5ac–0xa5c4、0xa688–0xa6a0、0xa724–0xa738、0xa800–0xa818；Main 0x9c24/0x9c28 解包。completion_source 在同步模式是原生等待者/消息目标 ID，不是图像/DMM 句柄。

| opcode | 内容 | 参数/消息字节 | 原构造 / 分发 |
|---|---|---|---|
| 0 | FillRect | 0x38 / 0x48 | 0xa430 / 0x9c20 |
| 1 | BitBlit | 0x90 / 0xa0 | 0xa514 / 0x9c54 |
| 2 | StretchRotateBlit | 0x90 / 0xa0 | 0xa5f0 / 0x9c74 |
| 3 | DrawVariousFrames | 0xf0 / 0x100 | 0xa6cc / 0x9c88；内部格式未充分恢复 |
| 4 | Flush | 0x18 / 0x28 | 0xa768 / 0x9ca8 |
| 5 | DoCallback | 特殊：+4 是次数 | 0x9cc8；不是上述普通参数 |

Main 跳表 `0x14e70 = 00 0d 15 1a 22 2a`，分支基址 0x9c20。SendDraw 将 gpe0/1 发向 `0x80820884/0x80820885`（0xd83c/0xd824），非 CP/VDF 菜单命令。私有 0xd6b0 分配 OSAL 消息、设置目标、复制 payload、send，失败释放；返回 bool 成功，不是绘制 status。

### FillRectParam：56B

| 偏移 | 类型 | 含义 / 证据 |
|---|---|---|
| 0x00 | u64 | 目标物理基址；0xc61c 读取，硬件路径取低32位加偏移 |
| 0x08/0x0c | u32 ×2 | x/y；0xc60c–0xc618 |
| 0x10/0x14 | u32 ×2 | width/height；0xc634，编码成 w−1/h−1 |
| 0x18 | u32 | stride，单位像素；0xc610/0xc664 |
| 0x1c | u32 | format；0xc384、0xb1f4 |
| 0x20..23 | u8 ×4 | 顺序颜色分量；format0 用每分量高4bit，0xc400–0xc428；format1 整字 rev，0xc390–0xc39c |
| 0x24 | u8 | blend selector，原件分支0/1/2；0xc3a4、0xc458、0xc520、0xc590 |
| 0x25 | u8 | constant alpha，0..255；255 与 selector0 进入 overwrite；0xc458 |
| 0x26 | u8 | async/no-wait flag；0xa474、0xc69c |
| 0x27 | byte | padding，尚无消费证据 |
| 0x28 | u64 | callback function，0xc6a8/0xaf14 |
| 0x30 | u64 | callback argument，0xaf14 |

格式0的16位颜色精确打包：`(c0>>4)<<12 | (c1>>4)<<8 | (c2>>4)<<4 | c3>>4`。常称 RGBA4444，但分量语义仍需上层颜色定义独立核对；格式1的32位值是 `bswap32(load_le32(c0..c3))`。不同分量顺序不能沿用 uniform 全黑结果猜测。

### BitBlitParam：144B

下列名字以代码用途命名；未知字段用偏移保留，不用猜测填默认值。

| 偏移 | 类型 | 用途 / 证据 |
|---|---|---|
| 0x00 | u64 | 目标物理基址，0xb3b4/0xbc24 |
| 0x08/0x0c | u32 ×2 | 目标坐标项，0xb3a0/0xb380 |
| 0x10/0x14 | u32 ×2 | 目标宽高项；0xb3ec，缩放路径0xce98使用 |
| 0x18/1c/20/24 | u32 ×4 | clipping rectangle x/y/w/h，0xbc88–0xbcc4（右下界为 x+w−1,y+h−1） |
| 0x28/0x2c | u32 ×2 | clipping/位移项，0xb37c；准确上层坐标命名未证实 |
| 0x30/0x34 | u32 ×2 | 目标 stride（像素）/format，0xbc34–0xbc84 |
| 0x38 | u64 | 源物理基址，0xb364/0xbcf0 |
| 0x40/0x44 | u32 ×2 | 源 x/y，0xb354–0xb360 |
| 0x48/0x4c | u32 ×2 | 源/本次矩形 w/h，0xb3cc；快路径用此 w/h |
| 0x50/0x54 | u32 ×2 | 坐标校正项，0xb388/0xb398 |
| 0x58/0x5c | u32 ×2 | 源 stride（像素）/format，0xb358、0xbd18/0xbd28 |
| 0x60/0x64 | float32 ×2 | scale 比率，0xd0bc–0xd100；确切变换方向待验证 |
| 0x68 | u32 | rotation/变换选择项；非零转 StretchRotateBlit，0xcf9c/0xd104 |
| 0x6c..0x6f | u8 ×4 | 颜色参数，由 libObj 0x101b9c–0x101bb8 填入；准确混合语义未闭合 |
| 0x70 | u8 | blend selector；值2被 BitBlit 拒绝，0xcf48–0xcf88 |
| 0x71 | u8 | 色彩转换模式，0xb708、0xbd84 调0xaf98；不能认作palette索引 |
| 0x72 | u8 | alpha，0xb2d0/0xb514 |
| 0x73..0x78 | u8 ×6 | 变换/混合 flags，0xcfb4–0xcfcc 及0xbd94；完整语义未证实 |
| 0x79 | u8 | async/no-wait，0xa558/0xb440 |
| 0x7a..0x7f | bytes | padding/未证实 |
| 0x80/0x88 | u64 ×2 | callback/argument，0xb480、0xaf14 |

同尺寸、无特殊 flag 等条件下进入私有0xb234；纯格式转换进入0xb578；通用图元进入0xbbcc；旋转/缩放回退0xc878（分派见0xcf8c–0xd144）。不能把所有 BitBlit 都套 memcpy。

快路径原地址公式（0xb354–0xb3c8），用 `Pxx` 表示参数偏移xx处u32，`B(fmt,n)` 为字节换算：

```
src = u64@38 + B(P5c, P44*P58 + P40)
dst = u64@00 + B(P34, (P0c+P2c-P54)*P30 + P08+P28-P50)
width = P48; height = P4c
```

必须先按有符号坐标/clip做范围验证，再用宽整型算地址，不照搬32位溢出。此公式限定私有0xb234分支，不能用于任意缩放旋转。

### 像素格式与低层二进制描述符

`B` 来自0xb1f4与表0x151f8：format0→2B，1→4B，2→1B，3→2B，4→4B（其他值原实现也落2B，但软件后端应拒绝未知）。硬件格式码分别0x14、0、0x21、0x1a、3。0/1颜色写法已见上；2/3/4的通道意义、YUV布局与是否索引尚未证明。

0xadac 是单个 register-set sprite 构造器，调用 `cslMakeRegSetSprite` 0x14778。每条临时槽64B，**不是**64B有效命令：n=1的有效内容 `u16 0xe000; u16 reg; u16 value_low; u16 value_high; u16 0`，余槽先由 cslClearSat 清零。通用 n≤4：头 `0xe000|((n-1)&3)`，各entry写寄存器16位及值32位，中间对齐16位；不要用64B槽布局冒充最终FIFO线格式。0xaf30 调 `cslSendSpriteTableMC`，再 `CMF::Set`；传输/宏命令细节保留于JSON原指令，软件入口拦截无需实现这些硬件FIFO。

| reg | 已观察用途 / 代码 |
|---|---|
| 0xb07 | 填充颜色，0xc398 |
| 0xb01..0xb06 | 混合控制/系数/constant alpha，0xc464–0xc5dc、0xb2d0–0xb330 |
| 0xb10 | 格式/操作配置，0xc5fc、0xb344、0xb63c |
| 0xb11 / 0xb12 | 源 / 目标低32位地址，0xb374/0xb3c4；Fill仅0xb12 |
| 0xb13 | `(h-1)<<16 | (w-1)`，0xc634/0xb3cc |
| 0xb14 | 源/目标行末增量项，0xb3ec–0xb414 |
| 0xb00 | 启动1，0xc674/0xb418 |
| 0x80a | 同步屏障值0x80000000，0xc688 |
| 0 | 完成请求标记0或1，0xc69c–0xc6bc |

`0xaf98` 随mode1..4选择0x15228/0x15260/0x15298固定系数表，写reg0x900再7个寄存器；这是转换配置证据。没有找到由菜单传入palette地址、palette长度或动态CLUT装载的闭合路径。不能把format3或conversion mode称为已确认CLUT。

## 菜单字体与图像原件

只识别目录/头部/表目录，没有解码全部字形或图像。JSON `resources` 给出大小、SHA256和前64B，可逐项复核；它不是资源导出包。

| guest 原位置 | 格式识别与使用证据 |
|---|---|
| `/usr/share/app/fontlist.dat` | 文本映射 FONT_UNIVERS/JAPANESE/KOREAN/S_CHINESE/T_CHINESE/ICONS 到下列路径；JSON保存完整360B内容 |
| `/usr/share/app/UniversOTS-SJ_wIcon.ltt` | 611416B，`LTT\n7\n2\n`头与Monotype Font-linking copyright；LTT字体链接容器，内部glyph编码未定 |
| `/usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt` | 851496B，同LTT头 |
| `/usr/share/app/MYingHeiC-KSX1001-SJ_wIcon.ltt` | 924104B，同LTT头 |
| `/tmp/images/MYingHeiC-GB18030-SJ_wIcon.ltt`、`MYingHeiC-Big5-SJ_wIcon.ltt` | fontlist指向的简/繁中文字库；脚本仅在原投影实际存在时记录头/哈希，映射存在不等于文件在该投影已齐全 |
| `/usr/share/app/Sony_DI_Icons.ttf` | 624596B，sfnt TrueType 0x00010000；含cmap/glyf/loca/head/hhea/hmtx/maxp等12表，非位图文件；`/tmp/images/`另有同名字体候选副本 |
| `/usr/share/app/image.uxb` | 2281172B，头`75 78 62 07`（uxb+07），UX资源容器/索引候选，索引语义未全解 |
| `/usr/share/app/image_00_32.uxc`、`image_00_43.uxc`及其他image_*.uxc | 样本26839932/27607512B，头`75 78 64 07`（注意扩展名uxc，实际magic为uxd）；尺寸/压缩/像素编码未证明，不能按PNG/BMP读取 |
| `/usr/share/app/style.uxb`、`color.uxb`、`lang.uxb` | uxb头；布局/颜色/语言资源候选，不能据文件名断定字段 |
| `/usr/share/app/string_english.uxc` | 165740B，`75 78 63 07`头；与图像uxc的magic不同；本次未解字符串表 |

文本入口 `libObj TextRM_loadFont` 0x5b284 与 `ux::core::TextLayout::registerFontFaceFile` 0x15e920 在JSON保存指令；后者0x15e950/0x15e954将字体路径和属性传虚函数槽0x10。字体资源路径到具体文字绘制命令的完整xref仍未闭合，不能用“文件存在”代替菜单文字已栅格化。

FlushParam的24B字段为`u8 async@0, padding@1..7, u64 callback@8,u64 argument@16`（0xc760–0xc76c、0xc7b8）；其消息不带像素输入。DrawFramesParam虽已确认240B拷贝长度，内部逐字段未闭合，应保持unsupported。

## DMM 地址与完成语义

GPE 入口参数保存的是物理地址，硬件生成时只取低32位（如0xc61c–0xc628）；v12 CPU映射使用完整64位。对本机 >4GiB DMM，不能直接把硬件低32位地址 mmap，也不能假设统一 OR 一个高位。

DMM句柄→地址应由原分配/映射层和当前extent表提供：`libObj::GetDmmMemInfo` 0x101d84 构造24B输入，将首参数写入+8，调用0x102394创建对象（malloc0x118），0x102560执行映射，0x102718转换。它不是无副作用的句柄查询，不能每次绘制调用来做lookup。输出结构 `+0 u64物理, +8 u64逻辑, +16 u32大小`（0x101e0c–0x101e20）。原地址转换内核0x102b98明确是区间检查后 `physical_base + (logical-logical_base)`；反向0x102bd0为 `logical_base + (physical-physical_base)`，对象子结构+0x10/+0x18/+0x20存两基址和长度。获取句柄的实际分配生命周期、映射pin/unpin仍须独立实现/验证。

后端应以活跃extent为准解析 `(handle, generation, parent_base, offset, bytes)`，校验每行源/目标span均在各自extent且在完成前仍活跃。v12仅实证 handle545、base0x43feb5000、size0x140000及payload起0x43feb5100，不能推成全体DMM公式。

`async=0`：Gperm包装器私有0xa398取等待目标，消息+8保存它；0xa3d4等待。成功绘制后，CMF::SyncCallback 0xa110发送 **4B status=0** 至该目标；失败时 Main 0x9c34–0x9c4c对同步请求发送实际非零status。`async!=0 && callback==NULL` 原路径省略callback和同步回复。callback非空时，0xaf08入CallbackInfo `{u32 sequence,u32 completion_source,u64 function,u64 argument}`（24B）；0xa158弹出后调用function，传16B `{u32 sequence,u32 zero,u64 argument}`，之后必要时同步回复。必须保持调用顺序、单次交付及内存可见性。

任务所称 `nativeSendDrawComp` 未在 libgpe/libObj/appFw 的已定义 dynsym 中定位；可确认的原接口是 `_ZN5mpgpe7message12SendDrawCompEjPKvm` @0xd888，参数 `(u32 destination,const void*,size_t)`，返回发送成功bool。发送完成不等于LCD已显示，也不是VDF/CP ACK。

## 软件后端优先级与 v12 衔接

| 优先级 | 实现规格 | 可执行验收边界 |
|---|---|---|
| P0 | 通用活跃DMM lookup/lease、全64位地址、每行span/clip验证；按FIFO批次记录失败；完整同步与callback完成状态机 | 先构造跨边界/释放中/失败批次反例；不允许越界写后报成功 |
| P1 | FillRect format0/1，selector0 alpha255；颜色按原打包，不限uniform；填充 x/y/w/h、stride | 不同颜色通道与行padding有像素比对，随后独立物理面readback |
| P2 | BitBlit同格式0/1、无旋转缩放/特殊flags，先实现0xb234地址公式与clip，按src/dst stride逐行；重叠复制方向需独立核对后支持 | 原菜单请求捕获证明命中支持子集；源/目标预置非零图案、跨行/重叠验收 |
| P3 | alpha混合与格式转换；0xc458/0xc520及0xb578/0xbbcc分支作为规格入口；先证实straight/premultiplied、alpha量化/舍入再实现 | alpha0/1/127/254/255、透明边缘、格式0↔1对照原路径；当前这些数学细节未闭合，禁止猜公式 |
| P4 | 字形bitmap的实际格式绑定；format2/3/4与mode1..4转换；若再发现动态CLUT才补CLUT | 完成AP文本栅格→GPE命中证据；当前不能直接解LTT/UX喂后端 |
| P5 | StretchRotateBlit、DrawVariousFrames及剩余flags | 逐分支恢复变换矩阵、采样、边框描述符；现仍不具备完整实现规格 |

v12的五个绑定入口不变：init0xc1d0 / Gperm::Init0x9ae8 / fill0xc30c / blit0xcf2c / flush0xc760，另保留setup0xdb74替换、原GetInstance/Main/FIFO。扩展 `fill` 和 `blit` 参数规划/写入层；先把 `extent_live()` 从固定545变为原分配事件绑定的只读活跃表，不能仅删掉固定extent检查。若还需支持opcode2/3，应新增对应worker入口，当前v12没有拦截它们，不能宣称全GPE覆盖。

v12 `flush` 只接受全零24B、此前有成功fill、无失败，条件下发4B0；该限制不能覆盖新异步callback或无绘制同步flush。建议以原FIFO命令为粒度完成并记录批次，而非永久 `raster_failed`/全局`fills_done`。此为设计建议，未改runtime。

既有 `gpe-uniform-native-readback.json` 只证明独立快照中的黑色清屏；没有文字、图标、混合、不同通道或显示提交验收。菜单实际使用操作码统计、字形格式、所有混合算法、CLUT存在性、动态DMM生命周期、旋转/边框详细字段、显示完成关联均明确未证实，不能将本报告当成菜单修复已完成。
