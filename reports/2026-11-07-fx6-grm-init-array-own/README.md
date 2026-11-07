# FX6 GRM init_array / own_ 静态追踪

日期：2026-11-07（本机 PT 2026-11-06）  
范围：`libuxengine`/`libux_core` 的 `.init_array`/`.fini_array`、`GraphicsSystemInterface::own_`（0x486f0）写入点、`InitializeIF` vtable 目标  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未写代码；未编译；未跑 pmemsave/解析器；未触碰用户三问**

## 1. 结论先行

1. **`.init_array`/`.fini_array` 没有直接引用 `GraphicsEngine` ctor（0x8350c）或 `sys_createApplication`（0x82854）。**
   - `libuxengine` `.init_array` 8 项：`0x74b40, 0x744e0, 0x7451c, 0x74640, 0x74690, 0x7481c, 0x74834, 0x749f4`；
   - `libux_core` `.init_array` 6 项：`0x23eb0, 0x23cc0, 0x23d00, 0x23d44, 0x23d88, 0x23d94`；
   - 两库 `.fini_array` 各 1 项：`libuxengine 0x74af8`、`libux_core 0x23e68`；
   - 均不是 0x8350c/0x82854/0x2764c。
2. **`GraphicsSystemInterface::own_`（0x486f0）没有静态写入点。**
   - `.text` 内没有 `str/stp/stur` 到 `#0x6f0`/`#0x6e8`；
   - 没有引用 `InitializeIF` 所用的 GOT 0x460e50；
   - 没有 relocation 指向 0x486f0；
   - `own_` 是 BSS，静态为零。
3. **`InitializeIF` 的 vtable 目标“未设置”。**
   - `InitializeIF` 的逻辑是：`own_` → object → vtable → `vtable[0]`；
   - 但 `own_` 没有静态赋值；若此时调用，`ldr x5,[own_]` 得到 0，下一句 `ldr x4,[x5]` 会空指针，根本到不了 vtable；
   - 若假设 `own_` 指向 `GraphicsSystemCore`，其 vptr=0x45ba8，`vtable[0]` 是 `GraphicsSystemCore::Initialize`（0x27ef0）；但这只是**条件性推断**，没有对象赋值证据。
4. **这进一步支持“`InitializeIF`/`sys_createApplication` 未被使用”的假设。**
   - 没有 init_array 入口；
   - 没有 own_ 赋值；
   - 没有外部 `U`；
   - 若被调用会先崩在 own_ 空指针。
5. 仍不是运行时证明：`.init_array` 项内部可能间接调用；动态加载/外部代码可能写 BSS；需要运行时断点确认。

## 2. `.init_array` / `.fini_array` 实测

### 2.1 `libuxengine`

```text
DT_INIT_ARRAY   0xbc260
DT_INIT_ARRAYSZ 0x40   (8 entries)
DT_FINI_ARRAY   0xbc2a0
DT_FINI_ARRAYSZ 0x8    (1 entry)
```

`.init_array` 条目：

```text
0x74b40
0x744e0
0x7451c
0x74640
0x74690
0x7481c
0x74834
0x749f4
```

`.fini_array`：

```text
0x74af8
```

RELATIVE reloc addends 与 raw 值一致；没有 0x8350c/0x82854。

### 2.2 `libux_core`

```text
DT_INIT_ARRAY   0x45710
DT_INIT_ARRAYSZ 0x30   (6 entries)
DT_FINI_ARRAY   0x45740
DT_FINI_ARRAYSZ 0x8    (1 entry)
```

`.init_array` 条目：

```text
0x23eb0
0x23cc0
0x23d00
0x23d44
0x23d88
0x23d94
```

`.fini_array`：

```text
0x23e68
```

没有 0x2764c（InitializeIF）或 0x27ef0（GraphicsSystemCore::Initialize）。

### 2.3 结论

- `GraphicsEngine` ctor（0x8350c）不在 `.init_array`；
- `sys_createApplication`（0x82854）不在 `.init_array`/`.fini_array`；
- `InitializeIF`（0x2764c）不在 `.init_array`/`.fini_array`；
- 这些 init/fini 函数本身是静态构造/析构；不排除它们内部间接调用，但没有任何直接指针证据。

## 3. `own_` 写入点

### 3.1 `own_` 符号

```text
00000000000486f0 B ux::core::GraphicsSystemInterface::own_
```

