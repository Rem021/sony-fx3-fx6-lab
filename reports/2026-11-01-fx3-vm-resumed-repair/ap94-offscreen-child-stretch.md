# AP94 离屏子块与首次设置

2026-11-02。**最终 AP94-r4 完整300秒通过健康与 im.elf 存活检查，原资源子块绘制及 nearest_v2 已走通，英语设置页、配对QR页与MENU返回均有实际PNG。首次设置尚未完成，拍摄待机与菜单浏览仍未验收；已转入AP95宿主逐步白名单计划。** 前三次受控拒绝记录全部保留。

## 实现与证据边界

基线 AP93-r5；合同 msg_fd22adc6ac57。已完整阅读 [离屏审计](../../work/fx3-vm-20261101/lead-claude/audits/offscreen-subblock/README.md)，截获写操作重放脚本，不改审计文件；proof SHA256 精确等于 `331cd0acab44d79634d297d7662cf0f46af0304add1f4071c2ee31455febb4a6`。

- 新 GPE v19/backend v4/resource v4：成功原 malloc103550 登记 parent/child epoch、logical/physical/bytes/align；free10364c 入口与 close/重开/父失效撤销。资源池离屏目标逐行匹配唯一活跃父与子块；保留545/native403目标及 OSD frame_target 规则。
- 原 flags0、selector0、K255、fmt0、rotation0、零 coordinate/adjust、完整 clip 的整数4倍子集：`nearest_v1` 原16bit覆写，`approx_blend=0`，不改原 P73/selector。未知变换继续拒绝。
- 七处 compaction 入口只观测，记录是否在绘制期间进入，不阻断。子块账本不等于 bitmap 命令引用锁；queued ABA/bitmap 绑定/compaction 保护仍未覆盖。
- RM core v2 不变；输入改为 UP→ENTER，再逐页实际查看 PNG 后默认 ENTER ≤12，待机后 MENU 与四步导航。host/guest 同时限制顺序与总数19；每步≥4s。只写新增软件控制页8B，不写原 UI 状态或参数。

[宿主回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-host-check.json)：审计12项 Python 人工模型重放；C 两组13456像素覆写与每例2784B padding/源/邻块不变、十项实际子块准入、九项零写拒绝及保留回归 ASan/UBSan 均退出0。旧73条参数与独立参考 FNV 全相等。[七探针 Unicorn 回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-compaction-probe-host-check.json)确认 GPR（ABI scratch x16除外）、SIMD、NZCV/FPCR/FPSR/SP/LR 保存，不代表实际 compaction 验收。输入 C sanitizer 与 host 顺序模型通过。

## 第一轮：ap94child-ad25d7a1

[候选构建](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-child-stretch/build-receipt.json) / [原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94child-ad25d7a1/receipt.json) / [复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94child-ad25d7a1-review.json) / [0x11a后保存请求时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94child-ad25d7a1-post11a-requests.json)。请求300秒，因新拒绝在39.837481秒受控停止。

`qemu_exit=0 / process_reaped=true / PID_absent=true / inputs_unchanged=true / 双锁FREE / missing_markers=[]`。无 symbol lookup error 或 guest fatal。结尾完整快照 im.elf PID228、uptime36.65，三条原 im.elf maps 仍在。

RM 两请求原生消费释放，empty-slot 原 Start 为2/2、notify1000/1010 status0，无 INIT_TIMEOUT、Mount 或 MOUNT_ERR。只有第一步 UP3 的 down/up，两消息经原输入接收；未发 ENTER。没有 UP 后独立 QMP PNG，不据旧表面截图推断 UP 完成。

失败原文 LF31869：`seq86 BitBlit fmt0 source6×6 dst43ae96100 src410924f80 flags1000000000001 result5 reason4`。`src_fmt=0i` 是该行末与内核输出交织；原144B可独立读出 src_fmt0。统计器因此列此条为 incomplete：96条完整记录均0 + 1条含真实失败的不完整记录，**不能写“全部绘制成功”**。现场紧邻 AP_SNAPSHOT_1 的 DMM 大段输出，只有相关性，尚未证明争用因果。

