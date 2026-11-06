"""Seal current source/build/own-child receipts without any native launch."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage255-native-generation-and-service-stream'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    raw=x if isinstance(x,bytes)else enc(x)
    fd=os.open(H/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb')as f:f.write(raw)
previous=(P/'final-receipt.json').read_bytes();assert sha256(previous).hexdigest()=='aaef5296dd35b0c46fc271e5fbef21127ae9e709956c45d01cecba5b471cce4a'
for x in json.loads(previous)['files']:
    raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes']and sha256(raw).hexdigest()==x['sha256'],x['path']
build=json.loads((H/'build-receipt-v4.json').read_text())
for x in build['sources']:assert sha256((H/x['path']).read_bytes()).hexdigest()==x['sha256'],x['path']
for x in build['builds'].values():assert sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256']
checks=json.loads((H/'integration-test-receipt.json').read_text());bounds=json.loads((H/'final-boundary-test-receipt.json').read_text());scope=json.loads((H/'current-scope-test-receipt.json').read_text());analysis=json.loads((H/'analysis-receipt.json').read_text())
assert(checks['checks'],bounds['checks'],scope['checks'])==(5,2,2) and analysis['diagnostics']==0
assert all(x['status']=='PASS'for batch in [checks,bounds,scope]for x in batch['rows'])
assert '#define FX3_SERVICE_PROFILE_READY 0'in(H/'service_profile.h').read_text()
assert 'native service launch rendering remains closed'in(H/'fixed_launch.py').read_text()
now=datetime.now(timezone.utc).isoformat()
decision=dict(status='ROOT_SERVICE_FLOW_SOURCE_AND_PRIVATE_IPC_INTEGRATED_OFFLINE_LIVE_ENTRY_CLOSED',
    root_entry_adapter_integration_implemented=True,
    actual_root_helper_executed=False,actual_IOKit_backend_executed=False,
    real_own_child_and_kernel_identified_Unix_peer_tested_as_unprivileged_user=True,
    pipe_callbacks_artificial_not_camera_emulation=True,
    new_frame_schema='512B FX3FLOW1 per-call chain and1024B FX3RCPT2 final envelope',
    raw_before_decode_and_root_private_before_send=True,
    normal_fixture_frames=80,old_object_cleanup_delegated=True,
    service_error_and_stop_before_next_call_retain_UNKNOWN=True,
    global_camera_state_remains_UNKNOWN_even_on_nominal_host_return=True,
    remaining=[
        'Implement/fix real SERVICE descriptor discovery/validation and control-only exit on mismatch. Native profile remains deliberately absent; do not put fixture endpoint data into production.',
        'After the complete path is reviewable, bind a fresh current cache target, nonce, privacy material and service-scope one-shot permit into a new fixed trial package. No old permit or authority is reusable.'
    ],
    native_profile_ready=False,native_launch_rendering_enabled=False,
    new_approval_package_created=False,new_authority_requested=False,
    milestone2_complete=False,persistent_write_release=False)
put('admission-decision.json',decision)
readme='''# FX3 主机入口整合与逐调用私有回执

2026年10月31日。**255的原生组件已接入完整主机入口候选，新增的原始回执、对象转交及异常保留逻辑已通过普通用户子进程整合测试。** 本轮实际运行的是不链接IOKit的自写测试程序，USB管道全部人工提供；管理员入口和相机后端仅编译，没有运行。

## 已经落到代码的整合

- [主机入口](owner_entry_main.c)连接同进程接管对象、已核对的父进程/Unix连接、新范围许可解析器、共享进度与逐调用私有日志。新范围使用schema4/独立scope、独立grant命名及FX3RCPT2最终帧，旧状态许可和旧最终帧不能直接套用。
- [普通接管端](owner_iokit.c)通过[原生委托](flow_native.inc)将已经打开的MSC650对象转交一次，并清空原指针。转交后，旧release/return/close回调只接受新流程的完成状态，不再使用旧句柄关闭设备或归还驱动。
- [实际C流程](service_flow.c)连接MSC交换、旧对象释放、新SERVICE绑定、SERVICE交换、固定read0、结束及新MSC归还请求。使用255的固定帧和显式分模式摘要，不增加任意文件、上传或固件命令。
- [回执写入](flow_journal.c)在每次控制、批量读写和对象释放前后记录原始结果：先写私有文件并fsync，再发送到已验证的Unix连接。每帧含helper身份、nonce、范围摘要、序号及摘要链；没有原串号、挑战、摘要材料或HASP原文。
- [父端](supervisor.py)先保存收到的原始512B帧，再由[新解码器](flow_receiver.py)核对身份、顺序、调用配对、同机标签、交换次数和88B读取范围。通信结果先存，后续清理不会覆盖它；最终帧还要与接管前的私有机身标签对应。

逐调用记录解决了255的last_call会被下一步覆盖的问题。另在每次真正原生调用前检查停止请求，因此认证批次中途收到取消后，不会继续启动下一次IN/OUT。失败或未返回的调用保留UNKNOWN和原实例，不重发、重置或强杀。

## 实际完成的验证

| 范围 | 证据与结果 |
|---|---|
| 最终候选构建 | [v4构建回执](build-receipt-v4.json)：native helper、无IOKit的ASan/UBSan测试helper、主机IPC库均编译；native helper SHA256为0b7cc928ab10f5211076c111635f35b3323b5c49e4f277cf6323566dbed2d47c |
| 正常整合 | [当前构建测试](current-scope-test-receipt.json)：真实普通用户子进程与内核识别的Unix连接走完整人工管道流程；80条父端原始帧与子进程私有日志逐字节相同；最终两个vendor范围标志均为1；旧清理回调没有再次执行 |
| 部分失败 | SERVICE第一次OUT返回人工STALL后，报告OWNER_RETAINED；不重放、不释放服务对象、不归还驱动、不标记完成。最终构建也验证了该状态 |
| 认证中途停止 | [取消回归](final-boundary-test-receipt.json)：初始MSC第一次OUT后设置停止请求；下一次IN、后续SERVICE、对象释放及驱动归还均未启动，原实例保持UNKNOWN |
| 来源与损坏记录 | [5组整合检查](integration-test-receipt.json)：错误self-image在接管前拒绝；nonce、出生身份、序号、摘要链、错配返回、改变调用对象、虚构证明及缺失调用链不能充成功；旧范围/旧最终帧/未放行factory拒绝 |
| 静态检查 | [分析回执](analysis-receipt.json)：5个当前相关C单元无诊断。源文件与最终构建摘要一致；测试程序没有IOKit依赖，没有运行下载或Sony/Linux原代码 |

测试按代码改动分批：早期5组、补逐调用取消后的2组、最终vendor标志和回执的2组。它们不是9次相机试验；测试中的取景/相机线程/物理录制均未验证。初次构建暴露的POSIX F_OK名称冲突已通过独立状态名前缀修复。早期核查脚本的一处guard字段偏移已按原结构改正，失败记录保留，没有重复已完成的初次正常子进程。

测试程序发生保留状态时，只使用其专有的人工退出门清理测试子进程；该门不出现在实际相机分支，不能当成真实阻塞I/O的终止或恢复方法。所有测试子进程均已确认退出，没有终止其它历史进程或观察器。

## 下一步与当前放行状态

**剩余主要代码缺口是SERVICE描述符发现、配置核对及不匹配时的控制退出。** [service_profile.h](service_profile.h)仍固定READY=0，没有把测试端点填进真机配置；实际入口在接管前停止。缓存节点、nonce和隐私材料也尚未固定到新试验包，native渲染/factory保持关闭。当前没有可执行的新批准包，也没有暂存、Terminal、sudo或相机命令。

这一项补齐后，再形成一次性的完整Sony通信诊断包，明确认证可能更新历史/模式、可选读取机身.hasp文件的范围及失败处置。不能沿用原“不认证、不读机身文件”的授权。首次Sony通信诊断仍与首次持久刷写分开。[准入结论](admission-decision.json)。

正常人工流程只报告HOST_RETURN_CAMERA_STATE_UNVERIFIED；全局相机状态仍写UNKNOWN。内部结束通知、USB返回与相机线程完成继续分别判断，不因整合测试通过降低G01至G16。12号真实Mac接管归还通过及11号UNKNOWN保留；完整同机备份、独立恢复、MAIN1080p H.265和最小持久化尚未通过，首刷未放行。[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)。

[基于原封存源码的差异](source-changes.diff) · [复制来源与摘要](source-copy-receipt.json)。原250/255代码、许可和所有历史回执保持原样。本轮依据的公开通信参考仍为[固定PMCA维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890)，不把公开参考族等同于FX3实机认证接受。
'''
put('README.md',readme.encode())
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();assert gb==(P/'goal-status-after.json').read_bytes();g=json.loads(gb);assert len(g['requirements'])==16
preserve={k:x for k,x in g.items()if k not in ['updated_utc','latest_stage','research_activity','next_safe_offline_actions']}
g['updated_utc']=now;g['latest_stage']=H.name
g['research_activity']='Integrated native C service flow into copied root entry/owner framework: exclusive650 object transfer, delegated stale cleanup, new scope/schema4/FX3RCPT2,512B per-call private fsync-before-peer-send chain and raw-save-before-decode parent. Real unprivileged own child/kernel Unix peer test with artificial pipes produced80 matching raw frames and no legacy double cleanup. Service STALL and stop between auth OUT/IN retain UNKNOWN without later calls. Wrong self-image stops before owner; corruption/old-scope checks pass. Current v4 native/fixture/IPC build and5C static analyses pass. Actual root/IOKit not executed; SERVICE profile READY0 and native rendering closed, no new grant/package. Global camera UNKNOWN retained even nominal fixture. Next implement SERVICE descriptor/mismatch control exit, then bind fresh one-shot package. All16/12pass/11UNKNOWN/grants unchanged.'
g['recovery_root_service_flow_private_receipts']=dict(
    readme=str((H/'README.md').relative_to(R)),root_entry=str((H/'owner_entry_main.c').relative_to(R)),flow=str((H/'service_flow.c').relative_to(R)),journal=str((H/'flow_journal.c').relative_to(R)),receiver=str((H/'flow_receiver.py').relative_to(R)),build=str((H/'build-receipt-v4.json').relative_to(R)),tests=str((H/'current-scope-test-receipt.json').relative_to(R)),decision=str((H/'admission-decision.json').relative_to(R)),
    native_sha256=build['builds']['native']['sha256'],root_flow_source_and_IPC_integrated=True,actual_root_or_IOKit_execution=False,fixture_normal_frames=80,real_camera_calls=0,SERVICE_profile_ready=False,native_factory_closed=True,new_live_package_ready=False,milestone2_complete=False)
g['next_safe_offline_actions']=[
    '256已把原生组件接到主机入口/对象转交/跨代清理/新scope与私有IPC回执。普通用户真实子进程和人工USB管道的整合、失败保留、取消后不启动下一调用及原始日志一致性通过；实际root/IOKit未运行，不重复已完成的同一正常链。',
    '下一项实现SERVICE匹配节点的描述符发现、固定配置核对，以及不匹配时只走已审查控制退出的分支；READY目前0，禁止用人工端点或仅端口一致放行。保持原逐调用记录和UNKNOWN边界，不用USB返回冒充相机线程完成。',
    '完整进入/退出代码与新分支固定后，才绑定新鲜缓存目标、nonce、隐私材料及新service单次许可，生成独立完整试验包。当前native渲染/工厂关闭，没有新授权；不复用12或旧状态范围。认证历史/模式影响和.hasp读取要在新范围明示。',
    '12号实机Mac子步骤与11号UNKNOWN、G01至G16保持。完整备份/独立救砖/MAIN HEVC/持久化准入未通过，首刷不放行；不重建用户已清除的自动目标。'
]
for k,x in preserve.items():assert g[k]==x,k
assert not g['goal_complete']and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();text=rb.decode();overview=next(x for x in text.splitlines()if x.startswith('- [FX3实施路线与当前进度]'));assert H.name not in text
entry='- [2026-10-31 FX3主机入口整合与逐调用私有回执](<work/sony-firmware-20261024/stage256-root-service-flow-and-private-receipts/README.md>)：原生组件已接主机入口、独立通信范围和对象转交；80条人工管道原始回执与子进程私有日志一致，失败/中途停止保留UNKNOWN。完整候选编译，实际root/IOKit未运行；SERVICE发现与不匹配退出仍待补，真机入口关闭。'
ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();assert '最新研究证据为第255阶段。'in text;text=text.replace('最新研究证据为第255阶段。','最新研究证据为第256阶段。',1)
start=text.index('最新进展：');end=text.index('\n\n下面8项',start)
text=text[:start]+'最新进展：12号实机Mac接管归还子步骤通过，11号UNKNOWN保留。[实际结果](../../work/sony-firmware-20261024/stage251-authorized-owner-status12/README.md)。256已把跨MSC/SERVICE的原生组件接到完整主机入口候选，加入对象仅转交一次、新范围及逐调用私有回执。普通用户真实子进程与人工管道的正常/失败/中途停止检查通过，80条原始帧与子进程日志一致；实际root和IOKit未运行。主要剩余代码缺口是SERVICE描述符发现与不匹配时的控制退出，真机入口仍关闭。[最新整合与证据](../../work/sony-firmware-20261024/stage256-root-service-flow-and-private-receipts/README.md)。'+text[end:]
start=text.index('Mac接管归还子步骤已由251实测关闭',text.index('## 下一批工作的交付边界'));end=text.index('\n\n这一批应交付',start)
text=text[:start]+'Mac接管归还子步骤已由251实测关闭，不重复。256已完成主机候选的原生组件/对象转交/独立scope与逐调用IPC回执整合及限定离线验证。下一批补真实SERVICE节点的描述符发现、固定配置核对和不匹配时的控制退出，然后绑定新鲜目标/nonce/单次许可，形成新的完整诊断包。READY目前为0、native渲染关闭；不能把测试端点直接放进生产配置，不复用旧授权。正常主机返回与机内线程完成仍分开，认证/历史/模式影响和可选88B机身文件读取需在新范围明示。'+text[end:];ma=text.encode()
for name,raw in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,raw)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,status='ROOT_FLOW_AND_PRIVATE_RECEIPTS_INTEGRATED_OWN_CHILD_PASS_LIVE_CLOSED',previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=72,
    native_sha256=build['builds']['native']['sha256'],root_flow_source_and_IPC_integrated=True,native_helper_executed=False,real_camera_or_USB_cache_or_root_operations=0,normal_fixture_raw_frames=80,
    checks_by_revision=dict(initial_integration=5,per_call_stop_regression=2,final_scope_receipts=2),artificial_pipes_not_camera_emulation=True,final_analyzer_units=5,final_analyzer_diagnostics=0,
    same16_and_authorizations_unchanged=True,old12_pass_and_11_UNKNOWN_preserved=True,SERVICE_profile_ready=False,native_launch_closed=True,new_approval_bundle_created=False,live_trial_ready=False,milestone2_complete=False,goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for path in sorted(H.rglob('*')):
    if path.is_file():
        raw=path.read_bytes();members.append(dict(path=str(path.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage256-root-service-flow-private-receipts-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(members),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),native_executed=False)))
