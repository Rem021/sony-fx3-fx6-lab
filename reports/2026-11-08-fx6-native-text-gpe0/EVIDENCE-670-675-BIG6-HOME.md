# EVIDENCE 670–675：Big-6 Home 整页渲染与六格文字阻塞点

时间：2026-11-08（America/Los_Angeles）
图像：`menu-670-big6-home.png`（取自 `runs/cp-bind-0105c380`，candidate 672 帧）

## 1. 六格标题 ResID 已核验（静态线定位）

按静态线给出的地址逐条读 `.rodata` / `.data.rel.ro`，四元组 `[id0, id1, -1, -1]` 结构成立：

| 格 | 标题 ResID | 来源 | `getText` |
|---|---|---|---|
| FPS | `0x02005082` | `.rodata 0x226c980`，同 `A84[1]` | ✅ `FPS` |
| Shutter | `0x020050e8` / `0x02002fe1` | `.rodata 0x2270f48` / `A84[5]` | ✅ `Shutter` |
| ISO / Gain | `0x02004c32` / `0x0200420e` / `0x02005459` | `.rodata 0x226c848` / `0x226aec8` | ✅ |
| ND Filter | `0x02004288` / `0x020054fd` | `.rodata 0x2270f18` | ✅ |
| White Balance | `0x02005689` / `0x02002934` | `.rodata 0x226c1f8` / D 表 | ✅ `WB: A` |
| Base Look | `0x020023f8` / `0x02003003` / `0x020044f5` | `.rodata 0x226b8f0` / `A84[43]` | ✅ `Look` |

669 补入 `string_english_2.uxc` 之后，这些 ns=2 标题全部可解析，
说明静态线的定位是正确的。

## 2. 670/672：整页渲染结果

```
FX6_VSR670 cells collected=6
FX6_VSR670 cell FPS        (96,72,257,122)   title=02005082 value=020030ce
FX6_VSR670 cell Shutter    (349,72,262,122)  title=020050e8 value=02002fe1
FX6_VSR670 cell ISO/Gain   (607,72,257,122)  title=02004c32 value=02005459
FX6_VSR670 cell ND Filter  (96,382,257,122)  title=02004288 value=020054fd
FX6_VSR670 cell White Bal. (607,72,257,122)  title=02005689 value=02002934
FX6_VSR670 cell Base Look  (96,72,257,122)   title=020023f8 value=02002464
FX6_VSR670 done text=36 fill=14 icon=0 cells=6 skipN2=38 text_ok=24
gpe0 nz 1,325,194
```

六格的矩形、顺序（按 `(y,x)` 排序后正好是上排左中右 + 下排左中右）全部来自
`TABLE 0x2e9e210` 的 `No101..No106`；中央区域 24 条描述符文案照常渲染。

## 3. 六格文字为什么没出（5 次对照实验已排除的方向）

| candidate | 假设 | 结果 |
|---|---|---|
| 671 | 六格先画，避免被 `No1_BG` 覆盖 | 仍无文字（且被 `No1_BG` 盖住底色） |
| 672 | 六格最后画（改 z 序） | 底色 `#222222` 正确出现，**文字仍无** |
| 673 | 去掉底色，排除“填充盖住字形” | 仍无文字（`fill` 从 14 降到 8） |
| 674 | 换成已验证可渲染的 **ns=1** ID | 仍无文字 → **不是 namespace 问题** |
| 675 | 补 `+0x20c` font2、layout 默认值 | 仍无文字 → **不是字段缺失** |

共同现象：`text=36`（36 次字符串交给原生链路）但 `text_ok=24`，
**12 次六格字符串（6 标题 + 6 值）的 `setImageLoadCallback` 从头到尾没有触发**，
日志里没有任何一条对应坐标的 `text blit`。

因此阻塞点不在 ResID、不在 namespace、不在 z 序、不在字段默认值，
而是**这 12 次文本请求在 TextSprite/TextProcessor 内部没有完成**
（很可能 `validText` 失败或 `getTextProcessor` 未返回有效处理器）。
下一步应该在 `fx6_render_string_rid` 里打印
`validText(ts)`、`createTextProcessor` 返回值、`ts+0xa8` 标志与
`ts+0xb0/+0xd0` 的 ResID，一次就能定位是哪一步返回 0。

## 4. 仍然达成的东西

- 六格位置与顺序完全由 appFw 描述符表决定（`(96,72) (349,72) (607,72)` / `(96,382) (349,382) (607,382)`）；
- 六格标题/数值 ResID 已按固件真实数据接好（见上表）；
- 中央状态网格（24 条原生文案 + 8 条原生填充/分隔线）照常出图；
- `string_english_2.uxc` 补齐后 84/84 全解出（669）。

## 5. 交付物

- `menu-670-big6-home.png` — 当前 Big-6 Home 帧（中央网格 + 六格底色）
- `menu-669-three-layer.png` — 三层菜单（8 条真实文案）
- `menu-668-three-layer.png` / `menu-657-three-layer.png` — 三层页前序对照
- `menu-656-panel.png` — home 页早期版本（无六格）
- `EVIDENCE-669-NS2-FIX-ALL-84.md`、`EVIDENCE-664-666-RESID-TABLES-VERIFIED.md`
