"""Persist concrete package and current absence evidence; do not launch it."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import difflib,json,os,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
P=B/'stage257-service-descriptor-discovery-and-control-exit'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,value):
    with(H/name).open('xb')as f:f.write(value if isinstance(value,bytes)else enc(value))
previous=(P/'final-receipt.json').read_bytes()
assert sha256(previous).hexdigest()=='1bbe59cdc806d464c3b35f67b73048960a7c44b3d456be9fff4d9d4ff61dd236'
for m in json.loads(previous)['files']:
    raw=(R/m['path']).read_bytes();assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256']
bundle_raw=(H/'approval-bundle.json').read_bytes();bundle=json.loads(bundle_raw)
for m in bundle['files']:
    raw=(H/m['path']).read_bytes();assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256'],m['path']
build=json.loads((H/'build-receipt.json').read_text())
for m in build['sources']:assert sha256((H/m['path']).read_bytes()).hexdigest()==m['sha256']
checks=json.loads((H/'package-test-receipt.json').read_text())
assert checks['checks']==5 and all(m['status']=='PASS'for m in checks['rows'])
assert not Path('/private/tmp/fx3-702-service-diagnostic-20261031-01').exists()
cache=json.loads((H/'current-preparation-cache.json').read_text());assert not cache['unique_fixed_camera_node_present']
diff=[];changed=[]
for m in json.loads((H/'source-copy-receipt.json').read_text())['files']:
    old=(R/m['source']).read_bytes();assert sha256(old).hexdigest()==m['sha256'];new=(H/m['destination']).read_bytes()
    if old!=new:
        changed.append(m['destination']);diff.extend(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),m['source'],H.name+'/'+m['destination']))
put('source-changes.diff',''.join(diff).encode())
put('source-delta-review.json',dict(changed_copied_files=changed,
    native_changes='new independent job/grant/nonce/permit and frozen cached target; live code release flags enabled in this build, factory still requires exact canonical authority and fresh target',
    factory_changes='typed new scope authority; cached storage topology and mounted-volume gate before job creation; one-shot Terminal renderer and observer lifecycle',
    USB_flow_changes='none from257; bounded descriptor discovery/control-only exit retained',
    binding_current=False,root_helper_executed=False))
decision=dict(status='FIXED_COMMUNICATION_PACKAGE_AND_GATES_COMPLETE_TARGET_ABSENT',
    bundle_sha256=sha256(bundle_raw).hexdigest(),helper_sha256=build['builds']['native']['sha256'],
    scope=bundle['scope'],maximum_helper_invocations=1,
    code_and_reviewable_steps_ready=True,native_target_snapshot_current=False,
    current_Sony_nodes_observed=0,fixed_camera_connected=False,
    must_rebind_new_node_and_freeze_new_material_before_actual_trial=True,
    native_authority_bound_to_canonical_goal=False,job_staged=False,Terminal_started=False,
    new_root_or_USB_interface_or_Sony_commands=0,zero_camera_writes_claimed=False,
    first_Sony_trial_released=False,first_persistent_flash_released=False,
    same16_preserved=True,milestone2_complete=False,
    user_general_continuation_consent_preserved=True,new_general_permission_request_needed=False,
    physical_connection_reply_pending=True,system_native_authentication_by_user_still_required=True)
put('admission-decision.json',decision)
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();assert gb==(P/'goal-status-after.json').read_bytes()
g=json.loads(gb);req=g['requirements'];assert len(req)==16
now=datetime.now(timezone.utc).isoformat()
g.update(updated_utc=now,latest_stage=H.name,
    research_activity='Prepared concrete first Sony communication diagnostic: new bound source/build/96B permit, typed authority, fixed shell/Terminal rendering, mounted-volume gate, native frame and own-child tests. Five package checks pass. Preparation cache has no Sony node; no root/USB/Terminal operation, no staging. Fresh device connection/node binding and new frozen material required before trial. General continuing consent retained; original16 and flash gates unchanged.')
g['current_continuation_context'].update(previous_goal_turn_classification='progress',current_goal_turn_classification='progress',same_blocker_no_progress_count=0)
g['prepared_Sony_communication_diagnostic']=dict(readme=str((H/'README.md').relative_to(R)),
    plan=str((H/'fixed-plan.json').relative_to(R)),tests=str((H/'package-test-receipt.json').relative_to(R)),
    decision=str((H/'admission-decision.json').relative_to(R)),**decision)
g['current_physical_dependency']=dict(source=str((H/'current-preparation-cache.json').relative_to(R)),
    observed_utc=cache['observed_utc'],camera_present=False,
    asked_user='Connect FX3 to Mac in MSC and safely eject all camera volumes; report state',
    pending=True,Windows_access_not_attempted=True,authorization_is_not_the_missing_dependency=True)
g['next_safe_offline_actions']=[
    '258首次Sony通信诊断的具体步骤、工厂、固定许可/构建和主机检查已完成。不要重复同一正常链，不启动绑定旧节点的程序。',
    '当前Mac缓存未见Sony节点。待用户接机MSC并安全推出全部卷后，仅重新盘点缓存并将新节点/nonce/单次许可固定到新包；保持新旧构建分开，不覆盖258或复用旧状态许可。',
    '整体研究授权已保留；可复核新构建和前置满足后在该授权内继续限定诊断，原生管理员验证仍由用户完成。未知调用保留原实例，不强杀、重置、重发或自动清除全局UNKNOWN。',
    '真实SERVICE身份/配置、认证与退出不保证成功。未完成同机备份、独立恢复、MAIN目标及最小持久化准入，不放行首刷；G01至G16原要求不变。']
assert g['requirements']==req and not g['goal_complete']and not g['persistent_write_release']
ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();rt=rb.decode();anchor=next(x for x in rt.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-31 FX3首次Sony通信诊断固定包](<work/sony-firmware-20261024/stage258-fixed-Sony-communication-diagnostic01/README.md>)：具体认证、配置识别、固定88B读取和退出步骤及主机许可/启动器已写成；五组离线检查通过。当前缓存未见Sony相机，需要接机并固定新节点后才可启动；未暂存、未开Terminal、未运行root或Sony命令。'
assert H.name not in rt;ra=rt.replace(anchor,anchor+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();mt=mb.decode();assert '最新研究证据为第257阶段。'in mt
mt=mt.replace('最新研究证据为第257阶段。','最新研究证据为第258阶段。',1)
a=mt.index('最新进展：');z=mt.index('\n\n下面8项',a)
mt=mt[:a]+'最新进展：12号实机Mac接管归还子步骤通过，11号UNKNOWN保留。258已形成首次Sony通信诊断的具体操作、固定构建/许可、主机工厂和观察器；五组离线检查通过。下一次实际范围包含MSC/SERVICE认证、条件性的固定88B机内记录读取及退出，不上传模块或写固件，认证仍可能改变历史/工作模式。准备时Mac缓存未见Sony相机，需要接机并固定新节点才能启动；没有暂存或root/Sony操作。[诊断包及影响范围](../../work/sony-firmware-20261024/stage258-fixed-Sony-communication-diagnostic01/README.md)。'+mt[z:]
a=mt.index('Mac接管归还子步骤已由251实测关闭',mt.index('## 下一批工作的交付边界'));z=mt.index('\n\n这一批应交付',a)
mt=mt[:a]+'Mac接管归还子步骤已由251实测关闭，不重复。257的描述符/分支代码与258的完整通信诊断包及工厂检查已经完成。当前物理前置是相机未在线：接机MSC、安全推出全部相机卷后，先查缓存固定新节点，再生成新的固定材料和包摘要；不覆盖或直接启动绑定旧节点的258。用户整体研究授权保留，不再重复询问同一授权；管理员系统验证由用户本人完成。首次实际通信观察每一步及退出，异常保留UNKNOWN，不自动重置、强杀或重试。Sony认证可能更新机身历史/模式/文件，不充零写入；仍未验证机内程序或恢复。'+mt[z:]
ma=mt.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=333,
    bundle_sha256=decision['bundle_sha256'],helper_sha256=decision['helper_sha256'],offline_package_checks=5,
    root_or_actual_USB_or_Sony_commands=0,job_staged=False,current_camera_present=False,
    first_trial_waits_for_fresh_target_binding=True,goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for p in sorted(H.rglob('*')):
    if p.is_file():
        data=p.read_bytes();members.append(dict(path=str(p.relative_to(R)),bytes=len(data),sha256=sha256(data).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage258-fixed-Sony-communication-diagnostic-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status=decision['status'],members=len(members),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),trial_started=False)))
