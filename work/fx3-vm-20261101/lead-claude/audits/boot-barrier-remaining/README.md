# 启动屏障剩余两项与完成队列

**最新续查AP83/AP84a：原四任务屏障已越过，当前黑屏不能继续归为license/getfunc未完成。AP84a四核及AppFw实际CPU0–3均已生效，但仍仅进入UI更新2次后等待OSAL信号量。** 三轮RAM/线程快照独立复核、MTTCG与icount分组条件和下一轮最小等待取证见[AP83/AP84续查](AP83-CLOCK-GATE.md)、[脚本](audit_ap83_clock_gate.py)、[proof](ap83-clock-gate-proof.json)；未启动QEMU。以下各轮历史结论按其冻结证据保留。

**最新收录AP81：SKD硬件不可用分支已通过240秒健康运行，原boot通知、UI timer和GPE首次清屏均恢复；当前仍是均匀黑屏，后续等待90050004的新pin。** 已闭合option6→9ab2518的实际选择，以及新增6端点/3边和9包条件合同，见[AP81续查](AP81-PIN.md)、[脚本](audit_ap81_pin.py)与[proof](ap81-pin-proof.json)。以下历史故障与缺证均保留各自轮次，不代表当前仍停在相同位置。

**2026-11-02续查：AP80c已实证闭合0119消费、panel真实handle4单任务屏障、同event原notify及AppFw协作等待返回。** 后续在SeqQueueNetwork/libInfraSKD发生external abort，菜单和健康运行仍未通过；详见[启动尾段续查](BOOT-TAIL.md)与[独立重建脚本](audit_boot_tail.py)。以下保留前轮AP76–AP80b2的历史推导与四任务证据。

结论：**新增 AP80 既有运行证据已证明四任务屏障正常通过：同一 sequence 的四个不同句柄各自然完成、各匹配一次，计数4→3→2→1→0，屏障返回0。** AP80a串口与已保存RAM的42条探针记录逐值一致（`22325–23115`）；AP80b1/b2再现通过。最新纳入的 **AP80b2已消费0328/path3与digital op3，当前捕获的未完成项是0119/panel reverse，实际enum2、h/v/osd=1/1/0**（`13953/13969/13996/14011`，没有1119回复）。这不是菜单、原CP或声音验收。AP76当时的“未证实”结论保留为历史，不能把后轮结果倒填AP76。

范围：只读原 AP/CP、库、AP76–AP80既有 serial、已保存RAM、部署清单与STATE；仅写本目录。不启动 QEMU，不拿运行锁，不改 runtime/STATE/原件，不操作设备。VA 均为 image VA；AP 运行 VA 加本轮模块基址，CP offset=VA−`108000`。原[脚本](audit_boot_barrier.py)重建[证据JSON](boot-barrier-proof.json)，固定五份原图 SHA256、44条关键指令、45个已部署探针的原始指令、8个0328锚点、四个任务指针和两类闭包虚表；proof保留代码块原字节及运行行号。新增续查另见BOOT-TAIL，所有输出仍在本目录。

## 续查：AP80已越过四任务屏障

本节 `AP80` 指 `runtime/runs/ap80apins-d8b39ab6/serial.log`；RAM指同目录 `ui-gate-counters.bin`，以下偏移是RAM**文件偏移**。`proof.runtime_continuation` 自动读回AP77、AP78b、AP79、AP80并验证，所有行号仍按原始LF计。四轮原receipt的UTC时间分别为2026-11-02 05:24、05:54、06:24、07:04；当地仍为11月1日。

| 轮次 | 原创建/完成数 | 屏障入口/正常返回 | 原始证据 |
|---|---:|---:|---|
| AP77 `ap77agate-f63dd39e` | 3/3 | 0/0 | 创建21294/21314/21316；完成21390/22104/22164；没有getfunc创建回执 |
| AP78b `ap78bboot-537976cc` | 3/3 | 0/0 | 创建21402/21423/21425；完成21611/22315/22378；没有getfunc创建回执 |
| AP79 `ap79tail-17293cc1` | 4/4 | 0/0 | getfunc创建21569、返回句柄21570；四完成21655/21803/22444/22504；四子任务完成仍不等于父已经调用屏障 |
| AP80 | 4/4 | 1/1 | 入口22233；四匹配22326/22409/23050/23113；归零23114；返回0为23115 |

这是不同轮的独立证据。AP77/78b支持“父流程可能未创建第四任务”的解释，**不能据此证明AP76也停在同一个前置调用**；AP76缺少这些探针，精确停止PC仍未证实。AP79表明“没有屏障回执”也可能是四任务已完成、父还没进入屏障，不能再把完成回调缺证统一当任务卡住（上述创建/完成行、AP79父getpin请求21619，原父屏障调用 `2b67a6c`）。

AP80中sequence=`7f881841b0`，appFw基址B=`7f43fde000`，由创建记录 `x2−任务入口VA`四路核对。创建函数 `2b63224`、完成函数 `2b634dc`、屏障 `2b6353c`均绑定同一sequence：

