# FX3 首画面触发与 AP86B 后继队列审计

**已定位可复现的同步缺口：AP86B display v2 在 0400 完成后立即进入 `sequence_sys_set_timecode_run`，发送 SYS0402 并等待回复；后面的 timecode preset、人脸清理和 release-lock 尚未越过这道门。** 0402 可由保存配置的显式软件后端诚实接受，成功回复为 **`0d2002140c00018000000000`**，状态是裸0，不带590000域。第二项 preset 实际是 **0404**，成功回复 **`0d2004140c00018000000000`**，其完整请求四个值尚未采齐。（AP `2dca7fc、2dca864、2df2528..25a0、2dca698、2df2310..235c`；CP `1a8134、1b9146..9178、1ae03c..e09c、1a8190、1b917a..91ac、1ae0c0..e120`；serial **17905–17951**。）

**首屏的高层决策已恢复，但“回完这些请求便一定出现菜单”的因果边尚未闭合。** `scr0039_boot_controller::process_power_on` 在 UUD reset 被调度时提前返回，尚未走普通首屏/日期设置选择；Backup1841/1842=4/4是在排入异步工作时写的，不能代替人脸清理完成。冻结状态也没有保存当前 screen/controller，不能把一个非空 Layer 当作可见 Widget 根。（AP `238030c..334、28272a8..2d4、2b8036c..37c、21916b0..1920`；serial **16496–16566、17908–17934、20632**。）

**当前 profile 不应仅因默认种子的 NOT_SET 而被预期显示首次日期设置。** date状态的原持久键为 `02cf01b4`，种子值2，AP86B冻结RAM已0；原 boot 会从 udate 当前时间类型重新更新它。AP86B在启动前已通过原 BY_BOOT API 初始化虚拟时钟并读回。（AP `40f92c8..92e8、2b63924..39b8、2b63c2c..c40、2380464..474`；serial **1087–1101**；Backup文件偏移 **9100c**。）

本轮只读原件与已存在回执，只写本目录三个文件；未启动QEMU、执行客体/CP、改runtime/STATE/锁、改Backup或操作相机。A=原字节/冻结运行直接事实，B=有约束推断，U=未证实。AP/Obj地址分别为appFw.so/libObj.so的ELF image VA；CP是Thumb VA，文件偏移=VA−108000。serial指 `menu-repair-01/runtime/runs/ap86bdisplayv2-3d542078/serial.log`，**按LF计行**，非 `splitlines()`。

## 重建与证据身份

项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/first-screen-trigger/audit_first_screen.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/first-screen-trigger/audit_first_screen.py --check
```

第一条退出0重建 [first-screen-proof.json](first-screen-proof.json)，第二条独立提取并逐字比较、不写文件。[脚本](audit_first_screen.py)核卷UUID、三份原库SHA、54项指令断言、10个CP跳表槽、parser表、RTTI、screen名表、日期类型分支、原种子校验和与冻结Backup字段、AP86B serial及display双bank RAM。只反汇编/解码，不执行原指令；`dis ap VA LENGTH`、`dis cp VA LENGTH`、`str`、`xref`为只读查询。

| 原件 | 固定SHA256 |
|---|---|
| appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| libObj.so | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |
| cpapp-b.bin | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` |

proof.sources保存各输入真实路径/长度/SHA；没有把早期失败的 `ap86bnative-37785e4e` review当成本轮display-v2验收。

## 1. 谁决定首个画面

**A静态：首屏选择属于AP业务控制器，不是CP发一条“显示首屏”通知。** 共同UI循环 `16f1998` 驱动事件、资源、notifyDraw与drawFramebuffer；screen管理器则是 `presenter_controller_manager`。原日志字符串 `30f9ec0` 明确 `open_screen_ii`，函数入口 `218fd0c`；分派器 `21916b0` 从活动controller取vtable+88。在boot时，该槽 `455b2b8=2380778` 对内部30072调用 `237fe28`，RTTI `23scr0039_boot_controller`（header455b220、typeinfo455af38、字符串3135820）。boot presenter RTTI/日志名存在于 `30da2f8、30e1ae0`，不把它的存在当作屏幕可见回执。（AP上述VA；serial **11114**确实消费30072。）

