# FX3 boot / shutdown / rep_boot 与 UUD 后 Backup reset 审计

**当前确定的阻塞是原 `Backup_reset_all` 发往 CP Backup `0x903e0811` 的 `op=0x33` 没有接收者，AppFw 在内核中无限等待。** UUD 原路径会设置 reset 类型 `e85=3`，shutdown 初始化随后依次调用原 flags **1、4** 两次；现有日志与第一次等待吻合，实际40B请求、动态 reply queue 和当时的 flag 尚未捕获，仍须被动核对。（AP `2827324→2823098/28230dc、2381c50→285d238→285c658、285d118..124`；backup.ko `.text+34d0..3524、11c0..1b30`；serial **20359、22946–22960、37388–37402、51830–51844**。）

**开屏前提应纠正：`2ae / 2af / 2ae` 是一次调用的三个引用参数，未观察到三次开屏或 shutdown→boot 返回。** 全部 serial 只有两个 `SCREEN_OPEN_ENTER`：初次 `(407,2ae,407)`、后一次 `(2ae,2af,2ae)`。`0x30086` 是人脸清理完成；另有一条实际 `MODEL_POWER_OFF=3002c` 在后一次开屏之前入队，它才是 boot 本类关闭分支接受的事件。末条活动 boot 快照位于开屏入口之前，不能当作卡住后仍活动 boot 的新读回。（AP `2380778..07a8、237fb50..fc40、237f8fc..fb4c、218fd0c..2190010`；serial **11187、18476–18477、18806、20038、20097、20104–20105**。）

只读审计日期：2026-11-02。仅写本目录三文件，未启动QEMU、执行固件、改runtime/STATE/锁/种子或操作相机。A=原字节或保存的直接观测，B=受约束推断，U=未证实。AP/Obj/CP地址分别是对应原库 image VA / Thumb VA；CP文件偏移=VA−108000。内核模块是ET_REL，地址写 `.text+offset`；不得把它当固定加载VA。serial指 `runtime/runs/ap87r2native-51e93181/serial.log`，按LF字节计行。

## 1. 实际事件链和画面切换原因

```text
初始 AppFw 自发 30072 (MODEL_POWER_ON_COMP)
  → manager21916b0 → vtable+88=2380778 → process_power_on237fe28
  → update_uud2827348 →2827290
      1841<1842：调度mode option6，重置APP子系统，更新版本
      →2827324→2823098：param e85=3
      →controller+110c3=1，提前返回2380330

原异步人脸删除任务2b7f8cc
  →2b8036c..37c 发布30086 [serial18476–18477]
  →manager收到30086 [20038]
  （boot自身+88只认30072，30086不会直接调用process_power_on）

同轮原队列后段 sequence_sys_request::run2d74344
  →2dd6794→2e3a19c，原SysCon/UPM目标90030001、cmd4022
  .. B：原UPM/InfraNotify通知回路未逐帧采齐 ..
  →InfraNotify(tid327)发布3002c MODEL_POWER_OFF [18806]
  →manager特殊电源分派（std::function具体绑定未逐条恢复，B强）
  →boot vtable+90=237fb50
      flag110c2!=0 →237f8fc，按shutdown information选screen
      默认分支选择2af →237f74c→manager开屏
  →一次open_screen_ii(2ae,2af,2ae) [20105]
  →shutdown init2381bbc→业务门2381a60
  →2381c50→285d238→285c658
      e85=3 → backup_reset_all(1)，随后backup_reset_all(4)
      当前停在第一次远端CP reset等待
```

**A：30086与3002c是两个独立原事件，不能用时间邻接把前者改名成开屏ready。** 名表 `4171f80→MODEL_FACE_MEMORY_ALL_RESET_COMP`、`41719e0→MODEL_POWER_OFF`；发布30086的原指令 `2b8036c` 写86、`2b80370`写高3，原28B消息在serial18477逐字匹配。boot `2380784..07a8` 对其他消息直接返1；manager随后还会走共享/generated事件回调 `218e194`，本审计未穷举其全部注册项，不能把直接handler的忽略升级成“30086全局没有任何消费者”。（上述VA；serial **18476–18477、18806、20038**。）

**A：进入的是原 shutdown 业务流程；U：不能宣布实际电源已关闭或UI软重启已完成。** 原 `sequence_sys_request` 的wrapper明确构造4022并发到90030001，保存队列中同run任务输入+1b8=54、+1c4=2、+1c8=1；这里54仅记原task字段，不冒称wire command。`InfraNotify` 的原分支更新shutdown信息参数17a并发3002c（日志字符串 `37fef33=INFRA_NOTIFY_POWER_OFF...`）。原序列任务在serial18805–18808进入/返回，附近3002c确由InfraNotify发送；缺少完整UPM通知payload、用户栈及factor/type/next_boot瞬间值，所以精确跨线程归属仍B强。（AP `2d74478..74508、2dd67bc、2e3a1c8..2254、2a8a8a0..aa24`；serial **18805–18808、23092以后tid327名InfraNotify**。）

