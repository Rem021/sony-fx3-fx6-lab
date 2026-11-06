# AP104 完成队列逐代被动观测

当前状态：r4轻量轮在417.117秒、语言弹窗绘制期间复现unfetched，支持原5000ms接收预算已过、软件绘制完成迟到的判断，尚未修复。性能实现已按Lead授权离线集成为AP105，运行暂停给用户TRY1试用，等待Lead明确恢复；未占运行锁、未改试用入口或STATE。首选候选仍为AP101-r4，English落盘与日期保存闭环尚未验收。v7重探针虽满600秒未复现，最终4个用户VA原字检查未通过，保留其收尾限制。

本诊断沿用原AP103-r2的设备/Backup/LDEC/像素模型及原厂Backup种子，在4核MTTCG中仅发送目视后选择的白名单单键。完整逐步截图路径、描述、选键理由见[34步画面记录](ap104-visual-step-log.md)；AP105与TRY2待执行门见[离线运行准备](ap105-offline-preparation.md)和[TRY2方案](try2-ldec-performance-plan.md)。

## 原码结论与观测边界

Lead `audits/gpe-completion-unfetched/README.md` 否定“第一次 rcv 前没有 owner”：原 `osal_dynamic_id` 在 SendDraw 之前写 owner，释放时清零；接收函数不负责设置 owner。两个错误日志不证明重复发送零状态完成。AP104 的目标是区分适配层显式完成、内联用户回调、原 Main/CMF SyncCallback 与 Main 失败路径，按原 owner 领取/释放的观察代次关联真实 QID、tid 和 caller PC。

原件散列与原指令存于 `runtime/ap104-observer-original-proof-v1.json`。内核模块基址来自本轮只读 sysfs；libgpe 基址来自被动绑定日志。原指令在安装和卸载时逐字核对；QEMU Z1 只操作宿主断点表。宿主仅沿用既有 12B 按键控制区和 8B 收尾控制区，未写原代码、队列 owner 或寄存器；没有 stat_msgq、强制 fetch、额外完成或新协议回复。

“观察代次”是宿主对原 owner STR 指令的计数，原队列没有新增 generation 字段。原始 T05 停点携带实际 CPU 身份；Hg/Hc 只绑定该身份，vCont;s:thread 只运行该 CPU 的一条原指令，随后核验 post-PC 和 owner。所有其他 vCPU 在该单步期间保持暂停；正常运行由 vCont;c 开启异步停止通知。调试会改变线程时序，UART 行顺序不等于跨线程 happens-before。

## 新文件与候选

- 被动适配层：`helpers/fx3-gpe-observe-v25-complete104.c/.so`，继承 v24；包装真实 callback、SendDrawComp、dynamic_id，保留调用次数、参数、结果、errno，ASan/UBSan 宿主测试通过。
- 原生观察：`gdb_native104_v2.py`、`gdb_sysregs104_v2.py`、`gate_input104_v5.py`、`run_candidate104_v6.py`。运行中保留 29 点：3 个原 owner 写/清、1 个原首错、4 个原生完成路径点、21 个原 Backup 点；可选的 +3480 owner LDR 点因无关定时器流量移除，+34a4 首错仍读取真实队列字段并暂停。
- 候选：`ap104-r2-observer-ready/candidate.json`。相对 AP104-v1 只修改 init 的观察进程启动顺序并新增带 readiness 的 file observer v2；先初始化控制页、核对活 PID readiness，再绑定 CP API。原 shutdown 脚本与全部设备模型未改。
- `restore_api103_v2.py`：绑定后收尾必须同时见 guest ack seen1/status0 及原 API16；若未绑定且 API16 已原始、无待处理请求，则不恢复执行，直接保持暂停退出。
- 宿主回归与来源散列：`ap104-host-build-review-v2.json`；v6 来源固定于 ap104-host-build-review-v3.json 和本轮 observer 源文件快照；v7 另修故障持久化与cleanup专用T05core回执解析，严格post-PC门未放宽。

## 校准轮（既有 runs 保持只读）