```text
AppFw 自发内部30072
  -> manager21916b0 -> controller vtable+88
  -> scr0039_boot_controller237fe28
     -> 必要时285f3b4 /285dc98启动并等待boot future
        -> sequence_boot原通知 -> 本机wait返回
     -> 读取boot information、cancel key、date187、force1098等
     -> shutdown/特殊启动分支
     -> update_uud_backup_reset_and_initialize
        true: 设controller+110c3，日志uud reset，提前return
        false: 普通首屏选择 / rep_boot设置流程
  -> manager218fd0c创建controller/presenter
  -> Widget实际可见/资源/notifyDraw -> GRM dirty -> GPE
```

图中前半静态调用可重建；**最后从UUD异步完成重新进入正常首屏的整条业务边仍U**，不是无条件实线成功链。AP86B已保存 `FX3_BOOT_CV_RETURN byte_done=1`（serial **15984**），因此旧AP77的boot future等待不再是本次UI线程卡点。（AP `285e3fc..e430、2b68370..838c`。）

**A：普通选择依赖的是一组状态，不存在一个通用的“电池ready便画首屏”条件。** `2380144..17c`读boot information结构、`187=date_time_set_status`、`185=cancel key`、`1098=clock_force_settled`；`237fc44`与`237fcb8`计算特殊启动/电源键分支，`238023c..274`还处理外部模式。原日志分别为 `3135899、31358c6、31358f6、3135994`，可在后续同实例采集直接核对。涉及的特殊启动key/type/ext-mode本轮只有原整数分支，未给它们补造机身模式名字。（AP `237fc44..fd08、2380144..0274、238034c..03ac`。）

日期/普通分支的原screen ID可独立从16B名表行核对：

| 条件或用途 | 原screen ID / 名称 | 依据 |
|---|---|---|
| 启动控制器 | `2ae scr0039_boot` | 表415a990；handler2380778 |
| 日期未设/force等设置入口 | `2e1 rep_boot` | `2380464..488、238061c..628`；表415acc0；原类日志312c1e0 |
| 普通拍摄候选之一 | `178 scr0103_0009` | `23806c0..6d0`；表4159630 |
| 其他受功能/当前mode控制的候选 | `18e scr0103_0023`、`192 scr7248_0001`、`193 scr7221_0004` | `23803d0..404、2380628..6bc`；表4159790/97d0/97e0 |
| 哨兵 | `407 SCREEN_NONE` | 表415bf20；237f74c检查 |

`237f74c`经controller+10f50的接口请求开屏/附加层，`21916b0`随后按当前与pending ID处理。**U：当前究竟停留在boot、rep还是其他screen，不能从78个Widget候选反推。** rep_boot本身还有 feature、地区/初始化/其他首启选择，入口范围 `2324xxx..23257xx`、日志312c1e0；本轮没有闭合所有语言、地区、隐私提示的产品组合，不能把其中某一个页宣称为FX3唯一首屏。（AP `237f80c..890、2191758..17b4、2325170..5440`。）

## 2. AP86B此刻缺的具体前置工作

**A：0400已完整返回并继续队列，随后0402确实发出。B强：SeqQueueCommon末段仍被0402同步接收阻塞。** 原402发送栈在同tid362中含 `2de7264←2df259c←2dd1f00←2dca868←2bd76fc`；原公共接收器 `2de72fc` timeout−1。三轮SeqQueueCommon snapshot均在OSAL receive，同SP=`7ec135d170`、参数=`7ec135d530`、PC=`7f8489acbc`。没有保存用户LR/消息队列当前内容，故等待的跨时刻唯一归属仍B强，不能冒充完整用户栈。（serial **17905、17927、17935、17939–17951、26264–26329、54497–54574、84078–84158**；AP `2df2598、2de72fc..7320`。）

