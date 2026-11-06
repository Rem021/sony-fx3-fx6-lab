# 菜单高亮、面板与图标：同一 OSD 内的纹理路径最可疑，具体像素根因尚未闭合

2026-11-02。**现有证据优先指向 AP 生成的 fmt0 纹理及近似 GPE 栅格链，尚不支持通过“补一个 CP overlay 层”修复。** 高亮候选有真实九宫格 BitBlit；面板与瓦片候选也有向屏幕 bitmap 的真实 BitBlit，均为 selector1/K255/P73=1，原厂进入通用图元或缩放路径。它们没有被当前模型标成空 clip no-op；已记录的五条空 clip 确实在可见域外。**未取得这些命令执行时的源纹理字节，因此还不能在“源图为空/alpha 解释错误/取样或混合错误/后续覆盖”之间给出唯一根因或一个已证实的像素补丁。**（原码 libObj `153860–153938、1698f4–169954、101970–101d1c`；libgpe `cf2c–d144、bbcc–c150、c878–cf28`；AP101-r4 serial LF **60771–60782、246706–246711、258734–258738**。）

本任务完成的是有边界的离线审计与修复规格；**没有完成渲染修复或原厂硬件像素等价验证**。只写本目录三份文件，不改 runtime、STATE、固件、Git 或锁，不启动 QEMU、不连接 QMP、不操作设备。复用了 `gpe-blend-p3` 的只读重放类，未调用其他审计的 main/rebuild。

## 复现和证据

