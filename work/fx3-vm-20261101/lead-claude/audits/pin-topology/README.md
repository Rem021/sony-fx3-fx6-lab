# sequence_boot change_mode：pin 拓扑、回复与软件所有权审计

**AP79 已锁定启动表 `appFw+0x9ab1258`，不是猜测默认值。** 捕获输入 `010000000000000001000000000000000100000000000000` 对应 mode=1、option=0、proxy=1、remote=false、network=1、stream=false；经 `2b67a44→2de1f84→2ebe9c0→2ebeb30` 选择该表，`2ebeb34` 置检查已有连接标志为1。与旧表 `9ab0d70` 比较有 **14 条差异：3 条“不要求连接”，11 条连接；初次没有 disconnect**。旧表每条的 source 有效，state/destination 全零，不能说整张旧表1200B全零（原静态构造 `1694028..1697260`、AP79 serial **21603、21605–21617**）。

**仅首个 GET 已实捕，后续包仍是条件推导。** 原线程 tid327 首次查询 row7 的 InfraBB YC OUT1，目的 **`9284074a`**，48B Dataflow 请求，经 `2e11438→2e10d78→2e109d0` 发送后无限等待；没有 pin reply 被消费。本审计给出独立软件模型全端点冷启动成功时的 **22 GET +11 REQUEST_CONNECT=33 包**与每包完整32B业务回复，不能把它们当作AP79已发送/已通过（AP79 **21619–21635**；AP `2e10cc4`、`2e11644..688`）。

只读原件和既有捕获；仅写本目录的 [audit_pin_topology.py](audit_pin_topology.py)、[pin-topology-proof.json](pin-topology-proof.json)、本文。未启动QEMU，未执行guest代码、修改原件/runtime/STATE/锁/Git、操作相机。下文AP地址是appFw ELF VA，CP地址是Thumb加载VA（offset=VA−`108000`），DF地址属于 `dataflowInfraFramework.so`。日志行按原始LF计数，保留CR；本次固定日志SHA `01009cc3a8fe5e8c253114c57e0fe6cc13b167511c74996fdd6acd9d9c4ac72f`。

## 1. 表的生产、选择和初值

启动输入的来源逐字段为：

| input偏移 | sequence来源 / 构造 | AP79值 | AP VA |
|---:|---|---:|---|
| +0 u32 | `sequence+1c4` system_mode | 1 | `2b67a14..20` |
| +4 u32 | `sequence+1c8` system_mode_option | 0 | `2b67a24..2c` |
| +8 u32 | `sequence+28c` proxy_recording | 1 | `2b67a30..34` |
| +c byte | is_remote_shooting_enabled，原调用明确写false | 0 | `2b67a10` |
| +10 u32 | `sequence+600` network_streaming_mode | 1 | `2b67a38..3c` |
| +14 byte | `sequence+620 == 1` 的比较结果 | 0 | `2b679e0..9fc`、`2b67a28` |

最后一项只能证明原字段 **不等于1**，不能反推`sequence+620`必为0；24B捕获中其余padding字节为0。AP78b尚未到此调用，本文不从AP78b零样本推导这些值（AP79 serial21603；前审计AP78b阻塞于0165）。

`.init_array+`槽 **`3d20828→1694028`** 是无分支的原静态构造器；3215条指令仅有整数赋值、load/store及ret。脚本解析这些赋值，重建12张候选表与旧表，共650条，不调用原函数、不模拟Sony服务；两组不同入口寄存器种子得到同一全局结果。每个字段保留写入VA，完整原字节/反汇编在proof `constructor.instructions`。特别是 `1696f5c..1697258` 填入旧表50个source、清状态和destination，ELF `.bss` 的初始全零只是构造前状态。

记录格式为 **50×24B**：`+0:u64 source_descriptor*`、`+8:u32 topology_state`、`+12:u32 padding`、`+16:u64 destination_descriptor*`。AP拓扑state **0=断开，1=连接，2=不要求**；descriptor是16B `[provider_OSAL_ID, type, direction, index]` 四个u32，**不是缓冲地址或DMM句柄**。类型由原 `_INFRA_PIN_ATOM` 名表 `4117648` 与构造值对应：YC0、OSD1、AUDIO2、SYSND3、HDMIVIDEO4、HDMIAUDIO5、DRAWINFO6、RAW8；direction1=IN、2=OUT、3=INOUT。验证器同时要求source非空、state1时destination非空、OUT→IN或INOUT→INOUT（`2ebed60..2ebefbc`；本审计proof保留的生产写VA与原名表绑定）。

