# Candidate 293 的队列生产者与屏幕启动依赖（2026-11-07）

**结论：293 至少静态删除了一个真实的 App 队列消息生产者：`App::start_utimer`。`0x910040` 是定时器服务队列目的地，不是 App 的启动事件 ID。** 另外，`0x12d8254` 原指令调用一个包含 70 个 infrastructure 生命周期初始化包装器的总入口；NOP 它的影响远大于跳过一项服务注册。当前不能把“没有 SEGV、停在接收队列”认定为原生 UI 已初始化完成。

这两点解释了为什么应先审查被删除的生产链；本轮没有证明它们是当前等待的唯一根因，也没有生成或注入完成事件。

## 输入与执行边界

- 原厂 FX6 `appFw.so`：50,520,424 bytes，SHA-256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。
- 路径：`/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so`。
- 对照源：`/tmp/libgrm-fbinit25-293.c`，本次读取的 bytes / SHA 记录在 `dependency-result.json`；未复制此共享文件，也未证明其与正在运行的二进制逐字节一致。
- 全部地址为上述 appFw 的相对 VMA。只读分析；未启动/控制 VM，未修改共享 shim、donor 或候选。

## 四个入口分别做什么

| 位置 | 已证明功能 | 调用先后 |
|---|---|---|
| `0xc14dfc` | 跳转 `0xc15060`，注册 `adjust::senser` 两个同步队列回调：`0x01050244 → 0xc1543c`、`0x02170625 → 0xc15274` | App initialize 中 `0xc09df0`；在初始模型/infra 初始化返回之后、App 定时器启动之前 |
| `0x1397450` | 模型 value-id `0x3b19` 的封装；`0x1397494 → 0x1395c3c`，原厂诊断名为 `model::model_api::detail::model_start()` | 主循环的启动分支 `0xc0a860`，位于下项之前 |
| `0xdf91e8` | manager 初始屏幕过渡：把 screen-id 引用参数组设为 `{0x255, 0, 0x255}`，清重入状态，`0xdf9230 → 0xdf8d6c` | `0xc0a870`，在 `model_start()` 返回之后。registry id 0 为 boot；不是直接 HOME 构造 |
| `0x12d8254` | 原厂 `BL 0x20ed13c`，后者顺序执行 70 个 infrastructure 初始化包装器 | 在 `App initialize → 0x12d9fc8 → 0x12d8174` 的早期路径，先于 `0xc14dfc` 和 App 定时器 |

`0xc14dfc` 的身份由回调实现邻近的原厂 `000_main/adjust/senser.cpp`、`adjust::senser::biz_senser_cb` 以及两个 `osal_reg_sync_msg_queue_cb` 调用共同约束；不能把它当成主屏幕 model-start 入口。

**sentinel 数值勘误：`0x255`＝十进制 `597`。** 初始 screen-id 参数组为 **`{0x255,0x0,0x255}`＝十进制 `{597,0,597}`**；先前协调消息漏前缀写成 `{255,0,255}`，应按此纠正。`0xdf9204` 指令 word `0x52804aa0`（little-endian `a04a8052`）明确是 `mov w0,#0x255`；`0xdf9214` 将它写入第三参，`0xdf921c` 的 `stp w0,wzr,[x29,#0x30]` 写入前两参。HOME controller 在 `0xf2dedc` 用 word `0x7109541f`（`1f540971`）执行 `cmp w0,#0x255`。脚本/JSON 均明确校验 hex 和 decimal，不能解释为十进制 255（`0xff`）。

## `0x910040` 与 App 消息队列不是一回事

原厂 PLT 符号提供精确分类：

| 常量 | 调用位置/数据位置 | 作用 |
|---|---|---|
| **`0x910040`** | `0xc09c68 / 0xc09ce4`，作为 `osal_snd_sync_direct` 的第一个参数 | App timer 分配/设置等操作的服务队列目的地 |
| **`0x5503e0`** | `exec_utimer` 的 `0xc09bbc → osal_snd_msg`；`recv_event_i` 的 `0xc0a208 → osal_rcv_msg_tmo` | 同一条 App 消息队列的发送/接收端 |
| **`0x02010094`** | `exec_utimer` 写入消息首 word；`0xc09fd8` 比较该 word | 真正的 timer 消息标识；App 转换器将它映射成内部 event type **5** |

