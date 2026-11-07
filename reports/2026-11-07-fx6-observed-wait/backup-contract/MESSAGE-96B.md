# 0x92a208fc / 96B 消息来源契约（2026-11-07）

**结果：这条日志与当前运行候选内核 UPM 的 DFS 通知生产路径吻合；不是已证实的 UX 资源装载请求，也不是指针宽度污染证据。`96B` 与原 FX6 的 `40B` 差异来自不同二进制的显式分配指令。该目的使用异步 `osal_snd_msg`；不能因为 `no_reply=1` 就为它制造同步应答。** 还没有该条消息的 caller PC/TID，不能把它与 AppFw 的 futex 等待建立因果关系。

只读验证脚本为 [inspect_96b_contract.py](inspect_96b_contract.py)，可复核断言和冻结日志在 [message-96b-evidence.json](message-96b-evidence.json)，状态 PASS。所有 `.text+偏移` 均针对各自 ET_REL 模块的 `.text`，不是运行 VA；appFw/DSO 数字则是 ELF VA。

## 直接绑定本轮产物

本轮 CPIO：`work/fx6-observer-integration-20261107/guest-observer-only295.cpio`，SHA `d02c7909458dcf8dff73fdf426953d07034cb386f8c8bd0bbd40a9440d32569e`。读取成员到内存，不解包或改写。

| 来源 | 大小 | SHA-256 |
|---|---:|---|
| 本轮 CPIO `usr/kmod/upm.ko` | 453,896 | 5be2aa0b6d6c0a31bb7802400fcd688a980583a08e945245adad7700b9882994 |
| 真正 FX6 donor `nflasha15-files/kmod/upm.ko` | 414,720 | 34d5bca76b6750f2af36f34404c305aaef71aeabab1d3ae52a9e00b65c6b7970 |
| 本轮 CPIO `usr/kmod/osal_uipc.ko` | 76,168 | 6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38 |
| 真正 FX6 `libUsbControl.so` | 135,424 | 951d1da8a4366dc8cf7bf475181344ea487e661869701218a2343e9c9ecf1483 |

冻结串口 `observer-004ab971f4/serial.log` 第 1313 行是题述最后一条消息，第 1314 行是 source。前面第 1132/1145 行同目的、同为 96B，kind 分别 3/4，低 32 位参数分别 `13/26`。JSON 保留所有该目的行及文件哈希，不只选择最后一条。

## 96B 来自当前内核生产者的显式长度

当前 `upm.ko` 中：

| 函数或路径 | 分配调用 | `w2` | 发送调用 |
|---|---|---:|---|
| `k_upm_off_seq_enter_active` | `.text+0x63ec` | 0x60 | `.text+0x641c → osal_snd_msg` |
| `k_upm_off_seq_exit_active` | `.text+0x65b4` | 0x60 | `.text+0x65e4 → osal_snd_msg` |
| DFS 同步操作后的 kind4 通知分支 | `.text+0x207c4` | 0x60 | `.text+0x207f8 → osal_snd_msg` |
| DFS kind4 辅助路径 | `.text+0x23294` | 0x60 | `.text+0x232c4 → osal_snd_msg` |

以上调用由 `.rela.text` 的原始符号重定位绑定，不把 ET_REL 的未重定位 `bl #自身地址` 误认作递归。完整模块还有 `k_upm_off_factor_handler_inacting_cp`、`upm_mp_dfs_state_machine_resume` 等同目的通知路径。**冻结日志不能区分最后一条具体出自哪一个；只凭 kind4/参数13不足以唯一归属。**

真正 FX6 donor 对应 `k_upm_off_seq_enter_active` `.text+0x63c4`、`exit_active` `.text+0x658c` 分配的却是 **0x28（40）**。原 FX6 用户态 `libUsbControl.so` 同构发送函数 VA `0x12e40` 也是 40B，实际命名调用者是 `UFW::DfsWrapper::ok()` / `ng()`。实际 FX6 appFw 的同构函数 VA `0x215ddb4` 也分配 40B，其两个直接调用点为 `0x2162254/0x21622bc`，分别 kind3/4。