`2ebeaf4..2ebeb08` 使用 `39a4708` 的16个signed byte；option=0才再按mode查 `39a4718`。不是所有0..15都走同一mode分派：

| 选择条件 | 表VA / 标志 | 原选择VA |
|---|---|---|
| option0、mode0 | `9ab1708` /0，全断开 | `2ebec18..3c` |
| option0、mode1（本次） | **`9ab1258` /1** | `2ebeb30..3c` |
| option0、mode2 | `9ab2518` /0 | mode jump→`2ebec6c` |
| option0、mode3、proxy=0 | `9ab3a08` /0 | `2ebeb78..8c` |
| option0、mode3、proxy≠0、network=0 | `9ab41b8` /0 | `2ebeb90..a4` |
| option0、mode3、proxy≠0、network≠0 | `9ab2068` /0 | `2ebeba8..b0` |
| option0、mode4（原日志MODE_PLAY_STILL） | `9ab2e78` /0 | `2ebebb4..d8` |
| option0、mode5（MODE_PLAY_MOVIE_STREAM）、stream=false/true | `9ab29c8` / `9ab4b18`，均0 | `2ebebdc..2ebec14` |
| option1/2/7/8/10/11/12 | `9ab1bb8` /0 | `2ebec5c..68` |
| option4/6 | `9ab2518` /0 | `2ebec6c..78` |
| option5 | `9ab3328` /0 | `2ebec7c..88` |
| option3/9/13/15 | 跳到unlock尾部，**不切表、不写current mode** | jump→`2ebeb50` |
| option14或>15；option0且mode>5 | 记invalid日志后退出，不切表 | `2ebec8c` / `2ebec40` |

remote字段在本函数只打印，不影响分表；proxy/network/stream在mode1本次也不影响选择（`2ebea9c..ad8`、`2ebeb0c..40`）。不能把下一轮不同mode的包纳入本轮白名单。

独立RAM `runtime/runs/ap79tail-17293cc1/ui-gate-counters.bin`：`+7800`保存24B输入，`+8000`头含magic `31504f5447583346`、selected/current地址、tid327、flags1、差异数14，`+8040/+84f0`保存selected/current各1200B。ASLR基址由current−`9ab0d70`计算，**全部100条的两个指针归一化后逐字节与静态构造结果一致**；不是只比较serial前12条。proof `AP79_full_table_readback` 保存原字节与归一化字节，RAM SHA `f42b565ea4a69d103e482712ffc02543d471306535a54e4a388895c5feefcef7`。

## 2. 精确差异与发包顺序

初次old的state均0，因此第一遍50条不会disconnect；new state2的1/4/5只表示“不要求”，不会发GET或CONNECT，也不会把old state0改成2（`2ebe1d4..314`、`2ebe344..36c`）。其余11条按索引递增：先GET source，再GET destination；两个GET成功且descriptor与请求逐字段一致后，若两个CP connection_state均0则直接视为已连，否则REQUEST_CONNECT。这里 **CP pin state 0=已连、1=断开、2=转换中，和AP topology state不是同一个枚举**，不能对空后端返回state0（`2e106ec..73c`、`2e11438/2e11564`、`2e11644..688`；CP `5ba9c8..d6`）。

下面tuple固定顺序为 `[owner,type,direction,index]`，十进制小字段，owner为hex；完整wire字节在后面的逐包表及proof。表中顺序为**已声明的空软件图、每个请求成功、没有并发变化**条件下的AP业务包顺序；真实AP79仅到序号1。

