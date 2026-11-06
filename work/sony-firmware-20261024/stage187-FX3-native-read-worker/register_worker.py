"""Seal the native read-worker candidate without changing device authority."""
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,os,plistlib,subprocess,zipfile
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
TOOL=ROOT/'outputs/fx3-recovery-adapter'
PRIOR=BASE/'stage186-fx3-bounded-capture-engine'
PRIOR_SHA='93208ab9fd785df1815838fe727f955830d2a899581d40e4ce104c7c2cbccbe9'
REL=str(HERE.relative_to(ROOT))


def digest(p):
    h=sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def volume():
    data=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if data['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise RuntimeError('wrong volume')


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    volume();assert not (HERE/'final-receipt.json').exists()
    assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
    previous=json.loads((PRIOR/'final-receipt.json').read_text());assert len(previous['files'])==5017
    for row in previous['files']:
        p=ROOT/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],row['path']
    release=json.loads((HERE/'release-receipt.json').read_text());archive=ROOT/release['archive']
    assert digest(archive)==release['archive_sha256'] and archive.stat().st_size==release['archive_bytes']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==len(release['files'])==16
        for row in release['files']:
            assert digest(TOOL/row['path'])==row['sha256']
            assert sha256(z.read('fx3-recovery-adapter/'+row['path'])).hexdigest()==row['sha256']
    reports={}
    for kind,want,status,test in [('capture',14,'PASS_LOCAL_BOUNDED_CAPTURE','test_capture.py'),('adapter',13,'PASS_OFFLINE_FX3_IMAGE_ADAPTATION','test_adapter.py')]:
        d=json.loads((HERE/'runs'/f'{kind}-tests-final/test-receipt/results.json').read_text())
        assert d['tests_run']==want and d['status']==status and d['failures']==d['errors']==d['new_camera_or_USB_operations']==0
        for path,h in d['source_sha256'].items():assert digest(TOOL/path)==h
        assert digest(TOOL/'tests'/test)==d['test_sha256'];reports[kind]=d
    w=json.loads((HERE/'runs/worker-tests-ABI-final/test-receipt/results.json').read_text())
    assert w['tests_run']==11 and w['status']=='PASS_COMPILED_WORKER_SYSCALL_FIXTURE' and w['failures']==w['errors']==w['new_camera_operations']==0
    assert not w['AArch64_machine_code_executed'] and w['production_object_only'] and w['fake_kernel_metadata_not_physical_observation']
    assert digest(TOOL/'native/fx3_p1_reader.c')==w['worker_source_sha256']
    assert digest(TOOL/'tests/test_worker.py')==w['test_source_sha256']
    assert w['python_source_sha256']==reports['adapter']['source_sha256']==reports['capture']['source_sha256']
    for path,h in w['python_source_sha256'].items():assert digest(TOOL/path)==h
    for version,h in reports['adapter']['original_references_unchanged'].items():
        assert digest(ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine'/version/'nflasha1')==h
        assert digest(HERE/'runs/adapter-tests-final'/('restored-'+version)/'restored.p1')==h
    assert digest(HERE/'runs/worker-tests-ABI-final/assembled/source.p1')==w['synthetic_source_sha256']==digest(HERE/'runs/worker-tests-ABI-final/restored/restored.p1')
    abi=json.loads((HERE/'kernel-ABI-review.json').read_text());assert len(abi['verified_syscall_numbers'])==12
    for row in abi['references']:assert digest(ROOT/row['path'])==row['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    new=deepcopy(old);now=datetime.now(timezone.utc).isoformat();new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Implemented0.3 fixed-target Linux AArch64 read-worker C candidate and offline wire decoder.11 compiled syscall-fixture tests plus27 host regressions pass; object is relocatable, not linked/executed/deployed. Explicit launch/transport, current7.02 source and real recovery remain open.'
    new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
    new['progress_audit']['basis'].extend([
        '187新增机身侧显式入口C读取候选：固定cnflasha1 O_RDONLY，动态核对内核分区/设备号及容量，真实长度/保护区/元数据/时钟检查；RAM目录fstatfs和独占输出，无preload/构造/删除/源写入/重试。',
        'AArch64 ET_REL对象只编译，未链接为模块且未执行；同C算法Mac系统调用夹具11项/44场景加原14/13项共38项通过。三窗口383块组装→候选→原件还原，源为显式合成2.05补尾非7.02读回。',
        'Linux4.9 UAPI12 syscall号及statfs布局核对，补有符号可用空间负数拒绝后重验；当前Sony内核支持未证。完成清单存在不覆盖非0返回，调用者返回码不提升为相机独立观察。',
        '下一项显式临时启动/链接/传输与同机绑定/归还。p1不是完整eMMC或独立救砖，MSC root整合/SERVICE/认证尾部写入退出及HEVC缺口未消失；不启用或上传候选，授权与16要求不变。',
    ])
    new['latest_stage_evidence']['stage187_native_read_worker_candidate']={
        'readme':REL+'/README.md','worker_source':'outputs/fx3-recovery-adapter/native/fx3_p1_reader.c',
        'worker_test_receipt':REL+'/runs/worker-tests-ABI-final/test-receipt/results.json',
        'ABI_review':REL+'/kernel-ABI-review.json','version':'0.3.0','release':release['archive'],'release_sha256':release['archive_sha256'],
        'tests_passed':38,'fixture_cases':len(w['cases']),'AArch64_object_only_not_linked_or_executed':True,
        'camera_startup_or_transport_route_implemented':False,'current7_02_p1_identity_verified':False,
        'same_point_in_time_or_independent_recovery_proven':False,'new_camera_operations':0}
    new['next_safe_offline_actions'].append('187已完成固定只读C工作器候选和格式解码；下一项链接与单个临时进程的显式启动/传输路线，优先避全局preload，追原命令入口并固定同机/范围/归还。当前仅ET_REL对象，不得作为模块上传/执行；p1非完整eMMC/独立救砖，首次实际采集仍需具体完整方案与新增授权。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for key in old:
        if key not in allowed:assert old[key]==new[key],key
    for key in old['latest_stage_evidence']:assert old['latest_stage_evidence'][key]==new['latest_stage_evidence'][key]
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    index=ROOT/'README.md';ib=index.read_bytes();(HERE/'readme-rebased-before.md').write_bytes(ib)
    marker='## 相机与固件研究\n';entry='- [FX3恢复适配工具0.3](outputs/fx3-recovery-adapter/README.md)：新增固定只读C工作器候选和输出解码，38项本地检查通过；AArch64仅编译对象，未链接、未上机，无独立救砖证明。[187证据](<'+REL+'/README.md>)。'
    text=ib.decode();assert text.count(marker)==1 and entry not in text
    ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(ia)
    volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS concurrent change'
    for path,data,name in [(canonical,encoded,'.goal.tmp'),(index,ia,'.index.tmp')]:
        p=HERE/name
        with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(p,path)
    files=[];excluded=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_symlink():excluded.append({'path':str(p.relative_to(ROOT)),'reason':'intentional adversarial link fixture not followed'});continue
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
    put('final-receipt.json',{'schema':'fx3-stage187-native-reader-candidate-v1','created_utc':now,'previous_manifest_sha256':PRIOR_SHA,
        'files':files,'member_count':len(files),'excluded':excluded,'external_immutable_release':{'path':release['archive'],'sha256':release['archive_sha256'],'bytes':release['archive_bytes']},
        'source_working_tree_mutable_not_manifest_members':True,'source_snapshot_in_verified_release_archive':True,'mutable_heads_not_manifest_members':True,
        'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),'tests_passed':38,'new_camera_or_USB_operations':0,
        'native_goal_manager_untouched':True,'goal_complete':False,'persistent_write_release':False})
    print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(files),'tests_passed':38,'archive_sha256':release['archive_sha256'],'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