`InitializeIF`（0x2764c）使用 GOT 0x460e50：

```text
adrp x4, #0x46000
ldr  x4, [x4, #0xe50]   ; GOT -> own_
ldr  x5, [x4]           ; own_ 值（object）
ldr  x4, [x5]           ; vtable
ldr  x6, [x4]           ; vtable[0]
...
br   x6
```

### 3.2 扫描结果

在 `libux_core` `.text`：

- `str/stp/stur` 到 `#0x6f0`/`#0x6e8`：**0 个**；
- `adrp #0x46000` + `ldr #0xe50`：**0 个**（除 `InitializeIF` 自身外无引用）；
- relocation 指向 0x486f0：**0 个**；
- `nm -D` 没有 `own_` 的外部 `U`；
- `own_` 在 BSS，静态初始为零。

### 3.3 解释

`own_` 没有静态写入点，意味着：

- 如果 `InitializeIF` 被调用，`x5 = [own_] = 0`，`ldr x4,[x5]` 会访问地址 0；
- 也就是说，**在静态可见的初始化流程中，`InitializeIF` 是不可用的/未被设置的**；
- 它要么从未被调用，要么由运行时动态代码（不在当前静态扫描范围）赋值。

## 4. vtable 目标

`GraphicsSystemCore` vtable：

```text
vtable for ux::core::GraphicsSystemCore = 0x45b98
0x45b98: offset-to-top (0)
0x45ba0: typeinfo pointer (reloc -> _ZTIN2ux4core18GraphicsSystemCoreE)
0x45ba8: GraphicsSystemCore::Initialize        (0x27ef0)
0x45bb0: GraphicsSystemCore::Finalize
0x45bb8: GraphicsSystemCore::SampleRunLoop
0x45bc0: GraphicsSystemCore::SampleProcessSystemMessage
...
```

如果 `own_` 指向 `GraphicsSystemCore` 对象，其 vptr 通常是 `0x45ba8`，`vtable[0]` = **`GraphicsSystemCore::Initialize` (0x27ef0)**。

但：

- `own_` 没有写入点；
- 没有对象被赋给 `own_`；
- 所以这个 0x27ef0 只是**条件性目标**，不是实际可达目标。

**结论**：`InitializeIF` 的 vtable 目标在当前静态图里**未设置/不可达**；不能声称它会调用 0x27ef0。只有在运行时 `own_` 被赋为 `GraphicsSystemCore` 对象后才成立。

## 5. 对“未使用”假设的意义

前一份报告已确认：

- `sys_createApplication` 无 `.text` xref、无外部 U；
- `InitializeIF` 无 `.text` xref、无外部 U；
- `sys_initialize`/`sys_getInstance`/ctor 都不创建 framebuffer。

本报告补充：

- `.init_array`/`.fini_array` 也没有它们；
- `own_` 没有赋值，`InitializeIF` 即使被调用也会先空指针；
- 因此“`InitializeIF`/`sys_createApplication` 未被使用”得到更强的静态支持。

但仍有缺口：

- `.init_array` 函数内部可能间接调用（没有逐函数全反汇编）；
- 动态加载器/外部代码可能写 `own_`；
- 运行时可能通过 **另一个模块** 设置 vtable/own_。

## 6. 运行时验证方案（仅设计，不执行）

```text
libux_core:
  InitializeIF                 0x2764c
  GraphicsSystemCore::Initialize 0x27ef0
  own_ 地址                     0x486f0

libuxengine:
  sys_createApplication        0x82854
  GraphicsEngine ctor          0x8350c

libgrm:
  GRM_fbrmInitialize           0x23374
  FrameBuffer::update          0x23160
  GRM_screenGetOnBitmap        0x2368c
```

判定：

- 断点 `InitializeIF` 命中前，先读 `[0x486f0]`；若为 0，确认 own_ 未初始化；
- 若 `InitializeIF` 未命中、`GraphicsSystemCore::Initialize` 未命中、`GRM_fbrmInitialize` 未命中 → 入口未调用；
- 若 `sys_createApplication` 命中 → 读 `w1/w2`；
- 若 `GRM_fbrmInitialize` 命中 → 读 `w0/w1/w2`；
- 若 `GraphicsEngine` ctor 命中 → 说明静态 xref 漏了 `.init_array`/动态路径，继续 backtrace。