| row / GET源→GET目的→连接序号 | source | destination | 记录/生产VA |
|---|---|---|---|
| 1 / 不发包；state2 | `[0x90050004, 0, 2, 1]` | `无` | `0x9ab1270`；`169481c, 1694824, 169487c` |
| 4 / 不发包；state2 | `[0x90050004, 8, 2, 0]` | `无` | `0x9ab12b8`；`1694828, 1694860, 1694890` |
| 5 / 不发包；state2 | `[0x90050004, 3, 2, 0]` | `无` | `0x9ab12d0`；`169482c, 1694874, 1694894` |
| 7 / 1→2→3 | `[0x9284074a, 0, 2, 1]` | `[0x905a0048, 0, 1, 1]` | `0x9ab1300`；`1694844, 1694854, 1694870` |
| 10 / 4→5→6 | `[0x9284074a, 8, 2, 0]` | `[0x905a0048, 8, 1, 0]` | `0x9ab1348`；`16948b0, 16948b4, 16948c0` |
| 13 / 7→8→9 | `[0x905a0048, 0, 2, 2]` | `[0x90590818, 0, 1, 0]` | `0x9ab1390`；`16948bc, 16948c8, 16948d4` |
| 14 / 10→11→12 | `[0x905a0048, 0, 2, 3]` | `[0x90590818, 0, 1, 1]` | `0x9ab13a8`；`16948e0, 16948e4, 16948f0` |
| 18 / 13→14→15 | `[0x905a0048, 8, 2, 0]` | `[0x90590818, 8, 1, 0]` | `0x9ab1408`；`1694930, 1694934, 1694940` |
| 20 / 16→17→18 | `[0x90590818, 0, 2, 1]` | `[0x91670464, 0, 1, 4]` | `0x9ab1438`；`169493c, 1694948, 1694958` |
| 21 / 19→20→21 | `[0x90590818, 0, 2, 2]` | `[0x9058003f, 0, 1, 0]` | `0x9ab1450`；`1694954, 1694964, 1694970` |
| 22 / 22→23→24 | `[0x90590818, 6, 2, 0]` | `[0x928d0783, 6, 1, 0]` | `0x9ab1468`；`1694960, 169497c, 1694988` |
| 23 / 25→26→27 | `[0x90590818, 4, 2, 0]` | `[0x909a015a, 4, 1, 0]` | `0x9ab1480`；`169496c, 1694994, 16949a0` |
| 24 / 28→29→30 | `[0x90590818, 1, 3, 0]` | `[0x9080003b, 1, 3, 0]` | `0x9ab1498`；`1694978, 16949a8, 16949b4` |
| 29 / 31→32→33 | `[0x9058003f, 5, 2, 0]` | `[0x909a015a, 5, 1, 0]` | `0x9ab1510`；`16949c8, 16949cc, 16949e4` |

每个目标provider分别GET；REQUEST_CONNECT发给source owner，不发给destination。GET请求业务24B=`LE16[1000,0,24,2] + LE32[type,dir,index,0]`；REQUEST_CONNECT业务40B=`LE16[1000,1,40,2] + LE32[src.type,src.dir,src.index,src.owner,dst.type,dst.dir,dst.index,dst.owner]`；若后续已有连接需要断开，则是24B的cmd2，body同GET（AP `2e10da0..de8`、`2e10fc8..2e11010`、`2e11710..74c`）。

首包实捕OSAL payload：

```text
c061cf81a0a0a0a001003000180000003000000000000000001000001800020000000000020000000100000000000000
```

后续第2–33包的整包padding、未来动态reply_id没有捕获；不得照搬第一包source `81cf61c0`。proof逐包给出业务请求与56B规范软件回复，外层保留字段选择清零。

## 3. 目的服务与CP真实处理

**`9284074a` 与 `90590818` 是两个不同的pin管理服务，不是同一VDF队列的别名。** `9059000e` 又是另一条VDF控制服务；timecode的36B回包不能移植到pin的56B封套（CP InfraBB `1bcace..1bcafc`；VDF PinMem `608112..11c`；前审计控制服务 `5f1126`）。

| provider SID | 管理者、在本表中的角色 | CP原代码证据 |
|---|---|---|
| `9284074a` | **InfraBB PinMgrTask**，YC/RAW producer；首个查询实际目标 | `1bcaf2..1bcb1a` 以本SID无限Receive；`1bcff4..1bd0dc`分type1000与cmd0/1/2；21个对象指针表`efa624`→`11cbe1c`起。GET `1bd2cc..34c`找完整type/dir/index，`1bd6aa..71c`填状态、owner与回复；REQUEST_CONNECT `1bd770..778→5ba9f4`；REQUEST_DISCONNECT `1bd5bc..5c4→5baeb0` |
| `905a0048` | **VEF**，接InfraBB YC/RAW，再向VDF输出 | `62d4b0..4c6`绑定SID；RTTI `b40510`/vtable`ba300c+14→1fb734`为SystemCmdPinGet，GET `1fb734..7c6`；`1fb7f4..8ee→5ba9f4`处理请求连接；`62dd5e/62dd8e/62ddbe`返回cmd0/1/2 |
| `90590818` | **VDF PinMemMgr**，YC/RAW输入，YC/DRAWINFO/HDMIVIDEO/OSD输出 | 构造 `60810a..148`把SID传基类；`608316..35e`查13个pin；GET RTTI`b3f000`、vtable`b80cdc+14→1e71d0`；请求连接/断开`b80d08/b80d34+14→1e72ac/1e7400`；它们调用同一DataflowInfraPin状态机 |
| `91670464` | **NS_SCALAR_INFRA/SFRS** YC consumer，index4 | `4e0f68..86`和`ac83c6..3e4`绑定SID；RTTI`b54170`、vtable`d1516c+14→4ead2c`；GET `4ead2c..dc8`，响应 `ac71a8→ac838a` |
| `9058003f` | **ADF pin管理者**，YC consumer、HDMIAUDIO producer | `5aa2f2..346`分cmd0/1/2；GET `5aa350..41a`查10个pin，`5aa3f0..402`写源SID；请求连接/断开分别`180d78`/`180f9c`，进入通用pin控制器；该服务不等于BB/ADF控制`92840747` |
| `928d0783` | **DrawInfoPinMgr线程 / DrawInfoPinCtrl**，DRAWINFO consumer | `151138..160`按SID接收，`56e866..8c2`逐业务分派；`56dc44..76`安装`b65900`（RTTI为`15DrawInfoPinCtrl`）；GET `56dcee..ddba`，匹配两对象，`56dd8e..dda2`设置回复source |
| `909a015a` | **HDMI PinHandler**，HDMIVIDEO与HDMIAUDIO consumer | `218814`入口；`21888e..90→218a6a`分GET，`218cfc..d4a`按完整type4/5选择对象，`65a554..5de`构造32B业务回复；请求连接 `2188c6→5ba9f4`；配置2500与pin1000须分别分派 |
| `9080003b` | **CP FBM/GPE OsdPinIF**，双向OSD metadata/control pin | GET `4ace28..ee4`固定self `[type1,dir3,index0,owner9080003b]`，从DataflowInfraPin读取状态；`4acf82→5baeb0`请求断开；`4ad2fe→5ba9f4`请求连接；不是“把OSD pin当帧缓冲地址” |

