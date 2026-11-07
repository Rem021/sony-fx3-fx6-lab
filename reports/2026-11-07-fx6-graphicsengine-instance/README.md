# FX6 GraphicsEngine 单例静态追踪

日期：2026-11-07  
范围：`GraphicsEngine::m_instance` 是否被写入、`sys_getInstance` 的返回值、appFw 调用点是否判空  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未写代码；未编译；未跑 pmemsave/解析器；未触碰用户三问**

## 1. 结论

**`GraphicsEngine::m_instance` 在静态可见流程中没有写入点，`sys_getInstance` 只会返回这个 BSS 的当前值（静态为 0）。appFw 在 `0x16f0014` 取到返回值后没有判空，就直接把它作为 `x0` 传给 `0x1592130`。**

因此，单例这一层就已经断了：

```text
m_instance (0xc4bf8) 无静态写入
  -> sys_getInstance 返回 0
  -> appFw 0x16f0014 取到 0
  -> 0x16f0020 直接把 0 当作 this 传入
```

这比 framebuffer/GRM 更上游；与“`sys_createApplication` 未使用、init_array 无 ctor、own_ 无写入”一起，说明当前静态链没有可用的 GraphicsEngine 实例。

## 2. 证据

### 2.1 `m_instance` 与 GOT

`libuxengine`：

```text
0xc4bf8  B  ux::gfxeng::GraphicsEngine::m_instance
```

`sys_getInstance`（0x8265c）：

```text
0x8265c: adrp x0, #0xc1000
0x82660: ldr  x0, [x0, #0xf78]   ; GOT -> &m_instance
0x82664: ldr  x0, [x0]           ; m_instance 值
0x82668: ret
```

GOT 0xc1f78 的 relocation：

```text
.rela.dyn 0xc1f78  R_AARCH64_GLOB_DAT -> GraphicsEngine::m_instance
```

### 2.2 无静态写入

扫描 `libuxengine` `.text`：

- `adrp page 0xc4000` + `#0xbf8` 的 store：**0 个**；
- 对 `m_instance` 的直接/GOT 写入：未发现；
- `m_instance` 在 BSS，静态零；
- `GraphicsEngine` 构造函数（0x8350c）没有 `bl/b/adrp-add` xref，也不写 `m_instance`；
- `libuxengine` `.init_array` 的 8 个函数没有 ctor（§13 已列）；
- `sys_createApplication` 无 xref/外部 U（§12 已定）。

### 2.3 appFw 调用点

appFw 导入 `GraphicsEngine::sys_getInstance`，PLT 0x1594580；调用点：

```text
0x16f0014: bl  sys_getInstance
0x16f0018: mov w2, #0x15
0x16f001c: mov w1, #0x1c
0x16f0020: bl  0x1592130
```

关键：

- `0x16f0014` 之后**没有 `cbz x0`/`tst`/空指针检查**；
- 返回值直接作为 `x0` 传给 `0x1592130`；
- 若 `m_instance` 为 0，这里就是 `this=0` 的调用。

第二个调用点 `0x16f0024` 同样直接取返回值后调用 `0x1591c00`，也没有判空。

## 3. 解释

可能的路径：

1. `m_instance` 本应由某个初始化函数写入；
2. 但 `sys_createApplication`/`GraphicsEngine` ctor/init_array/own_ 都没有静态写入；
3. appFw 取到 0 后直接调用成员函数；
4. 结果可能是崩溃、空实现或未定义行为；当前 FX6 没到可见 UI。

这与前面的结论一致：

```text
没有 GraphicsEngine 实例
  -> 没有 createFramebuffer/GRM 初始化
  -> 没有 on-screen bitmap
  -> 没有 OSD 帧
```

## 4. 实测 vs 推断 vs 缺失

### 静态实测

- `m_instance` 地址 0xc4bf8，BSS；
- `sys_getInstance` 只读 GOT 0xc1f78 -> `m_instance`；
- GOT 0xc1f78 的 GLOB_DAT 符号；
- `m_instance` 无直接 store/GOT 写入；
- appFw 调用点 0x16f0014/0x16f0024 无判空；
- ctor 无 xref，init_array 无 ctor。

### 推断

- `sys_getInstance` 在当前静态流程中返回 0；
- appFw 的 0x16f0020 会以 `this=0` 调用；
- 这是 UI 无法起来的更上游原因；
- 实际运行时可能由未扫描的动态代码写 `m_instance`，但静态没有证据。

### 缺失

- 运行时 `[0xc4bf8]`（m_instance）实际值；
- `0x1592130` 的精确符号（未映射）；
- 是否有动态加载/外部模块写 `m_instance`；
- 运行时断点/approval；本轮不执行。

## 5. 边界

- 未启动/未改动任意 VM；
- 未解包/修改 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未写代码、未编译、未运行；
- 未跑 pmemsave/解析器；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）。

## 6. 下一步（需批准）

运行时最快验证：

```text
断点 sys_getInstance 0x8265c
读 [0xc4bf8]（m_instance）
若为 0：单例未初始化
断点 appFw 0x16f0020，读 x0
若 x0=0：确认 this=0
再回溯谁应该写 m_instance
```

或者静态继续：

- 映射 appFw PLT 0x1592130 的符号，确认它是否是 `createScreen3D`/`setArea`；
- 查 `m_instance` 是否被 **`memcpy`/`memset`/GOT 间接写**（当前只查了直接 store/adrp-add）；
- 查 appFw 的 `GraphicsEngine` 初始化入口是否根本未调用。

本轮未新建运行时步骤，也未执行任何断点。