**A：日志没有 shutdown→boot 重入回执。** 捕获中3002d（MODEL_POWER_ON）、3002e（MODEL_POWER_OFF_CANCEL）、30074（MODEL_POWER_OFF_COMP）的 `BOOT_QUEUE_SEND raw` 都为0；这是本observer保存范围内的零计数，并非全局事件不可能发生。第二次开屏还在初始化过程中同步等待Backup，不能以第三参数2ae推导“shutdown已取消”。（事件名表 `41719f0/4171a00/4171e60`；相应控制器路径 `237fbe8..fc40、2381760..1824、23815a4..15e4`；serial **20105、22946–22960**。）

**A：末条scene不是卡住之后的活动controller读回。** `20104` 的observer event32与`20105`同sample1187，均处于 `218fd0c` 入口；它保存旧boot、flags1/1、date187=0、force1098=1、mode143=2/option145=6。之后没有新的scene记录。原manager在 `218ffd0..ffe4` 创建并调用新controller的init，随后 `218fff0` 才继续presenter步骤；不能用入口旧对象的RTTI判定后续新对象的存在、可见性或最终提交。需在init返回处及manager调用返回处再读。（AP上述VA；serial **20104–20105、22950**。）

## 2. Backup reset：内核到CP的逐字节合同

当前原件身份由脚本强校验，不能套用旧success-cases中的其他机型/版本偏移。

| 原件 | SHA256 |
|---|---|
| appFw.so | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |
| backup.ko | `8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d` |
| libbackup.so | `6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d` |
| cpapp-b.bin | `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba` |

**A：本地reset已执行到返回成功，随后才发送远端reset。** `libbackup+237c` 使用本地3e014d/op15请求原kernel API；kernel dispatcher `.text+7df0..7dfc` 调 `Backup_reset_all`。该函数先调用 `.text+33f0 Backup_reset_all_subsystems`，非0则早退；只有0才到 `.text+3514` 进入公共封装。这解释为何“same-model kernel Backup已加载”仍不能覆盖当前等待；缺的是CP侧第二步，不是AP本地读写API。（libbackup `237c..23b4、1a10..1b10`；backup `.text+34e4..3518`；serial **22950–22954**。）

**A：远端是reset命令，不是 `backup_put_cp_wt_data` 写数据事务。** kallsyms显示 `backup_put_cp_wt_data+23c`，但该导出函数位于 `.text+72b8`、大小dc；`+23c=74f4`已经超出它。实际是无名callback `.text+74e8` 在74f0调用 `backup_osal_call_func(7aa8)` 后的返回地址。模块加载text基址由 `Backup_reset_all+48=ffffff80004ec518` 推为 `ffffff80004e9000`，匿名帧 `ffffff80004ea524` 正是公共接收器返回点 `.text+1524`。（原symtab、relocation74f0→backup_osal_call_func；serial **22949–22954、37391–37396、51833–51838**。）

**A：请求logical length=40B，使用一个消息页。** `.text+34f0..3514` 传变参 `(2,0,F,1)`，opcode33；`.rodata+80` 的entry10=ca，跳到 `.text+16b4`，selector2走19fc：两个scalar、零pointer、size28。公共封装以 `803e0811 | (1<<28)` 得903e0811，`osal_dynamic_id(2a,3e,...)` 生成本次Q；发送source也设Q。字段均u32 LE：

| offset | 值 | 原依据 |
|---|---|---|
| 00 | `00000033` | 13a0，opcode |
| 04 | `00000000` | 13a0，初始result |
| 08 | `903e0811` | 12ac..12b8、13a8，目的端 |
| 0c | **Q，实际动态queue** | 1298..129c、13ac..13b4 |
| 10 | `00000001` | 13a4..13b0 |
| 14 | `00000001` | 40B向4096上取整，12c0..12d0、13b0 |
| 18 | `00000002` | 19fc..1a04、13bc，scalar个数 |
| 1c | `00000000` | 1a00、13bc，pointer个数 |
| 20 | `00000002` | selector=reset_all；1a04、13e4..13ec |
| 24 | **F，实际native reset flag** | 34f0、1a08、13e4..13ec |

原码推导、**不是本轮实捕**的请求模板：

