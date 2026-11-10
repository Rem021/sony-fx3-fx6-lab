# EVIDENCE 687–690：TC/Media、Thumbnail、Technical 三层页 + Network 状态页

时间：2026-11-08（America/Los_Angeles）

四页共用 `/private/tmp/fx6_pages_687_690.c`（`-DPAGE_TCMEDIA/-DPAGE_THUMB/-DPAGE_TECH/-DPAGE_NETWORK`）。
导出 PNG 后一律只用 Python 读像素校验，不调用图像读取。

## 1. 687 — TC/Media（`runs/cp-bind-5d471074`）

```
FX6_VSR68y col-title  (568,62,280,36)  text=0200222b   TC/Media
FX6_VSR68y list-item  (578,163,370,40) text=02004242   Timecode
FX6_VSR68y list-item  (578,214,370,40) text=02004243   Users Bit
FX6_VSR68y list-item  (578,265,370,40) text=02004244   TC Display
FX6_VSR68y list-item  (578,316,370,40) text=02004245   HDMI TC Out
FX6_VSR68y list-item  (578,367,370,40) text=02002244   Clip Name Format
FX6_VSR68y list-item  (578,418,370,40) text=02004253   Update Media
FX6_VSR68y list-item  (578,469,370,40) text=02004254   Format Media
FX6_VSR68y done text=18 fill=17 icon=1 text_ok=18
```

左列 9 项，选中条在第 6 项 `TC/Media`。

## 2. 688 — Thumbnail（`runs/cp-bind-3ae03677`）

```
FX6_VSR68y col-title  (568,62,280,36)  text=02004209   Thumbnail
FX6_VSR68y list-item  (578,163,370,40) text=02004209   Thumbnail
FX6_VSR68y list-item  (578,214,370,40) text=02004ff3   Clip
FX6_VSR68y list-item  (578,265,370,40) text=0200410d   Shot Mark
FX6_VSR68y list-item  (578,316,370,40) text=020028e8   Essence Mark
FX6_VSR68y list-item  (578,367,370,40) text=020042c7   Index Picture
FX6_VSR68y list-item  (578,418,370,40) text=02004fdd   Delete Clip
FX6_VSR68y list-item  (578,469,370,40) text=02004ff8   TC Index
FX6_VSR68y done text=18 fill=17 icon=1 text_ok=18
```

左列 9 项，选中条在第 9 项 `Thumbnail`。

## 3. 689 — Technical（左列下滚，`runs/cp-bind-bf2193a9`）

左列显示第 3..11 分类（`g_cats[2..10]`），行距按 9 行窗口重算：

```
FX6_VSR68y category (78, 64,462,41) text=02002227  Shooting
FX6_VSR68y category (78,115,462,41) text=02002228  Project
FX6_VSR68y category (78,166,462,41) text=02002493  Paint/Look
FX6_VSR68y category (78,217,462,41) text=0200222b  TC/Media
FX6_VSR68y category (78,268,462,41) text=02002229  Monitoring
FX6_VSR68y category (78,319,462,41) text=020041fb  Audio
FX6_VSR68y category (78,370,462,41) text=02004209  Thumbnail
FX6_VSR68y category (78,421,462,41) text=0200222a  Technical   ← 选中
FX6_VSR68y category (78,472,462,41) text=02004203  Maintenance
FX6_VSR68y col-title (568,62,280,36) text=0200222a  Technical
FX6_VSR68y done text=18 fill=17 icon=1 text_ok=18
```

右列 7 项：`Gain` / `Shutter` / `Iris` / `Focus` / `Auto Exposure` /
`White Balance` / `Detail`（`fx6_technical_items` 前 7 项）。

## 4. 690 — Network 状态页（`runs/cp-bind-a856514a`）

表格：`TABLE 0x2ead870`，55 行（Phase 18 的 `fx6_network_page_rows`）。

```
FX6_VSR68y done text=26 fill=6 icon=1 text_ok=26
FX6_VSR68y net (106,54,405,36) text=02002122   Network（标题）
FX6_VSR68y net (736,101,230,30) text=020052c9  IP Address 标签
FX6_VSR68y net (292,101,230,30) text=020052c7  Status 标签
FX6_VSR68y net (736,160/244/328,230,34) text=020050f6  IP 值 ×3
FX6_VSR68y net (299,404/469,230,34)     text=020050f6  Bluetooth 状态 ×2
...
```

- `fill=6`：`No4_NETWORK_BG`（`0x0200c003`）+ 5 条 `No41..47_SEPARATOR`（`0x0200c00b`）；
  四条 `No58..61_INACTIVE_FRAME`（`0x042d57d0`）的 `+0x18` 是 0，按无颜色跳过——
  这正是固件里「未启用的网络通道不画底色」的行为。
- `icon=1`：`No72_LEFT_ARROW`（`img=0x0200043d`，`32,267,45,60`）。

## 5. 像素校验（全部用 Python）

| 页面 | gpe0 非零 | 选中条 | 纯白 | 左列白 | 右列白 | 帧 sha256(前 24) |
|---|---|---|---|---|---|---|
| 687 TC/Media | 435,024 | 38,973 | 2,664 | 1,211 | 1,255 | `95c5af45c4962f73571f1102` |
| 688 Thumbnail | 435,024 | 38,912 | 2,498 | 1,211 | 1,083 | `bca30d998f32a152712b153b` |
| 689 Technical | 435,024 | 39,260 | 2,439 | 1,332 | 842 | `c66fb5fb97cdd813f9bbc27f` |
| 690 Network | 435,024 | 0 | 1,725 | 1,274 | 36 | `70d8d4c7299afa34757fc96a` |

四个帧的 sha256 各不相同，确认是四张独立画面而不是缓存复用。
687–689 的 `nz` 恰好相同是因为它们共用同一套面板/分隔线填充（只是文字与选中位置不同）；
690 换了整页背景色与布局（`0xdf111111` 占 420,256 像素，无选中条），所以构成明显不同。

## 6. 交付物

- `menu-687-3layer-tcmedia.png`
- `menu-688-3layer-thumbnail.png`
- `menu-689-3layer-technical.png`
- `menu-690-network-status.png`
- 源码 `/private/tmp/fx6_pages_687_690.c`
- 前序：`EVIDENCE-684-686-SETBUTTON-AND-3LAYER.md`、`EVIDENCE-681-683-PROJECT-AND-SETTING.md`