native CP查pin的策略并不完全一致：InfraBB比完整u32三元组；VDF/VEF/SFRS部分入口按低byte查对象，HDMI按完整type选对象，OSD返回固定own key（上述GET VA）。**本轮软件白名单只接受捕获/表中完整canonical key，拒绝高位别名**，不把原宽松查找变成更多获授权的软件对象。

`1000/1`是 **REQUEST_CONNECT**；原CP会继续进行type1000的内部 `0100/8100` 连接握手，而非收到AP请求就完成。通用对象布局为 `+8 peer[4]`、`+18 self[4]`、`+28 state`、`+2c/+30 requestor`、`+34 transition kind`，对象总长38hex；原构造 `5ba9ac..9e0`将state初始化为1（断开），peer设无效值。`5ba9f4`检验当前状态和peer，进入state2并暂存requestor、发内部控制；`5badd0`收到完成后构造8001给原requestor，`5baeb0/5bb1a2`是断开对应链。缺少对端确认、队列或资源状态，不能立即给8001成功（`5baa06..5bac2e`、`5badd0..5baeac`、`5baeb0..5bb00e`、`5bb1a2..27e`）。

## 4. 32B逐字段回复与Dataflow封套

以下偏移以**业务体**起点计算；OSAL实际payload是 **24+32=56B**。header为四个LE16：type1000、cmd8000/8001/8002、length32、flags2。request也有24B业务体，但完整OSAL请求是48B；REQUEST_CONNECT的业务体40B，完整64B（AP `2e10d78/2e10f98/2e116e8`；CP `1bd2de..30c`、`5badf0..5bae42`、`5bb1c0..222`）。

| 业务偏移 | GET 8000 | REQUEST_CONNECT 8001 / REQUEST_DISCONNECT 8002 |
|---:|---|---|
| 0..7 | `0010008020000200` | `0010018020000200` / `0010028020000200` |
| 8 u32 | self.type | self.type |
| 12 u32 | self.direction | self.direction |
| 16 u32 | self.index | self.index |
| **20 u32** | **CP connection_state：0已连、1断开、2转换中** | **self.provider_OSAL_ID** |
| **24 u32 / i32** | **self.provider_OSAL_ID** | **signed status** |
| **28 i32 / u32** | **signed status** | reserved=0 |

GET中descriptor按业务`+8/+12/+16/+24`收集后重排回AP的 `[owner,type,dir,index]`；`+20`另存给检查已有连接函数。它不是32B中的连续16B descriptor，也没有peer descriptor、queue handle或buffer handle（AP `2e10ee4..f0c`；CP InfraBB `1bd6ba..6e4`、VDF `1e71fe..7258`、HDMI `65a57e..5a2`）。8001/8002中的descriptor才是连续业务`+8..23`，CP从self复制16B后把完成signed status放`+24`（`5bae34..42`、`5bb212..222`）。

以首个已声明、断开状态的InfraBB YC OUT1软件对象为例，GET业务32B：

```text
0010008020000200000000000200000001000000010000004a07849200000000
```