| 0400完成时队列顺序 | 原run / 名称 | 实际推进与缺口 |
|---|---|---|
| 0 | `2dca7fc sequence_sys_set_timecode_run` | 已执行，0402 mode0 raw已捕获；serial17941–17951 |
| 1 | `2dca610 sequence_sys_set_timecode_preset` | 排队；只有+1bc=0，另三项未采；serial17910、17931 |
| 2 | `2b7f8cc sequence_delete_all_individual_face` | 排队；其原尾部才发布内部30386；serial17911、17932；AP2b8036c..37c |
| 3 | `2d9ac90 sequence_set_release_lock` | 排队；+1bc=80000033，但+1b8/+1c0未采；serial17912、17934 |
| 4..10 | 七项未捕获 | 观察器只遍历前4，不能凭长度11列出另外7项 |

**长度11是0400返回检查点，不是终态队列长度readback。** display RAM mirror中的queue字段保留该采样；0402已经进入，不能把保留的11解释成它尚未开始或11项都被一一观察过。0400的completion列表begin=end=0（serial **17919、17926**），这里不存在一个已保存、但尚未执行的0400 UI-enabling observer。（AP `2bd76f8、2bd7754..7788`。）

独立解码 `osd-ring-final.bin` 的display header `+3000` 与active bank，得到：model index6→原表2f99ce0的type0、270=7、243=2、d22=MONITOR1，Widget候选78，dirty非零1次/零5165次；不是文件初值index8/type2。GUI持续推进仅产生FillRect+Flush（serial **20779、20785**），后续dirty采样为0（**22788、23022**等）。**A：没有新的绘图命令；U：具体缺哪个可见Widget/资源/scene状态。** Layer非空不证明Widget根可见，观察器也明确 `visible_and_resources_loaded_unproven=1`。（Obj `175044、1771f4..268、16ea58..60`；serial **20632–20651**；proof.display_RAM。）

## 3. 0402与0404的原CP合同

这两项与0400同属SYS/TCUB过程式路径，**不是旧VDF2001类命令**。脚本重新从CP原表计算下列槽，未照抄A7C2 VA。（CP本表所有地址，proof.cp_timecode_tables/cp_parsers。）

| 层 | 0402 | 0404 |
|---|---|---|
| parser登记 | b71d34→1a8134 | b71d3c→1a8190 |
| wire→internal | 1acba2→1ad042，internal40 | 1acba6→1ad046，internal41 |
| phase0 | 1a8f96→1a9a60，TCUB event2 | 1a8f98→1a9a72，event4 |
| TCUB | 1b90ae→1b9146，pending mask0x4/bit2 | 1b90b2→1b917a，mask0x10/bit4 |
| 完成→internal | 1ad1ce→1ad37e，241 | 1ad1d2→1ad384，242 |
| 回复分派 | 1aabb2→1ab1ae→1ae03c | 1aabb4→1ab1bc→1ae0c0 |

0402 parser把byte8存到 `19eafb8+434=19eb3ec`；0404把四个byte存到 `+438..43b`。TCUB各自设置pending位，然后通过共同 `1b944a` 传r1=0给完成器，**原样**写reply+8，没有590000 OR。二者均在配置接收后即可确认，计数器处理是另一生命周期。（CP `1a814a..815c、1a81a4..81b6、1b9164..9178、1b9198..91ac、1b944a..9450、1ae06c..e094、1ae0f0..e118`。）

```text
0402 实捕请求 10B：0d2002040a0001800000
1402 成功回复 12B：0d2002140c00018000000000

0404 请求 12B：0d2004040c000180 + task[1bc,1c0,1c4,1c8]各低8位
1404 成功回复 12B：0d2004140c00018000000000
```

0404若四值全0，请求为 `0d2004040c00018000000000`，**仅静态示例，未实捕**；不能依据首字段0冻结后面三个0。AP构造没有在此验证时分秒合法性，CPparser也只是保存，故不把任意猜定的23/59上限冒充原字段合同。（AP `2dca670..698、2df232c..2348`；CP `1a8196..81b6`；serial **17910**只含input1bc。）

