# FX6 开机证据独立只读审计

**结论：现有材料不足以称“固定 FX3 平台上的 FX6 上层已开机”，更没有可用 FX6 菜单验收。** 历史最远可核验的是原 FX6 AP 已执行初始化相关代码、同次固定 FX3 MPR 调用返回 `3`，另一个观察轮捕到 CAPID `initialized=0 / owner=0` 及同请求返回 `-1021`；最近 veneer 候选只取得 IM dispatch/dlsym 停点，没有取得 AP 身份、bridge/原 Init 执行证明。[M L190–260、300–344；O L270–296；E L58–59、61–125；C L149–152]

与现有两份主审查及 README 当前条目没有发现推翻其总判断的新增冲突；本报告复核已有版本断裂，并补充跨轮证据、故障停点、清理与健康状态的适用边界。不能把多轮的局部证据拼成一次成功启动。[A L235–258；B L4、25–43；D L19；下文“结论冲突与适用范围”]

## 范围与方法

- 任务 `task_caff27534971` / dispatch `ctx_58ad41090a5d`；唯一输出是本目录，本报告不修改 README、台账或任何共享候选。
- 先读两级项目入口；Mac 本目录 `git rev-parse --show-toplevel` 返回“not a git repository”，因此不存在本目录可报告的分支或提交状态。项目总入口也将 Mac 登记为无 GitHub 仓库。[V L33–55]
- 读取指定 A/B/C/D 及其明确指向的必要小型文本/JSON、相应运行目录内观察/输入回执。未做全盘扫描、未重算任何固件/候选大文件哈希；沿用审查中的哈希记录，日期与适用版本在下文单列。未导入或执行候选/测试/研究脚本，未启动 QEMU、guest、浏览器、服务或物理设备，也未实现、重新封存或改写被拒候选。
- 外盘读前及输出写前经 `diskutil info -plist` 核对 MountPoint `/Volumes/KAFU2T`、VolumeUUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。本次仅对本报告和审计 JSON 作格式/引用核验。
- A 的审查时刻是 `2026-11-05T04:19:01.749303+00:00`，B 是 `04:20:18.331546+00:00`，均为 **2026-11-04 PT**，不构成日期冲突；本次不把它们的 `actual` 哈希冒充再次重算的实时值。[A L2；B L2]
- 这是本地历史证据审计，不提出外部平台现状结论；未追加联网调研，也未追读无关研究材料。源文件执行政策与提供方拒绝保持有效。[A L5、253–258；B L3、43]

## 最远已证实阶段与最近停点

| 证据层/版本 | 已证实 | 不能据此主张 | 精确依据 |
|---|---|---|---|
| 两入口历史包 `fx6entry-a39715a8` | 32.38 秒内 loader verify/list/true 三 RC0、自然 bootin、IM 映射、FX3 AP 发送标记；收尾完成 | 包内没有 FX6 AP/AV/CP；IM 可执行段与 FX3 相同，不能称 FX6 系统已执行 | Q L3–9 |
| 三载荷原 FX6 AP `fx6ap-bb7588e5`，CPIO `bb618bd2…` | FX6 appFw 调用栈、原服务请求；42.734 秒停首个真实断言 | 不证明完整 AP 初始化/IPC 回复/菜单；请求相邻断言不单独证明具体失败因果 | R L3、7–8、18–26；S L2–3、21–29 |
| 同一三载荷系列 `mpr-ro-b22ccc48` | AP 当前 ELF/PHDR/代码身份、调用点和 656B 参数、同次调用返回 `3`，返回后 GOT 指向固定 FX3 MPR 身份；29.235 秒 | `mpr_entry_observed=false`；CAPID 断点未武装。只证明调用/返回与绑定，未直接捕到 MPR 内部分支，更非 Init 成功 | M L190–260、300–344；N L3–7、131–137 |
| 同一三载荷系列 `ap-ro-8548d224` | 同 TLS/请求/调用帧的 CAPID `initialized=0 / owner=0`，返回 `-1021`；53.624 秒 | 这是初始化未就绪的负证据；`assert_branch_will_fire=true` 是停点处对后继分支的判定，不能仅该字段声称断言已执行；其 receipt 另有真实断言 | O L270–296；P L3–7、131–137、191–197 |
| veneer 候选 `guest-veneer-33d090b1`，CPIO `8abed374…` | loader 三 RC0、自然 bootin、IM 身份、dispatch 与 dlsym 两个只读停顿；零键 | 未取得 AP/MPR 身份；`gate_installed=false`，无 bridge/原 Init 通过。它的最远证据比旧三载荷观察更早，不能继承旧包的 AP/Init 结果 | C L50–97、124–152；E L58–59、61–125；F L46–54 |
| 当前源码（A/B 审查时点） | 三个小型源码与旧封存不同；runner、probe、旧测试回执三种 probe 校验值不一致 | 未建立当前源码的成功宿主回归或真实运行，不存在“当前候选已复测通过”的证据 | A L62–83、218–238；B L25–41 |