| 任务 | 真实句柄/内部4B | 创建行 / 返回行 | 自然完成行（TID） | 完成RAM偏移 |
|---|---|---|---|---|
| license | 0 / `00000000` | 21398 / 21400 | 23112（323） | `5bc0` |
| volume | 1 / `01000000` | 21417 / 21418 | 22325（324） | `5200` |
| beep | 2 / `02000000` | 21419 / 21420 | 23049（325） | `5800` |
| getfunc | 3 / `03000000` | 21569 / 21570 | 22408（326） | `5500` |

入口22233的 `x0=sequence,w1..4=1/3/2/0`。父TID327依原循环匹配，不是用四个不同线程日志凑计数：

| token | `2b63628`匹配前行 / w22 | `2b63678`匹配后行 / w22 | 前/后RAM偏移 |
|---:|---|---|---|
| 1 | 22326 / 4 | 22327 / 3 | `52c0 / 5380` |
| 3 | 22409 / 3 | 22410 / 2 | `55c0 / 5680` |
| 2 | 23050 / 2 | 23051 / 1 | `58c0 / 5980` |
| 0 | 23113 / 1 | 23114 / 0 | `5c80 / 5d40` |

四个token唯一且等于创建返回的四句柄；每次w25..28均为1/3/2/0，x19均为同一sequence。随后common `ret`观测点 `2b63624` 在23115返回w0=0，RAM偏移`5e00`。**不能读入口22233的remaining/expected为屏障初值，也不能读ret23115的remaining/expected为最终计数**：入口尚未执行保存，ret已恢复调用者的callee-saved寄存器；只有23/24号匹配探针内w22/w25..28有效。最终计数来自23114，返回状态来自23115（部署源 `helpers/fx3-ui-gate-v6.c:18–49,85–91`，原AP `2b6353c..680`）。license尾部23111的x0=`72`是void业务函数返回时遗留寄存器，不能把它当失败码；其真实完成句柄为紧随的0。

getfunc已在22262实际到发送点 `2dec7e4`，记录dest92840747、请求8B、回复28B与完整请求首8B。22275提交精确静音能力回复，22278原接收释放链标记消费成功，22408业务自然完成；所以**本轮325回复及后置MPR成功路径已运行通过**。部署的 `fx3-capid-v33.c:414`静态包恰为下文28B，`packet+12`填16个80；`.so`与CPIO所部署成员hash相同。它仍只实现能力不可用的软件profile，互补回退位不表示实际音频。

RAM证据：65536B、物理快照地址`41dc00000`、SHA256=`e71bd846f1adb9d7f02ce504b1c97132ad02a8619dc1bd84e9f13ceaa11f5889`，与原run receipt的只读快照条目相符。头magic=`3145544147335846`、版本2、发布记录数42、overflow0；记录从`4000`起、stride192B、24个LE64，尾sentinel=`544f4f4245544147`。脚本核对全部42条的id/n/tid、PC、x0..4/x19、w22、四expected、token与创建/完成身份；原数据布局见gate v6源48–49行。**RAM与串口来自同一个探针生产者，是两条保存路径的交叉核对，不是两套独立执行实验。**

观测边界：AP80 serial5191记录GPR/SIMD/NZCV/SP及NOP/CBNZ/BL自检通过，5192绑定45个点。脚本固定v6源码/ELF和v33源码/ELF SHA256，校验CPIO `simulation/fx3-ui-gate-v1.so`/`fx3-capid-v1.so`恰为这些版本，并将45处预期指令逐字与原appFw比较。v6源77–81重放原指令/原分支，48–49只发布记录；没有写w22或投递token。本审计未安装或执行探针；这是已有插桩软件guest的证据，不能排除插桩的时序影响。原run receipt确认qemu_exit0、process_reaped=true、inputs_unchanged=true、menu_verified=false。

### 屏障后的新等待：0328/path3

23115屏障返回后，23116–23127用户栈捕获 `2dee79c→2dd1040→2b67aa4`。23128、23140在父TID327、原source=`81cf61c0`发送精确10B：

```text
request: 0d2028030a0001800300
success: 0d2028130c00018000005800
```

请求是path3、pad0，目的92840747。原链 `2b67aa0→2dd1014→2dee6f0` 在 `2dee798`同步等待12B；成功必须保留CP音频状态域580000（CP `18588e/18589e`、`1adc8a/1adcde`、`5ca236/5ca258`），不能因别的ADF命令用全零status就混同。最小合同是**保存软件静音path3、保持playback_enabled=false、绑定本次source/lease后单次回复上述12B**；不是等待声音播放，也不是主动回复屏障句柄。完整原setter/路由/错误边界见[boot尾段审计](../boot-deferred-0119-0328-digital/README.md)。本脚本新增8个原指令锚点并保存相应AP/CP代码块。

