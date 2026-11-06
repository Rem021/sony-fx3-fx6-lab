#!/usr/bin/env python3
"""Seal original-reader guest evidence; preserve all trial permissions."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import copy
import difflib
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage156-hardened-owner-launch-and-ack'
PRIOR_SHA='4a2b0a50ee1ee7480f9c6b4dd089c99adcacdda5287e871748840b99779cda7c'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    member=next(m for m in json.loads(raw)['files'] if m['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==member['sha256']
    spec=importlib.util.spec_from_file_location('reader_lengths_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous=helper.check_previous();assert previous==311
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=(HERE/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    original=(HERE/'readme-before.md').read_bytes();index_before=index.read_bytes()
    assert all(line in index_before.decode().splitlines() for line in original.decode().splitlines() if 'work/sony-firmware-20261024/' in line)
    with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(index_before)
    put('index-rebase-review.json',{'original_sha256':sha256(original).hexdigest(),'rebased_sha256':sha256(index_before).hexdigest(),
        'all_previous_firmware_entries_preserved':True,'diff':list(difflib.unified_diff(original.decode().splitlines(),index_before.decode().splitlines(),lineterm=''))})
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['driver_change'] and not old['authorization']['camera_file_access'] and not old['authorization']['service_auth_mode_or_stop']
    assert not old['prepared_first_device_trial']['Mac_owner_trial_released']
    assert old['prepared_first_device_trial']['Mac_owner_trial_current_candidate_key']=='Mac_owner_trial_fixed_grant_ACK_candidate'
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed'] and not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    lib=BASE/'stage2/extraction/files/nflasha15/lib/libJiritsu.so'
    expected='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9';assert helper.digest(lib)==expected
    caller=json.loads((HERE/'run-original-GET_FILE2/results.json').read_text())
    linked=json.loads((HERE/'run-linked-original-POSIX/results.json').read_text())
    assert caller['case_count']==len(caller['cases'])==16 and linked['case_count']==len(linked['cases'])==10
    assert caller['original_library_sha256']==linked['original_library_sha256']==expected
    assert caller['instruction_entries']==2369 and linked['instruction_entries']==3163
    assert caller['actual_IO_or_file_read_or_DMM_allocation'] is False and linked['no_actual_device_or_native_Sony_IO']
    assert caller['negative_wrapper_returns_are_declared_not_actual_unwind']
    assert linked['negative_errors_stop_before_exception_unwind_and_do_not_prove_the_declared_wrapper_error_returns']
    for source,directory in [('reader_guest.py','run-original-GET_FILE2'),('linked_posix_guest.py','run-linked-original-POSIX')]:
        assert (HERE/source).read_bytes()==(HERE/directory/'executed-source.py').read_bytes()
    review=json.loads((HERE/'read-length-and-result-admission-review.json').read_text())
    assert review['original_library_sha256']==expected and not review['authorization_changed']
    assert review['new_Mac_cached_or_USB_driver_admin_Windows_camera_or_file_service_operations']==0
    assert review['owner_trial_request_pending_no_reply_treated_as_consent']
    by={c['name']:c for c in caller['cases']};lb={c['name']:c for c in linked['cases']}
    assert all(c['function_return_w0']==0 for c in caller['cases'])
    assert lb['linked_short_read']['function_return_w0']==0 and lb['linked_short_read']['reply_status']=='0x1000000a'
    assert lb['linked_4GiB_plus16']['reply_status']=='0x0' and lb['linked_4GiB_plus16']['reply_length']==20
    assert lb['linked_4GiB_plus16']['events_by_name']['read'][0]['args'][2]==16
    for c in linked['cases']:
        if c['name'].endswith('_fenced'):assert not c['service_function_returned'] and c['reply_status'] is None
        else:assert len(c['events_by_name']['close'])==1 and len(c['events_by_name']['fsync'])==2
    assert by['pending_log_short_write']['pending_log_bytes_after']==7
    assert by['pending_log_short_write']['events_by_name']['_ZN11CFileAccess4statEPKcP13tag_FILE_INFO'][0]['path']=='/tmp/jiritsu/jit.log'
    for name,n in [('original-functions.json',6),('linked-original-functions.json',6)]:
        r=json.loads((HERE/name).read_text());assert r['original_library_sha256']==expected and len(r['functions'])==n
    assert review['seek_scope']['direct_B_or_BL_call_sites_in_own_text']==[] and review['seek_scope']['does_not_exclude_indirect_calls_or_other_modules']
    bundle=old['prepared_first_device_trial']['Mac_owner_trial_fixed_grant_ACK_candidate']['bundle_sha256']
    assert helper.digest(PRIOR/'release-bundle.json')==bundle=='e099d58b73261c076491fc0c08c9b1b4b72f5a844fe3af22b3d8060110a956a4'
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Original GET_FILE2 whole-file arithmetic/reply and six native POSIX wrappers checked in26 guest cases/5532 entries; short read vs outer return, low32 truncation and pending-log retarget refined; no actual IO or permission expansion'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段157重验156全部311成员；上一轮固定grant/root staging/ACK及17项自写检查为进展，用户未回复新授权，本轮继续原固件离线备份路线。没有将自动继续视为设备/管理员同意。',
        '16组完整GET_FILE2/原CheckUnitType客体，加10组联接原FileAccess构造/stat/open/read/fsync/close客体，共5532次原指令/边界进入。POSIX/DMM/挂载/加密/日志外部提供者明示为声明结果，无实际文件或设备操作。',
        '短读31/32及EOF后外层函数仍return0，内部状态1000000a；实际备份准入必须核对内部状态与完整长度。声明64位stat4GiB+16经原stat方法后被调用者截为read16且报20字节成功；N+4回绕也已定位。不能将旧GET_FILE2扩成通用分区/大文件备份。',
        '官方app参考79015712普通分支原分类选307，variant1二倍158031432选ffffffff；DMM结果仍fixture，不充实际容量。日志短写后仍改读日志路径，待处理7字节保持，进一步限制固定目标/selector。',
        '正常/短读原包装链准备一次open/read/close与两次fsync，第二次包装close依关闭标志跳过。负POSIX结果停在C++异常申请前，不将声明-1调用者反例充实际展开或漏洞。seek导出无本库直接调用不等整机无分块路线。',
        '156单次试验编号/运行包/selector与原权限保持；未执行缓存、USB、root、Windows、认证/文件/模块或刷写。26客体结果不是实机备份/恢复/救砖/编码验收，16项原要求保持。'])
    new['latest_stage_evidence']['stage157_original_whole_file_read_length_and_status']={
        'readme':REL+'/README.md','review':REL+'/read-length-and-result-admission-review.json',
        'caller_guest':REL+'/run-original-GET_FILE2/results.json','linked_original_guest':REL+'/run-linked-original-POSIX/results.json',
        'caller_cases':16,'linked_cases':10,'instruction_entries':5532,'original_library_sha256':expected,
        'error_unwind_or_actual_file_backup_proven':False,'device_or_admin_operations':0,'physical_acceptance':False}
    new['next_safe_offline_actions'].append('157已验证原整文件读的32位长度/状态及六个FileAccess正常包装链；下一步核对C++异常选择/展开后真实清理和其它模块可达分块路线，读范围及设备内分配要受限，不能仅主机分片。固定libs/app原始文件长度/强摘要与完整同机恢复/独立救援仍须实际证据。156接管授权请求待用户明确回复，编号/运行包/selector不改，不重复询问或执行。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for k,v in old['latest_stage_evidence'].items():assert new['latest_stage_evidence'][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
    marker='## 相机与固件研究\n'
    entry='- [2026-10-28 FX3原整文件读长度与备份准入](<'+REL+'/README.md>)：26组原指令guest/5532进入，短读与外层0返回分离、64位stat到32位读取/分配及日志改读已验证；实际备份/异常展开仍未验，无新增设备操作。'
    text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    with (HERE/'readme-after.md').open('xb') as f:f.write(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after;helper.check_previous()
    put('completed-evidence-review.json',{'status':'PASS_ORIGINAL_FILE_READ_LENGTH_AND_STATUS_NOT_BACKUP_OR_RESCUE_ACCEPTANCE','created_utc':now,
        'previous_manifest_members_verified':previous,'original_guest_cases':26,'instruction_entries':5532,
        'all16_requirements_authorization_constraints_and_all_previous_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'goal_complete':False,'persistent_write_release':False,'Mac_owner_trial_released':False,
        'root_device_cache_or_file_service_operations':0,'current_trial_bundle_unchanged':bundle})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage157-original-read-length-and-status/1','created_utc':now,'volume_uuid':helper.UUID,
        'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,'allowed_goal_keys_changed':sorted(allowed),
        'mutable_project_heads_not_manifest_members':True,'mutable_progress':{'before_sha256':sha256(before).hexdigest(),
        'after_sha256':sha256(encoded).hexdigest(),'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
