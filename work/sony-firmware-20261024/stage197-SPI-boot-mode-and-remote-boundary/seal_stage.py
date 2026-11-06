"""Seal stage197 source-only findings and update existing research indexes."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
import json, os, plistlib, re, stat, subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
PRIOR = BASE/'stage196-early-FAT-and-boot-selection'
HOST = BASE/'stage195-root-host-validation-plan'
REL = str(HERE.relative_to(ROOT))
PRIOR_SHA = '3f647cecd0aca8219be832a82f63ab8137c283e2597183ac3e8c00c1d20535f3'
SRC = BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
SRC_SHA = '4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
HOST_SHA = '00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'

def digest(p):
    return sha256(p.read_bytes()).hexdigest()

def put(n,v):
    with (HERE/n).open('x') as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
        f.write('\n')

def volume():
    v = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

volume()
assert not (HERE/'final-receipt.json').exists()
assert digest(PRIOR/'final-receipt.json') == PRIOR_SHA
prior = json.loads((PRIOR/'final-receipt.json').read_text())
for e in prior['files']:
    p = ROOT/e['path']
    assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size == e['bytes'] and digest(p) == e['sha256'], p
assert len(prior['files']) == 36
assert digest(SRC) == SRC_SHA
assert digest(HOST/'approval-bundle.json') == HOST_SHA
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')

slices = json.loads((HERE/'source-slices.json').read_text())
raw = json.loads((HERE/'raw-source-verification.json').read_text())
cfg = json.loads((HERE/'spi-state-cfg.json').read_text())
assert raw['SPI_state_CFG_raw_encoding_matches'] and cfg['instructions'] == cfg['reachable_instructions'] == 679
assert len(raw['exact_BL_targets']) == 10 and len(raw['raw_words_checked']) == 13
assert slices['sha256'] == raw['sha256'] == SRC_SHA
assert not raw['original_or_guest_execution'] and raw['root_or_device_operations'] == 0
all_slices = slices['ranges'] + raw['additional_source_ranges']
assert len(all_slices) == 10
data = SRC.read_bytes()
for e in all_slices:
    a, z = int(e['start'],16)-0xfe049000, int(e['end_exclusive'],16)-0xfe049000
    assert z-a == e['bytes'] and sha256(data[a:z]).hexdigest() == e['sha256']
for link in re.findall(r'\]\(([^)]+)\)', (HERE/'README.md').read_text()):
    if '://' not in link:
        assert (HERE/link.strip('<>')).resolve().exists(), link

canonical = BASE/'GOAL_STATUS.json'
before = (HERE/'goal-status-before.json').read_bytes()
assert canonical.read_bytes() == before == (PRIOR/'goal-status-after.json').read_bytes()
old = json.loads(before)
assert len(old['requirements']) == 16
assert not old['prepared_root_host_trial']['explicitly_authorized']
native = json.loads((HERE/'native-goal-observed.json').read_text())
assert native['goal']['status'] == 'active'
now = datetime.now(timezone.utc).isoformat()
put('implementation-review.json', {
    'status': 'SPI_MODE_INPUT_TRACED_REMOTE_RECOVERY_NOT_PROVEN',
    'new_findings': [
        'original command1 SPI payload prefix+0x30 flows through bootdata import to global0xfe0615d4; getter reads same location',
        'COMMON Copy BM/BF can copy getter to context+0x1b4, but flags0x8000 preserves conditional reachability',
        'full0xfe054c88 local CFG679instructions with post-RET tail blocks; observed top-level behavior concerns PWD standby/backup exchange',
        'receive routine clears caller counter on entry;0xc0 initialization cannot be promoted to a proven receive bound'],
    'source_bound_verification': {'raw_CFG_matches': True, 'BL_targets': 10, 'raw_instruction_fields': 13, 'source_slices': 10},
    'limits': [
        'ordinary BL returns assumed for local CFG; no guarantee of callee return or exhaustive whole-boot execution',
        'aligned BL scan includes data and cannot prove absence of indirect callers or aliases',
        'SPI remote-controller identity and firmware, trigger conditions and p1/p3 choice remain unresolved',
        'no independent cold-boot restoration, actual current p1 backup or MAIN HD HEVC recording proof',
        'A7CII participant video-mode workaround is not a verified FX3 recovery interface'],
    'initial_window_correction': raw['initial_underbounded_window'],
    'pending_root01': 'same195 bundle; no explicit answer, no fixed job, no repeated question or administrator launch',
    'original_or_guest_execution': False, 'root_or_device_operations': 0,
    'goal_complete': False, 'persistent_write_release': False})
put('verification-receipt.json', {
    'status': 'PASS_SOURCE_BOUND_STATIC_SPI_REVIEW', 'created_utc': now,
    'previous_manifest_sha256': PRIOR_SHA, 'previous_manifest_members_reverified': 36,
    'NOR_sha256': SRC_SHA, 'SPI_state_instructions': 679, 'independent_raw_CFG_matches': True,
    'BL_targets_checked': 10, 'raw_fields_checked': 13, 'selected_original_slices': 10,
    'runtime_or_guest_tests': 0, 'root_or_device_operations': 0,
    'host01_bundle_sha256_unchanged': HOST_SHA, 'new_approval_granted': False,
    'source_unchanged': True, 'native_goal_observed': 'active'})

new = deepcopy(old)
new['updated_utc'] = now
new['latest_stage'] = HERE.name
new['research_activity'] = 'Static NOR SPI boot-mode provenance: command1 payload+0x30 imported into0xfe0615d4, same getter, conditional COMMON context copy. Complete679instruction PWD state CFG verified by independent A64 branch decoding; post-RET tails included. No independent p1/p3 restoration or external interface proved. Source unchanged; no original/guest/device/root operation.195 host01 still awaiting specific answer.'
new['goal_manager_status'] = new['goal_manager_status_last_observed'] = 'active'
new['native_goal_state_not_modified'] = True
new['current_native_goal_observation'] = {'receipt': REL+'/native-goal-observed.json', 'observed_utc': native['observed_utc'],
    'status': 'active', 'source': 'native get_goal read only', 'device_authorization_expanded': False}
new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
new['progress_audit']['classification'] = 'progress'
new['progress_audit']['basis'].append('197补齐原NOR SPI模式输入链：命令1前缀+0x30→导入→同一全局FE0615D4/getter，Copy BM/BF仍条件执行。完整PWD函数679指令及RET后尾块，独立编码图一致；10调用/13字段/10切片核对。长度初值不充接收上限。更新环境远端与p1/p3仍未证，195待答；无guest/root/设备，16要求与全部授权不变。')
evidence = {'readme': REL+'/README.md', 'verification': REL+'/verification-receipt.json',
    'raw_source': REL+'/raw-source-verification.json', 'CFG': REL+'/spi-state-cfg.json',
    'scope': REL+'/implementation-review.json', 'web_review': REL+'/web-source-review.json',
    'original_or_guest_execution': False, 'root_or_device_operations': 0}
new['latest_stage_evidence']['stage197_SPI_mode_input_and_remote_boundary'] = evidence
new['recovery_SPI_mode_input_provenance'] = {**evidence, 'mode_input_local_dataflow_located': True,
    'remote_controller_identity_proven': False, 'p1_or_p3_selection_proven': False,
    'independent_restore_proven': False}
new['next_safe_offline_actions'] = [
    '195 root01精确问题仍待答，保持原bundle/未授权/固定作业未创建；不把继续解释为批准、不重复询问。明确批准后才新开执行阶段，严格HOST_ONLY范围。',
    '不再把C88 PWD备份/待机交换当独立更新器。按已核对SPI命令1模式输入，分开定位发送端、早期NOR与AP侧p1/p3实际选择；COMMON flags0x8000保留条件路径。',
    '如使用旧2.04/2.05 p1，只作历史结构参考并明确版本，不能代当前7.02同机备份；实际逆写、独立冷启动恢复及MAIN HD HEVC等16项验收继续保留。']
for k in ('authorization','requirements','prepared_first_device_trial','research_priority',
          'current_native_owner_channel_candidate','prepared_root_host_trial'):
    assert new[k] == old[k], k
assert not new['goal_complete'] and not new['persistent_write_release']
after = (json.dumps(new, ensure_ascii=False, indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:
    f.write(after)
index = ROOT/'README.md'
ib = index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:
    f.write(ib)
marker = '## 相机与固件研究\n'
entry = '- [2026-10-29 FX3 SPI启动模式来源与远端边界](<'+REL+'/README.md>)：命令1前缀+0x30到模式全局已连通，679指令PWD控制流经独立编码复核；真实p1/p3选择和独立恢复仍未证；195待答，无root/设备/guest动作。'
text = ib.decode()
assert text.count(marker) == 1 and entry not in text
ia = text.replace(marker, marker+'\n'+entry+'\n', 1).encode()
with (HERE/'readme-after.md').open('xb') as f:
    f.write(ia)
volume()
assert canonical.read_bytes() == before and index.read_bytes() == ib, 'concurrent CAS change'
for dest, content, name in ((canonical, after, '.goal.tmp'), (index, ia, '.index.tmp')):
    p = HERE/name
    with p.open('xb') as f:
        f.write(content); f.flush(); os.fsync(f.fileno())
    os.replace(p, dest)
members = []
for p in sorted(HERE.rglob('*')):
    if p.is_file() and not p.is_symlink():
        members.append({'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)})
put('final-receipt.json', {
    'schema': 'fx3-stage197-SPI-mode-input-v1', 'created_utc': now,
    'previous_manifest_sha256': PRIOR_SHA, 'previous_manifest_members_reverified': 36,
    'files': members, 'member_count': len(members), 'mutable_heads_not_manifest_members': True,
    'goal_before_sha256': sha256(before).hexdigest(), 'goal_after_sha256': sha256(after).hexdigest(),
    'host01_bundle_sha256_unchanged': HOST_SHA, 'new_approval_granted': False,
    'original_or_guest_execution': False, 'root_or_device_operations': 0,
    'native_goal_observed': 'active', 'native_goal_status_changed_by_assistant': False,
    'goal_complete': False, 'persistent_write_release': False})
print(json.dumps({'sealed_manifest_sha256': digest(HERE/'final-receipt.json'),
    'members': len(members), 'requirements_unchanged': 16, 'all_authorizations_unchanged': True,
    'root_or_device_operations': 0, 'goal_complete': False}))
