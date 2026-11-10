# EVIDENCE 684–686：Assignable Button 网格页 + Monitoring / Audio 三层页

时间：2026-11-08（America/Los_Angeles）

三页共用 `/private/tmp/fx6_pages_684_686.c`（编译期 `-DPAGE_SETBUTTON/-DPAGE_MONITOR/-DPAGE_AUDIO`）。
PNG 导出后一律只用 Python 读像素校验，不再走图像读取（避免多模态退避）。

## 1. 684 — FX6_PAGE_SET_BUTTON（page 110，`0x02eb75f0`）

`runs/cp-bind-7569e0a2`

```
FX6_VSR68y chrome-text (106,54,405,36) text=0200211e     Assignable Button
FX6_VSR68y chrome-text (706,54,94,36)  text=02002e12     Index
FX6_VSR68y chrome-text (60,51,45,42)   text=020026c2     \ue60b 标题图标
FX6_VSR68y chrome-text (668,54,38,36)  text=02002e21     Index 箭头
FX6_VSR68y chrome-text (814,54,36,36)  text=020021d6     翻页箭头
FX6_VSR68y slot-label (74,103,421,58)  text=020023c4     AF Speed/Sens.
FX6_VSR68y slot-label (74,175,421,58)  text=020020d0     White Balance
FX6_VSR68y slot-label (74,247,421,58)  text=02004288     ND Filter
...
FX6_VSR68y done text=35 fill=17 icon=1 text_ok=35
```

像素统计（Python）：

```
gpe0 非零           435,314
0xdf111111 (BG 0x0200c003)  366,923
0x0                        117,646
0xff00aaff (选中条)          29,598
0xff444444 (分隔线 0x0200c00b) 21,416
0xffffffff                 4,965
标题带 near-white          626
左右两列 near-white      4,296 / 4,296
```

实现要点：

- 背景与 **12 条分隔线** 全部来自 `fx6_set_button_page_rows` 的 `view_fill` 行，颜色
  `0x0200c003` / `0x0200c00b` 直接取自描述符 `+0x18`；
- 顶部 chrome（标题 / Index / 三种箭头 / 标题图标）由描述符里的 `view_string` 与
  `view_icon` 两行按 `+0x18` 渲染，坐标即表内坐标；
- **30 个槽位**按描述符矩形排布（左列 `x=60`、右列 `x=515`，行距 72/57 两段），
  文字来自 `fx6_assignable_label_pool[30]`；
- 首格加 `0x0200c014` 选中条。

## 2. 685 — Monitoring 三层页

`runs/cp-bind-5cfcef8c`

```
FX6_VSR68y col-title (568,62,280,36)  text=02002229   Monitoring
FX6_VSR68y list-item (578,163,370,40) text=02004238   Output Setting
FX6_VSR68y list-item (578,214,370,40) text=02004236   Output Format
FX6_VSR68y list-item (578,265,370,40) text=02004235   Output On/Off
FX6_VSR68y list-item (578,316,370,40) text=02004234   Audio Output
FX6_VSR68y list-item (578,367,370,40) text=02004239   Monitor LUT
FX6_VSR68y list-item (578,418,370,40) text=0200423a   Output Display
FX6_VSR68y list-item (578,469,370,40) text=02004241   Display On/Off
FX6_VSR68y done text=18 fill=17 icon=1 text_ok=18
```

像素：`gpe0 nz 435,024`，`0xcc222222`（面板底）360,311，
选中条 `0xff00aaff` 38,617，列表区 near-white 1,568。
左列选中条移到第 7 项 `Monitoring`。

## 3. 686 — Audio 三层页

`runs/cp-bind-7138f141`

```
FX6_VSR68y col-title (568,62,280,36)  text=020041fb   Audio
FX6_VSR68y list-item (578,163,370,40) text=02004232   Audio Input
FX6_VSR68y list-item (578,214,370,40) text=02004233   Audio Level
FX6_VSR68y list-item (578,265,370,40) text=02004234   Audio Output
FX6_VSR68y list-item (578,316,370,40) text=02002192   Volume
FX6_VSR68y list-item (578,367,370,40) text=02002191   Headphone Out
FX6_VSR68y list-item (578,418,370,40) text=02003132   Wind Filter
FX6_VSR68y list-item (578,469,370,40) text=0200429f   WRR Setting
FX6_VSR68y done text=18 fill=17 icon=1 text_ok=18
```

像素：`gpe0 nz 435,024`，列表区 near-white 1,356。左列选中条移到第 8 项 `Audio`。

## 4. 一致性

三页 `text_ok` 均等于 `text`（35/35、18/18、18/18），没有丢字形交付。
685 与 686 的像素总量、选中条面积、列表文字量完全一致，说明两页只有数据不同、
渲染路径完全相同。

## 5. 交付物

- `menu-684-setbutton-page110.png`
- `menu-685-3layer-monitoring.png`
- `menu-686-3layer-audio.png`
- 源码：`/private/tmp/fx6_pages_684_686.c`
- 前序：`EVIDENCE-681-683-PROJECT-AND-SETTING.md`、`EVIDENCE-679-680-THREE-LAYER-PAGES.md`