最小诚实提供：只在明确虚拟配置profile下，保存实际desired run/preset及pending counter backend，独立分配12B回复，source92840747，投给**本次请求source**，等待原AP消费释放；不固定跨run的81cf61c2，不变更原request所有权。发送/分配失败回滚，不重复完成；只声称软件配置接受，不声称CP计时器、帧元数据、live view或HDMI生效。0402此时不需要伪造SysCon、电池、镜头ready或live-view帧。（CP `1aef1c..7c、1b944a`；AP `2de7304..7320`；实捕serial **17951**。）

## 4. 人脸清理：同步请求全集与字节边界

本节覆盖原 `sequence_delete_all_individual_face::run` 的成功路径 **2b7f8cc..2b80460**，并单列文件/本地内核操作；不把先前common_preparation的remote1d9分配再算一遍。该任务当前仍排队；表内是静态后继，**不是本轮已发送的新请求**。（serial **17911、17932**；原函数名3920da8。）

| 顺序 / AP调用点 | 原同步操作 | 回复与诚实实现 |
|---|---|---|
| 1 /2b7f9b0 | `2dda334→2e4efb8`，local DMM op20、unit1dc、domain0、allocate-only | 原0061003c服务分配真实本地内存；40B响应含动态handle。未知handle不能写死 |
| 2 /2b7fa08 | `2dda374→2e4f4c0`，local op24按上一步handle打开 | 原本地服务；40B响应需真实映射/容量，不能用remote1db响应替代 |
| 3 /2b7fc18 | `2dda5b4→2e50150`，open/mmap | 主动本地syscall，无OSAL成功回复；原任务清零0xe220并写8份facerec文件 |
| 4 /2b7ff38 | `2dda5f4→2e50264`，munmap/close | 本地syscall，无OSAL回复 |
| 5 /2b7ff84 | `2dda434→2e4f7b8`，local op25关闭视图 | 动态handle/引用计数，40B原服务响应 |
| 6 /2b80128 | `2dda474→2e4f280`，local op23、option0释放1dc | 必须实际释放；不是op25，也不是提示音的option2 |
| 7 /2b80230 | `2dda3f4→2e4fbf0`，remote op21打开unit1db、domain1 | 40B；请求+8复制task+1c4的保存handle，不是已证open-count字段；需核实际generation/opens/字节区 |

后面 `2b8028c→2dd8b54→2e41e20` 向90060197发 **0206/24B no-wait登记更新**，x4/x5都0，发送后原wrapper直接写本地result0；**不应给0206补同步reply**。随后原任务更新Backup/登记model参数，在 `2b8036c..37c` 自发 **28B内部30386**。它是AP清理完成事件，不是CP/SysCon应发送的ready通知；不得直接造30386绕过真实字节清理/文件写入。（AP `2e41e7c..e94、2b802ac..2b8037c`；本轮serial未捕获30386，只能称未记录，观察器有界。）

remote1db已在此前准备阶段真实分配/open：serial **17198–17200、17780–17782**，本软件几何为handle840a、CP地址1dd80000、容量d100。**若后续实捕仍绑定该活代次、corr0，则8021成功响应的条件示例为：**

```text
2180000000000000010000000a84000000000000000000000000d81d0000000000d1000000000000
```

这不是未捕获请求的通用白名单。必须复制实际correlation、维护真实opens、保留已有1db字节与读租约；原AP请求字段见 `2e4fcf0..fd38`，响应读取/释放见 `2e4fe04`以后。local1dc的分配handle/物理区未采，因而**不给虚构固定成功字节**。该路径不新增ICDT：原AP本地清理facerec，再更新登记元数据；不得为清理任务伪造识别结果、sensor帧或把remote1db清零冒充原任务操作。（AP `2b7fd18..fe50、2b7ff18..2b8037c`；前阶段存储合同见[1d9审计](../dmm-unit-1d9/README.md)。）

