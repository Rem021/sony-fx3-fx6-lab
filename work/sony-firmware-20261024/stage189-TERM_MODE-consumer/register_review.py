"""Register completed offline evidence, preserving every device/flash gate."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, os, plistlib, subprocess
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = str(HERE.relative_to(ROOT))
PRIOR = BASE / 'stage188-static-ELF-link-and-explicit-entry'
PRIOR_SHA = 'aa3c1606b9752ed2f6d6595f50e7626383f7bbf434609322440fa38f225dd6c5'
def digest(p):
    h = sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()
def volume():
    d = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if d['VolumeUUID'] != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('wrong volume')
def put(name, value):
    with (HERE / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')

volume()
assert not (HERE / 'final-receipt.json').exists()
assert digest(PRIOR / 'final-receipt.json') == PRIOR_SHA
v = json.loads((HERE / 'verification-receipt.json').read_text())
assert v['status'] == 'PASS_SOURCE_BINDINGS_AND_OFFLINE_RECEIPTS'
assert v['original_guest_cases'] == 30 and v['PLT_symbols_independently_reconciled'] == 14
assert v['new_camera_operations'] == 0 and v['tool_0_4_source_and_archive_unchanged']
for r in v['files']:
    assert digest(HERE / r['path']) == r['sha256'] and (HERE / r['path']).stat().st_size == r['bytes']
native = json.loads((HERE / 'native-goal-observed.json').read_text())
assert native['goal']['status'] == 'active'
assert native['goal']['objective'] == '持续研究，直到可以正常刷入。'
assert json.loads((HERE / 'RESUMED.json').read_text())

canonical = BASE / 'GOAL_STATUS.json'
before = (HERE / 'goal-status-before.json').read_bytes()
assert before == canonical.read_bytes() == (PRIOR / 'goal-status-after.json').read_bytes()
old = json.loads(before)
assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
new = deepcopy(old)
now = datetime.now(timezone.utc).isoformat()
new['updated_utc'] = now
new['latest_stage'] = HERE.name
new['research_activity'] = 'Original FX3 AP TERM_MODE dispatch rejected before IPC in24 bounded ARM64 cases;2 controls reached distinct stopped boundaries.4 original fixed-loader prefixes show writable nflasha6 mount before upload/load.797 AP regular files scanned; PMCA suppresses TERM_MODE errors.0.4 unchanged; no real camera/loader/recovery proof.'
new['native_goal_state_not_modified'] = True
new['goal_manager_status'] = 'active'
new['goal_manager_status_last_observed'] = 'active'
new['current_native_goal_observation'] = {'receipt': REL + '/native-goal-observed.json',
                                       'observed_utc': native['observed_utc'], 'status': 'active',
                                       'source': 'read native get_goal; user renewed persistent objective',
                                       'previous_project_blocked_label_is_historical': True,
                                       'device_authorization_expanded': False}
new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
new['progress_audit']['classification'] = 'progress'
new['progress_audit']['basis'].extend([
    '189执行原TransactionStart：24组TERM_MODE在IPC前返回0x80，原表801f分类分支不变；2组对照停在OSAL/testcmd调用前。未把原ProductInfo ACK1或客户端忽略异常当终端成功。',
    '189执行原set_file/包装/选择mount前缀共4组，捕获source=/dev/nflasha6,target=/tmp/jiritsu,vfat,flags=0xc0ed0490且无MS_RDONLY；未执行mount或伪造返回。固定路径不是已证纯RAM入口。',
    '189核对797个AP普通文件和14个PLT身份；完整固定FIFO路径仅libsencore命中，尚无接收端证明。工具0.4源码及ZIP保持不变；历史47项不计作新跑。',
    '最新原生持续目标已读回active；旧STOPPED为助手误读且有RESUMED回执，不代表当前暂停。所有设备与刷写限制保留。',
])
new['latest_stage_evidence']['stage189_TERM_MODE_and_fixed_loader'] = {
    'readme': REL + '/README.md', 'verification': REL + '/verification-receipt.json',
    'dispatch': REL + '/dispatch-guest-results.json', 'fixed_loader_prefix': REL + '/fixed-loader-prefix-results.json',
    'fifo_inventory': REL + '/fifo-route-review.json', 'public_client': REL + '/public-client-review.json',
    'original_ARM64_bounded_cases': 30, 'real_kernel_loader_or_camera_test': False,
    'TERM_MODE_as_ready_shell_route': False, 'fixed_libJit_path_as_proven_RAM_route': False,
    'new_camera_operations': 0,
}
action = '仅离线：绕开已证拒绝的TERM_MODE和先挂载nflasha6的普通固定libJit路径，继续追独立进程/RAM装载的真实接收端、初始化、退出/等待和失败副作用；不修改命令表、不执行mount/上传/认证/相机调用。保留当前p1原件和MAIN故障态恢复缺口。'
new['next_safe_offline_actions'] = [action] + old['next_safe_offline_actions']
for key in ('authorization', 'requirements', 'prepared_first_device_trial', 'research_priority'):
    assert new[key] == old[key]
assert new['goal_complete'] is False and new['persistent_write_release'] is False
encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
with (HERE / 'goal-status-after.json').open('xb') as f:
    f.write(encoded)

index = ROOT / 'README.md'
ib = index.read_bytes()
with (HERE / 'readme-rebased-before.md').open('xb') as f:
    f.write(ib)
marker = '## 相机与固件研究\n'
entry = '- [2026-10-29 FX3终端分派与固定库入口](<' + REL + '/README.md>)：30组原ARM64局部检查确认TERM_MODE拒绝及固定libJit的可写闪存挂载前缀；0.4工具保留，真实备份/救砖未验，无设备动作，持续目标active。'
text = ib.decode()
assert text.count(marker) == 1 and entry not in text
ia = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
with (HERE / 'readme-after.md').open('xb') as f:
    f.write(ia)

volume()
assert canonical.read_bytes() == before and index.read_bytes() == ib, 'CAS concurrent change'
for path, data, name in ((canonical, encoded, '.goal.tmp'), (index, ia, '.index.tmp')):
    temp = HERE / name
    with temp.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)
members = []
for p in sorted(HERE.rglob('*')):
    assert not p.is_symlink()
    if p.is_file():
        members.append({'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)})
external = [BASE / 'stage2/extraction/read_filesystems.py', BASE / 'stage2/extraction/nflasha15.img',
            Path(json.loads((HERE / 'dispatch-guest-results.json').read_text())['source']),
            Path(json.loads((HERE / 'fixed-loader-prefix-results.json').read_text())['source']),
            ROOT / 'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip']
put('final-receipt.json', {
    'schema': 'fx3-stage189-original-dispatch-and-loader-prefix-v1', 'created_utc': now,
    'previous_manifest_sha256': PRIOR_SHA, 'previous_manifest_reverified_members': False,
    'files': members, 'member_count': len(members),
    'external_inputs': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in external],
    'mutable_heads_not_manifest_members': True,
    'goal_before_sha256': sha256(before).hexdigest(), 'goal_after_sha256': sha256(encoded).hexdigest(),
    'original_ARM64_bounded_cases': 30, 'real_kernel_loader_USB_or_camera_operations': 0,
    'native_goal_observed': 'active', 'native_goal_status_changed_by_assistant': False,
    'goal_complete': False, 'persistent_write_release': False,
})
print(json.dumps({'manifest_sha256': digest(HERE / 'final-receipt.json'), 'members': len(members),
                  'original_guest_cases': 30, 'native_goal': 'active', 'new_camera_operations': 0,
                  'goal_complete': False, 'persistent_write_release': False}))