目标父 LF2604 按 native_open/type403/epoch1 登记且未 retire/reopen；源父与子块也已登记。新增源 child 门仅 offscreen_child 分支执行，故未将 native403 源误施加 child 要求。[同原144B宿主对照](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-seq86-host-comparison.json)在 v18、v19 的“源父区间但无child”均通过，不能替代 guest 根因。已 escalation msg_298bb40cb2f0 / msg_9b47306a5806。

唯一已实际复核的画面为**输入前日文标题“言語”语言选择页**，含 English/日本語/Français/Deutsch/Italiano 列表；不是 UP 后画面：

![AP94 输入前原语言页](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94child-ad25d7a1/ap93-phaseA-before-SETUP.png)

最终固定545 QMP样本 SHA `2485079bdfe8c91590235540c1929a813f03a96b17cae33b32d53539e77e708e`，只代表旧545表面；没有把它当作新 active frame 或新页验收。记录未观测到 compaction entry，不证明 compaction 不存在。

## 诊断续轮

Lead msg_49124d89bac2 已授权：v19r2-diag/screen-v2-diag 只加 stage/errno、父对象复核原读值、screen_live/proc/mmap 失败诊断，不变更判定、不重试、不放宽。backend/resource/输入/RM/OSD 保持第一轮。宿主保留套件 ASan/UBSan 通过，使用同一 run_candidate94.py/300秒运行；结果如下。


### 第二轮：ap94r2diag-4f9de767

[原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/receipt.json) / [复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r2diag-4f9de767-review.json) / [0x11a后时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r2diag-4f9de767-post11a-requests.json) / [新缩放请求原证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-noninteger-stretch-runtime-evidence.json)。请求300秒，123.881124秒因新未覆盖规划受控停止；同样 `exit0/reaped/PIDabsent/inputsunchanged/双锁FREE/missing[]`。im228 最后完整maps uptime118.94，三条 im.elf 映射仍在，无 symbol lookup error/fatal。

第一轮 seq86 未复现，无 screen_guard_fail 记录；**不能据续轮成功认定瞬时 `/proc` 争用根因**。没有放宽守卫或新增重试。

资源池 seq216/218 FillRect 与217/219缩放成功：活跃child epoch27/28及29/30，parent epoch3，same_parent1；29×29→116×116、`replace/nearest_v1/approx_blend0`。原应用继续开192隐私页、18e手机引导页，证明已越过 AP93-r5 阻塞。11个provider分配均原接收者原生free0一次；4步共8个 down/up，经原输入队列消费。完整GPE372条=370成功/2拒绝，另26条交织不完整，不作全局无丢失声明。

四张**实际打开复核**的PNG均有独立QMP物理SHA与原leased committed snapshot相等的回执：

| step/key | 实际画面 | 当前物理 | raw SHA256 |
|---|---|---|---|
| 1/0x3 | [Language标题的语言选择页](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/ap93-step-01-key-003.png) | 0x43ae96100 | `bc4846e012450dd2403d49cd98cc7157199366f742f8223cf28dbd25736fc01e` |
| 2/0x1ac | [英语生物识别隐私说明/QR码/sony.net/dics/privacy](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/ap93-step-02-key-1ac.png) | 0x43ae96100 | `39c6280d79aba370c3ae7229d811d4cea0b80ddcc3d26d9fefd229bec5cce514` |
| 3/0x1ac | [初始设置手机引导/Creators App/Set on the camera](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/ap93-step-03-key-1ac.png) | 0x43feb5100 | `3e307e4ab567896c8915681e523b226d9e09d6925509e777cb45668d0d8c0eab` |
| 4/0x1ac | [Connect Smartphone；Bluetooth Function设为On中的提示/Cancel](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/ap93-step-04-key-1ac.png) | 0x43ae96100 | `80826296f65c7fa57bafc1f5666dd5b08add5f525d217b0fb8bb9a43c416724a` |

![原应用英语隐私说明（step2）](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/ap93-step-02-key-1ac.png)

