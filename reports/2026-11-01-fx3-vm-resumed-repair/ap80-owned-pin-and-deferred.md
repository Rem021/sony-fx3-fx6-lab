# AP80 软件引脚图与启动尾段

AP80a已越过原四任务屏障；菜单尚未恢复。240秒运行`ap80apins-d8b39ab6`：qemu_exit=0、process_reaped=true、inputs_unchanged=true、missing_markers=[]，末次/proc maps含im.elf，无符号查找错误/新增致命路径，两锁释放已独立重取核验。

## AP80a：真实软件图状态

在capid v32基础生成v33，只支持FX3原表9ab1258的8个owner、22个完整canonical endpoint和11条允许连接。GET读取当前图，连接提交双方peer/state/generation及空队列；未知key/方向/类型、占用或未结束lease均拒绝，断开受队列和资源引用约束。注册没有产生硬件帧；当前所有pin pending_hardware=1。

原应用实际发送22 GET+11 CONNECT，共33条56B规范回复均由原接收端free(result=0)。Dataflow外封套padding实际可含栈残值，仅记录不参与匹配，回复清零；源队列绑定本次动态source。独立QMP在原屏障入口复制图：ready1/fault0、serial33、queries22、connections11，22个endpoint均state0、generation2且peer互为对应，reply_refs/resource_refs=0；11对队列active1/capacity4/count0，所有handle0；16个buffer槽均未注册。它证明控制图与空队列，不证明GPE帧已流动。

四业务任务自然完成各一次且完成函数均返回0；原屏障2b6353c入口一次，实际匹配token顺序1/3/2/0，remaining为3/2/1/0，原屏障正常返回0。未补token、notify、1004或GPE。

宿主ASan/UBSan覆盖33条原审计金样、连接后GET、错误key/方向/类型、畸形封套、重复与陈旧lease、外国PID/线程、分配/发送失败回滚、buffer域/owner/generation/队列引用与断开限制，以及8线程24000次锁保护。buffer模型仅宿主验证，guest本轮未注册或转交buffer；仅545域OSD owner可注册，拒绝复用失效generation。

后续原线程到达0328：目的92840747、当前source81cf61c0、完整10B `0d2028030a0001800300`。栈appFw+2dee79c→2dd1040→2b67aa4→2b68374；本轮不新增该回复。UI仍等boot事件；timer生产继续而消费1，GPE_CMD=0，无成功绘制可读回，故没有PNG。

[AP80a完整回执及0x11a后请求时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80a-review.json)；[QMP图与原表副本](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80a-gate-readback.json)；[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80a-owned-pin-graph/candidate80a.json)；[宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/pin-transport-host-check.json)。

## 后续阶段

AP80b1按已审计合同仅实现实际path3的静音sink逻辑保存，成功完成回1328/status580000；仍不允许播放。digital与0119继续先抓实际全包/enum，再逐步实现与单独240秒验证。A7C2第一方pin registry及端点生命周期研究仅参考设计，22端点/11连接均由本机FX3原件和运行包核对：[联网研究](../../work/fx3-vm-20261101/lead-claude/research/a7c2-latest/README.md)。

## AP80b1：静音path3完成

240秒`ap80b1path-d244a966`，qemu_exit0/reaped/unchanged/missing[]/im末存活/无fatal，两锁重取核验。原四任务屏障仍正常；v34接受实际10B path3，保存静音sink状态后回`0d2028130c00018000005800`，lease106原应用free0。没有声音/播放/DMA。后续实际digital目的912f0335、24B `030000000000000000000000000000000000000000000000`，source81cf61c0；本轮仅捕获，未回复。

[v34 ASan/UBSan](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/sound-path-host-check.json)；[完整回执/时间线/栈](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80b1-review.json)；[digital原包冻结](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80b1-digital-capture.json)。GPE仍0，无PNG。

## AP80b2：digital完成，真实方向为enum2

240秒`ap80b2digital-bd9672cf`，qemu_exit0/process_reaped/inputs_unchanged/missing_markers=[]/im末次maps存活，无新增symbol lookup/fatal，两锁释放后已重取核验。v35只接受已捕获op3精确24B，建立service_state2/sensor_enabled=false，保存notify_requested=true，samples_emitted=0。独立24B原op3/status0回复以912f0335为metadata source，回本次动态source81cf61c0，lease107原应用free0；不利用AP漏读回复状态的缺陷冒称成功。宿主ASan/UBSan已测全24字节负例、长度、非法source、服务未ready/启用sensor拒绝、PID、单lease及分配/发送失败回滚。

原33条pin及path3仍全部free0，四任务屏障仍正常；但boot没有返回/通知目标future。panel worker TID324在2b5fc68（原wrapper之前）读sequence+304，**实际enum=2**，完整28B为`0d2019011c0001800101000000000000000000000000000000000000`，对应hrev1/vrev1/osdRev0。只捕获不回复，enum0的软件consumer草稿未集成进任何候选；不得称identity已运行、panel reverse成功或最终boot完成。已escalation，Lead派audits/panel-reverse-enum2核对plane/scanout/input及原成功层级，指示收尾后待合同再做AP80c。

旁支libObj+c7508→cb900的TID219同步40B到80924127原样记录；封套声明56而msg_size40/sourcea5a5a5a5，不把它解释为规范endpoint请求或有效1004。没有拦截该目的或增加回复，完整raw/栈均保留。

