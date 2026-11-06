"""Seal implementation, tests and actual cache-only port probe, no live USB trial."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import difflib,json,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage259-original-SERVICE-identity-and-speed-policy'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    with(H/name).open('xb')as f:f.write(x if isinstance(x,bytes)else enc(x))
previous=(P/'final-receipt.json').read_bytes();assert sha256(previous).hexdigest()=='bc47035a5cdc68b9aeb354afc5e5a8a19510af90d0049d2f5965b0cca260cd23'
for m in json.loads(previous)['files']:
    raw=(R/m['path']).read_bytes();assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256'],m['path']
build=json.loads((H/'build-receipt.json').read_text())
for m in build['sources']:assert sha256((H/m['path']).read_bytes()).hexdigest()==m['sha256'],m['path']
for m in build['builds'].values():assert sha256(Path(m['path']).read_bytes()).hexdigest()==m['sha256']
tests=json.loads((H/'transition-test-receipt.json').read_text());assert tests['checks']==8 and all(x['status']=='PASS'for x in tests['rows'])
analysis=json.loads((H/'analysis-receipt.json').read_text());assert analysis['total_diagnostics']==0
probe=json.loads((H/'cached-port-probe-receipt.json').read_text());observed=json.loads(probe['stdout'])
assert probe['returncode']==0 and observed['candidate_count']==1 and observed['uid']==501 and observed['anchor_available']
for name,digest in probe['source_hashes'].items():assert sha256((H/name).read_bytes()).hexdigest()==digest
assert sha256((H/'cached-port-probe').read_bytes()).hexdigest()==probe['binary_sha256']
cache=json.loads((H/'current-MSC-port-cache.json').read_text());assert observed['registryID']==cache['target']['registryID'] and observed['logical_port_registryID']==cache['parent']['registryID']
assert '#define FX3_NATIVE_SERVICE_RELEASED 0'in(H/'service_profile.h').read_text()and '#define FX3_CONTROLLED_PORT_ASSOCIATION_RELEASED 0'in(H/'service_profile.h').read_text()
assert not Path('/private/tmp/fx3-702-service-diagnostic-20261031-01').exists()
diff=[]
for m in json.loads((H/'source-copy-receipt.json').read_text())['files']:
    old=(R/m['source']).read_bytes();assert sha256(old).hexdigest()==m['sha256'];new=(H/m['destination']).read_bytes()
    if old!=new:diff.extend(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),m['source'],H.name+'/'+m['destination']))
put('source-changes.diff',''.join(diff).encode())
decision=dict(status='CONTROLLED_PHYSICAL_PORT_ASSOCIATION_IMPLEMENTED_OFFLINE_SOURCE_ANCHOR_OBSERVED',
    inherited_SERVICE_serial_incompatibility_addressed_in_code=True,
    SERVICE_without_serial_keeps_serial_tag_zero=True,source_serial_context_kept_separate=True,
    identity_basis='bounded sampled physical USB-C port association; assumes physical custody/no substitution; not cryptographic camera authentication',
    source_unique_port_checked_before_capture_and_transfer=True,
    actual_source_port_probe=True,source_cache_uid=501,current_cached_device_registryID=observed['registryID'],
    physical_port_registryID=observed['physical_port_registryID'],logical_port_registryID=observed['logical_port_registryID'],
    zero_media_after_eject_preflight_fixed=True,
    test_checks=8,analyzer_units=4,analyzer_diagnostics=0,
    actual_Sony_authentication_SERVICE_transition_read_or_exit=False,
    new_root_or_USB_device_interface_operations=0,native_helper_executed=False,
    new_scope='schema6/SVC4/FX3FLOW3-672B/FX3RCPT4',native_sha256=build['builds']['native']['sha256'],
    native_release=False,new_fixed_live_package_ready=False,
    candidate258_still_not_released=True,old_grants_reused=False,
    pending=['Fix a new reviewed one-shot package with fresh source/physical anchor/nonce/permit and explicit physical-custody assumption.','Actual constrained Sony communication and return, then independent cache and camera observation; no camera-thread or rescue inference.'],
    milestone2_complete=False,goal_complete=False,persistent_write_release=False)
put('admission-decision.json',decision)
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();assert gb==(P/'goal-status-after.json').read_bytes();g=json.loads(gb);req=g['requirements'];assert len(req)==16
now=datetime.now(timezone.utc).isoformat();g.update(updated_utc=now,latest_stage=H.name,
    research_activity='Implemented bounded physical USB-C transition association with separate original serial context and absent SERVICE serial fields; unique source port checked before capture/transfer,2s/20-sample windows, companion logical port allowed for SERVICE, original serial/location required on returned MSC, failures retained. New schema6/SVC4/672B per-call/RCPT4 and parent checks integrated. Eight own-code checks and4 analyses pass; actual ordinary-user C metadata probe confirmed source physical anchor4294968654. No root/USB interface/Sony commands. Ejected zero-media preflight fixed. Next fresh fixed live package; actual cross-mode identity/auth/read/exit and all16 remain unverified.')
g['current_continuation_context'].update(previous_goal_turn_classification='progress',current_goal_turn_classification='progress',same_blocker_no_progress_count=0)
g['recovery_controlled_physical_port_association']=dict(readme=str((H/'README.md').relative_to(R)),
    build=str((H/'build-receipt.json').relative_to(R)),tests=str((H/'transition-test-receipt.json').relative_to(R)),
    cache_probe=str((H/'cached-port-probe-receipt.json').relative_to(R)),decision=str((H/'admission-decision.json').relative_to(R)),**decision)
g['prepared_Sony_communication_diagnostic'].update(identity_association_implementation_required=False,
    identity_association_code=str((H/'README.md').relative_to(R)),
    new_fixed_scope_and_current_material_still_required=True,first_Sony_trial_released=False)
g['current_physical_dependency']=dict(source=str((H/'cached-port-probe-receipt.json').relative_to(R)),
    observed_utc=probe['recorded_utc'],camera_present=True,user_reports_MSC_and_all_volumes_ejected=True,
    pending=False,current_cached_registryID=observed['registryID'],physical_port_registryID=observed['physical_port_registryID'],
    cached_zero_media_does_not_prove_camera_health=True,fresh_recheck_required_before_trial=True,authorization_is_not_the_missing_dependency=True)
g['next_safe_offline_actions']=[
    '260已把独立标注的物理USB-C端口采样关联接到原生后端、C流程和新协议；没有复制MSC标签充SERVICE串号，原串号恢复另验。8组针对性检查/4静态分析完成，不重复同一测试。',
    '当前用户确认MSC/全部卷推出；实际普通用户C缓存探针读到源端口，未接管或认证。以新鲜节点/物理锚点/nonce/许可生成完整固定上机包；新candidate release0、factory关闭，258继续不可直接运行。',
    '新范围须明示采样关联依赖物理保管、不是密码学身份/完整事件捕获；Sony认证可能更新历史/模式。整体继续授权保留，不复用旧单次凭据。新构建固定后才进入原生系统验证，保持UNKNOWN不重置/强杀/自动重试。',
    '推出后媒体节点0为合法；只拒绝挂载/未知/无驱动，root独立核对仍保留。真实跨模式认证/读取/退出、同机备份/独立恢复/MAIN H.265及首刷门槛未完成，16项不变。']
assert g['requirements']==req and not g['goal_complete']and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();rt=rb.decode();anchor=next(x for x in rt.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-11-01 FX3受控物理端口切换关联](<work/sony-firmware-20261024/stage260-controlled-port-transition-association/README.md>)：已用实际Mac缓存确认FX3的物理USB-C锚点；新的无SERVICE串号关联、原串号恢复核对及协议已接通，8组自写检查/4静态分析通过。仍未认证或接管；下一步固定新的上机包，258保持不可直接执行。'
assert H.name not in rt;ra=rt.replace(anchor,anchor+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();mt=mb.decode();assert '最新研究证据为第259阶段。'in mt
mt=mt.replace('最新研究证据为第259阶段。','最新研究证据为第260阶段。',1)
a=mt.index('最新进展：');z=mt.index('\n\n下面8项',a)
mt=mt[:a]+'最新进展：260已把受控物理USB-C端口采样关联接到原生后端和完整主机流程，保留原MSC串号，SERVICE无串号时字段仍为零，退出后另验原串号。8组针对性自写检查和4单元静态检查通过；实际普通用户C缓存探针确认源端口，用户确认MSC和全部卷推出。尚无真实Sony认证或跨模式退出结果，新候选release0，下一步固定新上机包。关联依赖物理保管，不是密码学机身认证；258旧包仍不可直接执行。[实现和证据](../../work/sony-firmware-20261024/stage260-controlled-port-transition-association/README.md)。'+mt[z:]
a=mt.index('Mac接管归还子步骤已由251实测关闭',mt.index('## 下一批工作的交付边界'));z=mt.index('\n\n这一批应交付',a)
mt=mt[:a]+'Mac接管归还子步骤已由251实测关闭，不重复。260已实现新的无SERVICE串号关联及退出后原串号核对，区分端口关联/串号/密码学身份；真实源端口仅作缓存探针验证，跨模式仍未实测。下一批生成新固定范围、当前节点/物理锚点/nonce/单次许可和包；两项native release目前0，258不可直接运行。用户整体继续授权保留，系统验证由用户完成。上机前重新核对MSC和全部卷推出；媒体节点为0不再误拒，未知/挂载仍拒绝。认证/模式副作用、物理保管假设与UNKNOWN处置须写入新方案，不自动重置/强杀/重试。'+mt[z:]
ma=mt.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=289,
    native_sha256=decision['native_sha256'],own_code_checks=8,analyzer_diagnostics=0,actual_unprivileged_cache_port_probe=True,
    actual_root_USB_interface_or_Sony_commands=0,all_test_children_gone=True,requirements_preserved=16,
    new_live_package_ready=False,goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for p in sorted(H.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();members.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage260-controlled-port-association-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status=decision['status'],members=len(members),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),actual_camera_trial=False)))
