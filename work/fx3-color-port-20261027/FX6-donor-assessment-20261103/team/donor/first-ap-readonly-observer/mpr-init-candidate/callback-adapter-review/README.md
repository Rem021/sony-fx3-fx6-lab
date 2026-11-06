# FX3 MPR → FX6 AP 回调边界：拒绝式离线适配核查

**结果**：固定 FX3 MPR 两个电影事件的真实 `SetIssueEvent` 堆载荷均为 `0x20`（32B）；`SendIssueEvent` 里的 `mov w1,#0x20` 是另一次 OSAL 诊断复制长度，不能单独用它证明分配尺寸。本次从原 `Notify* → SetIssueEvent → SetEventParam/malloc+memcpy → queue → SendIssueEvent/BLR → free` 绑定了分配、调用和所有权。原 FX6 AP 的两个对应回调无条件读取 32B 以外字段，故直接登记 FX6 回调指针存在对象越界读取风险；本阶段**拒绝**生成可调用的电影事件桥接。已有 PowerOn 12B 和 RecPbTime 60B 受限子集经固定 SHA 复用为 host 字节模块；其软件集成、自然事件与 FX6 开机仍未验收。

这是在 [MPR 唯一实测](../RUN-OBSERVATION.md) 之后的 host-only 阶段，不启动 VM、无设备、无 ELF 原函数执行，也不修改固定 FX3 平台或旧回执。详细 VA→PT_LOAD→fileoff、原 32 位机器字、反汇编、GOT 重定位与来源 SHA 由 [audit.py](audit.py) 生成 [evidence.json](evidence.json)，91 条指令逐条来自固定原件。

## 每条边的原字与尺寸

| 边 | FX3 原码证据 | FX6 原码证据 | 界限 |
|---|---|---|---|
| MovieWriteFinished 生产 | `cb488/490` 从 `execIssueEvent+4` 写 payload+4；`cb494/cb49c` 从 `exec+2c/+30` 写 +8/+c；`cb4a4..cb4b0` 从 `exec+38` 复制两个 qword 至 +10/+18；`cb4b4 mov x2,#0x20`、`cb4b8 BL SetIssueEvent`，事件字 `0x1009` | `1450f8 mov x24,#0x788`；`145114 mov x2,x24`、`145120 memset` 栈记录，`14512c` 长度 `0x75c` 将 `exec+5c` 复制至 payload+14；`145154` 从 `exec+7b8` 取标志存 +770；`145168/16c` 将 `exec+38` 两个 qword 存 +778/+780；`145174/178` 以 `0x788` 交给 SetIssueEvent | 核心三 u32、两个 qword 可定位；FX6 `exec+58` 的 payload+10、`exec+5c` 扩展数据和 `exec+7b8` 标志在 FX3 32B 记录无等价来源 |
| AutoDivided 生产 | `cb920` 清零 payload 前16B、`cb91c/cb928/cb930` 写 +8/+4 和从 `exec+38` 复制两个 qword 到 +10/+18；`cb93c mov x2,#0x20`、`cb944 BL SetIssueEvent`，事件字 `0x1030` | `1455c0 mov x24,#0x780`；`1455dc/5e8` 清零，`1455f8` 长度 `0x75c` 从 `exec+5c` 复制至 payload+10；`14561c` 从 `exec+7b8` 取标志存 +76c；`145628/62c` 从 `exec+38` 写两个 qword 至 +770/+778；`145638/63c` 以 `0x780` 和事件 `0x1037` 交给 SetIssueEvent | +c 在 FX3 此 producer 为零，但 FX6 从 `exec+58` 取，不能仅因同偏移填零就宣称行为等价 |
| 真正堆分配 | `b4168/b416c` 将 SetIssueEvent 的长度转交 x3；`b3f70/b3f7c` malloc(x3)，`b3f84..b3f8c` memcpy 同长，`b3fc0/b3fc4` 入队指针 | `128994/998` 同样转交 x3；`12879c/7a8` malloc(x3)，`1287b0..7b8` memcpy | FX3 32B 与 FX6 原生 1928B/1920B 是真实复制对象尺寸。`b4664/b46e8` 的 `w1=0x20` 只给 `b3a78` OSAL 日志，随后重新载入原 p 并 `BLR` |
| 分派/释放 | `b4654` GOT `0x2f9980` → `gp_evtMovieWriteFinishedFunc`；`b46d8` GOT `0x2f9750` → `gp_evtMovieRecAutoDividedFunc`；`b4670/74`、`b46f4/f8` 以 `x0=原 p` BLR；公共尾 `b4488/494` 对同 p `free` | FX6 原生 GOT 分别 `0x108e460`、`0x108bfb8`；其生产尺寸见上 | FX3 dispatcher 持有并释放原 p；未来桥接只能借用其生命周期，临时转换记录至少活到 FX6 回调返回，不能替原 dispatcher free 原 p。两个 UserData qword 只复制，深层所有权未证明 |

上述 GOT `R_AARCH64_GLOB_DAT` 在 [evidence.json](evidence.json) 中逐项验证；不是靠临近分支或 strings 把回调名字猜上去。`SetEventParam` 的队列 `{kind,event,p}`、`GetEventParam/GetIssueEvent` 取出同 p、`IntegEventMain` 派发及公共释放的更多原字链已由固定 SHA 的 [PowerOn 合同](../../../capid-init-portability/poweron-contract/README.md) 证明；本轮复核关键端点，不以那份合成状态模型代替实测自然事件。

