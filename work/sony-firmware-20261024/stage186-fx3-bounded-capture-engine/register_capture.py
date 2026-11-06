"""Seal local implementation evidence; preserve every device authority boundary."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, os, plistlib, subprocess, zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
TOOL = ROOT/'outputs/fx3-recovery-adapter'
PRIOR = BASE/'stage185-fx3-offline-recovery-adapter'
PRIOR_SHA = '2a56badd87fc5bf603b9a5094efcead498344ec4735b9b0c7c16712547d7f482'
REL = str(HERE.relative_to(ROOT))


def digest(path):
    value = sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): value.update(chunk)
    return value.hexdigest()


def volume():
    data = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if data['VolumeUUID'] != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B': raise RuntimeError('wrong volume')


def put(name, value):
    with (HERE/name).open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')


def main():
    volume(); assert not (HERE/'final-receipt.json').exists()
    assert digest(PRIOR/'final-receipt.json') == PRIOR_SHA
    prior = json.loads((PRIOR/'final-receipt.json').read_text())
    assert len(prior['files']) == 53
    for row in prior['files']:
        p = ROOT/row['path']; assert not p.is_symlink()
        assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256'], row['path']
    release = json.loads((HERE/'release-receipt.json').read_text())
    archive = ROOT/release['archive']
    assert digest(archive) == release['archive_sha256'] and archive.stat().st_size == release['archive_bytes']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == len(release['files']) == 12
        for row in release['files']:
            p = TOOL/row['path']; assert digest(p) == row['sha256']
            assert sha256(z.read('fx3-recovery-adapter/'+row['path'])).hexdigest() == row['sha256']
    tests = {}
    for kind,want,status,testfile in [('capture',14,'PASS_LOCAL_BOUNDED_CAPTURE','test_capture.py'),
                                     ('adapter',13,'PASS_OFFLINE_FX3_IMAGE_ADAPTATION','test_adapter.py')]:
        result = json.loads((HERE/'runs'/f'{kind}-tests-final/test-receipt/results.json').read_text())
        assert result['tests_run'] == want and result['status'] == status
        assert result['failures'] == result['errors'] == result['new_camera_or_USB_operations'] == 0
        for path,want_sha in result['source_sha256'].items(): assert digest(TOOL/path) == want_sha, path
        assert digest(TOOL/'tests'/testfile) == result['test_sha256']
        tests[kind] = result
    assert tests['capture']['source_sha256'] == tests['adapter']['source_sha256']
    original = ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine'
    for version,want in tests['adapter']['original_references_unchanged'].items():
        assert digest(original/version/'nflasha1') == want
        assert digest(HERE/'runs/adapter-tests-final'/('restored-'+version)/'restored.p1') == want
    local = HERE/'runs/capture-tests-final'
    assert digest(local/'complete/source.p1') == tests['capture']['synthetic_fixture_sha256']
    assert digest(local/'capture-restored/restored.p1') == tests['capture']['synthetic_fixture_sha256']
    canonical = BASE/'GOAL_STATUS.json'; before = (HERE/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR/'goal-status-after.json').read_bytes()
    old = json.loads(before); assert len(old['requirements']) == 16
    assert not old['goal_complete'] and not old['persistent_write_release']
    new = deepcopy(old); now = datetime.now(timezone.utc).isoformat()
    new['updated_utc'] = now; new['latest_stage'] = HERE.name
    new['research_activity'] = 'Implemented0.2 fixed-range capture engine and local O_RDONLY provider:383 chunks,3 hash-linked windows,durable journal,source-close admission and independent readback.27 local tests pass; no camera provider or physical recovery proof.'
    new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '186新增capture.py、capture-local/verify-capture；383固定块和3窗口、随机请求关联、逐块SHA/CRC、窗口链、来源前后全SHA及关闭后重新组装回读。只实现本地普通文件提供者，不把内部合同称为真实相机后端。',
        '14项读取故障测试加13项原适配回归通过；真实子进程阻塞期间不关闭/重试，未知调用保留提供者；未执行Sony代码，无新增USB/相机/管理员/Windows操作。',
        '社区工作器删除/etc/ld.so.preload早于tmpfs/请求检查；不能用分区O_RDONLY掩盖整体加载与清理的持久副作用。未导入或运行其A7CII节点/认证/工作器。',
        '完整源用显式合成2.05补尾夹具，非7.02机身读回；原件与旧0.1包不变。原生实际采集、源身份/正常归还、写回、独立恢复和HEVC仍未验，全部16要求及已有授权保持。',
    ])
    new['latest_stage_evidence']['stage186_local_bounded_capture_engine'] = {
        'readme':REL+'/README.md','implementation':'outputs/fx3-recovery-adapter/fx3_recovery/capture.py',
        'release':release['archive'],'release_sha256':release['archive_sha256'],'version':'0.2.0',
        'capture_verification':REL+'/runs/capture-tests-final/test-receipt/results.json',
        'adapter_regression':REL+'/runs/adapter-tests-final/test-receipt/results.json',
        'tests_passed':27,'synthetic_full_fixture_not_camera_readback':True,
        'actual_camera_provider_implemented':False,'current7_02_p1_identity_verified':False,
        'hardware_recovery_verified':False,'new_camera_operations':0,
    }
    new['next_safe_offline_actions'].append('186已实现主机定长采集合同与本地普通文件后端。后续补FX3真实来源/受限读取提供者和归还路径；首次真实采集采用另外评审的来源与一致性方案，不要求预先知道当前p1全SHA。不得启用社区/etc/ld.so.preload加载路线或复用已耗05；当前授权无认证/文件/上传/刷写。')
    allowed = {'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for key in old:
        if key not in allowed: assert old[key] == new[key], key
    for key in old['latest_stage_evidence']: assert old['latest_stage_evidence'][key] == new['latest_stage_evidence'][key]
    encoded = (json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    (HERE/'goal-status-after.json').write_bytes(encoded)
    index = ROOT/'README.md'; index_before = index.read_bytes()
    (HERE/'readme-rebased-before.md').write_bytes(index_before)
    marker = '## 相机与固件研究\n'
    entry = '- [FX3恢复适配工具0.2](outputs/fx3-recovery-adapter/README.md)：新增定长读取／日志／逐块校验和本地后端，27项本地检查通过；真实机身采集、写回及独立救砖未验。[186证据](<'+REL+'/README.md>)。'
    text = index_before.decode(); assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    (HERE/'readme-after.md').write_bytes(index_after)
    volume(); assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'CAS concurrent change'
    for path,data,name in [(canonical,encoded,'.goal.tmp'),(index,index_after,'.index.tmp')]:
        temp = HERE/name
        with temp.open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(temp,path)
    files = []; excluded = []
    for p in sorted(HERE.rglob('*')):
        if p.is_symlink():
            excluded.append({'path':str(p.relative_to(ROOT)),'reason':'adversarial symlink fixture not followed'}); continue
        if p.is_file(): files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
    put('final-receipt.json', {'schema':'fx3-stage186-local-bounded-capture-v1','created_utc':now,
        'previous_manifest_sha256':PRIOR_SHA,'member_count':len(files),'files':files,'excluded':excluded,
        'external_immutable_release':{'path':release['archive'],'sha256':release['archive_sha256'],'bytes':release['archive_bytes']},
        'source_working_tree_mutable_not_manifest_members':True,'source_snapshot_in_verified_release_archive':True,
        'mutable_heads_not_manifest_members':True,'goal_before_sha256':sha256(before).hexdigest(),
        'goal_after_sha256':sha256(encoded).hexdigest(),'tests_passed':27,'new_camera_or_USB_operations':0,
        'native_goal_manager_untouched':True,'goal_complete':False,'persistent_write_release':False})
    print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(files),
                     'tests_passed':27,'archive_sha256':release['archive_sha256'],'goal_complete':False,'persistent_write_release':False}))


if __name__ == '__main__': main()
