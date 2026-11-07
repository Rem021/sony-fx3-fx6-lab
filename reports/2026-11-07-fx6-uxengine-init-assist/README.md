# FX6 UI / UXEngine 适配辅助诊断笔记（供 DeepSeek 协同参考）

## 0. 如何在第一行 `APPFW_SEGV` 直接打印 `X30 (LR)`（无需 QEMU `-gdb`）

- QEMU 的 `-gdb tcp::12345` 是全系统内核态 stub，不会在用户态进程 `appfw-launch` 触发 `SIGSEGV` 时自动断下。
- 在 `/usr/bin/appfw-launch` 的 `segv_handler`（文件偏移 `0x8efc`）中，第一条 `fprintf`（打印 `APPFW_SEGV sig=%d addr=%p pc=%llx sp=%llx`）总是能成功输出。
- 在文件偏移 **`0x8f24`** 处，原指令是从 `siginfo_t` 读取 `si_addr` 放入 `x3`（`ldr x3, [x1, #0x10]`，字节为 `23 08 40 f9`）。
- 只需将 `usr/bin/appfw-launch` 文件偏移 **`0x8f24`** 的 4 字节改为从 `ucontext_t`（`x2`）偏移 `0x1a8` 读取 `regs[30]`（即 `ldr x3, [x2, #0x1a8]`，小端字节为 **`43 d4 40 f9`**），第一行 `APPFW_SEGV` 的 `addr=` 字段就会直接输出崩溃瞬间的 **`X30 (LR)`**！

---

## 1. 重大发现：`libIMDB.so` 揭示的 `grm_init()` 初始化链与 `libgrm-fbinit9.so` 绑定顺序

### (A) 为什么 `FBResourceManager` 的 `[this + 0x8]` (`FrameBuffer*`) 一直是 NULL
检查 `libIMDB.so` 的模块初始化表可知，真机 `im.elf` 启动顺序为：
1. `libgrm.so` -> **`grm_init()`**（偏移 `0x26f90`）
2. `libuxengine.so` -> `uxengine_init()` / `uxengine_init2()`
3. `appFw.so` -> `subapp_init()` / `Application_System_Init()`

在 `libgrm.so` 的 `grm_init()`（`0x26f90`）内部，依次执行了：
- `uiresp_init()`
- `CmdQueue::getInstance()->initialize()`
- `ResultQueue::getInstance()->initialize()`
- **`BMP_Initialize()`**（初始化 GRM Bitmap 管理器）
- **`MA_Initialize()`**（初始化 GRM 内存分配器）
- **`FBResourceManager::getInstance()->initialize()`**（偏移 `0x22898`）：
  - 在 `0x22904` 处分配 `new grm::FrameBuffer()` 并存入 `[FBResourceManager + 0x8]`；
  - 在 `0x22920` 处调用 `grm::FrameBuffer::initialize()`！
- **`GPEResourceManager::getInstance()->initialize()`**

因为 `appfw-launch` 从未调用 `grm_init()`，所以当使用原生 `libgrm.so` 时，`BMP_Initialize()`、`FBResourceManager::initialize()` 和 `[FBResourceManager + 0x8]` 全都处于未初始化状态。

### (B) 为什么 `libgrm-fbinit9.so` 的桩函数没有生效
`libgrm-fbinit9.so` 已经完整导出了以下拦截符号（会自动通过 `BMP_CreateBitmap` 分配 1024×540 帧缓冲并写入 `0x41e000000` 共享内存环）：
- `grm::FBResourceManager::getInstance()` (`0x10fa4`)
- `grm::FBResourceManager::initialize()` (`0x10f4c`)
- `grm::FrameBuffer::initialize(unsigned int, unsigned long)` (`0x10f60`)
- `grm::FrameBuffer::getOnscreen()` (`0x10da8`) / `getOffscreen()` (`0x10dd0`)
- `grm::FrameBuffer::setSize(unsigned short, unsigned short)` (`0x10d68`)
- `grm::FrameBuffer::update()` (`0x10f90`)

