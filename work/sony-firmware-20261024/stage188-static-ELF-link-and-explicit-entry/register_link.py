"""Seal offline executable/guest evidence; keep all physical gates unchanged."""
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,os,plistlib,subprocess,zipfile
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
TOOL=ROOT/'outputs/fx3-recovery-adapter';PRIOR=BASE/'stage187-FX3-native-read-worker'
PRIOR_SHA='0beb9a992141e9807accc33e9295285259dad10722297fa6784dd0c508af8dfa'
REL=str(HERE.relative_to(ROOT))


def digest(p):
    h=sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def volume():
    d=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if d['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise RuntimeError('wrong volume')


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    volume();assert not (HERE/'final-receipt.json').exists()
    assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
    prior=json.loads((PRIOR/'final-receipt.json').read_text());assert len(prior['files'])==4753
    for rec in prior['files']:
        p=ROOT/rec['path'];assert not p.is_symlink() and p.stat().st_size==rec['bytes'] and digest(p)==rec['sha256'],rec['path']
    release=json.loads((HERE/'release-receipt.json').read_text());archive=ROOT/release['archive']
    assert digest(archive)==release['archive_sha256'] and archive.stat().st_size==release['archive_bytes']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==len(release['files'])==19
        for rec in release['files']:
            assert digest(TOOL/rec['path'])==rec['sha256']
            assert sha256(z.read('fx3-recovery-adapter/'+rec['path'])).hexdigest()==rec['sha256']
    reports={}
    for kind,want,status,test in [('adapter',13,'PASS_OFFLINE_FX3_IMAGE_ADAPTATION','test_adapter.py'),('capture',14,'PASS_LOCAL_BOUNDED_CAPTURE','test_capture.py')]:
        d=json.loads((HERE/'runs'/f'{kind}-tests-final/test-receipt/results.json').read_text())
        assert d['tests_run']==want and d['status']==status and d['failures']==d['errors']==d['new_camera_or_USB_operations']==0
        assert digest(TOOL/'tests'/test)==d['test_sha256']
        for path,h in d['source_sha256'].items():assert digest(TOOL/path)==h
        reports[kind]=d
    worker=json.loads((HERE/'runs/worker-tests-final/test-receipt/results.json').read_text())
    linked=json.loads((HERE/'runs/link-tests-final/test-receipt/results.json').read_text())
    for d,want,status,test in [(worker,11,'PASS_COMPILED_WORKER_SYSCALL_FIXTURE','test_worker.py'),(linked,9,'PASS_STATIC_ELF_AND_ARM64_GUEST','test_elflink.py')]:
        assert d['tests_run']==want and d['status']==status and d['failures']==d['errors']==d['new_camera_operations']==0
        assert digest(TOOL/'tests'/test)==d['test_source_sha256']
        assert d['python_source_sha256']==reports['adapter']['source_sha256']==reports['capture']['source_sha256']
        for path,h in d['python_source_sha256'].items():assert digest(TOOL/path)==h
        assert digest(TOOL/'native/fx3_p1_reader.c')==d['worker_source_sha256']
    assert not worker['AArch64_machine_code_executed'] and not linked['real_Linux_or_Sony_kernel_executed']
    assert digest(TOOL/'native/entry.S')==linked['entry_source_sha256']
    assert digest(TOOL/'tests/test_worker.py')==linked['kernel_fixture_source_sha256']
    assert len(linked['guests'])==11 and all(g['AArch64_machine_code_executed'] and not g['real_Linux_or_Sony_kernel_executed'] for g in linked['guests'])
    successes=[g for g in linked['guests'] if g['worker_exitcode']==0]
    assert len(successes)==3 and sum(len(g['source_reads']) for g in successes)==383
    elf=HERE/'runs/link-tests-final/built/worker.elf'
    assert elf.stat().st_size==20480 and digest(elf)==linked['linked_ELF_sha256']=='c3a7b81d95d1d537d1f97bdab9eb0117f55bdeaee9b232d1f561d3d58040e2fd'
    assert digest(HERE/'runs/link-tests-final/reproducible/worker.elf')==digest(elf)
    assert digest(HERE/'runs/link-tests-final/ARM64-assembled/source.p1')==worker['synthetic_source_sha256']==digest(HERE/'runs/link-tests-final/ARM64-restored/restored.p1')
    for v,h in reports['adapter']['original_references_unchanged'].items():
        assert digest(ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine'/v/'nflasha1')==h
        assert digest(HERE/'runs/adapter-tests-final'/('restored-'+v)/'restored.p1')==h
    launch=json.loads((HERE/'launch-route-review.json').read_text());terminal=json.loads((HERE/'terminal-route-review.json').read_text())
    for row in launch['sources']:assert digest(Path(row['path']))==row['sha256']
    assert not launch['findings']['arbitrary_RAM_path_process_launch_proven'] and not terminal['real_USB_terminal_endpoint_or_prompt_observed']
    assert terminal['enabled_branch_plugin_command00F1']['original_hex']=='20008052c0035fd6'
    canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    new=deepcopy(old);now=datetime.now(timezone.utc).isoformat();new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Implemented0.4 restricted own-object static ELF linker and explicit entry.59 relocations/47 local tests pass, own ARM64 machine code completed383 fake-kernel reads and exact inverse. Original fixed date/library and terminal ACK routes audited; no real camera launch/transport or rescue proof.'
    new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
    new['progress_audit']['basis'].extend([
        '188新增限定ELF链接器与显式_start，固定C/汇编源码、5类59处重定位和字段回算；静态ET_EXEC20,480B，R/RX/R/RW及不可执行栈，无外部导入/动态加载。未安装新链接器。',
        '9项链接/ARM64测试加原11/14/13项共47项通过；Unicorn实际执行自写机器码及SVC寄存器，三组383块完整组装→候选→精确还原，另8失败场景返回非0。内核/root/设备/时钟/FP状态为显式夹具，非Sony或真实Linux启动。',
        '原cmd_debug固定20170704时间；原fork失败会_exit(-1)，waitpid无超时；固定libJit.so分支并非任意RAM临时进程接口。社区构造函数可提前退出匹配子进程，未将正常日期效果泛化为每次必然改时。',
        '终端开关默认1但onComplete(3)可清零；NoAction响应1与libpro00.command00F1仅movw0,1/ret不能充shell启用。TERM_MODE静态头0x003d025f/0x601/0x801f下游未证；初轮空返回误判失败和修正保留，未修改固件。',
        '当前公开HEAD仍YuuLuo f124d87 /QAQ ef7db11；无新增相机/USB/root/Windows操作。真实启动/传输/同机绑定/归还/当前p1/独立救砖/HEVC仍开，全部16要求与授权/恢复优先保持。',
    ])
    new['latest_stage_evidence']['stage188_static_ELF_and_ARM64_guest']={
        'readme':REL+'/README.md','implementation':'outputs/fx3-recovery-adapter/fx3_recovery/elflink.py',
        'version':'0.4.0','release':release['archive'],'release_sha256':release['archive_sha256'],
        'link_and_guest_tests':REL+'/runs/link-tests-final/test-receipt/results.json','linked_ELF_sha256':digest(elf),
        'tests_passed':47,'relocations':59,'own_ARM64_program_guest_execution':True,'complete_guest_windows':3,
        'real_Linux_or_Sony_kernel_execution':False,'launch_route_audit':REL+'/launch-route-review.json',
        'terminal_route_audit':REL+'/terminal-route-review.json','actual_camera_launch_or_transport_proven':False,
        'current7_02_p1_identity_or_independent_rescue_proven':False,'new_camera_operations':0}
    new['next_safe_offline_actions'].append('188已链接静态Linux ELF并完成自写ARM64指令+假内核三窗口完整验证。下一项追TERM_MODE静态目标0x003d025f的实际消费端/终端数据通道与临时子进程入口，再接真实root拥有者/SERVICE身份和传输/归还。不要将ACK1当shell启用，不强改终端开关或直接日期触发；首次真实入口验证应先限定无分区读取的启动/返回。当前无设备执行/上传/认证/刷写放行。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for key in old:
        if key not in allowed:assert new[key]==old[key],key
    for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    index=ROOT/'README.md';ib=index.read_bytes();(HERE/'readme-rebased-before.md').write_bytes(ib)
    marker='## 相机与固件研究\n';entry='- [FX3恢复适配工具0.4](outputs/fx3-recovery-adapter/README.md)：静态ELF链接与ARM64假内核三窗口383块验证完成，47项本地检查通过；机身启动/传输及独立救砖未验。[188证据](<'+REL+'/README.md>)。'
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
    put('final-receipt.json',{'schema':'fx3-stage188-static-link-and-guest-v1','created_utc':now,'previous_manifest_sha256':PRIOR_SHA,
        'files':files,'member_count':len(files),'excluded':excluded,'external_immutable_release':{'path':release['archive'],'sha256':release['archive_sha256'],'bytes':release['archive_bytes']},
        'source_working_tree_mutable_not_manifest_members':True,'source_snapshot_in_verified_release_archive':True,'mutable_heads_not_manifest_members':True,
        'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),'tests_passed':47,
        'own_ARM64_guest_execution':True,'real_Linux_or_Sony_kernel_execution':False,'new_camera_or_USB_operations':0,
        'native_goal_manager_untouched':True,'goal_complete':False,'persistent_write_release':False})
    print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(files),'tests_passed':47,'archive_sha256':release['archive_sha256'],'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
