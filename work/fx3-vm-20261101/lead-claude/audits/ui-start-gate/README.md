# UI 首绘、Widget timer 与 boot 屏障审计

结论：**AP75 的六次 1001 不是 `appFw+0x16ee6f8` 发出的；目前没有证据把首次清屏限定在四任务屏障之后。** 最有价值的新入口是 AppFw 的共同 UI 推进入口 `0x16f1998`：它先驱动 Widget 软件 timer，再驱动绘制。应先确认 AP75 有没有进入这段循环及 timer 注册表/时钟，而不是补发 1004 或假定 ADF 屏障是首清屏的唯一前置。

审计日期：2026-11-01（保存的 AP75 回执 UTC 日期为 11-02）。只读原 AP ELF、既有日志及观察器源码；只写本目录，未运行 QEMU、未修改 runtime、STATE、原件或设备。A=原码/捕获直接证据，B=有约束推断，U=未证实。以下 AP库 VA 为 image VA；`utimer.ko` 是重定位模块，`.text+offset` 不是加载后VA；行号均为各 run 的 `serial.log` 按 LF 分行，保留 CR/NUL。[proof](ui-start-gate-proof.json) 包含原字节、完整选定函数窗口、重定位/调用点、RTTI、逐行事件与源文件 SHA256。

## 1. 六次 1001 的归属：先纠正入口前提

**A：观察器的 `config` 钩在 `16ee6f8` 函数本体，不只是 `2191df4` 调用点。** `runtime/helpers/fx3-timer-observe-v3.c:55,62` 的第四地址明确是 `app_base+0x16ee6f8`；`:36–39` 无条件增加 `config_calls`，只有 `config_target_calls` 检查 caller=`2191df8`。因此 `config=0` 比“没有进入 2191df4 分支”更强，表示被钩函数自身未进入。

| run | hook 已安装 | 六次独立 UI_WIRE / 同时快照 | 最后保存统计 |
|---|---|---|---|
| `ap75final1-a67fe198` | 行5326 | 行7785–7797；TID289；六次 `1001`，每次 `patch_mask=0xf, config=0, timer_entry=0, fill=0` | 行45857–46594，所有保存样本保持0 |
| `ap75final2-4d01e9f8` | 行5601 | 行7993–8005；TID332；同上 | 行46418–46923，所有保存样本保持0 |

两轮 receipt 的 requested_seconds 均为240，实际 duration 分别243.275s/241.693s。六次发送有独立于去重锁的 `UI_WIRE`；其参数只给 target/op/tag1/tag2/result，**没有消息体或用户栈**。函数前缀/patch 检查与零计数支持排除 `16ee6f8`，不能用旧 `SEND_UNIQUE` 记录去重后的“一条”代替这六条。

### `16ee6f8` 调用者全集的静态范围

脚本扫描 appFw 所有可执行 section 的 AArch64 B/BL、所有 RELA、所有已分配 section 的原始8B指针、ADR/邻近 ADRP+ADD：

- **A：唯一直接调用是 `2191df4 bl 16ee6f8`；没有重定位函数指针、虚表项或原始8B地址引用。** 入口 `16ee6f8..16ee78c` 没有第二个中途分支调用入口。proof 的 `1001_address_taken_scan` 保留地址构造候选；不能据此数学排除任意运行时计算指针、外部注入或改写后的虚表。
- **A：`2191df4` 所在路径先检查主模式（`2191da0..da8`），再检查 `w24`（`2191de8`）；`w24` 来源与队列/状态变化有关：`2191c38..c54` 在容器相等且 `state+1d0==407` 时置0，否则到 `2192070` 置1。** 不应将其命名成“boot完成”或“LCD已开”而没有进一步状态语义证据。
- **A：`2191df4` 后同一分支 `2191dfc` 调 `16ee8d8`，后者在 `16ee968/9a4/9e0/a1c` 发送四个 1001（payload+8 selector=12/13/14/15）。** `16ee6f8` 本身另发一个 selector=2 的1001（`16ee748`），均640×480。这个“五条配置”分支与 AP75 六条不能按 opcode 混同；AP75 的函数入口计数已经排除了它的正常直接入口。