在 `/Volumes/KAFU2T/AI/Projects/Mac` 执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/menu-highlight-layers/audit_menu_layers.py
```

退出 0，重建 [menu-layers-proof.json](menu-layers-proof.json)。[脚本](audit_menu_layers.py) 核验外盘 UUID；固定 libObj、libgpe、既有重放器与三轮 serial 的 SHA；原始字节、完整参数、逐条 LF 行号、损坏记录和未证实项均保留。11 条**真实捕获参数**在隔离 Unicorn 中执行原描述符构造到提交前，拦截全部外部调用；不执行原像素硬件。另解析 103 份既有 ring slot header 中的完整 1003 和问题帧原始像素。PASS 表示证据重建及断言通过，不能作为修复通过。（proof `original、runs、selected_candidates_and_original_replay、native_publication_descriptors、final_readback`。）

重复发布日志的 `LIFE_SEND/OWNER_CURRENT` 保存全量计数及各op首/尾8条原行；完整serial由SHA固定，可重扫。其他身份/校验事件和所有完整GPE原参数保留，不用重复数万条未变化的1005填充proof。（proof各run `publication_record_counts/publication_record_sampling`。）

本轮核对 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html)，仅用于反汇编方法。Sony 私有语义来自本机原件，不从公共文档、邻机型号或工具 API 猜测。

本文 `R` = [menu-repair-01/runtime](../../../menu-repair-01/runtime/)，`A` = `R/runs/ap101r4tile600-be9996d0/serial.log`，`B` = `R/runs/ap100v1sync600-8d0d69c0/serial.log`，`C` = `R/runs/ap97r2alpha600-cd3c48f7/serial.log`。行号以 **LF、1 起算**；不将 CR 当换行。VA 是各自原 ELF 链接 VA，CP 是 Thumb，文件偏移=VA−108000。

| 等级 | 本文含义 |
|---|---|
| A1 | 原指令/表字节；原指令隔离重放得到的描述符，不含硬件像素 |
| A2 | 保存的运行日志、原始帧、发布元数据；保留观察器缺口 |
| B | 原码与几何/画面拟合；尚未绑定实际 Widget/resource ID |
| U | 未证实，不能作为默认实现规则 |

## 原厂 UI 的可确认路径

1. **UI 的矩形与图像最终可以进入 AP 本地 GPE。** `Sprite::setRectColorResID 168b70` 通过 ResourceManager 取颜色，`168c2c–168c40` 标记重绘；Sprite 实现区 `16954c` 调 `152ce8`，图像缓存区 `169908` 调 `15394c`，`169954` 经 PLT 调 GraphicsImage 的另一 copy 重载。`15394c→153714` 构造普通图像复制请求；`153860–153938` 装入 source/destination bitmap、源/目标矩形、方法和 repeat 选项，最后经 PLT55710→`GRM_gpermRectblit 101970`。`101b94–101ca8` 生成 selector/K/flags，原命令在 `101108–101174` 持 bitmap 锁取物理地址再调 GpermBitBlit。（A1，proof `original.libObj.so.blocks`。）
2. **纯颜色 fill 也是同一 GPE 层。** `1528b8` 读取 Color+3 的 alpha，部分透明时搬到 K，并将颜色 alpha 置255，随后 `152940→PLT56090→1017ac`。颜色不是 CP 提供的一条橙色高亮平面。这里仅证明一般绘制 API；没有运行时栈证明“每个选中条都走这个 fill”。实际三轮完整 FillRect 参数以清屏/灰色块为主，未见橙色 fill，因此“只补橙色 FillRect”没有依据。（A1：`15290c–152958、1017ac–101944`；A2：proof 各 run `raw_fill_counts、raw_records`。）
3. **有大量位图缓存/资源纹理；不能把每个 bitmap 当作显示层。** 例如 A:60771 的瓦片候选源属于父池 `[410924000,410c64000)`，A:258734 的面板候选源属于 `[410524000,410924000)`，目标则都是两个原屏幕 bank 之一。源资源是 GPE 输入，随后绘入 OSD；当前没有把这些源池单独发布为屏幕平面的证据。子块/bitmap/compaction 绑定仍有原 marker 明示的未覆盖项，read=1 和 result0 不保证源图内容正确。（A2：A **60771–60782、258734–258738**；A1 命令引用/锁：libObj `100fe4–101034、101108–101174`；[离屏审计](../offscreen-subblock/README.md) 第1、3节。）

上述链给出了实际原语入口，**没有恢复某个具体 UX resource ID→某个菜单 Widget 的一对一绑定**。下表特意称“候选”，不能把尺寸拟合升格为原生资源身份。（B/U，proof `unproven`。）

## 缺失元素的真实命令候选

以下六条都带完整144B参数且不在五条 no-op 内。除 separator 的 P74=1，均 `dstfmt0/srcfmt0, selector1, K255, P73=1, P74..78=0, conversion0, rotation0`；不是 fmt3/4，也不是带 CLUT 参数的调用。原重放全部提交到 `af30` 前，写 `760=1、770=05040501、771=0`；这证明源 alpha 混合控制路径，**没有恢复 factor 的硬件算术**。（A1/A2，proof `selected_candidates_and_original_replay`；原混合入口 `be04–be84、cb08–cb84`。）

| 候选 | A 的 LF行 / seq | 原144B几何与地址 | 原路径与判断 |
|---|---|---|---|
| 主菜单瓦片图案之一 | **60782 / 226** | src `410947400`，70×60，stride80；dst `43ae96100`，(195,302,70,60) | `cf2c→bbcc`；与同页多个70×60图案构成规则网格。角色为B级，未绑定名称 |
| Setup 内容/过渡面板之一 | **258738 / 1363** | src `41059c400`，640×384，stride640；dst `43ae96100`，(0,43,640,384)，clip同矩形 | `cf2c→bbcc`；覆盖内容区的纹理候选。不能只凭范围宣称它一定是不透明右面板 |
| 选中框上中片 | **246687 / 1215** | src `410977d00`，crop(6,0,308,6)，stride320；dst(144,43,486,6) | `cf2c→c878`，横向缩放 |
| 选中框中心片 | **246711 / 1218** | 同源，crop(6,6,308,40)；dst(144,49,486,41)，clip(138,43,498,53) | `cf2c→c878`，两轴倍率由486/308、41/40产生 |
| 选中框下中片 | **246729 / 1221** | 同源，crop(6,46,308,6)；dst(144,90,486,6) | `cf2c→c878`；加两侧6像素角片，形成320×52源的九宫格框 |
| 水平分隔线重复片 | **165317 / 757** | src `41093d500`，crop(16,0,32,2)，stride64；dst(240,95,458,2)，clip(224,95,416,2)，P74=1 | `cf2c→bbcc`；原描述符给出repeat相关mask，v8以 repeat_mask_v1 近似 |

九宫格形态还在语言列表首行出现：A **245381 / seq1130** 的顶部与 **245478 / seq1136** 的底部使用同一 `410977d00`，框位于(82,95,473,49)附近；后续回到 Setup 又移到 y43。与焦点移动的拟合较强，但缺少 Widget ID 与资源 ID，仍为 B 级高亮绑定。瓦片的重复实例见 A **60907–62658 / seq227..232**。（A2，proof `runs.ap101r4tile600-be9996d0.raw_records`；B角色解释。）

**修复应首先量测这些源纹理，而不是再加一个无法定位的绘制 opcode。** `P75=0/P76=0` 的候选在原码只写 color-op0/logic-op0；`741=0` 不能解释成“把图案染黑”。当前 fmt0 分支也没有用四个零 color 字节乘黑源纹理。真正需要核对的是 source bytes/alpha 与 sampler/blend 的实际输入输出。（A1：libgpe `bdd8–be00、cac4–caf0`；模型 `R/helpers/fx3-gpe-backend-v8.c:125–158、175–187、225–230`；像素内容 U。）

## 三轮运行对假设的检验

| run | 完整 CMD marker：fill / blit / flush | 可完整解码 RAW记录 / 损坏记录 | 观察到的 FB→bitmap/物理面 |
|---|---:|---:|---|
| AP97-r2 | 143 / 1059 / 3，已解析 result 均0 | 1195 / 35 | 单个 FB `7f70001140`，59次对象核验只出现两bank |
| AP100 | 163 / 1221 / 2，已解析 result 均0 | 1405 / 22 | 单个 FB `7f6c001140`，90次核验为两bank，各45次 |
| AP101-r4 | 317 / 1498 / 36，已解析 result 均0 | 1944 / 45 | 单个 FB `7f54001140`，383次核验为两bank，191/192次 |

数字与各轮 `*-review-v4.json` 的 `GPE_complete_records` 一致；RAW和CMD的保留数量不同，serial含跨线程拼接，**不能宣称观察到了全部 FIFO 命令**。这也不是三轮运行健康总评：AP97-r2旧 review 的 health_pass=false，而单独 acceptance 对未触发日期条件另有解释；本审计不重新裁定该门禁。（A2，proof `runs.*.review_summary、incomplete_raw_records`；R 下对应 `*-acceptance.json` 与 `*-review-v4.json`。）

| 假设 | 检验结果、证据等级 |
|---|---|
| 导出漏掉同时显示的第二 framebuffer | **B级不支持。** 三轮完整RAW BitBlit的目标都只有 `43ae96100 / 43feb5100`，上述核验把它们绑定到各自同一个FB；原 `f33ec/f33f0` 交换FB+60/+68两个 entry。A **23812、26026、28999**，B **26743、55949、62005**，C **24167、50107、64470**。这两bank是先后帧，不应叠加，否则引入旧帧重影。不能据此排除固件别处存在其他真正图层 |
| 1003+0xc 的 1 是层号 | **A1反证该推导。** 原 `f26f0 mov w1,#1; f26f4 str w1,[x0,#0xc]` 固定写1，没有来自Widget/层序的输入。103份已存1003头全部为1，token在401/402间切换；无z/global-alpha字段。其+10仅是`FB格式==2`布尔，非像素格式号。`f26f8–f2708`；proof `native_publication_descriptors` |
| 1002/1005 单独藏有另一像素面 | **A1不支持。** 1002是12B的next选择（1003或1005）；1005构造器只有8B，不携带地址/矩形/alpha。它不能凭空恢复缺少的源纹理。`f268c–f2698、f2770–f27d0`；A **23631–23692**；[完成审计](../osd-completion-6003/README.md) 第1节。原CP消费/合成后级仍U |
| 被当作成功no-op的空clip就是高亮/面板 | **A2针对已记录5条反证。** seq758/763/768 的交集 l=698,r=640；seq765/770为l=682,r=640，横向均无交集。原生成器仍会提交带clip的描述符；软件无像素读写是与几何一致的窄合同。A **165325、165355、165367、165387、165401**；原 `bc88–bcc4` 与本次11条重放。高亮1215/1218/1221、面板1363均有非空交集 |
| fmt3/4、CLUT或未知flags被成功忽略 | **A2有界否定。** 完整RAW BitBlit仅dst0/src0或src2。src0全为selector1、P73=1、P75/76=0，P74仅0/1；src2是文字遮罩候选P75=14，K128/255。当前v8对其余组合返回unsupported，并没有这些组合的成功no-op分支。`fx3-gpe-backend-v8.c:125–158、214、228–229`；proof各run `raw_blit_counts`。观察器缺口、其他直接opcode2/3仍不可排除 |
| 0x147提供了高亮/面板像素层 | **A1不支持。** 0x147的24×32B是YUV布局配置，不能提供纹理地址/stride/alpha。A **12029**、B **11967**、C **11952**；appFw `2deb060–2deb3fc`；[0x147审计](../vdf0147-plane-scanout/README.md) 第1、2节。不能把layout ID或配置bank当作OSD层 |
| 0x14c随焦点切换，控制缺失的区域overlay | **A2无支持。** 三轮各只捕获启动时三份相同40B布局配置，AP101为A **11946、11979、11997**，没有在已记录导航中随焦点改变。原CP旧0305接受后复制32B到内部f023（`5f5f7c–5f60b6`）；它与旧0306/f031的`SetOsdLayout`不是同一命令（`5f56ee–5f5768`）。仅有布局接受ACK不证明CP合成。适配绑定见R `fx3-vdf-config-proof.json:facts`；完整f023消费链U |
| PNG导出将透明的高亮丢掉 | **A2对问题帧反证。** [step10原始帧元数据](../../../menu-repair-01/runtime/runs/ap101r4tile600-be9996d0/ap101-step-10-key-1ac.json) 的raw SHA与committed ring SHA均`7aec7616…`，实际307200像素alpha nibble全15；没有可供alpha裁掉的透明分量。该帧缺失RGB已经存在于逻辑FB中；不能靠导出端强制不透明恢复。proof `final_readback` |
| 1000/1001 GUI配置包含尚未模拟的CP区域功能 | **U，必须保留。** 软件owner只冻结配置并计算hash，没有执行CP像素合成；A **22850–22861** 保存96B1001。appFw `16ee6f8–16ee77c` 构造含640×480的1001并异步发送，不能将96B或索引直接解释成图层。没有恢复原CP配置消费及每字段意义，因此不能证明它完全无关，也不能凭它指定一个新z层。模型R `helpers/fx3-osd-headless-v6-live-frame.c:64、68、80`；[握手审计](../libobj-frame-handshake/README.md) |

