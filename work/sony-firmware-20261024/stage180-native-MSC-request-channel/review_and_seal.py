"""Register native MSC protocol/child-process fixtures without changing authority."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage179-bounded-IOKit-wire'
PRIOR_SHA='cfc2b5495d0e4cca11e6dc9d700104f3d25b23ea99ff57a990220fe1e8e3e3d8'
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def digest(p):return sha256(p.read_bytes()).hexdigest()


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==UUID


def main():
    volume();assert not (HERE/'final-receipt.json').exists()
    f=PRIOR/'final-receipt.json';assert digest(f)==PRIOR_SHA
    previous=json.loads(f.read_text())
    for rec in previous['files']:
        path=ROOT/rec['path'];assert path.stat().st_size==rec['bytes'] and digest(path)==rec['sha256']
    assert len(previous['files'])==38
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=(HERE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(PRIOR/'goal-status-after.json').read_bytes()
    old=json.loads(before)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['service_auth_mode_or_stop']
    build=json.loads((HERE/'build-receipt-v6.json').read_text())
    assert not build['native_object_linked_or_executed'] and build['new_root_or_device_operations']==0
    for name,want in build['sources'].items():assert digest(HERE/name)==want
    for name in ('native_object','process_fixture'):
        rec=build[name];assert '-Werror' in rec['argv'] and digest(Path(rec['argv'][-1]))==rec['sha256']
    dep=build['process_fixture']['dependencies'].splitlines()[1:]
    assert len(dep)==1 and '/usr/lib/libSystem.B.dylib' in dep[0]
    r=json.loads((HERE/'run-process-tests-v3/results.json').read_text())
    assert r['status']=='PASS_NATIVE_MSC_DISPATCH_AND_REAL_PROCESS_FIXTURES_NO_USB'
    assert r['case_count']==len(r['cases'])==20 and r['actual_root_or_USB_operations']==0
    assert r['real_root_bootstrap_or_peer_credential_verification'] is False
    for name,want in r['source_sha256'].items():assert digest(HERE/name)==want==digest(HERE/'run-process-tests-v3'/name)
    assert len([x for x in r['cases'] if x['name'].startswith('native-MSC-budget')])==2
    for x in r['cases'][:2]:assert x['summary']['calls']==[2,7,7] and not x['summary']['body_completion_proven']
    last=r['cases'][-1]
    assert last['name']=='actual-controller-exit-sets-cancel-retains-pending-no-IN-or-automatic-STOP'
    assert last['summary']['calls']==[1,1,0] and last['summary']['host_idle'] and not last['summary']['peer_alive']
    assert not last['summary']['automatic_STOP'] and not last['summary']['body_completion_proven']
    assert last['result']['native'][0]['status']==17 and last['result']['pending']==0
    assert json.loads((HERE/'final-process-inventory.json').read_text())['current_process_matches']==0
    assert json.loads((HERE/'run-process-tests/results.json').read_text())['case_count']==16
    assert json.loads((HERE/'run-process-tests-v2/results.json').read_text())['case_count']==20
    now=datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json',{
        'created_utc':now,'previous179_members_verified':38,'current_real_process_fixture_cases':20,
        'MSC_grammar_and_single_session_budgets_in_C':True,
        'datagram_protocol_contains_no_pointer_or_file_command':True,
        'real_controller_exit_while_fake_native_call_pending_exercised':True,
        'exclusive_host_context_invalidation_and_detach_tested_during_blocked_fake_call':True,
        'host_finalization_not_device_close_or_worker_completion':True,
        'direct_children_waited_exit0_orphan_receipt_and_later_absence_separate':True,
        'native_module_compiled_not_linked_into_root_owner':True,
        'root_launch_peer_credentials_target_identity_pipe_map_and_SERVICE_not_implemented':True,
        'old_compile_clock_failure_missing_stdout_and_builds_preserved':True,
        'new_root_USB_Sony_auth_or_camera_operations':0,
        'same_agent_local_review_not_camera_or_privileged_IPC_acceptance':True,
    })
    new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']=('Implemented C-only bounded MSC request dispatcher and fixed datagram process fixture; '
        '20 current process cases passed, including actual controller exit during a blocked fake native call. '
        'No real root owner linkage/bootstrap, peer-credential admission, camera auth or recovery operation.')
    new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification']
    new['progress_audit']['classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段180保持179封存38成员，MSC认证顺序/一START/七交换/一STOP及固定代次/nonce/递增编号预算已独立落地C；SERVICE未实现。',
        '20项当前真实子进程夹具通过，固定572请求/676响应，无地址或文件操作；摘要与设备响应仍全为夹具，不充真机认证。',
        '实际控制端在假OUT阻塞时退出，持有者设置取消并保留在途；显式释放夹具后无IN/自动STOP，host idle与相机线程完成继续分开。',
        '生命周期复核修复仅查看pending的检查/使用间隙，改同一排他锁下本地失效与分离；当前源码/执行快照和v6构建一致，20项重新通过。',
        'SDK宏名冲突及首轮夹具时钟倒退失败保留；早轮最后stdout缺失原因未证，不算退出成功。当前直接子进程退出0和孤儿完成/后续不存在分别核对，无强杀。',
        '实际root启动与拥有者插入、UID/PID出生/审计身份、实际管道/目标身份/单次授权及跨模式预算仍未接通；全部16要求/授权/限制不变，无新增相机操作。',
    ])
    new['latest_stage_evidence']['stage180_native_MSC_request_channel']={
        'readme':REL+'/README.md','dispatcher':REL+'/native_session.c','verification':REL+'/run-process-tests-v3/results.json',
        'build':REL+'/build-receipt-v6.json','review':REL+'/completed-local-review.json',
        'real_process_fixture_cases':20,'MSC_grammar_and_budgets_in_native_candidate':True,
        'real_root_bootstrap_identity_and_owner_integration_ready':False,'SERVICE_ready':False,
        'actual_camera_authentication_backup_restore_rescue_or_MAIN_recording_proven':False,
        'new_root_or_camera_operations':0,
    }
    prepared=new['prepared_first_device_trial']
    prepared['native_MSC_request_channel_candidate']=REL+'/native_session.c'
    prepared['native_MSC_request_channel_fixture_receipt']=REL+'/run-process-tests-v3/results.json'
    prepared['native_MSC_request_channel_live_ready']=False
    new['next_safe_offline_actions'].append(
        '180已将MSC语法/次数放入C并验证匿名子进程夹具，仍不是root IPC。后续先固定真实拥有者插入点与管道索引保存、root bootstrap和既有PID/出生/UID/审计会话/单次授权绑定，再验证真实关闭顺序；不得以finish_host充设备退出。SERVICE/认证条件写入/完整备份恢复/独立救砖和MAIN目标仍未实机放行。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for key in old:
        if key not in allowed:assert new[key]==old[key],key
    for sec in ('prepared_first_device_trial','latest_stage_evidence'):
        for key,value in old[sec].items():assert new[sec][key]==value,(sec,key)
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
    index_before=index.read_bytes()
    with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(index_before)
    entry='- [2026-10-29 FX3原生MSC请求通道](<'+REL+'/README.md>)：C层单会话预算与20项真实进程夹具通过，含控制端退出时保留在途；root拥有者/身份/实际服务仍未整合，无新增相机操作。'
    marker='## 相机与固件研究\n';text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    with (HERE/'readme-after.md').open('xb') as f:f.write(index_after)
    volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'CAS refused concurrent update'
    for dest,data,name in ((canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')):
        tmp=HERE/name
        with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,dest)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    files=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            assert not path.is_symlink();files.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)})
    put('final-receipt.json',{'schema':'fx3-stage180-native-MSC-process-fixture/1','created_utc':now,'volume_uuid':UUID,
        'previous_manifest_sha256':PRIOR_SHA,'files':files,'member_count':len(files),'mutable_heads_not_manifest_members':True,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_progress':{'before_sha256':sha256(before).hexdigest(),
            'after_sha256':sha256(encoded).hexdigest(),'readme_before_sha256':sha256(index_before).hexdigest(),
            'readme_after_sha256':sha256(index_after).hexdigest()},'new_root_USB_or_camera_operations':0,
        'goal_complete':False,'persistent_write_release':False})
    print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(files),'current_process_cases':20,
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