AP80的部署清单中启用了pin graph，但没有`FX3_BOOT_DEFERRED`；build-receipt明确写“no0328/digital/119 success added”（`runtime/ap80a-owned-pin-graph/build-receipt.json`、run内`cpio-audit.json:init_text`）。因此这轮没有加入0328成功并非现有静音合同失败。serial没有1328发送记录，父在后续31389/31391、44536/44538仍处于ioctl/`osal_rcv_msg_tmo`；最后能绑定业务调用的等待为这条0328链。没有凭缺日志宣称后续所有boot步骤都已执行。

本次重建时，运行负责人已把STATE更新为`barrier_passed=true`，声明AP80a/b1/b2四任务均通过、后续panel-reverse单任务屏障/boot notify未闭合；本审计只读，未改STATE。proof分别保留最初AP76的null快照与重建时的STATE哈希。AP80a的0328等待是该轮历史停止点，后续进度见下一节。

### 最新纳入AP80b1/b2：0328与digital已越过，0119实际为enum2

`proof.runtime_followup`单独保存后两轮serial与receipt身份，不把AP80a的v6探针/RAM部署核对冒称为v7的核对。后两轮脚本仍逐项验证四个业务入口的创建返回、四个唯一自然回调、同sequence匹配、count4→0和w0=0。AP80b2的完成顺序为**1/3/0/2**，不同于AP80a/b1的1/3/2/0；验收核对集合和各次递减，不把任务完成顺序写死。

| 轮次与事件 | 原serial行号 | 结果 |
|---|---|---|
| AP80b1 `ap80b1path-d244a966` 四任务返回 | 23131/23132/23133 | 最后token0、remaining0、return0 |
| AP80b1 path3 | 23146请求、23157回复、23158提交、23160消费 | 1328/status580000，playback_enabled=0，result0 |
| AP80b2 `ap80b2digital-bd9672cf` 四任务返回 | 13922/13923/13924 | 最后token2、remaining0、return0；sequence=`7f7c182da0` |
| AP80b2 path3 | 13938请求、13949回复、13950提交、13953消费 | 同一静音合同已消费，result0 |
| AP80b2 digital op3 | 13966提交、13969消费 | service_state2、sensor_enabled0、notify_requested1、samples_emitted0，result0 |
| AP80b2 panel reverse | 13996枚举、14011/14094完整包 | enum2；28B请求、原source81cf61c0；尚无1119发送记录 |

AP80b2实际请求为：

```text
0d2019011c0001800101000000000000000000000000000000000000
```

+8/+9/+10=`01/01/00`与原AP enum2转换一致（`2dec094..2dec128`，既有[boot尾段审计枚举表](../boot-deferred-0119-0328-digital/README.md)）。**不能沿用enum0全零identity白名单给这个实际包回成功**：它需要处理两项reverse并保留独立osdRev语义，软件consumer/应用状态/原source完成需另行闭合。本审计只记录实际输入和未完成边界，没有集成新orientation后端。

四任务屏障已不缺license/getfunc或完成队列的新软件消息，0328/digital在b2也已有实际消费；剩余是实际enum2的0119完成、随后单任务等待、最终notify与菜单验收。AP80b2原receipt（UTC07:17:21）仍为menu_verified=false，不能用本脚本PASS关闭这些门槛。

## AP76历史运行事实与证据边界

下文 `corr` 为 `runtime/runs/ap76corr-316e20b7/serial.log`，`sync` 为 `ap76sync-fe30bc21/serial.log`，两者相对 `work/fx3-vm-20261101/menu-repair-01/`。行号按原文件 LF 计，保留 NUL，不采用会把其他控制字符拆行的 `str.splitlines()`。脚本封存每份 serial 的字节数、SHA256、请求全文和选定事件。

| 观察 | corr 行号 | sync 行号 | 可得结论 |
|---|---|---|---|
| 32e/33d 软件提交 | 21283、21326 | 21311、21318 | 服务端提交存在；不能替代子任务完成句柄 |
| 提示音 26 次提交 | 21370–22050 | 21363–22051 | 注册链走完最后一个 kind13/32a；此前静态循环末尾在 `2b61de0..df4` |
| ICDT 四次静音提交 | 21710、21808、21904、22001 | 21709 起至22001，共4次 | 文件分支通过软件完成，真实 DMA/声音仍未实现 |
| 三组原 `HasPublicKey/HasPrivateKey=0` | 22091–22096 | 22087–22092 | 至少已走到 `2b62640/684` 的类型1..3遍历；没有卡在这六次 Has 调用 |
| 0x325/1325 | 0条 | 0条 | 74条 provider 请求里没有325；没有已匹配的1325完成记录 |
| 四个 SeqThreadPool 的 futex 快照 | 43180–43412；syscall行43229/43287/43346/43404 | 43161起；syscall行43210/43269/43327/43385 | 都显示 sleeping/futex；只有内核栈和 syscall 参数，没有业务用户栈/闭包身份，不能直接判为四项完成 |

