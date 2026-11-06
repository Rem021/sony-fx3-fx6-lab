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
