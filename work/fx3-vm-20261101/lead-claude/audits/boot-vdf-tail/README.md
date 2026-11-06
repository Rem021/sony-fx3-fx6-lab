# sequence_boot：timecode 后至最终 notify 的服务审计

**当前阻塞可补的精确合同是 `0165/0200 → 1165/12B/status=0x590000`：`0d2065110c00018000005900`。** 不是裸 0 的亮度完成器合同，也没有宽高字段。AP78b 的五项 `0142/015a/0145/011b/0160` 都是 no-wait，均被委派到缺失的公共发送器；没有“已得到回复”的证据，也无需为解除本线程等待而给它们补回复。依据：AP `2deb854/2deb8b4/2deb924/2deba14/2debb18`、`2debab0`；CP `1adcda/5c9d3a`；serial **21445–21530**。

**不能承诺补一条 1165 后就能 notify。** 后面还有 HDMI 三类设置（其中 0117 连续五次）、条件 Dataflow pin 拓扑切换、屏障后 ADF 0328、数字水平仪通知，以及第二个面板翻转 worker 的 0119。325 已有模型，但 AP78b 尚未创建该任务。以下完整列出父流程、两个新 worker 和它们的条件依赖；没有证实的后端状态不会被编造成“成功回复”（AP `2b67674..2b681e4`；serial 的 gate16/17/18/22/41 均无样本）。

本次只读原件与既有日志，仅写本目录的 [脚本](audit_boot_vdf_tail.py)、[proof](boot-vdf-tail-proof.json)、本文。没有启动 QEMU、执行原厂业务代码、修改 runtime/STATE/原件、获取运行锁、操作相机或 Git。AP 地址为 appFw.so ELF VA；CP 为 Thumb 加载 VA，文件偏移=VA−`108000`。日志均指 `menu-repair-01/runtime/runs/ap78bboot-537976cc/serial.log`，按原始 **LF** 分行，保留 CR/NUL。

## AP78b 实际请求逐一对齐

timecode 软件回复于行 **21429** 排队，行 **21431** 被原调用者消费；不是仅观察到发送。随后原线程 tid327 的轨迹如下。源 `81cf6189` 是 no-wait main-thread source；`81cf61c0` 是此次同步线程/动态队列，均不可硬编码到后续运行（AP `2de66f4..2de6884`、`2de70a8..2de7320`）。

| 顺序 | AP 构造/发送 VA | 请求、source、serial 行 | 本轮处理和结论 |
|---|---|---|---|
| 1 | `2deb808..854` | 0142/10B `0d2042010a0001800100`，6189；**21445–21447** | `2de66f4` no-wait；内核 Skip747，delegated=1；无已匹配1142，原线程继续 |
| 2 | `2deb868..8b4` | 015a/10B `0d205a010a0001800100`，6189；**21462–21464** | 同上，no-wait；不是0159，现有OSD0159模型不处理它 |
| 3 | `2deb8c8..924` | 0145/24B `0d2045011800018000000001010000008961cf8100000000`，61c0；**21478–21480** | `2de83b4` no-wait；委派，无1145完成记录 |
| 4 | `2debb2c..bba0` | EVF温度 9059000e，Dataflow业务2001/020b/16B，总40B | 静态位于0145和011b之间（`2b67124`）；本轮无可独立绑定完整40B捕获。观察器有去重，不能用缺行宣称未发送，也不能继承 timecode 的回复 |
| 5 | `2deb9b8..ba14` | 011b/10B `0d201b010a0001800308`，61c0；**21494–21496** | no-wait，委派，无111b；后继触摸方向仍发生 |
| 6 | `2eabfd0..2eac044` | TP目的807b002b，op0/16B；**21497** | `osal_snd_msg`返回0/delegated；no-wait，无业务完成证明 |
| 7 | `2debacc..bb18` | 0160/10B `0d2060010a0001800000`，6189；**21512–21514** | no-wait，委派，无1160；不是阻塞点 |
| 8 | `2deba54..bab0` | 0165/10B `0d2065010a0001800200`，61c0；**21515–21530** | `send_and_wait_cmp_i`；原栈 `2de7264←2debab4←2dd06c0←2b67388←2b68374`；Skip747，无1165；未进入getfunc创建 |