```text
33 00 00 00  00 00 00 00  11 08 3e 90  QQ QQ QQ QQ
01 00 00 00  01 00 00 00  02 00 00 00  00 00 00 00
02 00 00 00  FF FF FF FF
```

FF表示F的四字节，不是固定FFFFFFFF。UUD静态预期先 `01000000` 后 `04000000`；Q不可沿用另一个run。`.text+151c` 明确timeout=-1，1520等待，154c只读取reply+4，1550交回原调用者；随后free和释放动态ID。失败状态是有符号负值，成功0，不带590000/f000等其他协议域。（上述VA；serial **20359**唯一Skip0x811，三份等待栈。）

### CP原处理与回复

**A：原CP注册/消费端为 `003e0811`，接收线程入口4989d4，分派器4986b4。** opcode27..34由inline TBB映射，33的目标49889c；读取request+20的selector，2走 `498962→a84ca0`，把request+24的F传入。a84ca0锁定256个subsystem锁，按header子系统数量调用496cf4，成功0，失败−7，再释放全部锁；分派器把结果逐字节写到reply body+4。（CP `4989de..9ea、4986e8..6f2、49889c..8c0、498962..984、a84ca0..d2e`；本轮CP未执行。）

**A：selector2的reset不是全块清零。** 原496cf4按F选择attribute：1→bit6(40)、2→bit4(10)、3→bit5(20)、4→bit2(04)，再调49750c将原默认源复制回当前项。默认源位于data容量之后；attribute bit7表示重复槽，数量来自003e000c当前值+1。F1重置全部槽，其他F仅重置第一槽；不应把重复项整体容量/默认源偏移混淆。未知可变容量、无效索引、分组/锁语义未实现时不回成功。（CP `496d92..dc6、49750c..7618`；AP同源算法 backup `.text+878..a48、a48..bc0、5350..54e8`。）

**A：原接收线程另分配4096B回复并复制4096B，随后设置source=003e0811，目的地取原请求+0c；不是直接把40B请求指针回给AP。** 分配 `498ab6..ac2`，复制 `4989f8..9fe`，source `498a02..a06→a878d2`（写消息头−c），发送 `498a0a..a24→49f140`，最后 `498ada..ae2` 释放来包；发送失败路径也free回复。AP只消费+4，不能因此冒称CP原回复logical length=40。（CP上述VA；AP backup `.text+1544..1568`。）

## 3. 最小诚实修正：声明CP Backup存储后端，按真实数据reset后回复

**A：本轮RAM确有可复验的第二BK4 fixture，但它不是已绑定运行的CP primary。** 原公开seed SHA `bf3a9d85...`，RAM snapshot SHA `ca6075b0...`。脚本按BK4 header/索引独立解码，第二bank为 **+d2000**；003e000c是**1B值03，重复4份**。第二bank当前字节与该固定seed完全相同，checksum有效；按flags1→4在Python bytearray做顺序投影，结果如下。（BK4 header@d2000；CP reset原码见第2节；proof.CP_Backup_fixture逐项保留key/attr/offset/default。）

| 操作 | 选中项 | 重复项 | 当前与默认不同 | 投影结果 |
|---|---:|---:|---:|---|
| F1 / attr40 | 317 | 2 | 0 | 无字节变化 |
| F4 / attr04 | 2 | 0 | 0 | 无字节变化 |

这是固定fixture下的幂等数据证明；不能直接套用旧报告的bank偏移、32项、13份或其他backup.ko哈希。AP本地root位于预留物理404000000，而CP primary是另一地址域；header内同值04000000不能证明两者同一backing。（backup原Data_getter `.text+57d8..57ec`；本轮reserved范围404000000+221000，run command.json；proof.sources/CP_Backup_fixture。）

建议运行链最小实现，**本worker未实现或运行**：