另一个容易混淆的成功返回是原 `GRM_fbrmFillrectYUV/RectblitYUV`：libObj `f393c/f3944` 本来就是 `mov w0,#0; ret`。这是**原库自身的stub**，不是本次软件模型漏实现后伪回成功；没有证据将当前高亮绑定到该入口。（A1，proof `original.libObj.so.blocks.0xf393c`；特定调用绑定U。）

## 最可能原因与可实施规格

**首选工作假设（B）：资源纹理内容/alpha约定与近似GPE消费链有断点。** 三种症状都拟合fmt0纹理：九宫格选择框、70×60瓦片图案、640×384内容区图像。文字srcfmt2及一些箭头/底栏能显示，不支持“所有OSD发布或整层都缺失”；但“source alpha全零”“ARGB误作RGBA”“预乘错误”“采样错误”都仍是U，不能现在任选其一作为修复。原厂只恢复到寄存器760/770，未恢复像素factor；当前 `straight_over_v1` 假设低nibble为alpha，源alpha为0时数学上不会改目标，这说明要抓源像素，**不是证明源alpha实际为0**。（A1/A2：上表真实参数；模型 `fx3-gpe-backend-v8.c:175–187、225–230`；B优先级推断。）

最小下一步由独占运行链实现，本worker未修改runtime：

