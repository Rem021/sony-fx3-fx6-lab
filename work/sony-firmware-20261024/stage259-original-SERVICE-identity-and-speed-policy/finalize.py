"""Seal actual original-source finding and bounded code repair; no live trial."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import difflib,json,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
P=B/'stage258-fixed-Sony-communication-diagnostic01'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    with(H/name).open('xb')as f:f.write(x if isinstance(x,bytes)else enc(x))
previous=(P/'final-receipt.json').read_bytes();assert sha256(previous).hexdigest()=='770628ab5ab433dfedf89bdccbec18322d3854916365f118590369ec468629af'
for m in json.loads(previous)['files']:
    raw=(R/m['path']).read_bytes();assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256'],m['path']
build=json.loads((H/'build-receipt.json').read_text())
for m in build['sources']:assert sha256((H/m['path']).read_bytes()).hexdigest()==m['sha256']
for m in build['builds'].values():assert sha256(Path(m['path']).read_bytes()).hexdigest()==m['sha256']
audit=json.loads((H/'original-service-descriptors-and-identity.json').read_text())
tests=json.loads((H/'speed-policy-test-receipt.json').read_text());assert tests['checks']==3 and all(x['status']=='PASS'for x in tests['rows'])
assert audit['SERVICE_serial_enabled_byte']==0 and not audit['original_Sony_instructions_executed']
assert '#define FX3_NATIVE_SERVICE_RELEASED 0'in(H/'service_profile.h').read_text()
assert not Path('/private/tmp/fx3-702-service-diagnostic-20261031-01').exists()
diff=[];changed=[]
for m in json.loads((H/'source-copy-receipt.json').read_text())['files']:
    raw=(R/m['source']).read_bytes();assert sha256(raw).hexdigest()==m['sha256'];new=(H/m['destination']).read_bytes()
    if raw!=new:
        changed.append(m['destination']);diff.extend(difflib.unified_diff(raw.decode().splitlines(True),new.decode().splitlines(True),m['source'],H.name+'/'+m['destination']))
put('source-changes.diff',''.join(diff).encode())
decision=dict(status='PREVIOUS_TRIAL_INCOMPATIBILITY_FOUND_SPEED_POLICY_FIXED_IDENTITY_UNRESOLVED',
    original_SERVICE_serial_suppression=True,SERVICE_DID=13,
    exact_candidate258_affected_bundle_sha256='20cc367690c74306ce07ec3c6c721b7e2830f3efc39931d21a53f41c8f3e090e',
    candidate258_not_to_launch_on_reconnection=True,
    reason='Reviewed default SERVICE route suppresses serial;258 requires nonempty same serial onSERVICE. A successful MSC switch could leave host flow retained before SERVICE STOP.',
    original_runtime_unchanged_default_not_observed=True,
    speed_policy_fixed_for_packets=[64,512,1024],raw_SS_companion_validation_implemented=True,
    SERVICE_identity_issue_fixed=False,port_only_automatic_fallback_added=False,
    next_action='Implement a separately labelled bounded continuous physical-port transition witness or a reviewed independent identity read; preserve original MSC tag separately and verify returned MSC.',
    native_sha256=build['builds']['native']['sha256'],native_release=False,
    new_live_package_ready=False,new_root_or_USB_or_original_Sony_code_execution=0,
    no_new_cache_query_or_Terminal=True,old_single_use_grants_reused=False,
    pending_connection_not_sufficient_for_trial=True,milestone2_complete=False,
    goal_complete=False,persistent_write_release=False)
put('admission-decision.json',decision)
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();assert gb==(P/'goal-status-after.json').read_bytes()
g=json.loads(gb);req=g['requirements'];assert len(req)==16
now=datetime.now(timezone.utc).isoformat()
g.update(updated_utc=now,latest_stage=H.name,
    research_activity='Original7.02 libInfraUsbCmn descriptor builder/GOT/ptbl_did/createGadget prove default SERVICE DID13 suppresses serial;258 nonempty cross-mode serial guard is incompatible and can retain after MSC switch before STOP. Do not launch258 upon reconnect. Original FS64/HS512/SS1024 four-endpoint tables recovered; bounded parser/native validation/parent raw-profile checks repaired and3 targeted own-code checks pass. No real root,USB/cache or Sony instructions this turn. Next implement explicitly labelled controlled physical-port transition witness or independent identity read; all16 and persistent-write gates intact.')
g['current_continuation_context'].update(previous_goal_turn_classification='progress',current_goal_turn_classification='progress',same_blocker_no_progress_count=0)
g['recovery_original_SERVICE_identity']=dict(readme=str((H/'README.md').relative_to(R)),
    original_audit=str((H/'original-service-descriptors-and-identity.json').relative_to(R)),
    original_functions=str((H/'original-functions.json').relative_to(R)),
    tests=str((H/'speed-policy-test-receipt.json').relative_to(R)),decision=str((H/'admission-decision.json').relative_to(R)),**decision)
g['prepared_Sony_communication_diagnostic'].update(code_and_reviewable_steps_ready=False,
    candidate258_withdrawn_for_known_static_route_incompatibility=True,
    withdrawal_evidence=str((H/'original-service-descriptors-and-identity.json').relative_to(R)),
    physical_connection_and_fresh_binding_alone_are_not_sufficient=True,
    first_Sony_trial_released=False,identity_association_implementation_required=True)
g['current_physical_dependency'].update(required_for_immediate_research=False,
    deferred_until='SERVICE association issue fixed and a new specific trial package is ready',
    connection_does_not_authorize_launch_of_known_incompatible_candidate258=True)
g['next_safe_offline_actions']=[
    '259发现原厂SERVICE DID13关闭USB串号；258跨模式非空串号条件与该原路径不兼容。258保持历史封存，不能接机后直接运行，也不能通过填入MSC标签伪造SERVICE身份。',
    '先实现独立标注的、限定时间和唯一节点的连续物理USB端口切换见证，保留初始MSC标签并核对退出后的MSC；或定位可独立读取机身身份的已审查接口。拓扑关联不是串号或密码学认证，假设与限制必须写入范围。',
    '三速配置识别/SS companion/父端原始profile核对的针对性修复和验证已经完成，不重放同一模型或反复查未连接设备。新候选release0/factory关闭，尚无新上机包。',
    '用户整体继续授权与16项目标、12号实机子步骤/11号UNKNOWN保持。真实SERVICE退出、同机完整备份、独立恢复和MAIN主录仍未通过，首刷不放行。']
assert g['requirements']==req and not g['goal_complete']and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();rt=rb.decode();anchor=next(x for x in rt.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-11-01 FX3原厂SERVICE串号与三速配置](<work/sony-firmware-20261024/stage259-original-SERVICE-identity-and-speed-policy/README.md>)：确认原厂SERVICE关闭USB串号，与258候选的跨模式身份条件不兼容，旧包不能接机后直接运行。三速配置识别已补齐并验证；接下来修复受控切换关联，无相机命令或管理员操作。'
assert H.name not in rt;ra=rt.replace(anchor,anchor+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();mt=mb.decode();assert '最新研究证据为第258阶段。'in mt
mt=mt.replace('最新研究证据为第258阶段。','最新研究证据为第259阶段。',1)
a=mt.index('最新进展：');z=mt.index('\n\n下面8项',a)
mt=mt[:a]+'最新进展：259在7.02原厂库中确认SERVICE默认关闭USB串号，导致258候选的跨模式串号条件不兼容；不能仅接机并换节点就运行258。已恢复FS64/HS512/SS1024三套原端点表，并修复有界配置识别和父端布局核对，三个针对性检查通过。当前真正需要补的是串号以外、明确标注证据强度的受控切换关联。没有执行Sony通信或管理员操作。12号实机Mac接管归还子步骤及11号UNKNOWN保持。[原厂证据与影响](../../work/sony-firmware-20261024/stage259-original-SERVICE-identity-and-speed-policy/README.md)。'+mt[z:]
a=mt.index('Mac接管归还子步骤已由251实测关闭',mt.index('## 下一批工作的交付边界'));z=mt.index('\n\n这一批应交付',a)
mt=mt[:a]+'Mac接管归还子步骤已由251实测关闭，不重复。258的上机候选在259被查出具体串号不兼容，不再仅等待接机：原厂SERVICE关闭串号，不能把MSC标签复制过去冒充验证。下一批先实现受控、连续的物理端口切换关联，或定位独立身份读取接口；区分拓扑关联、串号和密码学身份，并核对退出后的原MSC标签。三速识别已修复，不重复无针对性模型。关联与异常退出路径可复核后，再固定新目标、许可和包。用户整体研究授权保留，系统管理员验证仍由用户本人完成；不启动旧258，不自动重置/强杀/重试。'+mt[z:]
ma=mt.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=257,
    original_instructions_checked=27,original_Sony_code_executed=False,actual_root_or_USB_or_cache_queries=0,
    native_sha256=build['builds']['native']['sha256'],new_speed_checks=3,
    saved_decoder_bytes_regression_only=True,SERVICE_identity_fixed=False,
    candidate258_not_released=True,native_release=False,requirements_preserved=16,
    goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for p in sorted(H.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();members.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage259-original-identity-and-speed-policy-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status=decision['status'],members=len(members),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),native_released=False)))
