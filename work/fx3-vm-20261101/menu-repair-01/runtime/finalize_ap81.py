from pathlib import Path
import json,re,collections,datetime,hashlib
R=Path(__file__).resolve().parent;p=R/'ap81-review.json';v=json.loads(p.read_text());g=v['gate_readback'];run=Path(v['run']);ls=(run/'serial.log').read_text(errors='replace').splitlines();receipt=json.loads((run/'receipt.json').read_text());assert v['qemu_exit']==0 and v['process_reaped'] and v['inputs_unchanged'] and not v['missing_markers'] and v['im_alive_last_snapshot'] and not v['fatal'] and receipt['host_observer_error'] is None and not receipt['guest_exception_markers'] and all(z['released_verified'] for z in v['locks']);v['skd_events']=[{'line':i+1,'text':x} for i,x in enumerate(ls) if 'FX3_SKD_' in x or 'Error SKD_CipherInit err=' in x];v['gpe_commands']=[];groups=collections.Counter()
for i,x in enumerate(ls):
 if 'FX3_GPE_CMD ' not in x:continue
 d=dict(re.findall(r'(\w+)=([^ ]+)',x.split('FX3_GPE_CMD ',1)[1]));addr=int(d.get('dst_phys','0'),0);src=int(d.get('src_phys','0'),0);d.update(line=i+1,dst_in_545=(0x43feb5000<=addr<0x43fff5000) if addr else None,src_in_545=(0x43feb5000<=src<0x43fff5000) if src else None);v['gpe_commands'].append(d);groups[(d.get('op'),d.get('fmt'),d.get('flags'),d['dst_in_545'],d['src_in_545'],d.get('result'))]+=1
