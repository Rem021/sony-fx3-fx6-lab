# 附加复核：原厂 im.elf 如何消费生命周期表

2026-11-07；本次仅只读原厂 FX6 `bin/im.elf`（40,920 B，SHA-256 `2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772`）及 `libIMDB.so`（79,728 B，SHA-256 `a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896`）。没有调用这些代码。

## 确定的消费链

`IMDB_get_entries`（libIMDB+0xa64c）返回 `imdb_raw+0x100`，即 VMA `0x1e970`。`im.elf+0x4064fc` 是表扫描器：在 `+0x406564` 调用 `IMDB_get_entries`，以 `0x48`（72 B）步长扫描。它并非无条件执行每个表项：

- `+0x406570..0x40657c`：遇到本次请求的边界 token，或表尾 `0x28` 时停止；
- `+0x4065b0`：请求 enable 参数为 0 时不派发；
- `+0x4065b4..0x4065c0`：descriptor `+8` 的 target mask 必须与当前目标 mask 有交集；
- `+0x4065c4..0x4065cc`：descriptor `+4` 的 flags 必须与请求 flags 有交集；
- `+0x4065e4..0x4065f0`：按 descriptor `+0xc` 的模块 ID 调用派发函数 `+0x406374`；
- `+0x406608..0x406610`：递增索引并继续扫描。

`+0x40661c` 是上述扫描器的包装，令 flags 为 `0xff`。原厂主启动路径在 `+0x402670` 调该包装时，边界 token 为 **`0x08000004`**、enable 来自 `+0x405574`；起始索引来自前一个扫描调用的返回值。Kiki 与 MWF 两项均处于边界 `0x08000003` 与 `0x08000004` 之间，因此属于这次扫描区间。这里用真实数值 token 指代阶段，尚未恢复其原厂命名。

## 两项实际 descriptor

| 字段 | KikiLogGenerator | MWF |
|---|---|---|
| 表项地址 | `0x1f198`（索引 29） | `0x1f270`（索引 32） |
| descriptor `+0` 类型 | `0x20000001` | `0x20000002` |
| descriptor `+4` flags | `0x1` | `0x1` |
| descriptor `+8` target mask | `0x7fffffff` | `0x7fffffff` |
| descriptor `+0xc` 模块 ID | `272` | `151` |
| descriptor `+0x10` 库 | `libInfraKikiLogGenerator.so` | `libMWF.so` |
| descriptor `+0x18` init 入口 | `KikiLogGenerator_init` | `MWF_Init` |

`0x20000001` / `0x20000002` 是表项类型，**不能把它们解释成初始化 phase 1 / phase 2**。这一点已由实际扫描边界和类型分派代码区分。

## 库加载与 init 调用证据

模块装载路径 `im.elf+0x405f5c` 从 descriptor `+0x10` 取库名，在 `+0x405f9c` 调 `dlopen`；若 `+0x18` 的 init 字符串非空，则在 `+0x406004` 调 `dlsym`，随后 `+0x40602c` 通过函数指针调用原厂 init。另一条带参数路径在 `+0x405f0c` 做 `dlsym`、`+0x405f34..0x405f44` 选 descriptor 参数并调用。它们证明原厂管理器消费的是描述符中的 init 字段，而非只加载 `.so`。

## 顺序可以说到哪里

已还原实际扫描循环，因此在 enable/mask/flags 均通过、并按上述正常启动区间遍历时，**Kiki 模块 ID 272 的加载请求先于 MWF 模块 ID 151 的请求被扫描器派发**。这不是仅根据表的物理排列作出的判断。

但本次窄范围复核 **尚未完整还原派发器的工作线程、状态等待和 init 完成屏障**。不能据此声称 `KikiLogGenerator_init` 一定返回之后才进入 `MWF_Init`，不能声称二者构成直接依赖，更不能将上述数值 token 转成未经确认的原厂阶段名。模块管理器是否跳过/重试、实际选择的 target 与运行状态也仍需匹配真实启动上下文。

因此下一轮若恢复生命周期，应使用已确认的模块管理阶段和状态契约，不能仅凭这张表手动连续调用两个 init。这里的确定结论仍是：原厂存在带过滤、阶段边界和模块状态管理的显式 init 执行链；当前独立 `appfw-launch` 的 `dlopen` 不能替代它。