1. 在现有内核UIPC/public-owner的合法路由中增加**精确903e0811、op33、selector2** 的CP接收端模型，先捕实际40B/source/Q/F及原页容量。不修改AP指令、调用额外API或清busy；userspace `LD_PRELOAD` 的capid不能截获kernel内部osal_snd_msg，当前Skip在kernel中产生。（backup `.text+14e8..1520`；serial20359、22948–22954；现profile init84加载原backup.ko。）
2. 明示独立的虚拟CP Backup profile，用已校验的本轮第二bank作初值，保存独立可写backing和锁/epoch；不要向整个AP reserved root重复做reset。对F1/F4按逐项默认源真正应用并读回；本fixture虽0diff，也须检查完整索引/default边界、repeat4和before/after摘要。任一步失败应原负值失败/保持等待，不能仅凭“通常默认就是0”回0。（CP `a84ca0..d2e、496cf4..de4、49750c..7618`；proof逐项317+2。）
3. 原AP本地reset已经执行，不再重复；远端每条独立分配回复，原+0..27复制实际初始化40B，+4写实际结果。按原CP4096B分配reply；若只复制40B并把其余清0，明确记录这是未使用尾页的可控软件差异，绝不能越界读取40B对象。source003e0811、目的Q，按原接收端所有权释放request；发送/分配失败保留可重试事务身份，避免重复reset/双free。（CP `4989f4..a56、498aa2..ae2`；AP `.text+14f4/154c/1568`。）
4. 核对第一条F1原消费/返回、随后第二条F4原请求/消费/返回；再追踪shutdown业务完成、原电源/启动事件和首屏。当前profile只证内存，不支持磁盘持久化、CP硬件运行或物理关机；不注入30086、30074、3002d、30072来跨业务门。（AP `285d118..128、23815a4..15e4、237fb50..fc40`；serial三份等待。）

**尚未关闭的实现准入：实际request raw/Q/F、当前kernel发送路由owner与页容量、CP profile生命周期和原回复消费。** fixture幂等性只能提供数据端依据，不能充任已接入的成功回复。`Backup_save=0` 不影响这里的远端同步步骤；也不应为此打开真实持久化。（init-reviewed.sh84；backup `.text+34d0..3524`；serial20359。）

## 4. boot、shutdown、rep_boot接受什么才会继续

原虚表header：boot455b220、shutdown455bb60、rep4530818。脚本按RTTI与slot重建；+偏移均相对实际vptr=header+10，不把typeinfo两个header word算进槽。（proof.vtables。）

| 控制器 / 事件 | 本类动作与门 | 来源与本轮事实 |
|---|---|---|
| boot +88 `30072 MODEL_POWER_ON_COMP` | 2380778→237fe28；必要时等sequence_boot；UUD true存110c3并提前return，否则读date187/force1098等选择首屏 | 初次由AppFw自发（16f2298..22b8），后续是否原生重发需采样；本轮16740 UUDreturn1 |
| boot +90 `3002c MODEL_POWER_OFF` | 237fbd4检查110c2；237f8fc按shutdown info选屏，默认2af；另有温度/错误等special screen分支 | InfraNotify tid327入队于18806；非按键ready、非30086 |
| boot +90 `3002d MODEL_POWER_ON` / `3002e CANCEL` | 237fbe8/237fc2c更新原业务状态，再请求2ae；这只是回boot，不保证直接到拍摄页 | 内部电源通知，原producer2a8ab2c/2a8ac44；保存发送记录均0 |
| boot +90 `300ad FATAL_ERROR` | 237fbb4→278d158错误流程 | 原model fatal；本轮无相应首屏成功证据 |
| shutdown init | 2381bbc→2381a60：录制/存储等多项业务busy/许可状态及110c2防重入均过门才285d238 | 当前已进入其后Backup等待；不需凭空造电池/镜头ready |
| shutdown +88 `30074 POWER_OFF_COMP` | 23815a4→controller接口+38；不是画一个boot场景 | 应由原shutdown/power流程完成产生；本轮无捕获 |
| shutdown +90 `3002d/2e` | 2381760..1804重新请求2ae | 原power-on/cancel；本轮无捕获 |
| rep_boot init / +80 | 2324800选择设置路径；2323ff8用2323eb0 admission门，未准入时保存110c4/110c8；2324068重试pending屏 | 原model/软件状态推进，2323eb0还含连接/时间状态；不是通用CP ready包 |
| rep_boot +88 | 基类1c97f48；不包含本类30072分派 | 不能把再次30072当rep首屏万能开关 |

**A：普通首屏来自boot自身选择，路径不要求先造live-view像素。** `2380464..488` 合并date187==2或force1098；符合产品例外时选rep_boot2e1，其他分支候选178/18e/192/193等。**当前入口保存force1098=1，即使date187=0也不能断言绝不会进入设置页。** UUD先早退，复入时这些参数还可能被reset改变，所以不能从20104提前确定最终页。（AP `238034c..06d0`；serial **16739–16740、20104**。）

**U：本审计未逐条恢复manager特殊电源std::function到+90的绑定，未穷举各共享/generated signal回调、所有rep_boot产品设置页顺序、power-on后每一个sequence与CP依赖。** 已关闭的是当前Backup等待、控制器本类事件分派与若干首屏决策门；未找到证据把当前缺口归为特定镜头、电池、按键或SysCon ready。上述外部服务的其他业务依赖不可据此宣布全部不存在。（AP manager共享分派 `218e194/218ef28..ef74`、repinit `2324800..232582c`；serial **22946–22960**。）