## 5. release-lock：一条同步事务、一个条件分支

`2d9ac90`先读task+1b8选择0..3，得到要交 `2dd8814→2e33db8→2e33bcc` 的值；当前只采+1bc=80000033，不能代它选择+1b8或+1c0。原常见分支形成 **PID403d/16B**（目标90040193、原reply来源90040193、waiter80020002）：mask8000、布尔on/off、实际transaction token。AP通过引用计数 `9684fb8` 等可能省略一次重复wire提交，此时本地return0；应保留原行为。（AP `2d9acd0..ad38、2d9ae24..eb4、2e33bf0..cd0、2e33db8..e84`；serial **17934**。）

CP `98c8ea..c9a6`按mask/当前release状态决定立即确认还是延后；空闲分支 `98f66a`构造12B **type1/cmd403d/echo token/statusf000**。它不是BB200d报文，不带590000域，也不能回裸status0。（CP `98f68a..f698`；AP `2e33cc4..cd0`明确比较f000；旧独立原件证明导航：[release-inhibit](../../../menu-repair-01/runtime/release-inhibit-original-proof.json)，本脚本重新读取CP字节。）

```text
回复schema：01 00 3d 40 + 实际token u32 LE + 00 f0 00 00
若实际wire token=80000033：01003d403300008000f00000
```

**80000033只是队列输入，本轮还未捕获这次wire，不能先绑定它。** 原既有软件模型只接受空闲mask8000、保持抑制状态，active release不能ACK；完整CP功能并未运行。（AP `2f6de20、2e33ca0..cc0`；CP `98c974..c992`；serial **17934**；runtime/helper源SHA见proof。）

若task+1b8==1，run还会 `2dd8994→2e3334c` 发 **40a5/12B no-wait**，然后 `2dd8e14→2e26c40` 等本地 `9684918` 条件变量清零。40a5不需要同步成功reply；本地等待的原事件生产者/当前busy尚未闭合，**不能发一个“lens ready”包或直接清flag来替代**。这也解释为何仅凭序列名不能承诺release-lock完成必有首屏。（AP `2d9ad5c..add8、2e3337c..3a8、2e26c6c..c9c`。）

## 6. 首次日期设置与Backup依据

**A：版本reset键与日期设置键是不同状态。** 原UUD比较1841<1842时，先调度option6再写1841=1842；boot controller把返回true存+110c3并提前return。冻结RAM 4/4只能证明版本更新，不能证明后面的delete-all任务完成。（AP `28272b4..2d4、238030c..334`；serial **16496–16566、16838**；Backup `9ce74/9ce78`。）

| 日期项 | 原依据 | 本轮事实 |
|---|---|---|
| 参数187 | getter2930b9c→8227358，next822735c；enum表41359e0 | 0 MANUALLY、1 FORCIBLY、2 NOT_SET、3 UNKNOWN |
| 原持久化映射 | 表40f92c8含param187、key02cf01b4 | 同型号种子offset9100c=02；本轮RAM=00 |
| boot当前时钟重读 | 2f72504→2f720f4，经原90013d/op2；2b6393c跳表3917778 | 原datetime type0/1→status0，type2→2，type3→3；因此不是只读种子旗标 |
| force条件 | getter29489e4→8365c90，参数1098 | boot在2380468..474合并`status==2 OR force`；当前force未独立采样 |
| 当前clock profile | seed-date-clock-v2：原BY_BOOT API设置再读回 | serial1089冷态3；1091原初始日期；1095设置；1097/1099读回类型0；1100 ready |

**B强：当前已初始化的虚拟时钟解释了status由2变0，普通日期设置入口不应按种子02强行触发。** 最终RAM本身不能证明是唯一writer，也没有保存2380464当时的寄存器；因此不把整个运行逐指令归属升级为A。若以后要研究真正未设日期场景，应由Lead另建明示clock profile，走原未初始化语义及错误/默认日期合同；本审计不改当前profile或Backup来凑设置页。（AP `2b63924..39b8、2b63c2c..c40、2380160、2380464`；serial **1087–1101**。）