74条 provider 记录低于现有 `fx3-capid-v30.c:409–414` 的256条观测上限，325请求仅8B也低于其1024B长度限；最后一条 corr provider 为行22049。因而没有“观测256条配额耗尽”的证据。但没有 entry/创建探针，仍不能由缺包定位更早的 PC；串口 I/O 丢失和路径绕过观测也未被绝对排除。`FX3_UIPC_OBSERVER_END` 另有 dedup/stat 写丢弃计数，不能把其 unique 事件当成无损全量执行轨迹（corr 58934）。

首次AP76审计时只读 STATE 快照为 `barrier_passed=null`，`barrier_verdict=UNPROVEN_NO_MATCHED_FOUR_TASK_COMPLETION_HANDLE_RECEIPT`；历史哈希见proof `AP76_STATE_historical_snapshot`，当前快照单独保存。它是状态声明，完成判据仍以 `2b63628..678` 的真实句柄匹配为准。较早 `ap76file-c5303a3b` 只有18个beep提交、0个ICDT，不能用最终轮26/4倒填该轮（脚本分别统计）。

## license_get_i：完整顶层流程

入口 `2b61efc`，函数名 `391a590`。先调用 `16f0bd0`，结果等于1直接从 `2b6241c..438` 返回；其他模式执行下表。此模式分支是否在当前 guest 采用，六次 Has 事件已排除了本次 license 任务直接早退的解释（corr 22091–22096；Has遍历 `2b6261c..6bc`）。

| 阶段 | 原代码与行为 | 等待/失败处理 |
|---|---|---|
| 已安装选项 | `2b61f64→2de20a4→2e8b064`，向 `01ae852d` 发总长 `0x418` 的同步消息；首个u64操作码0，返回+8 u64状态，+16起10个选项字节；`3996420`表转换原值5..13为model枚举 | `2eacf18→2eacfe4` 调 `osal_snd_sync_msg`；非0服务状态经 `2b622e0..338` 重试50次、每次sleep20ms，最后采用type0/installed=false。**单次sync本身若挂起，外层50次重试并不提供超时。** |
| 选项归类/模型 | `2b61fac→2b5fec4` 更新映射；`2b61fc4→278e4c0→278e438` 从10项选出当前license type | 全部无选项映射为type0；其余类型1..6的优先关系见原分支，不能用Has结果反推整个选项响应 |
| 用户签名文件 | 当前type3：`2b61ff0→2de22e4→2e8b9a4` 读 `/setting/sig.txt`（字符串 `3917a6c`），fopen/fseek/ftell/malloc/fread/fclose；成功把指针/实际长度写model305/306；其他type：`2b62290→2de21a4→2e8b46c` 调 `remove(path)` | 文件缺失返回status2，`2b61ff8→2b620bc`继续；删除失败只日志。type≤1还调用模型清理 `2827214`（`2b622bc..2dc`）。这是原guest代码的潜在文件行为，本审计没有调用它 |
| 选项明细 | installed标志非0才执行 `2b620ec→2de21e4→2e8b4a4`，向同一服务发操作码u64=7、总长0x418，转换为0x230B明细表 | `2b620f4→2b6233c..418` 非0致命；installed=false跳过 |
| 密钥检测 | selected≠0：`2b62140/17c`检测该type；selected=0：`2b62640/684`循环type1、2、3，分别走 `2de2484→2e101a0` 和 `2de2444→2e1014c` | `Has*=0`被wrapper改为 `{missing:u32=1,status:u32=0}`（`2e10168..17c/1bc..1d0`）；两者皆缺时 `2b62694..6a4→2b5ffe4` 将1405/1406/1407模型标志写0。选定type的wrapper错误会fatal，循环中的非0状态跳过该type；“无密钥”本身不会fatal |
| MPR签名许可 | `2b62208→2ddba54→2e5d9e4→libmpr+2b4af4`，`mpr::SetDigitalSignitureLicenseType`；无选项列表产生mask0 | 即使mask0也匹配表category0/NONE（libmpr `369ce0`、`2b4aec`、`2b4bb0..bc4`），随后尝试GetPublicKeyDer；失败清factory hash后继续。libmpr `2b4ee0..4f08` 向 `80924127` 同步发送40B、内层cmd `00920111`；若返回+8为1或8，`2b4fb8`还调 `InfraC2PA::LoadCertificateInfo`。AP结果非0在 `2b626c0..798`fatal |
| 可选证书 | model feature `b1` 或 `360` 为真才走 `2b62de8→2de3894→2e0bae4→libmpr+95fc4` 的 `InfraC2PA::GetCertificateInfo` | 失败转默认信息，`2b62df0→2b6227c`继续；成功且返回有效标志则保存证书版本/字符串（`2b62df4..e4c`）。该库获取缓存、锁与加载器的完整存储依赖未穷尽 |
| 模型更新 | `2b62e50..2b62cf0`事务更新13b3..13bc、13c5、13c4、412、1324、11f5/11f6、13d2、13fc..1403；installed=true时展开明细行；发特性/事件94通知 | 这里还涉及模型锁、通知和字符串长度断言（`2b62bfc..c88`），不是仅六次Has就返回 |
| 电源选项 | `2b62d70→2de0994→2eb720c→2eb0988→2eb091c→2eafc58`，向 `80920871` **异步osal_snd_msg**发208B，总体op2、subtype12、内层cmd `00920171`；两项battery option ID为58/59，值由四个输入字段选1或2 | `2eafc7c`可能等待消息分配，`2eafca0`仅发送，**不等待服务回包**；分配/发送失败在 `2b62da0..dbc`仅日志。最后回 `2b6241c..438`，然后才允许worker完成回调 |

