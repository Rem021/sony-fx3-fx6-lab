"""Seal completed offline evidence; preserve requirements and authorizations."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess

H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R))
P=B/'stage211-NOR-runtime-map-and-SIO-initialization'
PREV='62070d9c8d226a08bc467e463d4faefdcd1aa858f7f3b9867077342e20e6eac8'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def volume():
    d=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert d['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,value):
    (H/name).open('x').write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
oldseal=json.loads((P/'final-receipt.json').read_text());assert len(oldseal['files'])==51
for row in oldseal['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode)
    assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
ver=json.loads((H/'verification-receipt.json').read_text())
assert ver['status']=='PASS_STATIC_REBIND_AND_HOST_ONLY_PARSER_COMPARISONS'
assert [ver[k] for k in ['reextracted_files','original_ranges','script_line_pins','independent_raw_instruction_checks','default_records','independent_present_property_matches','independent_absent_property_rejections']]==[7,15,61,5,22,1386,44]
proof=json.loads((H/'official-boot-writer-proof.json').read_text())
for row in proof['ranges']:
    src=(R/row['source']).read_bytes();off=row['file_offset']
    assert sha256(src).hexdigest()==row['source_sha256']
    assert src[off:off+row['bytes']]==(R/row['raw']).read_bytes()
    assert digest(R/row['raw'])==row['sha256']
cap=json.loads((H/'source-capture.json').read_text())
assert digest(R/cap['source_image'])==cap['source_image_sha256']
for row in cap['files']:
    assert digest(R/row['output'])==row['sha256'] and (R/row['output']).stat().st_size==row['bytes']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for f in H.glob('*.py'):ast.parse(f.read_text(),filename=str(f))

canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert len(old['requirements'])==16 and native['goal']['status']=='active'
assert not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
new=deepcopy(old)
new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',
    goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Bound current bksb -m record0/-c record1, BKSB subset format and separate AP eMMC/CP NOR writer routes. Correct current NOR role used in196/197/198/210/211: CP package path, not independent AP proof. CP65 list complete in11 CP defaults,predicted1088B;AP defaults each lack4IDs.1386 independent present comparisons+44 independent absence rejections. Selected pformat main discards writer status.7reextracted sources,15raw ranges,61script lines,5raw-word checks. No Sony/guest/root/device action;16requirements and195 pending unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',
    observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification']
new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('212绑官方bksb的-m首AP/-c次CP记录与BKSB子集格式；AP脚本写eMMC B0，当前NOR脚本走CP路线，修正196/197/198/210/211的AP推断范围。11CP默认65项齐全预测1088B，AP均缺4项；1386独立数据比较+44缺失拒绝。选中pformat主路径丢弃writer返回码，不能以OK当恢复验收；7原件/15范围/61行/5原字检查。16要求与授权不变，无设备/root/guest。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',
    proof=REL+'/official-boot-writer-proof.json',defaults=REL+'/default-BKSB-layout-comparison.json',
    capture=REL+'/source-capture.json',correction=REL+'/analysis-refinements.json',
    components=REL+'/recovery-component-map.json',scope=REL+'/implementation-review.json',
    web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage212_official_boot_backup_generator']=ev
new['recovery_official_boot_backup_generator']={**ev,
    'm_AP_record_index':0,'c_CP_record_index':1,'BKSB_is_property_subset':True,
    'current_NOR_package_role':'CP update route; actual hardware branch not run',
    'AP_script_boot_device':'/dev/nflashaB0','AP_loader_emmc_archive_acquired':False,
    'CP_list_count':65,'CP_default_predicted_BKSB_bytes':1088,
    'AP_records_missing_CP_list_IDs':['0x5d000b','0x5d000c','0x5d0011','0x5d0012'],
    'independent_present_property_matches':1386,'independent_missing_property_rejections':44,
    'selected_pformat_main_discards_writer_result':True,
    'AP_NOR_image_interchangeability_proven':False,
    'actual_same_body_backup_or_independent_restore_proven':False}
new['corrections_to_prior_stage']['stage212_current_NOR_role_and_bksb_records']={
    'evidence':REL+'/official-boot-writer-proof.json',
    'affected_current_NOR_stages':[196,197,198,210,211],
    'correct_scope':'Current package NOR image is assigned by official script to CP-side update route; not independent AP boot/recovery proof.',
    'original_byte_results_and_seals_preserved':True,
    'public_AP_default_candidate_3_0_4_2_unchanged':True,
    'AP_and_CP_property_lists_or_images_not_substitutable':True,
    'actual_current_body_transport_or_restore_proven':False}
for key in ['recovery_NOR_route_refinement','recovery_SPI_mode_input_provenance',
            'recovery_AP_CP_boot_component_boundary','recovery_early_SIO_clock_and_counter_contract',
            'recovery_runtime_zero_and_default_rate3']:
    new[key]['stage212_scope_refinement']=dict(evidence=REL+'/official-boot-writer-proof.json',
        current_package_NOR_role='CP-side update route in official script',
        current_NOR_code_not_independent_AP_recovery_proof=True,
        original_byte_claims_retained=True,hardware_route_not_executed=True)
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答；不把继续当批准，不启动或重问，不自动扩大到相机。',
    '优先在已有官方历史包与公开维护者资料中定位经典FX3 AP eMMC启动原件、loader_emmc配置和清单，核对身份/完整性；不能用当前CP NOR镜像或65项清单替代AP启动材料。只做普通本机文件静态分析。',
    '沿独立AP入口和完整同机boot0/p1/配置保存与回读合同继续FX3恢复适配；选中formatter丢弃返回码，独立内容/启动/恢复验收必须分开，不能以退出0或OK充成功。默认参数3/0/4/2仅离线候选。保留全部16项要求、真实MAIN1080p29.97 HEVC及长录验收。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority',
          'current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[k]==old[k],k
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3官方启动属性与AP／CP写入边界](<'+REL+'/README.md>)：更正当前NOR为CP路线，不能充AP救砖；-m/-c分选首/次记录，CP65项预测1088B而AP缺4项，1386比较+44独立拒绝；选中pformat丢弃返回码。7原件/15范围，195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p))
         for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage212-official-boot-generator-v1',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=51,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),
    mutable_heads_not_manifest_members=True,host01_bundle_sha256_unchanged=HOST,
    new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,
    goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),
    raw_ranges=15,source_files=7,present_comparisons=1386,missing_comparisons=44,
    requirements_unchanged=16,authorizations_unchanged=True,root_or_device_operations=0)))