**本轮未执行。**

## 7. 实测 vs 推断 vs 缺失

### 静态实测

- `libuxengine`/`libux_core` init/fini 数组条目与 reloc；
- 没有 0x8350c/0x82854/0x2764c 直接条目；
- `own_` 0x486f0，BSS；
- `.text` 无 `str/stp #0x6f0`、无 GOT 0x460e50 引用、无 relocation；
- `GraphicsSystemCore` vtable 0x45b98，vtable[0] 条目 0x45ba8 -> `Initialize` 0x27ef0（符号 reloc）。

### 推断

- `own_` 从未被静态赋值，`InitializeIF` 不可用/未使用；
- `GraphicsSystemCore::Initialize` 是条件性 vtable 目标，不是实际可达目标；
- init_array 项内部没有逐函数反汇编，不能 100% 排除间接调用。

### 缺失

- `.init_array` 函数体内部是否间接调用 ctor/sys_createApplication；
- 是否有其他库/动态代码写 `own_`；
- 运行时 `[0x486f0]` 实际值；
- 运行时 `GRM_fbrmInitialize` 是否命中；
- 实际 w/h/format。

## 8. 边界

- 未启动/未改动任意 VM；
- 未解包/修改 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未写代码、未编译、未运行；
- 未跑 pmemsave/解析器；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）。

## 9. 下一步

1. 静态：逐个反汇编 init_array 的 14 个函数，检查是否间接调用 `sys_createApplication`/`GraphicsEngine` ctor；当前只验证了数组条目本身。
2. 静态：查 `own_` 是否被 **`memcpy`/`memset`** 或外部符号写入；当前没有直接 store。
3. 运行时（需批准）：断点 `InitializeIF`/`GraphicsSystemCore::Initialize`，先读 `[0x486f0]`；这是判断“是否使用”的最快路径。

## 10. 续研：14 个 init_array 函数与 own_ memcpy/memset

时间：2026-11-07 15:30 PT（巡查 07:23）。本节为追加，不改变前文结论。

### 10.1 逐项结论

统一扫描结果：

- 14 个函数中，**没有任何直接 `bl`/`b` 到** `0x82854`（sys_createApplication）、`0x8350c`（GraphicsEngine ctor）、`0x2764c`（InitializeIF）；
- **没有 PLT 调用**到上述目标；
- **没有 `adrp/add`** 组成上述目标函数指针；
- 可见指令范围内**没有 `blr`**（间接调用）；
- 但部分函数以 tail `b` 进入 helper，helper 未展开；这些标为“无法判定”。

| # | 库 | init 入口 | 直接目标 | 可见调用/尾跳 | 结论 |
|---:|---|---|---|---|---|
| 1 | libuxengine | `0x74b40` | 无 | tail `b 0x74ab8` | **无法判定**（tail helper 未展开） |
| 2 | libuxengine | `0x744e0` | 无 | `bl 0x70050`，tail `b 0x71e50` | 不调用（直接/PLT）；间接未完全排除 |
| 3 | libuxengine | `0x7451c` | 无 | 多次 `bl 0x704c0` | 不调用（直接/PLT） |
| 4 | libuxengine | `0x74640` | 无 | 两次 `bl 0x724f0` | 不调用（直接/PLT） |
| 5 | libuxengine | `0x74690` | 无 | `bl 0x72b40` | 不调用（直接/PLT） |
| 6 | libuxengine | `0x7481c` | 无 | 无调用 | 不调用（函数体内无调用） |
| 7 | libuxengine | `0x74834` | 无 | `bl 0x72b40` | 不调用（直接/PLT） |
| 8 | libuxengine | `0x749f4` | 无 | `bl 0x724f0`，tail `b 0x70a20` | **无法判定**（tail helper 未展开） |
| 9 | libux_core | `0x23eb0` | 无 | tail `b 0x23e28` | **无法判定**（tail helper 未展开） |
| 10 | libux_core | `0x23cc0` | 无 | `bl 0x23bd0`，tail `b 0x22ac0` | **无法判定**（tail helper 未展开） |
| 11 | libux_core | `0x23d00` | 无 | `bl 0x22480`，tail `b 0x22480` | **无法判定**（tail helper 未展开） |
| 12 | libux_core | `0x23d44` | 无 | 无调用 | 不调用（函数体内无调用） |
| 13 | libux_core | `0x23d88` | 无 | tail `b 0x228f0` | **无法判定**（tail helper 未展开） |
| 14 | libux_core | `0x23d94` | 无 | `bl 0x22eb0`，tail `b 0x22eb0` | **无法判定**（tail helper 未展开） |

