# FX6 第三轮：先确认等待者，保留队列生命周期

2026-11-07，接续[原厂生命周期研究](../2026-11-07-fx6-native-lifecycle/README.md)。本轮复核已结束的 Candidates 291–293，完成三条并行静态/证据研究，并实现只观察队列调用的候选。没有启动或控制 VM、修改共享候选或操作相机。

## 推进结果

**293 的日志窗口不再出现异常，但画面仍全零；下一步应先取得真实 caller LR 和队列 ID。不能把 `wchan=osal_rcv_msg_tmo` 直接归因到某条无限等待，更不能直接缩短退出握手。**

已取得三个具体结论：

1. 计划调整的 `appFw+0x20efbb8` 是 `infra_wrapper_bb::detail::finalize()` 内的退出握手。它接收后不检查返回码，随即 free 消息、删队列和 join 五个 worker；直接改短超时不能保留原契约。
2. 293 的 `+0x12d8254` NOP 跳过了 **70 项 infrastructure 初始化**，其中 BB 初始化会创建五个 worker；`+0xc09e50` NOP 还跳过了向 App 队列生产事件的定时器。无异常不能证明这些必需链路已完成。
3. 已实现并离线验证[队列观察候选](observer/observe_osal_queue.c)。它记录 LR/TID/qid/timeout 和进入、返回信息；原样转发参数、输出槽和返回码，不调整等待、不制造消息、不删除队列。

## 实际等待仍未归属

293 完成 run 为 `cp-bind-4cdf812e`。原始串口的有限窗口中未匹配到 assert、SEGV 或 kernel Oops；gpe0/gpe1 各 2,211,840 B，均全零。

PID217 的 TID225 有 26 组完整 `wchan` 采样，均为 `osal_rcv_msg_tmo`。采集器没有线程名、用户态 PC/LR、qid 或用户栈，因此不能把 TID225 确认为原厂 UI worker，亦不能把它绑定到 `+0x20efbb8` 或 `0x910040`。

291→293 的 init、launcher、AppFw 和其余 476 个库 entry 相同，但 shim 同时新增五个 NOP、MonCtrl 空对象 guard 和两个 Backup 覆盖值，不能把结果单归因于一处 NOP。293 的代码写入路径和五条 `mprotect=0` 自报已核实；没有写后内存读回，故不宣称完成逐字节运行完整性验收。**容器内 AppFw 原件哈希不变，不代表运行字节未改写。**

292 属于另一个 bootin 启动分支，shim 还回退到289/290版；其异常为 `im.elf` 中 `libMWF+0x409d0 / MonQueue::GetQueueRemain()`，应与291的 MonCtrl 故障分开。详见[运行复核](candidate293-review/README.md)。

## 区分四种 BB 等待和 App 事件循环

