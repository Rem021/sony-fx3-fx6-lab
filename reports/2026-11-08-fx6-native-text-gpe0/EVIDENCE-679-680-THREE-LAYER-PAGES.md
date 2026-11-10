# EVIDENCE 679–680：三层菜单双列页面（Shooting / Paint·Look→Base Look）

时间：2026-11-08（America/Los_Angeles）

## 1. 679 — Shooting 页（`runs/cp-bind-a61c4dbe`）

```
FX6_VSR679 done text=18 fill=16 icon=1 skipN2=0 text_ok=18
gpe0 nz 1,711,188
```

画面（`menu-679-3layer-shooting.png`）：

- **左列 9 个一级分类**（原生 `No25_Gridlist` 区域 `62,56,494,462`，行距 51）：
  `User` / `Edit User Menu` / **`Shooting`（青色选中条 `0x0200c014`）** / `Project` /
  `Paint/Look` / `TC/Media` / `Monitoring` / `Audio` / `Thumbnail`
- **右列**：
  - 顶部标题 `Shooting`（`No23_Itemselectionofthefirstlayer` `568,62,280,36`）
  - 返回行：原生返回图标（`img=0x02000154`，`578,112,38,38`）+ `Back`（`622,112,326,40`）
  - 7 行 Shooting 项（`578, y=163..469 step 51, 370×40`）：
    `FPS` / `Shutter` / `ISO` / `Gain` / `ND Filter` / `Look` / `S&Q Motion`
- 16 条原生 `view_fill`（九宫格背景、四边外线、两条分隔线、选中条、滚动条）

分类 ResID 全部来自 mapA（`appFw+0x226a6c0`）按 slot id 解析：
`User=0x02004208`、`Edit User Menu=0x02004d4a`、`Shooting=0x02002227`、
`Project=0x02002228`、`Paint/Look=0x02002493`、`TC/Media=0x0200222b`、
`Monitoring=0x02002229`、`Audio=0x020041fb`、`Thumbnail=0x02004209`。

## 2. 680 — Paint/Look → Base Look（`runs/cp-bind-0998e0b5`）

```
FX6_VSR680 done text=18 fill=17 icon=1 skipN2=0 text_ok=18
```

画面（`menu-680-3layer-baselook.png`）：

- 左列同 9 项，选中条移到 **`Paint/Look`**
- 右列标题换成 **`Base Look`**（`0x020023f8`）
- 返回行同 679
- 7 行 look 选项，首项 `S-Cinetone` 带选中条（`0x0200c014`）：
  `S-Cinetone` / `S-Log3` / `s709` / `709(800%)` / `HLG Live` / `HLG Natural` / `ITU709`

`fill` 比 679 多 1，正是新增的选项选中条。

## 3. 实现要点

两个页面共用同一个渲染器，只有三处不同（选中分类下标、右列标题 ResID、右列 7 行内容），
其余全部一致：

- 描述符表 `TABLE 0x2ea02f8` 前 35 项先统一渲染 `view_fill`（背景/边框/分隔线/滚动条）；
- 左列 9 行按原生 Gridlist 矩形与行距排布，选中项用 `color_cmn.uxc` 的 `0x0200c014` 打底；
- 右列标题/返回行/7 行内容分别用 `fx6_render_string_rid` 渲染，
  返回箭头用 `fx6_icon_blit`（原生 `view_icon`）；
- 每次绘制后都 `processCommands(0)`，保证填充不盖住已交付的字形位图。

`text_ok` 两页都是 18/18，说明所有字符串都完成了字形交付。

## 4. 交付物

- `menu-679-3layer-shooting.png` — Shooting 页（9 分类 + Back + 7 项）
- `menu-680-3layer-baselook.png` — Paint/Look → Base Look 页（9 分类 + Back + 7 个 look 选项）
- `menu-677-big6-framed.png` — Big-6 Home 完成版
- `menu-669-three-layer.png` / `menu-668-three-layer.png` — 三层页前序
- 证据：`EVIDENCE-677-678-FRAMED-AND-SETTING.md`、`EVIDENCE-676-BIG6-COMPLETE.md`

## 5. 后续可做

- 其余 7 个一级分类的第二层内容（Project / TC/Media / Monitoring / Audio /
  Thumbnail / User / Edit User Menu）——静态线已有部分 option 表，
  按同一渲染器换数据即可；
- 左侧分类列表的滚动状态与右侧滚动条比例；
- `Gain`（`0x0200420e`）等个别项在容器里的别名需要按 mapA 的 slot 再核对一次。
