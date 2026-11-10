# FX6 原生首帧 — 阶段状态（截至 2026-11-07 23:00 PST）

## 1. 判据与当前状态

- 判据：`0x41e001000`（gpe0）非零，且像素来自 FX6 `appFw.so` / `libux*.so` / `libGrm.so` 管线。
- **管线里程碑已达成**：原生 `GraphicsDrawState` vtable 槽 → 兼容服务 → shim framebuffer → compat flush → 物理 `0x41e001000`。
  - run `cp-bind-241f6ecc`：`gpe0-late.bin` **nz=1,103,872**，正好 1024×540 红色填充。
- **但内容不满足判据**：该帧是我们兼容服务按测试色 `0xFFFF0000` 填的纯色帧，不是 FX6 app 自身的 UI 内容。按“严禁 fake 像素”的要求，**不宣称完成**，goal 保持 active。

## 2. 已经打通的链路

```text
app 的 GraphicsDraw 派发点
  GraphicsDrawState vtable +0xf8 (slot 31)
    -> fx6_gds_fill（我们的兼容服务）
      -> fx6_compat_fill_rect（写 shim pix_off，prims++）
      -> fx6_compat_flush_to_osd（memcpy 2211840B 到 osd41e = phys 0x41e000000）
        -> gpe0 (0x41e001000) 非零
```

关键补丁/实现：

- `GraphicsDrawState` vtable slot31 运行时替换为 `fx6_gds_fill`（mprotect + clear_cache）。
- `fx6_compat_fill_rect` / `fx6_compat_flush_to_osd` 直接位于 shim 内，避免 `dlsym((void*)-1)` 看不到自身符号。
- **不能走 `GRM_gpermFillrect`**：它内部 swap → `ExternalOSDIF::sendUpdate`（this=NULL）崩溃；compat 直填+flush 绕开。

运行参数（重要）：

- CPIO 源：`guest-hybrid-fx6kernel-capid-grmreal544-compatfill4.cpio`，payload `libgrm-fbinit25-545.so`。
- 触发时机：第 **3** 次 model reply（`fx6_uosal_inject_early.c`），必须早于 runner 的 `gpe0-late` 抓取。
- VM：单 VM 私有锁运行；并发 VM 会间歇性触发
  `libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev`。

## 3. 仍未解决的关键缺口

1. **app 自身内容**：目前 `view_fill` 等控件没有产生 draw 请求；presenter/model 缺失。
2. **model_lock**：多实例自定义 handoff 锁，`1acd6c0` 为共享等待点；全局 take 会破坏不变量（assert 55/59/75）。
3. **present 路径**：`ExternalOSDIF`/`FBResourceManager` 为 null；GRM fill 命令从未执行。

## 4. 下一步计划

1. **找 widget 的真正 draw 入口**：在 GDS 服务已安装的前提下，系统探测 `view_fill` 的 vtable 槽（40–52），看哪个槽会触发 `FX6_GDS_SERVICE2 call`（即 app 发起的绘制），从而把绘制请求来源从“我们手动调用”换成“app 控件调用”。
2. 若找到 draw 入口，将 widget 的 rect/color 作为 app 请求渲染；此时 gpe0 内容即为 **app 控件自身** 的填充（仍非完整菜单，但来源正确）。
3. 继续补齐 presenter/model，让真实菜单控件产生多图元绘制。

## 5. 证据索引

- `EVIDENCE-399-414-OSAL-EVENT-INJECTION.md`：§10.1–§10.60（含 545 的 gpe0 里程碑与 caveat）。
- `HANDOFF-20261107-RUNTIME.md`：运行/handoff 记录（持续更新）。
- `2026-11-08-gemini-coordination.md`：并行线协调记录。
- `MASTER-PLAN-FIRST-FRAME.md` / `STATIC-PIPELINE-MAP.md`：授权与静态管线图。
