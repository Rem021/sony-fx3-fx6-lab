# FX6 BB 队列契约：+0x20efbb8 是 finalize 终止握手

2026-11-07；只读静态分析与现有 293 日志核验。未启动/暂停/修改 VM，未改变任何固件、共享 shim 或队列。输入仅为用户本机 BYOF 资料，工具不输出固件二进制。

## 结论

**不能把 `appFw+0x20efbb8` 的 timeout 从 `-1` 直接改短并让函数继续。该 site 位于 BB 模块 finalizer，接收之后无返回码检查，接着释放消息、删除队列、清零全局 qid、join 五个 worker。超时返回不等于终止握手完成。**

而且本次读取的 293 `cp-bind-4cdf812e/serial.log` 只有反复 `osal_rcv_msg_tmo` wchan，没有实际 LR=`appFw+0x20efbbc` 或 qid=`0x910040` 记录。**尚未证明线程 225 正在这个调用点等待。** 当前正确下一步是记录真实 caller/LR 与 qid，先区分四种静态等待用途。

## 输入绑定

| 输入 | 字节数 | SHA-256 |
|---|---:|---|
| 真 FX6 `appFw.so` | 50,520,424 | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| 真 `libosal_uipc.so` | 43,752 | `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a` |

293 CPIO 的这两个成员与上述输入摘要一致；这不代表 guest 内存仍未被运行时 shim 改动。293 已存在的 NOP 日志表明它执行过 runtime patch，因此本报告区分原厂静态行为与当前运行行为。

## 1. 真实 ABI 与等待点分类

实际 `libosal_uipc.so` 导出 `osal_rcv_msg_tmo` 位于 `+0x6468`。寄存器契约为：

```c
int osal_rcv_msg_tmo(uint32_t qid, void **output, int timeout);
/* qid = w0, output = x1, timeout = w2, return = w0 */
```

timeout 的 `-1` 是 32 位有符号值。qid 是 32 位 ID，库以 bit 15 区分用户态队列与内核代理队列。若实际 qid 为 `0x00910040`，其 bit 15 为 0，会走 `u_osal_rcv_msg_tmo`（`+0x3c60`）的 ioctl `0x80000007` 分支。**这个参数是队列 ID，不是请求或响应的消息 code。**

| site | 实际返回 LR | 用途 |
|---|---|---|
| `appFw+0x20efbb8` | `+0x20efbbc` | `infra_wrapper_bb::detail::finalize()` 等待 worker 终止回执 |
| `appFw+0x20f80f4` | `+0x20f80f8` | BB worker 正常消息循环/终止请求入口 |
| `appFw+0x20ef7c8` | `+0x20ef7cc` | 通用同步 request/response helper 等待响应 |
| `appFw+0x20ef550` | `+0x20ef554` | 临时动态队列发现残留消息后的清理/诊断 |

只看 `osal_rcv_msg_tmo` wchan 无法分辨以上用途。四处都是原厂无限等待，但所需恢复动作完全不同。

## 2. 队列创建、存储和 worker owner

BB 初始化函数 `appFw+0x20ef9d0`：

1. 调 `osal_subsystem_id()`，以当时 subsystem 的低 16 位作为 owner 参数；
2. 经 `+0x215c954` 调 `osal_dynamic_id(0x2a, owner, &global_qid)`；
3. 将动态 qid 写到 **`appFw+0x5c38594`**；这只是模块数据的 VMA 偏移，不是 guest 物理地址；
4. 用原厂线程管理器启动 thread type `0x41`，callback=`appFw+0x20f80b8`，handle 写 `+0x5c384e0`；
5. 同时创建 `+0x5c38590`、`+0x5c38514` 两个动态队列，并启动另外四个 worker。

`+0x215c954` 的 0x2a 来源是 type `2 | 0x28`；销毁对应 `+0x215c9ac` 的 `2 | 0x48 = 0x4a`。这建立了创建/释放配对。具体运行中 subsystem 的值以及 qid 是否就是 `0x910040`，仍需入口实参、`osal_subsystem_id` 返回值和创建输出一起记录，不能只凭 ID 高位或旧运行推定。

原厂直接调用方：`+0x20cf5f0` 调 BB initialize，`+0x20cf618` 调 BB finalize。若后续实际 LR 证明进入了 finalize，还要确认谁触发模块回收/失败清理，不能把它默认当成正常 UI 启动等待。

## 3. finalize 的请求/回执协议

函数入口 **`appFw+0x20efb08`**；其 assert 字符串 `+0x26022d8` 明确为 `void infra_wrapper_bb::detail::finalize()`。

原厂行为可概括为：

