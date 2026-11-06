"""Source recheck and state registration for the bounded MCU read contract."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from elftools.elf.elffile import ELFFile
import json, os, plistlib, re, stat, subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage205-FX3-hardware-profile-differences';REL=str(H.relative_to(R))
PREV='0e78ad2026f887c118f1784a2a9a35566728495217e33a5facf4152f25cdee72'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,value):
    with (H/n).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==100
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
proof=json.loads((H/'MCU-read-contract-proof.json').read_text());assert len(proof['selected_original_ranges'])==18
for row in proof['selected_original_ranges']:
    p=R/row['source'];d=p.read_bytes();assert sha256(d).hexdigest()==row['source_sha256']
    a,z=int(row['start'],16),int(row['end_exclusive'],16)
    if row['layout']=='ELF_VA':
        e=ELFFile(BytesIO(d));s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']);off=s['p_offset']+a-s['p_vaddr'];part=d[off:off+z-a]
    else:part=d[a-0x4200:z-0x4200]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
assert proof['handler']['maximum_read_bytes']==120 and proof['handler']['response_preserves_request_header6']
assert not proof['pre_dispatch_effect']['whole_protocol_is_side_effect_free']
assert not proof['reply_freshness']['strict_same_request_freshness_proven']
ids=proof['AP_configuration']['Backup_inputs'];assert [r['id'] for r in ids]==['0xf900d4','0xf900b1','0xf9006d']
models=json.loads((H/'CRC-semantic-model-results.json').read_text())
assert models['byte_state_cases']==4608 and len(models['full126B_vectors'])==5 and not models['proves_MCU_hardware_CRC_or_transport']
refcap=json.loads((P/'payload-source-capture.json').read_text());ref=next(r for r in refcap['files'] if r['path']=='payloads/fastboot/src/darwin.c')
assert digest(R/ref['output'])==ref['sha256']
catalog=json.loads((H/'Backup-template-candidates.json').read_text())
assert digest(R/catalog['source'])==catalog['source_sha256']
old_inventory=json.loads((R/catalog['source']).read_text())
assert len(catalog['members'])==22 and all(r in old_inventory['tar']['members'] for r in catalog['members'])
assert not catalog['template_format_or_requested_ID_values_decoded'] and not catalog['current_body_template_selected']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link:assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert native['goal']['status']=='active' and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='BUNDLED_INITCOM_READ_SEMANTICS_AND_CONFIG_SOURCES_BOUND',
    previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Read frame grammar and echo path now source-bound; CRC-valid requests have common MMIO side effects, repeated identical headers lack strict freshness. SIO/GPIO inputs come from3Backup IDs. Public template candidates exist for further offline decoding; no need to guess fixed A7IV pins.',
    limits=proof['limits']+['MCU hardware CRC equivalence and target execution state not measured','Backup default template format/values and GPIO provider semantics not decoded'],
    root01='195 specific approval pending; no job, admin launch or repeated question',
    original_or_guest_executions=0,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_SOURCE_BOUND_READ_CONTRACT',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=100,selected_original_ranges=18,
    CRC_semantic_model_byte_cases=4608,CRC_semantic_model_full_vectors=5,
    Backup_configuration_input_IDs=3,public_template_candidates=22,
    hardware_CRC_or_reply_freshness_or_actual_entry_proven=False,
    host01_bundle_sha256_unchanged=HOST,release0_4_zip_unchanged=True,new_approval_granted=False,
    original_or_guest_executions=0,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Bound bundled7.02 MCU InitCom0x16 read branch/LE32/header6/payload120/echo128/CRC-tail and common pre-dispatch MMIO. Official AP3Backup IDs drive SIO/GPIO inputs. Software CRC semantic models4608+5 passed, not MCU hardware. Repeated identical header freshness unproven.18ranges; no original/guest/root/device actions.195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('206绑定包内MCU InitCom0x16读分支/6头/120数据/后续回复CRC；CRC通过公共路径写MMIO，重复同头不证新鲜。AP三Backup来源已绑；4608+5仅软件语义，18原范围。下一项默认模板/GPIO提供库，不猜固定引脚，无设备/root/guest；16要求/授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',contract=REL+'/MCU-read-contract-proof.json',
    CRC_models=REL+'/CRC-semantic-model-results.json',templates=REL+'/Backup-template-candidates.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',original_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage206_MCU_read_contract_and_configuration_sources']=ev
new['recovery_MCU_read_contract_and_configuration_sources']={**ev,'bundled_InitCom_read_grammar_bound':True,
    'SIO_GPIO_input_Backup_IDs_bound':True,'whole_protocol_side_effect_free':False,'strict_same_request_reply_freshness_proven':False,
    'actual_current_body_MCU_entry_hardware_CRC_or_SIO_pins_proven':False,'same_body_backup_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准、不启动、不重问；主机试验不自动放行相机。',
    '核对官方包经典ALCIN默认Backup模板格式，寻找F900D4/B1/6D的静态候选值，并查libul_GpioCtrl实际提供方/参数语义；默认模板不能当实机Backup，也不混用HIBIKI2。',
    '读取候选只可称内存读分支，必须保留公共MMIO副作用、InitCom状态、CRC外设和重复回复时效缺项。保留ROM/启动桥、同机boot0/p1、逆写/冷恢复及16要求/真实MAIN1080p29.97 HEVC长录验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3 MCU读取分支与SIO配置来源](<'+REL+'/README.md>)：包内InitCom0x16/6字节头/120数据/回复已绑，公共MMIO与重复回复边界已查；3Backup来源、18原范围，CRC4608+5仅语义模型。195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name in [(canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')]:
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage206-MCU-read-contract-v1',created_utc=now,previous_manifest_sha256=PREV,
    previous_members_reverified=100,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,
    new_approval_granted=False,original_or_guest_execution=False,root_or_device_operations=0,native_goal_observed='active',
    native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),source_ranges=18,
    configuration_IDs=3,requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