前五项不等待的结论来自原调用，而非“未见回复”的负证据。现有 v31 配置只覆盖016a、014c/013d、0147、0161、011a/0159等已审计请求，不覆盖上述五项；`fx3-capid-v31.c:436..471` 和 AP78b `build-receipt.json` 固定这层事实。proof 保存源码hash、全部六份VDF请求栈/邻接委派行，以及所有候选完成头的零计数；零计数受观察器去重限制，不能扩大为无损全局追踪。

## 全部父流程服务及新任务：执行顺序

下表从 timecode 后开始。共同 BB 同步器 `2de70a8` 在 `2de72fc` 设 timeout=`ffffffff`，`2de7300` 接收，`2de7304..314` 固定长度 memcpy，随后释放；没有有限超时、重试或自行校验回复头/实际长度。BB status由 `2de4574` 转换；HDMI由 `2de5720` 转换。表中“fatal”指父流程的原日志/断言路径，不能靠跳分支解除（AP `2b66ba8/2b63bf0`）。

| 顺序、服务 | 调用点→wrapper→构造 | 命令/长度和逐字段来源 | 等待、检查、失败后果 |
|---|---|---|---|
| 黑帧notify | `2b67020→2dd0554→2deb808` | 92840747；200d/0142/10/8001；body=0100，输入常量true | no-wait`2de66f4`，out=0；父失败仅日志后继续（`2b67028..58`）；底层分配/发送错误另有assert |
| OSD mute notify | `2b6708c→2dd0594→2deb868` | 同族015a/10；body0100，常量true | no-wait；父日志后继续（`2b67094/2b67238`） |
| shutter mute | `2b670d8→2dd05d4→2deb8c8` | 0145/24；清零body16B，+11/+12=1，+16u32来自全局`9684068`的main ID；+20=0 | no-wait`2de83b4`；父失败日志后继续（`2b670e0/2b67250`） |
| EVF temp event | `2b67124→2dd0714→2debb2c` | 9059000e；24B Dataflow封套+2001/020b/16/1；业务+8=main ID、+12/+13=1，其余0 | `2e109d0` SendASync，随后释放本次dynamic ID；无接收；父失败日志（`2b6712c`） |
| panel color | `2b67178→2dd0654→2deb9b8` | 011b/10；body selector3、color8，常量8在wrapper检查1..16 | no-wait；非法输入status2，父仍日志后继续（`2b67180`） |
| TP direction | `2b671cc→2ddfb74→2eabfd0` | 807b002b；16B LE32 `[0,16,map(input),0]`；input=sequence+304，表`399ecb0`允许0..4 | `2eace78`只send，无服务回复；send错误转本地status，父非0fatal（`2b671d4`） |
| panel-out notify | `2b67214→2dd06d4→2debacc` | 0160/10，body0000，常量false | no-wait；父仅日志（`2b6721c`） |
| **panel resolution** | `2b67384→2dd0694→2deba54` | **0165/10，body0200，固定值** | **同步−1，12B；+8 status→BB转换；`2b6738c`非0fatal** |
| OSD layout | `2b673e4→2dd0054→2deb504` | 0150/20；model getter`294b8bc`首u32，经`3963648`分支映射body+8=1/2，其余11B=0 | no-wait；父非0fatal（`2b673ec`），但wrapper发送后直接out0 |
| TP sensitivity | `2b6758c→2ddfaf4→2eabcdc` | 807b002b；12B LE32 `[2,12,value]`；sequence+1f8：输入0→2、1→1 | no-wait`2eace78`，无reply；send错误父fatal（`2b67594`） |
| **创建getfunc** | `2b67674→2b63224`，GOT`47a6698→2b60208` | 保存真实返回句柄于FP+64（`2b67678`） | 与以下HDMI链并发；其业务325见下一表；不是人为完成消息 |
| HDMI definitionHD | `2b676a0→2dd1394→2df7b14` | 909a015a；2500/010a/12/1；body00000000，构造器`2df7914` | 同步−1、reply12，+8HDMI状态；父非0fatal（`2b676a8`） |
| HDMI init resolution | `2b67794→2dd1214→2df6ce4` | 909a015a；2500/0101/16/1；body `0000000006050000`，构造器`2df6c98`，**没有宽高值** | 同步−1、reply12；父非0fatal（`2b6779c`） |
| HDMI init frame rate×5 | `2b678dc→2dd1254→2df7188` | 2500/0117/12/1；body=`port,rate,port,rate`，port0..4；rate来自表`3917900`的LE32 `[0,0,17,17,0]`低byte；若Backup`02cf1493`一字节==7则五次均7（`2ec1c90`、`2b678c4/2b67c28`） | **五次串行同步−1**，每次reply12，非0fatal（`2b678e4→2b67c30`）；本轮backup值未捕获 |
| change_mode | `2b67a44→2de1f84→2ebe9c0` | 输入来自sequence+1c4/+1c8/+28c/+600/+620，+0c=0；选择pin拓扑表后比较50条旧状态`9ab0d70` | 有条件Dataflow同步，详见后节；不能把此函数当纯本地写值；父未直接检查out状态（`2b67a48`） |
| **四任务屏障** | `2b67a6c→2b6353c` | w1..4来自FP+6c/+64/+68/+70，四个真实句柄 | 本地CV无限等待；4B自然完成token匹配回收；token2000特殊退出，非普通成功；**无UIPC回复可补** |
| ADF set path | `2b67aa0→2dd1014→2dee6f0` | 92840747；200d/0328/10/8001；sequence+1e4和+1ec转换pathbyte0/1/3，padding0（`2dee728..754/7bc`） | 同步−1、reply12；BB status；父非0fatal（`2b67aa8`） |
| 条件ADF sysrequest | `2b67dd4→2dd1794→2df5de0` | 若`2b5fea4(sequence+208..228)`为真且+1f0==0；0329/16；+8=1、+9=0、+10=model`2946508+791`、+11=0、+12u32=0；**输入syncflag被`2b67dbc`清0** | **本次no-wait**`2df5ecc→2de66f4`，增加本地sound请求计数；父失败仅日志。wrapper另有同步分支，但本调用不走，不能补1329 |
| digital level notify | `2b67b2c→2dd2194→2df2f60` | 912f0335；24B LE32 op3，后20B零；true输入选择3，false才是4 | 同步−1、reply24；**wrapper在`2df2fc0`读输入槽+16，不是回复槽+16**；父非0fatal（`2b67b34`）；仍不能因初始0而省略reply |
| key rollquad subscribe | `2b67b70→2dd4534→2e1407c` | 91170319；4B=`64800501`，位域为8064/05/01（`2e140b0..c4`） | no-wait；send错误转换后父fatal（`2b67b78`） |
| video light mode | `2b67ee8→2dd6b54→2e38cb0` | 90030001；imaging type5/cmd4051/12B，id=sequence+1c0，payload4B=0 | no-wait；父失败仅日志（`2b67ef0`） |
| hotshoe video light | `2b67f34→2dd6b94→2e38c38` | 同目的，cmd40c5/12B，id同上、payload0 | no-wait；父失败仅日志（`2b67f3c`） |
| eyeAF | `2b67f6c→2dd6e94→2e38480` | cmd4102/12B，id同上；输入mode0转body首byte1，其余0 | no-wait；父失败仅日志（`2b67f74`） |
| face regardless menu | `2b67fac→2dd6ed4→2e38358` | cmd40ed/12B；id同上；输入mode0转body首byte1 | no-wait；父失败仅日志（`2b67fb4`），此处日志仍写EYE_AF不能据此合并两命令 |
| 条件exposure bias | `2b6807c→2dd5a14→2e3c5e8` | 当sequence+1fc==1；cmd4048/12B；id=+1c0，bias参数20/+200经`2e18b6c`转换 | no-wait；父失败仅日志（`2b68084`） |
| **创建panel reverse任务** | `2b680c0→2b63224`，GOT`47c5b68→2b5fc68` | 真实句柄保存w24（`2b680c4`） | 与下项DMM并发，0119见下节；末尾另有单句柄屏障，**不是之前四任务的一项** |
| DMM get unit size | `2b680e4→2dda534→2e4fecc` | 9061003c；40B，u16op18、+4u32=`00050b58`，其他零；CPflag=1 | 仅send0才在`2e5005c`timeout−1接收；reply+2 signed16负数为错误，否则+16u32单位大小。当前v31远端DMM只接受20..23/2a，**op18立即−1024返回，没进入接收**；父仅日志，outsize0。禁止猜单位大小补成功 |
| AF frame size info | `2b6818c→2dd81d4→2e31cd8` | 90030001；type5/cmd4139/184B，id=+1c0，body176B从全局`9684e20`复制 | no-wait，父无紧邻结果检查；不能捏造AF几何 |
| 条件dictionary observe | `2b681b8→2de2e04→2de4394` | 只有`16f0ea0!=0`调用；实际实现`str wzr,[x1];ret` | **本地stub，无服务请求，无回复** |
| **等panel reverse完成** | `2b681e4→2b63718` | 同一sequence、w24真实句柄 | 本地CV等待；只能业务119返回后由原worker回调自然完成 |
| run_i返回→notify | `2b68370→2b638b8`返回后，`2b6838c→2aa1668` | sequence+1b8本地CV；此前若feature71真，`2b68384→2b45378`尝试mount`/dev/nflasha30`到`/usr/data/lut` | mount是本地文件系统操作，无VDF完成包。**不得主动调用notify/造token**；AP78b gate41=0 |