原厂 `libInfraCrypt.so+24a0..2524/+2664..26e8` 未初始化时返回0；没有必要为此伪造密钥或 `iCrypt_init`。顶层 `license_get_i` 不调用 Create API；但 **libmpr 即使收到许可mask0也会尝试 `iCrypt_GetPublicKeyDer(20300006)`，成功才做HashData，最终释放原分配数据**（libmpr `2b4c38/58/2b4d04/df0`）。GetPublicKeyDer失败分支 `2b4cac..cf0`清32B factory hash及长度，仍继续同步通知MPR，而非在此fatal；不能把“本函数顶层无Create”扩大成后续完全不调用crypt。当前六次Has只支持selected0遍历这一局部事实（corr 22091–22096）。

备份边界：顶层没有直接 `bk_read` 或备份文件调用；它读取选项服务与model状态。原 `libInfraOptionInstall+f6d0` 从缓存49188复制10B选项列表，`+10b44`从缓存生成明细；缓存的备份生产者、C2PA加载器、crypt底层安全存储及当前持久化状态，本轮没有完整闭合。因此不能说“license不读备份”，只能说**没有新增证据需要补一个备份协议回复**（上述AP服务链、Option库两个原函数）。

AP76的位置判断：六次Has均已正常返回，selected0循环可继续到 `2b621a8`；corr行22097紧接一个 `80924127` 同步返回，首16B为 `11019200020000000100000001000000`，与libmpr `2b4f08`的命令吻合，但该行没有TID/业务栈，**仅是MPR后续路径的相符线索，不是license完成证明**。目前不能精确指认它停在后续crypt/MPR/C2PA/model锁/消息分配还是已返回；UPM没有等待回包，不能猜为等待UPM回复。必须观测末尾与完成句柄，禁止再以“iCrypt=0”当阻塞原因。

## adf_get_func_i：325之前、之后与CP合同

函数入口 `2b60208`；`2b60258`仅日志，`2b60264→2dd0c94`进入wrapper。wrapper先调用trace helper `2f6ea24`（`2dd0cb0`，内部 `2f6eab0→16ed554`可能取锁），然后 `2dd0cbc→2dec778`构造325并在 `2dec7e4`发送。**任务内没有先于325的非ADF业务初始化/文件调用或功能条件分支**；不能用后置MPR操作解释“325尚未发送”。日志/trace锁/发送前分配是否卡住仍需PC观测（相应VA，corr/provider共74条且没有325）。

对AP76，“父任务还没有创建它”是另一种尚未证实的解释：创建点 `2b67674`位于TC同步、timecode、VDF黑帧/OSD/shutter/temp/panel、触摸方向、panel out、分辨率、OSD layout、touch sensitivity之后；最后前置调用为 `2b6758c→2ddfaf4`。这些前置操作在AP76的返回情况没有业务栈回执，不把任一项武断定为该轮阻塞点。创建后 `2b67678`保存句柄，才进行后续HDMI初始化，再于 `2b67a6c`入屏障（`2b66e08..2b676a0`）。

325回复后完整顶层正常路径如下：

1. `2b60268..26c`检查本地status=0，否则走 `2b60364..438`fatal；将19B能力写model `f04`，仅当low_cut_direct=true且advanced_wind=false时额外写 `f05=1`（`2b602a4..344`）。
2. 依据sequence `+5cc/+5bc/+5c0/+5c4/+5c8`，可调用 `2b60490→2ddb054→2e5c8e8` 的 `mpr_CheckCamIdReelNoFile`，据返回设置编号状态2或3（`2b60350..2b604c8`）。
3. 拷贝能力到sequence `+4dc..4ee`、清`+4ef`，调用 `2b60514→2ddae94→2e6e5d8` 的 `mpr_SetMovieRecParam`；可选 `2b60544→2ddb4d4→2e5cb80` 的 `mpr_ResetNumberingResume`。这两处没有紧邻的结果fatal判定（`2b604e8..2b60548`）。
4. `2b605ac→2dda7d4→2e69ef0`调用 `mpr_GetMovieRecStatus`；非0走 `2b60800..954`fatal。成功更新model72a/72b/6f4/6f5/6f8/6f9，发 `3010c`事件，再完成模型方法并从 `2b607d4`返回（`2b605b0..2b607d4`）。所以325回复不是整个任务完成的充分条件。

### 逐字节协议