1. **在同一原命令/资源租约内抓取输入与结果。** 对上述来源及几何白名单记录完整144B、seq/FIFO、父/子epoch、bitmap格式/stride/offset、原逻辑→物理转换，按source crop逐行抓raw/hash及alpha各nibble分布；另取dst clip绘前/绘后hash与少量像素。源范围是 `base+((sy+y)*stride+sx)*bpp`；本次中心源crop=(6,6,308,40)、stride320，不能把`308*40*2`当连续区域。快照与writer/free/compaction使用同租约，不另拿已持bitmap写锁自锁。（原物理/锁来源libObj `101108–101174、102b98、100fe4–101034`；A **246706–246711**；生命周期边界见[离屏审计](../offscreen-subblock/README.md) 第3节。）
2. **按测得断点修复，保留原参数。** 若源为空，追原资源解码/缓存producer及映射一致性，不把透明图一律置opaque；若源RGB/alpha非零但dst不变，定位resolver/取样/混合分支；若dst先正确后消失，沿FIFO找后续clear/blit覆盖及bank选择。只有源bitmap枚举、producer打包和原颜色定义共同证实时才增加格式转换；不要全局改FB位序或任意交换ARGB/RGBA。原fmt0高bit打包在libgpe `c400–c428`，独立PNG回调另有RGBA4444/ARGB4444两种（libObj `160224、16031c`），两者不能未经实际绑定互换。（A1；输入/输出结果仍待A2。）
3. **保持已恢复的原语合同。** 九宫格top/center/bottom按各自source crop及dst尺寸缩放，clip为半开矩形相交；P74=0从尺寸比产生scale，P74=1另按已批准repeat候选；selector1/K255继续启用源alpha混合，不能改成selector0覆写。零color且P75=0不tint，未知P75/P76、fmt3/4仍拒绝；empty clip仅在真实交集为空时零写完成。原依据libgpe `cf8c–d144、ce58–cedc、bdb0–be84`；本次重放覆盖11条真实命令。采样/混合仍标`approx_*`，不称Sony逐位公式。（A1规格；硬件像素U。）
4. **验收三种独立回执。** 源纹理与dst确实变化；1003对应当前bank提交同一hash；原生UP/DOWN后选择框随焦点变化，语言页可辨当前选中、瓦片图案出现、Setup右栏不再叠印左栏。对照不透明/半透明/透明边缘，空clip仍零写、旧fmt2文字不回归。原协议result0、host数学向量或只改变标题都不能替代这些像素/导航回执。（A1完成边界libObj `f2638–f27d4、f33d0–f3400`；当前缺口A的step10及proof `unproven`。）