它依次是 header、YC0、OUT2、index1、**disconnected1**、owner9284074a、status0。若把 `+20`写0来“清零回成功”，AP会把它解释为**已经连接**，可能直接跳过真实connect（`2e11644..678`）。

回复外层：`+4:u32 magic=a0a0a0a0`、`+8:u16 count=1`、`+10:u16 total_length=56`、`+12:u32 read_cursor=24`、`+16:u32 write_cursor=56`、`+20:u32 reserved`；原builder未显式初始化最后保留字段，软件选择0，不能称其为原机捕获值（DF `32278..2a0/32368..3cc`；CP `5ba420..436`）。**`+0 reply_id`并非一律0**：InfraBB GET原路径 `1bd6fc..70a→5ba598/5ba5e6` 都传9284074a，OSD GET `4ace54..58→5ba598`传9080003b；因此这两类GET回复outer+0=provider SID。其余本表已审GET回复与通用8001/8002构造不设置ReplyId，outer+0保持0（VDF `60ed16→61103a/611056`，VEF `6293c0→62d39c`，Scalar `ac71a8→ac838a`，ADF `5aa3b2..402`，DrawInfo `56dd50..dda2`，HDMI `65a5ae..5ca`）。

OSAL metadata source始终填**实际provider SID**，投递目的取**本次请求outer+0 reply_id**。响应outer+0不是投递目的；不能把provider SID拿来替代AP动态reply queue。首个GET的规范56B软件回复为：

```text
4a078492a0a0a0a0010038001800000038000000000000000010008020000200000000000200000001000000010000004a07849200000000
```

本次动态queue `81cf61c0`仅是捕获样值；每个edge的动态ID在`2ebe3fc/2ebe418`申请/释放，多个GET/CONNECT按序共享该edge有效期，不能跨运行/跨edge保存旧queue（AP `2ebe3f4..418`、`2e109d0`）。

## 5. 无摄像/无视频输出VM的最小诚实模型

这里是**设计判断和独立Python参照模型**，不是“已恢复CP”。依照原对象/握手合同（上一节VA），最小可行模型需要真实维护以下软件事实：

1. **对象登记和owner。** 用完整key `[provider,type,dir,index]`登记本次需要的22个端点，每个owner有一个明确的软件接收/发送身份。只登记实际由后端承担的对象；不因selected表存在就自动声称硬件producer可用。每个注册对象保存self、peer、CP state、generation、in-flight资源集合；source/destination的producer/consumer方向与type必须匹配。OSD为INOUT↔INOUT，另有双方metadata队列，不可硬塞为普通YC单向pin。原依据：`5ba9ac..9e0`、`18f408..452`、AP`2ebee88..2ebef88`。
2. **GET从登记状态产生。** 已登记对象返回自己的完整descriptor与当前state，冷启动应为state1/status0；它不创建edge、不创建像素、不给peer或buffer句柄。不存在的pin/provider不能构造“同请求descriptor+status0”当作存在。原GET失败码有provider差别：InfraBB找不到对象回−32（`1bd33c..34c`），VDF/VEF/Scalar未知对象用0000ffff（`1e723e`、`1fb790`、`4ead90`），ADF/DrawInfo用e002（`5aa39e`、`56dd3c`）；本参照模型统一选择有原依据且AP安全识别为错误的−32，仅为软件错误策略，未宣称逐服务重现这些原错误码。
3. **REQUEST_CONNECT是有条件提交。** 先验证两个key确实由本后端管理、type和方向兼容、当前peer无冲突、无transition/故障；为两端创建有界、**初始为空**的软件消息队列，建立双向peer引用，然后原子提交state0，最后给source owner的8001/status0。同一edge重试可幂等确认；已被其他edge占用返回−25、转换中返回−24、type不匹配−23、direction不匹配−22、缺对象返回−32；失败保持原图。对应错误常数/条件在CP `5bab0a`、`5baba6`、`5bb0f0`、`18f420/440`；原CP内部握手若被替换，只能在两个端点均由同一软件后端真实管理时用这一软件事务，不能伪造来自未建模CP对端的0100/8100。
4. **队列、buffer和descriptor分开。** 连接的metadata/控制队列可以为空；不得因连接成功创建假RAW/YC帧、HDMI ready、提示音、timer或GPE通知。软件生成的OSD buffer必须来自另行验收的GPE/DMM分配器，登记allocation domain、容量、producer、当前consumer、引用计数/generation；每次入队转移或共享lease，消费或取消后恰好归还一次。pin descriptor的owner SID不授予任意guest物理地址的所有权。连接合同中不含buffer句柄（上述24/40/32B原构造），所以不能从本次审计推导图像buffer大小或DMA有效性。
5. **REQUEST_DISCONNECT先收回所有权。** 先停止新提交；等待已有metadata/buffer lease消费或显式取消后归还，清双方peer与队列、变为state1，再回8002/status0。尚有in-flight资源时返回−24或继续真实deferred等待，不能先释放buffer再成功；已经断开可回−26，不重复释放；未知对象−32。native状态检查/延期与requestor保存见`5baeb0..5bb00e`，完成见`5bb1a2..27e`。本次启动无任何disconnect包，proof仍检验这类回复与资源拒绝规则。
6. **运输lease不能代替业务完成。** 只接受目的SID、完整Dataflow边界、type/cmd/长度/flags、完整canonical key和合法reply queue；为每条已接管请求分配独立56B回复，设置source后调用原OSAL发送。发送失败时释放己方仍拥有的reply并回滚未提交状态；成功排队后请求/回复分别按原分配域释放。用reply指针、queue、sender线程、序号、对象generation追踪租约；只有原waiter自然消费并free成功才记“已消费”，入队或另一线程free不能充这个证据。同样raw的重复GET仍应读实时状态，不能用永久去重屏蔽。参照来源见下一节；本Python模型只验证业务/资源所有权，不实现OSAL运输lease。