所有 imaging 行都以 x4=0 进入 `2e2fb90`；在 `2e2fdd0` 的 `cbz x22,2e2fe00` 跳过future接收，source固定80020002。它们虽分配future对象，却不等待业务完成；不能因看到future构造便把它们列为同步。内部发送错误仍可能assert（`2e2fd3c..dd0`）。

`2b68280..2b6832c` 是 run_i 更早分支的尾置代码，回跳`2b640b0`，不是从timecode成功路径顺序落入的后继；proof仍保留该区域原字节/调用清单，不把其中`2dddd74`误加为timecode后的无条件请求（`2b681e8`直接跳`2b63c0c`返回）。

## 0165：旧 VDF、状态域与640×480的关系

两级表由脚本直接读取，不凭相邻代码猜测：wire槽`1acad2→1acea8`产生internal a7；internal槽`1ab7b6→1abc84`调用`1b58b4`。它构造旧 **2001/0118/12/1**，body=`02000000`；selector取AP+8、size enum取AP+9，`1b592a..5956`仅对size≥3打诊断。发送到9059000e（`1b5992..59a4`）。

RTTI `VdfDisplayCmdSetPanelResolution`=`b3d260`，typeinfo=`b7e1e0`，vtable=`b7e1c8`，ID/Activate/Execute槽分别`5f4823/5f4833/5f4873`。Activate检查selector bit1，不满足回旧1118/status1（`5f4842..485c`）；Execute要求size<3（`5f488a..88e`），以`[2,size]`调用`60c5b6`，**先产生1118/status，再在status0时写缓存**（`5f48a0..c4`）。subsystem+164对应`60f17c`，selector2写valid/enum至状态+186/+187；并非写宽高。

