# FX6 原厂启动：294/295 完成证据、规范交叉验证与下一轮观察方案

## 1. 294/295 实际改了什么，GOT与Backup是否已修好？

### Takeaway

294同时改变GOT符号查找优先级并加入一组Backup桩，随后在桩的`Backup_read`清零路径崩溃。295只取消这一路径的写内存、恒返回0，有限日志未见崩溃且显示仍全零；这支持“避免294错误清零”，不能提升为Backup语义修复或原厂UI成功。[完成证据](latest_candidates/evidence.json)

### Cited Findings

- 只读复核三份完成回执：293=`cp-bind-4cdf812e`、294=`cp-bind-a8fdd5c4`、295=`cp-bind-f56cfd5f`；三者整包CPIO、loader、manifest与serial指纹均匹配。actual appFw始终是50,520,424 B、SHA `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`；完整newc扫描包含首TRAILER之后的追加成员，索引语义不替代内核hardlink抽取。本轮写前确认目标卷UUID正确，没有控制VM、端口或相机。[证据与工具](latest_candidates/evidence.json) · [复跑脚本](latest_candidates/review_294_295.py)
- 293→294：init不变，launcher从`0a4eb7a70b38…`变为`8bfd033670f1…`，shim从`73c603ab9685…`变为`ce96f00c605e…`；477个库entry中只有shim变。294→295：init及launcher不变，只有shim改为`c58b6509e451…`。本机`/tmp`对应ELF与294/295容器成员SHA一致，源码快照另记SHA；没有把源码路径或文件名当作可重复构建证明。[逐字节比较](latest_candidates/evidence.json)
- 新launcher先`dlopen(shim,RTLD_NOW|RTLD_GLOBAL)`，修GOT时优先`dlsym(shim_handle,name)`，失败才查`RTLD_DEFAULT`。两轮串口1225仍只汇总`entries=832 fixed=799 missing=33`。该查找路径可命中shim或其依赖中的实现，并非每个名字都保证属于shim；源码没有按每个实际Backup slot记录provider所有者和返回后读回。[launcher差异](latest_candidates/source-snapshots/appfw-launch294.c) · [运行日志摘要](latest_candidates/evidence.json)
- 实际launcher的`got_tab`包含`Backup_read=appFw+0x2ef22f8`、`Backup_nread=+0x2ef2220`、`osal_rcv_msg_tmo=+0x2ef2868`，与原件三个`R_AARCH64_JUMP_SLOT(1026)`重定位一致。细节日志却仍只针对旧`+0x47cd430/+0x47cc620`比较，因此这些实际slot没有before/after细节日志；汇总799次赋值不能证明每个槽最终provider正确或对应函数被调用。[实际ELF表项](latest_candidates/evidence.json) · [launcher细节guard](latest_candidates/source-snapshots/appfw-launch294.c)
- 294新增`Backup_read(id,buf,size)`按调用者`w2`作为长度清零。原厂`libbackup.so+0x1e14`入口保存`w0/x1`后覆盖`w2=-1`，没有把调用者`w2`用作长度；这证明294的长度来源缺少契约支持，**并不能单凭callee覆盖w2证明严格C原型恰有两个参数**。原型还需调用点准备、符号及原厂入口共同核实。[原件与桩ABI入口](latest_candidates/evidence.json) · [294源码](latest_candidates/source-snapshots/libgrm-fbinit25-294.c)
- 294串口1237为`APPFW_SEGV`，X2=`0x77ffd4e0`，PC=`libc+0x7a480`，LR=`shim+0x1881c`；实际shim的`Backup_read`范围是`+0x187d8..+0x18857`。它构成至少一次执行到该桩清零路径的具体证据，支持错误长度导致越界清零的机制，不能表述为“294所有Backup桩均未命中”。295把同一函数改为不写输出、返回0，原件各Backup ID需要的类型、长度与返回值仍未逐项验证。[现场寄存器与符号](latest_candidates/evidence.json) · [295单函数差异](latest_candidates/source-snapshots/libgrm-fbinit25-295.c)
- 295的1,571行raw serial没有assert/SEGV/Oops匹配；`gpe0.bin/gpe1.bin`各2,211,840 B，非零字节均0。1244仍是`prims=0 nz_pixels=0`。只记录217/220/221/222的wchan：主线程nanosleep、其余futex；没有225采样，`osal_rcv_msg_tmo`计数0，也没有真实receive LR/qid。不能沿用293的“225等消息”作为295状态。[运行与线程摘要](latest_candidates/evidence.json)
- 295保留与293相同的5处运行时NOP：`+0x12d824c/+0x12d8250/+0x12d8254/+0x12d825c/+0xc09e50`，串口1229–1233各自报告`mprotect=0`；没有写后guest指令字节读回。Backup桩没有按函数/id记录entry/exit、实际范围、返回值；内存全零与return0只体现替代策略，不证明相机模型值合法。[patch日志](latest_candidates/evidence.json) · [295源码](latest_candidates/source-snapshots/libgrm-fbinit25-295.c)

### Inferences

