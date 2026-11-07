# HOME 闭包节点的低成本到达图（import 入口 + LR 观察）

属 [Big6 依赖闭包报告](README.md) §3 的第 2 段产出。**设计说明，未编译、未运行。** 与 Codex 线 [`observe_osal_queue.c`](../2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c)（只覆盖 `osal_rcv_msg_tmo`）互补：本表把闭包节点映射到 **appFw 在该节点调用的导入函数**，用“导入入口 + 返回地址 LR”判断节点是否到达，不需要对 appFw 内部函数下钩子。

## 1. 原理

- 闭包中的大多数节点都会调用至少一个**导入函数**（PLT）。launcher 的 `fix_got_table` 已经把 appFw 的 GOT 改为按名查找，shim 只要导出同名函数即可接管；DeepSeek 已用同样机制接管 `Backup_*`、`kikilog_*`。
- 在导入入口记录 `LR`（= 调用点 + 4）和 `dladdr(LR)` 得到的 `DSO+偏移`，与下表“期望 LR”比对，即可确定**哪一个原厂调用点**到达，而不是只知道“这个函数被调用过”。
- 对经由公共封装（如线程封装 `0x222dd58`）进入的导入，再用 `backtrace()` 取 3–4 层（shim 的 `abort` 钩子已在用），由第 2/3 层 LR 识别真正的业务调用点。

## 2. 节点 → 导入 → 期望 LR（appFw `a1c58b69…` 相对 VMA）

| 闭包节点 | 导入（PLT 目标，取自已有 JSON） | 调用点 | 期望 LR | 到达即证明 |
|---|---|---|---|---|
| N3 UI worker / N4 前 | `uxengine_init2`（PLT `0xb19290`） | `0xc0b484` | `0xc0b488` | UI worker 已进入 |
| N5 资源数据库 | `ResourceManager::setDatabase`（PLT `0xb188c0`，确切修饰名以 `.rela.plt` 为准） | `0xc0b4d4` | `0xc0b4d8` | `global.xdb` 加载请求已发出；同时记录返回值 |
| N8 BB worker 创建 | `osal_create_waitable_thread`（在 `0x222dd58 → 0x222dc1c` 内，调用点 `0x222dcf4`，见 [native-init](../2026-11-07-fx6-parallel-native-ui/native-init/README.md)） | 业务调用点 `0x20efa1c / 0x20efa6c / 0x20efabc / 0x20efad8 / 0x20efaf4` | 导入 LR 恒为 `0x222dcf8`；backtrace 中出现上述调用点 +4 | 70 项 infra 的第 1 项（BB）已执行到创建 worker；返回值为负（`-1024/-1023`）表示线程未真正起跑 |
| N3 UI 线程创建（参考） | 同上 | `0xc0b118`（`Application_System_Init` 内） | backtrace 中出现 `0xc0b11c` | UI worker 创建请求；与 N3 的 `uxengine_init2` LR 联合判读 |
| N11 senser | `osal_reg_sync_msg_queue_cb`（PLT `0xb17970`） | `0xc15084 / 0xc150b8` | `0xc15088 / 0xc150bc` | App::initialize 已越过 infra 段 |
| N13→N14 | `GRM_fbrmRegisterTriggerFrameworkCb`（PLT `0xb173c0`） | `0xc09e48` | `0xc09e4c` | `manager::initialize`（`0xc09e0c`）已返回；拿到回调 `cb` 应等于 `base+0xc091d0`，`user` 应为 App 指针 |
| N12 timer（需先撤销 `0xc09e50` NOP） | `osal_snd_sync_direct`（PLT `0xb18c00`）、`osal_reg_msg_queue_cb`（PLT `0xb17b30`） | `0xc09c68 / 0xc09ce4`、`0xc09c98` | `0xc09c6c / 0xc09ce8`、`0xc09c9c` | start_utimer 实际执行；记录 qid 是否为 `0x910040` |
| N12 tick 生产 | `osal_snd_msg`（PLT `0xb1a120`） | `0xc09bbc` | `0xc09bc0` | `exec_utimer` 向 `0x5503e0` 发 `0x02010094` |
| App 事件循环 | `osal_rcv_msg_tmo`（PLT `0xb19ec0`） | `0xc0a208` | `0xc0a20c` | 主循环在等 App 队列（Codex 观察器已覆盖） |
| BB 等待点（参考） | `osal_rcv_msg_tmo` | — | `0x20efbbc / 0x20f80f8 / 0x20ef7cc / 0x20ef554` | 分别对应 finalize / worker / 临时请求 / 清理（Codex 已绑定） |

N15–N18（model_start、boot 过渡、MODEL_POWER_ON_COMP、HOME open、presenter 工厂）位于 appFw 内部，没有直接导入可用；在 N14 证实之前不建议为它们做内联钩子。

## 3. 帧触发回调的“透明包装”（N14 的关键观察）

拦截 `GRM_fbrmRegisterTriggerFrameworkCb` 时不改变语义：

1. 记录 `cb`、`user`、LR；
2. 把 `cb` 替换为一个**透明跳板**后转发给真函数；跳板每次被调用只计数/打印序号，然后以原寄存器状态跳到原 `cb`；
3. 判读：若整轮运行中跳板计数为 0，即“回调已注册但从未被触发”——支持闭包报告 N14 的预测，需要 Q3 决定是否补触发源。

跳板必须对任意签名透明（参数个数、浮点参数、栈参数都未知），因此不用 C 包装函数，而用汇编：

```asm
// 透明入口跳板：记录后以原 x0..x7 / v0..v7 / sp / x30 跳到原函数
fx6_tramp_N:
    stp  x29, x30, [sp, #-0xa0]!
    stp  x0,  x1,  [sp, #0x10]
    stp  x2,  x3,  [sp, #0x20]
    stp  x4,  x5,  [sp, #0x30]
    stp  x6,  x7,  [sp, #0x40]
    stp  q0,  q1,  [sp, #0x50]      // 如需保存 v0..v7，相应扩大栈帧
    // ... q2..q7 ...
    mov  x0, #N                     // 节点编号
    mov  x1, x30                    // 原 LR
    bl   fx6_reach_log              // C 侧：计数 + dladdr + 有界打印，保存/恢复 errno
    // 逆序恢复 q*/x0..x7
    ldp  x29, x30, [sp], #0xa0
    adrp x16, fx6_real_N
    ldr  x16, [x16, :lo12:fx6_real_N]
    br   x16                        // 不改 LR：原函数直接返回调用者
```

要点：跳板只看“进入”，不看返回；返回值观察留给已知 ABI 的函数（如 Codex 已确认的 `osal_rcv_msg_tmo`）。`fx6_reach_log` 需有上限计数与丢样计数，避免日志改变时序过多。

## 4. 与现有工作的边界

- 不重复 Codex 的 receive 观察器；本表只新增“节点到达”判据。
- 不修改 DeepSeek 文件；若运行线采用，建议与 Codex 观察器合并成同一个 observer-only 轮，**不与任何行为补丁同轮**。
- PLT 目标地址取自 [dependency-result.json](../2026-11-07-fx6-queue-contract/queue-screen-dependency/dependency-result.json) 与 [route-result.json](../2026-11-07-fx6-native-lifecycle/deep-screen/route-result.json)；导入名除已在 JSON 中出现者外，按 `.rela.plt` 复核后再使用。