v['gpe_statistics']=[dict(zip(['op','fmt','flags','dst_in_545','src_in_545','result','count'],[*k,n])) for k,n in groups.items()];v['logical_first_draw']=json.loads((run/'osd-first-draw.json').read_text());v['post_11a_full_captured_requests']=[{'line':i+1,'text':x} for i,x in enumerate(ls) if i>=next((j for j,y in enumerate(ls) if 'FX3_LCD_BRIGHTNESS_COMMIT' in y),len(ls)) and any(k in x for k in ['FX3_BOOT_TAIL_REQUEST','FX3_BOOT_TAIL_FRAME','FX3_UIPC_SEND_UNIQUE','FX3_UIPC_SYNC_RETURN'])];v['new_pending_request']=json.loads((R/'ap81-next-pin-capture.json').read_text());v['single_panel_barrier']={'entry':g['counts']['46'],'return':g['counts']['47'],'records':[z for z in g['boot_records'] if z['id'] in [46,47]]};v['skd_verdict']={'exact_mmap_unavailable':any('FX3_SKD_HW_UNAVAILABLE' in x for x in ls),'native_CipherInit_errors':[int(re.search(r'original_result=(-?\d+)',x)[1]) for x in ls if 'FX3_SKD_CIPHER_RESULT ' in x],'data_statuses':[int(re.search(r'status=(\d+)',x)[1]) for x in ls if 'FX3_SKD_DATA_ENCRYPTION_STATUS ' in x],'data_ret_count':g['counts']['50'],'access_auth_ret_count':g['counts']['51'],'key_material_fabricated':False};v['ui_progress']={k:g['statistics'][k] for k in ['dequeue_total','timer_dequeue','backlog_skip','time_skip','time_pass','last_a18','mirror_skip']};v['boot_notify_records']=[z for z in g['boot_records'] if z['id'] in [35,36,37,38,39,41]];assert v['skd_verdict']['exact_mmap_unavailable'] and v['skd_verdict']['native_CipherInit_errors']==[-1020,-1020] and v['skd_verdict']['data_statuses']==[2,2] and g['counts']['51']>=1;assert v['ui_progress']['dequeue_total']>2 and v['ui_progress']['timer_dequeue']>1;v['classification']='HEALTHY_BOOT_NOTIFY_UI_TIMER_UNIFORM_CLEAR_CONFIRMED_NEXT_PIN_PENDING';p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v[k] for k in ['run','missing_markers','im_alive_last_snapshot','barrier_passed','skd_verdict','ui_progress','gpe_statistics']},ensure_ascii=False,indent=2))
D=R.parents[3]/'reports/2026-11-01-fx3-vm-resumed-repair';report=D/'ap81-skd-unavailable-ui-clear.md';rows='\n'.join('|'+ '|'.join(str(z[k]) for k in ['op','fmt','flags','dst_in_545','src_in_545','result','count'])+'|' for z in v['gpe_statistics']);report.write_text(f'''# AP81：SKD不可用降级后UI恢复与首清屏

本轮240秒`{run.name}`通过健康运行回执：qemu_exit0、process_reaped/宿主PID不存在、inputs_unchanged、missing_markers=[]、末次/proc maps含im.elf，无新增external abort/symbol lookup/fatal，两锁释放后已重取核验。原启动链、UI future、timer与软件GPE首清屏均已出现；**尚无菜单内容或可操作验收**，后续新pin请求未扩展回复。

## 精确硬件不可用合同

保持AP80c capidv36全部模型，新增first-preload `fx3-skd-hw-unavailable-v1`。只在调用返回点`/usr/lib/libInfraSKD.so+645ec`（原BL+645e8）、addressNULL、offsetffffb000、len1000、prot1、flags1且fd readlink为`/dev/mem`时返回MAP_FAILED/ENODEV；其他mmap保持原参数、返回值及errno。没有ROM/零页/随机页、没有密钥/身份材料，没有改f340f000/f13b8000，没有强制CipherInit成功。宿主ASan/UBSan验证精确命中和相邻offset/len/prot/flags/fd/caller/模块/关闭profile原样转发。

实际只命中一次SKData_Init映射；原CipherInit两次返回−1020，data_encryption两次写status2并到原ret2eaa0d8，认证sequence到原ret2bcc544。原错误路径是非致命的；本轮只证明该路径运行，没有加密成功或认证功能验收。

gatev10保留原52个被动点的寄存器/指令检查与自检，新增CipherInit返回、data状态/返回、认证ret；在原boot future返回后停止观察旧event，避免AP80c所披露的对象生命周期后悬空字节读。统计count槽扩展64，原计数含义保留；QMP解码同步更新，未改原worker/notify。

## 启动、UI与GPE

四任务原屏障通过；panel单任务入口{g['counts']['46']}次/公共返回{g['counts']['47']}次，原返回0。QMP独立读回虚拟panel配置：{json.dumps(g.get('panel_config'),ensure_ascii=False)}。这与原1119消费、run_i0、notify→同event/cv首次返回的原记录互相支持；control3/osd0不修改逻辑framebuffer，原TP消费仍未证实。

QMP末次dequeue_total={g['statistics']['dequeue_total']}、timer_dequeue={g['statistics']['timer_dequeue']}、last_a18={g['statistics']['last_a18']}。176fb4c原timer与info/table/fill到达，1004、GPE清屏/Flush和8288076c发布事件见完整timer_events；这是原路径恢复，不是补发1004/强制清屏。所有计数只限本轮，不将AP72/73没有观测到绘制的旧回执追写成通过。

|op|fmt|flags|dst在545|src在545|result|次数|
|---|---|---|---|---|---|---|
{rows}

地址范围按v13原545合同`43feb5000+140000`；Flush没有像素地址，表中None表示不适用。首次FillRect后QMP暂停读`43feb5100/12c000`，SHA256为{v['logical_first_draw']['readback_sha256']}。format0-le16与format1-le32的640×480/stride640/RGBA/opaque假设各导出一张，均为均匀黑清屏（nonuniform=false），已查看图像。**两张都是logical framebuffer原字节解释，control3不导致导出旋转；不代表物理LCD/多plane最终scanout，不是菜单截图。**

![format0逻辑清屏](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/{run.name}/osd-first-format0-le16-RGBA-opaque.png)

[format1逻辑清屏](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/{run.name}/osd-first-format1-le32-RGBA-opaque.png)；[物理读回和两种格式假设](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/{run.name}/osd-first-draw.json)。两者PNG哈希相同，仅说明当前均匀面在两种解释下一致，不验证未来非均匀图的格式/通道。

## 新等待与限制

后续TID327发Dataflow48B到90050004/source81cf61c2：`c261cf81a0a0a0a001003000180000003000000000000000001000001800020000000000020000000100000000000000`，GET type0/dir2/index1。该owner不在既有22endpoint合同，原样委派、未新增回复；已escalation。原栈DF+33f20→app2e10ab8→2e10dec→2e11180→2ebe5ec→2ebeb40→2de1fb0→2d11e50→2d2f40c。消息参数及14层FP/LR已冻结，终态QMP提供当前CPU寄存器，**未单独取得睡眠TID327的完整寄存器集**，不将其冒称为原线程寄存器。菜单/后续资源连接仍待Lead审计。

QMP gate mirror_skip={g['statistics']['mirror_skip']}、boot overflow={g['extended_header'][6]}；旧UIPC仍有去重/文件写统计丢弃，完整时间线指全部已捕获0x11a后raw/栈/unique序列，不是系统无损包流。末次bank为最后完成发布，可略滞后于暂停中的回调。

[完整回执/命令统计/0x11a后捕获时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-review.json)；[QMP计数/软件图/面板控制读回](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-gate-readback.json)；[新pin原包与栈](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-next-pin-capture.json)；[宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/skd-hw-host-check.json)；[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap81-skd-hardware-unavailable/candidate81.json)。
''');s=json.loads((R/'STATE.json').read_text());s.update(phase='AP81_REVIEWED_UI_CLEAR_WAIT_NEXT_PIN',ap81_run=str(run),ap81_review=str(p),latest_report=str(report),latest_stage_summary='SKD exact hardware-unavailable path nonfatal; healthy im, nativeboot/UI timer resumed, GPE fill+flush and publication, physical545 readback uniform black logical PNG; next90050004 getpin pending',healthy_im=True,im_alive_last_snapshot=True,barrier_passed=v['barrier_passed'],boot_notify_verified_serial=True,boot_future_return_verified_serial=True,ui_resumed_dequeue=True,current_candidate_classification=v['classification'],last_reviewed_nonfatal_candidate=str(R/'ap81-skd-hardware-unavailable/candidate81.json'),work_in_progress='Wait Lead next90050004 owner audit; no additional reply/input injection',not_closed=['90050004 getpin lifecycle/next application initialization','nonuniform menu content/render/input acceptance','physical camera/audio/IMU/panel equivalence and actual encryption/authentication not verified'],next_minimal_command={'status':'Wait Lead accepted next-pin contract; no speculative descriptor or key injection'},updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(R/'STATE.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');idx=D/'README.md';t=idx.read_text();idx.write_text('当前回执：[AP81 SKD不可用降级后UI恢复/首清屏](ap81-skd-unavailable-ui-clear.md)。健康运行通过，已有均匀逻辑PNG，菜单内容仍未验收；AP80c失败现场保留。\n\n'+t.replace('当前回执：','历史回执：'));print('AP81 report/STATE/index synchronized')