但在 `appfw-launch.c` 中，`dlopen(..., RTLD_NOW | RTLD_GLOBAL)` 的调用顺序是：
```c
pre("/usr/lib/libgrm_bmp.so");
pre("/usr/lib/libux_core.so");
pre("/usr/lib/libgrm.so");
pre("/usr/lib/libuxengine.so");
pre("/usr/lib/libgrm-fbinit9.so"); // <--- 放在了最后！
```
由于使用了 `RTLD_NOW`，`libux_core.so`、`libgrm.so`、`libuxengine.so` 在加载当下就把各自的 PLT/GOT 绑定到了 `libgrm.so` 自身，导致后面加载的 `libgrm-fbinit9.so` 完全没有拦截到任何调用！
**修复方法**：在 `appfw-launch` 中把 `/usr/lib/libgrm-fbinit9.so` 放在 `libgrm.so` / `libux_core.so` **之前**加载（例えば与 `/usr/lib/libgrm.so` 交换顺序，或在 `appfw-launch` 的字符串表里把这两条路径字符串互换，因为：
- `"/usr/lib/libgrm.so"` 长度为 18 字节；
- 若在 `appfw-launch` 的 `main()` 中把调用 `pre("/usr/lib/libgrm-fbinit9.so")` 的指令移到 `pre("/usr/lib/libux_core.so")` 之前，只需交换 `main()` 里对应的 `adrp + add + bl pre` 指令块！）。

---

## 2. 为什么 `173`–`178` 中 `GraphicsEngine` 构造未返回（死循环原因）

在 `173`–`178` 中，`libuxengine.so` 的 `pgList::Item::Leave()`（偏移 `0x7be44`）被改成了直接返回（`ret`）。
但调用它的 `pgList::Clear()`（偏移 `0x83404`，由 `pgMap::Clear()` `0x8343c` 在构造函数 `0x83588` 处调用）是一个 `while` 循环：

```cpp
// pgList::Clear() @ 0x83404
while (this->next != &this->tail) {
    this->next->Leave(); // 若 Leave() 直接 ret 不摘除节点，此处将无限循环！
}
```

- **修复方式**：不要将 `pgList::Item::Leave()`（`0x7be44`）单独改为 `ret`；若需跳过清理循环，应直接将 **`pgList::Clear()`（`libuxengine.so` 偏移 `0x83404`）** 或 **`pgMap::Clear()`（偏移 `0x8343c`）** 的首条指令改为 `ret`（`c0 03 5f d6`）！

---

## 3. `appfw-launch` 中的两个架构冲突

1. **线程 117 与 `appfw-launch` 对 `[0x48800]` / `[0x48810]` 的竞争**：
   - `Application_System_Init()` 启动的后台线程（TID 117，打印 `I/stella( 117): Created HeapAllocator`）已经在原生地调用 `uxengine_init2()` -> `UXEngine::initialize()` -> `Kernel::sys_initialize()`（`0x31dfc`）。
   - 当 `[libux_core + 0x48810] == 0` 时，`Kernel::sys_initialize()` 会自动分配真实的 `ux::core::Kernel` 实例写入 `[0x48810]`（`0x31ee4`），并调用 `GraphicsSystem::sys_initialize()` 将真实的 `GraphicsSystemCore::GetInstance() + 8` 写入 `[0x48800]`（`0x30ce8`）。
   - `appfw-launch` 在主线程中向 `[0x48800]` 和 `[0x48810]` 写入全零的 `app_ctx`（`0x103c258`）会与线程 117 竞争并冲掉真实指针。
2. **`UXEngine::initialize()` 内部其实已经包含 `GraphicsEngine` 实例的创建与 `m_instance` 赋值**：
   - `GraphicsEngine::sys_initialize()`（`0x838e4`）通过 PLT 调用 `sys_createApplication()`（`0x82854`）和 `sys_createAfterTask()`（`0x83810`）。
   - `sys_createAfterTask()`（`0x83810`）内部已经执行了 `malloc(0x340)`、调用 `GraphicsEngine` 构造函数（`0x8350c`）、将指针写入 `[GOT 0xc1f78]`（`GraphicsEngine::m_instance` `0xc4bf8`），并创建默认 Screen。
