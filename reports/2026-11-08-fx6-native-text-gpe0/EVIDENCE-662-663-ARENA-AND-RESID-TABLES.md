# EVIDENCE 662–663：大对象 arena 修好堆踩踏；原生菜单 ResID 表已定位

时间：2026-11-08（America/Los_Angeles）

## 1. 660 崩溃根因与 662 的修复（已验证）

静态线给出的类尺寸表解释了 660 的 `libstella+0x30064` 崩溃：

| 类 | tag | 对象大小 |
|---|---|---|
| view_string | `0x42d57f0` | `0x1388` |
| view_icon | `0x42d5a50` | `0x668` |
| view_fill | `0x42d5a40` | `0x308` |
| view_menu_item | `0x42d58d0` | `0x19788` |
| view_list_scroll_cursor_fixed | `0x42d5a20` | `0x239870`（2.28 MiB） |

660 用 `calloc(0x12000)` 装 `view_menu_item`（实际需要 `0x19788`），写穿堆元数据后才在
libstella 里延迟崩掉。

**662** 改为一块 32 MiB 的 `mmap` 私有 arena（`fx6_arena_alloc`），按类尺寸切片：

```
FX6_VSR662 arena=0x7f7e000000 size=2000000
FX6_VSR662 setting main[06] M No106_BUTTON_BOTTOM_RIGHT (654,425,164,72) text=020023da
FX6_VSR662 setting main[07] M No105_BUTTON_BOTTOM_CENTER (398,425,164,72) text=020023da
FX6_VSR662 setting main[08] M No103_BUTTON_TOP_RIGHT  (654,80,164,72) text=020023da
FX6_VSR662 setting main[09] M No102_BUTTON_TOP_CENTER (398,80,164,72) text=020023da
FX6_VSR662 done text=0 fill=0 icon=0 item=4 skipN2=0 text_ok=0
```

**`APPFW_SEGV` 出现次数 = 0**，4 个 `view_menu_item` 全部构造并跑完 onDrawNotice。
堆踩踏问题彻底解决。

但该页仍无像素：`view_menu_item` 的 `onDrawNotice`（`0xc35358`）在
`+0x200` 的 16 项 style 表里分发到 `0xc347b0` 行渲染器，行渲染器最终走的是
**GDS drawImage**（icon/文本图）而不是 `fillRect`，其图像槽位需要
`+0x1d0/+0x1d8/+0x1e0/+0x228` 与子控件链表齐备；当前只设了 caption，图像请求没有发起，
所以既没有 `FX6_NEXT_FILL` 也没有 `drawImage`。663 已回退到 `view_string` 方案保持基线。

## 2. 原生菜单 ResID 映射表已找到（`.rodata` 连续表）

扫描 `appFw.so` 的 `.rodata` 里连续 8 个以上的 ResID，发现 4 组关键表：

| 地址 | 项数 | 首项 |
|---|---|---|
| `0x23be620` | 84 | `0x020043ed` |
| `0x23be7b8` | 23 | `0x02005261` |
| `0x23be86c` | 13 | `0x02003045` |
| `0x23be904` | 10 | `0x0200335a` |
| `0x23bf0d8` / `0x23bf270` / `0x23bf9e0` | 84 / 23 / 84 | 同上（三份拷贝，对应 home / setting / three-layer 三个 controller） |

`0x23be620` 的 84 项按「标题, 值」成对排列，例如：

```
020043ed 02005082   ← 标题 + "值格式"型
02004d96 02002fe1
020030cc 02002fe1
...
02005292 020023dd
0200246b 02003003
```

这正好是「菜单项标题 ResID + 其数值/格式 ResID」的映射，且三份拷贝与
`procam_big6_menu_home_controller` / `setting_controller` / `three_layer_controller`
一一对应。

## 3. Big-6 六格的 id → ResID 小表

`0xf320b4` 的代码：

```
adrp x0, 0x23be000 ; add x0, x0, #0x908
ldr  w22, [x0, w2, uxtw #2]      ; w2 = 状态枚举 0..8
```

即 `0x23be908` 处的 9 项 u32 表：

```
02002934 02002896 02002f08 02002919 02002cab 02002c82 02002c88 02002caf 02002ca3
```

这是「状态索引 → 显示字符串 ResID」的映射，用于 Big-6 六格里某一格的取值显示。

## 4. 容器构造函数（接管绘制的正确入口）

`0xc870cc`：`container(desc_array, count)`，逐条 `desc += 0x48`，用
`0xc87054(vptr)` 做 RTTI 白名单过滤，通过后把 `desc[0]` 与 `desc+0x3a`（row id）
存进容器：

```
c87120: ldr x0,[x20]              ; desc+0x00 = tag
c87124: ldp x1,x2,[x0]            ; tag 里的 {vtable, creator_idx}
c8712c: bl  0xc87054              ; RTTI allow-list
c87144: str desc[0] -> container+8+16*i
c87150: ldrh w1,[x20,#0x3a]       ; row id
c87150: str w1 -> container+0x10+16*i
```

调用点 `0xdd74d4`（三层菜单）：`x2 = 0x23`（35 项）——与 `0x2ea02f8` 的 35 项吻合，
说明**三层页就是 35 项描述符 + 这张容器**。

## 5. 结论与下一步

- 堆踩踏：已解决（mmap arena + 正确类尺寸）。
- 六格与三层菜单的**标题/数值 ResID 表已到手**（`0x23be620` 等三份、`0x23be908`）。
- 剩下的一步是：把「描述符行 → 该行对应 ResID 表项」的索引关系接上，
  再用已验证的 `view_string` 渲染路径把 ResID 画出来（不经过 `view_menu_item`
  的 GDS 图像链路，那条链路需要完整子控件树）。
