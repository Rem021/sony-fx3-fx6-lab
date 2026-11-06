from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parent;D=R.parents[3]/'reports/2026-11-01-fx3-vm-resumed-repair';v=json.loads((R/'ap85r4-review.json').read_text());proof=json.loads((R/'ap85-new-blocks-proof.json').read_text());base=json.loads((R/'ap84ar2-review.json').read_text());stages=['ap85a','ap85r2','ap85r3','ap85r4'];reviews={x:json.loads((R/(x+'-review.json')).read_text()) for x in stages};timeline={'scope':'All captured requests/stacks at existing selected service observation points after LCD11a; raw UIPC trace is bounded and reports drops, not a complete whole-system message history','run':v['run'],'requests':v['post_11a_full_captured_requests'],'observation_limits':v['end_stats']};(R/'ap85-post11a-requests.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2)+'\n');comp={'base':base['run'],'AP85':v['run'],'UI_updates':[base['speed_observations']['actual_UI_updates'],v['speed_observations']['actual_UI_updates']],'boot_barrier_passed':[base['barrier_passed'],v['barrier_passed']],'pin_commit_consume':[v['pin_commit_count'],v['pin_consumed_count']],'face_DMM_commit_consume':[v['face_commit_count'],v['face_consumed_count']],'face_ICDT_commit_consume':[v['face_icdt_commit_count'],v['face_icdt_consumed_count']],'GPE_AP85':v['gpe_grouped_statistics'],'approx_blend':v['GPE_approx_blend_marker_count'],'new_blocks':proof['late_OSD_pair_block'],'menu_verified':False};(R/'ap85-comparison.json').write_text(json.dumps(comp,ensure_ascii=False,indent=2)+'\n');assert v['qemu_exit']==0 and v['process_reaped'] and v['host_pid_absent'] and v['inputs_unchanged'] and not v['missing_markers'] and v['im_alive_end_compact_maps'] and all(z['released_verified'] for z in v['locks']);rows=[]
for stage,q in reviews.items():
 rc=json.loads((Path(q['run'])/'receipt.json').read_text());rows.append(f"|{Path(q['run']).name}|{rc['duration_seconds']:.2f}s|{q['qemu_exit']} / {q['process_reaped']} / {q['inputs_unchanged']} / {q['host_pid_absent']}|{len(q['missing_markers'])}|"+({'ap85a':'preload遮挡原CPversion caller；接入失败','ap85r2':'格式域混用，首snapshot安全拒绝；零ACK','ap85r3':'布局校验通过，proc/self/mem读bits失败；零ACK','ap85r4':'1358次原完成；新0400等待及后段1005待配对，未满300s'}[stage])+'|')
rel='../../work/fx3-vm-20261101/menu-repair-01/runtime/';img=Path(v['run']).name+'/osd-frame-000008-format0-RGBA-opaque.png';text=f'''# AP85：原OSD完成链已运行，菜单与新同步阻断仍开放

**部分通过：0152消费释放0，原6003/6005完成回调与绘制前置等待均验证；UI实际更新从2次升至1360次。仍只有首张黑色像素，未恢复可见菜单。** 最终轮因新同步阻断提前结束，不能称300秒完整健康验收。

## 独立运行与回收

|运行|实际时长|exit / reaped / unchanged / PID消失|缺marker数|结果|
|---|---:|---|---:|---|
{chr(10).join(rows)}

四轮原始目录均保留；双锁逐轮已核释放，im.elf末次完整/proc有映射。r2起另加既有1秒观测循环的紧凑PID/maps/uptime，r4结束窗口 `/proc/uptime=176.62` 仍有PID221的三段im.elf映射。r4无symbol lookup error、fatal/exception或OSD拒绝；[独立回执]({rel}runs/{Path(v['run']).name}/receipt.json)、[复核]({rel}ap85r4-review.json)。host退出0表示受控QMP quit和进程回收，不是guest正常关机。

## 最终接入与实测

基线为AP84r2原4×A35、MTTCG、原厂cpuset。v42新增精确0152 `0d205201100001800300010000eb8080`→`0d2052110c00018000005900`，selector3/peaking0/level1/mag0/color0/Y235Cb128Cr128，保存软件配置、硬件pending1；lease128原消费free0。原请求保留caller所有权。

headlessv3仅在原成功发送后影子1002/1003/1005，不取原队列所有权，不修改或释放原消息。FB+88/+78两个原身份锁→AddRef/ReadLock→与GPEv14共用raster guard→核bank/token/native format/stride/bitmap size/活跃545与实际CPU映射→memcpy+memcmp→逆序释放→提交环→8B软件完成。任何复制、校验或释放失败均不ACK。native发布sem绝不直接sig；记录的是原fd384→osal_sig_sem调用。

实捕首帧：bitmap枚举1、映射GPE0、FB枚举1，token402恰等1003+8；640×480/stride640，span与原bitmap size均614400B，physical43feb5100。ReadLock bits7f007dc100位于共享 `/dev/mem` 映射7f007dc000..7f00873000、offset43feb5000；CPU偏移100与物理完全一致。身份/活跃extent/原读租约和共享writer guard均通过，实际复制memcmp相同。

环41e000000/16MiB，FDT+native memrsv不重叠，8槽允许覆盖。host只读QMP；PNG编码不参与ACK关键路径。marker固定 `snapshot=ring png_pending=host_readonly original_schema_unproven=1`。8B零扩展是原接收路径至少安全读取+4..7后的软件选择，**原CP发送器、完整packet schema和面板退休/VSYNC时序未证实**。

最终1358个snapshot、1358个ACK入队、1358个原nativeSig成功；重复/拒绝/失败均0。采样74组原free0→fd384（父LR f2280/f22d0）→sem2886047 result0/matched1→原draw前置wait返回0；不同CPU日志顺序可交错，不按打印先后伪造全序。

|门控/绘制|AP84r2|AP85r4|
|---|---:|---:|
|原UI实际更新|2|1360|
|dequeue / timer dequeue|337 / 306|2905 / 2873|
|timer生产探针|12625|2873|
|a18 peak / 末值|12319 / 12318|208 / 0|
|四任务原屏障|通过|通过|
|pin请求/消费|42/42|{v['pin_commit_count']}/{v['pin_consumed_count']}|
|face DMM / ICDT提交消费|4/4 / 3/3|{v['face_commit_count']}/{v['face_consumed_count']} / {v['face_icdt_commit_count']}/{v['face_icdt_consumed_count']}|

不同运行时长且有新阻断，不把表中timer数量当速度基准。GPE统计：

|op|fmt|flags|地址是否在545 payload|result|次数|
|---|---|---|---|---|---:|
|FillRect|0|ff|dst43feb5100在；src0非源面|0|1|
|Flush|0|0|无像素地址|0|1|

原uniform Fill/Flush保持完成；近似混合/HV请求均0，无新增绘制。**只有一次1003像素快照，其余1005复用pixel_source_seq1**，1358个完成不是1358张新绘图。

## 物理读回与PNG

QMP取得232个校验有效槽，1126个中间序号被覆盖，撕裂拒绝0；host保存14份raw/28张双格式PNG。首30只捕到8..15，16..30及1..7已覆盖，every30也只保留观测到的槽；不声称完整保留前30。原环覆盖次数1350与host漏采序号含义不同。

全部实际614400B像素SHA256为 `{proof['pixel_readback']['unique_native_pixel_SHA256'][0]}`，与结束时独立545物理dump的payload相同。无非均匀像素，无可导出的非黑菜单。原format0视图已目视核对为均匀黑；format1替代解释为320×480、stride320，严格不读出原614400B范围。RGBA/opaque为解释假设，未H/V翻像素，无CP composition/面板等价。

![AP85 原软件像素：均匀黑，非菜单]({rel}runs/{img})

## 两处新阻断与未完成项

1. **VDF0400同步等待。** 原请求 `0d2000040a0001800000`，destination92840747/source81cf61c2，serial21809行。appFw2de7260发送，成功分支2de72fc timeout−1→2de7300原osal_rcv_msg_tmo；后两次SeqQueueCommon346均停fd3 ioctl80000007→osal_rcv_msg_tmo。AP84无此请求，未造回复，已escalation。
2. **后段1005描述未到。** 1358次ACK均已原消费后，新批只有1002；最终stage1/pending1005保持102.02 host秒，没有未消费ACK、软件错误或重复。原分配/发送/队列路径原因未证实，不能仅凭数量宣布pool耗尽，不能擅自收取或释放原CP队列。当前helper尚无独立pair deadline，只有owner有界运行停止；该超时和原生产者现场仍需补全后才能称稳健consumer。
3. 菜单/原按键到新帧、至少两张独立像素帧、原CP合成/面板/颜色alpha、完整300秒健康验收仍开放。此次未注入输入。

[新阻断原指令、线程与读回证据]({rel}ap85-new-blocks-proof.json)，[bitmap枚举→GPE域原跳表]({rel}ap85-format-domain-proof.json)，[AP85/AP84对比]({rel}ap85-comparison.json)。[11a后所有现有服务观测点的请求/栈时间线]({rel}ap85-post11a-requests.json)逐行索引；底层UIPC trace有capacity/lock drop，不宣称全机消息无遗漏。

## 宿主检查与接入更正

ASan/UBSan通过：0152精确黄金/逐字节变异/回滚；OSD配对、边界/零ACK/重复单ACK；实际capture/ring代码19条租约失败路径配平；native1/7与2/8映射；实际maps流式parser的大文件/跨chunk/过长行/5负例；GPE原回归、近似绘制与共享guard；26word环checksum/重复/撕裂/双视图PNG。仅对应宿主语义，原native调用另由本轮运行验证。[72段原代码与17项来源核验]({rel}ap85-audit-input-check.json)。

初轮把headless放capid前遮挡原CPversion caller；r2只纠正加载顺序。r2把bitmap枚举当GPE枚举，r3按原ef074/1de628与101890/1e220c表修正。r3通过布局后proc/self/mem读原bits失败；具体errno未采，PFNMAP解释为推断。r4按原合同在native读租约内实际memcpy，并新增真实共享devmem CPU VA/物理/span门控。所有失败轮、旧helper和原件保留。

## A7C2 在线对照

本轮联网重读[维护者当前README](https://github.com/chocotan/a7c2-qemu)与[headless源码](https://raw.githubusercontent.com/chocotan/a7c2-qemu/main/runtime/analysis/headless-osd.c)：有界读租约、writer guard及8B软件完成可作机制参考，A7固定format1/私有FB布局不能移植成FX3事实。其软件消费者实际拥有接收/释放路径，与本轮明确要求的被动影子不同。当前README区分可操作菜单和仍未完成的原拍摄成片。API SSL EOF后web回退成功，但没取得新的不可变commit ID；[在线回执]({rel}ap85-a7c2-latest-recheck.json)。
''';report=D/'ap85-software-osd-ring.md';report.write_text(text);p=D/'README.md';s=p.read_text();old='- [AP85 软件 OSD 环与0152](ap85-software-osd-ring.md)：验证进行中；首轮加载顺序回归保留，r2恢复原capid caller门控，软件完成schema明确未证实。';new='- [AP85 软件 OSD 环与0152](ap85-software-osd-ring.md)：r4原完成1358次、UI更新1360次，0152/free0；仍均匀黑，新0400同步等待及后段1005待配对开放，未满300秒。';assert old in s;p.write_text(s.replace(old,new));p=R/'STATE.json';s=json.loads(p.read_text());cp=Path(v['run'])/'command.json';command=json.loads(cp.read_text());s.update(phase='AP85_PARTIAL_OSD_COMPLETION_NEW_0400_AND_PAIR_BLOCK_WAIT_LEAD',current_run=None,current_candidate=command['candidate'],current_candidate_sha256=command['candidate_sha256'],current_candidate_classification='EXPLICIT_SOFTWARE_OSD_NATIVE_COMPLETION_PROVEN_NEW_SYNCHRONOUS_BLOCKS',last_run=v['run'],latest_stage_summary=str(R/'ap85r4-review.json'),latest_review=str(R/'ap85r4-review.json'),latest_report=str(report),ap85r4_run=v['run'],ap85r4_review=str(R/'ap85r4-review.json'),ap85_comparison=str(R/'ap85-comparison.json'),ap85_new_blocks=str(R/'ap85-new-blocks-proof.json'),missing_markers=[],im_alive_last_snapshot=True,im_alive_end_window_maps=True,inputs_unchanged=True,last_observation_candidate=command['candidate'],updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());s['ap85_in_progress']={'stage':'partial results audited; awaiting Lead next protocol/latepair decision','software_completed_publications':1358,'distinct_pixel_source_sequences':[1],'original_UI_updates':1360,'nonuniform_pixels':False,'original_completion_schema_unproven':True,'complete_300s_gate':False,'pair_deadline_implemented':False,'new_blocks':['VDF0400 synchronous wait','next1005 descriptor missing102s'],'runtime_active':False};s['next_minimal_command']={'status':'Await Lead audit/decision for VDF0400 and passive allocator/send observation; do not invent0400 reply or change original queue ownership; no QEMU running'};s['work_in_progress']='AP85 receipt synchronized; standby for Lead decision, no worker_done';s['not_closed_AP85']=['visible menu and input-to-new-frame','native CP completion schema/scanout','new0400 synchronous protocol','late1005 producer/allocation/send blocker and bounded pair deadline','300second complete healthy observation'];p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');print(report);print(json.dumps(comp,ensure_ascii=False,indent=2))
