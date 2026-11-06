"""Seal corrected status12 package; never stage or launch a native job."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess

H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage249-authorized-owner-status11'
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/'final-receipt.json').exists() and not Path('/private/tmp/fx3-702-owner-status-20261030-12').exists()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    raw=x if isinstance(x,bytes) else enc(x)
    fd=os.open(H/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw)
previous=json.loads((P/'final-receipt.json').read_text())
for x in previous['files']:
    raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256'],x['path']
bundle_raw=(H/'approval-bundle.json').read_bytes();digest=sha256(bundle_raw).hexdigest();bundle=json.loads(bundle_raw)
assert digest=='57dc8a85d05360e5df098a75ace9fa422dd31293396c65bb238d2eec5a6a5910' and len(bundle['files'])==50
for x in bundle['files']:
    raw=(H/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256'],x['path']
tests=json.loads((H/'package-test-receipt.json').read_text());assert tests['checks']==8 and all(x['status']=='PASS' for x in tests['rows'])
pipeline=next(x for x in tests['rows'] if x['case']=='new_supervisor_fixture_pipeline');fixture=H/pipeline['directory']
raw=(fixture/'received-final-record.bin').read_bytes();assert len(raw)==1024 and raw==(fixture/'private-record.bin').read_bytes()
plan=json.loads((H/'fixed-plan.json').read_text());material=json.loads((H/'fixed-material.json').read_text())
now=datetime.now(timezone.utc).isoformat();gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();g=json.loads(gb)
assert gb==(P/'goal-status-after-final.json').read_bytes() and g['authorization_consumption']['Mac_owner_status11']['consumed']
assert 'Mac_owner_status12' not in g['authorization']
requirements=g['requirements'];authorization=g['authorization'].copy()
g['updated_utc']=now;g['latest_stage']=H.name
g['research_activity']='249 executed one approved status11 diagnostic: kernel identity/live HELLO verified, helper absent, cached same-body MSC/drivers and user normal screen observed; private completion rejected because host parser omitted native trace101..109 and original frame was not archived. Formal UNKNOWN unchanged.250 integrates parser, raw-frame preservation and error-observer-exit repair into a complete fixed status12 package with new nonce/key/permit and cached post-reenumeration node.8 package checks pass, including actual unprivileged Unix fixture with synthetic102..109 trace and identical raw/accepted records.Production owner_iokit.c byte-identical to11.50file bundle frozen; no new root helper/USB operations, no job staged, no new permission recorded. Ready to request exactly one new status-only diagnostic; no Sony auth/file/module/firmware scope.'
g['prepared_owner_status12_trial']=dict(readme=str((H/'README.md').relative_to(R)),fixed_plan=str((H/'fixed-plan.json').relative_to(R)),bundle=str((H/'approval-bundle.json').relative_to(R)),bundle_sha256=digest,grant_id=plan['grant_id'],scope='MSC_OWNER_STATUS_ONLY',maximum_helper_invocations=1,ready_for_new_specific_approval=True,explicitly_authorized=False,staged=False,executed=False,target=material['target'],helper_sha256=plan['helper_sha256'],host_control_ops=['OBSERVE','STATUS','END'],production_USB_scope_unchanged=True,previous11_unknown_preserved=True,requires_manual_all_camera_volumes_ejected=True,old_grants_not_accepted=True)
g['current_native_owner_channel_candidate'].update(readme=str((H/'README.md').relative_to(R)),build=str((H/'build-receipt.json').relative_to(R)),verification=str((H/'package-test-receipt.json').relative_to(R)),identifier=plan['grant_id'],explicitly_approved=False,new_integrated_native_executed=False,new_root_or_camera_operations=0,ready_for_specific_status_diagnostic_approval=True,grant_consumed=False,diagnostic_outcome='PREPARED_NOT_APPROVED_OR_EXECUTED',candidate_execution_scope='status12 only',previous11_execution_record=str((P/'README.md').relative_to(R)),host_receipt_substep_fix_integrated=True,raw_final_frame_saved_before_decode=True,fixture_pipeline_covers_synthetic_native_substeps=True)
g['recovery_corrected_owner_status12_package']=dict(readme=str((H/'README.md').relative_to(R)),approval_bundle_sha256=digest,package_checks=8,production_owner_iokit_source_unchanged=True,root_or_USB_operations=0,live_cache_queries=1,root_helper_executed=False,new_diagnostic_approved=False,milestone2_complete=False)
g['next_safe_offline_actions']=[
 '250完整12号修复包已固定50文件，8项包检查通过；夹具包含101..109子步骤并经真实本机Unix连接保存原始回执。11号UNKNOWN和原始包保留，不为此继续追加同类模型。',
 '下一步提交250具体单次MSC_OWNER_STATUS_ONLY管理员/USB诊断供批准，并确认相机全部卷已推出、保持当前端口/MSC。批准前不启动。旧11号、195和05授权不可复用；12号当前未授权。',
 '获准后只执行一次，缓存节点或构建变化即拒绝不改目标；不发送Sony认证/模式/文件或固件命令。阻塞/结果不明保留UNKNOWN，不强杀/重置/自动重试；helper确认退出后只关闭观察器不改变UNKNOWN。完整备份、独立救砖和MAIN HEVC另待验证。'
]
assert g['requirements']==requirements and g['authorization']==authorization and not g['goal_complete'] and not g['persistent_write_release']
ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();text=rb.decode();overview=next(x for x in text.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3第12号修复诊断固定方案](<work/sony-firmware-20261024/stage250-corrected-owner-status12-package/README.md>)：修复101–109事件解析、先存原始回执及错误后观察器退出；新节点/单次材料和50文件包已固定，8项检查含原生编号夹具通过。生产USB范围不变；未授权/暂存/执行，11号UNKNOWN保留。'
assert H.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();assert '最新研究证据为第249阶段。' in text;text=text.replace('最新研究证据为第249阶段。','最新研究证据为第250阶段。',1)
needle='[实际记录与修复](../../work/sony-firmware-20261024/stage249-authorized-owner-status11/README.md)。'
assert needle in text;text=text.replace(needle,needle+' 第250阶段已将修复接入完整12号固定包，8项包检查通过（夹具已覆盖原生子步骤和原始帧留存），未授权或启动。[新诊断固定方案](../../work/sony-firmware-20261024/stage250-corrected-owner-status12-package/README.md)。',1)
text=text.replace('私有完成回执解析失败，修复候选待接入新固定包','私有完成回执解析失败；12号修复固定包已准备，待新单次批准',1)
old='第2项下一步将249的解析器/原始回执留存修复接入完整固定包，并重新固定重枚举后的缓存节点。新包准备好后再提交具体单次批准；不复用已消耗的11号、195或旧05授权，不自动重试/强杀/重置。本次UNKNOWN保留，不以共享页或合成测试倒填通过。'
new='第2项下一步提交250的完整12号修复包供具体单次批准。包和重枚举后的缓存节点已固定，不再追加相同模型；批准并确认相机卷全部推出后才执行。不能复用已消耗的11号、195或旧05授权，不自动重试/强杀/重置。11号UNKNOWN保留，不以共享页或合成测试倒填通过。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,status='CORRECTED_STATUS12_FIXED_PACKAGE_PREPARED_NOT_APPROVED_OR_EXECUTED',previous_manifest_sha256=sha256((P/'final-receipt.json').read_bytes()).hexdigest(),previous_members_reverified=len(previous['files']),approval_bundle_sha256=digest,approval_members=50,package_checks=8,fixture_pipeline_synthetic_native_substeps_verified=True,fixture_original_raw_record_preserved=True,production_USB_source_byte_identical_to11=True,live_cache_queries=1,new_root_helper_or_USB_operations=0,native_job_staged=False,native_helper_executed=False,explicit_new_authorization=False,old11_unknown_preserved=True,all16_and_existing_authorizations_unchanged=True,goal_complete=False,persistent_write_release=False,heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
files=[]
for p in sorted(H.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage250-corrected-status12-package-v1',member_count=len(files),files=files,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(files),approval_bundle_sha256=digest,manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest())))