### 其他原厂 1001 发送链

```text
路径 C（配置；AP75 已排除其16ee6f8入口）
  state/queue 门控 2191c38..2191de8
    ->2191df4 ->16ee6f8 ->16ee6f0 ->16ee598 ->8280074d
    ->2191dfc ->16ee8d8 ->4×16ee6f0 ->16ee598

路径 W（Widget 初始化；AP75 最可能的来源之一）
  widget vtable+148 =176ff74 ->176fefc
    [176ff14..28 清96B；176ff2c 写1001；+8取 widget+1e8]
    ->176ff60 ->16ee664 [按selector引用计数，16ee674..6ac]
    ->16ee598 ->8280074d
    ->176ff70 ->176fe88 [共享timer注册，见下]

路径 R（Widget mode/state 更新；另一个合法来源）
  176fe2c/176fe5c ->176fdac
    [176fdd4 比较保存状态；176fde4..fdf4比较Widget mode]
    ->176fc2c 更新持久96B记录 widget+1ec
    ->176fe18 尾调16ee6f0 ->16ee598 ->8280074d
```

`176ff74` 是11张相关虚表的 +148 槽（proof.vtables），并有 `177b400/414/428` 三个明确调用；这三个在构造 `177af28` 尾部、三次 `Widget::setMode(3)` 后执行。`177af28` 由 `1726d2c` 构造调用，其余子部件还经通用 Widget 生命周期初始化；**不能把这三个静态调用直接计成六条运行消息**。`16ee598` 的共同发送 source=`9088076b`、target=`8280074d`（`16ee5e0..634`），它不会等待1004。

**B：六条最符合监看 Widget 的初始化/状态刷新（W/R）。U：不能唯一分配六条的具体调用者、selector、对象或 W/R 比例。** AP75 的 `FX3_PROFILE` 栈只有已捕获服务请求（例如 final2 行7951–7962是 ADF032d，8028–8038是 VDF016a），不是1001用户栈；把邻近服务栈直接嫁接到1001不成立。后续若需确证，应在原共同发送器仅对u16=1001记录返回地址链和96B有效字段，保留原发送结果。

## 2. Widget timer 注册与驱动：软件扫描，不是每个Widget一个OSAL timer

**A：timer回调绑定在 vtable+0xf8。** 原厂 RTTI 与对应 slot：

| 类型 | table header / onTimer slot |
|---|---|
| `view_mp_aperture` | `41d62b0 / 41d63b8` |
| `view_mp_eframing_frame` | `41d6470 / 41d6578` |
| `view_mp_focus_lock` | `41d6638 / 41d6740` |
| `view_mp_focus_map` | `41d67f8 / 41d6900` |
| `view_mp_iso_sensitivity` | `41d69b8 / 41d6ac0` |
| `view_mp_shutter_speed` | `41d6b78 / 41d6c80` |
| `view_mp_tcub` | `41d6d38 / 41d6e40` |
| `view_mp_tracking_frame` | `41d6ef8 / 41d7000` |
| `view_mp_tracking_reservation_frame` | `41d70b8 / 41d71c0` |
| `view_mp_widget_base` | `41d7278 / 41d7380` |

以上十个槽直接指 `176fb4c`；另有 `view_mp_af_window` 的覆写/尾调路径（`176d8b8 b 176fb4c`），不能只扫描直接等于目标的虚表就遗漏它。

