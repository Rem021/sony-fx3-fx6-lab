# Sony 官方 OSAL/UIPC/UDIF 与 FX6 BB 退出契约交叉验证

## 1. 哪个官方公开包与本机 CXD90057 源码对应？

### Takeaway

访问日期：2026-11-07。已重新绑定 Sony 官方 **FX6 V6.00** 的两个公开内核包与本机现有归档；两包均包含 UDIF，未找到目标 OSAL/UIPC 实现。`linux-kernel-u` 是 **Linux 4.9.186 内核源码**，不能根据 `-u` 名称把它当用户态 OSAL 源码。[官方型号页](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html) · [今日核验记录](sony_osal/public-source-verification.json)

### Cited Findings

- Sony 专业设备目录将 FX6 V6.00 与 FX3 Ver7.00 分开列项，FX6 页同时发布 `linux-kernel.tar.gz` 和 `linux-kernel-u.tar.gz`；未列名为 OSAL/UIPC 的独立包。页面标记是 **V6.00**，不能改写为本机 donor 的 **6.01**。[Sony 目录](https://oss.sony.net/Products/Linux/B2B/category01.html) · [FX6 V6.00](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html) · [FX3 Ver7.00](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html)
- FX6 主包本机为 **109,952,792 B**、SHA-256 `2e5bdfa72018cef6bdfa209635794973d7266c7ee657db094c7ee2c414dbcc42`，顶层 Makefile 为 **4.9.337**；副包为 **108,790,863 B**、SHA-256 `73cb30ba66cb3128a8d39de360f15ff746f75e60a7250e60d94697e21a61160b`，顶层 Makefile 为 **4.9.186**。今日官方 Azure HEAD 的长度和 Content-MD5 与两份本地文件一致；记录另保存 ETag、Last-Modified、访问时间。没有重新下载包。[主包原件 URL](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz) · [副包原件 URL](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel-u.tar.gz) · [本地摘要与 HEAD 比对](sony_osal/public-source-verification.json)
- 两包包含 `drivers/udif/`、`include/linux/udif/` 以及 CXD90057 平台目录/配置；UDIF 文件头注明 Sony 版权与 GPLv2，顶层 COPYING 为 Linux GPLv2 条款。核验器扫描主包 **36,058** 个相关文本源码文件、副包 **35,861** 个，未命中 `osal_rcv_msg_tmo`、`u_osal_rcv_msg_tmo`、`osal_dynamic_id`、`osal_snd_msg` 四个精确符号，目录名 OSAL/UIPC 检索也无命中。此结论限定于所查两个包和这些明确检索项。[Sony 主包](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz) · [Sony 副包](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel-u.tar.gz) · [可重跑库存核验器](sony_osal/verify_public_sources.py) · [库存结果](sony_osal/public-source-verification.json)
- 本机 `early-kernel/sony-oss-fx3/linux-kernel.tar.gz` 实际是 **109,896,431 B**、SHA-256 `d2f3dc059b69149c2eb5504ba85f25b515fc9263fdf1c3033d9513521db1fb15`；今日官方 FX3 Ver7 URL 为 **109,987,145 B**，Content-MD5 不同。它也不是历史记录所指 `bb2d9cc6...` 那份归档。因此该目录名不足以证明这份 tar 是当前官方逐字节原件；本轮使用已重绑的 FX6 包作公开 UDIF 参照。[当前 FX3 官方链接](https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX3_Ver.7.00/linux-kernel.tar.gz) · [比对结果](sony_osal/public-source-verification.json)

### Inferences

- 公开包的版本、平台目录和选定 UDIF 文件可作接口框架参照；即使版本同为 4.9.337，仍不能直接认定其构建配置、私有模块或 ABI 与当前 FX3 内核运行字节相同。[官方包身份](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html) · [本地检查范围](sony_osal/public-source-verification.json)
- FX3 本地 tar 的差异可能是包版本、重打包或其他来源差别；本轮没有证据选择其中一种解释，不能据此宣布文件损坏或擅自替换运行输入。[当前长度/摘要差异](sony_osal/public-source-verification.json)

### Gaps

- 官方分发的是 tar 归档，本轮未发现可核实的 Sony Git commit/tag；可稳定引用的是型号页面、完整 URL、内容摘要与具体文件摘要，而不是虚构提交号。
- 未找到这份 `libosal_uipc.so` 或 BB 用户态 finalizer 的 Sony 官方公开实现。未穷举所有无关型号/组件，故不写成“Sony 从未公开过 OSAL”。
- V6.00 公开包与本机 6.01 donor、FX3 运行内核的完整构建对应关系未建立；包 URL 中的日期和 Blob Last-Modified 不是固件发布日期。

## 2. 哪些队列语义有公开实现支持，哪些只由本机字节证明？

### Takeaway

公开代码支持 **UDIF 如何转发 ioctl、打印负返回值，以及自身 wait 封装的条件/超时语义**；它没有给出私有 OSAL 的消息指针所有权、队列删除或 BB 回执协议。BB finalizer 的危险错误路径仍来自绑定 SHA 的本机静态证据，不能换成 POSIX/Linux 通用规范作依据。[公开源码文件摘要](sony_osal/public-source-verification.json) · [本机队列契约](../../work/parallel-research-20261107/queue-contract/README.md)

### Cited Findings

- FX6 主包 `drivers/udif/cdev.c:94–100` 将命令和 arg 封装后交给设备注册的 ioctl callback；`include/linux/udif/macros.h:47–55` 对 callback 的负返回值输出设备名与数值，再返回该值。因此串口 `UDIF: cdev_ioctl() Line 100: uipc: warning ret = ...` 可说明 **uipc callback 返回了负值**，不能仅凭这一行确定具体哪个 OSAL 操作失败、哪个消息所有权已转移。[Sony 主包](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz) · [文件摘要和行定位](sony_osal/public-source-verification.json)
- 同包 `include/linux/udif/types.h` 的 UDIF 错误枚举是 Linux errno 包装，如 timeout 对应 `-ETIMEDOUT`；它不定义本机运行所见私有 UIPC 的 `-1020/-1021/-1022` 语义。不能将这些数值凭名称套成某个 POSIX 错误。[Sony 主包](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz) · [types.h 摘要](sony_osal/public-source-verification.json)
- `include/linux/udif/wait.h:61` 的无限等待采用 `MAX_SCHEDULE_TIMEOUT`；该头文件 `:99–102`、`:116–119` 的 timeout 封装使用 `(tmo)*HZ`。Linux 官方 wait 文档说明基础 `wait_event_timeout` 以 jiffies 为参数，并区分超时与条件满足返回。这些仅支撑该层接口，**不能推出私有 `osal_rcv_msg_tmo(...,-1)` 的换算单位或失败写回行为**。[Sony 主包 wait.h](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz) · [Linux 官方 wait 文档](https://www.kernel.org/doc/html/latest/driver-api/basics.html#c.wait_event_timeout) · [本地行定位](sony_osal/public-source-verification.json)
- 本机 `libosal_uipc.so` 为 **43,752 B**、SHA-256 `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a`。其 ABI 是 `int recv(uint32_t qid[w0], void **out[x1], int timeout[w2])`；qid bit15=0 的路径将 out-slot 地址和 timeout 交给 ioctl `0x80000007`，库层不预先清空槽。它的错误后 out-slot 最终值仍须由对应私有内核实现/实际返回观测判定。[绑定字节的解析记录](../../work/parallel-research-20261107/queue-contract/inspection-293.json) · [可重跑解析工具](../../work/parallel-research-20261107/queue-contract/inspect_queue_contract.py)
- 真 FX6 `appFw.so` 的 `+0x20efbb8` 在 `infra_wrapper_bb::detail::finalize()` 中：向动态 qid 发独立的 4B 零请求，source 设为同 qid，等响应后无 rc 检查便 free、删 qid、清零并 join 五个 worker；接收 worker 在 source==qid 时发新分配的 4B 零 ack、free 请求并返回。这是 **本机原厂字节的静态事实**，本轮没有公开 Sony 源码为其补证。[finalizer/worker 及输入 SHA 证据](../../work/parallel-research-20261107/queue-contract/README.md) · [调用解析 JSON](../../work/parallel-research-20261107/queue-contract/inspection-293.json)

### Inferences

- 观察到负 UDIF 日志时，应继续关联 command、callback、qid、caller 和返回码。公开 UDIF 只能证明传递/报错框架，不能把私有 ioctl 号按通用 `_IO*` 宏名称推成完整数据契约；Linux 官方文档也强调 ioctl 是驱动特定接口。[UDIF 转发证据](sony_osal/public-source-verification.json) · [Linux 官方 ioctl 文档](https://www.kernel.org/doc/html/latest/driver-api/ioctl.html)
- 将无限等待改短会引入原厂未检查的失败分支：worker 可能把空槽交给 `osal_get_msg_src`，finalizer 可能处理旧发送指针或空槽后提前销毁队列。风险判断来自上述本机错误路径，**不是**“所有无限等待都不能超时”的通用断言。[本机未检查 rc 的四处接收点](../../work/parallel-research-20261107/queue-contract/README.md)

### Gaps

- 尚无公开 Sony OSAL/UIPC 维护者代码支持对本协议把 `-1` 直接改成短 timeout 后继续执行。Linux 自身的可超时 wait 机制不构成这个操作的授权或正确性证明。
- 对内核队列分支，timeout 返回时是否保留 out-slot、消息是否仍排队、删除队列如何处置正在等待的接收者，本轮未由公开实现确定。不能假设输出一定 NULL，也不能假设原请求一定还归调用者。

## 3. 最少观察什么，才能区分正常等待与退出等待？

### Takeaway

先把 **实际 caller module+LR、线程、qid 生命周期与 recv entry/exit** 绑定到同一运行；只看到 `osal_rcv_msg_tmo` wchan 或看到 `0x910040`，无法判定 UI 正常等待、请求响应、残留清理还是 BB 退出握手。[四类静态 site](../../work/parallel-research-20261107/queue-contract/README.md)

### Cited Findings

- 静态返回 LR 可分类：finalize=`appFw+0x20efbbc`；BB worker=`+0x20f80f8`；同步 request/response helper=`+0x20ef7cc`；临时队列残留清理=`+0x20ef554`。293 日志快照只有 wchan，未提供将线程 225 绑定到这些 LR 或 qid 的实际记录；这不代表后续 295 的运行结果。[site 解析与 293 快照范围](../../work/parallel-research-20261107/queue-contract/inspection-293.json)
- BB qid 由 `osal_subsystem_id` 的 owner 经动态 ID 操作 `0x2a` 创建，写 `appFw+0x5c38594`；释放操作为 `0x4a`。该 storage 是模块数据 VMA 偏移，不是固定物理地址。`0x910040` 若为 recv 的 w0 实参，它是 qid，不是消息 payload/type。[创建/删除配对证据](../../work/parallel-research-20261107/queue-contract/README.md)

### Inferences

- 最低只读观测字段建议为：`run/attempt id`、输入/运行时 patch 身份、单调 entry/exit seq、TID、caller DSO+LR offset、实际 provider DSO、32 位 qid、原始 32 位 timeout、out-slot **地址**、原始 rc 与即时 errno。先不解引用消息正文，不改 timeout、不合成成功。[实际 ABI](../../work/parallel-research-20261107/queue-contract/inspection-293.json) · [ioctl 适用边界](https://www.kernel.org/doc/html/latest/driver-api/ioctl.html)
- 若精确命中 finalize LR，再关联 qid 创建/释放和原厂 worker type `0x41` 的启动、终止请求来源、ack 发送和退出状态；若命中普通 worker LR，长期无新消息可能是正常空闲，不能仅凭时长判故障。[BB 退出协议静态证据](../../work/parallel-research-20261107/queue-contract/README.md)
- 当前可复核的推进应保持原始收发逻辑，观察“未返回的哪一个调用”以及对应生命周期；公开代码没有提供可替代该取证步骤的短超时捷径。[公开包检索范围](sony_osal/public-source-verification.json) · [本机控制流](../../work/parallel-research-20261107/queue-contract/README.md)

### Gaps

- 本轮未操作正在进行的 VM295，也未为其新增通过/失败结论。没有观察到实际 LR、qid owner 与退出回执前，无法宣称 UI 卡点就是 finalizer，或宣称某项 hook/超时修改修复了菜单。
- 本轮没有下载闭源固件、没有新增第三方源码副本。支持脚本仅对官方公开 URL 执行 HEAD，并读取现有公开归档；完整证据、访问日期和可重跑脚本见同名 `sony_osal/` 目录。[核验工具](sony_osal/verify_public_sources.py) · [结构化记录](sony_osal/public-source-verification.json)