语言/地区是后续设置流程与产品feature条件的一部分，本轮未确认它们的具体持久键/所有组合。**没有证据把当前黑帧归因为语言未选、镜头未装、电池未就绪或缺live-view。** 已定位的真实服务缺口是0402；其他服务的必要性需补完整调用/状态读回，不能根据字符串存在补发通知。（AP `237fe28..2380774、2325170..5440`；serial **17951**。）

## 7. 最小被动采样与验收

以下交给运行链持有者，本worker未安装探针/运行。所有对象必须使用本run真实基址/生命周期；不得直接写状态、调用额外getter改变引用计数或读取已析构task。（AP表内VA，原指令在proof.code。）

| 观测VA | 只读字段 | 判定目标 |
|---|---|---|
| `2dca868 /2df259c` | task身份、转换result、reply实际source/free | 0402被原waiter消费且run返回 |
| `2dca610` | task+1bc/+1c0/+1c4/+1c8，捕完整wire | 冻结0404真实preset，不填猜测0 |
| `2bd76f8 /2bd7754` | queue+10节点、+20长度、+88active；每node+10的task/vptr/run；completion+158/+160 | 11项当时的完整身份及后续进入/完成，补未采7项 |
| `237fe28 /2380310 /2380464 /23803f4` | controller、+110c2/+110c3、187/1098、三个目标screen ID | 普通首屏选择是否执行/为何早退 |
| `21916b0 /218fd0c` | manager+1d0 pending，+2b8/+2b0活动controller，+2c4/+2c0 screen IDs；创建返回 | 确认真实boot/rep/普通screen对象及presenter |
| `2b8037c /1cdcf28` | 原30386发布、接收者RTTI/状态 | 原清理完成；后者是dlg_set026_controller，不能直接认它为boot controller |
| `2d9ac90` | +1b8/+1bc/+1c0，9684f80/fbc/fb8、9684918 | PID403d实际on/off与可选40a5本地wait |
| `2930b9c /29489e4 /293019c /29301ec` | 当前187/1098、当前mode143/option145 | 不以desired144或Backup版本代替当前业务mode |
| `Obj1771f4 /17723c /16ea60` | 真正Widget/Layer qualifier、visible/resource flags、dirty与对象RTTI | 首个非清屏绘制；Layer非空不等于根可见 |

**最小运行验收应分别保留**：0402消费→真实0404及后继任务推进→原人脸清理和内部完成→实际screen创建/visible/dirty→新增原GPE文字图形→1003新像素与MENU反馈。单独完成前几项不充最后两项；即便当前四项均完成，另外七项/首屏重入/Widget资源仍U。（原VA见表；本次直接像素证据只有serial **20779、20785**的黑清屏。）

## 8. A7C2参考与明确开放项

本地 [a7c2-latest](../../research/a7c2-latest/README.md)固定 `b3d7c1fed349f1d918acc4259f1d2b3a7c52a500`，记录维护者已有原菜单与640×480 OSD；本轮联网能读[上游仓库首页](https://github.com/chocotan/a7c2-qemu)，但固定进度文档raw读取失败。因而“已越过首屏”仅作为本地冻结研究所记的上游报告，**没有重新验收其当前运行，更不补FX3因果边**；不移植其VA、offset或成功通知。工具方法核对了[Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)，Sony私有语义全部由本地原码/serial支持。

仍U：首屏当前controller与完整可见Widget树、UUD完成到正常首屏的完整静态/动态边、七个未采队列项、0404全值/release selector及token、原CP DMM动态handle/opens之外的完整硬件行为、40a5本地wait的事件生产者、语言/地区各产品组合、SysCon/镜头/电池ready的必要依赖、连续非黑原菜单及按键反馈、CP计数器/sensor/live-view/物理机验收。**脚本PASS表示离线证据可重建，不表示上述门槛关闭。**（缺口对应第2、4、5、7节VA及serial范围。）