| 运行 | 时长 | 结果与限制 | 收尾 |
|---|---:|---|---|
| ap104v1trace600-a21c2a5e | 2.60s | QEMU target XML 未声明 xi namespace，解析前停；无按键/无原生事件 | API 本来是原始字节，旧 helper 因观察页未初始化记失败；QEMU0/reaped/input SHA 不变 |
| ap104v2trace600-b3192009 | 383.00s | 固定250ms检查使探针迟服务，人工正常停；非600s验收 | ack+API16 1.563s，所有断点卸载/原字未改、QEMU0/reaped/input不变 |
| ap104v3trace600-eb38badf | 4.79s | 裸 s 的 owner 后读不吻合；QEMU 原实现会放行全部 CPU，旧版未留 post-PC，不能倒推哪个 CPU 实际执行 | 故障发生于 CP 绑定后、file observer 启动前；API仍为跳转，seen0；失败如实保留 |
| ap104v4trace600-6450b8c8 | 112.98s | 6470原始事件未再见单步/owner不符；主循环 continue 让后续探针安装饥饿，定向SIGINT收尾；0键 | ack+API16 1.550s，5断点卸载/原字不变，QEMU0/reaped/PID消失/两锁独立释放/input不变 |
| ap104v5trace600-65c08de2 | 368.85s | 30点装齐、待机截图确认、一次MENU开页但读回仍过渡画面；可选LDR点占大多数事件，STOP_FOR_REVIEW正常停；未复现 | ack+API16 1.565s，30断点卸载/原字不变，QEMU0/reaped/PID消失/两锁独立释放/input不变 |
| ap104v6trace600-d85b586d | 23.26s | 冻结媒体观察 M 首项0x9c98近址池分配失败（-3），首帧前停、0键 | ack+API16 1.560s、QEMU0/reaped/PID消失/输入不变、已装探针原字一致、锁独立释放 |
| ap104v6bretrace600-45dfde57 | 285.29s | 原样复跑媒体绑定成功、完整菜单目视；MENU/LEFT两键，单步post-PC严格门失败，无unfetched | ack+API16 1.545s、QEMU0/reaped/PID消失/input不变/锁释放；断点清理 ? 的T05core格式被旧解析误拒，卸载与全原字核验未完成，不能记全通过 |

API16 原始值：`000b00b4fd7bbba9fd030091f35301a9`。v3 残留跳转：`5000005800021fd6bcfc4d0080ffffff`。v3 的提前启动缺口与 AP103 第四轮固定3秒超时是不同路径；前者由 readiness 前移覆盖，后者由有界等待 guest 确认修复。不得把旧轮失败重写成成功。

## 逐步画面（v5）

1. `runs/ap104v5trace600-65c08de2/ap102-phaseA-before-SETUP.png`：已目视，黑底待机 HD Fixed-59,94fps、橙色 NO CARD、AF-C、D-R OFF/测光/NFC 等图标。选 MENU（0x1ab、100ms）理由：从确认的待机打开原菜单，观测完成生命周期，不改设置。
2. `runs/ap104v5trace600-65c08de2/ap102-step-01-settled.png` 与 `ap102-menu-step01-late.png`：均实际查看，仍为部分待机 OSD 过渡帧；原生 screen0→2e0→275 已开，但没有把这些截图称为菜单，不再盲发 LEFT。完整决策与 SHA 在 runtime 外层同名 visual-decisions.json。

该轮实际 GPE 完成 QID 是 0x808261c1，不是旧轮的 c0；分析按本轮真实 SendDrawComp/error 的 QID 自动发现。静态指定旧QID的初版分析输出未找到记录，属于筛选目标错误，不构成“没有完成调用”的证据，后续用 analyze_completion104_v2.py。

## 当前未关闭的门

AP104轻量首错及原码/时间线已保存；性能版本尚无guest验收，须待Lead恢复运行。English自然保存、关闭MENU后待机≥60秒、日期原值确认和原厂新文件代次仍待完成。宿主性能字节等价、观察轮收尾通过与原UI截图均不替代这些门或实机验收。


## v6b 画面与证据缺口

`runs/ap104v6bretrace600-45dfde57/ap102-phaseA-before-SETUP.png` 已目视：HD/AF-C/D-R OFF待机。选择 MENU 后 `ap102-step-01-settled.png` 仍过渡OSD；等待并查看 `ap102-menu-step01-later.png` 才确认原厂菜单：Principal > Principal1 > Tx. quadros grav.，2/59，59.94p橙色瓦片，ISO100、AWB、PP11、XAVC S、Assist及灰色面板。基于此选择 LEFT；`ap102-step-02-settled.png` 与 `ap102-group-step02-later.png` 均目视，仍同一菜单瓦片画面，不宣称已切组，第三键未发。