AP请求严格为8B：`0d20250308000180`；目的 `92840747`，`200d/0325/8/8001`。AP等待28B，公共helper timeout=-1（`2dec77c..7e4`、`2de72fc..314`）。CP `1ac2c4→1b34a8` 的唯一 `SendADF_ProcGetFunc`构造旧 `2004/0128/8/0001`，完整请求 `0420280108000100`。CP内部case `d0`的TBH槽 `1ab808`解到 `1ac2c2`；**wire命令到internal case的上游注册表本轮未独立重建**，旧链和AP命令通过唯一getfunc构造器、下述1325转换器以及AP原调用链绑定，不能把表的未追踪部分伪称已解码。

旧处理类 `14ProcMsgGetFunc` RTTI `b38a70`、typeinfo `b6cb84`、vtable address point `b6cb6c`，Execute=`1645b4`。`1645ce..604`若对象+50错误非0，回`efff`；否则复制对象+38起24B缓存并用status0完成；`597f28..50`构造 `2004/8128/32/0001`，+8 status32覆盖复制数据首字。原CP缓存当前值与它的异步初始化执行结果均未观测，不能当作已知硬件能力。

转换器 `1b0a80`先检查旧cmd8128（`1b0ac0..acc`），生成 `200d/1325/28/8001`，+8原status32。旧+12..27的16个能力字节逐项变为AP同偏移；常规0/80，LowCut另有81；未知值会打诊断后保留（`1b0ace..1b0e74`）。最终 `1b105c..1064`以28B发送。旧32B中的最后4B不被这条转换器消费，意义未证实，不能附加到AP28B回复。

| AP/旧wire偏移 | 原CP字段名 | AP处理（out为325 wrapper输出结构） | 静音模型字节 |
|---|---|---|---|
| 0..7 | type200d、cmd1325、len28、flags8001 | 原请求配对、保持准确长度 | `0d2025131c000180` |
| 8..11 | status32 | `2decb30→2de4574`转换，本地status非0则boot fatal | `00000000` |
| 12 | inProSetIntMicSens | out+5=(byte==0)，out+4=(byte!=0) | `80` |
| 13 | inProSetInputType | out+b=(byte==0) | `80` |
| 14 | inProSetInputTrim | wrapper没有能力布尔写入 | `80` |
| 15 | inProSetChSource | out+8=(byte!=0)，out+9/out+a=(byte==0) | `80` |
| 16 | inProSetRecLevelMode | wrapper没有能力布尔写入 | `80` |
| 17 | inProSetAgcLink | 同上 | `80` |
| 18 | inProSetManualGainLink | 同上 | `80` |
| 19 | inProSetRecLevelLimitter | 同上 | `80` |
| 20 | inSetLowCut | out+7=(byte==0)，out+6=(byte==81) | `80` |
| 21 | inSetWindNr | out+d=(byte==0) | `80` |
| 22 | inSetIvoice | 仅日志，没有能力布尔写入 | `80` |
| 23 | inSetMyvoiceCanceling | out+13=(byte==0) | `80` |
| 24 | inSetPremiumCloserVoice | out+c=(byte==0) | `80` |
| 25 | prcSetZoomNrEe | out+14=(byte==0) | `80` |
| 26 | CP日志inProSetShoeMic；AP日志wind_nr_mode | AP仅打印零初始化out+15，无对应写入 | `80` |
| 27 | CP日志inSetWindNrMode；AP用于advanced_wind_nr_mode | out+16=(byte==0) | `80` |

字段名来自CP原字符串 `d8656c..d86758`、`1b1070/109c/10c8`；AP消费逐指令为 `2dec7ec..8a4`，AP输出名称来自 `3963cf9..3963f03`。**26/27的CP/AP命名不一致是真实证据边界**，保留双方名字，未推断为同一代硬件能力定义。

静音后端建议的精确28B：

```text
0d2025131c0001800000000080808080808080808080808080808080
```

它表达wire的“能力不可用”与正常查询status0；填16个00会被AP反向解释成支持一批功能。**80也不等于AP全部能力false**：其互补映射仍强制out+4 mic_base_level=true、out+8 tone_gen_direct=true，其他已写布尔为false；无法用一个raw12同时令out4/out5皆false，也无法用raw15同时令out8/out9皆false（`2dec7ec..83c`）。这不是已实现音频，后续tone/direct等命令仍须保留禁止播放政策。该回复静态不会触发 `2b6026c` 的status fatal；续查AP80已经观察到该回复消费及后置业务自然完成（22275/22278/22408），不能扩大为整机启动或原CP验收。

AP wrapper仅按固定28B复制并消费status/能力，没有自行比较回包opcode/length；下层UIPC的完整校验未证实。软件模型应严格限定上述目的、请求8B/type/flags、原request source、单次回复和生命周期，不能利用wrapper宽松处理（AP `2de7304..314`、`2dec778..b48`；CP `1b0aa0..ac4`）。

## 屏障：完成消息其实只有4B句柄

四次 `2b63224` 创建业务闭包，取free-handle队列；其返回由父任务保存：

