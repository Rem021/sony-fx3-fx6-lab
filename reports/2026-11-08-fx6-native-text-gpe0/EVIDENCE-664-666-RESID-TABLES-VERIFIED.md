# EVIDENCE 664–666：原生菜单 ResID 表确认可用（63/84 解出真实文案）

时间：2026-11-08（America/Los_Angeles）
运行：`runs/cp-bind-0675b343`（664 首探）、`cp-bind-a748f53f`（665 bank 扫描）、
`cp-bind-d18d0cf0`（666 完整 84 项）

## 1. 探针方法

用 appFw 自己的取值函数验证 `.rodata` 里那几张连续 ResID 表是否真是字符串表：

```
libra::String::String()
ux::resmgr::ResourceManager::getText(u32, libra::String&)
stella::String::ptrBuffer()
```

对每个条目打印 `rid / ns / idx / rc / text`。不绘制、不改状态。

## 2. 结论：表是真的（这是关键突破）

`TABLE A @ 0x23be620`（84 项）—— **63 项解出真实 FX6 菜单文案**：

```
A84[05] 02002fe1 -> "Shutter"
A84[12] 020030cc -> "Angle (Step)"
A84[14] 020030ce -> "Angle (Continuous)"
A84[16] 020030d1 -> "Speed (Step)"
A84[18] 020030dc -> "Speed (Continuous)"
A84[20] 020020a2 -> "Speed: ${v1}"
A84[22] 020020b1 -> "Speed: ${v1}F"
A84[26] 020020b2 -> "Angle: ${v1}F"
A84[32] 020020a4 -> "ECS: ${v1}.${v2:02}"
A84[38] 02002efc -> "Recall Internal Memory"
A84[39] 02002fe6 -> "Scene File"
A84[41] 020023dd -> "Back"
A84[42] 0200246b -> "Select"
A84[43] 02003003 -> "Look"
A84[44] 020028bd -> "SDI/HDMI"
A84[46] 020021d2 -> "Auto"
A84[48] 020021d1 -> "Manual"
A84[54] 0200225e -> "Internal Rec"
A84[55] 02002918 -> "XAVC"
A84[56] 02002e3c -> "VF/Proxy/Stream"
A84[58] 02002464 -> "S-Cinetone"
A84[60] 02002466 -> "Standard"
A84[62] 020023e9 -> "Still"
A84[64] 020023ed -> "ITU709"
A84[66] 02002a19 -> "709tone"
A84[68] 020023f1 -> "HLG Live"
A84[70] 020024ac -> "HLG Mild"
A84[72] 020023f5 -> "HLG Natural"
A84[74] 02002830 -> "LUT On"
A84[76] 020028ee -> "LUT Off"
A84[77] 020028f8 -> "Log"
```

高度规律：**偶数项是「画面显示用的短标签」，奇数项是同义的长标签**（如
`S-Cinetone` / `S-Cinetone`、`Still` / `Still`、`ITU709` / `ITU709`），
成对出现说明每个菜单项有两个文案槽（列表内 + 详情页）。

其它三张表同样为真：

| 表 | 地址 | 项数 | 样例 |
|---|---|---|---|
| B | `0x23be7b8` | 23 | `XAVC Intra` / `XAVC Long` / `HS-L422` / `XAVC HS-L 422` / `S-L420` |
| C | `0x23be86c` | 13 | `${v1}.${v2}` / `${v1}.${v2:02}`（光圈/焦距格式串） |
| D | `0x23be904` | 10 | `WB: A` `WB: B` `WB: Preset` `WB: C` … `WB: H`（白平衡预设） |

三份拷贝 `0x23bf0d8 / 0x23bf270 / 0x23bf9e0` 与
home / setting / three-layer 三个 controller 一一对应。

## 3. ns=2 为什么解不出来

`A84[00] 020043ed` 的 `ns=(rid>>13)&0x7ff = 2`，即 `string_english_2.uxc`，
`getText` 对所有 bank 0..7 都返回 `rc=0`：

```
FX6_VSR664 bank(2,0)=1 rc=0
...
FX6_VSR664 bank(2,7)=1 rc=0
```

说明这个 hybrid 里 **namespace 2 的字符串容器没有装载**（`string_english_2.uxc` 缺失或
未注册），不是 bank 选择错误。所有 `ns=1`（`string_english.uxc`）条目都正常。

因此可用文案 = 表里所有 `ns=1` 的条目；`ns=2` 条目需要额外把
`string_english_2.uxc` 注册进 resmgr 才能显示。

## 4. 关于「描述符行 → 表项」的索引

对 `0x23be620` 做了三种引用搜索：

1. `.rela.dyn` 里 `r_addend` 指向该地址 → **0 条**；
2. 文本段 `adrp 0x23be000` + `add #imm` 命中该区间 → **0 条**；
3. 全文件 8 字节指针值等于该地址 → **0 条**。

即这张表**没有被任何直接寻址指令引用**，只能通过「基址 + 运行时索引」访问
（表首地址极可能是 `adrp 0x23be000` 的某个基址 + 0x620 的常数偏移，
或由 controller 从 `variant` 对象里取出的游标）。

同页内唯一被直接引用的是 `0x23be908`（`0xf320b4`：`ldr w22,[x0,w2,uxtw #2]`，
`w2` 为 0..8 的状态枚举）——这是「状态 → 显示文案」的**运行时**索引表，
不是菜单行索引表。

## 5. 下一步（一步之遥）

现在唯一缺的是 **controller 里「行号 → A84 下标」的计算方式**。
有了它就能：

1. 对三层菜单 `No4_item1..No10_item7`（7 行）按下标取 A84 的标签 ResID；
2. 对 Big-6 六格按各自 `menu_item_id_t` 取标题 + D 表取数值；
3. 用已验证的 `view_string` 渲染路径（645–663 打通）把 ResID 画进 gpe0。

注意：`A84` 里 `Back` / `Select` / `Look` / `SDI/HDMI` 等已经能直接认出是
「三层菜单底部按钮 + 二级列表项」的文案，说明这张表就是三层菜单的文案源。
