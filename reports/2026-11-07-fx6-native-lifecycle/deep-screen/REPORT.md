# 真 FX6 原生屏幕状态机路线（第二轮，2026-11-07）

本轮已找到可连接原厂 screen manager、工厂回调和 HOME controller 的确定入口。下一次运行应沿这条链观察：**`App::run → App::initialize → presenter_controller_manager::initialize → 原生事件 → manager::open_screen_internal → controller/presenter 工厂`**。直接调用 HOME presenter 构造函数不能替代这条路径。

本轮只做静态读取，未启动或操作 VM，未修改共享源码、候选或 donor。

## 精确输入

`/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so`

- 50,520,424 bytes。
- SHA-256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。
- 下文地址全部是该 ELF 的 VMA，运行时须加同一文件的实际 load base。

## 1. App 到 manager 的创建顺序

| 阶段 | 地址与静态证据 | 必需上下文 |
|---|---|---|
| UI worker | `0xc0b470`，调用 `uxengine_init2`、Arena 初始化、`setDatabase("global.xdb")` | 已初始化的中间件、资源和内存池 |
| App 构造 | `0xc0b520 → 0xc0b12c` | worker 栈内 App 对象；不是空指针/零页对象 |
| manager 构造 | App 构造中 `0xc0b1f8 → 0xdf92cc`，manager 内嵌于 **App + `0xa40`** | App 自有的 view/resource/controller 支撑对象 |
| App 主循环 | `0xc0b528 → 0xc0a69c` | 上一步构造完成的同一 App 对象 |
| App initialize | `0xc0a6cc → 0xc09da0` | 完整模型生命周期 |
| manager initialize | `0xc09e0c → 0xde31ac` | 上方同一个 App + `0xa40` |
| GRM trigger 注册 | `0xc09e48 → GRM_fbrmRegisterTriggerFrameworkCb` | 回调 `0xc091d0`，回调 user 为 App 对象 |

`manager::initialize` 会填充 `0x432ded0` 开始的 7 个 display-layer presenter 预分配池指针，并建立辅助状态。HOME presenter 工厂 `0xde1244` 会从这个池按 layer 取 `this`；池指针为空时它直接返回 NULL。**跳过 initialize 后只进绘图循环，并不满足 screen 创建条件。**

`AppConfig.so` 在此 worker 首先作为配置字符串处理：`strncmp` 相等产生 `w2=0`，不等产生 `w2=1`；App 构造把该 bit 存到 `App+0x12b8`，initialize 经 `0x12d9fc8` 写入模型 value-id `0x3b16`。不能把改字符串或单独进入 worker 视为模型初始化已经完成。本轮没有把此 bit 的全部语义强命名为工厂/正式模式。

## 2. 原厂 registry 和 screen ID

屏幕 registry 基址 **`0x293bed8`**，由 GOT **`0x2ee2100`** 的 `R_AARCH64_RELATIVE` addend 绑定；每行 **`0x38` bytes**。

| 原厂 screen | screen ID | 行地址 | presenter 工厂（row+0） | controller 工厂（row+8） |
|---|---:|---|---|---|
| Shooting | **2** | `0x293bf48` | `0xdd3fa4` | `0xdb2524` |
| Big6 HOME | **10** | `0x293c108` | `0xde1244` | `0xdb2f28` |
| Menu 第一层 | **15** | `0x293c220` | `0xdd75a4` | `0xdb3584` |

行 `+0x20` 独立保存相同 screen ID；controller 工厂也把该 ID 写入 `controller+0x28`。因此 HOME ID 为 **10**，不能把相邻行里的 9 当作 HOME。表里还有 layer/restore/显示性质字段，本轮只保留原值，不扩充未证明的语义。

## 3. 从 screen manager 经工厂创建