**“最远历史阶段”与“最近一轮阶段”必须分别汇报。** 原 FX6 AP 在三载荷包上执行过，不能简化成“FX6 完全未执行”；最近 veneer 包没有 AP 身份证据，也不能扩大成“已进入 bridge”或断定其 ELF 从未装入。共同没有通过的是初始化成功、PowerOn 闭环与可用 FX6 菜单。[M L150–187、190–260、339–344；E L58–59、108–125；A L241–250]

### 最近一次运行停点的准确含义

`receipt.stop=unknown_loader_return`，总 host 时间 `38.5776543749962` 秒；`host_error=null` 只表示该回执没有宿主异常字段，并非启动成功。[C L3–5]

观察记录先在 vCPU `03` 得到 `appFw.so / Application_System_Init` dispatch，再在 vCPU `02` 得到 dlsym 返回 `x0=0x7f0377d044`；两个记录的 TLS 字面相同，但第二条状态为 `not_same_im_record_tls`，没有记录 dlsym 时的 x22，`mapping.ap=null / mpr=null`、`gate_installed=false`。这证明历史观察器拒绝归属并保留停点；**仅凭 stop 名称不能判定 guest loader 实际返回失败、成功，也不能用非零 x0 充当 bridge 身份或 AP 成功执行证明**。vCPU 迁移是现有静态审查/夹具讨论的背景，本次不把它判作已经排他证明的根因。[E L58–59、63–125；B L31–41；L L106–109]

`health.failure=null` 与 `diagnostic_captured=false / lifecycle_healthy=false` 同时存在；观察在早期门被截停，没有观察到 fault 不能解释成系统健康通过。四条 FX3 专用观察器拒绝仅表明旧地址/代码合同未绑定，不证明已适配 FX6。[C L99–122、149–152]

## 结论冲突与适用范围

### 1. 已有阻断复核：当前版本不能继承旧 PASS

A 记录封存 33 项中 30 项匹配，变化的是 `guest_probe.py`、`run_guest_once.py`、`test_guest_host.py`；这是一组完整性计数，不是开机完成度，也不代表其余 30 项获得运行验收。[A L15–18、62–83]

三种 probe 身份如下，前两项是已有审查时记录值，本次未重新扫描计算：[B L25–28]

| 身份 | SHA256 | 适用证据 |
|---|---|---|
| 当前 runner 常量 | `6f40e30e62fde9eddd74d547da8d6f3ab0d13be59413204632a232bc1d449aec` | K L39 |
| A/B 记录的当前 probe | `f10defaad641b3565d49c78225e84c9bcc4d60dabe4e7fdc70a82883de7c0842` | A L62–65；B L26 |
| 旧宿主测试/历史运行 probe | `bb5c5e18b98cced5f86d4a57ff5487138d9cbc62ef7d98e4dfb4a1164db27921` | H L2–11；F L54；G L2–7 |

当前 K L97–99 同时要求旧测试回执的 probe SHA 与实际 probe SHA 等于 runner 常量；已有三值使该条件静态为假。这只能得出“该身份门不能通过”的审计结论，本次没有运行 runner，也不保证程序在此之前的其他依赖一定能通过。[K L83–110；B L25–28]

历史回执仍可审核：A 明记运行目录中的 observer 副本与原封存匹配，G 保留 runner/probe/host-tests 的绑定，I 的 `PREFLIGHT_NO_QEMU` 也绑定旧 runner/probe。不能以当前源码变化抹掉旧运行，也不能把旧预检移用于当前源码。[A L218–228；G L2–7；I L2–7]

### 2. 宿主 PASS 与合成寄存器不能补成真实迁移通过

H 的 `PASS_NO_QEMU` 明确只覆盖旧 probe 的宿主范围；L 的正例声明 `dlsym_x22=NOT_CAPTURED`、只有合成夹具假设 x22 等于 dispatch record。源码中的 assert 与输出 `PASS_NO_QEMU` 语句不证明该测试已经执行，更不证明真实 guest 跨 vCPU 身份门接受成功。[H L2–11；L L91–114；B L31–41]

