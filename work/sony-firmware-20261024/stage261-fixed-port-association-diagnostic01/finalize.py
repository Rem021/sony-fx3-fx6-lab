"""Freeze exact reviewed package and bind the existing continuing consent."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import difflib,json,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage260-controlled-port-transition-association'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    with(H/name).open('xb')as f:f.write(x if isinstance(x,bytes)else enc(x))
previous=(P/'final-receipt.json').read_bytes();assert sha256(previous).hexdigest()=='d291ed0fe27be8761303bffe1011acba69fb781f6a21fb0750d121ad51f015ad'
for m in json.loads(previous)['files']:
    raw=(R/m['path']).read_bytes();assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256'],m['path']
bundle_raw=(H/'approval-bundle.json').read_bytes();bundle=json.loads(bundle_raw);digest=sha256(bundle_raw).hexdigest()
assert digest=='8a4cde7317b8cd747113f366bcedbc236a56ae5a3a6e890e7e4ccacb5522de69'
for m in bundle['files']:
    raw=(H/m['path']).read_bytes();assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256'],m['path']
build=json.loads((H/'build-receipt.json').read_text());tests=json.loads((H/'package-test-receipt.json').read_text());material=json.loads((H/'fixed-material.json').read_text())
assert tests['checks']==5 and all(x['status']=='PASS'for x in tests['rows'])
assert not Path('/private/tmp'/Path(bundle['grant_id'])).exists()
diff=[]
for m in json.loads((H/'source-copy-receipt.json').read_text())['files']:
    old=(R/m['source']).read_bytes();assert sha256(old).hexdigest()==m['sha256'];new=(H/m['destination']).read_bytes()
    if old!=new:diff.extend(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),m['source'],H.name+'/'+m['destination']))
put('source-changes.diff',''.join(diff).encode())
grant=dict(authorized=True,grant_id=bundle['grant_id'],bundle_sha256=digest,scope=bundle['scope'],maximum_helper_invocations=1,
    usb_capture_and_return=True,Sony_authentication_and_mode_transition=True,camera_fixed_read0_maximum_bytes=88,firmware_write=False,
    physical_port_registryID=material['physical_port_registryID'],physical_custody_no_substitution_assumption=True)
decision=dict(status='FIXED_ONE_SHOT_PORT_ASSOCIATION_PACKAGE_READY_FOR_FRESH_PREFLIGHT',
    grant_id=bundle['grant_id'],bundle_sha256=digest,helper_sha256=build['builds']['native']['sha256'],
    scope=bundle['scope'],target=material['target'],physical_port_registryID=material['physical_port_registryID'],
    fixed_code_and_reviewable_plan_ready=True,authorization_origin='existing explicit user continuing research/all-agree consent',
    old_grants_reactivated=False,maximum_root_helpers=1,
    fresh_preflight_required=True,physical_custody_required=True,
    scope_is_experimental_communication_not_safe_firmware_flash=True,
    Sony_authentication_may_change_history_or_mode=True,
    actual_root_or_USB_commands=0,native_job_staged=False,Terminal_started=False,
    milestone2_complete=False,goal_complete=False,persistent_write_release=False)
put('admission-decision.json',decision)
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();assert gb==(P/'goal-status-after.json').read_bytes();g=json.loads(gb);req=g['requirements'];assert len(req)==16
now=datetime.now(timezone.utc).isoformat();g.update(updated_utc=now,latest_stage=H.name,
    research_activity='Fixed one-shot SVC4 port-association diagnostic package with fresh source registry/physical anchor, nonce/key and96B permit; root checks physical anchor in immutable target binding. New typed authority, source cache probe, zero-media gate, native frame/permit and one newly bound own-child namespace regression all pass(5 checks). Exact bundle bound under explicit continuing user consent, not old grants. No staging/root/USB commands yet. Next fresh preflight and single Terminal/native-system authentication launch; all16 and persistent-write gates remain.')
g['authorization']['Mac_port_association_diagnostic01']=grant
g.setdefault('authorization_sources',{})['Mac_port_association_diagnostic01']=dict(user_quote='持续研究，不要停止，我全部同意',
    supplementary_user_state='已连接MSC，全部卷已推出',concrete_scope=str((H/'README.md').relative_to(R)),
    bundle_sha256=digest,scope_explained_before_launch=True,new_general_permission_not_requested=True,
    native_authentication_by_user_only=True,existing_single_use_grants_not_reused=True)
g['current_effective_authorization_scope']=dict(key='Mac_port_association_diagnostic01',scope=bundle['scope'],
    old_flat_authorization_fields_are_historical=True,firmware_write_released=False)
g['prepared_port_association_diagnostic01']=dict(readme=str((H/'README.md').relative_to(R)),
    plan=str((H/'fixed-plan.json').relative_to(R)),build=str((H/'build-receipt.json').relative_to(R)),
    tests=str((H/'package-test-receipt.json').relative_to(R)),**decision)
g['current_continuation_context'].update(previous_goal_turn_classification='progress',current_goal_turn_classification='progress',same_blocker_no_progress_count=0)
g['next_safe_offline_actions']=[
    '261新固定单次诊断包已完成5项针对性验证，按已有整体继续授权绑定确切包摘要；尚未启动。只使用Mac_port_association_diagnostic01，不复用258或12号。',
    '下一步核对当前缓存节点/物理锚点及全部卷已推出，均满足才暂存一次并打开Terminal。最多一个root helper，系统验证由用户完成；固定范围包括MSC/SERVICE认证、条件性88B读取和退出，不上传或刷固件。',
    '关联依赖物理保管，非密码学身份；认证可改历史/模式。未返回/归还不明保留UNKNOWN和原实例，不强杀/reset/重试。记录活观察器/内核helper身份，重启或观察超时不重建同次试验。',
    '实际同机认证/退出与G01/G05仍需实机证据，原16项不变。完整备份、独立恢复及MAIN H.265等未完成，不放行持久刷写。']
assert g['requirements']==req and not g['goal_complete']and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();rt=rb.decode();anchor=next(x for x in rt.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-11-01 FX3物理端口关联诊断01固定包](<work/sony-firmware-20261024/stage261-fixed-port-association-diagnostic01/README.md>)：新节点/物理锚点/单次许可与构建已固定，5项新绑定检查通过；按用户整体继续授权准备一次Sony通信诊断。启动前仍核对缓存和卷状态；尚未暂存、运行root或发送Sony命令，未放行固件写入。'
assert H.name not in rt;ra=rt.replace(anchor,anchor+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();mt=mb.decode();assert '最新研究证据为第260阶段。'in mt
mt=mt.replace('最新研究证据为第260阶段。','最新研究证据为第261阶段。',1)
a=mt.index('最新进展：');z=mt.index('\n\n下面8项',a)
mt=mt[:a]+'最新进展：261已固定新的单次物理端口关联诊断包，绑定当前源节点/USB-C锚点/nonce/许可及确切构建；5项新绑定检查通过，并按用户既有整体继续授权登记。下一步须先核对新鲜缓存和全部卷已推出，然后最多启动一个root helper，原生系统验证由用户完成。当前尚未暂存、认证或切模式；旧258保持不可执行。此次只是限定Sony通信，不是H.265包或安全刷机。[操作、影响与固定包](../../work/sony-firmware-20261024/stage261-fixed-port-association-diagnostic01/README.md)。'+mt[z:]
a=mt.index('Mac接管归还子步骤已由251实测关闭',mt.index('## 下一批工作的交付边界'));z=mt.index('\n\n这一批应交付',a)
mt=mt[:a]+'Mac接管归还子步骤已由251实测关闭，不重复。260实现的有界物理端口关联已在261形成新固定单次包；新绑定/许可/工厂检查通过，按已有用户整体授权登记，未执行。接下来只做新鲜缓存预检；通过后一次暂存和Terminal启动，由用户完成必要系统验证。范围包括MSC/SERVICE认证、条件88B读取及退出，依赖物理保管且有历史/模式副作用，不上传或写固件。未知结果保留原实例，不重置/强杀/自动重试；helper退出、缓存/驱动、屏幕及机内线程继续分别核对。'+mt[z:];ma=mt.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=479,
    bundle_sha256=digest,native_sha256=decision['helper_sha256'],offline_binding_checks=5,
    authority_bound_from_existing_user_consent=True,new_root_or_USB_commands=0,
    native_job_staged=False,actual_camera_trial=False,requirements_preserved=16,
    goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for p in sorted(H.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();members.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage261-fixed-port-diagnostic-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status=decision['status'],members=len(members),bundle_sha256=digest,manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest())))