- 294→295是较清晰的容器单函数差异，观察结果支持取消错误清零路径的效果；“GOT修好了所有Backup”或“原厂Backup系统已恢复”超出现有证据。下一轮应验证真实provider、id及返回语义，而不是继续无类型全零替代。[差异及缺口](latest_candidates/evidence.json)
- 295线程数与293不同，可能更早退出、未创建或处于不同生命周期；已有wchan不含创建入口和退出原因，不能凭数量判断是哪条UI线程。[线程摘要](latest_candidates/evidence.json)

### Gaps

- 仍缺运行时GOT槽读回、每个Backup函数进入/退出和id类型/长度契约、用户线程入口/退出绑定、真实接收caller LR与qid；本轮没有通过连接guest补取这些数据。[审计边界](latest_candidates/evidence.json)

## 2. 四个被误标的位置应如何纠正？

### Takeaway

`+0x20efbb8`是BB finalize终止握手，`+0xc14dfc`是传感器同步回调注册，`+0x1397450`走`model_start`，`+0xc09e50`调用App定时器启动。它们都不是此前计划中的“普通等待 / widget factory / presenter / 20秒等待”。[队列契约](../../reports/2026-11-07-fx6-queue-contract/queue-contract/README.md) · [启动依赖](../../reports/2026-11-07-fx6-queue-contract/queue-screen-dependency/REPORT.md)

### Cited Findings

| 位置 | 已绑定原件语义 | 对下一轮的影响 |
| --- | --- | --- |
| `+0x20efbb8`，LR=`+0x20efbbc` | `infra_wrapper_bb::detail::finalize()`等待worker终止回执；随后不检查rc便free、销毁队列并join五个worker | 不能缩短timeout后假成功继续，否则引入消息所有权与队列生命周期错误。当前294/295没有真实LR/qid把任一等待绑定到该site。[原始契约](../../reports/2026-11-07-fx6-queue-contract/queue-contract/README.md) |
| `+0xc14dfc` | 转到`+0xc15060`，为`adjust::senser`注册两个同步队列回调 | 标记它只能观察传感器回调初始化，不是widget factory。[调用及诊断字符串](../../reports/2026-11-07-fx6-queue-contract/queue-screen-dependency/REPORT.md) |
| `+0x1397450` | model value-id `0x3b19`封装，经`+0x1397494`调用`+0x1395c3c model_start()` | 可观察model_start到达；不能据此说presenter构造或HOME已打开。其后`+0xdf91e8`才走初始boot屏幕过渡。[绑定调用链](../../reports/2026-11-07-fx6-queue-contract/queue-screen-dependency/REPORT.md) |
| `+0xc09e50` | `BL App::start_utimer(+0xc09c14)`；timer服务目的qid=`0x910040`，回调向App队列`0x5503e0`发送word=`0x02010094` | NOP它删除真实事件生产链，不是删除20秒sleep；timer tick也不是开机完成事件。[消息生产链](../../reports/2026-11-07-fx6-queue-contract/queue-screen-dependency/REPORT.md) |

- 上述两份静态报告绑定的appFw SHA均为`a1c58b...`，与本轮完整CPIO成员一致；OSAL库也为`fe248d...`。因此它们的VMA可用于本轮原件静态定位，但不能假定运行字节未被shim修改。[静态输入](../../reports/2026-11-07-fx6-queue-contract/queue-contract/inspection-293.json) · [本轮容器](latest_candidates/evidence.json)
- `+0x12d8254`原调用`+0x20ed13c`，后者包含70个infrastructure初始化包装器，含BB及worker创建。NOP该调用不等于跳过单一外部服务；它会删除潜在事件生产链。九个ScreenArea与无崩溃都没有证明这些初始化已经发生。[初始化闭包](../../reports/2026-11-07-fx6-queue-contract/queue-screen-dependency/dependency-result.json)

### Inferences

- 最小缺口是“当前实际运行在哪一阶段、哪条线程、由哪个caller等待哪个qid”，而非再猜一个地址强行返回。先用只观察记录把运行映射到这些静态分支，再决定后一轮只恢复哪一个生产者或生命周期步骤。[真实等待与生产者区别](../../reports/2026-11-07-fx6-queue-contract/queue-contract/README.md) · [295缺少caller证据](latest_candidates/evidence.json)

### Gaps

- 四个位置目前只有已绑定静态身份，没有294/295的实际命中记录。尤其不能因函数存在或ScreenArea创建推定model_start、boot屏幕、HOME controller已执行。[本轮诊断摘要](latest_candidates/evidence.json)

## 3. 官方规范能证明什么，下一轮怎样只增加观察？

### Takeaway

官方资料支持正确解释参数寄存器、LR、ELF槽位和虚实地址；它们不证明Sony私有状态机或本次shim已经正确。建议冻结295行为，仅增加一个有界、保留原参数/返回与provider的观察包；这是诊断候选，菜单验收仍单列。[观察候选配置](latest_candidates/observer-plan.json)

### Cited Findings