因此，最早只看实际 FX6 用户态函数会出现“请求40，日志96”的表象；加入**本轮实际 CPIO 内核模块**后，已有完全匹配 96B 的生产者。当前证据不要求用 allocator 扩宽、ABI 截断或日志解码错误解释这个差异，也不能把当前模块直接称为原厂 FX6 模块。

## 有效字段与残留数据

这些生产者新分配消息后都写：

| body 偏移 | 写入范围 | 已证明的含义 |
|---|---:|---|
| +0 | 4B | 0（discriminator） |
| +4 | 4B | kind，所见为 3/4 |
| +8 | 8B | 同步操作结果的参数块前 8B，属于块复制 |
| +16 | 4B | 参数块最后 4B |
| +20 到分配末端 | 无初始化写入证明 | 不能解释为规范参数或指针数组 |

最后一条前 20B 按 u32 是 `[0, 4, 13, 0xffffff80, 0x008ea700]`。低 32 位的参数 13 与同步参数块来源吻合，但后两个 word 的具体类型/语义未闭合。`str xN` 的 8B 拷贝并不单独证明它携带指针。

日志只抓前 40B，因而其中后 20B 已超出上述明确写入的前缀。`+20/+28/+36` 等反复出现的 `0xffffff80` 可以是内核消息池残留；代码没有把它们定义为可解引用的指针。**不能据此宣称 32→64 位指针污染，更不能把这些字节用于地址映射或完成回调。** 参数块内部的额外 8B 也不可贸然归零或“修复”；需要其真正处理者/字段证明。

本轮实际 `osal_uipc.ko` 的分配器 `.text+0x3370/0x3378/0x338c` 显式构造并写入 `0xa5a5a5a5`；body 指针为 allocation+0x18，而 `osal_get_msg_src` `.text+0x5e70` 读取 body-0xc，正好取到该初始化值。**source=a5a5a5a5 是原分配路径的未设 source 标记，不是回复队列，也不是宽度污染证据。** `osal_msg_size` `.text+0x5e54` 则读取 body-8 的逻辑长度，与这些生产者的 96B 分配一致。

## 等待关系与 Backup 的区别

可见 UPM 路径先用 `osal_snd_sync_msg` 发送另一个目的 **`0x80920901`** 的 20B 本地请求，取业务结果、拷回 12B 参数块并释放；业务结果成功后才分配 `0x92a208fc` 的通知并 `osal_snd_msg`。因此，本条通知出现，说明相应生产者已经越过它前面的那次本地同步调用；不是仍在等这次 `0x92a208fc` 请求的同步 reply。

这不排除 CP 后续事件与系统状态存在间接依赖，也不证明当前未知路由“无需实现”。它只排除了“看到 no_reply 就必定导致当前 AppFw futex”的推断。当前 CP helper 对该未知目的直接记录并返回0、不释放；确实没有完成其真实接收者职责，但安全修复仍需原消费者/所有权/后续状态契约。

本目录前一轮的 `Backup_read/backup_sync_msg` 是 **Backup 本地远端结果/输出契约错误**；此处是 **UPM/DFS 异步通知路由**。两者不使用相同目的，也不能因为日志前缀为 `FX3_BACKUP_CP_` 就把该消息解释成 Backup 操作。kind3/4 不应套用 Backup 的 op3/op4。当前没有证明这一条消息是 UI 资源完成通知、应用消息队列 ID 或来自 AppFw TID224。

## 后续最小观测

等待另一 agent 的 ptrace 调用链结果，以实际用户态调用栈绑定 AppFw/uxengine 的 futex 对象。若仍需定位本消息，下一次只记录这个目的的 sender caller PC/TID 与前20B，并分别识别内核/用户发送源；不做通用回复、不解引用尾部、不改变超时或返回值。若要实现 handler，先定位 CP `0x92a208fc` 对应的原接收者并确认通知所有权和后续动作。

本轮仅新增本目录脚本、JSON 与此报告；无 VM、相机、shim/供体/候选修改或 Git 写入。通用 AArch64 参数/返回寄存器解释沿用已核对的 Arm [AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)；该公开规则不证明 Sony 私有消息字段。