`60c5b6`先分派control descriptor(type2,op5,len2)，再经`5df0d6`构造64B控制项：长度40hex、+3c两字节0200，调用`1c77dc`后自身返回0。这个分支能给软件接受结果，**不证明panel扫描器已换分辨率**（`60c5b6..610`、`5df0d6..10c`）。

旧1118回到BB后，`1adbd4`识别2001，`1adcc4`取旧+8 status，`1adcda/1adcde` **OR 590000**；原reply分派`1ac752..758`到`5c9d3a`。该完成器**不归零**，直接复制到AP+8（`5c9d7a`），完整格式：

| 偏移 | 字节 | 含义 |
|---:|---|---|
| 0..1 | `0d20` | type200d |
| 2..3 | `6511` | cmd1165 |
| 4..5 | `0c00` | 长度12 |
| 6..7 | `0180` | flags8001 |
| 8..11 | `00005900` | LE32 00590000，原显示域成功 |

AP `2debab4`读取+8，`2de46c4..cc`明确把590000转本地0；裸0也被`2de45c4`接受，但这是AP宽松性，**本审计选择保真590000**。亮度011a及翻转0119的完成器另有590000→0归一化；不可把其reply照搬到0165（CP `1ae8cc`、`1aecb0..b6`）。

既有016a是**查询几何**，软件profile回复18B `0d206a11120001808002e0018002e0010101`，两个LE16宽高分别640/480，末两byte aspect1/1；AP78b行 **21188** 已提交。0165是**设置enum**，本请求selector2/size0，不返回几何；原枚举0到底对应哪种物理像素布局仍未证实。故无需、也不能在1165填640×480；最小软件合同保留enum0、保持现有640×480 surface，记录`pending_hardware=true`，不声称enum0已被证明等于640×480（AP `2debaa0..a4`；CP `60f17c`；现有`fx3-display-info.c`）。