**A：注册者为 `176fe88`，由 Widget 初始化 `176ff70` 进入。** 它通过 GOT `47c8908→7883dbc` 读取共享引用计数；只有为0才调用 `ID::genIDForSystem(0xf1ae2d31)`（`176feac..feb4`），以 `TimerType=1, interval=0x9c=156` 交 `WidgetBase::addTimer`（`176febc..fecc`），把返回timer ID写到 GOT `471f428→7883db8`（`176fed0..fedc`）。之后计数加1（`176fee0..fef0`）；注销 `176ff78` 递减，最后一个调用 `removeTimer` 并复位ID（`176ffb8..ffe0`）。ID和计数在 BSS，不能从文件中的零当成运行态已注册或未注册。

**A：注册只建立软件记录，没有在这个函数内创建线程/OSAL timer。** `libObj+17473c→17697c` 分配0x38B，记录widget ID(+0)、timer ID(+4)、type(+8)、interval(+c)、deadline(+10)、同步ID(+18)、基准时间(+20)、next(+30)，挂到管理器+890/+898（`1769c8..176aac`）。interval与时间在此按1000换算（`1769e4..176a0c`），故156是软件timer的毫秒级间隔；原始时钟单位由此代码换算确定，不代表OSAL配置常量也可未经核对同单位。

```text
AppFw 外层初始化16f16bc
  ->16f1794..17a8  向本线程队列注册callback16f1358
  ->16f17c8..17f4  以type38/op1向910040同步创建timer
      callback pointer GOT47817f8 =16f1c18
  ->16f1808..1814 ->16f1118  设置period参数0x4e20(20000), mode2
      16f1118 ->910040 type38/op2

原utimer.ko内核timer服务 [1e08注册910040，handler1cb0]
  ->.text+580..5c0 以source910040发送40B callback消息
  ->OSAL UIPC proxy回调 [AP75 TID205=uipc_proxy_0]
  ->16f1358 [只接受source910040，16f1370..137c]
  ->16f142c 调原消息callback16f1c18
  ->16f1c18 ->16f1a48 [增加object+a18；发150000到5503e0，16f1b70..1bb0]
  ->AppFw主循环16f2220 [接收5503e0，16f2098..2214]
  ->16f25ec..2640 时间/状态门控 ->16f1998
      ->16f19b0 WidgetSystem::updateCurrentTime
          ->libObj177650 ->1777d8 ->177548 到期扫描
          ->deadline(+10)<=manager当前时间(+0) [1775a0..5a8]
          ->构造TimerEvent178190 ->176ba4 ->132ad4 遍历分派
          ->TimerEvent虚表25f3d8=177f20
          ->177f44..5f58 widget ID匹配
          ->177f64..70 调widget vtable+f8
          ->appFw176fb4c ->timer ID匹配/getTimerInfo成功 ->1004
      ->16f1a1c GraphicsEngine::drawFramebuffer [见第3节]
```

**A：外层timer已绑定原内核服务，不是凭UTM名称推断。** `original-uipc/original-modules/utimer.ko` 的 `utimer_open_interface .text+1e08` 注册910042/910040/910041；910040的callback由 `.text+1ed8` 重定位到 `.text+1cb0`，后者分派alloc/init/mod/cancel/free（`.text+1d24/1d3c/1d54/1d08/1cec`）。到期线程 `.text+580..5c0` 分配40B通知、复制callback/context、source=910040，交osal_snd_msg；模块也通过 `.text+21b4` 创建原OSAL线程。用户态 `libosal_uipc+6ce0→3cd8` 用ioctl注册callback；AP75 final2行10279–10337的TID205快照名为 **uipc_proxy_0**，与行7987实际发送150000的TID相同。故链是内核utimer服务→UIPC代理回调→AppFw队列→Widget软件扫描；`libosal_utm`是线程基础设施，不能说它独立直接驱动每个Widget。硬件tick/时钟稳定性和整个周期连续消费仍未运行验收。

