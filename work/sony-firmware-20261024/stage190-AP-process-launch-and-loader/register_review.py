"""Seal this offline review and preserve every current physical requirement."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
import json, os, plistlib, subprocess
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = str(HERE.relative_to(ROOT))
PRIOR = BASE / 'stage189-TERM_MODE-consumer'
PRIOR_SHA = '315336e814eb0928e20a6c115f243678986fc52737ee6736e6cf25f23df06143'
def digest(p):
    h = sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()
def volume():
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if info['VolumeUUID'] != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('wrong volume')
def put(name, data):
    with (HERE / name).open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')
volume()
assert not (HERE / 'final-receipt.json').exists()
assert digest(PRIOR / 'final-receipt.json') == PRIOR_SHA
prior = json.loads((PRIOR / 'final-receipt.json').read_text())
for m in prior['files']:
    p = ROOT / m['path']
    assert not p.is_symlink() and p.stat().st_size == m['bytes'] and digest(p) == m['sha256']
v = json.loads((HERE / 'verification-receipt.json').read_text())
assert v['status'] == 'PASS_ORIGINAL_LOADER_REVIEW_AND_INVENTORY_COVERAGE'
assert v['original_loader_consumer_cases'] == 5 and v['new_camera_operations'] == 0
for m in v['files']:
    p = HERE / m['path']; assert p.stat().st_size == m['bytes'] and digest(p) == m['sha256']
observed = json.loads((HERE / 'native-goal-observed.json').read_text())
assert observed['goal']['status'] == 'active' and observed['goal']['objective'] == '持续研究，直到可以正常刷入。'
canonical = BASE / 'GOAL_STATUS.json'
before = (HERE / 'goal-status-before.json').read_bytes()
assert before == canonical.read_bytes() == (PRIOR / 'goal-status-after.json').read_bytes()
old = json.loads(before); new = deepcopy(old)
assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
now = datetime.now(timezone.utc).isoformat()
new['updated_utc'] = now; new['latest_stage'] = HERE.name
new['research_activity'] = 'Reverified532 AP ELFs/29 launch candidates with full aligned text coverage,103 direct branch candidates. Root BusyBox uses glibc2.25; etc declared on writable nflasha10, tmp_wbshd declared tmpfs.5 original loader error-consumer guest cases pass with caught-error/diagnostic fixtures; real lookup/loader/boot/WBI/recovery unproven. Next priority native owner/channel integration and fixed read admission.'
new['goal_manager_status'] = new['goal_manager_status_last_observed'] = 'active'
new['native_goal_state_not_modified'] = True
new['current_native_goal_observation'] = {'receipt': REL + '/native-goal-observed.json', 'observed_utc': observed['observed_utc'],
                                       'status': 'active', 'source': 'native get_goal read only', 'device_authorization_expanded': False}
new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
new['progress_audit']['classification'] = 'progress'
new['progress_audit']['basis'].extend([
    '190补全AP启动候选盘点：532 ELF哈希、29命中、103直接分支；首版遇数据停解码的77命中保留并纠正，逐4B对齐间隙及整段字节覆盖入账。候选不是USB可达或参数可控证明。',
    '190核对原rootfs中BusyBox动态解释器和glibc2.25；fstab.ext将/etc和/var声明在可写nflasha10，init2声明/tmp_wbshd为tmpfs。preload文件不是纯RAM改动。',
    '190在Unicorn运行原ld-2.25.so的148B错误消费者，3错误/新加载/重复共5组；真实lookup、catch与诊断I/O为明确夹具。原3处调用核对，未把缺失RAM库的局部分支当真实冷启动、WBI清空或p1救砖。',
    '190形成具体实施判断：0.4 ET_EXEC不能直接preload；须补guarded ET_DYN和同进程native owner/通道/准入。保持G09等16要求、一次授权已消耗边界及恢复优先不变。',
])
new['latest_stage_evidence']['stage190_process_and_preload_error_consumer'] = {
    'readme': REL + '/README.md', 'inventory': REL + '/launch-inventory-v2.json',
    'review': REL + '/preload-recovery-review.json', 'decision': REL + '/launch-decision.json',
    'verification': REL + '/verification-receipt.json', 'original_loader_consumer_cases': 5,
    'AP_ELFs_reverified': 532, 'real_loader_boot_or_WBI_recovery_proven': False,
    'preload_pointer_file_declared_persistent': True, 'new_camera_operations': 0,
}
new['next_safe_offline_actions'] = [
    '仅主机代码/离线：把stage179/180 IOKit wire与定长请求通道接入stage178实际owner，补完整bootstrap/peer identity/总预算/阻塞UNKNOWN寿命和用户结果交付；先完成代码与真进程夹具，再形成具体单次预检。无管理员程序或相机动作。',
    '仅离线：评估精确debug子进程guard与受限ET_DYN；0.4 ET_EXEC不是preload模块。保留日期触发失败、fork失败和unbounded wait风险；/etc指针为持久文件。继续G09真实clean-boot/WBI条件和独立updater，不把原loader捕获错误消费等同于救砖。',
] + old['next_safe_offline_actions']
for key in ('authorization', 'requirements', 'prepared_first_device_trial', 'research_priority'):
    assert new[key] == old[key]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
with (HERE / 'goal-status-after.json').open('xb') as f: f.write(encoded)
index = ROOT / 'README.md'; ib = index.read_bytes()
with (HERE / 'readme-rebased-before.md').open('xb') as f: f.write(ib)
marker = '## 相机与固件研究\n'
entry = '- [2026-10-29 FX3原加载器preload失败与冷启动边界](<' + REL + '/README.md>)：补齐29个启动候选、103处直接分支；5组原错误消费检查确认局部非致命分支，/etc为持久文件，真实冷启动/WBI与救砖未验，无设备动作。'
text = ib.decode(); assert text.count(marker) == 1 and entry not in text
ia = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
with (HERE / 'readme-after.md').open('xb') as f: f.write(ia)
volume(); assert canonical.read_bytes() == before and index.read_bytes() == ib, 'CAS concurrent modification'
for dest, data, name in ((canonical, encoded, '.goal.tmp'), (index, ia, '.index.tmp')):
    p = HERE / name
    with p.open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(p, dest)
members = []
for p in sorted(HERE.rglob('*')):
    assert not p.is_symlink()
    if p.is_file(): members.append({'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)})
external = [BASE / 'stage2/extraction/read_filesystems.py', BASE / 'stage2/extraction/nflasha15.img',
            BASE / 'stage2/extraction/nflasha7.img', BASE / 'stage2/extraction/files/nflasha7/lib/ld-2.25.so']
put('final-receipt.json', {'schema': 'fx3-stage190-loader-error-consumer-and-process-inventory-v1', 'created_utc': now,
    'previous_manifest_sha256': PRIOR_SHA, 'previous_manifest_members_reverified': len(prior['files']),
    'files': members, 'member_count': len(members),
    'external_inputs': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in external],
    'mutable_heads_not_manifest_members': True,
    'goal_before_sha256': sha256(before).hexdigest(), 'goal_after_sha256': sha256(encoded).hexdigest(),
    'original_loader_consumer_cases': 5, 'real_filesystem_kernel_loader_or_camera_operations': 0,
    'native_goal_observed': 'active', 'native_goal_status_changed_by_assistant': False,
    'goal_complete': False, 'persistent_write_release': False})
print(json.dumps({'manifest_sha256': digest(HERE / 'final-receipt.json'), 'members': len(members),
                  'previous_members_reverified': len(prior['files']), 'original_loader_cases': 5,
                  'native_goal': 'active', 'new_camera_operations': 0, 'goal_complete': False}))