| 任务 | GOT→入口 | 父FP句柄槽 / 返回观测PC | 屏障参数 |
|---|---|---|---|
| license | `472c3c0→2b61efc` | +70 / `2b63900`（保存于63904） | w4 |
| volume | `472b2d0→2b5fae4` | +6c / `2b66de4` | w1 |
| beep | `474f098→2b61a90` | +68 / `2b66e04` | w3 |
| getfunc | `47a6698→2b60208` | +64 / `2b67678` | w2 |

父任务 `2b67a60`加载+6c/+70到w1/w4，`2b67a68`加载+64/+68到w2/w3，x0=同一sequence后调 `2b6353c`。任务句柄是运行值，不能拿函数VA或source UIPC ID充当句柄。free队列空时 `2b6329c`返回**0x1000**，这不是成功创建；还必须观察派发返回值（`2b63224..318`）。原文未加前缀的1000/2000均为十六进制；脚本已显式使用0x1000/0x2000并断言两处原哨兵指令，见proof `handle_sentinels`。

业务闭包40B布局：`vptr64, target_object64, member_function64, adjust64`，尾部未用于本次业务调度；虚表 `46e5030+20→2b5fc40`解析成员调用。完成闭包40B布局：`vptr64, sequence64, completion_method64, adjust64=0, handle32, pad4`；虚表 `46e5008+20→2b5fe2c`解析出 `46fe548→2b634dc`。这两个绑定由脚本直接读GOT/虚表并断言，不是仅凭相邻反汇编猜测（`2b63258..270`、`2b632e4..308`、`2b5fc40..464`、`2b5fe2c..e50`）。

worker执行 `2dcb9bc blr x1`调用业务；业务返回后，`2dcb9cc blr x1`调用完成闭包。完成函数 **`2b634dc(x0=sequence,w1=handle)`** 的动作是：

1. 把w1存为栈上4B（`2b634fc`），锁sequence+f8（`2b63500`）。
2. `2b63504..50c`把该4B值压入sequence+a8的`std::deque<uint32_t>`；front游标在sequence+b8，end游标在sequence+d8（`2b634a8..4d8`、`2b635a0..5dc`）。
3. 解锁并 `notify_one(sequence+128)`（`2b63510..528`），然后worker清busy并回收闭包/归还worker（`2dcb9d0..ba04`）。

**精确内部记录为 `LE32(actual_handle)`，没有UIPC目的、type、cmd、status或callback字段。** 例如handle1234编码`34120000`只是编码示例，不是可注入的有效本轮句柄。serial里 `FX3_BOOT_QUEUE_SEND bytes=28 raw=00001500... caller_relative=16f1bb4`（例如corr22065起连续事件）是另外的主循环事件，地址和格式均不等同此完成函数，不能拿这些行凑四项完成。

屏障锁+f8，front==end时在+128无限条件等待（`2b63590..5d4`）；读4B、pop并解锁后才匹配。`2b63600`遇token**0x2000**返回1，这是特殊退出；普通token必须匹配保存的w25/w26/w27/w28之一，匹配后w22从4减1，将句柄回收到free deque+28（mutex+78），直至 `2b63678`看到0并返回w0=0（`2b63628..680`）。不匹配走assert（`2b63684`以后）。

原屏障没有“每个任务done位”去重，只比较任意四句柄，所以重复token理论上也会减计数。**验收必须额外核对四个不同创建句柄各一次，不以四次减计数或PC越过单独判成功**；原回调单次生命周期是正确性前提（`2b63628..648`、`2dcb9bc..ba04`）。调用者 `2b67a70`也未先检查w0，所以只看到其PC不能排除2000特殊退出。

## 运行链最小观测点

全部使用本轮appFw基址B；corr的Has caller可核出B=`7f35297000`（`7f380a71bc−2e101bc`，corr22091）。未来轮必须重新读取ELF映射，不沿用该B。无需为观测改变原指令控制流或投递任何完成消息。

| 目的 | VA / 需读取内容 |
|---|---|
| 绑定四个任务身份 | `B+2b63224`：x0sequence、x1目标对象、x2业务入口、x3调整、w4优先级；返回表中四个PC读取w0并绑定调用时的sequence。reject1000，四句柄须不同 |
| license末尾 | `B+2b62208`看MPR入参；`B+2b62de8`看可选证书；`B+2b62d70`看UPM四个u32入参（x0指向type和sequence+624/628/62c派生值）；`B+2b62438`看到原返回，再要求同句柄completion |
| 区分getfunc未创建/未调度/trace等待 | `B+2b67674`创建、`B+2b67678`句柄；`B+2b60208`入口x0；`B+2dd0cb4`已越过trace；`B+2dec7e4`发送前x0=92840747、x1指8B原请求、w2=8、x3指28B回包槽、w4=28 |
| 原任务自然完成 | `B+2b634dc`读取x0sequence、w1handle；同时记录TID与闭包上下文，必要时在`B+2dcb9c0`读取x19worker、[worker+30]完成闭包+8/+10/+20以绑定身份 |
| 屏障匹配 | `B+2b6353c`读x0,w1..4；`B+2b63628`读w0token、w25..28和w22；`B+2b63648`读减前w22；`B+2b63678`读减后w22，内存[FP+7c]为4B当前token |
| 正常成功 | `B+2b67a70`读w0=0，且已有同一sequence的四个不同句柄创建→自然入队→匹配回收、w22=0完整链；不能2000退出、不能合成完成 |