最小可接入合同限定目的92840747、完整10B **`0d2065010a0001800200`**、本次原source、已启用software-640x480 profile。保存selector2/enum0的独立shadow；一次分配12B回本source，metadata source92840747；只有原send接受后才提交valid/cache，再由原调用者释放该reply。分配/发送失败回滚shadow、释放自己的reply，保留request所有权；重复pointer、并发未完成lease、错误source、其他header/length/selector/size/padding都拒绝。脚本只验证纯软件状态合同及七个拒绝例，没有运行或实现传输拦截器。

## 后继同步合同与硬件边界

| 请求 | CP映射/处理与精确完成 | 最小软件选择与拒绝集 |
|---|---|---|
| 325 | **不是VDF**：旧ADF2004/0128，getfunc缓存查询；AP1325/28B，status0、16个80能力byte，完整见下表。CP `1b34a8/1645b4/1b0a80..1064`与[屏障审计](../boot-barrier-remaining/README.md) | 已有v31静音模型；只接受8B精确请求，一次原source回复。80不是“所有AP能力false”，后置MPR必须原样完成，禁止播放能力被虚构 |
| HDMI010a | **不是VDF**：注册`659aba→217bb0→65a08e`，state slot70；inactive=`65c8da`保存desired definition到singleton+e0，回810a/12B/**status1**（`65c918`）。AP `2de578c..798`把0或1均视成功 | 显式disconnected后端可只保存definition0；不得发HPD/输出就绪事件。拒绝非12B/非固定body、active状态、未配对lease。active state slot70另指65ee7c/65f932/660b04，不能泛用inactive逻辑 |
| HDMI0101 | 注册`6599fa→2178e0→659f5e`，**state slot54**；inactive=`65c440`保存5B到singleton+92..96，回8101/12B/status0（`65c488..4a4`） | 固定16B `00250101100001000000000006050000`，保存完整参数0000000006；尾部5是constructor保留字节，不被该CP wrapper的五字节输入消费。无物理输出可安全shadow接受；拒绝其他模式、EDID/active-output承诺 |
| HDMI0117×5 | 注册`659c6c→217f4c→65a202`，state slot80；inactive=`219834`按port0..4保存rate到singleton+a2..a6，回8117/12B/status0（`2198e0..900`） | 只按原端口顺序0..4逐次保存并回复，不合并成一条。实际rate须先抓本轮backup/整包，允许静态表0/17或明确backup7分支；任何其他port/rate/header/重放都拒绝 |
| change_mode pin API | **不是旧VDF**。最多50条旧/新拓扑差异；disconnect=`2ebe12c→2e116e8` business1000/2/24B；getpin=`2e10d78` 1000/0/24B；connect=`2e11138`先查询src与dst，再走producer连接调用。所有发送由Dataflow封套包裹，reply32B：getpin的+8/+12/+16/+20为descriptor、+28为signed状态；connect/disconnect的状态在+24（`2e110e4/2e11814`） | **不能给固定成功包**。必须真实维护软件producer/consumer、队列及buffer归属；本轮未捕获selected表/endpoint/current state，保持拒绝，不把table存在当连接完成。AP `2e10e48..f54/2e117a8..1888`只认可status0与特定负状态范围，返回descriptor不能填0冒充真实pin |
| ADF0328 | bridge `1b1a8c`构造旧2004/**0202**/12/1，body=path&7（`1b1ac2..aca`），目的9058003f；`5ca218`构造AP1328/12B，状态原样复制。旧ADF状态经`1adc88..8e` OR **580000**，成功格式`0d2028130c00018000005800` | **格式已证，成功准入未证**：需静音系统路径真实状态/原完成语义，不能仅收到328就宣称音频路由完成。当前允许path0/1/3的完整动态包尚未捕获；其他path、padding、active音频一律拒绝。旧0202完整内部接收/硬件completion未闭合 |
| digital level op3 | 非VDF、无200d头。CP注册`4c8918..8988`绑定912f0335→`4c8ee0`→`145330`；TBB case3/4都到`14535a→4c8da4`。若对象+0=2且+4=0，返回0（无sensor通知）；否则可能向90a3035b发20B注册请求，状态由`1454a6`写原message+16 | 能保存“订阅请求”而不合成角度数据；**generic callback自动回复/metadata生命周期尚未闭合**。24B `03000000`+20B零仅为有界格式候选，不是可直接集成的原发送器证明。缺少descriptor/状态时拒绝成功；不能伪造IMU水平样本 |
| DMM op18 | 非VDF，AP40B query→reply40B，signed16 status@2、unit bytes@16。当前v31 `dmm_dispatch`主动拒绝18，AP在`2e4ffe8`失败分支不进入接收，父非致命 | **保留−1024，无需新回复**。单位00050b58没有已证软件extent/真实配置；禁止编造大小或借70817/63a单位回答 |
| VDF0119 | wire119→internal24→`1ab894→1b3e74`，旧2001/**0101**/20/1；RTTI`VdfDisplayCmdSetPanelReverse`=`b3d290`。Execute`5f491c..497c`将payload12B排到内部**f02e**，自身不回成功；后续设备reverse完成`6073b8`构造1101，BB `1aeca0..1aed00`把590000归零后回1119/12B | **不能只收到包就回成功**。原链包含deferred device reversal；软件后端至少有明确orientation状态、消费f02e等价队列并使虚拟surface坐标/输入映射一致后，才可以1119/status0。没有该consumer则拒绝/保留pending，不造worker完成。sequence+304实际enum和28B包未捕获，不能默认全零 |