计数：

```text
不调用（直接/PLT）：7 项
无法判定（tail/helper 未展开）：7 项
调用目标：0 项
```

**注意**：这里的“无法判定”不是“有调用证据”，而是“没有直接/PLT 证据，但 tail helper 没逐层展开”；结合前一节的全局 xref（0x82854/0x8350c/0x2764c 在 `.text` 内无直接引用），这些 init 函数**直接调用目标的可能性为 0**，只剩间接 `blr`/helper 内部调用的可能性。

### 10.2 memcpy/memset 与 own_

PLT 统计：

```text
libuxengine:
  memcpy PLT 0x6f000
  memset PLT 0x70650
  调用点 6 个（2 memcpy + 4 memset）

libux_core:
  memcpy PLT 0x21390
  memset PLT 0x21d90
  调用点 15 个
```

检查：

- 两库 `.text` 中 `adrp/add` 到 `own_`（0x486f0）：**0 个**；
- 两库 `.text` 中 `str/stp/stur` 到 `#0x6f0`/`#0x6e8`：**0 个**；
- 两库 `.text` 中引用 `InitializeIF` 的 GOT 0x460e50：**0 个**（除 InitializeIF 自身）；
- `memcpy`/`memset` 调用点没有任何一个的目标地址是 `own_`；
- 外部 `U GraphicsSystemInterface::own_`：未发现；
- `own_` 仍是 BSS，静态为零；BSS 由 loader 清零，不是代码写入。

**结论：`own_` 静态无写入点。** 不能排除运行时动态代码/其他模块写 BSS，但当前两库的静态代码没有写入。

### 10.3 对 InitializeIF 的影响

- `own_` 无静态写入 → `InitializeIF` 的 `x5=[own_]` 为 0；
- `ldr x4,[x5]` 会先空指针；
- 因此 `InitializeIF` 在静态可见流程里**不可用**；
- `GraphicsSystemCore` vtable[0]=0x27ef0 仍是**条件性目标**，没有对象被赋给 `own_`。

### 10.4 本节实测 vs 推断 vs 缺失

**实测**：

- 14 个 init 函数的入口反汇编；
- 无直接 `bl/b`/PLT/adrp-add 到三目标；可见范围内无 `blr`；
- 7 项 tail helper 未展开，标为无法判定；
- memcpy/memset 调用点数与目标检查；
- own_ 无 adrp/add/store/GOT 引用、无外部 U。

**推断**：

- init 函数不是 framebuffer 初始化入口；
- own_ 从未被静态赋值，InitializeIF 未使用；
- 目标 0x27ef0 只是条件性 vtable 目标。

**缺失**：

- 7 个 tail helper 的完整函数体；
- 运行时 `[0x486f0]` 值；
- 动态加载/外部模块是否写 own_；
- 运行时 `GRM_fbrmInitialize` 是否命中。

### 10.5 运行时待批准方案（未执行）

```text
断点 InitializeIF 0x2764c
先读 [0x486f0]（own_）
若为 0：确认 own_ 未初始化
再断 GraphicsSystemCore::Initialize 0x27ef0
再断 GRM_fbrmInitialize 0x23374
```

本轮**未执行**任何运行时步骤。

## 11. 续研：7 个 tail helper 逐项

时间：2026-11-07 16:00 PT（巡查 07:23）。本节为追加，不改变前文结论。

### 11.1 逐项表

7 个 helper 都是 **`br`/PLT 型**（不是 `bl`/`blr`）；没有 `tail b` 再跳。逐个解析如下：

