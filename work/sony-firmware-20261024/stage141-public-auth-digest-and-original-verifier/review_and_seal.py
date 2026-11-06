#!/usr/bin/env python3
"""Seal public digest/original-verifier evidence without changing camera authority."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import copy
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage140-bounded-service-session-controller'
PRIOR_SHA='5cc7e18aea8ae5d407bdf075bd9d8e4031ecf838fac84fa76b870b362ca19816'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x') as handle:
        json.dump(value,handle,ensure_ascii=False,indent=2);handle.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    assert sha256((HELPER/'final-receipt.json').read_bytes()).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin=next(x for x in json.loads((HELPER/'final-receipt.json').read_text())['files']
             if x['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();count=helper.check_previous();assert count==19
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed=helper.pins(old)
    inputs=json.loads((HERE/'upstream-inputs.json').read_text())
    assert len(inputs['records'])==3
    for record in inputs['records']:
        assert not record.get('download_failed')
        path=ROOT/record['path'];assert path.stat().st_size==record['bytes'] and helper.digest(path)==record['sha256']
    review=json.loads((HERE/'original-digest-review.json').read_text())
    assert review['status']=='PASS_PUBLIC_SHA256_MATERIAL_AND_ORIGINAL_FX3_INPUT_ASSEMBLY_NOT_DEVICE_AUTH'
    assert len(review['round_material_map'])==3 and all(x['exact_bytes_match'] for x in review['round_material_map'])
    assert review['original_challenge_code']==8 and review['digest']=='SHA-256'
    assert len(review['functions'])==4 and len(review['checked_calls'])==5
    assert helper.digest(HERE/'public_digest_provider.py')==review['provider_source_sha256']
    caller=json.loads((HERE/'caller-round-review.json').read_text())
    assert caller['initial_round']==1 and caller['inclusive_round_limit']==3 and caller['no_NinThread_execution']
    result=json.loads((HERE/'run-original-verifier/results.json').read_text())
    assert result['status']=='PASS_PUBLIC_PROVIDER_WITH_ORIGINAL_FX3_VERIFIER_AND_INERT_CONTROLLER_NOT_LIVE_AUTH'
    assert len(result['native_verifier_cases'])==result['native_verifier_case_count']==38
    assert sum(x['expected']==0 for x in result['native_verifier_cases'])==24
    assert all(x['original_return']==x['expected'] for x in result['native_verifier_cases'])
    assert result['inert_controller_integration']['round_count']==6
    assert all(x['original_return']==0 for x in result['inert_controller_integration']['original_verifier_rounds'])
    assert result['original_guest_function_entries']==169 and result['provider_invalid_input_cases']==7
    assert result['AST_nonliteral_rejected'] and result['no_original_full_NinThread_or_live_authentication_executed']
    assert result['inert_controller_integration']['challenge_generation_final_auth_acceptance_mode_driver_and_physical_receipts_are_fixtures']
    assert result['EVP_SHA256_and_C_memory_operations_are_CPU_bridges_not_original_camera_OpenSSL_execution']
    assert (HERE/'public_digest_provider.py').read_bytes()==(HERE/'run-original-verifier/provider-executed.py').read_bytes()
    assert (HERE/'test_provider_with_original.py').read_bytes()==(HERE/'run-original-verifier/test-executed.py').read_bytes()
    assert helper.digest(HERE/'test_provider_with_original.py')==result['test_sha256']
    pin=result['inert_controller_integration']['controller_source_pin']
    assert helper.record(ROOT/pin['path'])==pin
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Fixed public SHA256 material/provider matched to original FX3 verifier and inert controller; no device authentication'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段141固定PMCA公开材料3块各512B，与FX3原库逐字节相同；原挑战8/SHA256与调用者1..3轮、主机0..2编号已对应。',
        '实现固定SHA/AST literal的CPU摘要提供者，未导入或执行下载源码；FX3专用提供者拒绝旧SHA1码2，未假称工厂私钥。',
        '原xxstep/CmdDecode/SEN摘要封装在Unicorn中38例(24接受/14拒绝)，6原轮接140惰性会话，共169原函数进入。EVP和C内存为CPU桥。',
        '最终认证接受/设备变化/驱动和物理确认仍为夹具，无完整NinThread、实机认证或历史写入；尚缺Mac真实传输及期限审查。',
        '没有设备/驱动或Sony原生主机执行；所有16项要求、完整授权/用户Mac-only约束、旧准备字段和75/117固定原型保持。'])
    key='stage141_public_auth_digest_and_original_verifier';assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key]={
        'readme':REL+'/README.md','public_provider':REL+'/public_digest_provider.py',
        'original_material_review':REL+'/original-digest-review.json','caller_round_review':REL+'/caller-round-review.json',
        'guest_and_inert_integration':REL+'/run-original-verifier/results.json',
        'exact_public_material_blocks':3,'native_verifier_cases':38,'accepted_cases':24,'rejected_cases':14,
        'inert_controller_original_rounds':6,'original_guest_function_entries':169,
        'real_Sony_factory_private_credentials_obtained':False,'actual_device_authentication_or_recovery_proven':False,
        'new_device_or_driver_operations':0,'authorization_unchanged':True}
    new['prepared_first_device_trial']['fixed_public_auth_digest_provider']=REL+'/public_digest_provider.py'
    new['prepared_first_device_trial']['public_provider_original_verifier_receipt']=REL+'/run-original-verifier/results.json'
    new['prepared_first_device_trial']['public_SHA256_digest_implemented_and_offline_verified']=True
    new['prepared_first_device_trial']['actual_body_authentication_or_real_transport_ready']=False
    new['next_safe_offline_actions'].append(
        '阶段141后实现Mac传输层并离线审查单机缓存到接口绑定、固定VID/PID/端点/包长、显式capture/attach配对和close无隐式复位。公开SHA256摘要虽接原校验器及惰性控制器，最终认证接受与模式/驱动/物理仍为夹具；不把原比较0充实机认证或完整写者退出。审查在途完成/取消与时间界限，形成具体方案再请求对应实机授权；完整MAIN/备份恢复/独立救援要求保持。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit',
             'latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,v in old[section].items():assert new[section][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    (HERE/'goal-status-after.json').write_bytes(encoded)
    entry='- [2026-10-27 FX3公开摘要与原认证校验器](<'+REL+'/README.md>)：三块材料逐字节对应，38原校验例/六轮惰性集成通过；真实USB/整机认证及恢复未验，刷写未放行。'
    marker='## 相机与固件研究\n';text=index_before.decode()
    assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-write.tmp'),(index,index_after,'.index-write.tmp')]:
        temporary=HERE/name
        with temporary.open('xb') as h:h.write(data);h.flush();os.fsync(h.fileno())
        os.replace(temporary,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    completed={'status':'PASS_PUBLIC_PROVIDER_ORIGINAL_GUEST_CHECK_NOT_DEVICE_AUTHENTICATION',
        'created_utc':now,'previous_manifest_members_verified':count,'exact_material_blocks':3,
        'original_verifier_cases':38,'inert_integration_rounds':6,'original_guest_function_entries':169,
        'provider_invalid_inputs':7,'AST_nonliteral_rejection':True,'new_native_host_camera_or_driver_operation':0,
        'all16_requirements_authorization_and_user_constraints_unchanged':True,
        'old_prepared_trial_and_source_evidence_preserved':True,'stage75_backend_and_stage117_frontend_pins':fixed,
        'canonical_equals_after':True,'same_agent_local_review_not_real_camera_acceptance':True,
        'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',completed)
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage141-public-digest-original-verifier/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
                           'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'operations':completed})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
                      'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