关于no-wait五项的旧VDF映射，两个表和handler同样已读回：0142→internal97/`1aba9e→5cbca6`→旧0311；015a→a1/`1abbbe→5cbe8a`→旧0322；0145→8f/`1ab970→1b4678`→旧0312；011b→1f/`1ab818→1b3d48`→旧0104；0160→a4/`1abc00→5cbf24`→旧011f。这些是通知/订阅或设置请求；当前AP调用不等待结果，**不要主动注入猜测的1142/115a/1145/111b/1160**。可保存已验证payload和source/订阅状态，但不能合成黑帧、shutter、温度、panel-output物理事件（上述VA；serial21445–21530）。

## AP78b之后的同步清单：按程序次序，含精确字节

“可补”只指上述限定的软件合同；“格式候选”不表示已经得到必要状态或可集成。并发worker的实际wire到达可能交错；尤其325与HDMI、119与DMM不能强行规定总到达顺序（`2b67674/2b680c0`）。

| 次序 | 同步请求 | 精确reply（OSAL payload） | 当前处理/动作 |
|---|---|---|---|
| 1 | **VDF0165/10B** | **`0d2065110c00018000005900`**（12B） | 当前真阻塞；captured0200合同可实现shadow+pending，无几何改写 |
| 2a并发 | ADF0325/8B | `0d2025131c0001800000000080808080808080808080808080808080`（28B） | v31已有；仍须原任务/MPR完成回执，无需重复补模型 |
| 2b | HDMI010a/12B | **`00250a810c00010001000000`**（12B，status1） | 新增disconnected definition shadow合同；不要误用status0冒充本inactive原值 |
| 3 | HDMI0101/16B | **`002501810c00010000000000`**（12B） | 新增inactive resolution配置shadow；不发送输出就绪 |
| 4–8 | HDMI0117五包/各12B | **每包**`002517810c00010000000000`（12B） | 每个原请求独立配对；不能只回一次；须观测rate白名单 |
| 9条件 | change_mode pin get/connect/disconnect | **无已证固定reply；禁止给假成功字节** | source/destination/descriptor随50条状态变化；需运行只读抓包和真实软件pin合同，不属于VDF165修复 |
| 10 | 四任务屏障 | **无wire reply**；原内部4B=`LE32(actual_handle)` | 需要四个不同自然完成；不能补28B boot消息 |
| 11 | ADF0328/10B | `0d2028130c00018000005800`（12B） | **仅格式候选**，静音path/backend原完成仍缺，当前不得无条件成功 |
| 12 | digital level op3/24B | `030000000000000000000000000000000000000000000000`（24B） | **仅格式候选**，CP callback reply传输/生命周期待闭合，不得直接作为原CP发送回执 |
| 13a并发 | VDF0119/28B | `0d2019110c00018000000000`（12B） | **仅格式候选**；须真实软件orientation consumer完成后再回，不能提前释放worker屏障 |
| 13b | DMM op18/40B | **不新增成功reply**；沿用当前−1024立即失败 | 不进入接收，outsize0且父日志后继续；未知unit size保持未知 |
| 14 | 单panel-reverse任务屏障 | **无wire reply**，原内部4B句柄 | 与四任务屏障不同；等待它后run_i才可返回到notify |

