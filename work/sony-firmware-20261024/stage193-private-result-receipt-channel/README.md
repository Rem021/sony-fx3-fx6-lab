# FX3 私有结果回执与存活身份握手

2026-10-29。**38项进程整合＋20项回执检查＝58项本地检查通过**。使用自建假设备和普通文件；原生候选只编译，未运行管理员程序或相机操作。新候选09仍为 `FX3_NATIVE_RELEASED=0`，原生通道固定 observe/status/end。

新增的是主机控制器的结果链路。它不能证明机身退出、当前p1备份、掉电恢复、独立救砖或目标主录可用。

## 这次解决的问题

- [owner_receipt.c](owner_receipt.c)从入口的私有结果制作固定1024字节记录，经原来已核对peer的Unix stream发送；不从用户文件取最终状态。记录绑定UID、PID、微秒出生时间、nonce、固定grant、ABI4结果和校验摘要。
- [receipt_receiver.py](receipt_receiver.py)先核对存活helper的实际内核身份、可执行路径及文件哈希，在accept时核对socket的UID/PID，再给固定nonce握手。入口收到握手后重查停止请求、报告有效性、观察者身份及时间，才可能取得owner。未握手、错误nonce、附带FD和握手前停止均不进入owner。
- `COMPLETE`只表示本次主机调用已返回；还要区分返回已观察、返回不明、设备动作前拒绝，并独立观察原helper退出。`HELD`只报告保留，继续持有进程、对象和排他日志，不能充作完成。没有回执或回执不完整保持UNKNOWN，不自动重试。
- 共享文件被截断或伪造completed，不改变私有回执或保留状态。收到的SCM_RIGHTS副本会关闭并拒绝，不导入文件或设备句柄。

这里的身份依据是本次存活握手和同一连接；SHA256只检查完整性，**不是数字签名**。控制器重启后，不能只读用户可改的回执文件就重新建立可信身份。该持久化验证和完整启动监督仍待整合。

## 测试与修复记录

| 证据 | 结果与范围 |
| --- | --- |
| [最终构建](build-receipt-v3.json) | 假设备helper使用ASan/UBSan；native仅编译/链接，入口关闭 |
| [进程整合](integration-results.json) | 38项；原同进程owner、私有状态、预算、排他及阻塞保留回归 |
| [回执检查](receipt-results.json) | 20项；文件损坏、假完成、阻塞超时、真实peer、握手拒绝、格式/重放、进程观察及分段/截断/超长/FD流 |
| [复核](verification-receipt.json) | 源码、产物和测试摘要；低层设备代码与192保持相同 |
| [限制](implementation-review.json) | 真实root跨UID、完整监督器、设备与恢复未验 |

首版测试发现：peer退出后再查询 `LOCAL_PEERPID` 可得到ENOTCONN；已改成在helper仍存活时完成身份握手，保留同一连接接收完整结果。Apple [XNU实现](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_usrreq.c)也在连接已拆除时返回该错误。旧构建、失败和对应源码均保留；另一次格式测试误把被损坏的摘要重新算正确，已修正测试并保留原失败。

真实Unix peer与出生时间检查只在普通用户下执行；部分格式输入、进程观察分支及传输攻击为明确构造的本地模型，不能算真实root或相机验收。192的18项日志测试和191的55项底层检查沿用旧证据，没有重复计入58。

## 下一步

将固定bootstrap、Terminal入口和用户监督器接到这条链路；补充控制器重启后的可信回执核对，固定实际helper PID与relay PID的区分。代码和方案具体可复核后，再安排一次另行批准的root→UID501、仅主机假对象对照。

Sony鉴权、模式切换、机身文件/p1读取、模块执行与固件写入均未在本轮授权或运行。旧一次授权没有复用；恢复优先目标及全部16项要求保持，`goal_complete=false`、`persistent_write_release=false`。