## FX6 AP 的直接读取边界

| 目标回调 | 原字与最高直接读取 | FX3 32B 直传的后果 |
|---|---|---|
| FX6 MovieWriteFinished `0x213ca24` | `213caa0 ldrb [x19,+0x770]`、`213caec ldr x0,[x19,+0x778]` 均无条件；最高读取末端 `+0x780`。若 +770 非零，`213cb20..cb30` 从 +14 复制 `0x75c`，源末端 +770 | 无条件读已越过 32B 对象末端 `0x760`（1888）字节；条件 memcpy 也越过 `0x750`（1872）字节。AP 会创建自己的消息并复制标量/指针，不是把原 p 长期保留的证据 |
| FX6 AutoDivided `0x212d9fc` | `212da18 ldrb [x0,+0x76c]`、`212da54 ldr x2,[x20,+0x770]` 均无条件；最高末端 `+0x778`。若 +76c 非零，`212da84..da94` 从 +10 复制 `0x75c`，源末端 +76c | 无条件读越过 32B 末端 `0x758`（1880）字节；条件 memcpy 越过 `0x74c`（1868）字节。目标 event 由原生 producer 改为 `0x1037`，不能照搬 FX3 `0x1030` |

这些是**直接原指令的对象边界**；实际 malloc 可用块大小、是否崩溃、异步 AP 新消息的最终释放与录制期自然事件尚未实测。`0x20` 源若被内存分配器放进更大 size class，仍不能因此允许读取未分配给该对象的数据。

## 可复用的代码、拒绝条件与仍未闭合的开机边

[adapter.py](adapter.py) 只在核验既有源 SHA 后调用原 [PowerOn 12B 模块](../../../capid-init-portability/poweron-contract/offline.py) 和 [RecPbTime 60B 录像计时子集](../../../capid-init-portability/init-callback-entry-contract/record_subset.py)。`inspect_movie_core` 从精确 32B FX3 Notify fixture 析出已证事件键、三个 u32 和两个 UserData qword，并给出目标偏移；`translate_host_subsets` 对两个电影事件一律抛 `ContractRejected`，因为扩展标志、路径块和其所有权缺乏自然来源。这个接口**不核运行态来源、有效等待者或 callback 指针身份**，不能直接在 guest 调用；它从不调用回调、分配 guest 消息、返回“成功”或生成可装载代码。长度、可变缓冲、错误事件、AutoDivided 非零 +c、PowerOn 非零结果和未知回调均拒绝。五项正反例见 [test_adapter.py](test_adapter.py)，只是符号化 host fixtures。

既有 Gemini 文字中的“`780/1440` 安全互换”不能放行：固定 SHA 的 [u16 合同](../../../capid-init-portability/init-u16-contract/README.md) 原字指出 FX6 Xavcs writer 强写 780，Mxf writer 保留 1440，固定 FX3 Xavcs 保留传入值；实际 writer/模式在本轮 Init 观察中未知。其“PowerOn/RecPbTime 100% 一致”也不成立：PowerOn 原事件键 `0x1026→0x102d`，RecPbTime `0x1022→0x1029`；已有 [回调入口合同](../../../capid-init-portability/init-callback-entry-contract/README.md) 仅闭合录像计时且尾字段为零的 60B 子集，播放/音频语义仍拒绝。三个先前结论的 SHA 均在 evidence 固定，不重做 57 项表。

开机最小未闭合边按先后是：

1. FX6 `0x290` Init 参数到固定 FX3 `0x1f8` 的 count、slot、回调表与 u16 条件映射；本次 `w0=3` 只证明第一处偏移错读与返回，未执行后续初始化。必须保留真实错误分支。
2. Init 创建异步事件线程且无“Init 返回后才可派发”门；必须在接入前确认早期事件集合并只注册已有安全合同的回调。PowerOn 的 `0x1026→0x102d` 只可在已注册有效等待者时桥接；RecPbTime 仅录像计时子集，不能吃掉播放状态。
3. 固定 FX3 MPR 的电影录制回调必须用事件特定转换并验证 `exec+58/+5c/+7b8` 来源及两 qword 语义，或在启用录制前显式拒绝；不能以“菜单阶段也许不触发”直接注册不安全原回调。是否在开机窗口出现这两事件仍未知。
4. CAPID model/owner `0/0` 与 AP `-1021` 是更早的独立实测边；MPR 参数修正不能自动修复该服务。固定 FX3 平台、17 helper、Backup 与硬件接口保持不动，须另按实际服务边分析。

这些局部接口工作是 FX6 上层搬移的必要组成，不等于整个用户目标不可行；也不把一个 Init adapter 说成完整移植。下一步最小 host 实现是对原 FX3 MPR `Init` 入口**所有直接读取的字段**建立拒绝式映射，先验证 count=2 与四槽状态/注册时序，允许已证 PowerOn 与 RecPb 子集，其他事件不注册或显式报不支持；只有完整静态合同与软件保护均通过才考虑由 runtime owner 申请新的只读 VM 窗口。本任务没有申请或使用新的 VM 窗口。

## 复算

在本目录执行 `python3 -B audit.py`、`python3 -B -m unittest -v test_adapter.py`；前者固定输入 SHA、三份旧合同 SHA、旧运行 SHA、91 条原字/VA→fileoff/objdump 与两种 GOT 重定位，后者五项 host 字节/拒绝测试。`audit.py` 只更新本目录 `evidence.json`，不触碰原 ELF 或运行历史。