## 若后续证实有额外图层，导出端的最小诚实做法

当前**没有恢复额外平面的z、位置、global-alpha或同时活跃身份**，所以不能交付“原厂多层合成公式”。已证实的最小行为是选当前FB entry快照，保留原extent/bitmap/token；**不要把401与402两个双缓冲帧叠加**。（A1：libObj `f335c–f3418`；A2：上述383次同FB对象核验；额外层参数U。）

若今后获得独立、同时活跃的平面描述，先逐平面验证bitmap/格式/stride/epoch、冻结同一提交点，分别导出raw与manifest；只对**实际证实**的z顺序、位置和alpha启用合成。可沿现有 [dump_osd_frame.py](../vdf0147-plane-scanout/dump_osd_frame.py) 提供显式命名的8bit straight source-over视觉候选：从后向前，以`As*globalAlpha/255`为有效alpha，将源/目标按显式RGBA布局合成并裁剪位置；若源是premultiplied则须另证并用对应式，不能复用straight假设。z/alpha未知时只交各独立面，不发明层序，也不根据0x147或1003常量1补参数。此为软件导出设计，**不是原厂CP合成规则**。（现工具规格见[0x147审计](../vdf0147-plane-scanout/README.md)“物理地址来源及离线导出规格”；当前CP断口`4b3712–4b3732→4b3874`仍只识别2000/2001/2002。）

## 明确未证实项与交付边界

- 高亮/瓦片/面板候选的确切Widget ID、资源ID、原资源producer及命令执行时source字节。
- 原硬件selector/factor像素式、alpha量化/预乘约定、采样中心与滤波；原指令重放只到提交前。
- 其他直接opcode2/3是否发生且被观察器遗漏；不以三种worker marker覆盖宣称全部GPE覆盖。
- GUI1000/1001与CP f023/f031的完整消费/区域作用、真正扫描合成/退休、6003/6005原发送schema。
- 修复实现、新运行像素/导航验收与实机视觉等价；本次均未执行。

这些缺口分别留在proof `findings/unproven`；它们不被“命令result0”“bitmap存在”“原描述符提交”或“当前能导航”所关闭。三份交付只在本目录，其他材料均只读。
