# AP81健康首清屏与option6的IMAGING pin等待

**SKD异常已有诚实降级并通过240秒健康运行，当前新缺口是IMAGING拓扑的三条连接。** AP81原SKD CipherInit两次返回−1020，data_encryption两次写status2后自然返回，认证sequence也返回；原UI timer恢复，实际GPE FillRect/Flush和已保存物理读回均存在，但只得到均匀黑清屏，没有菜单内容或输入闭环。后续原mode-transition选中`9ab2518`，option6分支由入口寄存器与原数据流绑定，等待发往 **90050004** 的GET。依据：serial2112、23299–23310、26428、26340/26378、23353–23373；以下给出完整字段与原VA。

本续查仅写本目录，不改原件/runtime/STATE，不拿运行锁，不启动QEMU或读取实时guest内存。所有guest事实来自既有`runtime/runs/ap81skd-b9850378/`。新增[audit_ap81_pin.py](audit_ap81_pin.py)重建[ap81-pin-proof.json](ap81-pin-proof.json)，并保留[AP80c尾段历史](BOOT-TAIL.md)和原[四任务屏障审计](README.md)。serial行号按LF计，保留NUL。

## 1. AP81已经完成和仍未完成的事

原receipt记录241.22秒、qemu_exit0、process_reaped/inputs_unchanged=true、guest_exception_markers=[]；独立review记录missing_markers=[]、末次im maps存在、fatal=[]。本脚本读回并核对两份文件身份，没有将单独的QEMU退出值作为guest健康判据。

| 事件 | 原serial行 | 限定结论 |
|---|---|---|
| 精确SKD硬件不可用 | 2112 | 仅SKD+645ec的`/dev/mem` mmap ffffb000/1000/prot1/flags1返回MAP_FAILED/ENODEV，无假ROM/密钥 |
| CipherInit原失败 | 23299、23306 | original_result=−1020，forced_success=0 |
| 加密API正常错误收尾 | 23301/23303、23308/23310 | status2，原ret2eaa0d8；不是加密成功 |
| 原认证sequence返回 | 26428 | 原ret2bcc544；不等于认证功能验收 |
| 原首清屏 | 26340 | FillRect/result0，format0、640×480、dst43feb5100、flagsff |
| 原Flush | 26378 | Flush/result0；不把它当像素地址或菜单发布完成 |

SKD语义原件已由相邻[SKD审计](../skd-ffffb000/README.md)通过原WBI页表恢复绑定：同库磁盘受保护字节不能直接解码的缺口已被原快照代码补齐；读ROM取数垫的`ldrb`为S+63fc0，初始化映射失败有原返回路径。Lead选择了硬件不可用方案，没有采用跨机参考ROM；本报告只确认AP81实际非致命路径（原AP`2eaa0a4/2eaa0c0/2bcc544`、上述serial）。

沿用尾段解析器独立读AP81，0119应用/消费、真实handle4完成和单await正常匹配、同event原notify、AppFw wait返回done1、外层285e430继续六项均成立，保存在proof `AP81_boot_continuation`。`run_i`为void，现场x0=0仍不当定义的业务状态。新等待已经是 `sequence_mode_transition::enter_face_all_deletion_mode_proc()` 调用的pin拓扑链，不是boot四任务仍未完成（原`2d11dd4..1e4c`，serial23359–23372）。

物理首读回`osd-first-draw.raw`为 **1228800个00字节**，SHA256=`3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c`。两种候选格式解释均导出相同的640×480黑色PNG，SHA256=`4eb57253605c71963d1c5dc42c4bfc2f7f5af572846c270ea6e316045daf52bd`；本轮已查看现有图。均匀黑面不能区分format0/1、通道或alpha规则，不证明物理scanout/多plane、更不是菜单截图（原`osd-first-draw.json`的假设和menu_acceptance=false）。

## 2. 第二次选择的是option6，不能写成实际mode2

AP81 module base B=`7f4815f000`。23353记录第二次 `selected=7f51c11518`、`current=7f51c0fd70`、flags0；归一化为 **selected9ab2518/current9ab0d70**。第一次21612为9ab1258/flags1。两个50行selected与current表均从保存RAM重取，全部200行的指针归一化和其余字节与原构造/原成功更新规则一致，不只比较串口显示的3行。

RAM=`ui-gate-counters.bin`，SHA256=`004271eb3a947fab3a059e5f3d29019493381133605939925e8aca25dc9c2d88`，与原receipt只读快照一致。第0/1捕获在文件8000/8a00，各有64B头、1200B selected、1200B current；当前表中11个旧连接已由前次原调用更新，不能再以冷启动全断开表替代。

