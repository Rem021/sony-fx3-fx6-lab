"""Register the implemented offline adapter; no device authority is changed."""
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,os,plistlib,subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage184-community-recovery-and-standalone-service'
PRIOR_SHA='a0eac1d23620dd65d76005d89f7a34d8e03f5363ae056fa8681d41ef04c4d8af'


def digest(p):
    d=sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):d.update(b)
    return d.hexdigest()


def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if v['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise RuntimeError('wrong volume')


def put(name,obj):
    with (HERE/name).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    volume();assert not (HERE/'final-receipt.json').exists()
    f=PRIOR/'final-receipt.json';assert digest(f)==PRIOR_SHA
    previous=json.loads(f.read_text())
    for rec in previous['files']:
        p=ROOT/rec['path'];assert p.stat().st_size==rec['bytes'] and digest(p)==rec['sha256'],rec['path']
    assert len(previous['files'])==100
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md';before=(HERE/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    result=json.loads((HERE/'runs/tests/test-receipt/results.json').read_text())
    assert result['status']=='PASS_OFFLINE_FX3_IMAGE_ADAPTATION' and result['tests_run']==13 and not result['failures'] and not result['errors']
    tool=ROOT/'outputs/fx3-recovery-adapter'
    for path,want in result['source_sha256'].items():assert digest(tool/path)==want
    assert digest(tool/'tests/test_adapter.py')==result['test_sha256']
    release=json.loads((HERE/'release-receipt.json').read_text());archive=ROOT/release['archive']
    assert digest(archive)==release['archive_sha256'] and archive.stat().st_size==release['archive_bytes']
    for rec in release['files']:
        p=tool/rec['path'];assert digest(p)==rec['sha256'] and p.stat().st_size==rec['bytes']
    for v,want in result['original_references_unchanged'].items():
        p=ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine'/v/'nflasha1'
        assert digest(p)==want
        bundle=HERE/('runs/tests/bundle-'+v)
        restored=HERE/('runs/tests/restored-'+v)/'restored.p1'
        assert digest(bundle/'source.p1')==want==digest(restored)
    now=datetime.now(timezone.utc).isoformat();new=deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Implemented FX3 offline recovery adapter0.1: exact-library P1 construction, bounded parsing, original backup and exact inverse; two genuine legacy references passed13 tests. Current7.02 body, transport, DAT/HEVC and physical restore remain unverified.'
    new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification']
    new['progress_audit']['classification']='progress'
    new['progress_audit']['basis'].extend([
        '185按用户明确要求实现FX3适配代码，不再仅研究报告；新交付outputs/fx3-recovery-adapter，Mac命令行inspect/build/verify/diagnose/rollback，无设备后端。',
        'FX3旧SD库绑定完整60584B/SHA，原版本/签名函数9fd4/abf0取代A7CII a0cc/ace8；共享corecommon绑定完整72864B/SHA及d208/d27c，模型/地区谓词字节保留。',
        '真实官方2.04/2.05 p1均完成候选生成、重解析、范围外不变与原件逐字节还原；13项故障/状态/源保护及CLI检查通过，未执行Sony代码。',
        '首轮原VFAT长名不支持而拒绝的记录保留；补严格长名验证后通过，不以跳过原件校验解决。完整快照路径仅人工补尾fixture，不充当前7.02读回。',
        '源码ZIP只含实现/说明/测试，原件及候选留本地证据；当前机身p1身份、真实恢复后端、菜单RAM门、DAT和HEVC功能未接入，两个false及全部16要求/授权/限制保持。',
    ])
    new['latest_stage_evidence']['stage185_FX3_offline_recovery_adapter']={
        'readme':REL+'/README.md','tool_readme':'outputs/fx3-recovery-adapter/README.md',
        'implementation':'outputs/fx3-recovery-adapter/fx3_recovery/engine.py','verification':REL+'/runs/tests/test-receipt/results.json',
        'release':release['archive'],'release_sha256':release['archive_sha256'],'version':'0.1.0',
        'real_reference_images':['FX3 official2.04','FX3 official2.05'],'offline_tests':13,
        'current7_02_camera_p1_verified':False,'live_transport_or_camera_restore_proven':False,'HEVC_feature_included':False,'new_camera_operations':0,
    }
    new['next_safe_offline_actions'].append('185已实现离线FX3 p1适配和原件逆构建。下一项限定当前p1来源/库指纹与受限读取合同，核对Jiritsu/root提供者可达及认证/加载副作用；只有取得可信本机原件才扩展当前版本配置。不要复用A7CII偏移、MENU RAM门或用参考候选直接刷机；设备后端与HEVC补丁仍需实现和具体授权。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for key in old:
        if key not in allowed:assert new[key]==old[key],key
    for key,value in old['latest_stage_evidence'].items():assert new['latest_stage_evidence'][key]==value
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    index_before=index.read_bytes();(HERE/'readme-rebased-before.md').write_bytes(index_before)
    entry='- [FX3恢复适配工具0.1](outputs/fx3-recovery-adapter/README.md)：已实现本地p1检查/候选/逆还原，真实2.04/2.05原件闭环及13项检查通过；当前7.02机身和实际刷写未验。[185证据](<'+REL+'/README.md>)。'
    marker='## 相机与固件研究\n';text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'CAS concurrent change'
    for path,data,name in [(canonical,encoded,'.goal.tmp'),(index,index_after,'.index.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    files=[];excluded=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_symlink():excluded.append({'path':str(p.relative_to(ROOT)),'reason':'intentional adversarial symlink fixture; not followed'});continue
        if p.is_file():files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
    put('final-receipt.json',{'schema':'fx3-stage185-offline-adapter-v1','created_utc':now,'previous_manifest_sha256':PRIOR_SHA,
        'files':files,'member_count':len(files),'excluded':excluded,
        'external_immutable_release':{'path':release['archive'],'sha256':release['archive_sha256'],'bytes':release['archive_bytes']},
        'source_working_tree_mutable_not_manifest_members':True,'source_snapshot_in_verified_release_archive':True,
        'mutable_heads_not_manifest_members':True,'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),
        'tests':13,'new_camera_or_USB_operations':0,'native_goal_manager_untouched':True,'goal_complete':False,'persistent_write_release':False})
    print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(files),'source_archive_sha256':release['archive_sha256'],
                      'tests':13,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
