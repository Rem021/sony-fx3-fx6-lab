#!/usr/bin/env python3
"""Seal original USB-dispatch and Mac ownership evidence; no camera operations."""
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
PRIOR = BASE / 'stage137-service-exit-and-host-cleanup'
PRIOR_SHA = '94746ba8efe62c6b3b195ea93ea95a5359cbc483b8ac095a32e9eda78f42ecec'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


def put(name, value):
    with (HERE / name).open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    assert not (HERE / 'final-receipt.json').exists()
    assert sha256((HELPER / 'final-receipt.json').read_bytes()).hexdigest() == '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    helper_pin = next(x for x in json.loads((HELPER / 'final-receipt.json').read_text())['files']
                      if x['path'] == (HELPER / 'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER / 'review_and_seal.py').read_bytes()).hexdigest() == helper_pin['sha256']
    spec = importlib.util.spec_from_file_location('prior_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    previous_count = helper.check_previous()
    assert previous_count == 9
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    inputs = json.loads((HERE / 'inputs-receipt.json').read_text())
    assert len(inputs['selected_kernel_sources']) == 11
    assert len(inputs['original_modules']) == 2 and len(inputs['fixed_upstream_sources']) == 5
    for field in ('selected_kernel_sources', 'original_modules', 'fixed_upstream_sources'):
        for entry in inputs[field]:
            path = ROOT / entry['path']
            assert path.stat().st_size == entry['bytes'] and helper.digest(path) == entry['sha256']
    dispatch = json.loads((HERE / 'vendor-dispatch-review.json').read_text())
    host = json.loads((HERE / 'Mac-driver-ownership-review.json').read_text())
    assert dispatch['status'] == 'PASS_STATIC_FX3_VENDOR_HEADERS_KERNEL_DISPATCH_NOT_LIVE_SERVICE_OR_RECOVERY'
    assert host['status'] == 'PASS_STATIC_MAC_DRIVER_OWNERSHIP_NOT_DRIVER_RELEASE_OR_CAMERA_QUERY'
    assert len(dispatch['original_library_functions']) == 6
    assert len(host['libusb_source_reference']['functions']) == 5
    assert dispatch['kernel_vendor_code']['span_bytes'] == 200
    assert dispatch['configured_control_headers']['bytes'] == '4301ff37aad70000430100c855280000'
    assert dispatch['separate_forced_service_file']['path'] == '/setting/sen/smode'
    assert dispatch['separate_forced_service_file']['two_byte_marker'] == 'UU'
    assert not dispatch['separate_forced_service_file']['actual_file_existence_or_auth_modification_verified']
    assert not dispatch['consumer_boundary']['all_registration_dynamic_callbacks_queue_ownership_and_wire_completion_closed']
    assert not host['driver_library_import_load_or_device_open']
    for entry in dispatch['upstream_reference_pins']:
        assert helper.record(ROOT / entry['path']) == entry
    for library, digest in [('libInfraUsbCmn.so', '6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396'),
                            ('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')]:
        assert helper.digest(BASE / 'stage2/extraction/files/nflasha15/lib' / library) == digest
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Offline original FX3 USB setup headers/kernel event dispatch and Mac libusb driver ownership audit'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段138原镜像/内核参考重验，新增2个原模块/11个源码/5个固定上游来源，均未执行。',
        'FX3原库两组8B setup与PMCA Start/Stop逐字段相符；原usbg_sen.ko登记、完整比较及4B异步事件投递片段已定位。',
        '原消费者回调分界与不同事件类型保持分开，控制传输/排队不充cancel/join或正常模式完成。',
        '强制服务检查另读/setting/sen/smode的UU，区别/ramdsk/dev/mode的AA；未测存在、写者或冷启动。',
        'PMCA构造/reset/列表为活动操作；libusb1.0.30 Mac接管整机重枚举及重绑错误返回边界已固定，未实际加载/捕获。',
        '16项要求、既有授权/用户Mac-only约束、旧准备字段及75/117固定原型不变，无新设备操作。'])
    key = 'stage138_USB_stop_dispatch_and_Mac_ownership'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'inputs': REL + '/inputs-receipt.json',
        'vendor_dispatch': REL + '/vendor-dispatch-review.json', 'Mac_driver_ownership': REL + '/Mac-driver-ownership-review.json',
        'whole_original_library_functions': 6, 'kernel_vendor_code_bytes': 200,
        'fixed_setup_headers': 2, 'upstream_libusb_C_functions': 5,
        'source_only_no_foreign_code_or_device_execution': True,
        'actual_driver_handoff_or_camera_safe_return_proven': False, 'authorization_unchanged': True}
    new['prepared_first_device_trial']['FX3_vendor_dispatch_review'] = REL + '/vendor-dispatch-review.json'
    new['prepared_first_device_trial']['Mac_driver_ownership_review'] = REL + '/Mac-driver-ownership-review.json'
    new['prepared_first_device_trial']['active_entry_exit_and_driver_handoff_ready'] = False
    new['next_safe_offline_actions'].append(
        '阶段138后继续将原gadget cmd0/1回调登记/消息消费者接到137取消join及USB完成，形成限定单机/显式错误/未知状态/驱动复绑的首次方案。原setup匹配与异步排队不充退出；/setting/sen/smode(UU)与/ramdsk/dev/mode(AA)分开核对。PMCA普通列表会reset/查询，Mac显式detach和dispose不构成已验证配对恢复；现有缓存/Fastboot识别许可不扩大，79MB MAIN同机备份与独立救援要求继续保留。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('prepared_first_device_trial', 'latest_stage_evidence'):
        for key, value in old[section].items():
            assert new[section][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3原USB分派与Mac驱动归属](<' + REL + '/README.md>)：原库setup与内核匹配/事件投递已对应；另有UU强制模式文件，Mac接管/复绑需独立验证，实机及刷写未放行。'
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent heads changed; CAS refused'
    assert helper.pins(old) == fixed
    for target, data, name in [(canonical, encoded, '.goal-write.tmp'), (index, index_after, '.index-write.tmp')]:
        temporary = HERE / name
        with temporary.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    helper.check_previous()
    completed = {
        'status': 'PASS_STATIC_USB_DISPATCH_AND_HOST_OWNERSHIP_NOT_LIVE_RELEASE', 'created_utc': now,
        'previous_manifest_members_verified': previous_count,
        'original_modules_extracted_not_loaded': 2, 'selected_kernel_reference_sources': 11,
        'fixed_upstream_sources': 5, 'whole_original_library_functions': 6,
        'kernel_vendor_static_code_bytes': 200, 'libusb_C_functions': 5,
        'new_device_or_driver_operations_or_Sony_execution': 0,
        'all16_requirements_authorization_and_user_constraints_unchanged': True,
        'old_prepared_trial_and_source_evidence_preserved': True,
        'stage75_backend_and_stage117_frontend_pins': fixed, 'canonical_equals_after': True,
        'same_agent_static_review_not_real_camera_acceptance': True,
        'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', completed)
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {
        'schema': 'fx3-stage138-USB-dispatch-Mac-ownership/1', 'created_utc': now,
        'volume_uuid': helper.UUID, 'files': files, 'member_count': len(files),
        'previous_manifest_sha256': PRIOR_SHA, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
                            'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'operations': completed})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'), 'members': len(files),
                      'canonical_sha256': helper.digest(canonical), 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