表9ab2518单靠地址可以由mode2/option0或option4/6选中，地址本身不够判断实际输入。**但23357在原`2ebe188`入口捕获x4=6**：

1. `2ebeae8`读取`w4=input.option`。
2. `39a4708+6`的signed jump byte落到`2ebec6c`。
3. `2ebec6c..78`只设置x0=9ab2518/w1=0，跳到`2ebeb3c`；在入口探针前没有w4改写或另一调用。

因此此轮实际为 **system_mode_option=6**，不是由表名反推“system_mode=2”。完整第二次24B输入及其他mode/proxy/remote/network/stream字段仍未捕获，不能拿第一次21610的24B输入倒填。父原函数名确为enter_face_all_deletion_mode_proc（字符串3937400、`2d11df8`），这和option6原路径相符，不构成对完整模型参数的补读。

## 3. 精确新增三边、六端点

原静态构造器`1694028..1697260`已有三条IMAGING source；在初始9ab1258中状态2表示“不要求”。新9ab2518使row1/4/5变为状态1并给出目的，其他11条连接不变：

| row | source `[owner,type,dir,index]` | destination | 原descriptor VA |
|---:|---|---|---|
| 1 | `[90050004,0,2,1]` IMAGING YC OUT1 | `[9284074a,0,1,1]` BB YC IN1 | `9ab3fd8 → 9ab3f98` |
| 4 | `[90050004,8,2,0]` IMAGING RAW OUT0 | `[9284074a,8,1,0]` BB RAW IN0 | `9ab4088 → 9ab4008` |
| 5 | `[90050004,3,2,0]` IMAGING SYSND OUT0 | `[9058003f,3,1,0]` ADF SYSND IN0 | `9ab4118 → 9ab39c8` |

owner为hex，小字段十进制；type0=YC、8=RAW、3=SYSND，direction2=OUT、1=IN。名称由原`4117648`表与构造记录对应，完整写入VA保存在proof `new_rows`。新集合为 **28端点、9 owner、14允许边**，在原22端点/11边上增加6/3；三条source与三个新的consumer key均不在旧22个key中。

原拓扑函数先检查旧连接是否需要断开；本次已有11边未改、三个新source旧state0，无需disconnect（`2ebe290..314`）。flags0选`2ebe50c`路径，只对目的指针变化的行连接，保持旧11边；每个新边执行GET源→GET目的→REQUEST_CONNECT（`2ebe58c..5e8`、`2e1117c/2e112a4/2e11390`）。在三条控制连接都成功且无并发变化时，条件投影为 **9包**。AP81只捕获第1个GET，余8包不能标作已发或已消费。

## 4. 90050004的原CP处理与回复格式

CP `3c6a00`管理循环以90050004无限接收（`3c6a3c..4a→18f460`），原诊断文件名`deba12`为`InfraImaging.cpp`。其pin指针表 **f15380**有6个对象，指向13ad6cc起每38hex字节一个对象；原初始化`9b5114..51da`分别调用`5ba9ac`，模板 **f15320..f15370** 按CP的`[type,dir,index,owner]`顺序提供：YC OUT0/1/2/3、SYSND OUT0、RAW OUT0。当前软件合同只需其中OUT1/SYSND/RAW三个，不能因原CP有六个就自动开放全部。

GET `3c6c1e`构造业务`1000/8000/32/flags2`；`3c6c4a..78`逐完整type/direction/index查6个对象。成功`3c6eb0`取self与状态，`3c6ee6`置status0；找不到返回−32（`3c6c84`）。公共构造器`5ba9ac`将CP pin state初始化为1=断开，运行中当前值尚无原CP执行证据；虚拟后端也必须从自己的真实登记状态读取，不能把state0当“默认成功”。

| 业务偏移 | GET8000/32B |
|---:|---|
| 0..7 | LE16 `1000/8000/32/2` |
| 8/12/16 | self.type / direction / index，u32 |
| 20 | CP connection_state：0已连、1断开、2转换中 |
| 24 | owner=`90050004` |
| 28 | signed status，成功0 |

90050004的GET还明确调用 **`3c6f0e→5ba598` 设置外层reply-id为90050004**，`3c6f1c→5ba5e6`设置metadata source为90050004，再按原请求回复路线发送。当前旧模型只把9284074a/9080003b列入这种外层策略；扩容时必须加本provider，不能复用其他GET的outer+0=0。

本次首个request为精确48B、source=`81cf61c2`（23358）：

```text
c261cf81a0a0a0a001003000180000003000000000000000001000001800020000000000020000000100000000000000
```

在软件对象确实已登记、当前断开state1时，完整56B软件回复为：