最后完整 JSONL 成功记录1154是 grm_gpe tid286 对0x808261c1第21观察代次的原 owner清零，post-PC精确+4，owner前8261c1/后0；此前1152是真实SendDrawComp、1153是真实返回。触发严格post-PC门的下一条在旧版仅保存在进程内存，清理又先失败，故其实际PC/点位没有持久化，不能倒推原因。v7已增加在异常返回前保存全部含部分故障记录，并把原始停止/执行命令单独追加到gdb104-execution.jsonl；QEMU原码 gdb_build_stop_packet 的T05core回执只允许用于cleanup，绝不作为观察CPU身份。相关故障与负例宿主回归通过，原PC门和设备/完成语义均未变。


## v7 满600秒，未复现；收尾复核限制保留

`ap104v7trace600-da26dd55` 600秒观测、总602.597s，1181条原生记录，无 unfetched、运行中无单步PC异常。MENU后实际查看 `ap102-menu-step01-reviewed.png` 确认为完整瓦片；选择LEFT；`ap102-group-step02-reviewed.png` 已见橙色Principal1组列，才选择第二个LEFT；`ap102-category-step03-reviewed.png` 已见最左白色选中分类图标、Principal组列和右侧菜单内容。3个按键均目视后逐步选择；早期settled帧另保留为过渡，不替代较晚语义截图。

29点卸载返回通过，25个内核点原字复核通过，4个libgpe用户VA末次检查False。原清理器只记录same_original_runtime_word，未区分不可读与值不同；不能据此断言原代码被改，也不能写成通过。宿主因此退出2，回执error为Original kernel probe words changed。API仍获得guest ack seen1/status0、原API16逐字匹配（1.3098s），QEMU退出0/reaped/PID消失/输入散列不变/两锁独立释放。

后验补看v6b保留的 `osd-frame-000090-format0-RGBA-opaque.png`，其raw SHA `5e9a7a5f6c99cb9ffa9cc33613f96ed8dbd892a55da026a9f1274eeea33be48c` 与最后序97相同，确见橙色Principal1组列，说明该轮第一LEFT最终完成；不改变其宿主异常/清理核验缺失的结论。

## 轻量方案（Lead msg_b27db37f09d2）

v7未复现后按Lead授权转 `ap104-light-v1`：同设备/Backup/LDEC/像素/原收尾脚本，保留v25被动适配层与dynamic_id日志，只新增独立 `fx3-completion104-light-v1.so`（先于原preload链），记录原生SendDrawComp PLT、osal_valloc_msg_wait、osal_snd_msg入口/返回、tid/TPIDR/ns/QID/caller、返回值/errno。ASan/UBSan验证每次仅委托一次原函数、参数/结果/errno保留，CPIO审计只有init加载该观察库并新增该.so，其他既有成员逐字不变。

原SyncCallback在libgpe+a128经PLT调用SendDrawComp，原生caller+a12c可唯一识别该路径；原Main失败路径caller+9c50另标。它不拦截内部直接BL的SyncCallback入口、不声称捕获其完整返回。适配层本来的显式dlsym调用已有v25 seq/op/async/completion_source日志；新库只补原生PLT路线及真实alloc/snd返回。无kernel或user GDB断点，无GDB寄存器读；GDB只沿用软件自有RAM的按键/收尾控制。0内核owner读意味着本轮只能把原厂unfetched printk与用户API时间序对齐，不构造内核owner/代次证据。

轻量运行在首次观察到unfetched或alloc -1018后尽快停；宿主轮询/UART有延迟，可能原guest已继续执行后续调用，不把此停止称为精确首错误指令处暂停。绘制/输入/进程保护及每步截图目视仍保留，不改变完成条件或添加回复。


## 轻量接入校准与首两轮结果

前置新sender包装改变了既有capid-v49（604..619行）看到的outermost caller，使CP_VERSION cmd4的libupdaterufp+1984精确guard失效；原版本应返回unavailable，前置版本却将912503d0/op4原生delegated并等待。light-v1 345.949s、light-v3 218.120s均84threads/无首屏/0键，STOP_FOR_REVIEW正常结束；v1恢复1.303s、v3恢复1.580s，QEMU0/reaped/PID消失/输入不变/锁独立释放。原先加载锁依赖只是排查假设，不当作已证根因；v3已提前解析osal、无运行时dladdr，仍前置失败。