| # | 库 | helper | 结构 | 解析结果 | 结论 |
|---:|---|---|---|---|---|
| 1 | libuxengine | `0x74ab8` | `br x2`，GOT `0xc1fc0` | symbol `_ITM_registerTMCloneTable` | **不调用三目标**（间接到 ITM 表） |
| 2 | libuxengine | `0x70a20` | `br x17`，PLT `0xc2e38` | `ux::core::Vector2::Vector2()` | **不调用三目标** |
| 3 | libux_core | `0x23e28` | `br x2`，`.data.rel.ro 0x460fa0` | 数组 `0x486b0..0x486b0` 长度 0；`br` 不可达 | **不调用三目标**（空析构表，GOT 未读取） |
| 4 | libux_core | `0x22ac0` | `br x17`，PLT `0x470bf8` | `__cxa_atexit` | **不调用三目标** |
| 5 | libux_core | `0x22480` | `br x17`，PLT `0x4708d8` | `ux::core::Color::Color(unsigned char, ...)` | **不调用三目标** |
| 6 | libux_core | `0x228f0` | `br x17`，PLT `0x470b10` | `ux::core::ID::ID()` | **不调用三目标** |
| 7 | libux_core | `0x22eb0` | `br x17`，PLT `0x470df0` | `ux::core::Vector2::Vector2(float, float)` | **不调用三目标** |

计数：

```text
不调用三目标：7 项
无法判定：0 项
调用三目标：0 项
```

### 11.2 细节

- `0x74ab8`：
  - 计算 `0xc4ba8` 附近的数组长度，若为 0 返回；
  - 从 GOT `0xc1fc0` 取函数指针，`br x2`；
  - GOT 符号为 `_ITM_registerTMCloneTable`，不是 `GraphicsEngine`/`sys_createApplication`/`InitializeIF`。
- `0x70a20`：
  - 标准 PLT stub；
  - 目标 `ux::core::Vector2::Vector2()`；
  - 不是三目标。
- `0x23e28`：
  - 计算 `0x486b0 - 0x486b0 = 0`，`cbz x1, 0x23e60` 直接到 `ret`；
  - `0x460fa0` 实际在 `.data.rel.ro`，不在 `.got`；无 reloc/符号；
  - 由于长度 0，`ldr x2,[0x460fa0]`/`br x2` **不可达**；
  - 分类改为“不调用三目标”。
- `0x22ac0`：PLT `__cxa_atexit`，不是三目标。
- `0x22480`：PLT `ux::core::Color::Color(unsigned char, ...)`，不是三目标。
- `0x228f0`：PLT `ux::core::ID::ID()`，不是三目标。
- `0x22eb0`：PLT `ux::core::Vector2::Vector2(float, float)`，不是三目标。

### 11.3 对“InitializeIF/sys_createApplication 未使用”的影响

- 7 个 helper 中 **0 个调用三目标**；
- 7 个均可解释为静态初始化/析构/工具函数（`0x23e28` 是空析构表，GOT 未读取）；
- 没有 framebuffer 初始化入口；
- 结合 §10 的 14 个 init 函数（无直接/PLT/adrp-add 到三目标），**没有新增证据表明 `InitializeIF`/`sys_createApplication` 被调用**；
- “未使用”假设继续得到支持，但仍不是运行时证明。

### 11.4 本节实测 vs 推断 vs 缺失

**实测**：

- 7 个 helper 的入口反汇编；
- PLT 名称（`Vector2`/`Color`/`ID`/`__cxa_atexit`）；
- GOT `0xc1fc0` 符号 `_ITM_registerTMCloneTable`；
- `0x23e28` 的数组长度 0；`0x460fa0` 在 `.data.rel.ro`、无符号/无 reloc；
- 0 个 helper 直接/间接落到三目标地址。

**推断**：

- `0x23e28` 是空析构表；`0x460fa0` 未被读取；
- 7 个 helper 都是静态初始化/析构链，不是 UI/framebuffer 入口。

**缺失**：

- `0x460fa0` 的具体用途（不影响结论）；
- 运行时 `[0x486f0]` 值；
- 运行时 `GRM_fbrmInitialize` 是否命中；
- 仍未执行任何运行时断点。

### 11.5 运行时待批准方案（未执行）

沿用 §10.5：

```text
断点 InitializeIF 0x2764c
先读 [0x486f0]（own_）
若为 0：确认 own_ 未初始化
再断 GraphicsSystemCore::Initialize 0x27ef0
再断 GRM_fbrmInitialize 0x23374
```

本轮**未执行**任何运行时步骤。

## 12. §12：0x23e28 的 0x460fa0 与 0x486b0 数组

时间：2026-11-07 16:30 PT。本节只补 §11 的最后一个缺口，不再扩展。

### 12.1 结论