上述连接成功只表示**空软件拓扑已提交**。所有模型对象保持 `pending_hardware=true`、`physical_output=false`；没有摄像producer的真实帧、无物理HDMI/面板输出。若某个端点后端尚不存在，应返回准确错误并保留缺口，不能仅为让boot往后跑而生成固定成功包。AP后续是否需要empty-queue以外的OSD事件、buffer交接，必须另取运行证据（原控制/完成链VA如上，AP79仅首个GET）。

## 6. AP失败是否致命

**业务失败一般不致命；缺回复会无限卡住；假的成功descriptor可致命。** 三种情况必须分别处理：

| 情形 | AP原行为 | VA |
|---|---|---|
| 没有回复 | SendASync可以返回0后在RecvASync timeout=−1永久等；不会走错误日志后继续 | `2e10cc4`；AP79 `21619–21635` |
| GET status=0 | 拷出descriptor和connection_state；随后全4字段比较 | `2e10eb4..f10`、`2e114a0..4b0` |
| GET status=−26/−25/−24 | **虽打GetPinErr not OK日志，仍保留接收成功的local0并拷出descriptor/state**，不能把它们当通用拒绝码，不能配垃圾descriptor | `2e10eb8..ec8→2e10f14..f50→2e10ee4` |
| GET其它非零status（例如−32、ffff、e002）或transport返回错误 | local1，当前edge停止后续GET/CONNECT；拓扑层记录error并继续下一条，不提交该edge shadow | `2e10f54..f94`、`2e1143c..484`、`2ebe450→2ebe700..764` |
| REQUEST_CONNECT任意非零status | local1，记录error，old shadow不更新，继续其余edge；不是SEQUENCE FATAL ERROR | `2e110e4..2e11134`、`2ebe628..694→2ebe760..764` |
| REQUEST_DISCONNECT 任意业务status | −26..−24打not OK仍local0；其它非零也在`2e118c0`显式置local0。原shadow可能继续更新，不能据其成功日志认定已断开 | `2e11814..8c8`、`2ebe2e8..300` |
| GET声称成功但descriptor任一字段不符；或非法拓扑state | 原assert日志后走 `lib::assert::notify_model_system_error`，最终`__assert_fail` | `2e114b4..53c` / `2e115b8..640`、`2ebe1f0..28c`；`2ebf420→PLT1594060=__assert_fail` |

`change_mode`父调用后没有直接检查out状态，甚至无条件写“Success change_mode”；这句不能充11条连接都成功的回执（`2b67a44..5c`）。check_and_connect只看双方state是否0，**不比较它们实际peer是否互为对端**，所以两个错误连接的对象都报state0会被AP跳过；软件图必须如实记录真实peer，不能利用此AP宽松性（`2e11644..678`）。

## 7. A7C2固定版参考、一致与差异

本轮2026-11-02 UTC只读核对固定提交 `b3d7c1fed349f1d918acc4259f1d2b3a7c52a500` 的 [pin-registry-core.h](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/pin-registry-core.h)、[pin-registry-core.c](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/device-models/pin-registry-core.c)、[Get退租测试](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/test_pin_registry_key_retirement.py)。C原文12217B、SHA `c9e1cfa23766caea09ef2080882681ddb698c31bc421e5b28a7ec279a144523d`；读取后只保留URL/哈希/结论，不落第三方源码副本，不执行其测试或VM。