J 的 `STATIC_VERIFIED_NOT_RUN`、I 的 `PREFLIGHT_NO_QEMU` 是静态/预检回执自己的证据级别；C 是同一 CPIO 的后续实际运行。因此 `NOT_RUN` 不应被读成“截至现在从未运行”；同样 C 的存在也不将静态检查升级为 bridge 执行通过。[J L2–4；I L2–6；C L3–5、37–45；E L124]

### 3. 补充审计：观察完成不等于健康运行，回收不等于恢复通过

旧 MPR/CAPID 轮次的 `stop` 分别为 `mpr_same_call_return_captured`、`same_call_return_captured`，但其 receipt 都另存 `health.failure.kind=real_fault_or_unproven_guard` 和 `assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075`。故“已取得目标返回证据”可以成立，“该轮无真实故障/已健康启动”不能成立；不能只展示 stop 字段。[N L3、191–197；P L3、191–197]

最新 C 有 `qemu_exit=0 / qemu_reaped=true`、断点全移除、双锁 free；同时 `API16_restored=false`、明确为保留故障停点跳过恢复、`lifecycle_healthy=false`。应表述为“按故障停点政策退出回收完成，正常 API16 恢复及生命周期验收未过”。旧 R 的 API16 成功恢复不能移作新包结果；也不能把主动跳过恢复误写成已尝试但超时。[C L6–35、149–152；R L24–26]

### 4. README 的旧状态属于历史，不形成当前完成证明

当前 D L19 明确新状态与“下方较早条目为历史阶段记录”。因此 L49 的“更早 MPR 返回待观察”已由 L43 补足，L55 的 owner/返回未知已由 L49 补足，L37 的“继续构建”受 L19 当前执行拒绝限制；若提取摘要时丢失顶层说明，会制造假冲突。本次不改这些历史条目。[D L19、37、43、49、55]

### 5. 已有勘误需要随历史 callback 结论一并携带

U L45–46 把 FX6 callback 的读取边界写成 `0x788/0x780`；T L38–40 已明确勘误：两值是 producer 分配尺寸，AP 最高无条件读取末端为 `+0x780/+0x778`。这是历史措辞冲突，后者已有纠正；无论哪一口径，均远超 FX3 原 32B payload，原指针直通不兼容这一结论不变。这里只复核勘误一致性，没有再次反汇编或重做 ABI 研究。[U L45–46；T L38–40；A L245–246]

## 已过/未过验收门与合理先后

“历史局部已证”不自动移用于改版候选；以下顺序是验收依赖，不是执行许可或补丁步骤。

| 顺序/门 | 当前状态 | 通过要求与依据 |
|---|---|---|
| 0 提供方执行阻塞 | **未解除** | A `execution_blocker.status=unresolved`，B 亦确认；本任务只读，不能以换模型、重封存、放松守卫恢复实施。[A L253–258；B L43] |
| 1 固定平台与完整版本身份 | 历史平台静态已证；当前源码一致性**未过** | 旧 S 核固定 QEMU/内核/完整 DTB/Backup，F 保留最近命令的 CPU/RAM/内核/DTB/模型声明；后续证据须绑定同一源码、测试、载荷与冻结平台。不能只凭路径声称当前二进制重新验证完毕。[S L29–40；F L3–44；A L62–83] |
| 2 loader/自然入口/IM 身份 | 历史及最近轮**局部已证** | 三 RC0、自然 bootin、IM ELF/代码；不证明 FX6 AP/bridge 成功。[C L50–85、124–145；E L72–99] |
| 3 当前候选 AP 与 bridge 的实际绑定 | **未过** | 最近 ap/mpr 为 null，gate 未安装；旧原 AP 身份不能代替新 appFw-bridge 身份。[E L58–59、124；M L150–187；C L40–42] |
| 4 参数、callback ABI/所有权及未支持边界 | 宿主/静态子集；运行态**未过** | 需要在原 Init 调用前就满足支持表、登记/生命周期及模式条件；不能放在 Init 返回后再验，因为已知可在 Init 内建异步队列。[A L245–246；U L43–50；T L24–28] |
| 5 同次原 Init 调用/返回与 CAPID ready | **未过** | 旧 MPR 返回 3；新 bridge/原 Init 未观测；旧 CAPID initialized/owner 均0。须是当前绑定下的原结果，不能将非零返回传播等同成功。[M L339–344；O L270–296；A L241–242；T L26] |
| 6 PowerOn 真实事件/等待者闭环 | **未过** | 现有仅宿主字节转换合同，未证明真实 waiter/key/echo/所有权与完成通知；它可能与 Init 内部过程交叠。[T L28；U L43、50] |
| 7 可用 FX6 菜单/按键到画面/持续健康 | **无通过证据** | 需要真实 FX6 菜单、输入消费和对应画面更新，并有无真实故障的持续窗口；FX3 新菜单 32 键验收属于另一条线。[A L249–250；D L19–21] |
| 8 正常退出与恢复 | 最近轮仅故障退出回收**局部通过** | API16 正常恢复、生命周期健康需另有同版同轮证据；不能由 exit0 或空锁推导。[C L6–35、149–152] |

