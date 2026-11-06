#!/usr/bin/env python3
"""Adopt158 under the current159 authorization state; no device release."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import copy
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage159-authorized-owner-trial-preflight'
PRIOR_SHA='c3463719ae200f824428fd490eb41db6cfcfbb6b11034a5297af8144ef719c2b'
WORK=BASE/'stage158-original-LSDA-and-read-error-cleanup'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    m=next(m for m in json.loads(raw)['files'] if m['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==m['sha256']
    spec=importlib.util.spec_from_file_location('current_LSDA_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous=helper.check_previous();assert previous==8
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=canonical.read_bytes(),index.read_bytes()
    assert before==(PRIOR/'goal-status-after.json').read_bytes()
    (HERE/'goal-status-before.json').write_bytes(before);(HERE/'readme-before.md').write_bytes(index_before)
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert old['authorization']['Mac_owner_trial_authorized'] and old['authorization']['Mac_owner_trial_admin_launch_authorized']
    assert not old['prepared_first_device_trial']['Mac_owner_trial_released']
    assert not old['authorization']['camera_file_access'] and not old['authorization']['service_auth_mode_or_stop']
    grant='fx3-702-msc-owner-20261028-01'
    assert old['authorization']['Mac_owner_trial_grant_id']==grant
    bundle=BASE/'stage156-hardened-owner-launch-and-ack/release-bundle.json'
    bundle_sha='e099d58b73261c076491fc0c08c9b1b4b72f5a844fe3af22b3d8060110a956a4'
    assert helper.digest(bundle)==bundle_sha==old['authorization']['Mac_owner_trial_bundle_sha256']
    for m in json.loads(bundle.read_text())['files']:assert helper.digest(bundle.parent/m['path'])==m['sha256']
    assert not (bundle.parent/'physical-grant-attempt.claim').exists() and not Path('/private/tmp',grant).exists()
    library=BASE/'stage2/extraction/files/nflasha15/lib/libJiritsu.so'
    lib_sha='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
    assert helper.digest(library)==lib_sha
    assert (WORK/'lsda_audit.py').read_bytes()==(WORK/'LSDA-parser-executed.py').read_bytes()==(WORK/'run-LSDA-selected-errors/metadata-parser-executed.py').read_bytes()
    assert (WORK/'error_landing_pad_guest.py').read_bytes()==(WORK/'run-LSDA-selected-errors/executed-source.py').read_bytes()
    parsed=json.loads((WORK/'original-LSDA-review.json').read_text())
    assert parsed['original_library_sha256']==lib_sha and len(parsed['functions'])==6 and parsed['callsite_count']==46
    assert not parsed['actual_personality_unwinder_or_camera_executed']
    for f in parsed['functions']:
        if f['function']=='adj_cmd_get_file2':assert not f['types']
        else:
            types={t['filter']:t for t in f['types']}
            assert types[1]['RTTI_symbol']=='_ZTI19FileAccessException' and types[2]['RTTI_symbol']=='_ZTISt9exception'
            assert not types[1]['catch_all'] and not types[2]['catch_all']
    tests=json.loads((WORK/'run-LSDA-selected-errors/results.json').read_text())
    assert tests['case_count']==len(tests['cases'])==12 and tests['instruction_entries']==5030 and tests['modeled_exception_selections']==19
    assert not tests['actual_camera_or_native_Sony_runtime_executed'] and tests['external_runtime_and_POSIX_providers_are_declared_not_physical_success']
    cases={c['name']:c for c in tests['cases']}
    for name in ['close_errors','fsync_and_close_errors']:
        c=cases[name];assert c['reply_status']=='0x0' and c['reply_length']==36
        assert len(c['events_by_name']['close'])==2 and c['original_file_object_fields_after_outer_return'][0]['open_flag']==1
    assert cases['first_close_error_second_success']['original_file_object_fields_after_outer_return'][0]['open_flag']==0
    assert cases['read_error']['reply_status']=='0x1000000a' and cases['open_error']['reply_status']=='0x10000008'
    assert cases['stat_error']['reply_status']=='0x10000006'
    assert cases['near4GiB_read_error_alias']['reply_status']=='0x0' and cases['near4GiB_read_error_alias']['reply_length']==3
    for c in tests['cases']:
        assert c['function_return_w0']==0 and c['LSDA_selected_runtime_provider']
        assert not c['external_personality_unwinder_allocator_type_match_and_catch_release_executed']
        assert all(e['selection']['kind']=='handler' and e['selection']['filter']==1 and e['thrown_RTTI']=='_ZTI19FileAccessException' for e in c['throws'])
    upstream=json.loads((WORK/'upstream-reference-receipt.json').read_text())
    assert upstream['commit']=='abaef5489e27672c45aa05f41ea7ed52f3fa2748'
    for m in upstream['files']:
        assert helper.digest(WORK/m['local_path'])==m['sha256'] and (WORK/m['local_path']).stat().st_size==m['bytes'] and m['downloaded_not_executed']
    review=json.loads((WORK/'error-cleanup-admission-review.json').read_text())
    assert review['metadata_functions']==6 and review['callsite_rows']==46 and review['new_root_or_active_USB_or_camera_file_operations']==0
    preserved=[helper.record(p) for p in sorted(WORK.rglob('*')) if p.is_file()]
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Original6-function LSDA/46 callsites plus12 error/cleanup guest cases with19 metadata-selected provider contexts; close-error retained flags can coexist with data success; actual Sony runtime and device remain untested'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段160重验159全部8成员及156固定运行包。上一轮明确授权与挂载前置检查为进展；本轮在保存授权状态下采用158WIP的原异常表解析和新错误路径guest，未使用旧157 before回写。',
        '原7.02 libJiritsu注释GCC6.4.0/Sony CE，六函数46调用区间解码：FileAccessException为filter1，std::exception为filter2，非catch-all；GET_FILE2相关表为cleanup。上游6.4 commit与三份参考SHA固定，非实际Sony运行时。',
        '12组原指令guest/5030进入，19次上下文按原LSDA与CFI选定；原栈/帧保持，运行时参数/IP由明示提供者交付。stat/open/read错误分别回10000006/08/0a；fsync错误可被成功字掩盖。',
        '声明两次close失败时出现两次同FD调用，最终读取成功但原对象open标志1/FD3保留；第一次失败第二次成功时才清标志/FD。字段不是实际内核FD存活，未观察真实泄漏/FD复用误关。Linux close错误可能已释放FD，不能假设失败就重试来证明恢复。',
        '实际personality/unwinder/异常析构/系统调用/DMM/挂载/加密仍未执行；12例不充实机备份/恢复/救砖验收。最后一次缓存见disk10s1挂载，已获156单次授权但保持runtime release=false且次数未耗，不自动卸载/请求重复授权或调用管理员。全部16要求/旧候选/权限保持。'])
    new['latest_stage_evidence']['stage160_original_LSDA_selected_error_and_close_review']={
        'readme':REL+'/README.md','LSDA':str((WORK/'original-LSDA-review.json').relative_to(ROOT)),
        'guest':str((WORK/'run-LSDA-selected-errors/results.json').relative_to(ROOT)),
        'review':str((WORK/'error-cleanup-admission-review.json').relative_to(ROOT)),
        'metadata_functions':6,'callsite_rows':46,'guest_cases':12,'instruction_entries':5030,'modeled_contexts':19,
        'actual_Sony_runtime_or_POSIX_IO_proven':False,'new_root_or_active_device_operations':0}
    new['next_safe_offline_actions'].append('160已将原异常表与处理代码在显式运行时提供者下联接：成功字/完整数据不充句柄清理；关闭失败可能触发重复同FD close，原字段未清不等实际FD仍开。继续寻找可独立核对清理与设备分配的有界读取方案，不直接发布旧GET_FILE2为健康备份。156授权已获准且不重复询问，仍等待所有FX3卷手动推出；满足已批准前置条件后才放行固定编号一次，当前未耗。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for k,v in old['latest_stage_evidence'].items():assert new['latest_stage_evidence'][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    marker='## 相机与固件研究\n'
    entry='- [2026-10-28 FX3异常表与读取清理结果](<'+REL+'/README.md>)：6函数/46调用区间、12组原指令guest；关闭失败可保留open标志而数据回复成功，实际运行时及备份未验；已获接管授权仍等待卷推出，次数未耗。'
    text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed and [helper.record(p) for p in sorted(WORK.rglob('*')) if p.is_file()]==preserved
    for target,data,name in [(canonical,encoded,'.goal.tmp'),(index,index_after,'.index.tmp')]:
        tmp=HERE/name
        with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after;helper.check_previous()
    put('completed-evidence-review.json',{'status':'PASS_ORIGINAL_ERROR_HANDLER_AND_FIELD_REVIEW_NOT_RUNTIME_OR_CAMERA_ACCEPTANCE','created_utc':now,
        'previous_manifest_members_verified':previous,'LSDA_functions':6,'callsite_rows':46,'guest_cases':12,'instruction_entries':5030,
        'modeled_contexts':19,'adopted158_before_snapshot_not_current_parent':True,
        'all16_requirements_authorization_and_previous_prepared_values_preserved':True,'fixed_guest_front_backend_pins':fixed,
        'current_grant_authorized':True,'runtime_released':False,'physical_attempt_consumed':False,'goal_complete':False,'persistent_write_release':False})
    files=preserved+[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage160-LSDA-error-cleanup/1','created_utc':now,'volume_uuid':helper.UUID,
        'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,'adopted_work_directory':str(WORK.relative_to(ROOT)),
        'allowed_goal_keys_changed':sorted(allowed),'mutable_heads_excluded':True,'canonical_after_sha256':sha256(encoded).hexdigest()})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'runtime_release':False,'physical_attempt_consumed':False}))


if __name__=='__main__':main()
