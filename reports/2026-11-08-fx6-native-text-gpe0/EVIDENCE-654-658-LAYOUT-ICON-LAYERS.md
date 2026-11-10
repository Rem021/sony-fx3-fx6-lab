# EVIDENCE 654–658：布局去重叠、1px 线、icon 判定、三层菜单表

时间：2026-11-08（America/Los_Angeles）

## 1. 654/655/656：中栏重复布局过滤（最终版 656）

`TABLE 0x2e9e210`（98 项）同时带两套互斥布局：
`No1xxx_*`（标准中栏）与 `No2ddd_*`（紧凑中栏）。同时渲染会让 y=194..382 的中栏文字叠字。

过滤规则经过两次修正才正确：

| 版本 | 规则 | 结果 |
|---|---|---|
| 654 | `No2` + 非 `_` | 误伤 `No210_AUDIO_LEVEL_METER`、`No28_BG` 等两/三位编号控件，fill 从 8 掉到 6 |
| 655 | `No2` + 非 `_` | 同上，仍误伤 |
| **656** | `No2` + **恰好三位数字** + `_`（即 `No2ddd_`） | ✅ `skipN2=38`，`fill` 恢复 8，`No28_BG` 正常 |

656 关键日志：

```
FX6_VSR656 home presenter[02] F No28_BG  (96,194,768,188) rects=... c=222222ff
FX6_VSR656 done text=28 fill=8 icon=0 skipN2=38 text_ok=19
gpe0 nz 790166
```

交付：`menu-656-panel.png`（中栏清爽，`Reel/Shot/3840P/FF` 等不再重叠）。

## 2. 1px 细线

`fx6_render_fill` 的入参校验由 `w<2 || h<2` 放宽为 `w<1 || h<1`，
三层菜单表里的 1px 外框线（`No11_Upperoutsideline` w=910,h=1；
`No13/No17_*outsideline` w=1,h=477）得以正常走原生 `view_fill` 渲染。
657 实测 15 条 `FX6_NEXT_FILL`，含 `r=57,49,910,1` 与 `r=967,49,1,477`。

## 3. view_icon 判定（尚未出像素）

- 正确构造器 `appFw+0xc2c188`（内部构造内嵌 `view_fill` 于 `+0x240`、`Sprite` 于 `+0x550`、
  `ImageData` ID 于 `+0x648`），`image_resid` 在 `+0x20c`，`+0x1fc` 为绘制开关；
  `onDrawNotice` 在 `+0x158`，前段 `0xc2d120` 检查 `+0x1fc` 与 `+0x20c != -1`。
- 但描述符里 icon 类（tag `0x42d5a50/0x42d5800/0x42d5930`）的 `+0x18` 多数是 **0**，
  真正的 image ResID 由运行期 model 写入（如 `No9_BATTERY` 的 q18=0）。
  因此 654/655 的 `icon=0` 不是代码缺陷，而是这些图标本来就没有静态图片资源。
- 657 里出现的唯一带静态图片的 icon 是 `No2_Backiconinthesecondlayer`
  （`img=02000154`，位于 `578,112,38,38`）。

## 4. 657：三层菜单表 `TABLE 0x2ea02f8`

- 表长 **35 项**（`0x2ea02f8 + 35*0x48 = 0x2ea0c88`），其后的 `0x2ea0d18` 已是另一张 69 项表。
- 渲染结果：15 条原生 `view_fill`（九宫格背景、左右/上下外框线、两条分隔线、滚动条底/条、
  条目选中条 `No21_ItemBG`）+ 1 条文字 + 1 个 icon。
- 该页大部分行（`No4_item1..No10_item7inthesecondlayer`、`No24_Itemnumber`）的 `+0x18`
  在静态表里就是 0，文本由 controller 在运行时按当前选中项注入；
  hybrid 里没有 controller，所以这些行是空的。
- 交付：`menu-657-three-layer.png`（框线/背景正确，内容区留空）。
- 注意：**657 用的是 35 项**；表中的 `No28..No35_itemtouchbutton*`（8 个按钮）；
  都是有静态几何但无静态文本的按钮位。

## 5. 658：setting 主页

`TABLE 0x2ea3e50`（10 项）单独渲染：
- `[01] No4_SETTING_LIST_MAIN`（`0x42d5a20`）是列表容器类，不是 `view_fill`，未绘制；
- `[02..05]` 的 `+0x18` 为 0（动态值），未出文字；
- `[06..09]` 四个 `Set` 按钮正常，落在 `(398/654, 80/425)`。

交付：`menu-658-setting.png`。

## 6. 当前最佳整页

**656（home presenter）**：`menu-656-panel.png`
背景板 + 三条分隔线 + 4 个 `Set` 按钮 + 28 条原生文案，无重叠。

## 7. 下一步可做的

1. 用 controller 的运行时注入路径补齐 `[02..05]` / 三层表行文本（需要 `menu_item_id_t` 与 model 值）。
2. 为 `No4_SETTING_LIST_MAIN`（`0x42d5a20`）这类列表容器找到真正的类（很可能是
   `view_list_scroll_item`，vptr `0x2d1c2c0`，ctor `0xc30c3c`）并驱动其 onDraw。
3. 接 Big-6 六格外框的子 presenter 表（FPS/Shutter/ISO/ND/WB/Look）。