```text
04000590a0a0a0a0010038001800000038000000000000000010008020000200000000000200000001000000010000000400059000000000
```

metadata source=90050004，**发送目的取该次请求动态source/outer+0＝81cf61c2**；回复自己的outer+0=90050004不是发送目的。它只报告已登记软件对象与当前断开状态，不创建连接、frame、DMM handle或buffer。

REQUEST_CONNECT原CP在`3c6d84→5ba9f4`开始公共100/8100握手，内部完成由`3c7012→5badd0`生成8001，不能收包即成功。软件后端须真正提交双端peer/state/generation和空软件队列，满足当前所有权/引用后才回8001；不必也不能冒称原传感器帧已产生。32B完成字段沿用[原pin合同](../pin-topology/README.md)：+8/+12/+16为type/dir/index，+20为owner，+24为signed status，+28保留0；通用8001外层reply-id为0，与GET的90050004策略不同。

## 5. 九包条件合同与最小集成范围

全部业务请求、32B回复与56B封套已在proof `conditional_nine_packet_contract`逐包列出；下面只列有助于审阅的顺序：

| # | row | 操作 | 目的owner / key |
|---:|---:|---|---|
| 1 | 1 | GET源（本次已捕获） | 90050004 / YC OUT1 |
| 2 | 1 | GET目的 | 9284074a / YC IN1 |
| 3 | 1 | REQUEST_CONNECT | 90050004 / YC OUT1→BB YC IN1 |
| 4 | 4 | GET源 | 90050004 / RAW OUT0 |
| 5 | 4 | GET目的 | 9284074a / RAW IN0 |
| 6 | 4 | REQUEST_CONNECT | 90050004 / RAW OUT0→BB RAW IN0 |
| 7 | 5 | GET源 | 90050004 / SYSND OUT0 |
| 8 | 5 | GET目的 | 9058003f / SYSND IN0 |
| 9 | 5 | REQUEST_CONNECT | 90050004 / SYSND OUT0→ADF SYSND IN0 |

**为什么AP81没有回复：** 当前部署`fx3-capid-v36.c:537`在进入pin_dispatch之前要求`pg_owner(dst)`；`fx3-pin-core-v1.c`的22个key没有90050004。因而该请求原样委派，23373原内核报告“No snd_msg registered…0x4”，没有90050004的PIN_COMMIT。当前等待由缺失软件服务/白名单解释，不能归因于SKD仍崩溃或四任务未完成。

仅改一处owner判定还不够，最小完整变化需要：

- 在明确profile下追加上述6个完整key和3个允许edge；保留旧22个key/11条edge的编号、peer/generation与lease语义。若新进程统一初始化28个对象，所有对象初始断开，旧33包仍按原流程提交，新增6个对象等后续请求。
- 将硬编码22/11的数组、遍历、peer范围、resource/queue/buffer边界与QMP decoder一并按版本更新；不能只扩数组或对未知key回echo成功。
- GET的outer-reply-id策略加入90050004；保留metadata source=provider、reply目的=当前活跃请求source。每条edge的动态source生命周期继续由原代码管理，后8包不能写死81cf61c2。
- 新对象state1/peer空/generation1、空队列、无已注册buffer、pending_hardware1；CONNECT在本地双端逻辑图实际提交后才成功，维持原sender/generation/refs/重复free校验与分配/发送失败回滚。不补1004、worker token或硬件帧。
- 独立运行验收预期是新增9条回复均原接收free0、总queries28/connections14/pin_serial42、没有未归还引用；这些是条件预期，不能拿本审计Python通过替代。随后还要重新观察新的服务请求和菜单绘制。

本次没有集成或运行这项扩展；没有恢复imaging/RAW/YC/SYSND producer、DMA或原CP。更后面的start/queue/buffer请求若出现，必须单独建立完成语义，不能由本次GET/逻辑连接白名单自动授予成功。

## 复现与未证实项

项目根执行：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/boot-barrier-remaining/audit_ap81_pin.py
```

退出0重建proof：固定原AP/CP哈希、24处原指令、两种寄存器种子下的原构造结果、两次selected/current全部200行RAM字节、option6实际入口数据流、6个CP对象、28key/14edge和9包精确条件合同，同时核对AP81健康、原boot完成、SKD真实失败返回与全零首清屏。脚本没有启动guest或执行Sony函数。

仍未证实：第二次24B输入中除option6外的字段；后8包实际发送/扩展回复消费；新软件图的运行实现、硬件producer与下游资源完成；非均匀菜单帧、格式/scanout、原TP消费以及输入导致新帧。工具API/ABI沿用既有官方依据；私有服务、地址、对象和协议全部以本地原VA及已有回执为准。