**A：主循环有具体门控，不是“只要线程存在就绘制”。** `16f22c8` 调 `GraphicsEngine::processSystemMessage`，返回false则退循环（`22cc..25c4`）；`16f2478..2488` 的 `a18>2 && !a12` 会跳过本轮 UI 时间检查；`a18` 是待消费的唤醒计数，发送callback在 `16f1a68..74` 加1，消费source83128/type150000在 `16f1d30..68` 减1；`16f25f4..2604` 比较已过时间与0x62f4，未超过则跳过；`16f2610` 调 `16f2218`（原函数恒返1）；`16f2624` 的全局状态 `78ab0d9` 或 `a13` 非0先执行清理分支，随后仍到 `16f2638..2640`。这些数据在保存日志中未采样，不能宣布哪一条实际拦住AP75。

**A：AP75并非完全没有timer唤醒发送。** final1 行7781、final2 行7987都有后台TID205向5503e0发送150000；主线程的5503e0首次接收分别在7782/7990。它只证明有一次唤醒发送/接收等待记录，不能证明相应callback被消费或周期持续。`UTIMER_RC=0` 也不能代替Widget timer回调验收。当前证据不支持创建另一个UTM线程作为修复。

`176fb4c` 的两个退出门槛仍是timer ID比较（`176fb78..80`）和 `getTimerInfo`（`176fbb8..c0`）；但AP75 **入口计数已经是0**，优先级应在它之前，不应先归咎这两个内部条件。软件扫描还要求timer存在、deadline到期、注册owner仍在可分派Widget树且ID匹配（`1775c4..620`, `177f44..58`）；这些都未由保存日志关闭。

## 3. FillRect 的创建、enqueue、执行与更上层

**A：`100c48`不是命令创建者。** 确定的下游闭包为：

```text
libObj GRM_gpermFillrect=1017ac
  ->bitmap/rectangle/format检查1017f4..1018f8
  ->101944 ->1013a8 [enabled字节+8必须非0，1013a8..3ac]
  ->1013f4 new(0xa0) ->10140c ->100b40 构造CmdFillrect
      vtable2536f8；拷贝56B FillRectParam到+40 [100b80..84]
      保存bitmap到+78，持有/WriteLock [100b88..ba0]
  ->10142c ->fc0cc 设置completion参数
  ->10144c 尾调fc184
      ->fbee4 入GRM工作队列 [fbf20..fbf78持锁/链表插入/唤醒]
  ->[grm worker虚调用，完整dispatcher与首命令身份U]
  ->vtable slot253720 =100cfc
      state(+34)==1 ->100d18 ->100c48
      state==2 ->100c04 完成，不执行fill
  ->100c88 获取bitmap物理地址 ->100cbc写参数 ->100cc4 GpermFillRect
  ->libgpe SendDraw ->80820884 opcode0 [沿用前审计原码]
```

**A：找到两个原上层调用入口及实际参数门槛。** libObj 对 `GRM_gpermFillrect` PLT56090只有 `10ecfc` 和 `152940` 两个直接调用点；`10eae0` 处理真实bitmap、裁剪范围、颜色与异步参数（`10eb40..10ecfc`），由 `GraphicsContextGRM` 的清除方法 `10f29c` 在 `10f2f8` 调用，后者为虚表 header255f20 的 +18 槽（slot255f48）；另一裁剪fill在 `10f698`。第二条 `1528b8→152940` 由 `153678` 进入，矩形width/height>0才创建，位于 GraphicsImage clear/fill 辅助链（`153708→15368c→1535e4`）。因此既有GRM画图上下文，也有GraphicsImage API路径，不能把opcode0自动当成某一个Widget的直接调用。

**A：AppFw共同渲染驱动入口**：`16f1998→16f1a1c→libObj GraphicsEngine::drawFramebuffer=16ea10`。它先检查引擎+312（`16ea30..34`），使用 `15d900`/`16daac` 准备状态（`16ea38..54`），再查 framebuffer/dirty状态 `128518`（`16ea58..60`），非0才取rect并调用 `16dd04`，后者消费回调开关/函数指针（`16dc30..16dcc4`）和后续绘图对象。**U：从这个动态渲染上下文到 AP70 那一个 `CmdFillrect` 的唯一高层调用分支没有闭合。** 图中不能把它与 `GraphicsContextGRM+18` 直接画成已证实的一条无条件边；也没有证据表明1004接收方生成了这条命令。

