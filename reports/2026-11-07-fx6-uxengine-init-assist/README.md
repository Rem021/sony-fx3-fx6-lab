# FX6 UI / UXEngine 适配辅助诊断笔记（供 DeepSeek 协同参考）

## 1. 为什么 `178` 消除了 `osalErr = -1023` 后 `GraphicsEngine` 构造仍未返回（死循环原因）

在 `173`–`178` 中，`libuxengine.so` 的 `pgList::Item::Leave()`（偏移 `0x7be44`）被改成了直接返回（`ret`）。
但调用它的 `pgList::Clear()`（偏移 `0x83404`，由 `pgMap::Clear()` `0x8343c` 在构造函数 `0x83588` 处调用）是一个 `while` 循环：

```cpp
// pgList::Clear() @ 0x83404
while (this->next != &this->tail) {
    this->next->Leave(); // 若 Leave() 直接 ret 不摘除节点，此处将无限循环！
}
```

- **修复方式**：不要将 `pgList::Item::Leave()`（`0x7be44`）单独改为 `ret`；若需跳过清理循环，应直接让 `pgList::Clear()`（`0x83404`）或 `pgMap::Clear()`（`0x8343c`）返回，或者恢复 `0x7be44` 原指令并排查为何 `ScenegraphWindow` 构造后 `x20` 寄存器被污染。

---

## 2. 为什么之前 `172`/`176` 在 `0x7be44` 出现 `APPFW_X0 = 0x900001b7f94027e8`

- `0x900001b7f94027e8` 并非随机堆数据，而是 `/usr/bin/appfw-launch` 中 `main()` 在 `0x1018e0c` 处的 8 字节指令机器码，恰好位于 `ge_ctor(ge_buf)` 返回地址 `LR = 0x1018df4` 加 `+0x18` 处（`0x1018df4 + 0x18 = 0x1018e0c`）。
- 也就是说，在进入 `pgList::Clear()` 读取 `[x19 + 0x18]` 时，原本应当保存 `ge_buf + 0x40` 的 `x20` 寄存器变成了调用方保存在栈上的返回地址 `0x1018df4`。

---

## 3. `appfw-launch.c` 中的两个关键架构冲突（根因与简化路径）

### (A) 线程 117 与 `appfw-launch` 对 `[0x48800]` / `[0x48810]` 的竞争

串口日志中出现的：
```text
I/stella(   117): Created HeapAllocator: ...
I/stella(   117): Replaced log-hook: ...
```
来自 `libux_core.so` 的 `ux::core::Kernel::sys_initialize()`（`0x31dfc`）：
1. `Application_System_Init()` 启动的后台线程（TID 117）已经在原生地调用 `uxengine_init2()` -> `UXEngine::initialize()` -> `Kernel::sys_initialize()`。
2. 当 `[libux_core + 0x48810] == 0` 时，`Kernel::sys_initialize()` 会自动：
   - 创建 `stella::HeapAllocator`（打印 `Created HeapAllocator`）；
   - 初始化日志（打印 `Replaced log-hook`）；
   - 分配真实的 `ux::core::Kernel` 实例并写入 `[0x48810]`（`0x31ee4`）；
   - 调用 `GraphicsSystem::sys_initialize()`（`0x30cb8`）-> `initialize_porting_layer()`（`0x283e4`），将真实的 `GraphicsSystemCore::GetInstance() + 8` 写入 `[0x48800]`（`0x30ce8`）。
3. `appfw-launch.c` 在主线程中手动向 `[0x48800]` 和 `[0x48810]` 写入全零的 `app_ctx`（`0x103c258`），与线程 117 发生数据竞争：
   - 若 `appfw-launch` 写在了线程 117 的 `0x31ee4` 之后，就会把真实的 `Kernel*` 和 `GraphicsSystemCore*` 覆盖成全零的 `app_ctx`，导致 `addr = 0x231` 等崩溃；
   - 若不覆盖 `[0x48800]` 和 `[0x48810]`，让线程 117（或单次 `uxengine_init2()`）自然完成 `Kernel::sys_initialize()`，则 `[0x48800]` 和 `[0x48810]` 会自动指向真实的 `GraphicsSystemCore` 接口表与 `Kernel` 对象。

### (B) `UXEngine::initialize()` 内部其实已经包含 `GraphicsEngine` 实例的创建与 `m_instance` 赋值

在 `libuxengine.so` 中：
- `UXEngine::initialize()`（`0x74d70`）依次调用：
  1. `ux::core::Kernel::sys_initialize()`
  2. `ux::resmgr::ResourceManager::sys_initialize()`
  3. `ux::gfxeng::GraphicsEngine::sys_initialize(path, 1024, 540, 10)`（`0x838e4`）
- `GraphicsEngine::sys_initialize()`（`0x838e4`）内部通过 PLT 依次调用：
  1. `GraphicsEngine::sys_createApplication(path, 1024, 540)`（PLT `0x6f520` -> `0x82854`）
  2. `GraphicsEngine::sys_createAfterTask()`（PLT `0x70f80` -> `0x83810`）
- 在 `GraphicsEngine::sys_createAfterTask()`（`0x83810`）中：
  - `0x83824`: `malloc(0x340)` 分配 `GraphicsEngine` 对象；
  - `0x83834`: 调用 `GraphicsEngine::GraphicsEngine()` 构造函数（`0x8350c`）；
  - `0x83840`: 将新对象指针写入 `[GOT 0xc1f78]`（即 `GraphicsEngine::m_instance` `0xc4bf8`）；
  - `0x83870` / `0x83880`: 自动调用两次 `GraphicsEngine::createScreen()` 创建默认 Screen！
- 之前之所以 `UXEngine::gfxeng()` 返回 `NULL`，是因为 `ResourceManager::sys_initialize()` 或 `sys_createApplication()` 中途返回了 `false`，导致 `UXEngine::initialize()` 提前退出，未走到 `0x74ddc`（`GraphicsEngine::sys_initialize()`）。

---

## 4. `libgrm-fbinit9.so` 的预加载顺序问题

在 `/tmp/appfw/appfw-launch.c` 中：
```c
pre("/usr/lib/libgrm_bmp.so");
pre("/usr/lib/libux_core.so");
pre("/usr/lib/libgrm.so");
pre("/usr/lib/libuxengine.so");
pre("/usr/lib/libgrm-fbinit9.so");
```
`libgrm.so` 在 `libgrm-fbinit9.so` **之前**被 `dlopen(..., RTLD_NOW | RTLD_GLOBAL)` 加载。
因此 `libgrm.so` 内部的符号（如 `grm::FBResourceManager::getInstance`、`grm::FrameBuffer::initialize`、`grm::FrameBuffer::update`）在加载时直接绑定到了 `libgrm.so` 自身，而没有被 `libgrm-fbinit9.so` 拦截。

- **修复方式**：将 `pre("/usr/lib/libgrm-fbinit9.so")` 移到 `pre("/usr/lib/libgrm_bmp.so")` / `pre("/usr/lib/libgrm.so")` **之前**（或放入 `LD_PRELOAD`），使 `libgrm-fbinit9.so` 提供的 `FrameBuffer` / `FBResourceManager` 桩函数优先生效并向 `0x41e000000` 共享内存环写入帧数据。
