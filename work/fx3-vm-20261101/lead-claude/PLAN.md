# FX3 VM 菜单移植 — Lead 计划（Claude 主导，2026-11-01 起）

Orca Run: run_46113644da79。公共上下文: COMMON-CONTEXT.md。

## 组织
- 运行链（构建候选件 / 跑 QEMU / 改 runtime/STATE.json / 报告回执）只能有一个持有者，用 .run.lock 串行。
- 静态审计与独立模块实现并行派给 Codex 工人，只写 lead-claude/audits|impl/<任务>/，由 Lead 验收（脚本复跑、哈希一致、VA 证据、未证实项）后集成。

## 已验收审计（2026-11-01）
| 请求 | 结论 | 模型动作 |
|---|---|---|
| VDF 0x11a LCD 亮度 | AP send_and_wait timeout=-1，**卡住 SeqQueueDispSwi**（AP66 自 376s 起）；CP 旧0x0102→回复0x111a/12B/status0 | **P0：下一轮实现**，只接受捕获14B（selector1/亮度6），回 `0d201a110c00018000000000` |
| VDF 0x118 PanelOut | AP no-wait；CP 旧0x0100→0x1118/12B | 可选：保存状态+回 `0d2018110c00018000000000`（AP 不等待；需先确认 main-thread 对未请求回复的处理） |
| VDF 0x159 OSD on/off | AP no-wait，原路径**无回复** | 仅记录状态 pending_f030，**不得回复** |
| GPE 菜单绘制 | opcode0..5、FillRect56B/BitBlit144B/Flush24B 字段表与完成语义 | impl/gpe-backend 实现 P0–P2（进行中） |

## AP70 结果（2026-11-01 19:4x）
- 0x11a 回复被消费释放，SeqQueueDispSwi 越过 sequence_display_setup::set_lcd_brightness，发出 no-wait 的 VDF 0x429/0x500。
- **新阻断（Lead 发现）**：约 10 秒后 `im.elf: symbol lookup error: appFw.so: undefined symbol: iCrypt_HasPublicKey`，主进程被动态链接器终止。appFw 导入 9 个 iCrypt_*，已提取分区无提供者。→ 审计任务 audits/icrypt-missing（含全量未解析符号清单），之后由运行链加最小桩库。
- ADF 0x32e/0x33d：子任务句柄进入启动完成屏障 2b6353c（四句柄），0x33d 阻塞启动收尾 → audits/adf-032e-033d。

## 下一步顺序
0. iCrypt 桩库（主进程存活前提）
1. ~~0x11a 软件回复~~（AP70 完成） → 运行验证 SeqQueueDispSwi 越过 sequence_set_lcd_brightness，观察 BACK_LIGHT_MODE 后续请求。
2. 0x159 静默接受（防止被当作未知请求委派）。
3. GPE 后端 P0–P2 接入 gpe-observe 新版本，捕获菜单真实 GPE opcode 分布。
4. 显示发布：VDF plane/f024 → 宿主可见帧（QMP 读回 → PNG）。

