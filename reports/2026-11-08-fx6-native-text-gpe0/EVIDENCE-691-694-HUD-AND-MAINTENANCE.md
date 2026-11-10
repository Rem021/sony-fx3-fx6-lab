# EVIDENCE 691–694：Maintenance 三层页、HUD 状态条、HUD 主视窗、Paint/Playback

时间：2026-11-08（America/Los_Angeles）

四页共用 `/private/tmp/fx6_pages_691_694.c`
（`-DPAGE_MAINT / -DPAGE_HUDSTRIP / -DPAGE_HUDMAIN / -DPAGE_PAINT`）。
所有 ResID 与几何来自 appFw 描述符表与 `.rodata` 表；HUD 页用静态线 Phase 19/20 的
`fx6_hud_default_bindings` 绑定规则（DIRECT / NUMERIC_V1 / NUMERIC_V1_V2 三种模式）。
PNG 导出后**只用 Python 读像素**，未对任何 `.png` 调用图像读取。

## 1. 691 — Maintenance 三层页（`runs/cp-bind-4d7c108f`）

```
FX6_VSR68y col-title (568,62,280,36)  text=02004203   Maintenance
FX6_VSR68y list-item (578,163,370,40) text=0200426b   Language
FX6_VSR68y list-item (578,214,370,40) text=0200426c   Clock Set
FX6_VSR68y list-item (578,265,370,40) text=0200426d   Country
FX6_VSR68y list-item (578,316,370,40) text=0200426e   Hours Meter
FX6_VSR68y list-item (578,367,370,40) text=0200426f   Network
FX6_VSR68y list-item (578,418,370,40) text=02004270   Wi-Fi
FX6_VSR68y list-item (578,469,370,40) text=02004291   Network Reset
FX6_VSR69y done text=18 fill=17 icon=1 text_ok=18
```

左列下滚窗口显示分类 3..11，选中条在最后一项 `Maintenance`。

**一处 ResID 裁决**：任务给的 `0x0200222c` 在容器里解不出 `Maintenance`；
`fx6_pick()` 让固件裁决后命中 `0x02004203`（`fx6_top_categories` 里的那个 id）。

## 2. 692 — HUD 状态条（`runs/cp-bind-9e124870`）

三张表叠加：

| 表 | 基址 | 行数 | 渲染 |
|---|---|---|---|
| shooting strip | `0x2e957b0` | 11 | 6 条 |
| TC status | `0x2e96608` | 35 | 若干 |
| audio meter | `0x2e911f0` | 8 | 若干 |

日志样例（含绑定模式）：

```
FX6_VSR69y hud9  No49_clip_name        (244,417,536,30) desc
FX6_VSR69y hud9  No1066_base_look      (512,44,410,30)  desc
FX6_VSR69y hud11 No4_recstate_string_slot_1st (508,6,92,36) DIRECT
FX6_VSR69y hud11 No1004_recstate_string_slot_1st (522,2,92,36) DIRECT
```

像素：`nz=2,563`、纯白 826、抗锯齿绿 `0x99ffffaa` 228
—— 说明只渲染了少量 HUD 文本，没有整屏面板，符合「状态条」形态。

## 3. 693 — HUD 主视窗（`runs/cp-bind-3766b21f`，重跑）

首轮（`cp-bind-977302c1`）在渲染第 12 行后 **SIGSEGV（addr=nil）**：

```
APPFW_SEGV sig=11 addr=(nil) pc=... X0=0 X1=... X2=...
```

根因：253 行里有若干 `view_string` 描述符的 `+0x18` 是「看起来像 id 但容器里解不出」
的值，直接塞进 `+0x200` 会让 `TextProcessor` 拿到空记录后在内部解引用 null。

修复：未命中 HUD 绑定表的行，先用 `ResourceManager::getText` 探一次，
解析不出来就跳过（`fx6_render_row` 里的 `fx6_text_of` 守卫）。

重跑后仍记录到 1 次 `APPFW_SEGV`，但发生在第 12 行之后的其它线程上下文，
主渲染路径已完成到 `No16_resolution (846,47,142,30) DIRECT`。
帧已可用：`nz=5,288`、纯白 1,726。

**如实说明**：693 的主视窗页是 253 行、含大量运行时才注入状态的控件，
静态 hybrid 里无法完整跑完；当前帧是「已成功渲染的前 12 行 HUD 元素」，
不是整页完成态。要彻底跑完需要 controller 侧的状态注入，与 Setting 分类行同一类阻塞。

## 4. 694 — Paint / Playback（`runs/cp-bind-0b59967c`）

`TABLE 0x2eafdd8`（49 行）——Paint Direct 页：

```
FX6_VSR69y paint No6_Itemselectionofthefirstlayer (128,62,280,36) desc
FX6_VSR69y done text=1 fill=22 icon=2 text_ok=1
```

像素：`nz=434,495`、`0xcc222222` 390,370、`0xff333333` 20,943、`0xff666666` 11,425。

即：面板底、分隔线、图标都画出来了（22 条填充 + 2 个图标），
但只有 1 条文本 —— 该页绝大多数行是 `view_menu_item`（`0x042d58d0`），
其文本由 controller 注入，与 Setting 页同因。

## 5. 四张图的像素统计（Python）

| 页面 | 帧 | nz | 纯白 | 主色 |
|---|---|---|---|---|
| 691 Maintenance | `cp-bind-4d7c108f` | 435,024 | 2,567 | `0xcc222222` 361,504 |
| 692 HUD strip | `cp-bind-9e124870` | 2,563 | 826 | `0x00000000` 550,397 |
| 693 HUD main | `cp-bind-3766b21f` | 5,288 | 1,726 | `0x00000000` 547,672 |
| 694 Paint/Playback | `cp-bind-0b59967c` | 434,495 | 214 | `0xcc222222` 390,370 |

## 6. 交付物

- `menu-691-3layer-maintenance.png`
- `menu-692-hud-strip-and-tc.png`
- `menu-693-hud-main-viewfinder.png`
- `menu-694-paint-and-playback.png`
- 源码 `/private/tmp/fx6_pages_691_694.c`
- 前序：`EVIDENCE-687-690-TCMEDIA-THUMB-TECH-NET.md`

## 7. 结论与下一步

691 完成度与前面的三层页一致（18/18 文案）。
692 是真正的「状态条」形态（少量文本、无面板），符合预期。
693/694 暴露出同一个结构性限制：**`view_menu_item` 与大量运行时控件的文本
必须由 controller 注入**，静态描述符里是 0。这与 Setting 分类行、Big-6 六格当初的情况同源。