1. **`0x23e28` 的数组长度是 0。**
   反汇编：
   ```text
   0x23e28: adrp x1, #0x48000
   0x23e2c: adrp x0, #0x48000
   0x23e30: add  x1, x1, #0x6b0
   0x23e34: add  x0, x0, #0x6b0
   0x23e38: sub  x1, x1, x0      ; = 0
   0x23e3c: asr  x1, x1, #3
   0x23e40: add  x1, x1, x1, lsr #63
   0x23e44: asr  x1, x1, #1
   0x23e48: cbz  x1, 0x23e60     ; 必跳
   0x23e4c: adrp x2, #0x46000
   0x23e50: ldr  x2, [x2, #0xfa0]
   0x23e54: cbz  x2, 0x23e60
   0x23e58: br   x2              ; 不可达
   0x23e60: ret
   ```
   `0x23e60` 是 `ret`；因此 `0x460fa0` 的 load 和 `br x2` **永远不会执行**。

2. **`0x460fa0` 实际在 `.data.rel.ro`，不在 `.got`。**
   - `.data.rel.ro`：`0x45750 + 0x11f0`，覆盖 `0x45750..0x46940`；`0x460fa0` 在其中；
   - `.got`：`0x46c40..0x46fe8`；
   - `.got.plt`：`0x46fe8..0x484f8`；
   - `.rela.dyn`/`.rela.plt` 没有指向 `0x460fa0` 的条目；
   - 没有附近符号；`.dynsym`/`.symtab` 未给出它的语义。

3. **`0x486b0` 在 `.bss`，且代码范围是空区间。**
   - `.bss`：`0x486b0..0x48868`（size 0x1b8）；
   - `0x23e28` 的 start/end 都是 `0x486b0`，长度 0；
   - 因此数组没有表项，也不会指向 `InitializeIF`/`sys_createApplication`/`GraphicsEngine` 初始化。

4. **§11 分类已更新：**
   - `0x23e28` 从“无法判定”改为 **不调用三目标**；
   - 7 个 helper 计数变为 **不调用 7 / 无法判定 0 / 调用 0**。

### 12.2 证据表

| 项 | 结果 |
|---|---|
| `0x23e28` 数组 start | `0x486b0` |
| `0x23e28` 数组 end | `0x486b0` |
| `sub` 结果 | `0` |
| `cbz x1, 0x23e60` | 必跳 |
| `0x23e60` | `ret` |
| `0x460fa0` section | `.data.rel.ro`（0x45750 + 0x11f0） |
| `.got` range | `0x46c40..0x46fe8` |
| `.rela.dyn/.rela.plt` @ 0x460fa0 | 无 |
| `.dynsym/.symtab` 附近符号 | 无 |
| `0x486b0` section | `.bss`（0x486b0..0x48868） |
| 数组表项 | 0（start=end） |
| 三目标引用 | 无 |

### 12.3 对“未使用”假设的影响

- `0x23e28` 不再是一个未解析的间接调用；它是 **空析构表**；
- 7 个 helper 全部可解释为静态初始化/析构/工具函数；
- 没有新增证据表明 `InitializeIF`/`sys_createApplication` 被调用；
- “未使用”假设继续得到支持；仍是静态结论，不是运行时证明。

### 12.4 实测 vs 推断 vs 缺失

**实测**：

- `0x23e28` 的起止地址都是 `0x486b0`，长度 0；
- `cbz` 到 `ret`，`br x2` 不可达；
- `0x460fa0` 在 `.data.rel.ro`，无 reloc/符号；
- `.bss`/`.got`/`.got.plt` 范围；
- §11 分类与计数已更新。

**推断**：

- `0x23e28` 是空析构表/`__cxa_finalize` 风格 registry；
- `0x460fa0` 是未使用的静态槽位；
- 不是 framebuffer 初始化入口。

**缺失**：

- `0x460fa0` 的具体用途（不影响结论）；
- 运行时 `[0x486f0]` 值；
- 运行时 `GRM_fbrmInitialize` 是否命中；
- 运行时断点仍待批准。

### 12.5 运行时待批准方案（未执行）

```text
断点 InitializeIF 0x2764c
先读 [0x486f0]（own_）
若为 0：确认 own_ 未初始化
再断 GraphicsSystemCore::Initialize 0x27ef0
再断 GRM_fbrmInitialize 0x23374
```

本轮**未执行**任何运行时步骤。
