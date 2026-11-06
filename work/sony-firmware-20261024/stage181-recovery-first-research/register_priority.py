# Register recovery-first research only; no device API, native goal API, or tests.
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import plistlib
import re
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage180-native-MSC-request-channel'
PRIOR_SHA='627afd9565a43b5c68056e8808c260693b0d28af67f290a1df17de01e7030883'
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
QUOTE='主要寻找刷坏退回， 就是因为没有可验证的这些包，才让你去研究怎么更改，对吧。'
REPORT=HERE/'reports/FX3 改机失败 恢复路线.md'
NOTE_DIR=HERE/'research_notes/FX3 改机失败 恢复路线'


def digest(path):return sha256(path.read_bytes()).hexdigest()


def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v.get('VolumeUUID')==UUID and v.get('MountPoint')=='/Volumes/KAFU2T','Target external volume absent or changed'
    assert ROOT.resolve()==Path('/Volumes/KAFU2T/AI/Projects/Mac')


def write_fresh(name,data):
    volume()
    with (HERE/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())


def put(name,value):write_fresh(name,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())


def replace_cas(destination,expected,data,temp_name):
    write_fresh(temp_name,data)
    volume()
    assert destination.read_bytes()==expected,'CAS refused concurrent update: '+str(destination)
    os.replace(HERE/temp_name,destination)
    assert destination.read_bytes()==data


def verify_manifest(path,want):
    assert digest(path)==want,'Prior manifest drift'
    m=json.loads(path.read_text())
    assert m['member_count']==len(m['files'])
    for rec in m['files']:
        p=ROOT/rec['path']
        assert p.resolve().is_relative_to(ROOT.resolve()) and not p.is_symlink()
        assert p.stat().st_size==rec['bytes'] and digest(p)==rec['sha256'],rec['path']
    return m


