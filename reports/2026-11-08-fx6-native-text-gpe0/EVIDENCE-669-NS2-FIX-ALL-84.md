# EVIDENCE 669：补齐 `string_english_2.uxc` 后 ResID 表 84/84 全部解出

时间：2026-11-08（America/Los_Angeles）
运行：`runs/cp-bind-f439b898`
CPIO：`guest-hybrid-fx6kernel-capid-grmreal669-ns2.cpio`
（430,411,936 B，`sha256 d2411e0a…`）

## 1. 根因与修法

`global.xdb` 里登记了两个字符串容器：

```
string_english.uxc
string_english_2.uxc      ← 之前 guest CPIO 里没有这个文件
```

旧 CPIO 只带 `string_english.uxc / _f / _g`，所以所有 `ns=2` 的 ResID
（`(rid>>13)&0x7ff == 2`）都 `getText` 失败；665 的 bank 0..7 全扫也证明不是 bank 问题。

669 用新写的 `cpio_add_member.py`（流式复制 + 在 TRAILER 前插入一个成员）
把 `usr/share/app/string_english_2.uxc`（118,676 B）补进 guest。

**结果：A84 从 63/84 → 84/84 全部解出。**

## 2. A84（`0x23be620`）完整解出内容 —— 这是 Shutter 设置页的条目表

```
[00] Frequency          [01] FPS
[02] Frame Rate         [03] FPS
[04] Shutter Angle      [05] Shutter
[06] Shutter Speed      [07] Shutter
[08] ECS Frequency      [09] Shutter
[10] Mode               [11] Shutter
[12] Angle (Step)       [14] Angle (Continuous)
[16] Speed (Step)       [18] Speed (Continuous)
[20] Speed: ${v1}       [22] Speed: ${v1}F      [24] Speed: 1.2F
[26] Angle: ${v1}F      [28] Angle: ${v1}.${v2:02}
[32] ECS: ${v1}.${v2:02} [34] ECS: ${v1}.${v2:01} [36] ECS: ${v1}
[38] Recall Internal Memory   [39] Scene File
[40] Off                [41] Back
[42] Select             [43] Look
[44] SDI/HDMI           [46] Auto            [48] Manual
[50] (No File)          [52] (No LUT)
[54] Internal Rec       [55] XAVC            [56] VF/Proxy/Stream
[58] S-Cinetone         [60] Standard        [62] Still
[64] ITU709             [66] 709tone
[68] HLG Live           [70] HLG Mild        [72] HLG Natural
[74] LUT On             [76] LUT Off         [77] Log
[78..83] ${v1:02} 类格式串
```

**规律确认**：偶数项 = 行内短标签，奇数项 = 同义长标签/分类名。
`[40..77]` 是 `Off / Back / Select / Look / SDI-HDMI / Auto / Manual / (No File) /
(No LUT) / Internal Rec / XAVC / S-Cinetone / … / Log` —— 这是**色彩/输出设置页**
的完整选项表，不是 Big-6 六格标题表。

## 3. 本轮渲染

三层菜单页（668 的渲染路径 + 新增 icon 分支）：

```
FX6_VSR669 three-layer[...] S ... text=...      x8
FX6_VSR669 three-layer[...] F ... color=...     x15
FX6_VSR669 three-layer[...] I ... img=...       x1
FX6_VSR669 done text=8 fill=15 icon=1 text_ok=8
gpe0 nz 1,735,388
```

`text_ok=8`（668 是 6）说明补齐 ns2 后，之前解不出文案的行现在也能出字形。
icon 分支首次跑通（`No2_Backiconinthesecondlayer`，`img=02000154`）。

## 4. 关于 `0x23be8e0` 表（静态线新增）

前 19 项结构为：

```
[i]   0x02000571 (ns0, image)      0x02003307 (ns1, "2.0x")
...
[9]   0x0200335a (ns1)  ← 其后接 WB: A..H 连续 9 项
```

即「**图标 ResID（ns0, image_00_169.uxc）+ 文案 ResID（ns1）**」成对，
第 10 项起转为 10 个连续的 WB/曝光补偿文案。与 666 解出的 D 表
（`WB: A`…`WB: H`、`WB: Preset`）吻合。

## 5. 六格仍缺的那一环

Big-6 六格（`No101..No106`，见 659）的标题 **不在这两张表里**：
A84 是 Shutter/色彩页条目，D 是 WB 预设，`0x23be8e0` 是图标+曝光补偿。
六格标题应来自 controller 里按 `menu_item_id_t` 的另一张表。

已排除的定位手段（全部返回 0 条引用）：`.rela.dyn` 的 `r_addend`、
`adrp+add` 直接寻址、全文件 8 字节指针。说明这些表只能通过
「基址寄存器 + 运行时索引」访问，索引值由 controller 计算。

## 6. 交付物

- `menu-669-three-layer.png` — 三层页（8 条真实文案 + 15 条原生填充 + 1 图标）
- `EVIDENCE-668-THREE-LAYER-REAL-TEXT.md` — 首版三层页真实文案
- `EVIDENCE-664-666-RESID-TABLES-VERIFIED.md` — 表验证（63/84 阶段）
- `work/fx6-385-17b9f-calltrace-20261107/cpio_add_member.py` — 新工具，可向 CPIO 追加成员