一致：按owner/full key建立对象，回复租约检查归属并要求原sender成功free，GET退租只证明查询消费，不能自动成为连接成功；reply_sid与OSAL source单独记录。差异：该dispatch明确仅支持GET，CONNECT另走control dispatcher；其查找mask/count/能力和旧快照不迁入FX3，FX3本轮限定22个canonical端点，原CP独立验证InfraBB/OSD outer SID差异。这里借鉴的是运输生命周期结构，不借其运行结果给FX3补验收。

## 8. 重建、交付和未证实项

项目根执行，无联网依赖：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/pin-topology/audit_pin_topology.py
```

退出0重建proof；检查卷UUID、AP/CP固定SHA、3215条构造赋值、两组入口寄存器独立性、13×50条记录、AP79完整100条readback、31处关键指令、CP类/虚表、首48B真实请求、33包条件投影、11项软件模型正反例。反例含未知pin、type/dir错、占用冲突、in-flight断开拒绝；释放lease后才能断开，再断开回−26。模型测试token是纯Python所有权对象，绝不作为DMM/firmware handle。`ap:2ebe9c0:2fc` / `cp:1bd2cc:82` 参数只打印反汇编，不生成proof。

工具方法核对 [Capstone官方Python文档](https://www.capstone-engine.org/lang_python.html)；Sony协议结论全部来自本地VA。Thumb长区间可能含literal/字符串/跳转表，proof保存raw并标记，不把这些区域的偶然译码当执行证据。AP原件SHA `545c5053…58290f`，CP原件SHA `c90d00d8…6bcba`，DF原件SHA `5d6a9be3…57eae2a`，完整值在proof。

仍未证实：AP79没有pin回复消费、后32包发出、11个连接成功、boot屏障/notify或菜单首绘的pin阶段回执；CP真实运行、真实RAW/YC/audio/OSD buffer与硬件下游均未执行。Python参照模型不是已集成的软件后端，OSAL分配/发送/free错误、并发迁移及guest实际取消仍需运行链实现和独立验收。其它mode与后续拓扑切换未获本次动态样本；不得把本表成功序列当通用固定reply白名单。

## 附：33包条件投影的精确业务请求与32B软件回复

以下全部是**所提出的空软件图已真实登记并逐条提交后才成立**的示例；仅第1条request与AP79实捕一致，其余为静态生成。GET回复反映state1，CONNECT在本地双端图提交后才status0。表中的reply是32B业务体；56B封套、每包source、outer reply_id和动态目的规则见proof `projected_cold_software_requests`（原构造/消费VA见第2、4节）。

| # / row / 操作 | 目的SID | request业务hex | reply业务hex |
|---|---|---|---|
| 1 / 7 / GET_SOURCE | `0x9284074a` | `001000001800020000000000020000000100000000000000` | `0010008020000200000000000200000001000000010000004a07849200000000` |
| 2 / 7 / GET_DESTINATION | `0x905a0048` | `001000001800020000000000010000000100000000000000` | `00100080200002000000000001000000010000000100000048005a9000000000` |
| 3 / 7 / REQUEST_CONNECT | `0x9284074a` | `00100100280002000000000002000000010000004a07849200000000010000000100000048005a90` | `00100180200002000000000002000000010000004a0784920000000000000000` |
| 4 / 10 / GET_SOURCE | `0x9284074a` | `001000001800020008000000020000000000000000000000` | `0010008020000200080000000200000000000000010000004a07849200000000` |
| 5 / 10 / GET_DESTINATION | `0x905a0048` | `001000001800020008000000010000000000000000000000` | `00100080200002000800000001000000000000000100000048005a9000000000` |
| 6 / 10 / REQUEST_CONNECT | `0x9284074a` | `00100100280002000800000002000000000000004a07849208000000010000000000000048005a90` | `00100180200002000800000002000000000000004a0784920000000000000000` |
| 7 / 13 / GET_SOURCE | `0x905a0048` | `001000001800020000000000020000000200000000000000` | `00100080200002000000000002000000020000000100000048005a9000000000` |
| 8 / 13 / GET_DESTINATION | `0x90590818` | `001000001800020000000000010000000000000000000000` | `0010008020000200000000000100000000000000010000001808599000000000` |
| 9 / 13 / REQUEST_CONNECT | `0x905a0048` | `001001002800020000000000020000000200000048005a9000000000010000000000000018085990` | `001001802000020000000000020000000200000048005a900000000000000000` |
| 10 / 14 / GET_SOURCE | `0x905a0048` | `001000001800020000000000020000000300000000000000` | `00100080200002000000000002000000030000000100000048005a9000000000` |
| 11 / 14 / GET_DESTINATION | `0x90590818` | `001000001800020000000000010000000100000000000000` | `0010008020000200000000000100000001000000010000001808599000000000` |
| 12 / 14 / REQUEST_CONNECT | `0x905a0048` | `001001002800020000000000020000000300000048005a9000000000010000000100000018085990` | `001001802000020000000000020000000300000048005a900000000000000000` |
| 13 / 18 / GET_SOURCE | `0x905a0048` | `001000001800020008000000020000000000000000000000` | `00100080200002000800000002000000000000000100000048005a9000000000` |
| 14 / 18 / GET_DESTINATION | `0x90590818` | `001000001800020008000000010000000000000000000000` | `0010008020000200080000000100000000000000010000001808599000000000` |
| 15 / 18 / REQUEST_CONNECT | `0x905a0048` | `001001002800020008000000020000000000000048005a9008000000010000000000000018085990` | `001001802000020008000000020000000000000048005a900000000000000000` |
| 16 / 20 / GET_SOURCE | `0x90590818` | `001000001800020000000000020000000100000000000000` | `0010008020000200000000000200000001000000010000001808599000000000` |
| 17 / 20 / GET_DESTINATION | `0x91670464` | `001000001800020000000000010000000400000000000000` | `0010008020000200000000000100000004000000010000006404679100000000` |
| 18 / 20 / REQUEST_CONNECT | `0x90590818` | `00100100280002000000000002000000010000001808599000000000010000000400000064046791` | `0010018020000200000000000200000001000000180859900000000000000000` |
| 19 / 21 / GET_SOURCE | `0x90590818` | `001000001800020000000000020000000200000000000000` | `0010008020000200000000000200000002000000010000001808599000000000` |
| 20 / 21 / GET_DESTINATION | `0x9058003f` | `001000001800020000000000010000000000000000000000` | `0010008020000200000000000100000000000000010000003f00589000000000` |
| 21 / 21 / REQUEST_CONNECT | `0x90590818` | `0010010028000200000000000200000002000000180859900000000001000000000000003f005890` | `0010018020000200000000000200000002000000180859900000000000000000` |
| 22 / 22 / GET_SOURCE | `0x90590818` | `001000001800020006000000020000000000000000000000` | `0010008020000200060000000200000000000000010000001808599000000000` |
| 23 / 22 / GET_DESTINATION | `0x928d0783` | `001000001800020006000000010000000000000000000000` | `00100080200002000600000001000000000000000100000083078d9200000000` |
| 24 / 22 / REQUEST_CONNECT | `0x90590818` | `00100100280002000600000002000000000000001808599006000000010000000000000083078d92` | `0010018020000200060000000200000000000000180859900000000000000000` |
| 25 / 23 / GET_SOURCE | `0x90590818` | `001000001800020004000000020000000000000000000000` | `0010008020000200040000000200000000000000010000001808599000000000` |
| 26 / 23 / GET_DESTINATION | `0x909a015a` | `001000001800020004000000010000000000000000000000` | `0010008020000200040000000100000000000000010000005a019a9000000000` |
| 27 / 23 / REQUEST_CONNECT | `0x90590818` | `0010010028000200040000000200000000000000180859900400000001000000000000005a019a90` | `0010018020000200040000000200000000000000180859900000000000000000` |
| 28 / 24 / GET_SOURCE | `0x90590818` | `001000001800020001000000030000000000000000000000` | `0010008020000200010000000300000000000000010000001808599000000000` |
| 29 / 24 / GET_DESTINATION | `0x9080003b` | `001000001800020001000000030000000000000000000000` | `0010008020000200010000000300000000000000010000003b00809000000000` |
| 30 / 24 / REQUEST_CONNECT | `0x90590818` | `0010010028000200010000000300000000000000180859900100000003000000000000003b008090` | `0010018020000200010000000300000000000000180859900000000000000000` |
| 31 / 29 / GET_SOURCE | `0x9058003f` | `001000001800020005000000020000000000000000000000` | `0010008020000200050000000200000000000000010000003f00589000000000` |
| 32 / 29 / GET_DESTINATION | `0x909a015a` | `001000001800020005000000010000000000000000000000` | `0010008020000200050000000100000000000000010000005a019a9000000000` |
| 33 / 29 / REQUEST_CONNECT | `0x9058003f` | `00100100280002000500000002000000000000003f0058900500000001000000000000005a019a90` | `00100180200002000500000002000000000000003f0058900000000000000000` |
