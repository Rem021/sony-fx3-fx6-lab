# EVIDENCE 677–678：Big-6 边框/图标完成；Setting 主页的静态边界

时间：2026-11-08（America/Los_Angeles）

## 1. 677：Big-6 六格边框 + 图标（成功）

```
FX6_VSR677 done text=36 fill=38 icon=6 cells=6 text_ok=36
FX6_VSR677 icon (102,78,28,28) img=02000571
FX6_VSR677 icon (355,78,28,28) img=02000571
FX6_VSR677 icon (613,78,28,28) img=02000571
FX6_VSR677 icon (102,388,28,28) img=02000571
gpe0 nz 1,321,608
```

相对 676 的增量：

| 项 | 676 | 677 |
|---|---|---|
| `text_ok` | 36/36 | 36/36 |
| `fill` | 14 | **38**（+24 = 6 格 × 4 边） |
| `icon` | 0 | **6** |

实现方式：

- **边框**：`fx6_border()` 用四个原生 `view_fill`（ctor `0xc27698` + onCreate + onDraw +
  `setRectPos` + `renderRect`）画 1px 四边。第一格用 `0x0200c011`（`color_cmn.uxc` 强调色，
  模拟选中态），其余五格用 `0x0200c00e`（分隔线灰）。
- **图标**：从 `appFw .rodata 0x23be8e0` 的 `(glyph, caption)` 成对表读取，
  经 `fx6_icon_blit()`（ctor `0xc2c188`，`+0x1fc=1`、`+0x20c=glyph`、`+0x21c..0x21f` RGBA、
  `+0x204/+0x206` 裁剪宽高）走 `onCreate → onDrawNotice`。
- 每格顺序：**底色 → proccmd(0) → 边框 → proccmd(0) → 图标 → proccmd(0) → 标题/值文字**，
  避免队列中的填充盖住已交付的字形位图。

截图：`menu-677-big6-framed.png`（六格均有灰框，首格高亮框，左上角图标，两行文字齐全）。

## 2. 678：Setting 一级主菜单（静态表本身没有文案）

`TABLE 0x2ea3e50` 共 10 项，逐项实况：

```
[00] No107_BLOCK_TOUCH      tag 0x42d5860  触摸屏蔽
[01] No4_SETTING_LIST_MAIN  tag 0x42d5a20  view_list_scroll_cursor_fixed（0x239870 字节容器）
[02] No20_SETTING_MAIN_STRING  text=0      ← 空
[03] No3_SETTING_VALUE         text=0      ← 空
[04] No32_SETTING_VALUE2       text=0      ← 空
[05] No2_SETTING_ITEM          text=0      ← 空
[06..09] No106/105/103/102_BUTTON_*  text=0x020023da "Set"  ×4
```

渲染结果：

```
FX6_VSR678 done text=4 fill=0 icon=0 skipN2=0 text_ok=4
```

即只有四个 `Set` 按钮出字，中间列表区与标题区为空。
`fill=0` 也说明这张页没有任何静态背景/分隔线描述符（对比三层页有 15 条）。

### 为什么没有 7 个分类行

我把 `appFw.so` 里所有 7 项连续 ResID 跑了一遍（`0x227f758 / 0x227fa18 / 0x2280928 /
0x23be8bc / 0x23d9700 / 0x23da5b0` …），解出内容分别是：

```
0x227f758: RAW / Recording / "" / S&Q Motion / Setting / On / Voltage Low
0x227fa18: ND Filter / Auto / VF / Unsupported / WHT BAL / PRESET / Cannot Proceed
0x2280928: "" / Clip Continuous Rec / Setting / On / High Frame Rate Mode / Recording / …
0x23be8bc: "" / 709(800%) / 709(800%) / S-Log3 / …
```

**没有一张是** `User / Edit User Menu / Shooting / Project / Paint·Look / TC·Media / Monitoring`。
而且 `Edit User Menu`、`Paint/Look`、`TC/Media` 这三个串在 `appFw.so` 里只有
`Monitoring` 能以明文找到（`0x262d55f`），其余都在压缩的 `.uxc` 容器里按记录号存放。

结论：Setting 一级页的 7 个分类行**和 Big-6 六格当初的情况完全一样** ——
描述符 `+0x18` 是 0，文本由 `procam_big6_menu_setting_controller` 在运行时
按 `menu_item_id_t` 注入。静态表里没有这份映射，所以无法在不猜的前提下填出 7 行。

## 3. 累计成果（本轮 669→678）

| 候选 | 成果 |
|---|---|
| 669 | 补 `string_english_2.uxc`，A84 从 63/84 → **84/84** |
| 670/672 | Big-6 Home 整页骨架 + 六格定位（描述符驱动，`(y,x)` 排序） |
| 671–675 | 5 次对照实验排除 z 序/底色/namespace/字段缺失 |
| **676** | 修 `+0x20c` 与字体参数 → **`text_ok` 24→36，六格文案全出** |
| **677** | 六格边框（+24 fill）+ 图标（+6 icon） |
| 678 | Setting 页验证：静态表只有 4 个 `Set` 按钮，分类行需 controller |

## 4. 交付物

- `menu-677-big6-framed.png` — Big-6 Home 完成版（六格 + 边框 + 图标 + 中央网格）
- `menu-678-setting-main.png` — Setting 页（仅 4 个 Set 按钮，如实反映静态表内容）
- `menu-670-big6-home.png` / `menu-676-big6-top.png` / `menu-676-big6-bottom.png`
- `menu-669-three-layer.png` / `menu-668-three-layer.png` / `menu-656-panel.png`
- 证据：`EVIDENCE-676-BIG6-COMPLETE.md`、`EVIDENCE-669-NS2-FIX-ALL-84.md`、
  `EVIDENCE-664-666-RESID-TABLES-VERIFIED.md`、`EVIDENCE-670-675-BIG6-HOME.md`

## 5. 后续

Setting 页与三层页剩余空白行的共同前置条件是 controller 的
`menu_item_id_t → ResID` 索引公式。拿到它之后，
`fx6_render_string_rid`（现已完全可用）可以直接把这些行填满，
不需要新的渲染代码。