![原应用手机连接设置（step4）](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r2diag-4f9de767/ap93-step-04-key-1ac.png)

step4后原应用继续渲染，seq402/406在planner退出 `reason2/errno0`：源49×49 stride64 → 目标103×116 stride112，fmt0/selector0/K255/flags0/rotation0/fullclip。原先只准入4×，因此保持拒绝；父字段原读112B成功，两端child记录与原144B已保存。停止后未发送第五步；没有待机/MENU验收。

### 第三轮合同与构建

Lead msg_c030a5a3da12 批准同一关闭混合子集推广为任意正整数源/目标尺寸，包括非等比/缩小；采样 `min(sw-1,floor((dx+0.5)*sw/dw))`，y同理，marker `nearest_v2/approx_blend0`。硬件采样精度未证实。旋转/其他flags/其他格式门、完整clip、坐标子集、父/child/屏幕守卫均保留；不把未知组合泛化。

[nearest_v2宿主回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-r3-nearest-v2-host-check.json)：独立Fraction有理数生成全像素参考，49→103×116、49→7×5缩小、1×N/N×1/1×1边界和原29→116四倍相同预期通过；padding/源/邻区不变，保留套件ASan/UBSan退出0，旧73独立FNV未变。新版本 GPE19r3/backend5；同一300秒逐页脚本，第三轮结果如下。


### 第三轮：ap94r3center-f3bba0ba

[原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r3center-f3bba0ba/receipt.json) / [复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r3center-f3bba0ba-review.json) / [0x11a后时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r3center-f3bba0ba-post11a-requests.json) / [proc解析失败证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-proc-parse-evidence.json)。请求300秒，39.930069秒受控停止；exit0/reaped/PIDabsent/inputsunchanged/双锁FREE，无symbol error/fatal，im228最后完整maps37.44。**missing_markers=[approx_stretch=nearest_v2]**：首次UP即停，尚未到新的关闭混合缩放路径，不将本轮写成该功能通过。

seq93 `stage=screen_recheck/reason4/errno0`，同一时刻辅助 `/proc/udm/dmm_extents` 守卫 code3，读取38419B、EOF0、errno0。原行完整115B，内容是常规id0002：`429b00000 (400000000+29b00000) 06900000`。两端父对象112B复核成功，与登记一致。原格式sscanf宿主重放n12/used115/len115，地址/长度/末尾条件全通过；按原code3条件排除，**可推断此读中已遇过同id2，触发重复ID项**。没有保存此读的全部38419B，因此先前那条重复行未独立保存；AP_SNAPSHOT_1输出相邻，不夸大为并发因果已经完整闭合。该类别为直接proc解析失败，不是新49→103采样失败。

### 第四轮修正合同

Lead msg_4f0238f1bb4d：已登记原屏幕对象完整112B字段、epoch/state、关闭/释放与行范围为权威，proc作辅助；不一致仅有界重读一次，仍不一致且原对象核验通过才放行，并保留原行和 `screen_recheck=object_authoritative proc_inconsistent=1`。字段不符/epoch改变/关闭仍拒绝。正常proc与fallback均使用本地原资源epoch，避免切换依据造成假epoch变化；本地epoch不是原厂generation。

GPE19r4/resource5/screen3 实现同一检查，OSDv6通过已有frame_target acquire/recheck接口共享，无需改OSD二进制或读取租约。OSDv6旧extent函数仅有定义、无调用。init只将AP后快照中的DMM表cat改为明确skip marker；启动前DMM表、进程maps/uptime/任务快照均保留。落实Lead msg_7e5abad34096澄清：新增活跃child要求仅约束资源池目标，源保持原父区间规则，child只作可选遥测。

[第四轮宿主回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-r4-object-authority-host-check.json)：重复/截断/解析不一致+原对象复核通过，绘制与OSD目标接口均放行；字段错误/epoch改变/close均零写拒绝。源无child但父有效放行、目标无child拒绝。全部保留套件ASan/UBSan退出0。[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-r4-object-source-policy/build-receipt.json)从r3派生，同一300秒脚本第四轮结果如下。另有未运行的中间构建ap94-r4-object-authority（未加入源策略澄清），不作guest验收证据。