- **`presenter_controller_manager::open_screen_internal`：`0xdf790c`**。由原厂断言函数名绑定；参数是 `self`、三个 `const ds_screen_id&` 和三个 bool。它检查 screen ID、重入状态 `self+0x741` 及当前屏幕状态，随后进入内部切换。
- **`presenter_controller_manager::open_screen_ii`：`0xdf6680`**。原厂断言给出完整签名，包含 restore-mode、controller 引用、两组 presenter 数组和恢复 deque。它不是可以只给 screen ID 的简单 API。
- 该函数在 **`0xdf690c → 0xde3584`** 取 registry 的 **controller 工厂**，在 **`0xdf6930 → 0xde34fc`** 取 **presenter 工厂**。
- `0xde3584(self, screen_id, display_layer)` 从 row+8 取原厂 controller 工厂，同时提供 manager、view、caution resource 上下文；`0xde34fc` 从 row+0 取原厂 presenter 工厂。
- HOME 工厂进 `procam_big6_menu_home_presenter` 构造 `0xde10f4`，因此原厂控件表能够由这条路径消费，无需重新排列控件。

上述 factory/manager 入口用于 **观察原厂流转或复用现成有效对象**。不能把 `App+0xa40` 当作独立缓冲区临时 calloc 后直接调用，也不能伪造 controller 的 view/model/resource 指针。

## 4. 原厂 controller 和 boot 完成事件

通过函数内 `open_screen` 断言名与 prologue 独立确认：

| controller 的屏幕请求入口 | VMA |
|---|---|
| `procam_big6_menu_home_controller::open_screen` | **`0xf2dec0`** |
| `procam_shooting_controller::open_screen` | **`0xfb2f88`** |
| `procam_menu_layer_1st_controller::open_screen` | **`0xf5dce0`** |
| `rep_boot_controller::open_screen` | **`0x1009518`** |

这些方法使用 `controller+0x28` 的当前 ID 和 `controller+0x30` 的 manager，参数为三个 screen-id 引用；它们向 manager 的虚函数发出切换请求，而不是无上下文地把本屏点亮。

`rep_boot_controller::process_MODEL_POWER_ON_COMP(const ds_event&)` 已由原厂名字引用绑定到 **`0x1009be0`**，其原厂 handler function-pointer 位于 **`0x2d2ad38`**。该方法按模型状态选择后继屏幕：在 `0x100ab00..0x100ab10` 可见分支常量 **2 或 7** 写入目标 screen-id 栈槽（registry 独立证明 ID 2 为 Shooting；本轮没有给选择条件的模型值命名），并可能先开其他屏幕；随后经 `rep_boot_controller::open_screen` 请求切换。**不能假设上电完成后必然直接到 HOME，也不能仅注入名叫“开机完成”的自制事件代替真实模型的完成状态。** 本轮尚未证明该事件的数值 ID 和真实投递路径，也未完整证明全部模型条件。

## 5. 下一次候选应观察什么

首先解决当前中间件初始化阻塞；相关 MWF 生命周期由并行 native-init 任务负责。本分支不改共享候选。

之后建议只加少量 caller 观察点，保持原厂路径：

1. 记录同一 run 的 `appFw.so` SHA、load base、App 指针以及 manager=`App+0xa40`；确认 `0xc09da0` 和 `0xde31ac` 实际返回、7 个池指针有效、`GRM_fbrmRegisterTriggerFrameworkCb` 成功执行。
2. 观察 manager `0xdf790c` 的三个 screen ID、`self+0x741`，再观察 `0xdf6680` 的目标 ID 和 factory 调用。特别关注 **ID 2 / 10 / 15**。
3. 若停在 boot，先观察 `0x1009be0` 是否由原厂 event-dispatch 到达，并记录其模型条件分支；不要先绕过它或强改 ID。
4. 只有原厂 factory 被调用且 framebuffer 出现后，才把按键、同轮 framebuffer 原始字节及截图绑定，验收是否为原生菜单。

本轮把“原厂路径可定位”推进到了确定调用链和对象先决条件；**没有证明任何一个入口在 guest 实际到达、HOME 可操作或菜单可见**。

## 重跑

```sh
python3 -B audit_screen_route.py /path/to/the/pinned/fx6/appFw.so > route-result.json
```

标准库脚本会校验输入 SHA、registry relocation、screen ID/工厂行、关键 BL 调用边、方法名 ADRP/ADD 引用、open_screen 无效 ID 检查以及 boot handler 绑定。输出只含结构、地址和少量函数名，不导出固件或整段反汇编。