AP60行7548–7550、AP70行7651–7654是首个GPE请求及614400B软件清屏完成；AP75两轮没有FillRect execute入口调用，也无该完成marker。软件内存清屏仍不是屏幕、菜单文字或CP扫描验收。

## 4. 四任务屏障：首清屏不能归为“只能屏障后”

```text
sequence_boot 主序列
  license_get_i 2b61efc  ---------+
  adf_set_volume_i 2b5fae4 ------+
  regist_beep_signals_i 2b61a90 -+->2b67a6c ->2b6353c 等4个句柄完成
  adf_get_func_i 2b60208 --------+
                                      |
                                      +->2b67a70 后续ADF/path/notify初始化
                                      ..U.. 最终boot通知与UI业务状态

AppFw UI主循环16f2220
  ->16f1998 ->软件timer / drawFramebuffer
  （尚无“仅由上述屏障后路径启动”的调用边）
```

**A：boot的正常完成确实等待四个子任务；B：首次清屏并不要求已经正常越过这个屏障。** 最强运行反例是AP70：清屏在行7654，两个子任务032e/033d的捕获请求却在行20496/20492，随后行20494/20498是两个子线程的接收等待，20499–20500明确Skip snd to 0x747，并且没有对应成功回复/静音提交；它们的原同步等待timeout=-1（前审计 `2de72fc..7300`），正常四任务完成屏障不能因此已经成功越过。即使考虑跨线程日志交错或异常提前退出，仍然不能把AP70首清屏当作正常屏障已完成证据。AP60也有早期清屏，但缺少同等级ADF请求捕获，因此只作辅助，不用不存在的完整时序作证明。

**B：最可能的解释是早期Widget初始化后，AppFw在AP60/AP70获得了至少一次有效UI时间推进/绘制机会，AP66/AP71–75没有走到等效的有效机会；差异落在初始化/事件消费/软件timer owner、时钟deadline及frame/dirty状态，而非1001等待ACK。** 该判断由已恢复共同入口16f1998、AP75排除入口计数及AP70屏障反例共同支持，**不是已定位到一个确定branch的根因**。所谓“先前屏障偶然更快完成”缺少支持；“某sequence回复时序改变UI机会”仍可成立，须新增观测。**更具体的优先假设是待消费timer消息积压：`a18>2 && !a12` 会持续推迟UI推进，若guest执行/日志开销使生产快于消费，早期初始化后就可能长期没有有效UI机会；AP60/AP70可能在积压形成前完成过一帧。** 原码支持这个机制，保存日志只证明有过150000发送，未记录a18/a12和实际出队速率，故仍B，不能认定为确定的饿死或给出加sleep补丁。

一个可测的时序线索：AP70行7650的30170通知在首次清屏附近，而AP75该通知延后到final1行7957/final2行8437；静态 `2bb0b28/2bb2e94` 的sequence析构会发布30170，前者RTTI为 `sequence_get_movie_rec_status`，**不是凭数字就能叫作display完成通知**。本审计没有将其认定因果。显示setup成功也不充分：final2行8294已发送011a，行8839–8872已经进入后续0429/0500，但最终UI入口仍0。局部timer注册/扫描和GRM命令构造窗口内没有LCD/背光判断；全局业务状态可能经其他调用影响Widget树，仍U。

## 5. 若要正常越过boot屏障，还欠什么

此节是正常boot推进清单，**不是已证明的首清屏充分条件**。

