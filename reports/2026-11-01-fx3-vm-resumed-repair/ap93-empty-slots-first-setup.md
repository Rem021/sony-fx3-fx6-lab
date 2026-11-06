# AP93：软件空槽通过，首次设置与交互绘制

2026-11-02。**软件 RM 空槽链已运行验收；原语言选择页已取得“下键改变画面、上键恢复原图”的独立物理PNG反馈。确定后原应用进入新首次设置屏，但新的资源池子块目标/放大复制尚未建模，已安全停止；尚未到拍摄待机或MENU。**

以AP90-r2健康基线构建，不加载原mcmn_drv硬件模块。独立provider在原MediaDetect加载前，先核对80d9016e缺席再经原OSAL reg_msg_queue_cb注册；单worker串行释放请求、按本次动态reply/notify ID分别分配回包。cmd9按已审计112B原配置投影；cmd3注册后回放新分配7B `02000007000000`，source=本次notify ID；cmd3(0)取消；未知命令回80000003/24B/长度0。明确标记 `synthetic_empty_slot_provider=1 original_CP=0`，不声称原机enable/counter历史或CP实现。

| 运行 | 时长/结果 | 验收与限制 |
|---|---|---|
| `ap93empty-9b0fd885` | 15.184秒，实施过严门控主动停 | 动态reply ID被误要求已注册callback；cmd9已收/释放0但无回包，13个必需marker未到。Lead同意移除额外stat，保留原valloc/send校验。此轮不算空槽通过。 |
| `ap93r2empty-77c94f2c` | 请求300/实际302.709秒，健康完整 | missing[]，state2/mask4与2、两次status0；无110/Mount/MOUNT_ERR；72GPE全0；首屏语言选择。MENU两包原接收0，约2.99秒后读回未变。 |
| `ap93r3setup-d8c86a95` | 38.471秒，新目标拒绝主动停 | missing[]，空槽链再次成立；下键两包已接收，原FillRect/BitBlit切到43ae96100触发result5/reason2；上/确定及后续键均未发。 |

三轮均qemu_exit0/process_reaped/PID_absent/inputs_unchanged/两锁FREE，无新guest致命或symbol lookup error。最后完整im228 maps分别在13.73s、r2见独立review、35.70s；不把早停当300秒或菜单验收。每轮的独立review、receipt及0x11a后已保存请求时间线均位于runtime；serial按LF读取，边界/交错记录不声称全系统无损。

## 原空槽消费与所有权

r2/r3的cmd9共136B、cmd3共28B：原服务request释放0，原D消费reply释放0；新7B回放由原FRONT callback接收并释放0，动态目的均取当次请求，没有硬编码AP92 ID。r3已在**原拥有消息、原osal_msg_size确认长度**的两个消费点直接只读copy，取得独立完整136B/28B/7B；通用peek没有放宽。旧observer通过/proc/self/mem读/dev/uipc映射会失败，本轮原maps已定位该映射，不能把旧readable0当作收到空body。

两个media ID1000/1010在原StartInOut前的mask分别4/2、state2，均走fa3c/status0一次，hold0。软件FRONT RemoveCnt字段0；原D自己的首次通知RemoveCnt实测1，保留原计算结果，没有改写。无原ThreadInit110、无status1、无Mount、无MOUNT_ERR警告；后续无卡图标与待机仍须另验。

宿主ASan/UBSan覆盖长度/配置/注册/重复注册每次回放一次/取消/未知命令/分配失败/发送失败/仅释放一次；v2增加“动态reply无callback仍可由原分配/发送处理”的回归。新控制页41df00000/64KiB经FDT及原memrsv不重叠核验，宿主仅在QMP暂停时通过本机Unix GDB向其+8写8B(seq/key)，原应用参数/回调均不写。按键仍由im内原OSAL向807a0020、source410025发送20B；原表只读、NOLOAD与receiver门控保持。

## 实际画面与按键

r2阶段A：原 `scr0039_boot → scr0099_0001`，screen0xfa；最后原开屏被宿主观察后10.906秒取独立QMP帧，再发送MENU1ab down/up。原IInputRecv两包from_type1/source410025/native_result0；没有新开屏或新GPE。前后614400B物理读回均SHA `2485079bdfe8c91590235540c1929a813f03a96b17cae33b32d53539e77e708e`，并与当时原已提交ring帧吻合，**没有进入MENU**。

!['原厂首次设置语言页，独立QMP物理读回'](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r2empty-77c94f2c/ap93-phaseA-before-MENU.png)

r2各步文件：

