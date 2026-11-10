# EVIDENCE 681–683：Project·Rec Format、Setting Center、Setting 主菜单填充态

时间：2026-11-08（America/Los_Angeles）

三个页面共用同一渲染器（`/private/tmp/fx6_pages_681_683.c`，编译期用
`-DPAGE_PROJECT/-DPAGE_CENTER/-DPAGE_SETTING` 选择），
所有坐标、颜色、文案都来自 appFw 描述符表与 `.rodata` ResID 表。

## 1. 681 — Project → Rec Format（`runs/cp-bind-561e137c`）

```
FX6_VSR68x col-title (568,62,280,36) text=0200425f
FX6_VSR68x rec-format (578,163,370,40) text=02004987
FX6_VSR68x rec-format (578,214,370,40) text=02004989
FX6_VSR68x rec-format (578,265,370,40) text=0200498b
FX6_VSR68x rec-format (578,316,370,40) text=0200498d
FX6_VSR68x rec-format (578,367,370,40) text=0200498f
FX6_VSR68x done text=16 fill=17 icon=1 text_ok=16
```

画面（`menu-681-3layer-project.png`）：
- 左列 9 个一级分类，**`Project` 带青色选中条**
- 右列标题 `Rec Format`、返回图标 + `Back`
- 5 个录制格式，首项带选中条：
  `XAVC 4096×2160 P` / `XAVC 3840×2160 P` / `XAVC 2048×1080 P` /
  `XAVC 1920×1080 P` / `MPEG 1920×1080 i`

**一处 ResID 分歧已用固件裁决**：静态线的 `fx6_project_items` 给 `Rec Format = 0x0200425f`，
而任务里写的是 `0x020022d2`。我加了 `fx6_pick()` —— 两个 id 都交给
`ResourceManager::getText` 实际解析，谁解出 `Rec Format` 就用谁。
日志显示命中的是 **`0x0200425f`**，所以页面用的是它。

## 2. 682 — Setting Center（`runs/cp-bind-658847a9`）

```
FX6_VSR68x centre-title (154,269,148,32) text=020029f8
FX6_VSR68x cell-title (104,78,241,30) text=02005082
FX6_VSR68x cell-title (357,78,246,30) text=020050e8
FX6_VSR68x cell-title (615,78,241,30) text=02004c32
FX6_VSR68x cell-title (104,388,241,30) text=02004288
FX6_VSR68x cell-title (357,388,246,30) text=02005689
FX6_VSR68x cell-title (615,388,241,30) text=020023f8
FX6_VSR68x done text=14 fill=38 icon=0 text_ok=14
```

画面（`menu-682-setting-center.png`）：
- `No1_BG`（`0x0200c001`）+ `No28_BG`（`0x0200c008`）+ 6 条分隔线（`0x0200c00e`）
- 中央条：`Look`（`0x020029f8`）+ `S-Cinetone`（`0x02002464`）
- 上下六个外圈格：每格四边线 + 标题 + 数值
  （`FPS`/`Angle (Continuous)`、`Shutter`/`Shutter`、`ISO`/`ISO/Gain`、
  `ND Filter`/`ND Filter`、`White Balance`/`WB: A`、`Base Look`/`S-Cinetone`）

修复记录：首版把 row 1..10 全部当填充画，其中 `No8_CENTER_VALUE`、
`No7_CENTER_TITLE` 是 `view_string`（`+0x18` 为 0），于是画出一条白带。
改为只对 `fx6_tag_kind == 2`（`view_fill`）的行填充后干净了，`fill` 从 40 降到 38。

## 3. 683 — Setting 主菜单填充态（`runs/cp-bind-67a081b7`）

```
FX6_VSR68x setting-cat (116,82,362,40)  text=02004208   User
FX6_VSR68x setting-cat (116,136,362,40) text=02004d4a   Edit User Menu
FX6_VSR68x setting-cat (116,190,362,40) text=02002227   Shooting   ← 选中
FX6_VSR68x setting-cat (116,244,362,40) text=02002228   Project
FX6_VSR68x setting-cat (116,298,362,40) text=02002493   Paint/Look
FX6_VSR68x setting-cat (116,352,362,40) text=0200222b   TC/Media
FX6_VSR68x setting-cat (116,406,362,40) text=02002229   Monitoring
FX6_VSR68x setting-cat (116,460,362,40) text=020041fb   Audio
FX6_VSR68x main-string (519,95,305,32)  text=02002227   Shooting
FX6_VSR68x button x4                    text=020023da   Set
FX6_VSR68x done text=15 fill=1 icon=0 text_ok=15
```

画面（`menu-683-setting-populated.png`）：
- 左侧列表区 `(96,72,402,432)` 内 8 个顶级分类，`Shooting` 带青色选中条
- 右侧 `Shooting` / `Base Look` / `S-Cinetone`
- 四个 `Set` 按钮

**第二处 ResID 裁决**：任务写按钮文字为 `0x020047a4`，而 678 实测按钮描述符用的是
`0x020023da`。`fx6_pick()` 再次让固件裁决，命中 **`0x020023da`**（解出 `Set`），
`0x020047a4` 在这个 hybrid 里解不出 `Set`。

## 4. 交付物

- `menu-681-3layer-project.png`
- `menu-682-setting-center.png`
- `menu-683-setting-populated.png`
- 渲染器源码：`/private/tmp/fx6_pages_681_683.c`
- 前序证据：`EVIDENCE-679-680-THREE-LAYER-PAGES.md`、`EVIDENCE-677-678-FRAMED-AND-SETTING.md`

## 5. 说明

- 三页的 `text_ok` 都等于 `text`（16/16、14/14、15/15），即所有字符串都完成字形交付。
- 两处 ResID 与任务描述不一致时，我没有二选一硬猜，而是让 `ResourceManager::getText`
  现场裁决并在日志里留痕，这样后续复核可以只看日志。