| 项目 | 原码要求 | AP75保存证据与当前结论 |
|---|---|---|
| 032e子任务 | `2b5fae4` API成功后返回，经worker完成回调 `2dcb9c0..2dcba04` 上报句柄 | final1行20118/final2行8914有静音模型成功提交；没有单独的四句柄匹配完成回执，不能把提交直接等同屏障已计数 |
| 033d/13项注册子任务 | `2b61a90` 得地址后，`2b61de0..df4` 逐项注册；内置9项327/32a，后4项文件/DMM/ICDT | final1行20095/final2行8994提交033d；随后首个327仍在final1行20206/final2行9116等待；保存流未见该轮327完成，**这个子任务未提供完成证据** |
| license_get_i | `2b61f20..28` 按主模式可能提前返回；否则 `2b61f64→2de20a4` 读license结果，继续消费/发布状态 | U：没有该子任务返回/完成栈或句柄快照；仅有原库符号/HasPublicKey加载不能称license完成 |
| adf_get_func_i | `2b60264→2dd0c94→2dec778`；`2dec7a0` 写0325，8B请求，`2dec7e4` 等28B回复，消费多个能力字节（`2dec7ec..`） | 两轮保存流0325 request计数0；这只能称“未捕获”，不能判已经回复、没有依赖，或必定卡在0325 |
| 屏障自身 | `2b6357c` 剩余数4；`2b635d0` 无期限收完成；`2b63628..48` 匹配句柄才减1 | U：没有4个句柄/剩余数/return的运行回执；`0x2000`特殊提前退出不当作正常完成 |
| 屏障之后 | `2b67aa0→2dd1014→2dee6f0` 的adf_sys_set_path成功；后有sys_request `2b67b2c`、digital_level_notify `2b67b70` 等，原日志字符串391a002起可核对 | 这些步骤本轮未提供到达/回复回执；不能用回复032e+033d承诺菜单恢复 |

后4项提示音文件/DMM/ICDT的合同已在相邻 [adf-beep-file-dmm审计](../adf-beep-file-dmm/README.md)；那份是静态方案，不代表AP75已集成或通过。最终启动状态需四个原任务真实返回并被屏障消费，再观察后续原协议，不伪造许可/功能能力或成功完成。

## 6. 最小后续观测与未关闭项

仅建议运行链加有界观察，本worker未改/运行：

1. AppFw `16f2220/16f16bc` 入口及return、`16f2640` 调用与跳过原因；记录 `a18/a12/a13`、旧/新时间、`GraphicsEngine::processSystemMessage` 返回、5503e0实际出队计数。先分清初始化未退还是循环门控，避免把futex空闲直接叫死锁。
2. `176fe88` 的共享计数、owner、返回timer ID；`libObj177548` 当前时间/head/deadline、到期/owner命中；这些比再次只观察176fb4c内部更上游。
3. 每条1001的有效96B字段和调用链；`GRM_gpermFillrect1017ac/1013a8` 的调用链、CmdFillrect指针与入/出队序号。如此才能连接AP70第一条fill到高层，不用1004时间邻接替代因果。
4. 四任务句柄、完成事件/remaining与 `2b67a70` 到达。将boot等待与UI循环证据并排记录，不假设它们是同一门。

U保留：六条1001的逐条身份；首FillRect唯一高层创建分支；AP75未推进UI的具体门；原utimer硬件tick及当前模型时钟/周期连续消费的稳定性；boot完成通知到UI状态的虚调用闭包；license/0325运行状态、四句柄正常完成、最终可操作菜单/像素与物理显示。

## 复现

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/ui-start-gate/audit_ui_start_gate.py
```

退出0重建proof。也可 `...audit_ui_start_gate.py dis appFw.so 16f1998 b0` / `xref appFw.so 16ee6f8` / `sym libObj.so WidgetSystem` 作只读查询。验证固定三原库哈希和原utimer模块/重定位、选定窗口完整解码、直接调用/虚表数据、AP75每轮六条wire与快照/保存零统计；不是原固件执行测试。工具API仅参考 [Capstone官方Python文档](https://www.capstone-engine.org/lang_python.html)（本轮核对）；Sony语义以本地原字节为准。