这些观测点不依赖未知原CP数据，也不需要补发28B boot消息。AP76未完整捕获；续查AP80已有上述创建、回调、四次唯一匹配和返回0回执，已关闭四任务屏障的软件guest证据缺口。

## AP76时点的缺口与最小软件合同（历史）

下表保留首次审计缺口；AP80a/b1/b2四项均已完成并匹配，不再需要为license新增crypt/Option补丁，也不需要伪造屏障完成。最新纳入b2的缺口为实际enum2的0119及后续boot尾段，不能沿用历史表里的“未证”描述当当前结论。

| 项目 | 已有/仍缺 | 最小精确合同与边界 |
|---|---|---|
| license | 六次Has=0已证；原返回/匹配句柄未证 | 原Has返回w0=0，wrapper结果8B=`0100000000000000`；不伪造key/init。若确证阻塞于Option服务，空选项候选须同一次0x418B同步请求内op64=0或7、+8 u64 status0、相应列表清0，并向原sync调用返回；AP只明确消费op0的+16起10B以及op7转换明细。**是否需要该候选未证，不应直接集成。** MPR/UPM仍走原服务/已有合同（`2e8b064/4a4`、`2eacf18`、`2b62208/2b62d70`） |
| getfunc | 未观测325，原因尚未定位 | 只在收到`0d20250308000180`后，保存原source/lease并回精确28B `0d2025131c0001800000000080808080808080808080808080808080`；不能主动推送。80字段及互补回退说明见前节；后置MPR尚需原成功（`2dec778..b48`、`2b60208..96c`） |
| volume | 软件回复提交已证；完成句柄未证 | 已有请求`0d202e030a0001800800`→`0d202e130c00018000000000`；返回后让原回调投递真实句柄（前审计、corr21283；本次`2dcb9bc..9cc`） |
| beep | 26/26+4/4已证；任务回调/匹配未证 | 保留现有33d backing/DMM/ICDT和327/32a精确合同；两命令成功分别`0d2027130c00018000000000`、`0d202a130c00018000000000`；最终循环返回后自然完成，不另造消息（corr21370–22050、`2b61dcc..df4`） |
| 屏障 | 完整四句柄验收仍缺 | 内部4B=`LE32(actual_handle)`，原厂自动入队；最小动作是观测，**没有需要新增的完成wire回复**（`2b634dc..538`、`2b6353c..680`） |

若运行链以后确认需要“无已安装选项”的Option软件后端，候选精确字节可写成：op0响应为 **1048个00字节**；op7响应为 **`0700000000000000`后接1040个00字节**，在本次原同步消息存储上返回0。两条完整hex已在proof `software_minimum`列出；这是限定空列表的软件选择，未冒称原备份内容，也不是当前已定位的修复需求（构造/消费 `2e8b064..0f0`、`2e8b4a4..63c`、`2eacf18..2ead06c`）。UPM电源通知是异步，不添加回包（`2eafca0`）。

AP76原日志仍无法把“license卡在哪”或“325为何尚未到达”收敛为一个确定PC，因为该轮缺少创建/用户栈/内部句柄。续查AP80已经闭合四项完成与屏障正常返回，保留了“六次Has没返回”“后置MPR先挡住325”“28B timer消息就是屏障完成”三种错误推论的排除依据（上述VA与corr行22091–22097、22065起事件）。静态原代码重建、AP80软件guest屏障、菜单首绘、声音和实机是不同验收层级。

## 重建

项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/boot-barrier-remaining/audit_boot_barrier.py
```

退出0重建proof；校验卷UUID后才写本目录JSON，不执行原厂业务代码。可附 `ap|cp|crypt|mpr|option VA:LENGTH` 打印只读反汇编，`string ap VA...`读取字符串。44条关键原指令（原42条加两处十六进制哨兵）、五原图hash、闭包/GOT、能力译码与AP76计数为静态检查；新增45个部署探针原指令、8个0328锚点、AP77–80a任务计数和AP80a全部42条RAM/serial比对。退出0同时断言AP80a/b1/b2四个不同句柄自然完成、count4→0、return0，b1/b2 path3消费、b2 digital消费与实际0119 enum2捕获；不把Python能力译码当guest消费证明，实际消费依据原运行记录。

工具依据：[Capstone官方Python说明](https://www.capstone-engine.org/lang_python.html)、[Arm AAPCS64固定2025Q1版](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)，2026-11-01核对。它们仅支持反汇编API与寄存器ABI；Sony私有协议和流程均由本地原VA推导。复用的只读先例为[四任务/音量/地址](../adf-032e-033d/README.md)、[原iCrypt提供者](../icrypt-missing/README.md)、[完整提示音注册](../adf-beep-regist/README.md)、[文件/DMM/ICDT](../adf-beep-file-dmm/README.md)。