因此，把 `0x910040` 伪造成 App 的消息首 word，或把它直接发给 App 队列，都没有原厂调用链依据。

## 被删掉的 timer 生产链已闭合

原厂顺序如下：

1. `App initialize +0xc09e50 → App::start_utimer +0xc09c14`。
2. 向 `0x910040` 发同步 direct request，获取 timer 相关句柄和返回队列。
3. `+0xc09c98 → osal_reg_msg_queue_cb` 注册返回队列回调 `+0xc09498`；随后再次向 timer 服务设置 callback `+0xc09bd4`、user=`App*`，再启动 timer。
4. callback `+0xc09bd4` 尾跳 **`App::exec_utimer +0xc09ac8`**。
5. `exec_utimer` 在 **`0x5503e0`** 分配消息，设置首 word **`0x02010094`**、sender **`0x830128`**，然后通过 `osal_snd_msg` 发回 App 队列。
6. `App::recv_event_i +0xc0a1d0` 从同一队列取消息；转换器识别 sender / word，并将内部 type 设为 **5**。

293 对照源的 `offs[5]` 包含 **`0xc09e50`**。故只按该源的改动推断，原厂 timer 生产链已被主动跳过。它与 App 的正常事件/绘制节拍相关，但**此 timer 消息不是主循环检查的 `0x0100003c` 启动分支消息**，也不是 `MODEL_POWER_ON_COMP`。恢复 tick 本身不能被称为恢复开机完成事件。

本轮未定位 `0x910040` 服务提供者的完整初始化/运行状态；也未读取 live 队列内容或调用栈来判断当前等待的是永久阻塞还是正常超时等待。

## `0x12d8254` NOP 的影响范围

原厂 `0x20ed13c` 执行 **69 个 BL + 1 个尾 B**，共 70 个 infrastructure 生命周期包装器。第一个包装器 `0x20cf5dc` 进入 **`infra_wrapper_bb::detail::initialize +0x20ef9d0`**：原厂诊断字符串明确给出该身份，其函数创建 **5 个后台 worker**（`0x20efa1c / 0x20efa6c / 0x20efabc / 0x20efad8 / 0x20efaf4` 均调用线程封装 `0x222dd58`）。

因此，“跳过会阻塞的一项回调注册”不足以描述这个 NOP。它去掉整组 infrastructure 初始化及其 worker 创建，可能同时失去后续硬件/模型输入的生产者。**本轮没有把某一个被删 worker 强认作 `MODEL_POWER_ON_COMP` 的唯一生产者**，也没有证明这 70 项中的每一项都是菜单首帧的硬性条件。

293 同时跳过 `0x12d824c`（原调用启动一个 worker）、`0x12d8250`、`0x12d825c` 和 `0xc09e50`。这些差异累计后，等待队列本身无法证明原厂启动依赖已满足。

## 最小后续观察

- 保留真实队列区分：记录等待调用的 **qid、timeout、调用者 PC**，同时观察同一 qid 的真实发送者和注册状态；不要用捏造“完成”消息使消费者前进。
- 观察 `App::start_utimer` 是否真正执行、timer 服务返回值/句柄、回调是否触发和 `0x02010094` 是否进入 `0x5503e0`。这能单独验证被删除的 timer 生产者。
- 单独观察 `0x1397450 → model_start` 和 `0xdf91e8 → boot` 是否到达；当前源码路径存在不等于运行已到达。
- 对 `0x20ed13c` 分项建立已执行/未执行/阻塞项，不再把全部 70 项统称“一项注册”。需要恢复时由运行负责人以最小候选排查实际首个阻塞项。

本轮产物为 **静态依赖证据**，不包含修补方案应用、guest 成功、首帧或可操作菜单验收。

## 重跑

```sh
python3 -B audit_queue_dependency.py /path/to/pinned/fx6/appFw.so \
  --shim /path/to/libgrm-fbinit25-293.c > dependency-result.json
```

脚本只用标准库；SHA 错误时拒绝。校验原厂导入符号、关键 B/BL 调用、队列/消息常量、初始化包装器数量和对照源 NOP 列表。输出结构性元数据，不导出固件/资源载荷或大段反汇编。