## Lead 决策记录
- 2026-11-01：ADF 0x33d 采用**静音软件后端**：独立 64KiB、64KiB 对齐的 guest 预留区（清零，容量≥0x8480），回复 133d/24B/status0/+16 phys64；仅声称地址/注册状态，禁止播放命令，不冒称原厂提示音。0x32e 只接受 body `08 00`，回 `0d202e130c00018000000000`。依据 audits/adf-032e-033d/README.md。
- 2026-11-01：iCrypt 不做桩。原机由 IMDB 第86项 dlopen(0x101) 加载 libInfraCrypt.so；AP70 终止前未加载。AP71 先在现有 preload 末尾追加 /usr/lib/libInfraCrypt.so 仅恢复符号可见性（未 iCrypt_init 时 Has* 原厂自身返回0）；同时观测 IMDB 第86项为何未被加载。依据 audits/icrypt-missing/README.md。
- 2026-11-01：ADF 提示音注册 13 轮 0x327/40B→0x32a/10B（26 包）按 audits/adf-beep-regist 合同实现静音保存；冲突 e004/越界 e002 不得伪造。后 4 轮依赖文件/DMM/跨芯片传输，需运行中逐项观察。
- 2026-11-01：发现 libObj 帧握手（0x8280074d 0x1001→0x1004→GPE 清屏）在 AP66/AP71+ 不出现，AP70 出现 → audits/libobj-frame-handshake。
- 2026-11-01：提示音后 4 轮按 audits/adf-beep-file-dmm 方案 1 实现：remote DMM 单元 0x70817（6×50KiB，预留 41db00000/60000，句柄 8402..8407）+ 用户态 ICDT（0x02820746 接受→另发 24B 完成到 0x0282078f，callback/context 取自本次请求），静音清零目的区。待 AP75 观测后作为 AP76。
- 2026-11-01：libObj 握手审计静态未闭合（outcome failed，边界清楚已接受）→ AP75 有界运行时观测，禁止补发 1004/强制清屏/sleep。
- 2026-11-01：按键注入合同已就绪（audits/key-input 方案1）：capid 同进程原 OSAL 发送 20B 到 0x807a0020（src 0x00410025），MENU=0x1ab 按下 `ab01000000000000010000000000000001000000`，抬起 status=0；方向键 上3/左15/下30/右1af/确定1ac。marker 须标明合成输入。待启动屏障越过且有绘制后再用。
- 2026-11-01：AP76 完成提示音 26/26 包 + 4/4 ICDT（v30），屏障状态未证实（license/0x325 无证据）。
- 2026-11-01：UI 首绘不以启动屏障为前提（AP70 首清屏早于 0x32e/0x33d）。首要嫌疑（B 级）：AppFw 主循环 16f2478 `a18>2 && !a12` 待消费 timer 积压门控——TCG 下 guest CPU 慢于墙钟，内核 utimer 20000 周期回调堆积。AP77：先无改动观测主循环门控，再用同候选 + QEMU `-icount shift=0,sleep=off` 对照（模拟器时钟层修正，不改原厂语义）。
- 2026-11-01 AP77a：启动 sequence tid327 中 license/volume/beep 自然完成；在 vdf_srvc_set_timecode（appFw 2debbb4，发 0x9059000e 经 Dataflow，timeout=-1）无回复处卡住，get-func 未创建 → audits/svc-9059000e。UI 主循环处理 150000、0x30072 后 AppFw 线程 futex 等待；timer 生产 11381/消费 1 → audits/appfw-30072-wait。更正：AP77b 的 9821 秒是 printk 尺度代理值，icount 对照不能排除时序假说。
- 2026-11-01 因果链闭合（审计 A 级静态 + AP77a 栈拟合）：AppFw 处理 0x30072 → scr0039_boot_controller → condition_variable 等 sequence_boot+1b8 事件；sequence_boot 在 2b638b8 内依次经 VDF timecode（0x9059000e，Dataflow 52B，回 36B 规范回复）→ get-func 0x325 → 四任务屏障 → 2b6838c notify_one。AP78：先只读抓完整 52B 冻结白名单，再实现 timecode 回复 + 0x325 静音能力回复（28B，能力字节 80），观测 notify 与 UI 恢复消费/首绘。
- 2026-11-01 AP78b：timecode 回复已消费，sequence_boot 卡在 VDF 0x165。尾段审计 audits/boot-vdf-tail 给出完整同步清单。AP79 实现已闭合的 0x165(…5900)/HDMI 010a(status1)/0101/0117×5；未闭合 change_mode pin、0119、0328、digital level 另派审计；DMM op18 保持 -1024。
- 2026-11-01 AP79：0165/HDMI 8 包 + 0x325 消费；四任务 license/volume/beep/getfunc 自然完成。阻塞于 change_mode 首个 getpin（9284074a）。pin 审计：表 9ab1258，11 连接 / 33 包（22 GET + 11 REQUEST_CONNECT）。AP80：软件 pin 管理器 + 0328/digital/0119（audits/pin-topology、audits/boot-deferred-0119-0328-digital）。
- 2026-11-01 AP80a/b：33 pin 回复消费，四任务屏障按真实句柄 1/3/2/0 归零正式越过；0328 path3、digital op3 消费。0119 实际 enum2（hrev1/vrev1/osdRev0，来自参数 243 REVERSE_CLOSE 分支）。
- Lead 决策：按原语义接受 enum2——独立虚拟面板 consumer 保存 control3 与 osdRev0 后回 0d2019110c00018000000000；逻辑帧缓冲不改像素，宿主导出按逻辑缓冲原样并标注面板控制；触摸注入按 enum2 两轴反向（libObj d6ac4..d6b0c）。不改虚拟铰链状态去凑 enum0。
- 2026-11-01 AP80c：0119 enum2 consumer→1119 消费→单任务屏障→run_i 返回→原 notify→UI future 返回（启动链全程原厂自然完成）。随后 SeqQueueNetwork 的 libInfraSKD 读 /dev/mem 物理 0xffffb8eb（Mira BootROM 加密取数垫）外部总线异常。
- Lead 决策（AP81）：SKD 采用"安全密钥硬件不可用"降级——仅对精确 /dev/mem mmap(offset 0xffffb000,len 0x1000,PROT_READ,MAP_SHARED) 返回 MAP_FAILED/ENODEV，走原厂 SKData_Init 失败→CipherInit 错误→data_encryption 非致命路径。不使用 A7 IV 公开 ROM（会在 0xf340f000 继续崩，且非 FX3 本机），不伪造密钥/零页。
- 2026-11-02 AP81：SKD 降级非致命，UI 主循环恢复（dequeue 495/timer 466），首次 GPE FillRect 640x480 fmt0 + Flush + 8288076c 发布，物理读回首帧为均匀黑（非菜单）。随后 sequence_mode_transition::enter_face_all_deletion_mode_proc（option6，原厂 UUD reset：Backup 02cf1841<02cf1842，种子 0/4）发 90050004 getpin。决策：按原语义完成 UUD reset，不预改 Backup。AP82：表 9ab2518 新增 3 边/6 端点（IMAGING YC OUT1→BB YC IN1、RAW OUT0→BB RAW IN0、SYSND OUT0→ADF SYSND IN0），6 GET + 3 CONNECT，GET 外层 ReplyId=90050004。
- 2026-11-02 Lead 决策（GPE P3）：硬件混合舍入无 oracle 不可逐位闭合；为可视菜单实现**近似视觉模型**：未预乘颜色（c3=alpha）+ 标准 source-over，常量 alpha K 按审计寄存器路径参与，marker approx_blend=1，绝不称逐位等价；format2..4、动态 CLUT、未知 flags 仍拒绝。impl/gpe-p3-approx → backend v2 + adapter v14。
- 2026-11-02 AP82：42 pin 消费，UUD reset 原厂完成（Backup 4/4）；人脸登记准备 sequence 申请 remote DMM 0x1d9（单槽 0x64000，另 1da/1db）→ 现模型 -3 → assert。AP83a：按 audits/dmm-unit-1d9 实现三单元（预留 41dd00000/0x90000，句柄 8408..840a），ICDT 对这三单元做**真实字节复制**（人脸数据，不清零）。AP83b：集成 GPE v14（近似混合）。
- 2026-11-02 AP83a（v41）通过 300s 健康验收：remote DMM 1d9/1da/1db + 1db open、人脸 ICDT 3/3 真实复制、pin 42/42、Backup 4/4；GPE 仍仅首清屏（黑）。AP83b 换入 v14。并行审计 audits/post-clear-idle：首清屏后 UI 不再绘制的原因。
- 2026-11-02 根因（A 级运行证据）：AP83a UI 实际更新 2 次、backlog_skip 559、a18 末值 12320（timer 生产 12853/消费 532）——TCG 单核模拟过慢，原厂主循环积压保护 16f2478 持续跳过 UI。修正属模拟器层：AP84 对照 -smp（按原厂 AP 核数）+ MTTCG，以及 -icount shift=0,sleep=off，用门控计数器度量，不改 guest。
- 2026-11-02 AP84a（原厂 4×A35、MTTCG、原厂 cpuset 语义）UI 仍仅更新 2 次 → 积压不是唯一根因。审计 post-clear-idle（B 强）：AppFw 在 drawFramebuffer 前置回调等 ExternalOSDIF 上一帧发布完成信号量，需 source 8280074d 的 6003/6005 释放；另 SeqQueueCommon 等 VDF 0x152 peaking。下一步：audits/osd-completion-6003（原厂完成通知 schema + 无头 OSD 消费者合同，消费点即 PNG 导出点）与 audits/vdf0152-peaking。
- 2026-11-02 AP84 三种配置（4 核 MTTCG、原厂 cpuset、icount）UI 均仅 2 次更新 → 积压非主因；新基线 = 4 核 + 原厂 cpuset（r2）。
- Lead 决策（AP85）：OSD 完成原厂 CP 发送者/schema 未证实（audit outcome failed，边界清楚），但 AP 6003/6005 回调 A 级证实不读负载、不校验帧身份/状态。实现**软件无头 OSD 消费者**：在原 FB/bitmap 读租约下有界快照→PNG→释放→以 source 8280074d 向 8288076c 回 6003（负载取 AP 接收路径要求的最小长度、零填充），marker original_schema_unproven=1；校验失败不 ACK。同轮实现 0x152（回 0d2052110c00018000005900）。
- 2026-11-02 AP85r4：0x152 消费；无头 OSD 消费者首帧真实快照后 6003 + 数百次 6005 被原厂消费，drawFramebuffer 前置等待返回（发布闸门越过）。仍无新绘制。新阻塞 VDF 0x400 → audits/vdf0400；并行 audits/display-target-hinge（REVERSE_CLOSE 是否抑制 LCD OSD）。
- 2026-11-02 审计：0x400 = sequence_sys_set_timecode_tcmode（SYS/TCUB），回 0d2000140c00018000000000。显示目标：原厂 27ed7f4 在面板类别 270=2/9（REVERSE_CLOSE 等）且 active display=MONITOR 时改为 NONE（关显示）；铰链四键 GPIO bank7 bit18..21（我们未建模），enum2 可来自 7 类状态，需采样。Lead 决策：AP86 加被动采样；若证实铰链无初值导致不可见类别，AP87 声明虚拟面板 NORMAL_OPEN，经原输入协议（807a0020/src 00410025，V1/H0/C0/S0 键 71c4/71c5/71c3/71c6）送状态，0119 enum0 事务另审。
- 2026-11-02 AP86A 证实池耗尽：GMSGQ 74D 1663 / 84E 1315 条无 consumer/free，normal 池仅剩 64B 碎片。Lead 决策 A：软件消费者作为 74D/84D/84E 的 CP 接收端替身接收全部消息（GUI 1000/1001/1004 存状态不回复；未知类型记录后 free；积压按序排空），与 0x400 合同 + 显示/铰链被动采样合并为 AP86B。
- 2026-11-02 AP86B：CP 接收端替身使池恢复（free 392064/524288）、0x400 消费。显示采样：五铰链键 cache 全 0x7fffffff（无输入）→ 270=7 VALI_ANGLE、243=2；d22=MONITOR（未关显示）；GRM dirty 仅首次 1 后恒 0 → UI 运转但无界面元素需绘制。下一步 audits/first-screen-trigger：首个场景（拍摄待机/首次开机设置界面）创建触发条件。
- 2026-11-02 首画面审计：UUD reset 清理队列（11 项）卡在首项 sequence_sys_set_timecode_run 的 0x402（回 0d2002140c00018000000000）；后续 preset 0x404（回 0d2004140c00018000000000）、人脸删除（local/remote DMM 同步、0206 无回复）、release 403d/f000 等。日期 Backup 01b4 已为 MANUALLY（seed-date-clock 所致），不会出首次日期屏。AP87：实现 0402/0404，按顺序推进队列，捕获其余项，观察删除完成通知 30386 与首屏重入。
- 2026-11-02 AP87-r2：0402/0404 消费，人脸删除完成事件 0x30086（审计笔误 30386 已更正）由原厂自然发出并被 AppFw manager 接收；随后 open_screen 依次 0x2ae scr0039_boot → 0x2af scr0039_shutdown → 0x2ae，活动 controller 停在 scr0039_boot_controller，无新 GPE。→ audits/boot-screen-controller。
- 2026-11-02 boot-screen 审计：UUD 清理后原厂发 MODEL_POWER_OFF(0x3002c) → shutdown → 内核 Backup_reset_all(1) 与 (4) → 各自向 CP Backup 903e0811 发 40B op33 并 timeout=-1 等回复。CP 侧 reset 可由 FX3 原厂种子投影诚实提供（flags1 317 项 / flags4 2 项，当前与默认 0 diff）。
- Lead 决策（AP88/AP89）：AP88 实现 CP Backup op33 reset 软件后端（先只读捕获实际 40B/flags，严格两次顺序，按原种子投影执行重置后回复），让 shutdown 自然走完并观察电源关闭请求；AP89 以 AP88 关机后保存的 Backup 存储作为下一次启动输入（模拟重启），验证第二次开机走正常路径并显示拍摄画面。
- 2026-11-02 AP88：首条 Backup op33 已经内核 reg_public 捕获冻结（40B flags1）。早期偶发故障根因：GPE 工作线程在 v14 setup 替换绑定前进入原 setup，写真实寄存器 0xf3400280（AP86B 首轮同因，原归因 display DSO 更正）。修正：在 osal_create_thread 的精确 GPE 线程创建点先完成绑定再放行。
- 2026-11-02 AP88b-r4：GPE 提前绑定生效；两次原 Backup_reset_all（F1 317 项、F4 2 项）经软件 CP Backup 后端返回 0，关机流程继续后出现新致命（待辨认）。Lead 决策：关键持久化已完成即进入 AP89，用 backup-after-shutdown.bin 作为下次启动 Backup 输入模拟重启。
- 2026-11-02 **AP89 突破**：以 AP88 关机后 Backup 回放模拟重启 → UUD false，正常开机；开屏 0xfa → 0x2c7，首次大量 BitBlit（dst 545 屏幕缓冲，src 0x41052…/0x41092…/0x410c6… 资源区，src fmt0 与 fmt2），被 v14 单 extent 门拒绝（reason2/result5）。下一步 audits/gpe-fmt2-resource-extents：fmt2 语义（疑为 A8 字形蒙版 + 颜色参数）、格式转换 BitBlit 路径、资源 DMM extent 的原厂真实生命周期识别。
- 2026-11-02 首个可见画面 = Caution [MOUNT_ERR_EXTMEDIA_SLOT1_FOR_AUTO_TRIGGER]（dlg_dbl021_base，存储卡槽1挂载错误）。AP89 73 条 BitBlit：28 fmt0 通用 / 36 fmt0 缩放 / 9 fmt2（op14，色 ddddddff）。资源堆 mpMemoryHeap 410524000/400000、Heap2 410924000/340000、TextHeap 410c64000/200000（原厂日志）。
- Lead 决策（AP90，GPE v16）：资源 extent 仅在 libObj 1032a0 成功返回时按原对象字段（+10 身份/+38 type/+40 uhdl/+58 逻辑/+60 物理/+68 大小）登记，release 103454 与绘制读锁串行，不按地址区间放行；fmt0 通用沿用 v14 近似；fmt2 = A8 覆盖度×前景色 straight-over 近似（approx_fmt2=1）；缩放 = 最近邻近似（approx_stretch=nearest_v1）；其余拒绝；校验先于写像素。
- 2026-11-02 **AP90-r2 里程碑**：资源父区间 malloc_parent_v1 登记 + GPE v16 近似后，73 条 BitBlit/Flush 全 result0；物理读回 PNG（runs/ap90r2parent-f5c66d0b/osd-frame-000420-format0-RGBA-opaque.png）Lead 目视确认：原厂字体日文「メモリーカードが正しく読めません／メモリーカードを入れ直してください／スロット1」。下一步 AP91：按 audits/key-input 原协议注入按键，关闭对话框并尝试 MENU。
- 2026-11-02 AP91-r2：合成按键 6 步 12 事件全部被原厂输入层接收（I-InputRecv/内部 28B/EventThread），无 unknown key；画面仍为槽 1 读卡警告。Lead 判断：VM 无卡却报"读取错误"→ 卡检测被读为已插入；应提供诚实"未插卡"状态。→ audits/media-slot-dialog（插卡检测/挂载错误来源 + 对话框按键退出条件）。
- 2026-11-02 media-slot 审计（部分）：按键已进入应用回调（16f0fc0→5503e0，inh0）；卡检测在 libInfraMediaDetect（FRONT RMDATA/RM 80d9016e/MediaMount），NotifyInOutEvent status 1=插入 0=移出；AP90 原厂确实收到两次插入事件并做了挂载，物理判定源未证实。AP92 = 纯被动观测轮（README 第6节第1-2、4项）。
- 2026-11-02 AP92 定论：卡"插入"来自原厂超时兜底——RM helper 返回 0x80000004（无 RM 队列 80d9016e），ThreadInit 等待 110 超时→默认初始化→StartInOut 发 status0→status1；MediaCommon 路径 /nondev/rm3、/nondev/rm2，mcmn_drv_open 返回 0x80000004，Mount→0x7fffffff→MOUNT_ERR 警告。Lead 决策：提供诚实的 RM 介质状态服务（双槽无卡），消除兜底分支 → audits/rm-media-service。
- 2026-11-02 RM 审计：0x80d9016e 由 AP 内核 mcmn_drv.ko 注册（会访问真实硬件，不加载）；CP 经 0x8028017c 发 7B FRONT，内核缓存并在 cmd3 注册时回放。Lead 决策（AP93）：软件 RM provider 仅实现 cmd9（112B 原配置投影）+ cmd3（注册通知并回放 synthetic 空槽 7B 02000007000000，source=通知目的 ID），其他命令按原 0x80000003 拒绝；marker synthetic_empty_slot_provider=1 original_CP=0；不伪造挂载。随后观察 NO CARD 画面并注入 MENU。
- 2026-11-02 **AP93-r2 里程碑**：软件 RM 空槽 provider 生效（cmd9/cmd3/7B 回放均消费，D 两媒体 state2 仅 status0，无 Mount/MOUNT_ERR）。画面为原厂首次开机语言选择页（runs/ap93r2empty-77c94f2c/ap93-phaseA-before-MENU.png，Lead 目视确认）。MENU 在该页无响应（符合首次设置流程）。AP93-r3：语言页导航（下/上/确定）→ 首次设置页依次确定 → 拍摄待机 → MENU。
- 2026-11-02 **AP93-r5 交互证据**：下键→标题变「Langue」，上键→「言語」（Lead 目视：光标在语言列表间移动，初始在日本語；高亮条本身未见，疑在另一合成层）。确定→ scr7248_0001，新页在 Heap2 资源子块做离屏绘制：FillRect dst 4109364c0 32x29、BitBlit flags0 29x29 dst 410936c80/src 4109364c0 被拒。→ audits/offscreen-subblock。下轮语言选择改为：上(3)→English→确定。
- 2026-11-02 离屏子块审计：BitmapImpl::create f14fc→102560→103550 分配 Heap2 子块；seq217 = c878 StretchRotateBlit 29→116 四倍缩放，reg760=0 关闭混合 → v19 用 nearest 覆写（approx_stretch=nearest_v1, approx_blend=0）；目标准入 = 已登记父资源 extent 区间 + 活跃 malloc 子块记录。compaction 独立移动链（150c04…f0a98）不覆盖，检测并标注。
- 2026-11-02 **AP94-r2**：上→English（标题 Language）→确定→英文生物特征隐私说明页（含 QR 与 sony.net 链接）→确定→Creators App 引导→Connect Smartphone/Bluetooth On 页（Lead 目视确认，runs/ap94r2diag-4f9de767/ap93-step-0{1..4}-*.png）。停于 flags0 49x49→103x116 非等比缩放；Lead 批准 nearest_v2（任意正比例，center 采样，覆写）。
- 2026-11-02 AP94-r3：偶发 GPE_STALE 根因 = screen_recheck 解析 /proc/udm/dmm_extents 时 code3 重复 ID（与 AP_SNAPSHOT 同时读表，疑 procfs 非原子读），父对象 112B 复核通过。Lead 决策 v19r4：原对象字段复核为权威，procfs 不一致时有界重读后以对象复核为准（marker object_authoritative），快照与绘制读表串行化。
- 2026-11-02 AP94-r4：procfs 对象权威修正后，首次设置走到 Install Creators App QR 页；ENTER 不推进，MENU 返回到"可用手机进行初始设置"页（底部 删除键→Set on the camera）。Lead：派 audits/key-delete-c4；AP95 改为宿主逐步放行输入计划 v2（工人每步看 PNG 自选白名单键，≤30 步）。
- 2026-11-02 删除/C4 键审计：UI 0x23 → Infra 0x1f8，down20 f801000000000000010000000000000001000000 / up status0；另 C1 0x66、C2 0x70e7、C3 0x70ec、PLAY 0x1f7、FN 0x7095。Lead 批准将 DELETE(0x1f8) 加入 AP95 白名单（其余新键暂不开放）。
- 2026-11-02 运行链工人（ctx_ee4f6943c8d7）因累积长历史反复触发服务端内容过滤，已 abandon（对话保留）；以 lead-claude/RUNTIME-HANDOFF.md 新起运行链工人执行 AP95。
- 2026-11-02 **AP95**：删除键→Set Area/Date/Time，12 步走完首次设置（地区/日期格式/日期时间/高温提示/HOME 引导/Creators App 说明），原厂开屏 screen0；保存 backup-after-setup.bin（SHA 191924ef…）。两轮复现：第 13 步 MENU 写入控制区后 guest 按钮 worker 不再执行。AP96：用 backup-after-setup 回放直接开机到设置完成状态 + 按钮 worker 门控诊断 + MENU。
- 2026-11-02 AP96：Backup 回放后仍进首次语言页（完成标记不在 Backup RAM → audits/first-setup-persistence）。按钮 worker 停滞根因：首次设置退出到 screen0 后 im.elf THREAD_INFRA1(tid327) State T / do_signal_stop，之前大量 UIPC -1021/-1022 → audits/thread-stop-standby。
- 2026-11-02 **根因更正**：AP95/AP96 线程停止 = 原 assert（infra_wrapper_bb.cpp:870 → lib_assert → SIGABRT → 停止），起因为首次设置结束后再次发出同一 VDF 0x119 enum2 28B，而面板 consumer 只接受一次。先前"guest 健康"判断撤回（仅生命周期通过）。AP97：面板 consumer v2 幂等处理重复 enum2；健康判定加入 assert/Assertion/exception monitor/signal6 全文检索。
- 2026-11-02 持久化审计：回放生效（语言 English、UUD 4/4），重复首次设置因 force1098（02cf0014/01070140）仍为 1；原厂仅在日期事务 2d7e6f4 返回 0 后清零并经 type5 daemon Backup_write。下一轮观测日期事务返回与日期服务 0x80900141 原字节。线程停止审计：lib_assert→abort→do_coredump→stop_all_threads_timeout→SIGSTOP。
- 2026-11-02 **AP97 里程碑**：面板 v2 幂等后无 assert，首次设置完成进入**原厂拍摄待机 OSD**（HD 59.94p / ±0.0 / ---，Lead 目视 runs/ap97v1panelrepeat-8003227c/ap97-standby-before-menu.png）。MENU 触发原菜单绘制，被拒为常量 alpha K128(fmt2)/K65(fmt0) 混合。Lead 批准 straight_over_v1 扩展到 K∈[0,255]（近似标注）。
- 2026-11-02 **原厂菜单首次可见**：AP97 MENU 后最终帧（runtime/ap97v1panelrepeat-8003227c-final-frame/registered-frame.png，Lead 目视）：Main > Rec Frame Rate 2/59、Main1、59.94p、ISO100、PP11、底栏 Page / 删除? / MENU Close；半透明底块/选框缺失（对应被拒 K128/K65 混合）。
- 2026-11-02 **AP97-r2 菜单交互里程碑**：K128/K65 常量 alpha 近似放行后 MENU 页正常（step11），DOWN 后标题变 "Main > Main1 > Av Auto/Manual Switch" 并绘出主菜单瓦片网格（step12，Lead 目视 runs/ap97r2alpha600-cd3c48f7/ap97r2-step-1{1,2}-*.png）。首次设置日期成功路径未出现、force 仍 1 → 需日期服务审计。
- 2026-11-02 **菜单导航验收（AP97-r2）**：DOWN→Av Auto/Manual Switch，DOWN→White Balance，RIGHT→Picture Profile，ENTER→Picture Profile 子页（PP11 橙色选中，MENU Cancel / ● OK）。15 步按键全部原生收发，常量 alpha 近似混合无拒绝。Lead 目视 step11..15 PNG。
## 剩余事项
1. 首次设置日期事务未成功（force1098 仍 1）→ 每次开机重走首次设置；需审计日期服务 set（0x80900141 等）并修复，之后保存 Backup 回放直接开机到待机。
2. 主菜单瓦片图标/选中高亮缺失（原因待查：未支持绘制格式或依赖实时状态）。
3. 无实时取景（无传感器），拍摄待机信息精简。
4. 运行健康判定已加入 assert/Assertion/exception monitor/signal6 全文检索。
- 2026-11-02 日期审计 + AP98 抓包：语言页阶段 SeqQueueCommon 已发 80900141（32B，2021-01-01）→ 内核 udate_set_date → 向 CP 909005c5 分发 44B type1 → timeout=-1 等 type4，CP 缺失 → 永久阻塞 Common 队列；首次设置 UI 日期任务 sequence_clock::date_time_initial_setting(2b725c8) 因此从未执行，force1098 不清零。Lead 决策 AP99：在唯一 public owner 内实现 CP 日期分发 consumer：type1 → 向 source 发 type2 取钟（日期 16B+10/时区 8B+20）→ 更新软件 CP 时钟 → 以 source 909005c5 回 type4（reason 原样）；不直接回 80900141 成功。
- 2026-11-02 **AP99 日期链修复生效**：CP 日期分发 consumer（type1→type2 取钟→软件 CP 时钟→type4）使语言页起的 80900141 sync 返回 0，boot force 路径两次 Backup_write 返回 1；Backup_nread 观测 ABI 已修。新阻塞：Common 队列解除后发 VDF 0x146（10B 0d2046010a0001800100）同步等待，首帧前停住 → audits/vdf0146-common-tail。
- 2026-11-02 首绘新门（B 强）：AppFw 等 model_setting_value::sync_and_wait_comp 条件变量；AppBackupDaemon 卡 backup_get_cp_data→Backup_sync_all→osal_rcv_msg_tmo（CP Backup 同步取数未实现）。0x146 = sequence_set_touch_panel，回 0d2046110c00018000005900。→ audits/backup-sync-cp。AP100 = 0x146 + CP Backup sync。
- 2026-11-02 Backup sync 审计：backup_get_cp_data = op30(3,1) 锁（40B，+18 scalar1/+1c pointer1，回 4096B，CP 置 SuspendComp）→ pcidma_transfer_async 把 CP bank 拷到 AP 第二 bank → 原 backupfile_cb_getcp(.text+5e30) 释放 30s sem → op30(0,1) 解锁 → Backup_sync_all 显式 backupfile_save(1) 写 /setting/Backup.bin。VM 中 pcidma init 被禁用。Lead 决策 AP100：0x146 回复 + CP Backup op30 锁/解锁 + 对精确 DMA descriptor 的真实复制并调用原回调（不伪造数据，返回值不作验收依据）。
- 2026-11-02 **AP100 持久化打通**：0x146 + CP Backup op30/DMA 真实复制后首绘恢复；首次设置日期页 OK → 80900141 返回 0 → force 两键原 Backup_write 写 0（读回 0）→ Backup_sync_all → 原厂写出 /setting/Backup.bin（gen7 SHA 552fd5f8…，AP/CP 段原 checksum 吻合，force 字节 0）；待机 + MENU（葡语界面，因列表高亮不可见误选语言）。AP101：以原厂写出的 Backup.bin 替换 CPIO 种子，由原模块加载，验证直接开机到待机。
- 2026-11-02 **AP101-r2 持久化闭环**：以原厂写出的 Backup.bin（gen7）替换 CPIO 种子，原 backup 模块加载（AP/CP 段逐字一致），零按键直接进入拍摄待机（开屏 2ae→2e1→2dd→0，无首次设置）。CP 模型初始 pin 跟随原 loader 实际加载内容（Lead 批准）。
- 2026-11-02 **AP101-r4**：v8（P74 平铺 repeat_mask_v1 + 屏外空 clip no-op）后菜单导航到 Setup > Area/Date > Language 并改为 English（Lead 目视 ap101-step-10）。已知缺口：右侧内容面板不透明底色缺失导致左栏文字与右栏叠印。改语言后 450s 内无新 Backup.bin 代次 → 不直接调 Backup_sync_all；audits/backup-save-trigger 查普通设置保存时机（定时/关机等）。
- 2026-11-02 保存触发审计：普通设置（语言 type8）写 RAM 后，daemon 空闲 2s 走 Backup_sync_subsystem(2cf)（DMM 临时区合并保存，无 op30）；全量 Backup_sync_all 仅 boot/clock 请求位；shutdown 槽 backupfile_save(0) 与 suspend op35 分离。AP102：被动观测空闲局部 save 路径（入口/DMM 临时区/返回/文件代次），菜单改语言后等待 ≥30s；若未落盘，再用菜单 Area/Date/Time Setting 重新确认日期（AP100 已验证的全量同步路径）作对照，观察语言是否随全量 save 落盘。
- 2026-11-02 用户要求试用 → TRY1 优先于 AP102：本机网页试用工具（实时 OSD 帧 + 7 个原协议按钮 + 安全收尾），说明放 outputs/fx3-vm-trial/README.md。
- 2026-11-02 TRY1 交付（outputs/fx3-vm-trial/README.md，run_trial.py → 127.0.0.1:8765）。用户：先继续完善 → 恢复 AP102（保存诊断，附菜单 GPE/层统计）+ 新审计 audits/menu-highlight-layers（高亮/底色/图标缺失）。
- 2026-11-02 **菜单缺失根因（A 级运行数据）**：AP102 v3 纹理直方图——高亮九宫格/面板/图标等 Heap/Heap2 纹理四通道全 0，仅 TextHeap 文字有内容 → UI 图像资源未解码填充 → audits/ui-image-resource-load。保存诊断：空闲局部保存链在首次设置阶段正常（DMM 1a3917 4MiB 成功、局部 save 返回 0）。AP102 v3 在语言列表弹窗触发 adapter GPE_BUSY（观测锁内哈希副作用）→ 锁外计算 + 有界等待。
- 2026-11-02 UI 图像审计：9 份 uxd 共 51,642 条 encoding4 记录经 /dev/ldec 硬件 LZ77（ldec.ko 32B ioctl、DMA330/IRQ 同步完成）；image.uxb 831 条 PNG 走软件 libpng。VM 无 /dev/ldec → 解码失败 → 纹理全零。LZ77 位流 token 规则未证实 → impl/ldec-lz77（格式破解 + 软件解码器）。delivery 失败独立：alloc_msg for unfetched dynamic queue 808261c0。
- 2026-11-02 **LDEC 格式破解完成**（impl/ldec-lz77）：f0 块 LSB-first 标志、BE12 距离、长度表 3..16/32/64、距 0 终止、0f raw 块；51,642/51,642 精确，Python/C 一致（Lead 复跑通过）；佐证 Sony 公开 lib/lz77/lz77_inflate.c、fwtool、A7C2 sony-lz77.c。样图可辨 3D/S&Q/222M 422 10bit/选框/九宫格。
- Lead 决策 AP103：新内核模块软件 /dev/ldec，按原 ldec.ko 32B ioctl ABI 同步解码（不加载需 DMA330/IRQ 的原 ldec.ko），marker synthetic_ldec=1；之后高亮/图标可见再做日期确认与开关保存诊断。
- 2026-11-02 **AP103 里程碑**：软件 /dev/ldec（fx3-ldec-soft103，原 32B ioctl ABI）接入后菜单与待机完整还原（Lead 目视 runs/ap103r2ldec600-a7c9c32d/ap102-menu-settled.png 与 ap102-phaseA-before-SETUP.png）：左侧彩色分类图标、橙色选中高亮、灰色面板/分隔线、M/ISO/AWB/PP11/XAVC S/Assist/Px 等图标；待机 OSD 含橙色 NO CARD、AF-C、D-R OFF、测光、NFC 等。叠印问题消失。
- 2026-11-02 AP103 四轮均未完成 600s：主阻塞 = alloc_msg for unfetched dynamic queue 808261c0（grm_gpe 完成队列）→ SendDrawComp errno1018。Lead 假设：软件 GPE 同步立即完成早于发起方首次 fetch → audits/gpe-completion-unfetched。第四轮 API16 还原读回失败另查。
- 2026-11-02 unfetched 审计：首次 rcv 假设被原码否定（owner 在 osal_dynamic_id 领取时已写，完成释放时清零）；Flush437 投递时 owner=0。新假设：适配层重复投递同一动态完成队列 → AP104 逐代被动观测（API16 修复后）。
- 2026-11-02 AP104-light-r4：无断点轻量观测，健康 600s，9 键走到语言弹窗无 unfetched（重型观测轮出现、轻量轮未出现 → 观测扰动假设，待第二轮佐证）。接入问题：轻量包装置于 preload 首位破坏 capid outermost caller guard（同 AP85），移至末尾修复。下一轮合并保存诊断。
- 2026-11-02 **unfetched 根因（A 级运行时间线）**：原 libgpe ReceiveDrawComp 接收超时 5000ms（d798），超时后 a41c 释放动态队列；语言弹窗时软件 GPE 完成投递晚于释放 44.7s → alloc -1018 unfetched。非重复投递、非观测扰动（轻量轮复现）。Lead 决策：不改原超时，优化软件 GPE 性能（impl/gpe-perf → backend v9，像素逐字节同 v8）；运行链给出逐命令耗时分解。
- 2026-11-03 GPE v9 backend + v26-perf adapter（impl/gpe-perf，SO SHA 30667f76…）Lead 复跑通过：2,470,763,765 字节与 v8 逐字节一致，ASan/UBSan 通过；宿主加速 backend 2.4–227x、adapter 小命令 237–898x。callback 地址缓存默认关闭。待用户试用结束后由运行链集成（AP105：AP103-r2 + v26-perf，验证语言弹窗 5000ms 内完成、unfetched 消失，再做保存诊断，然后 TRY2）。