菜单目标与电影/真实 RAW/ISP、硬件拍摄及实机安装分别验收。当前宿主原型没有录制放行，U 也明确把 CAPID/DMA/CP/AV/电影像素留给后续，不能把没有电影验证误算菜单已通过，亦不应反过来把完整电影实现作为第一项菜单验收的替代工作。[T L3、28、49；U L58；D L71]

**现在的下一验证门**：提供方执行阻塞仍未解除；在只读范围内先完成“目标源码版本—测试回执—历史运行载荷”的一致归属，明确哪些证明属于旧版、哪些根本尚无证据。本报告已完成这项证据分类。任何后续运行都必须先有有效的允许范围和对应版本证据，再按门 2→3→4→5/6→7 验收；门 4 的前置合同须在原 Init 前满足。这里不提供被拒工作的补丁、重试、装载或绕过操作。[A L235–258；B L25–43；U L50]

## 交付与限制

- `REPORT.md`：中文审计报告及来源索引；`audit.json`：可机器复核的结论、门状态与精确字段/行号。
- 无新增开机成功证据，无新增被实验证实的代码根因；新增的是跨材料的适用范围审计，不能将其当作实现进展。
- 不复用历史记忆作为本轮证据；不更改共享入口；不重封存候选；不宣称本地宿主检查等同 guest、菜单或实机验收。[A L5、235–258；B L3–4；D L19]

## 来源索引

下文路径为实际读取的文件，正文 `A L6–13` 等定位同时给出行号和相应字段；哈希除特别说明均为来源原记录，并非本次重算。报告的静态门状态来自这些材料的范围内判断。

- **A**：[fx6-primary-readiness-audit-20261104.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-primary-readiness-audit-20261104.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-primary-readiness-audit-20261104.json`
- **B**：[fx6-primary-static-review-20261104.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-primary-static-review-20261104.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/fx6-primary-static-review-20261104.json`
- **C**：[receipt.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/receipt.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/receipt.json`
- **D**：[README.md](/Volumes/KAFU2T/AI/Projects/Mac/README.md:1) — `/Volumes/KAFU2T/AI/Projects/Mac/README.md`
- **E**：[guest-veneer-observation.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/guest-veneer-observation.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/guest-veneer-observation.json`
- **F**：[command.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/command.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/command.json`
- **G**：[source-sha256.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/source-sha256.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/runs/guest-veneer-33d090b1/source-sha256.json`
- **H**：[host-tests.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/host-tests.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/host-tests.json`
- **I**：[preflight.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/preflight.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/preflight.json`
- **J**：[static-receipt.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/static-receipt.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/static-receipt.json`
- **K**：[run_guest_once.py](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/run_guest_once.py:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/run_guest_once.py`
- **L**：[test_im_inherited.py](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/test_im_inherited.py:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/guest-veneer-candidate/test_im_inherited.py`
- **M**：[mpr-observation.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/mpr-observation.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/mpr-observation.json`
- **N**：[receipt.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/receipt.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/receipt.json`
- **O**：[readonly-observation.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/runs/ap-ro-8548d224/readonly-observation.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/runs/ap-ro-8548d224/readonly-observation.json`
- **P**：[receipt.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/runs/ap-ro-8548d224/receipt.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/runs/ap-ro-8548d224/receipt.json`
- **Q**：[README.md](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/coordinator-entry-runtime-review/README.md:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/coordinator-entry-runtime-review/README.md`
- **R**：[OBSERVATION.md](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/hybrid-ap-candidate/runs/fx6ap-bb7588e5/OBSERVATION.md:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/hybrid-ap-candidate/runs/fx6ap-bb7588e5/OBSERVATION.md`
- **S**：[receipt.json](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/coordinator-ap-candidate-review/receipt.json:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/coordinator-ap-candidate-review/receipt.json`
- **T**：[README.md](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/writer-veneer-prototype/README.md:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/writer-veneer-prototype/README.md`
- **U**：[README.md](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/init-field-adapter/README.md:1) — `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/first-ap-readonly-observer/mpr-init-candidate/init-field-adapter/README.md`
- **V**：[README.md](/Volumes/KAFU2T/AI/Projects/README.md:1) — `/Volumes/KAFU2T/AI/Projects/README.md`