def main():
    volume()
    assert not (HERE/'final-receipt.json').exists(),'Stage181 already sealed'
    assert not (ROOT/'.git').exists(),'Root unexpectedly became Git-managed'
    prior=verify_manifest(PRIOR/'final-receipt.json',PRIOR_SHA)
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=canonical.read_bytes()
    assert before==(PRIOR/'goal-status-after.json').read_bytes(),'Concurrent canonical drift: refuse registration'
    old=json.loads(before)
    assert old['latest_stage']==PRIOR.name and len(old['requirements'])==16
    assert old['goal_complete'] is False and old['persistent_write_release'] is False
    notes=[NOTE_DIR/n for n in ('official.md','community.md','independent-entry.md')]
    inputs=notes+[REPORT,ROOT/'reports/索尼 FX3 救砖与官方接口.md',PRIOR/'README.md',PRIOR/'final-receipt.json']
    records=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in inputs]
    urls=sorted(set(re.findall(r'https://[^\s)<>]+','\n'.join(p.read_text() for p in notes+[REPORT]))))
    now=datetime.now(timezone.utc).isoformat()
    put('priority-change.json',{'schema':'fx3-research-priority-change/1','recorded_utc':now,
        'user_correction_verbatim':QUOTE,
        'quote_provenance':'Latest direct user correction, relayed verbatim by coordinating parent agent for registration.',
        'research_priority':'recovery-first','principle':'absence of prevalidated modified package is not a research blocker',
        'meaning':'先研究修改失败后如何回退；修改包和恢复方案缺证是待解决问题，不以其缺失循环阻止离线研究。',
        'objective_and_all16_requirement_statuses_unchanged':True,'device_authorization_expanded':False,
        'native_goal_manager_touched':False})
    put('provenance.json',{'schema':'fx3-stage181-research-provenance/1','recorded_utc':now,
        'report_and_complete_notes_plus_background':records,'primary_source_urls_in_notes_and_report':urls,
        'researcher_notes_completed_before_synthesis':True,'synthesis_uses_notes_and_existing_local_evidence_only':True,
        'new_broad_research_or_device_queries_by_registrar':False,
        'source_scope':'Old2.04/2.05 independent updater is distinct from current7.02 installed updater;7.02 up.sh exact-byte bridge is static evidence, not forced-entry or camera acceptance.'})
    next_actions=[
        '恢复优先：静态解析7.02 ud_send_lsi.elf的0/2/5请求、目标控制器/持久标志与上游boot selector，证明MAIN失效后能否独立选择updater；核对7.02材料是否含完整nflasha1，缺件精确登记，不拿2.05代替。',
        '恢复优先：静态追SDUUDConditionChecker::getUpdateFirmwareInfo、dat2/dat3/dat4版本来源及恢复续行分支，输出正常更新/失败续行/独立触发的准入差异表；不把正常同版拒绝推广为恢复拒绝，不照搬A7IV版本补丁。']
    new=deepcopy(old)
    new['updated_utc']=now
    new['latest_stage']=HERE.name
    new['research_activity']='已按用户纠正完成恢复优先综合研究：旧官方独立updater、7.02切换脚本桥接及A7IV受限SD触发设计已分清；下一项聚焦ud_send_lsi/boot selector和恢复续行版本条件。无新增设备动作、测试或授权。'
    new['research_priority']={'mode':'recovery-first','source':REL+'/priority-change.json','user_correction_verbatim':QUOTE,
        'principle':'absence of prevalidated modified package is not a research blocker',
        'focus':'先证明MAIN失效后的独立updater选择与恢复包准入，再据实际写入范围设计最小可逆修改。',
        'prior_offline_actions_retained_as_backlog':True,'device_authorization_expanded':False}
    new['next_safe_offline_actions']=next_actions+old['next_safe_offline_actions']
    audit=new['progress_audit']
    audit['previous_goal_turn_classification']=old['progress_audit']['classification']
    audit['classification']='progress'
    audit['basis'].extend([
        '阶段181逐字登记用户“主要寻找刷坏退回”纠正：缺少已验证修改包是研究要解决的问题，不是离线研究阻断条件；原16项、目标、全部授权与prepared字段保持。',
        '旧2.04/2.05独立kernel/initrd与7.02 up.sh全字节桥接提供具体恢复研究入口；当前7.02完整updater身份、MAIN失效后的独立选择和恢复续行版本门仍未证明。A7IV仅为依赖RP2040/入口及特定修改initrd的设计先例。',
        '恢复材料按RAM/appFw/av-cam与CP/boot-updater范围区分；纯RAM不一律要求全eMMC，认证仍有条件持久副作用。55/20夹具不充相机验收，无新增查询/执行/测试/授权，goal_complete及persistent_write_release保持false。'])
    new['latest_stage_evidence']['stage181_recovery_first_research']={
        'readme':REL+'/README.md','report':REPORT.relative_to(ROOT).as_posix(),'priority_change':REL+'/priority-change.json',
        'provenance':REL+'/provenance.json','recovery_selector_and_resume_version_conditions_proven':False,
        'modified_package_independent_rescue_or_target_MAIN_recording_proven':False,'new_device_operations_or_tests':0}
    allowed={'updated_utc','latest_stage','research_activity','research_priority','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    assert set(new)-set(old)=={'research_priority'}
    for key,value in old.items():
        if key not in allowed:assert new[key]==value,key
    for key,value in old['latest_stage_evidence'].items():assert new['latest_stage_evidence'][key]==value,key
    assert new['requirements']==old['requirements'] and new['authorization']==old['authorization']
    assert new['prepared_first_device_trial']==old['prepared_first_device_trial'] and new['objective']==old['objective']
    after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    write_fresh('goal-status-before.json',before)
    write_fresh('goal-status-after.json',after)
    stage_readme=f'''# 第181轮：先研究改机失败后的恢复路线

2026-10-29。用户纠正：{QUOTE}

**研究顺序改为recovery-first；没有已验证修改包是待解决问题，不是离线研究阻断条件。** 目标仍为经典ILME-FX3 7.02的1080p29.97 HEVC主录，全部16项要求、原状态、授权与旧prepared字段保持。

[综合报告](<reports/FX3 改机失败 恢复路线.md>) · [逐字优先级变更](priority-change.json) · [三份研究笔记及来源指纹](provenance.json)。旧2.04/2.05独立更新环境与7.02 up.sh全字节桥接已分开表述；A7IV的Fastboot→MODE5→SD更新仅为依赖硬件入口和特定修改initrd的设计先例。

接下来仅按现有原件离线追两条：7.02 ud_send_lsi请求及更早boot selector；SD更新器的恢复续行版本条件。正常同版拒绝不推广为恢复拒绝。备份/回退按RAM、appFw、av-cam/CP、boot/updater范围设计，纯RAM不一律要求全eMMC，服务认证的条件持久副作用保留。

未新增相机/USB/原生管理员/Windows/UU/GUI操作、安装、固件执行或测试；55/20旧夹具不充相机验收。当前无已验证修改包、独立救援或目标主录证明，goal_complete=false、persistent_write_release=false。未调用原生goal manager，也未扩大或消耗设备授权。

登记前逐一重验180封存成员，canonical与180 goal-status-after字节相同；本轮保留goal前后及README前后快照，使用新鲜读取和CAS核对后更新可变入口。封存见[最终清单](final-receipt.json)。
'''
    write_fresh('README.md',stage_readme.encode())
    index_before=index.read_bytes()
    text=index_before.decode()
    marker='## 相机与固件研究\n'
    entry=f'- [2026-10-29 FX3改机失败恢复路线](<{REL}/README.md>)：按用户纠正改为恢复优先；已找到独立updater和7.02脚本桥接，下一项追启动选择与恢复续行版本门，无新增设备动作。'
    assert text.count(marker)==1 and REL not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    write_fresh('readme-before.md',index_before)
    write_fresh('readme-after.md',index_after)
    volume()
    assert canonical.read_bytes()==before and index.read_bytes()==index_before,'CAS refused concurrent mutable-head drift'
    replace_cas(canonical,before,after,'.canonical-stage181.tmp')
    replace_cas(index,index_before,index_after,'.index-stage181.tmp')
    assert canonical.read_bytes()==after and index.read_bytes()==index_after
    for rec in records:
        p=ROOT/rec['path'];assert p.stat().st_size==rec['bytes'] and digest(p)==rec['sha256'],'Research source drift'
    verify_manifest(PRIOR/'final-receipt.json',PRIOR_SHA)
    put('registration-verification.json',{'schema':'fx3-stage181-registration-verification/1','recorded_utc':now,
        'previous180_manifest_sha256':PRIOR_SHA,'previous180_members_verified':len(prior['files']),
        'canonical_before_byte_equal_to180_after':True,'requirements_count':16,
        'objective_all16_requirements_statuses_all_authorizations_and_all_prepared_fields_unchanged':True,
        'all_unrelated_top_level_sections_unchanged':True,'all_old_evidence_entries_unchanged':True,
        'old_next_actions_retained_after_two_recovery_first_actions':True,
        'canonical_after_byte_equal_to181_after':True,'root_README_fresh_read_CAS_and_exact_after_match':True,
        'native_goal_manager_untouched':True,'new_camera_USB_admin_Windows_UU_GUI_or_firmware_operations':0,
        'new_installs_or_test_runs':0,'goal_complete':False,'persistent_write_release':False})
    files=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file():
            assert not p.is_symlink()
            files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
    put('final-receipt.json',{'schema':'fx3-stage181-recovery-first-research/1','created_utc':now,'volume_uuid':UUID,
        'previous_manifest_path':(PRIOR/'final-receipt.json').relative_to(ROOT).as_posix(),
        'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_verified':len(prior['files']),
        'files':files,'member_count':len(files),'mutable_heads_not_manifest_members':True,
        'allowed_goal_keys_changed':sorted(allowed),
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(after).hexdigest(),
            'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'research_priority':'recovery-first','native_goal_manager_untouched':True,'new_device_operations_or_test_runs':0,
        'goal_complete':False,'persistent_write_release':False})
    final=HERE/'final-receipt.json'
    final_sha=digest(final)
    verify_manifest(final,final_sha)
    verify_manifest(PRIOR/'final-receipt.json',PRIOR_SHA)
    assert canonical.read_bytes()==after and index.read_bytes()==index_after
    print(json.dumps({'report':str(REPORT),'final_manifest_sha256':final_sha,'members':len(files),
        'previous180_members_verified':len(prior['files']),'canonical_matches181_after':True,
        'requirements_and_authorizations_and_prepared_unchanged':True,'goal_complete':False,
        'persistent_write_release':False,'new_device_operations_or_test_runs':0},ensure_ascii=False))

if __name__=='__main__':main()
