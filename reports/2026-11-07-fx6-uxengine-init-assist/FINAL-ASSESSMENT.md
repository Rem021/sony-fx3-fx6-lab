# FX6 原生首帧 — 最终评估（2026-11-07 23:22 PST）

## 1. 结论摘要

**更新（566）**：已达成首个原生帧——合成 screen update 驱动原生 Window::render 全屏 clear，经 GRM shim 输出到 gpe0；gpe0-late nz=2,207,744，PNG `first-native-frame.png`。内容为背景 clear（dark slate），菜单控件尚未出现。


- **`0x41e001000`（gpe0）非零已实现**：run `cp-bind-241f6ecc` 的 `gpe0-late.bin` nz=1,103,872（1024×540）。
- **但不是原生 UI 帧**：这是兼容服务按测试色 `0xFFFF0000` 填的纯色帧。按“严禁 fake 像素”的要求，**不满足判据**。
- **原生管线已被打到门口**：`GraphicsEngine::sys_render → Window::render → Render2DWalker → GraphicsDraw::fillRect`，最后一次 run 中渲染器**确实调用到了我们的 fill 服务**（1 次），但 rect 是未初始化的恒定 garbage 值，来自缺失的 screen/layer 几何。
- **硬边界**：FX6 的 model/presenter/graphics 服务栈在 FX3 guest 中不存在；widget/screen 树为空，`Node2D::draw` 是空桩，presenter path 全部依赖这些缺失状态。

## 2. 已经打通的链路

### 2.1 兼容渲染 → gpe0

```text
GraphicsDrawState vtable slot31（或兼容服务直接调用）
  → fx6_compat_fill_rect（写 shim pix_off，prims++）
  → fx6_compat_flush_to_osd（memcpy 2211840B → osd41e = phys 0x41e000000）
  → gpe0 = 0x41e001000 非零
```

关键 run：`cp-bind-241f6ecc`（gpe0-late nz=1,103,872）。

### 2.2 原生渲染器 → 我们的 fill 服务

```text
GraphicsEngine::sys_render
  → GraphicsSystem::prepareRendering
  → beforeRenderingCallback
  → Window::setGraphicsContext
  → ScenegraphWindow::setDirtyRect
  → Window::render
    → DirtyRegion::getDirtyRect(window+0x40)
    → Render2DWalker::setRenderRect
    → renderInternal(layer) → GraphicsDraw::fillRect → 我们的服务
```

关键 run：`cp-bind-0d27f761` / `cp-bind-499f7e69` / `cp-bind-24ab709b`（`FX6_DIRTY_FILL n=1`，但 rect garbage）。

### 2.3 其他已验证能力

- `u_osal_snd_msg(0x807e0030, msg)` 成功（sr=0），可回 model reply（10 次固定周期）。
- 17b9f1c 调用点恢复（`c56fec`）使 walk 从 ~24 min 降到 ~30 s。
- UI 初始化跑通：18 screens、9 layers、一个 `view_fill`（1024×540, color 0, visible 1）。
- 原生 `GraphicsDraw::fillRect/setColor/begin/end` 符号与参数已定位。
- `ScenegraphWindow::setDirtyRect` 是 8 字节 setter；真正 dirty region 在 `window+0x40`。
- `Element::setupDrawState`、`Node2D::draw` 在本构建中是空桩（`ret` / `mov w0,#1; ret`）。

## 3. 为什么原生 UI 帧不可达

1. **model 服务缺失**：UI 线程阻塞在 model_lock（多实例自定义 handoff 锁，`1acd6c0` 共享等待点）；任何强制 take 都会触发 `model_mutex.cpp:55/59/75` assert。
2. **presenter/GRM 服务缺失**：`ExternalOSDIF`/`FBResourceManager`/`Semaphore` 为 null；GRM fill 命令从未执行；present 崩溃在 `0x58`。
3. **screen/layer 树为空**：`renderScreen`/`renderInternal` 无子节点；walker 收到恒定 garbage rect（24574,-22083,…），说明几何字段未初始化。
4. **widget draw 是空桩**：`Node2D::draw` 直接返回 1；`Element::setupDrawState` 直接 `ret`。
5. **dirty region 无法产生内容**：即使 `addDirtyRect` 成功（n=1），没有 screen 几何仍不画。

这些都不是再打一个 patch 能解决的：FX6 的 model/presenter 是独立服务，FX3 guest 中没有它们的运行时。

## 4. 运行清单（关键）

| run | 目的 | 结果 |
|---|---|---|
| `cp-bind-241f6ecc` | compat fill 提前 + flush | **gpe0 nz=1,103,872**（纯色，非 UI） |
| `cp-bind-0d27f761` | sys_render + dirty rect | 原生 fill 1 次，rect garbage |
| `cp-bind-24ab709b` | addDirtyRect + sys_render | addDirtyRect n=1，仍 garbage |
| `cp-bind-63a0b0d3` | widget vt[3] | 崩 addr=0x30 |
| `cp-bind-3318dc3f` | Node2DWalker+draw | 静默返回 |
| `cp-bind-7e60fafe` | 真 fillRect 直调 | 未命中 slot31 |
| `cp-bind-ebe35e63` | owner=222 | 无 assert，但无 PRE/helper |

## 5. 建议的后续方向

1. **补 FX6 服务运行时**：把 FX6 的 model/presenter/graphics 服务（或其最小实现）跑起来，让 screen/layer 几何与 dirty 数据自然产生。
2. **换启动路径**：用 FX6 完整 rootfs/服务集启动，而不是在 FX3 guest 上强行加载 `appFw.so`。
3. **或接受兼容层方案**：明确把当前 compat 渲染定义为“软件 OSD 兼容层”，以 shim 内容（而非 FX6 UI）作为展示输出——但这不再是“原生首帧”。

## 6. 证据索引

- `EVIDENCE-399-414-OSAL-EVENT-INJECTION.md` §10.1–§10.72。
- `HANDOFF-20261107-RUNTIME.md`（运行/handoff 记录）。
- `2026-11-08-gemini-coordination.md`（并行线协调）。
- `FIRST-FRAME-STATUS.md`（阶段状态）。
- `MASTER-PLAN-FIRST-FRAME.md`、`STATIC-PIPELINE-MAP.md`（授权与静态管线）。