|GPE统计|值|
|---|---:|
|FX3_GPE_CMD total|0|
|op/fmt/flags/地址545/result分组|无命令，空表|
|result0绘制物理读回|无可触发绘制|
|PNG|未生成|

旧UIPC统计有去重/写文件观察限制；完整请求时间线指捕获到的0x11a后请求/栈序列，不是全系统无损追踪。gate mirror_skip=0、boot记录overflow=0；QMP图只在原四任务屏障入口复制，与后续面板状态分开。

[完整回执/请求时间线/新命令计数](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80b2-review.json)；[gate读回含enum2](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80b2-gate-readback.json)；[实际方向全包和栈](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80b2-orientation-capture.json)；[v35宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/digital-host-check.json)；[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80b2-digital-notify/candidate80b2.json)。

## AP80c：启动链与notify成立，SKD总线异常导致本轮失败

**本轮失败，不能作为240秒健康/菜单验收。** `ap80cpanel-5dd371e5`原计划240秒，发现新增external abort后发SIGTERM给observer，按既有finally回收QEMU，实际105.13秒。qemu_exit=0、process_reaped=true、inputs_unchanged=true、宿主PID已不存在、两锁已独立重取；observer明确记录`KeyboardInterrupt('Observer received signal 15')`。missing_markers为`FX3_TIMER_OBSERVER_END`、`FX3_UIPC_OBSERVER_END`。最终QMP/RAM快照未生成；异常监视器保留原im.elf任务/maps不等于健康主进程存活，不能关闭末尾存活门槛。既有AP80a/b1/b2三轮clean回执均保留。

### enum2虚拟面板控制

依Lead新审计合同，在v35基础生成v36（覆盖未启用的enum0草稿，旧运行未使用该草稿），只接受实际28B h1/v1/osd0及本次动态source。f02e等价FIFO与独立consumer先安装`control=3/hrev=1/vrev=1/osdRev=0`，从控制状态读回一致、generation1后才分配12B并发送`0d2019110c00018000000000`。本次source81cf61c0、lease108，原接收端自然free(result0)。成功发送才释放原request；失败恢复所有控制/队列/generation状态，回收自身reply并保留caller request，不补token或notify。

ASan/UBSan验证完整28B每字节负例/其他enum拒绝、同线程观测source绑定、独立consumer先于分配/回复、control读回、FIFO/generation、单lease/重复free/外国线程/陈旧租约、分配/发送失败回滚。最初宿主检查把第二次合法generation也写成固定1而失败，已改为断言consumed/readbacks等于实际generation；模型代码未因此放宽。

marker明确`logical_framebuffer_unchanged=1 pixels_flipped=0 panel_control=3 osd_rev=0 tp_axes_reversed=1`。后者是本profile对应原TP false/false方向的说明，另以`tp_native_consumption_unproven=1`保留原TP是否已消费的门槛；没有新增raw触摸或重复反转输入。logical framebuffer导出仍原样，无物理面板安装/最终scanout等价声明。

### 原启动链正向证据

|原路径|本次证据|
|---|---|
|四任务屏障|原任务自然完成后继续，未合成完成句柄|
|panel单任务屏障2b63718|TID327等真实handle4；2b637d4原公共返回路径x0=0，栈中原token4|
|run_i返回|2b68374处原result0|
|2b6838c notify|原调用点41→setter36→cv37，均为同event7f62c2b3e8/cv7f62c2b3f0|
|原UI future|TID289从2aa23a8返回，首次byte_done1；外层285e430返回0|
|UI后续dequeue|未证实；仍仅150000与30072两条，timer消费1|
|176fb4c/1004/GPE/8288076c发布|未出现，GPE_CMD=0，op/fmt/flags/545/result分组为空，无result0绘制可触发PNG|

future返回后旧observer点38仍按TID打印早先event地址，后续byte136属于对象生命周期结束后的无效状态观察，不能用作boot事件再次变化/返回证据。未见fault PC指向该observer；以后应在原future返回后停止绑定旧event，防止悬空被动读取。新gatev9仅加原单屏障入口/公共返回点，48点完整寄存器自检通过；128条boot记录设计不覆盖旧观测区域，但本轮停机未保存QMP二进制，实际只报告serial证据。`FX3_PANEL_CONFIG_QMP_SNAPSHOT`是guest向观测RAM复制marker，不是宿主完成物理读回的凭据。

### 新故障现场

原serial第23334行：`Unhandled fault: synchronous external abort (0x92000010) at 0x0000007fb79b88eb`，随后进入exception monitor，signal7。原异常任务为`im.elf(SeqQueueNetwork)`、TID332；PC7fb6084fc0按原maps减base7fb6021000＝`libInfraSKD.so+63fc0`，LR+64098。访问VA7fb79b88eb所在映射7fb79b8000对应`/dev/mem`物理ffffb000，按偏移推算访问ffffb8eb；这是映射推算，指令/私有设备含义尚未审计。UIPC随后-1021风暴，未补缺失设备、伪造网络/安全状态或继续跑候选。Lead已派`audits/skd-ffffb000`，收尾后等待。

[失败回执/完整捕获请求时间线/原寄存器stack/maps](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80c-review.json)；[原receipt](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap80cpanel-5dd371e5/receipt.json)；[v36宿主ASan/UBSan](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/panel-config-host-check.json)；[候选/构建哈希](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap80c-enum2-panel-config/candidate80c.json)；[enum2审计合同](../../work/fx3-vm-20261101/lead-claude/audits/panel-reverse-enum2/README.md)。