以下静态地址绑定 AppFw SHA `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。表中是调用后的 **LR**，不是 recv 指令地址：

| 调用后 LR | 用途 | 直接改短超时的问题 |
|---|---|---|
| `+0x20efbbc` | BB finalize 终止请求/回执 | 未确认 worker 退出就 free、删队列和 join |
| `+0x20f80f8` | BB worker 收请求 | 未检查 rc 就调用 `osal_get_msg_src(msg)`，可能访问无效消息 |
| `+0x20ef7cc` | 通用临时请求/响应 | 可能破坏请求所有权和响应配对 |
| `+0x20ef554` | 临时队列残留清理 | 不能从其他等待点继承退出/超时假设 |
| `+0xc0a20c` | App 事件循环 | 无消息时等待可能是正常行为，先核生产者和实际 qid |

实际 `libosal_uipc.so` 为 43,752 B、SHA `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a`，ABI 是 `int fn(unsigned int qid, void **out, int timeout)`。timeout 为32位有符号值，不能按64位超时策略替换。库层不会替调用者初始化输出槽。

finalize 向全局动态 qid 发送四字节零请求；worker 以消息源等于该 qid 判别终止请求，另发零回执后退出。这是资源退出协议，不能把“超时返回”解释为“退出完成”。详见[队列契约](queue-contract/README.md)。

## 已移除的 App 消息生产链

`0x910040` 是 App 定时器 API 使用的服务队列目的地；实际 App 收消息的队列是 `0x5503e0`。

原厂 `App::start_utimer +0xc09c14` 注册回调 `+0xc09bd4`，该回调进入 `exec_utimer +0xc09ac8`，生产首 word 为 `0x02010094` 的消息并发送到 `0x5503e0`。App 的 `recv_event_i +0xc0a1d0` 从同一队列读取，转换器将此消息映射为内部 type 5。

293 NOP 的 `+0xc09e50` 正是 start_utimer 调用点，因此至少移除了一个确定的 App 生产者。这不能证明缺 tick 是唯一停顿根因，也不允许将该消息伪造成 `MODEL_POWER_ON_COMP` 或启动分支消息 `0x0100003c`。

其他入口已区分：`+0xc14dfc` 属于 adjust::senser 回调注册；`+0x1397450` 封装 model_start；`+0xdf91e8` 请求初始 boot 屏过渡。该过渡参数组准确为 `{0x255,0,0x255}`，即 `{597,0,597}`；**不是十进制255**。详见[生产者与屏幕依赖](queue-screen-dependency/REPORT.md)。

## 已实现的观察候选和验证

[observe_osal_queue.c](observer/observe_osal_queue.c) 在调用前记录 seq、TID、LR、DSO相对地址、分类、qid、原始 int timeout、outslot地址及实际解析到的下一层函数；返回后记录相同seq、rc和errno。

- 不读取或写入 `*out`；不调整 timeout、消息、qid 或原厂初始化。
- 日志/符号查找会改变 errno，因此调用真实函数前恢复调用者 errno，返回日志后恢复真实函数留下的 errno。OSAL 返回码为首要结果，不能把任意 errno 值都解释成错误。
- 使用 `RTLD_NEXT` 并记录实际下一层 DSO，不能只凭钩子函数名字认定命中了原厂库。解析不到函数或解析到自身时退出126，不伪造接收成功。
- 最多记录1,024次调用；达到上限后打印标记并继续原样转发。缺少返回日志仅表示该日志窗口内没有观察到返回，不能自动定为死锁。

[build_and_check.py](observer/build_and_check.py) 已用 Clang 编译出 **AArch64 ELF `ET_REL` 目标文件**，检查只导出 `osal_rcv_msg_tmo`、未引入意外编译器运行库依赖。三组隔离宿主检查通过：参数/输出所有权/返回值/errno及caller分类；缺失符号拒绝；解析到自身拒绝。宿主替身故意破坏 errno，以验证观察代码正确恢复。

```sh
python3 -B reports/2026-11-07-fx6-queue-contract/observer/build_and_check.py \
  > /path/to/build-check.json
```

生成的对象文件和宿主检查程序保留在仓库忽略的 `work/`；[构建检查回执](observer/build-check.json) 保存精确命令、源/目标指纹与结果。**尚未链接成 guest `.so`、打包 CPIO 或执行 guest。** 宿主检查不证明真实链接器解析、运行时 ABI、时序或菜单效果。日志自身也会影响时序，不得用于性能结论。

下一轮由现有运行负责人沿用其 VM 窗口：保持一个已明确的输入基线，仅加入观察；先拿到真实 LR/qid，再决定应恢复 App timer/infra，还是调查退出路径。若要恢复原厂调用，应按原厂初始化和消息所有权契约处理，不把恢复全部调用与改等待等多个变化混为一次归因。

本轮已通过 Orca 内部状态消息回传关键发现及观察候选（`msg_1ad3aa9876c5`、`msg_e50f87712bda`、`msg_30b0f2d0163c`）。提交回执不证明收件 agent 已采用或运行。

## 资料与边界

动态包装的 `RTLD_NEXT` 语义参考 [Linux dlsym](https://man7.org/linux/man-pages/man3/dlsym.3.html)；errno 的线程局部性及仅在错误返回时有解释意义，参考 [Linux errno](https://man7.org/linux/man-pages/man3/errno.3.html)。这些公共文档仅支持包装器语义，Sony 私有队列契约由本机输入的静态/运行证据证明。

原生菜单像素、按键闭环与实机兼容仍未通过。本轮没有削弱现有门禁、伪造原厂完成事件或改变运行政策。