r4将同一v3.so放全部既有preload之后，四条init的原preload前缀逐字不变，所有原caller guard保持在前；CP_VERSION_UNAVAILABLE重新命中，原192线程及待机恢复。实际native libosal ABI另从原码核对（67b0使用W0/X1/W2/W3；5e60使用W0/X1），保留参数/返回值/errno的ASan回归与preload顺序审阅分别见helper build JSON和ap104-light-preload-order-review-v1.json。以上改动都是观察接入修正，未改设备回复或完成语义；不能把首两个观察器候选的启动停滞归咎原固件。

| 运行 | 结果 | 末次RAM/原厂文件 | 收尾 |
|---|---|---|---|
| ap104light4menu600-c115023e | 请求600s，总606.460s；9步逐图到语言弹窗并DOWN环回English焦点，未ENTER确认；无unfetched | RAM语言32，原文件gen2语言32 | required全齐，host error无、QEMU0/reaped/PID消失/input不变/锁释放，ack+API16 1.526s |
| ap104light4bmenu600-09dcd746 | 请求600s，总604.854s；11步逐图确认English，英文菜单实际可见；后续状态请求时已结束，工具拒绝未写旧run | RAM语言0，原文件gen2仍32 | required全齐，host error无、QEMU0/reaped/PID消失/input不变/锁释放，ack+API16 1.566s |

两轮末次原厂文件均SHA be048e8557acc93208425687f823993fc70542036158adea77ae87db74dd53bd，AP/CP bank checksum都正确，force0/0。第二轮UI+RAM证明English已提交到原RAM，不能宣称落盘；关闭MENU后≥60s静置与原值日期确认尚未做完。

上述首两轮有效轻量运行和AP104新增重型断点轮均未捕获unfetched；随后1200秒轻量轮已复现（下节）。重型断点不是复现所需条件；轻重观测改变时序、日志量、启动PID/地址分配等，“重型观测可能抑制复现”仍仅是假设，未构造不存在的重型阳性对照。

## 1200秒保存诊断授权

Lead msg_157c8eaf5a9b要求合并English确认/关MENU静置≥60s/原值日期确认；msg_4e88c7b0d2b2明确允许同一r4、0断点、新host上限1200s，assert/停止条件/20s确认收尾不变。run_candidate104_light_v2仅更改时间界限和授权元数据；保留30键以兼容同一guest输入模块，未使用可选40键。

## 轻量首错：原预算到期后，第一完成迟到

`ap104light4save1200-2e5d177c` 请求1200秒，总417.117434秒，8步到Setup语言弹窗，首个unfetched被宿主观察后停止。末次实际查看的 `ap102-language-step08-reviewed.png` 仅部分画出Tiếng Việt/한국어；未发送第9键，也未确认English。本轮不计1200秒健康通过；宿主轮询/UART有延迟，不冒充精确首错误指令处暂停。

同一用户态CLOCK_MONOTONIC时间线如下，原始serial行号、SHA及原ELF指令字节见[原码与时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104-unfetched-source-timeline-v1.json)。内核printk时钟未混入计算。

| 事件 | 时间ns | 含义 |
|---|---:|---|
| grm_gpe tid279，dynamic_id(0x2a,module82)返回 | 350103662992 | 领取QID 0x808261c0成功 |
| 同线程dynamic_id(0x4a,module0)返回 | 355389662000 | 约5.285999秒后释放成功，caller libgpe+a420 |
| GPE tid280首次显式SendDrawComp进入 | 400101364000 | Flush1207，status0；距释放44.711702秒 |
| 首次显式完成返回 | 400115166000 | alloc -1018/errno1018，完成返回false |
| 原Main失败路径SendDrawComp进入 | 400168432000 | caller libgpe+9c50，status5 |
| 原Main失败完成返回 | 400185742992 | 又一次alloc -1018，返回false |

原libgpe SHA `363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464`：ReceiveDrawComp在+d8ac置w3=1；+d798置w2=0x1388，+d79c保留5000分支，+d7a8调用osal_rcv_msg_tmo。CMF在+a3f0接收，成功或失败最终均在+a41c调用释放。观察到的领取→释放与迟到完成符合接收预算到期；release处errno1022可能是保留值，并非直接测得ReceiveDrawComp返回。本轮没有直接拦截接收入口/返回或读取内核owner；结论结合原指令与实际API调用，保留此范围。

