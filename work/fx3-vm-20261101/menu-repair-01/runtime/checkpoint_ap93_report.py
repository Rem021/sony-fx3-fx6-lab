from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;D=R.parents[3]/'reports/2026-11-01-fx3-vm-resumed-repair';p=D/'ap93-empty-slots-first-setup.md';assert not p.exists();pref='../../work/fx3-vm-20261101/menu-repair-01/runtime/'
p.write_text('''# AP93：软件空槽通过，首次设置与交互绘制

2026-11-02。**软件 RM 空槽链已运行验收：原检测回调消费有效首包，两媒体 state2、仅 status0，无原 Mount 尝试/读卡警告。原画面进入语言选择页，尚非拍摄待机/菜单。下键已触发原重绘；旧 GPE 模型拒绝另一个原生缓冲区，正在按原对象证据修正。**

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

!['原厂首次设置语言页，独立QMP物理读回']('''+pref+'''runs/ap93r2empty-77c94f2c/ap93-phaseA-before-MENU.png)

r2各步文件：

- 无输入阶段：[PNG]('''+pref+'''runs/ap93r2empty-77c94f2c/ap93-phaseA-before-MENU.png)，言語/English/日本語/Français/Deutsch/Italiano。
- MENU后：[PNG]('''+pref+'''runs/ap93r2empty-77c94f2c/ap93-step-01-key-1ab.png)，与前图逐字节相同，仍语言选择。

Lead目视确认语言页后，以msg_f063a6eaccba授权r3：下→上→确定，之后逐页目视接受默认最多12步，再待机/MENU/导航。r3阶段A[PNG]('''+pref+'''runs/ap93r3setup-d8c86a95/ap93-phaseA-before-SETUP.png)仍语言页；只发首个下30的两包。2秒后单步PNG尚未到时，模型已因新绘制目标主动停；[最终QMP PNG]('''+pref+'''runs/ap93r3setup-d8c86a95/ap93-final-QMP-logical-fmt0.png)来自原43feb5100前台，不能冒充新43ae96100目标的成功读回。

## 新目标来源与修正边界

r3 L2592：原libObj1031b0成功返回后，已有登记 `object7f500011e0 / identityffffffc11e1d6800 / vptr=libObj+253a48 / type403 / uhdl401 / state10 / epoch1`；原对象+58 logical7f58508000、+60 phys43ae96000、+68 bytes140000；原maps另证实相同/dev/mem映射。不是未知地址，也不是缺少登记；本轮没有保存完整dmm_extents文本，不编造proc读回。

L30557首条拒绝：FillRect seq72，目标43ae96100、640×480/stride640/fmt0/flagsff，56B原参数完整。旧command在resource_lookup之前只允许within(545)，故被拒。131条完整CMD：72成功、59拒绝；另4条交错/不完整原记录独立保留，不强行解析成完整数值。新目标尚无成功像素证据。

Lead msg_4c95916cbc49授权按已观测原对象修正守卫。新模型只准原成功native-open、type403、原类vptr、完整字段/本地epoch匹配、逐行span在父对象内的目标；在生命周期锁下重查，原close先撤销，源独立映射只读，源/目标为同父对象时使用同一代次别名。没有物理地址允许列表，没有宣称已证明第二屏幕/双缓冲角色。原bitmap子分配、compaction与queued ABA的既有限制仍明确保留。

原件/旧runs/既有helpers均保留；后续修正新起v17与registry v3，近似像素公式/FIFO/完成顺序/545原proc检查未改。[原目标证据]('''+pref+'''ap93-new-target-original-proof.json)与[宿主目标回归]('''+pref+'''ap93-native-target-host-check.json)。

## 证据入口

- [r2独立复核]('''+pref+'''ap93r2empty-77c94f2c-review.json) / [RM与输入]('''+pref+'''ap93r2empty-77c94f2c-rm-input-observation.json)。
- [r3独立复核]('''+pref+'''ap93r3setup-d8c86a95-review.json) / [RM与输入]('''+pref+'''ap93r3setup-d8c86a95-rm-input-observation.json) / [GPE统计]('''+pref+'''ap93r3setup-d8c86a95-gpe-statistics.json)。
- 后续同脚本运行与每步PNG待追加；目前 NO CARD图标、拍摄待机、MENU菜单和完整输入反馈均未验收。
''')
idx=D/'README.md';t=idx.read_text();assert 'ap93-empty-slots-first-setup.md' not in t;idx.write_text(t+'\n- [AP93：软件空槽与首次设置交互](ap93-empty-slots-first-setup.md)（空槽链已运行通过，首个下键触发原重绘；新原生目标守卫修正待运行）。\n');s=json.loads((R/'STATE.json').read_text());assert s.get('current_run') is None;s['AP93_completed_attempts']=[{'run':n,'review':str(R/(n+'-review.json'))} for n in ['ap93empty-9b0fd885','ap93r2empty-77c94f2c','ap93r3setup-d8c86a95']];s['AP93_report']=str(p);s['phase']='AP93_NATIVE_EMPTY_CHAIN_PASSED_FIRST_DOWN_REDRAW_NEW_NATIVE_TARGET_GUARD_FIX_HOST_PASSED';s['next_minimal_command']={'status':'Lead msg_4c95916cbc49: v17 native-open target guard fix hostASAN passed, rerun sameAP93r3 setupscript withap93-r4-native-render-target; no physicalallowlist/no extraRMprotocol'};(R/'STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');print(p)
