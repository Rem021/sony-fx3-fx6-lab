# libObj 帧握手审计：0x1004 是 timer 通知，完整根因尚未闭合

2026-11-01。只读原固件、既有 serial/printk/snapshot；未启动 QEMU、未修改 runtime。**Lead 的运行序列观察成立，但将 1001→1004 当作同一同步握手没有原码支持。** 1004 的确定发送者是 **appFw** Widget timer 更新函数 `0x176fb4c`，不是 libObj 的 1001 接收线程；它先比较 timer ID，再查询 WidgetBase timer 注册表，成功才发送。AP71 等缺少 timer 通知与首次绘制共同出现，尚不能确定哪一个门槛改变，更不能据此直接注入1004或伪造回复。

本次未达到“接收方1001处理及导致差异的唯一条件、确定性修正”完整验收。可复现证据已落地；下面严格区分证实与未证实，避免把有限审计当成运行修复。

## 复现与证据边界

在项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/libobj-frame-handshake/audit_libobj_handshake.py
```

退出0重建 `libobj-handshake-proof.json`，含五个原件的SHA256、原字节/VA/汇编、六次运行的全部相关事件、握手邻接原行、命名线程完整snapshot和printk匹配项。行号按 LF 分割，保留serial中的CR/NUL，不使用会因二进制提示提前终止的普通rg，也不使用会把VT等字符另算一行的splitlines。脚本另可传 `libObj.so f2820 244` 等三个参数只读打印指定区间。

本次核对 [Capstone 官方 Python 文档](https://www.capstone-engine.org/lang_python.html) 的 ARM64/Thumb 反汇编API；Sony语义只来自本地原件。所有VA为链接地址；CP为Thumb、文件偏移VA−0x108000。脚本检查关键store与反汇编覆盖，并非CPU执行测试或运行时因果证明。

## 1001 与 1004：发送者、字段、条件

| 项 | 原代码事实 | 等级 |
|---|---|---|
| 1001发送者 | appFw `0x16ee6f8` 构造栈上96B；`0x16ee73c` 写u16 1001，+4清零；`0x16ee768–774` 写640×480；`0x16ee77c→16ee6f0→16ee598` 发送 | 证实 |
| 共同发送器 | `0x16ee5e0–5f0` 对8280074d分配；`0x16ee604–614` memcpy；`0x16ee61c–624` source=9088076b；`0x16ee628–634` osal_snd_msg；失败释放，未等待回复 | 证实 |
| 1004发送者 | appFw `0x176fb4c`；`0x176fb78–80` 比较输入ID，不匹配直接返回；`0x176fbb8–c0` getTimerInfo失败直接返回 | 证实 |
| 1004内容 | `0x176fbcc` 写u16 1004至stack+50；`0x176fbc8` 清+54；`0x176fbd0–d8` 写u64 `输入时间−timer记录时间` 至+58；`0x176fbdc–e4→16ee790` 发送16B | 证实 |
| tag1高位 | 1004结构+2/+3（stack+52/+53）未被该函数写入，整个消息未memset；AP60=4a4e1004，AP70=617f1004，低16保持1004 | 证实为padding未初始化；具体旧栈来源未证实 |
| 有效字段错误 | 单凭32位观察器tag1不能证明原协议消费高16，也不能证明有效字段未初始化；1004+8的u64有明确写入 | 排除该证据推导；不排除其他未知缺陷 |

WidgetBase::getTimerInfo 在 libObj `0x1747e0→176ab0`。`0x176ae8` 取管理器+890链表；`0x176af4–b18` 比较widget ID与timer ID，匹配后输出记录+8/+c/+18/+20；`0x176b5c` 遍历next+30，空表在 `0x176b40` 返回false。故“timer不存在”是具体可测的原语义门槛，但保存日志没有该函数的入参/返回值，不能宣布AP71实际命中此分支。appFw `0x2191dec–dfc` 调1001及额外配置；此处不等待1004。

## 队列与发布：已闭合和未闭合

- **8288076c = AP ExternalOSDIF**：libObj `0xf29f0–f2a10` ReceiveASync(...,-1)，成功 `0xf2a20→f2820` 分发；AP70 serial:2148、AP71:2192记录线程名。`0xf28b4–e8` 按source分流：8288076c→f27d8；8280074d→f22f0；828808e1→f2570。因此在此函数里 **8280074d是source而非正在接收的queue**。
- `f22f0` 只分发u16 **6003/6005**，进入f2238/f22b0；没有1001 handler。把ExternalOSDIF称作“8280074d的1001工作线程”不符合这段代码。
- 发布候选原链保持：f2fa0非零分支→f33d0交换+60/+68→f2428构造40B本地msg1→f233c发8288076c→f27d8/f2638。f268c–f2698构造12B **1002**（+8=1003），f25f4发8280074d；f26e0–f2760构造36B **1003** 发8280084d，source8288076c（f1e80–f1e98）。AP70 serial:7655–7657实际命中消息边界，不能据此宣布物理扫描完成。
- **8280084d有CP侧消费者证据**：cpapp `0x4b3632–4b3650` 将1003选择到8280084d（1005选择相邻84e）；`0x4b368c–4b36aa` 以−1接收、交给4b36fc并释放。此函数尚未绑定命名任务/构造注册表，后续payload处理仍需追踪；不能从它反推当前AP已送达或CP已扫描。
- **8280074d的注册接收方、1001处理及6003/6005生成链尚未闭合**。只发现AP发送代码与ExternalOSDIF对其回复source的分发，没有找到可据以命名的libObj接收线程；不能声称它由grm_gpe、内核grm_ma或某特定CP线程消费。
- OSAL已证实的ID规则：libosal_uipc `0x5e6c` 用 `id & 0x7fff` 作索引；`0x5eb8→6050` 按bit15选择内核u_osal_snd_msg（0）或用户态队列（1）。这里的74d/84d/76c均bit15=0；0x8288与0x8280高位不能直接当作线程号。完整高位module/domain位分解尚未恢复，proof保留osal_dynamic_id完整反汇编供续查。

## 首次清屏条件与因果限制

libObj `0x100c48` 是GRM fill命令的执行入口：`0x100c80–88` 从bitmap取得物理地址，成功后 `0x100cbc` 写到FillRectParam，`0x100cc4` 调GpermFillRect，之后完成原命令。gpe wrapper `0xa430` 经SendDraw，`0xd824/0xd83c` 选择80820885/884；Main `0x9c20` 分发opcode0。AP70 serial:7651–7654显示grm_gpe提交Fill/Flush并写614400B@43feb5100，这是清屏执行证据。

**未证实**：哪一个上层绘图分支首次创建这条fill命令，以及它是否受1004影响。1004目标是8280074d，GPE目标是80820884；相邻出现不提供跨线程因果关系。不能把补1004当作已证明可恢复清屏的最小修正。

## 六次运行逐行比较

以下均引用各run自己的serial.log；“无”指保存日志没有该事件，不代表未观测函数返回值。JSON保留完整逐条事件及1001前后邻接原行，两次REMOTE_DMM完成记录在其中可直接核对。

| run | AppFw tid / 1001行 | 1004行及tag1 | GPE/清屏 | 发布1002/1003 | 排队服务已建立 |
|---|---|---|---|---|---|
| AP60 entries-5611350a | 284 / 7545 | 7546 / 4a4e1004 | 7548、7550；清屏7549 | 7556 / 7557 | ExternalOSDIF2145，GPE0 2201 |
| AP66 lut-ed5764ad | 284 / 7598 | 无 | 无 | 无 | ExternalOSDIF2144，GPE0 2196 |
| AP70 lcd-f61554d9 | 284 / 7648 | 7649 / 617f1004 | 7651–7652；清屏7654 | 7656 / 7657 | ExternalOSDIF2148，GPE0 2208 |
| AP71 crypt-68d9c419 | 419 / 11378 | 无 | 无 | 无 | ExternalOSDIF2192，GPE0 2275 |
| AP72 muted-f2a05842 | 438 / 12331 | 无 | 无 | 无 | ExternalOSDIF2177，GPE0 2294 |
| AP73 gpe240-6c2f3137 | 442 / 12577 | 无 | 无 | 无 | ExternalOSDIF2206，GPE0 2277 |

AP71 serial:11379–11396，AP72:12332起、AP73:12578起，AppFw在1001之后继续向3e014d、5503e0及811006e9发送后续初始化消息；不是停在1001等待。六次均无针对74d/84d的`Skip snd`。GPE和ExternalOSDIF服务在1001之前均已有接收等待记录，反驳“这两个已命名AP队列尚未建立”；**无法因此判断74d的未定位接收方是否ready**。printk-decoded.txt的grm_ma初始化都返回0，此模块是内存服务，不等于OSD控制接收线程验收。

观察器限制：`runtime/helpers/ioctl-trace-v10.c:18–38` 的send_unique按target/op/tag1/tag2去重，容量256且抢锁失败丢观察；recv_begin也只记录首次等待。六份serial的SEND_UNIQUE总数分别144/142/198/193/196/195（包含bootin等不同进程），没有单靠总数证实容量耗尽；即使尚未满，抢锁丢观察仍不可排除。因此1004缺失严格称为“没有记录”，而清屏marker也同时缺失可增强未绘制推断，不能取代入口观测。

### 线程snapshot等待点

以下是初始化之后最近的命名snapshot；后续snapshot全部保存在proof。相同的空闲等待也出现在有清屏的运行，不能把它命名为死锁。内核栈没有解出用户态具体调用者。

| run | 线程 / tid | 等待证据serial行 |
|---|---|---|
| ap60entries | grm_result / 227 | 10030：futex等待 |
| ap60entries | ExternalOSDIF / 228 | 10088：OSAL接收 |
| ap60entries | grm_gpe / 229 | 10148：futex等待 |
| ap60entries | MPGRM_GPE0 / 230 | 10206：OSAL接收 |
| ap60entries | AppFw / 284 | 13150：futex等待 |
| ap66lut | grm_result / 227 | 10112：futex等待 |
| ap66lut | ExternalOSDIF / 228 | 10170：OSAL接收 |
| ap66lut | grm_gpe / 229 | 10230：futex等待 |
| ap66lut | MPGRM_GPE0 / 230 | 10288：OSAL接收 |
| ap66lut | AppFw / 284 | 13232：futex等待 |
| ap70lcd | grm_result / 227 | 10220：futex等待 |
| ap70lcd | ExternalOSDIF / 228 | 10278：OSAL接收 |
| ap70lcd | grm_gpe / 229 | 10338：futex等待 |
| ap70lcd | MPGRM_GPE0 / 230 | 10396：OSAL接收 |
| ap70lcd | AppFw / 284 | 13341：futex等待 |
| ap71crypt | grm_result / 230 | 5649：futex等待 |
| ap71crypt | ExternalOSDIF / 231 | 5731：OSAL接收 |
| ap71crypt | grm_gpe / 232 | 5810：futex等待 |
| ap71crypt | MPGRM_GPE0 / 233 | 5892：OSAL接收 |
| ap71crypt | AppFw / 419 | 18010：futex等待 |
| ap72muted | grm_result / 230 | 6517：futex等待 |
| ap72muted | ExternalOSDIF / 231 | 6600：OSAL接收 |
| ap72muted | grm_gpe / 232 | 6729：futex等待 |
| ap72muted | MPGRM_GPE0 / 234 | 6924：OSAL接收 |
| ap72muted | AppFw / 438 | 18794：futex等待 |
| ap73gpe240 | grm_result / 230 | 6620：futex等待 |
| ap73gpe240 | ExternalOSDIF / 231 | 6720：OSAL接收 |
| ap73gpe240 | grm_gpe / 233 | 6867：futex等待 |
| ap73gpe240 | MPGRM_GPE0 / 234 | 6954：OSAL接收 |
| ap73gpe240 | AppFw / 442 | 19216：futex等待 |

## 根因等级与最小修正方案

**证实**：1004是有条件的timer状态通知，不是1001同步ACK；高16位是未写padding；失败运行AppFw越过1001继续执行；GPE工作线程已经存在但没有记录绘制请求。**推断**：AP60/AP70进入了一条含timer状态更新及初次绘制的上层路径，而AP66/AP71–73没有完成同一路径。**未证实**：具体是未调用timer更新、ID不匹配、timer表缺记录、后续draw门槛不同，或观察器丢事件；libInfraCrypt的加载时序究竟改变了什么。AP66在未增加该preload的情况下同样无清屏，已不能用“加crypt必然破坏握手”解释全部样本（AP66:7598及全日志统计）。AP70→AP71完整候选包唯一差分未独立核验，本报告不把Lead描述当作二进制差分证明。

现阶段不应直接补1001回复、发送固定1004、清零padding期待修复、强制提交清屏或增加sleep。它们缺少有效因果依据。**最小可复核下一步是有界观测候选**（交运行链执行，本目录不修改runtime）：

1. 在appFw+176fb4c入口、176fb80条件、176fbc0条件记录widget/input ID、比较结果、getTimerInfo返回和取到的时间，保留原返回值及errno；在libObj+176ab0仅针对该widget记录timer注册表命中。先读并核对指令、处理原prologue/PC相对指令，再制作拦截，不能盲写跳转。
2. 在appFw+2191df4的调用完成、真正的UI绘制/dirty检查入口和libObj+100c48记录单调序号、线程、命令/bitmap身份；明确清屏是否与1004同一次UI更新产生。记录GPE原队列入/出、完成及8288076c发布。
3. 若证实timer尚未注册或被提前移除，最小语义修正是修复导致此状态的初始化/调度顺序，让原timer注册完成后再调用原timer更新；如是我们注入库触发过早回调，应在该注入层保存原事件，待原注册完成单次投递。依据是176fb78/176fbb8的原门控，**具体依赖和patch位置仍待观测**，不能现在承诺这是已确定的修复。
4. 若getTimerInfo成功且发送1004却无绘图，应停止timer方向，按100c48上游的dirty/frame门控继续定位；若handler根本未进入，先找调用/虚表事件，而非添加队列ACK。

运行验收应在保持同一候选件/环境下重复至少三次：原timer条件命中、原FillRect/Flush完成且DMM生命周期有效、8288076c→1002/1003边界出现；另对timer不存在的负例保持原“不发送”语义，禁止伪造成功。像素独立读回、菜单文字实际绘制和CP/显示输出仍是独立验收。没有运行授权的本worker没有执行以上步骤。

## 留给续查的准确入口

- appFw+176fb4c：timer更新的虚表绑定和所有间接调用；输入ID常量经GOT+471f428指到BSS，不能从文件填猜测ID。
- libObj+176ab0：timer表+890、记录next+30；追addTimer/removeTimer的生命周期。
- libObj+100c48：首次FillRect实际命令execute；追对应命令创建和enqueue。
- 8280074d控制接收者→1001→6003/6005，以及CP侧4b3628接收8280084d之后的格式/状态消费，仍需恢复完整服务注册表。