0329不在此同步清单：本调用syncflag=0；dictionary是本地stub；TP、key、imaging均no-wait（AP构造/分支VA见上表）。

## 未闭合项与后续最小观测

1. **条件pin拓扑与getfunc后置MPR**：本审计已识别它们可能发额外同步请求，未取得本轮selected50条拓扑、provider当前值、MPR请求完整字段/存储状态，无法提供诚实的固定成功字节。不能把它们隐去后声称“全部后续同步回复已齐”。下一轮在`2b67a44`读取完整输入，`2ebe188`读取selected和current各50×24B，记录实际Dataflow目的/封套；getfunc按[前审计](../boot-barrier-remaining/README.md)的MPR链观测（`2b60490/2b60514/2b605ac`）。
2. **ADF0328、digital、0119**：精确完成外形与消费位置已给出，完整后端成功状态/自动回复路由或deferred完成链仍有缺口。硬件动作不能因回复字节可构造而算完成；软件后端可实现自身状态/队列后单独验收（上述CP VA）。
3. **0165 enum0的像素含义**、OSAL底层−1取消语义、全局队列匹配规则未新增证明；保留固定captured请求与完整reply，不利用AP盲拷贝或初值零宽松路径。016a的640×480是显式软件配置，非机身实际LCD测量（serial21188）。
4. AP78b只证明timecode回复被消费及0165后等待。getfunc创建、五项新同步服务、两次任务屏障、notify、GPE首绘/菜单/物理面板均没有本轮通过回执（serial21431、21515–21530；gate零计数）。

## 交叉参考与重建

A7C2公开固定版 [b3d7c1fe/vdf-device.c](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fe/runtime/analysis/device-models/vdf-device.c) 的95–168行同样处理10B/selector2，141–142行回1165并保留raw状态，158–160行注明先control shadow、后reply、后cache，pending_hardware不清；与FX3本次 **0200请求、12B、590000状态域**一致。区别是它放行size输入和自身控制shadow生命周期；本审计只准入FX3捕获的size0，不移植A7C2动态状态/地址，也不借其guest结果充FX3消费回执。来源2026-11-02 UTC只读核对，FX3结论独立由本地VA重建。

在Mac项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/boot-vdf-tail/audit_boot_vdf_tail.py
```

退出0重建proof：固定AP/CP SHA256，核对**55条关键原指令、32个直接调用绑定、1282条父流程指令的全部call/branch、8项两级dispatch、RTTI/GOT/HDMI state vtables、六个捕获请求及其栈、7个拒绝例**。可传`ap:2deba54:78 cp:5c9d3a:52`等参数只打印反汇编。Thumb长区间含literal/TBB数据，proof明确标为可能混合数据并保留raw；`.byte`或表内容的偶然译码不是控制流证据，决定性结论均另有精确地址断言。

工具使用依据为本轮核对的[Capstone官方Python文档](https://www.capstone-engine.org/lang_python.html)与[Arm AAPCS64固定2025Q1](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)；只支持反汇编API和寄存器ABI，不提供Sony私有协议语义。可重建静态proof与软件模型验证，不等同guest消费、完整启动、菜单或实机验收。