恢复日志没有首错前的第二次零状态完成，原SyncCallback-PLT路径记录数为0；这只是本次已恢复记录范围，不能推广为全局否定证明。两条unfetched分别对应适配层首次status0和原Main后续status5，不能据两条内核日志认定重复零完成导致首错。原超时、完成条件和发送次数均未修改。

收尾：QEMU退出0、reaped、原PID消失，输入散列不变，host observer无错误，guest异常/警告为空；当轮独立复核两锁已释放。guest ack seen1/status0和原API16双核验1.308582秒完成，详见[冻结回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/receipt.json)。这些是故障运行的收尾健康，不能写成guest业务健康。

## 性能离线拆分与版本勘误

最终使用[性能表v3](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104-light1200-performance-v3.md)、[JSON](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104-light1200-performance-v3.json)和[CSV](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104-light1200-performance-v3.csv)。153/153个连续seq1055..1207均有返回和参数；表中是同一worker相邻CMD_RETURN端点间隔，包含生产者/出队空隙、调度、QMP暂停、验证、映射、绘制、复制/哈希/输出等，不能当作单条backend CPU耗时。未记录的入队/开始/后端时钟、life-lock等待、原FIFO深度均为unknown。

释放到首次完成的44.711702秒按右端命令分类：普通K255 blit 21.971897秒、nearest_v1 K255 18.792854秒、fmt2 K255 3.917563秒、Flush 0.029388秒，tile在该窗口为0。seq1165仅16×2 blit却有4.747750秒端点间隔，纹理复制/三次SHA合计192B；seq1159为1×2→441×2，3.954488秒/3532B；seq1161为40×40，2.925427秒；seq1162 fmt2 219×42，2.181211秒。不能仅按像素面积认定瓶颈，proc/maps验证与mmap等需独立测量。seq1154记录command lock等待0.437261秒；未记录不等于全程无锁等待。首Fill1055的9.679061秒在当前领取/释放窗口前，包含上一Flush到新生产者的空隙，不归入迟到窗口。

v1误把带UART后缀的none枚举当作tile/stretch，分类统计已废止；v2临时变量名碰撞损坏时间计算，**v2整体无效**。旧文件保留；v3仅恢复完整已知枚举前缀、保存原token，断言非负间隔及两个窗口总和精确一致。历史批次最终使用[inventory-v2](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104-historical-unfetched-inventory-v2.json)：AP103-r2共2789命令/无unfetched；AP103-v3 seq1780为STALE类拒绝（reason5）并记录0.527150秒锁等待，不能称unfetched；AP103-v4共438命令/2条unfetched，首错Flush437，前一Flush378后59命令，锁等待seq421为0.414932秒。旧v24没有逐命令ns，不用内核时钟补造时长。

## 低开销计时器与AP105离线准备

已另建 `helpers/fx3-gpe-observe-v26-profile104.*`，与Lead接受的v26-perf不同。计时器覆盖proc读取/解析、mmap/munmap、对象字段、command/life锁、backend plan/submit、callback检查/调用、tex复制/输出及完成投递；使用既有F100保留区尾部0x41d640000/0x80000，文件观察器最大写入止于0x41d631000，DTB保留区0x41d400000/0x300000内不重叠。原函数只委托一次，参数/返回值/errno保留，环发布在原锁释放后。life hold为包含时间，texcopy可能含首次workspace mmap，各项不简单相加；原FIFO深度与入队仍未知。

环边界/回卷/嵌套、完成路径准确委托、PROT_NONE复制/原500ms等待等三份ASan/UBSan宿主回归通过，见[host review](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap104-profile-host-review-v1.json)。该计时器未进入guest，亦未叠加AP105。为先验收性能件，AP105仅复制Lead已接受的v26-perf精确二进制（SHA30667f76…00d7ba4），其余AP103-r2 CPIO成员含init/软件LDEC/原关机脚本逐字不变。

Lead msg_d037c7cda3d1明确把运行窗口让给用户TRY1；msg_719755e33697授权AP105离线准备、恢复后再测。候选及host脚本已备，未启动QEMU、未占运行锁、未改TRY1或当前STATE。AP105接收预算内完成、原厂保存和TRY2实际网页/早停验收均待执行，不提前提升首选候选。