- 无输入阶段：[PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r2empty-77c94f2c/ap93-phaseA-before-MENU.png)，言語/English/日本語/Français/Deutsch/Italiano。
- MENU后：[PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r2empty-77c94f2c/ap93-step-01-key-1ab.png)，与前图逐字节相同，仍语言选择。

Lead目视确认语言页后，以msg_f063a6eaccba授权r3：下→上→确定，之后逐页目视接受默认最多12步，再待机/MENU/导航。r3阶段A[PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r3setup-d8c86a95/ap93-phaseA-before-SETUP.png)仍语言页；只发首个下30的两包。2秒后单步PNG尚未到时，模型已因新绘制目标主动停；[最终QMP PNG](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r3setup-d8c86a95/ap93-final-QMP-logical-fmt0.png)来自原43feb5100前台，不能冒充新43ae96100目标的成功读回。

## 新目标来源与修正边界

r3 L2592：原libObj1031b0成功返回后，已有登记 `object7f500011e0 / identityffffffc11e1d6800 / vptr=libObj+253a48 / type403 / uhdl401 / state10 / epoch1`；原对象+58 logical7f58508000、+60 phys43ae96000、+68 bytes140000；原maps另证实相同/dev/mem映射。不是未知地址，也不是缺少登记；本轮没有保存完整dmm_extents文本，不编造proc读回。

L30557首条拒绝：FillRect seq72，目标43ae96100、640×480/stride640/fmt0/flagsff，56B原参数完整。旧command在resource_lookup之前只允许within(545)，故被拒。131条完整CMD：72成功、59拒绝；另4条交错/不完整原记录独立保留，不强行解析成完整数值。新目标尚无成功像素证据。

Lead msg_4c95916cbc49授权按已观测原对象修正守卫。新模型只准原成功native-open、type403、原类vptr、完整字段/本地epoch匹配、逐行span在父对象内的目标；在生命周期锁下重查，原close先撤销，源独立映射只读，源/目标为同父对象时使用同一代次别名。没有物理地址允许列表，没有宣称已证明第二屏幕/双缓冲角色。原bitmap子分配、compaction与queued ABA的既有限制仍明确保留。

原件/旧runs/既有helpers均保留；后续修正新起v17与registry v3，近似像素公式/FIFO/完成顺序/545原proc检查未改。[原目标证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93-new-target-original-proof.json)与[宿主目标回归](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93-native-target-host-check.json)。

## 证据入口

- [r2独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r2empty-77c94f2c-review.json) / [RM与输入](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r2empty-77c94f2c-rm-input-observation.json)。
- [r3独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r3setup-d8c86a95-review.json) / [RM与输入](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r3setup-d8c86a95-rm-input-observation.json) / [GPE统计](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r3setup-d8c86a95-gpe-statistics.json)。
- 后续同脚本运行与每步PNG待追加；目前 NO CARD图标、拍摄待机、MENU菜单和完整输入反馈均未验收。

## r4：原生目标绘制通过，画面导出固定目标门待修正

`ap93r4target-aa8bcce7`实际39.480秒，原下30两包之后138条可完整核对CMD均result0；6条串口交错/不完整记录不计完整命令（包括看似数值29的src_fmt，被判定为交错污染，绝不称支持格式29）。native-open目标对象的epoch/state/字段/逐行检查通过；原FB同一个`7f58001140`从bitmap`7f5468ecb0`/physical`43feb5100`/token402切至bitmap`7f5468ead0`/physical`43ae96100`/token401。

原read_lease+raster_guard已持有，bitmap_bytes614400、640×480/stride640/nativefmt1→GPEfmt0与发布参数匹配，但旧OSD consumer固定active545检查拒绝capture，未ACK；driver主动停。此轮exit0/reaped/inputs_unchanged/PIDabsent/两锁FREE/missing[]，im228最后完整maps37.18s，无新致命。首步PNG仍读旧已提交545帧，不算新目标导出成功；上/确定均未发送。

Lead `msg_91eda4ecac90` / `msg_781d1794767b`授权把捕获与宿主逐帧导出扩为当前原FB活跃bitmap对应、已按原对象规则登记且epoch/state有效的屏幕缓冲；必须在原read_lease+raster_guard下校验，保留尺寸/格式/行宽和失败不ACK，不能按地址放行。修正宿主回归后继续同脚本重跑。

## r5：当前原生画面导出通过，语言页输入反馈成立