## 5. boot画面内容与绘制：不能把旧黑帧移植成本轮回执

**A：boot确有presenter和view/订阅初始化；U：尚未找到一条可证明Sony logo/特定可见Widget的完整资源链。** presenter factory2145918→2145764调用view接口、1e86638、22a2ae8等；2145844调用的2381050本身仅ret。它们能证明对象/共享订阅存在，不能证明boot应显示logo或已加载某图片资源。本轮未闭合到具体资源ID、Widget visible/Layer active与draw命令，故不给“logo缺文件”或“强制dirty即可修复”结论。（AP `2145764..2145914、2381050`；proof.code。）

**A：AP87-r2保存流GPE_CMD=0、DISPLAY_WIDGET=0、GRM_DIRTY=0条记录；这里是记录条数，绝不等同dirty值为0。** 早期有17条Element_setVisible调用（9204–9259），身份/资源与boot场景未建立对应；没有晚期scene或Widget树读回。不能把AP86B的首清屏/dirty统计算成本轮证据。原drawFramebuffer在Obj16ea58..60检查dirty，AppFw从16f1a1c调用；当前AppFw阻塞于Backup，足以解释没有后续主循环业务/绘制进展，但不能排除更早的资源或可见性问题。（AP `16f1998..1a44`；Obj `16ea10..16eae0`；serial **9204–9259、22946–22960**。）

## 6. 运行链最小被动采样清单

全是只读观测，不在本轮安装。使用实际对象生命周期/基址，禁止调用额外getter触发通知或读取析构对象。（表中VA均已在proof记录对应原指令或静态来源。）

| 位置 | 读什么 | 关闭的问题 |
|---|---|---|
| backup.ko `.text+14e8/14f4/1520/154c` | initialized40B、allocated capacity、src/dest/Q/F、replylen/+4和free | 最关键原协议，确认F1后真的有F4 |
| AP `285d034/285d118/285d120` | e85 current/next、两次实参和return | UUD reset类型实际归属 |
| AP `21916b0/237fb50/237f8fc` | message category/type、controller身份、110c2、shutdown info17a原三word | 区分30086、3002c及shutdown原因 |
| AP `218fd0c/218ffe4/218fff0/2381bbc/2381c50` | 三个ID分开记、新controller、init返、presenter、manager返后活动ID | 排除入口旧scene被当终态 |
| AP `2380778/237fe28/2380310/2380464/23803f4` | 原30072出现、110c3、187/1098、最终三ID | reset后是否自然复入首屏选择 |
| AP `2324800/2323ff8/2324068` | rep pending110c4/110c8、admission结果、具体setting ID | 首设置页而非万能ready |
| CP存储后端 | primary身份/epoch、317+2项当前/默认、repeat4、摘要/rollback | 回复0必须对应真实reset |
| AP `16f1a1c` / Obj `16ea10/16ea60` | dirty实际返回、根Widget/Layer visible/active/resource ID | 新原GPE与首可见内容 |

本run appFw基址=**7ed83b4000**；e85 current静态VA **83618dc**、next **83618e0**，对应 **7ee07158dc / 7ee07158e0**。这些是由映射计算的候选采样地址，**未运行读取**；不能当作已读到值3。（getter `29450e0/29450f4`；proof.runtime_VA_derived_only。）

## 复现与验收

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/boot-screen-controller/audit_boot_screen.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/boot-screen-controller/audit_boot_screen.py --check
```

第一条退出0重建 [boot-screen-proof.json](boot-screen-proof.json)，第二条重新读取输入并逐字比较、不写文件。[audit_boot_screen.py](audit_boot_screen.py)核卷UUID、8个固定原件/运行输入哈希、93条指令、所选完整窗口、ET_REL重定位、CP跳表、RTTI/事件名、两次开屏/三份等待、BK4 checksum和317+2条投影。可用 `dis backup.ko 34d0 58`、`dis ap 285d118 14`、`dis cp 49889c 28` 只读复核。

离线PASS不证明运行修正已实施、CP Backup回复被消费、原电源周期完成、rep或普通场景实际创建、菜单像素/按键反馈、物理机验收。明确开放项还包括实际raw/Q/F、CP地址域与kernel路由owner、晚期controller对象、boot logo资源闭包、全部共享事件/产品设置页。（对应上文第2–6节VA/serial；proof.unproven。）

方法仅核对[Capstone官方Python API](https://www.capstone-engine.org/lang_python.html)（2026-11-02），不以公开工具文档推断Sony私有语义；本轮结论均来自固定本地字节和保存日志。
