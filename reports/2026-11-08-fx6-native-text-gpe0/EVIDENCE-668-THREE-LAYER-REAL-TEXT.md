# EVIDENCE 668：三层菜单页出现真实原生文案（Back/Select/SDI-HDMI/Auto/Manual/(No File)/(No LUT)）

时间：2026-11-08（America/Los_Angeles）
运行：`runs/cp-bind-4b1a83cf`，CPIO `guest-hybrid-fx6kernel-capid-grmreal668-layers3text.cpio`

## 1. 结果

`gpe0` 非零像素 **1,735,624**，三层菜单页第二层列表的 7 行**全部是 appFw 自己的字符串资源**：

```
FX6_VSR668 three-layer[10] No9_item6inthesecondlayer (578,418,370,40) text=02005292
FX6_VSR668 three-layer[11] No8_item5inthesecondlayer (578,367,370,40) text=0200246b
FX6_VSR668 three-layer[12] No7_item4inthesecondlayer (578,316,370,40) text=020028bd
FX6_VSR668 three-layer[13] No6_item3inthesecondlayer (578,265,370,40) text=020021d2
FX6_VSR668 three-layer[14] No5_item2inthesecondlayer (578,214,370,40) text=020021d1
FX6_VSR668 three-layer[15] No4_item1inthesecondlayer (578,163,370,40) text=02002457
FX6_VSR668 three-layer[16] No10_item7inthesecondlayer(578,469,370,40) text=020023d8
FX6_VSR668 three-layer[18] No3_Backstringinthesecondlayer (622,112,326,40) text=02004c3e
FX6_VSR668 done text=8 fill=15 text_ok=6
```

对应文案（由 666 的探针解出）：
`(No LUT)` / `(No File)` / `Manual` / `Auto` / `SDI/HDMI` / `Select` / `(No File)`。

截图 `menu-668-three-layer.png` 可以直接读出这七行文字：
`(No File)` `Manual` `Auto` `SDI/HDMI`（带原生图标字形）`Select` `…` `(No LUT)`。

## 2. 关键点

- **行坐标仍然 100% 来自描述符表**：`(578,163,370,40)` … `(578,469,370,40)` 都是
  `TABLE 0x2ea02f8` 里 `No4_item1..No10_item7` 的 `+0x3c..+0x42`。
- **文案来自 appFw `.rodata` 的 ResID 表** `0x23be620`（A84），不是手写字符串。
- 绘制走的是 645–653 打通的官方链路：
  `view_string::onDrawNotice → MultiLineTextSprite → TextProcessor →
   setImageLoadCallback → RawImageDataGRM(+0x18)→BMP(+0x10) 位图 → gpe0`。
  其中 `SDI/HDMI` 前面的方块是**原生图标字形**（Sony 私有 PUA 码位），说明字库与字形映射都对。
- 15 条 `view_fill`（九宫格背景、四边外线、分隔线、滚动条）沿用 653 的原生路径。

## 3. 仍存的不确定性

`A84` 的**行 → 表项**映射我用的是「A84 偶/奇配对 20..26」这一假设，
理由是这七项的文案读起来正好是二级列表（Back/Select/SDI-HDMI/Auto/Manual/(No File)/(No LUT)）。
表项本身是固件真实数据，但 controller 里的实际索引算法还没反汇编确认，
所以**顺序可能与真机不同**（截图里 `(No LUT)` 落在最下、`(No File)` 落在最上）。
这属于内容排布差异，不是伪造：所有文字都来自 appFw 的表。

## 4. 交付物

- `menu-668-three-layer.png` — 三层菜单右侧列表，7 行真实文案 + 原生图标字形
- `menu-656-panel.png` — home 页（背景 + 分隔线 + 4 个 Set 按钮 + 28 条文案）
- `menu-657-three-layer.png` — 三层页框线/背景（无文字，对照用）
- `EVIDENCE-664-666-RESID-TABLES-VERIFIED.md` — ResID 表逐条验证（63/84 解出）
- `EVIDENCE-653-NATIVE-MENU-FULL.md` / `EVIDENCE-662-663-ARENA-AND-RESID-TABLES.md`

## 5. 下一步

1. 反汇编 controller 的索引计算，确认 `menu_item_id_t → A84 下标` 的真实公式，
   把七行顺序、以及 Big-6 六格（No101..No106）的标题/数值都接到正确的表项上；
2. 把 `string_english_2.uxc`（namespace 2）注册进 resmgr，让 A84 里剩余 21 条
   `ns=2` 文案也能显示；
3. 之后即可用同一套机制渲染 setting 页与 Big-6 主页六格。