`ap93r5frame-19bbfb81`请求300秒，实际50.704秒因新GPE拒绝主动停；qemu_exit0/reaped/PIDabsent/inputs_unchanged/两锁FREE/missing[]，无新guest致命或symbol lookup error。im228最后完整maps段在46.39s，首条映射串口交错，另两条完整im.elf映射保留。三次按/抬共6包全部发出、原IInputRecv接收，所有9个原分配lease均原free0（以观测JSON为准），没有后续默认确定/MENU/导航。

画面导出用GPEv18的guarded目标tuple：原read_lease+raster_guard期间再持lifecycle锁，legacy545仍核对原proc/unit402/serial，另一活跃原bitmap按native-open403/type/class/uhdl/epoch/state/字段核对，复制前后均重查；尺寸/格式/stride/原CPU VA到physical映射保留。来源或代次不匹配不ACK。新ringV2用512B头独立保存目标tuple、CPU映射和原descriptor，宿主逐帧物理读回须与原lease已提交快照SHA相同。宿主ASan/UBSan已测FB切换、旧epoch拒绝、旧绘制/完成回归；Python导出测任意已登记目标、无效epoch和物理内容变化拒绝。未按物理地址扩名单。

| 步骤 | 实际画面/证据 | 物理与SHA | PNG |
|---|---|---|---|
| 阶段A无输入 | 原语言页，日语标题「言語」 | 43feb5100，2485079b…7e708e | [阶段A](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r5frame-19bbfb81/ap93-phaseA-before-SETUP.png) |
| 1 下30 | 标题变「Langue」，原语言列表仍在；Lead目视确认从日本語移动至法语 | 43ae96100，7766cd63f5c0d8639587f63c4fe6ddfc9b1ea50097b824dc7a85da8bdb3d1b43 | [下键后](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r5frame-19bbfb81/ap93-step-01-key-030.png) |
| 2 上3 | 标题回「言語」，像素逐字节恢复阶段A | 43feb5100，2485079bdfe8c91590235540c1929a813f03a96b17cae33b32d53539e77e708e | [上键后](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r5frame-19bbfb81/ap93-step-02-key-003.png) |
| 3 确定1ac | 原open screen `scr0099_0001 → scr7248_0001`；下一页未完成绘制，不命名其内容 | 新绘制未成功，2秒后独立单步PNG未到 | 不伪造第3步PNG；最终旧545样本不冒充新页 |

上述两张单步PNG均实际查看，独立QMP与当时原已提交ring逐字节吻合；这是原输入→原绘制→不同像素→返回像素的运行证据。下键后截图约在宿主观察up后2.818秒，上键后2.850秒，不声称精确guest2秒；原按键hold目标100ms，实际时序见原ns标记。RGB图按原ring的opaque-alpha查看方式导出，物理raw未改，颜色仍属于既有近似模型。

!['下键后Langue，独立物理读回'](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap93r5frame-19bbfb81/ap93-step-01-key-030.png)

**更正首次设置预期：** 初始选中日本語，所以上一步脚本的“下→上→确定应选English”仅是先前预期，并未成立；Lead `msg_6732ee79a03e`目视确认本次确定选了日语。下一轮改为**上3→PNG（预期English标题）→确定→逐页实际观察**，不能沿用本轮动作声称英语已选择。

### 新阻塞，等待独立审计

首个新失败FillRect seq216：dst4109364c0，32×29/stride32/fmt0/result5/reason4，原父为Heap2；其成功原子分配在L37065记录bytes780/align40。下一条BitBlit seq217：src4109364c0的29×29图放大到dst410936c80的116×116，原新分配7400/align40，flags0，result5/reason2；后又出现同型两包。209条可完整解析CMD中206成功/3拒绝，10条交错/不完整独立保存；最后一条失败标记数值交错，不计作完整CMD。原56B/144B及原malloc子块元数据完整保存，不擅自将父资源池升为任意可写，也不把未实现的flags0放大复制称已完成。

Lead已派 `audits/offscreen-subblock` 复核子块目标生命周期与seq217语义，要求期间待命；未继续运行。下一轮先等合同，按上3/确定选择English，再原首次设置默认确认最多12步，待机后MENU及导航。NO CARD图标、拍摄待机、MENU菜单和完整首次设置均仍未验收。

[r5独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r5frame-19bbfb81-review.json) · [RM/所有权/输入/逐步读回](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r5frame-19bbfb81-rm-input-observation.json) · [GPE统计](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93r5frame-19bbfb81-gpe-statistics.json) · [新子块原始证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93-offscreen-subblock-runtime-evidence.json) · [捕获/导出宿主回归](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93-frame-export-host-check.json) · [完整来源哈希](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap93-r5-source-ledger.json)。
