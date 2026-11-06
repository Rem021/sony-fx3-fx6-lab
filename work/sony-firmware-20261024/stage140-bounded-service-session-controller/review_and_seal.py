#!/usr/bin/env python3
"""Seal inert session code/fixtures while preserving the complete real-device goal."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import copy
import importlib.util
import json
import os

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()
PRIOR = BASE / 'stage139-service-callback-bridge-and-queue-return'
PRIOR_SHA = '31d86ba93f56c44872b0036c83a4bb6cd053fc8f8d34cc01e76872c461819f6a'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


def put(name, value):
    with (HERE / name).open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    assert not (HERE / 'final-receipt.json').exists()
    assert sha256((HELPER / 'final-receipt.json').read_bytes()).hexdigest() == '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin = next(x for x in json.loads((HELPER / 'final-receipt.json').read_text())['files']
               if x['path'] == (HELPER / 'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER / 'review_and_seal.py').read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('pinned_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    previous_count = helper.check_previous()
    assert previous_count == 13
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    for folder, count in [('run-fault-injection-initial39', 39),
                          ('run-fault-injection-pre-provider-isolation46', 46), ('run-fault-injection', 47)]:
        d = HERE / folder
        result = json.loads((d / 'results.json').read_text())
        assert result['case_count'] == count and len(result['cases']) == count
        assert helper.digest(d / 'session-controller-executed.py') == result['controller_sha256']
        assert helper.digest(d / 'test-executed.py') == result['test_sha256']
        assert not result['live_transport_implemented'] and result['USB_driver_Windows_or_camera_operations'] == 0
    result = json.loads((HERE / 'run-fault-injection/results.json').read_text())
    assert result['status'] == 'PASS_INERT_SESSION_FAULT_INJECTION_NOT_USB_AUTHENTICATION_OR_DEVICE_RECOVERY'
    assert result['credential_computation_is_external_inert_task_not_inline_callback']
    assert (HERE / 'session_controller.py').read_bytes() == (HERE / 'run-fault-injection/session-controller-executed.py').read_bytes()
    assert (HERE / 'test_session_controller.py').read_bytes() == (HERE / 'run-fault-injection/test-executed.py').read_bytes()
    cases = {x['name']: x for x in result['cases']}
    assert cases['complete_fixture_family8']['report']['phase'] == 'FLOW_FINISHED'
    assert cases['complete_fixture_family2']['report']['auth_exchanges'] == {'MSC': 7, 'SERVICE': 7}
    for name in ['stop0_no_observed_effect','restore0_driver_not_bound','dispose0_loses_driver',
                 'cross_session_receipt_rejected','late_completed_receipt_does_not_resume',
                 'pending_DERIVE_DIGEST','same_session_receipt_replay_rejected']:
        assert cases[name]['report']['phase'] == 'UNKNOWN', name
    assert cases['physical_receipt_still_missing']['report']['phase'] == 'WAIT_PHYSICAL'
    for case in cases.values():
        report = case['report']
        assert report['stop_attempts'] <= 1 and max(report['starts'].values()) <= 1
        assert max(report['auth_exchanges'].values()) <= 7
        assert not report['evidence']['worker_completion']
        assert not report['actual_hardware_acceptance'] and not report['live_release']
    incident = json.loads((HERE / 'host-run-interruption.json').read_text())
    assert not incident['Python_test_assertion_failure_observed'] and not incident['unrelated_data_deleted']
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Implemented inert single-body service-session controller and47 fault scenarios; real transport/credentials/timings not ready'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段140实现单机惰性会话控制器：每模式1次start/7交换认证、最多1次stop，先记录意图再分派，超时未知不重发。',
        '47故障场景、4协议向量/3畸形帧通过；覆盖最终认证拒绝、身份替换/重放、在途、退出0无效果、驱动和物理结果分层。',
        '凭据计算移至有deadline的独立惰性任务，不内联执行任意provider；真实Sony凭据/USB后端和实机时限未实现验证。',
        '首轮39与隔离前46回执及源码保留；本机heredoc临时空间中断后改用项目外置临时目录，未清理其他数据。',
        '没有新设备/驱动/原Sony执行；所有16项要求、现有授权/用户Mac-only约束与75/117原型、旧准备字段保持。'])
    key = 'stage140_bounded_service_session_controller'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'controller': REL + '/session_controller.py',
        'fault_receipt': REL + '/run-fault-injection/results.json', 'host_interruption': REL + '/host-run-interruption.json',
        'inert_fault_cases': 47, 'codec_vectors': 4, 'malformed_codec_cases': 3,
        'initial39_and_pre_provider_isolation46_preserved': True,
        'real_USB_transport_or_Sony_credentials_implemented': False,
        'hardware_timing_or_actual_auth_recovery_verified': False,
        'new_device_or_driver_operations': 0, 'authorization_unchanged': True}
    new['prepared_first_device_trial']['inert_service_session_controller'] = REL + '/session_controller.py'
    new['prepared_first_device_trial']['service_session_fault_receipt'] = REL + '/run-fault-injection/results.json'
    new['prepared_first_device_trial']['inert_controller_implemented'] = True
    new['prepared_first_device_trial']['real_transport_credentials_and_hardware_timings_ready'] = False
    new['next_safe_offline_actions'].append(
        '阶段140后固定来源实现/核对真实Sony认证摘要提供者及Mac传输适配：单机凭据与USB配置、显式capture/attach配对、close无隐式复位、在途完成真实判据和实机前可审核期限。保持47场景的无重试/UNKNOWN/身份与物理证据分层；测试摘要及夹具同机/驱动/物理输入不能作为实机通过，尚无服务操作或持久刷写放行。')
    allowed = {'updated_utc','latest_stage','research_activity','progress_audit',
               'latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for key, value in old[section].items():
            assert new[section][key] == value
    encoded = (json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3单机会话控制器与47故障场景](<' + REL + '/README.md>)：惰性状态核心/协议向量通过，未知与无重试/驱动物理证据分层已实现；真实USB/凭据/时限及实机恢复未验。'
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent heads changed; CAS refused'
    assert helper.pins(old) == fixed
    for target, data, name in [(canonical,encoded,'.goal-write.tmp'),(index,index_after,'.index-write.tmp')]:
        temporary=HERE/name
        with temporary.open('xb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    completed={'status':'PASS_INERT_CONTROLLER47_NOT_LIVE_TRANSPORT_OR_CAMERA_ACCEPTANCE','created_utc':now,
        'previous_manifest_members_verified':previous_count,'inert_fault_cases':47,'codec_vectors':4,'malformed_codec_cases':3,
        'historical39_and46_results_sources_preserved':True,'credential_provider_external_timed_intent':True,
        'new_device_or_driver_or_original_Sony_execution':0,
        'all16_requirements_authorization_and_user_constraints_unchanged':True,
        'old_prepared_trial_and_source_evidence_preserved':True,'stage75_backend_and_stage117_frontend_pins':fixed,
        'canonical_equals_after':True,'same_agent_local_review_not_real_camera_acceptance':True,
        'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',completed)
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage140-inert-service-controller/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
                           'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'operations':completed})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
                      'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__ == '__main__':
    main()