- **2026-11-07联网读取**Arm官方AAPCS64 **2026Q3，发布日期2026-11-03**：x0–x7是参数/结果及caller-saved寄存器；BL/BLR把顺序返回地址写入LR。因此观察器需在嵌套日志调用前保存真实LR和原参数，不能把未建立契约的w2视作长度；LR应映射成原件调用site+4。本项目旧固件是否完整符合当前版规范并未因此得到证明。[AAPCS64 §6.1.1、§6.5](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)
- 同日读取Arm官方AAELF64 **2026Q3，发布日期2026-11-03**：1026是`R_AARCH64_JUMP_SLOT`，目标地址需经解析；未解析前的槽值不能被当最终函数指针比较。本轮实际槽位身份可离线确认，guest最终槽指针及owner仍需运行读回。[AAELF64 §5.7.15](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst)
- 同日读取ELF gABI **4.3 DRAFT**，页面未标明发布日期：ET_DYN/ET_EXEC的`r_offset`是重定位存储位置VMA。应以该映像实际load bias求slot地址，不能把`appFw+0x2ef22f8`当物理地址。[gABI §6](https://gabi.xinuos.com/elf/06-reloc.html)
- 同日读取QEMU官方**滚动master文档**，页面无固定发布日期：默认GDB读虚拟内存，物理模式需显式切换；system gdbstub的“threads”描述vCPU，不等于Linux用户TID。HMP `memsave`与`pmemsave`分别读虚拟和物理地址。这些是接口语义，本机patched QEMU是否逐项实现仍需其版本/实际响应验证；本轮未连接它。[GDB与物理模式](https://www.qemu.org/docs/master/system/gdb.html) · [Monitor](https://www.qemu.org/docs/master/system/monitor.html)

| 验收项 | 本轮离线已完成 | 下一次guest必须取得的证据 |
| --- | --- | --- |
| 输入与偏移 | 完整CPIO、init、shim、launcher指纹；原件BL及动态重定位身份 | run id、真实load bias和映射；启动后再次绑定这些输入 |
| GOT重定向 | 实际launcher中槽offset/name与原件重定位匹配；源码查找优先级已核 | 选定槽before/after及独立读回；provider DSO与entry；函数命中而非799总数 |
| patch效果 | 五个原件BL及shim偏移表、写入代码、自报mprotect成功 | 写前期望字节、写后字节读回及映射范围；没有读回就保留未验证状态 |
| 参数与线程 | 真实OSAL库receive ABI静态证据；AAPCS参数/LR规范 | 创建入口→child TID→退出原因；receive entry/exit的LR、qid、timeout、原rc/errno |
| 相机模型和帧 | 当前桩代码及全零gpe样本 | 真实screen/model到达及run-bound guest帧读回；宿主重画、area对象数与wchan均不替代 |

以上离线完成项与缺口逐项对应本轮证据及规范，不是功能PASS。[证据JSON](latest_candidates/evidence.json) · [官方来源清单及日期](latest_candidates/online-sources.json)

### Inferences

**可执行的下一轮单变量方案：295 + observer-only。** 由现有运行负责人把295清单、init、5处NOP、Backup返回/输出行为、模型环境、kernel、启动顺序及原有运行预算冻结；仅增加一个有界诊断记录包，不同时恢复timer、改变timeout、伪造消息或修改初始化。离线对比应显示除观察代码/数据及其新指纹外没有行为补丁变化；此方案尚未实施。[冻结SHA与方案](latest_candidates/observer-plan.json)

观察包的最少记录与判据：

1. 在首次原件entry前记录`Backup_read/nread/rcv_msg_tmo`实际slot与owner，以及既有五处patch字节读回；未匹配则判provenance失败，不能继续声称“已验证”。保持原修补行为，不新增修补。[槽位及patch缺口](latest_candidates/evidence.json)
2. 记录线程创建函数入口、DSO、creator TID、child TID、开始/退出序号及原因；重点解释295为何只观察到4个task，而不是先命名“225 UI线程”。[295线程差异](latest_candidates/evidence.json)
3. 只记录receive的真实`uint32 qid / void** out-slot / int32 timeout`、入口LR及provider、entry/exit序号、原rc/errno；不缩短timeout、不改rc、不在失败时解引用或伪造消息。[静态receive契约](../../reports/2026-11-07-fx6-queue-contract/queue-contract/README.md)
4. 对Backup桩只增加函数/id/验证过的参数形状和原返回记录，不再引入新清零或统一长度。记录需有界、保留errno并避免递归进入被观察路径；丢样计数必须输出，诊断存在时序扰动不能用于性能结论。[294反例](latest_candidates/evidence.json) · [AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)
5. 分开给出“观察包完整”“具体生命周期到达”“原生菜单可见”三个结果。若仍全零，菜单结论仍为未证明；若没有receive entry，结论是未进入/未捕获该provider，而非“消息阻塞已解除”。[验收表](latest_candidates/observer-plan.json)

### Gaps

- 观察器只读源码/宿主验证不等于guest ABI通过；其provider转发、参数/LR保存、重入控制、读取范围和运行时读回需要下一次有记录的实验验收。本轮只交付研究与复核工具，没有启动候选，也没有以公开规范替代Sony私有生命周期证据。[方案状态](latest_candidates/observer-plan.json)
