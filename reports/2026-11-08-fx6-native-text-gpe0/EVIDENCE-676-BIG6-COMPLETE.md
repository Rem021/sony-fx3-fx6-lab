# EVIDENCE 676：Big-6 Home 六格真实文案全部上屏

时间：2026-11-08（America/Los_Angeles）
运行：`runs/cp-bind-284326d4`
CPIO：`guest-hybrid-fx6kernel-capid-grmreal676-big6fix.cpio`
图像：`menu-670-big6-home.png`（整帧）、`menu-676-big6-top.png`、`menu-676-big6-bottom.png`

## 1. 结论

```
FX6_VSR676 done text=36 fill=14 icon=0 cells=6 skipN2=38 text_ok=36
gpe0 nz 1,322,858
```

**`text_ok` 从 24 提升到 36 —— 36 条字符串全部完成字形交付**，
六格的 12 条（6 标题 + 6 值）第一次真正画进了 gpe0。

## 2. 两个 bug 的修复（静态线定位）

### bug 1：`fx6_render_string_rid` 漏写 `+0x20c`

`fx6_render_string`（主循环用）写了 `font2`，但六格走的 `fx6_render_string_rid`
只写了 `+0x208`，`+0x20c` 保持 ctor 的 `-1`。`TextSprite` 在
`createTextProcessor` 里对 font2 为 `-1` 的路径会走空分支，导致
`setImageLoadCallback` 永远不会被调用 —— 这正是「36 次投递只回 24 次」的原因。

### bug 2：字体/布局参数取自按钮描述符

六格描述符（`No101..No106`，tag `0x042d58d0`）的 `+0x24 = 0x02006032`、
`+0x1c = 0x0200a02a` 是**按钮**的参数；`view_string`（tag `0x042d57f0`）需要的是
`0x0200600f / 0x0200600e / 0x0200a029` 这一组。把按钮参数塞进文本控件，
文本处理器同样无法完成布局。

修复后 `fx6_render_string_rid` 固定写入：

```c
*(uint32_t*)((char*)vs+0x208) = 0x0200600fU;   /* font   */
*(uint32_t*)((char*)vs+0x20c) = 0x0200600eU;   /* font2  */
*(uint32_t*)((char*)vs+0x210) = 0x0200a029U;   /* layout */
*(uint32_t*)((char*)vs+0xa14) = 0x0200600bU;   /* size   */
```

## 3. 六格最终画面（原生数据）

| 位置 | 标题 | 值 |
|---|---|---|
| 左上 `(96,72)` | `FPS` (`0x02005082`) | `Angle (Continuous)` (`0x020030ce`) |
| 上中 `(349,72)` | `Shutter` (`0x020050e8`) | `Shutter` (`0x02002fe1`) |
| 右上 `(607,72)` | `ISO` (`0x02004c32`) | `ISO/Gain` (`0x02005459`) |
| 左下 `(96,382)` | `ND Filter` (`0x02004288`) | `ND Filter` (`0x020054fd`) |
| 下中 `(349,382)` | `White Balance` (`0x02005689`) | `WB: A` (`0x02002934`) |
| 右下 `(607,382)` | `Base Look` (`0x020023f8`) | `S-Cinetone` (`0x02002464`) |

与之配套的证据行：

```
FX6_VSR676 text blit n=228 at 96,78
FX6_VSR676 text blit n=394 at 349,78
FX6_VSR676 text blit n=219 at 607,78
FX6_VSR676 text blit n=487 at 96,388
FX6_VSR676 text blit n=764 at 349,388
FX6_VSR676 text blit n=539 at 607,388
```

六格的矩形、顺序（`(y,x)` 排序）全部来自 `TABLE 0x2e9e210` 的 `No101..No106`；
标题/值 ResID 全部来自 appFw `.rodata` / `.data.rel.ro`；
底色用 `0x0200c008`（`color_cmn.uxc`），先画底色并立即 `processCommands(0)` 再画文字。

## 4. 中央网格

24 条原生文案 + 8 条原生填充/分隔线照常渲染，与六格互不遮挡：

```
FX6_VSR676 home presenter[...] S ... text=...   x24
FX6_VSR676 home presenter[...] F ... color=...  x8
```

## 5. 交付物

- `menu-670-big6-home.png` — **完整 Big-6 Home 帧**（六格 + 中央状态网格）
- `menu-676-big6-top.png` / `menu-676-big6-bottom.png` — 上下两排六格裁切
- `EVIDENCE-670-675-BIG6-HOME.md` — 修复前的阻塞点分析（5 次对照实验）
- `EVIDENCE-669-NS2-FIX-ALL-84.md` — ns2 补齐（84/84 解出）