### 第四轮：ap94r4object-37305ab2（最终AP94）

[原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/receipt.json) / [复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r4object-37305ab2-review.json) / [0x11a后保存时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r4object-37305ab2-post11a-requests.json) / [GPE统计](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94r4object-37305ab2-gpe-statistics.json) / [来源账本](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-r4-source-ledger.json)。完整300秒，实际302.103312秒；`exit0/reaped/PIDabsent/inputsunchanged/双锁FREE/missing[]`，无symbol lookup error/fatal，im228结尾三条maps uptime294.84。

本轮328条完整GPE均result0，另20条交织不完整；原49×49→103×116 nearest_v2已走通，approx_blend0。未观测到proc解析失败、对象权威拒绝或compaction入口；fallback已做宿主反例测试，但本轮未触发，**不声称guest已实测fallback分支**。AP运行期DMM快照cat改为skip marker，原进程maps/uptime快照持续。

15个RM/input原生分配均由原接收者free0一次。cmd9/3完整请求与独立原接收者owned reply header/status0/payload匹配。provider的136B串口reply LF5664存在奇数长度hex交织；保留原文，以LF5681完整原接收者136B副本复核，未补造或修复原包。新review_ap94_v2优先匹配完整原owned记录，不把坏序列化行当包。

六步独立QMP物理读回SHA均与对应原native lease committed snapshot相等，均实际打开查看：

| step/key | 实际画面 | 物理 | raw SHA256 |
|---|---|---|---|
| 1/0x3 | [Language语言页](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-01-key-003.png) | 0x43ae96100 | `229041acf0cec3f748f118f8025944a288857b7ad1cb5dd5186dd449835ff0bb` |
| 2/0x1ac | [英语隐私说明](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-02-key-1ac.png) | 0x43feb5100 | `39c6280d79aba370c3ae7229d811d4cea0b80ddcc3d26d9fefd229bec5cce514` |
| 3/0x1ac | [手机初始设置引导](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-03-key-1ac.png) | 0x43ae96100 | `3e307e4ab567896c8915681e523b226d9e09d6925509e777cb45668d0d8c0eab` |
| 4/0x1ac | [Bluetooth Function设On中的过渡提示/Cancel](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-04-key-1ac.png) | 0x43feb5100 | `80826296f65c7fa57bafc1f5666dd5b08add5f525d217b0fb8bb9a43c416724a` |
| 5/0x1ac | [Install Creators App配对QR页（ENTER不推进）](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-05-key-1ac.png) | 0x43feb5100 | `d5b2ca5616479eece8d0e59326aaf17c8c88b4e47b7b91421728e5768b1e440b` |
| 6/0x1ab | [MENU返回手机初始设置引导](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-06-key-1ab.png) | 0x43ae96100 | `3e307e4ab567896c8915681e523b226d9e09d6925509e777cb45668d0d8c0eab` |

![原应用配对QR页（step5）](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-05-key-1ac.png)

![MENU返回手机初始设置页（step6）](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-06-key-1ab.png)

手机初始设置页底部“Set on the camera”对应删除键图标；默认ENTER实际进入手机配对。Lead msg_87735767677d 授权QR页MENU返回，已验证；旧guest固定plan在首次MENU后只准四步导航，无法继续设置/再MENU，因此未向错误页面发送导航。Lead msg_8162589b2b22转入AP95：最多30步、宿主逐次白名单指令+按下时长、每步实际查看PNG再选择；删除键待独立审计核实后加入，尚未运行AP95。

STOP_FOR_REVIEW写入请求未被driver作为早停处理；本轮自然到达300秒，receipt `early_stop_reason=null`，不误报提前退出。固定545最终样本不单独代表当前页；以上六步current-frame物理关联回执用于输入/画面反馈。仍未到拍摄待机、NO CARD或原MENU浏览，不作可用菜单宣称。
