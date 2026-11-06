"""Seal new static read/exit evidence and CPU codec, not a live package."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage252-MSC-service-entry-impact-and-admission'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
 raw=x if isinstance(x,bytes)else enc(x);fd=os.open(H/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb')as f:f.write(raw)
previous=json.loads((P/'final-receipt.json').read_text())
for x in previous['files']:
 raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes']and sha256(raw).hexdigest()==x['sha256'],x['path']
a=json.loads((H/'level-gate-and-normal-exit.json').read_text());s=json.loads((H/'stop-unblock-audit.json').read_text());t=json.loads((H/'bounded-read-test-receipt.json').read_text())
assert len(a['functions'])==17 and len(s['module_ranges'])==6 and len(s['kernel_ranges'])==7
assert t['status']=='PASS_FIXED_READ0_GUARDS_AND_OPAQUE_REPLY' and t['reset_branch_excluded']
linux=json.loads((H/'linux-reference-api-followup.json').read_text())
assert sha256((H/'linux-v4.9-udc-core.c.txt').read_bytes()).hexdigest()==linux['sha256']
read_plan=dict(status='FIXED_READ_CODEC_PREPARED_NOT_LIVE_APPROVED_OR_EXECUTABLE',
 prospective_USB=dict(VID=0x054c,PID=0x0336,identity_binding_required_separately=True),
 request=dict(pFunc=0x10,category=0,command=0x1f,read_argument=0,sequence=1,bytes=17,hex='05000000100001000000000000001f0000'),
 reply=dict(max_bytes=100,payload_bytes=88,response=1,raw_payload_returned_by_codec=False,output='per-trial HMAC only'),
 forbidden=dict(reset_argument=0x80,arbitrary_command_or_payload=True,file_upload_or_firmware_operations=True),
 static_capability_requirement='Stock A or B table, level2 or3; reply cannot establish highest level3 or firmware identity.',
 effect_scope='Read branch of command body only. Full authentication/history, module loading and error logging remain separate effects.',
 does_not_complete_authentication_or_thread_exit_proof=True,contains_live_backend=False,approved=False)
put('fixed-read-candidate-plan.json',read_plan)
decision=dict(status='STOP_CHALLENGE_ONLY_BRANCH_PREPARE_FULL_ENTRY_EXIT_FLOW',
 reason='A conditional initial-MSC abort has no established cancellation trigger: normal callback handles only event1, while known NIN cancellation is in the semaphore-driven full supervisor. Serialize can wait indefinitely for cancellation.',
 not_a_measured_hang_or_exhaustive_absence_of_other_cancellers=True,
 fixed_read_candidate_found=True,read_grade_lower_bound=2,read_proves_grade3=False,
 STOP_wakeup_and_read_completion_are_separate=True,kernel_receive_minus4_maps_to_internal_minus15=True,
 host_return12_pass_preserved=True,new_live_package_ready=False,new_live_authorization=False,
 next='Bind the normal supervisor semaphore/resource handoff and Senser end callback into complete entry/exit flow; account for history writes and ignored cancel/join returns before fixing a new live package.',
 no_more_challenge_only_or_status12_model_loops=True,new_live_operations=0,first_flash_released=False)
put('admission-decision.json',decision)
readme='''# FX3 受限读取候选与初始MSC退出路径

2026年10月31日。**找到受认证级别限制的固定读取候选，并完成纯CPU编解码；退出缺口已定位到普通应用的取消/回收触发链。** 本轮全部离线，没有新的真机验收。12号Mac接管/归还通过仍保留，Sony完整进入/退出包尚未就绪。

## 已落实的读取候选

从固定官方nflasha15镜像提取原libpro00.so（6032字节，SHA256为771749c2397c48e9a3444a7562a8f8e2773abf59a262276c2b225cc415ac9403），只作数据解析。libsencore的ProductInfoFunc按libpro%02X.so与command%04X分派到command001F。

原pFunc表A、B有0x10 ProductInfo，C没有；onComplete分别将级别3、2、1映射至A、B、C，其它值清表。因此在这些原始绑定成立时，读取可用能区分A/B与C，不能单独证明最高级别3，更不是实机固件哈希或线程退出证明。

同一个0x001F命令包含两种不同效果：

| 参数 | 原处理分支 | 结果边界 |
|---|---|---|
| 0 | 分配88字节，调用Read_Hasp；按0x101000只读方式打开/setting/.hasp，读88字节并关闭 | 此读取函数没有直接write/fsync调用；成功返回1。不能扩大成整个认证会话零写入 |
| 0x80 | 调用Reset_Hasp | 0x101241写/创建/截断方式打开，实际调用write与fsync；必须排除 |

固定[候选计划](fixed-read-candidate-plan.json)只有一个17字节请求，内层为pFunc0x10、category0、command0x001F、单字节参数0；预期服务身份0336另须真实绑定。与[PMCA维护者readHasp实现](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L1013)的参数对齐，FX3具体分支和表门控来自本次原件核对。

[bounded_hasp_read.py](bounded_hasp_read.py)不含I/O或启动入口。它只生成/校验固定读取请求，拒绝重置参数和额外负载；返回帧最多100字节（12字节头和88字节数据），仅向调用者输出临时密钥HMAC与长度等信息，不输出原HASP内容，也不将回复升级为认证或退出成功。实际接入接收器时须另行保证原始服务记录的存储范围，不把这个CPU接口当作已部署的隐私保障。

[检查回执](bounded-read-test-receipt.json)通过：9种危险/变异请求、5种错误回复、4种无效序号和3种无效密钥均被拒绝；仅使用人工载荷，无机身读取。原始HASP可能包含服务身份/历史信息；这不是备份，也没有读取用户机身上的文件。

## 退出链的新定位

1. 原libObj普通协作者回调0xea128仅处理事件1，对其它事件直接返回。它与独立服务模式的WorkerThreadManager不是同一条取消链，实际机身的注册与所有其它取消来源也未测量。
2. 普通应用确有监督线程0xea750：在sem_wait之后调用0xec458取消NIN、0xec4bc等待；后续结束阶段通过0xea3e0处理工作线程。join包装器检查pthread_join返回并仅在成功时清句柄，但这两个已审查调用者没有消费其成功/失败返回值。不能凭状态推进或新PID认定回收完成。
3. 精确7.02 usbg_sen.ko的core_stop设置中断位2并唤醒队列；接收等待条件却是完成位1。完成回调才设置位1并唤醒。条件cleanup中的usb_ep_dequeue返回值未检查；唤醒与完成不能合并为一个事件。
4. 在已完成、被中断的接收路径中，内核count=-4被libInfraUsbCmn映射为内部-15，进入252核对的Serialize通用负值取消等待循环，并非-6/-4专用互斥锁释放分支。要结束仍需要正确的取消触发和回收。

这里形成的是带明确前提的反例：若选择普通协作者且没有其它取消者，只取挑战就省略完成/资源交接，而非事件1的回调又直接返回，则尚未建立谁来取消NIN；它可能留在等待取消的循环。**没有在真机制造或观察到这个挂起，也没有宣称不存在其它回收路径。** 此反例足以停止把“挑战次数更少”直接当作退出更安全的依据。

本轮还固定核对了gcore/gcw转发、DWC3 dequeue/giveback及usb_gadget_giveback_request等7个原内核符号范围。DWC3有直接giveback路径，也有局部返回0而未直接调用giveback的分支；实际端点绑定、请求状态和中断进度未测，不能据此宣布驱动缺陷。Linux v4.9的[原始API说明](https://github.com/torvalds/linux/blob/v4.9/drivers/usb/gadget/udc/core.c#L260)与新版异步说明不同，本轮使用版本对应参考，不用现代契约套FX3。即使一次dequeue按契约完成，也不能单凭该返回值证明用户态NIN已经join成功。

## 下一步与范围

停止推进仅挑战候选，不重复12号接管诊断。下一项转为普通应用完整进入/资源交接/服务结束的适配：把监督线程的信号量、资源回调及Senser结束回调接通，明确忽略cancel/join返回值时如何保留UNKNOWN，再固定完整的进入/退出范围。认证可能更新历史或模式状态，不能称作整个会话只读。

本轮核对17个原ELF完整函数、6段明确的模块代码范围、7个内核符号范围和56处指令；没有执行原Sony/Linux指令。[读取门控与普通监督路径](level-gate-and-normal-exit.json) · [精确停止/解阻塞审查](stop-unblock-audit.json) · [读取与重置区别](read-versus-reset-supplement.json) · [准入结论](admission-decision.json)。GPL参考仅作参考，实际7.02原字节与运行状态分别记录。

G01至G16及现有授权不变，没有新增USB缓存、管理员、Sony认证、机身读文件、上传或固件写入。完整同机健康备份、独立救砖、MAIN1080p H.265和最小持久化准入仍未通过，首刷未放行。
'''
put('README.md',readme.encode())
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();g=json.loads(gb);assert gb==(P/'goal-status-after.json').read_bytes()
keep={k:g[k]for k in ['requirements','authorization','authorization_consumption','prepared_owner_status12_trial','owner_status12_live_execution','prepared_root_host_trial','prepared_first_device_trial','research_priority']}
now=datetime.now(timezone.utc).isoformat();g['updated_utc']=now;g['latest_stage']=H.name
g['research_activity']='Offline extracted original libpro00 6032B and pinned17whole ELF functions,6module code ranges,7kernel symbol ranges/56instruction checks. ProductInfo001F arg0 reads88B Hasp, present in stockA/B notC; samecmd arg80 actually writes/resets/fsyncs. Added exact17B request/max100B opaque-HMAC reply codec,9request/5reply/4sequence/3key rejections, no IO. Normal callbackea128 ignores non-event1; normal supervisor sem_wait then NIN cancel/join exists, callers ignore returns. Exact702 stop setsINTR2 while receive waitsCOMP1; completed interrupted count-4 maps to-15 ->Serialize cancellation loop. Initial-MSC abort lacks established canceller absent full resource handoff; no real hang claimed. Stop challenge-only branch; prepare complete normal entry/resource/end flow. No new live operations;251pass/11UNKNOWN/all16/grants retained.'
g['recovery_level_gated_read_and_normal_stop_unblock']=dict(readme=str((H/'README.md').relative_to(R)),candidate=str((H/'fixed-read-candidate-plan.json').relative_to(R)),codec=str((H/'bounded_hasp_read.py').relative_to(R)),static_audit=str((H/'level-gate-and-normal-exit.json').relative_to(R)),stop_audit=str((H/'stop-unblock-audit.json').relative_to(R)),tests=str((H/'bounded-read-test-receipt.json').relative_to(R)),original_plugin_bytes=6032,static_read_grade_lower_bound=2,highest_grade3_not_proven=True,request_bytes=17,max_reply_bytes=100,read_body_bytes=88,reset80_rejected=True,initial_MSC_abort_cancellation_not_closed=True,challenge_only_route_stopped=True,live_operations=0,new_live_package_ready=False,new_live_authorization=False,milestone2_complete=False)
g['next_safe_offline_actions']=[
 '251实机Mac接管归还子步骤已通过，不重复。253固定ProductInfo001F/read0候选与17B/100B纯CPU编解码，原A/B有门控、C无；0x80重置写入明确拒绝，仍无实际Sony请求。',
 '停止仅挑战候选：普通回调只处理event1，而已知NIN取消/等待位于完整资源监督流程；在没有其它取消者的声明条件下，省略完成/资源交接会缺取消触发。该反例非实机故障，不再为同一4传输方案追加模型。',
 '下一步接普通应用完整进入/资源交接/服务结束回调：确定监督线程信号量与结束信号的实际来源，分别处理NIN及工作线程取消/等待返回。不要套用独立服务Worker取消链，也不以新PID、唤醒、6/1或本地清标志充退出。',
 '完整新发送/退出固定方案前不申请或执行Sony试验；认证历史/模式可能写入须明确。原16项、12号及旧单次授权消耗状态保持，完整备份/独立恢复/MAIN HEVC/持久化未通过，首刷不放行。'
]
for k,x in keep.items():assert g[k]==x,k
assert not g['goal_complete']and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();text=rb.decode();overview=next(x for x in text.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-31 FX3受限读取与初始MSC退出路径](<work/sony-firmware-20261024/stage253-level-gated-read-and-stop-unblock/README.md>)：原插件固定001F/read0的88B读取，A/B门控、C无，排除同命令80重置写入；17B/100B编解码检查通过。普通监督线程及STOP解阻塞路径已定位，初始MSC取消触发未闭合，停止仅挑战方案；无新设备操作。'
assert H.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();assert '最新研究证据为第252阶段。'in text;text=text.replace('最新研究证据为第252阶段。','最新研究证据为第253阶段。',1)
needle='[本轮结论](../../work/sony-firmware-20261024/stage252-MSC-service-entry-impact-and-admission/README.md)。'
assert needle in text;text=text.replace(needle,needle+' 253找到受A/B级限制的88字节读取分支并完成固定参数编解码；同命令的重置写入已排除。初始MSC监督取消路径与独立服务链不同，仅挑战方案停止，完整进入/退出仍待适配。[最新候选与退出定位](../../work/sony-firmware-20261024/stage253-level-gated-read-and-stop-unblock/README.md)。',1)
old='Mac接管归还子步骤已由251实测关闭。252的阶段影响及判定器已完成；下一步补初始MSC实际处理者与只读、受认证级别限制的验证指令，并追STOP到底层接收解阻塞和可观察完成条件。不重复接管或同一4传输模型，不以6/1、MSC类查询或清本地标志冒充认证/退出。完整固定发送与退出方案齐全后才提交新范围；已消耗授权不复用。'
new='Mac接管归还子步骤已由251实测关闭。253已落实001F/read0只读命令候选（不证明最高级3权限），并定位普通监督线程与接收中断/取消循环。仅挑战方案停止。下一步接完整进入/资源交接/服务结束的信号量与回调来源，补取消/等待返回的处理，再形成完整固定方案；不重复接管或同一4传输模型，不复用消耗授权，不以协议/状态变化冒充线程完成。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,status='OFFLINE_LEVEL_GATED_READ_CODEC_AND_INITIAL_MSC_EXIT_PATH_COMPLETE_NO_LIVE_RELEASE',previous_manifest_sha256=sha256((P/'final-receipt.json').read_bytes()).hexdigest(),previous_members_reverified=len(previous['files']),whole_original_ELF_functions=17,module_ranges=6,kernel_symbol_ranges=7,instruction_checks=56,request_rejections=9,reply_rejections=5,sequence_rejections=4,key_rejections=3,new_original_instruction_or_guest_execution=False,new_camera_USB_cache_admin_or_firmware_operations=0,host12_pass_preserved=True,old11_unknown_preserved=True,all16_and_authorizations_unchanged=True,new_live_package_ready=False,new_live_scope_approved=False,challenge_only_route_stopped=True,goal_complete=False,persistent_write_release=False,heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
files=[]
for p in sorted(H.rglob('*')):
 if p.is_file():
  raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage253-level-gated-read-and-normal-stop-v1',member_count=len(files),files=files,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(files),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),live_operations=0)))