```text
qid = global(+0x5c38594)
分配 4 字节请求，payload 写 0
将请求 msg_src 设置为 qid
osal_snd_msg(qid, request)
osal_rcv_msg_tmo(qid, &slot, -1)      ← +0x20efbb8
osal_free_msg(qid, slot)              ← 不检查 receive rc
osal_dynamic_id(0x4a, 0, qid)         ← 释放队列
global_qid = 0
osal_wait_thread_exit(handle) ×5
```

BB worker（`+0x20f80b8`）从同一个全局 qid 接收：

```text
slot = NULL
osal_rcv_msg_tmo(qid, &slot, -1)      ← +0x20f80f4
source = osal_get_msg_src(slot)       ← 不检查 receive rc
若 source == global_qid：
    分配新的 4 字节 ack，payload 写 0，msg_src 设置为 qid
    osal_snd_msg(qid, ack)
    osal_free_msg(qid, 收到的请求)
    worker 返回
否则：处理其他来源消息并继续循环
```

worker 的终止分支依据 **消息元数据的 source==qid**，没有把 payload `0x910040` 当消息 code；4 字节 payload 为零。请求与 ack 是两次独立分配的消息。没有运行中 request/ack 指针与调度证据时，不能人工伪造一个零消息来认定握手完成。

## 4. 超时/错误路径会消费什么

### finalize site

`+0x20efbbc` 直接从同一个栈槽取指针并 free，不查看接收 rc。进入接收前，该槽保存发送请求指针。内核代理仅将槽地址与 timeout 传给 ioctl，库层不预先清空该槽，也未给调用方提供“失败后一定已写 NULL”的保证。

因此错误返回后可能面对保留的发送请求指针，或由内核改写后的空槽/其他值；内核失败写回契约本轮未完整核实，不能限定为一种情况。对仍在队列中/已交给 worker 的请求擅自 free，或删除尚未完成握手的队列，均会破坏原本所有权与生命周期。之后的 join 也可能继续永久等待。

### worker site

worker 接收前明确把槽置 NULL，但接收后无 rc 检查，立即调用 `osal_get_msg_src(slot)`。实际函数只有 `ldur w0, [x0, #-0xc]; ret`，没有 NULL 检查。将这个无限等待改为可失败的短等待，会让空指针错误路径变得可达。

### 通用 request/response site

`+0x20ef7c8` 返回后无 rc 检查，立即把输出槽指针当响应地址 `memcpy` 指定长度，再 free。若超时后槽为空或仍是旧请求，可能产生非法读取、把请求误当响应、乃至长度越界。不能全局把 OSAL 无限等待改短，也不能在 hook 中返回假的成功。

### 临时队列残留清理 site

`+0x20ef550` 返回后无 rc 检查便读取 source、size 并复制消息。它此前靠 `osal_stat_msgq` 的计数进入清理，依赖“应当确有消息”的原厂前提；额外引入超时失败不会自动获得合法恢复分支。

## 5. 具体观察点

父线程正在准备仅观察 hook；本报告建议记录而不改行为：

- `osal_dynamic_id`：caller module/LR、op、owner、输出 qid；把 `+0x20ef9ec` 对应的创建与 `+0x20efbd0` 对应的销毁区分；
- `osal_rcv_msg_tmo`：实际 caller/LR、真实 provider DSO、线程 TID、qid、原始 timeout、out-slot 地址、原始 rc/errno 和 entry/exit 序号；不读取 outmsg 内容；
- 对 LR 精确归属 `appFw+0x20efbbc`，另保留进入 finalize 的模块生命周期/上游 caller；
- 对 BB worker，确认 thread type 0x41 的原厂 callback 是否真的启动，是否收到 source==global_qid 的终止请求、是否送出 ack 并返回；
- 请求/响应关联必须有同一运行、同一 qid 和生命周期证据；过去其他候选里出现过 `0x910040` 不能绑定到 293。

若需要为诊断设置等待上限，也只能采用不向原厂错误路径返回的观察策略，例如在外部结束整次受控诊断并记录未完成，或保留原始无限等待、由观察线程定时输出状态。任何局部恢复实现都须显式处理原始 rc、消息所有权、qid 生命周期和 worker 退出状态；本轮没有验证此类实现。

## 可重跑验证

`inspect_queue_contract.py` 以 `--appfw`、`--osal` 指定用户本机输入，`--cpio` 可检查实际 293 成员摘要，`--serial` 可统计现有日志是否真的含偏移/qid 证据。它只输出 JSON，不写固件字节，依赖 `pyelftools` 与 `capstone`。`inspection-293.json` 是本次快照；CPIO reader 仅覆盖首个 newc archive，全容器重复覆盖检查仍由协调者负责。

已验证：脚本语法、finalize 原厂字符串、四个精确 LR、293 实际 OSAL 成员摘要一致。没有将静态分析或无 SEGV 视作原厂菜单成功。
