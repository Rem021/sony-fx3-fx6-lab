#!/usr/bin/env python3
"""Read back stage65 sources and receipts without replaying native code or UI."""
import base64
import datetime
import hashlib
import json
import tarfile
import prepare_handoff as h


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    h.im.volume()
    s, root = h.STAGE, h.ROOT
    assert not (s/'final-receipt.json').exists()
    prior = h.BASE/'stage64-osal-offline-link/final-receipt.json'
    assert h.im.sha(prior.read_bytes()) == '0bf042fe283fe4a56c9146bbe9eb5cd8cc750847877922cecf45d69355220b6a'
    old = load(prior)
    assert len(old['files']) == 23
    for row in old['files']:
        raw = (root/row['path']).read_bytes()
        assert len(raw) == row['bytes'] and h.im.sha(raw) == row['sha256']
    before = (s/'goal-status-before.json').read_bytes()
    assert h.im.sha(before) == '383864bbaf766fc5e5a6c5b550a1f9499d9288097c1a36991621c6c2d340ca22'
    assert before == (h.BASE/'GOAL_STATUS.json').read_bytes()
    assert before == (prior.parent/'goal-status-after.json').read_bytes()

    attempt1, attempt2 = s/'from-windows-host-attempt-1', s/'from-windows-host-attempt-2'
    assert len(list(attempt1.iterdir())) == 8 and len(list(attempt2.iterdir())) == 13
    for original in (s/'windows-cache-handoff').iterdir():
        for destination in (s/'from-windows-transfer-verification', attempt1, attempt2):
            assert original.read_bytes() == (destination/original.name).read_bytes()
    for original in attempt1.iterdir():
        assert original.read_bytes() == (attempt2/original.name).read_bytes()
    receipt = load(attempt2/'receipt-attempt2.json')
    assert receipt['compile']['exit_code'] == 0 and receipt['compile']['status'] == 'PASS'
    assert not receipt['compile']['collect_called']
    assert receipt['dry_run']['exit_code'] == 1 and receipt['dry_run']['error_id'] == 'UnauthorizedAccess'
    assert not receipt['dry_run']['script_body_started']
    assert not receipt['cached_associations']['command_dispatched']
    assert receipt['cached_associations']['attempt_count'] == 0
    assert receipt['camera_device_handles'] == receipt['camera_commands'] == 0
    assert not receipt['execution_policy_changed'] and not receipt['elevation']
    assert not receipt['software_or_driver_installation']
    assert (attempt2/'compile-attempt2.log.txt').read_text(encoding='utf-8-sig').strip() == 'COMPILE_ONLY_X64_ABI_OK'
    assert 'running scripts is disabled' in (attempt2/'dryrun-attempt2.log.txt').read_text(encoding='utf-8-sig')

    boot = load(s/'boot-context-audit.json')
    vendor = load(s/'vendor-source-runtime-crosscheck.json')
    download = load(s/'runtime-source-downloads.json')
    for report, name in ((boot, 'audit_boot_context.py'), (vendor, 'audit_vendor_source.py'),
                         (download, 'resume_runtime_sources.py')):
        assert report['source_script_sha256'] == h.im.sha((s/name).read_bytes())
    kernel = (h.BASE/'stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin').read_bytes()
    assert h.im.sha(kernel) == boot['kernel_sha256'] == vendor['kernel_sha256']
    assert len(kernel) == 6610952 and boot['header']['entry_branch_file_offset'] == '0x5b0000'
    base = int(boot['kernel_model_base'], 16)
    for instruction in boot['original_instructions']:
        offset = int(instruction['offset'], 16)
        assert kernel[offset:offset+4].hex() == instruction['bytes']
        assert base+offset == int(instruction['va'], 16)
    cases = boot['independent_native_components']
    assert [x['seed'] for x in cases] == ['0xa5', '0xc3']
    for case in cases:
        assert case['executed_pcs'] == [hex(base+x) for x in range(0x5b0188, 0x5b019c, 4)]
        assert case['native_SP'] == boot['initial_stack'] == '0xffffff8008684000'
        assert case['native_SP_EL0'] == boot['original_startup_current_context'] == '0xffffff800868c500'
        assert case['RAM_writes'] == 0 and not case['host_wrote_SP_SP_EL0_PSTATE_or_return_adapters']
        assert not case['real_boot_MMU_scheduler_task_or_OSAL_request_continuation']
    bss = boot['original_BSS_clear_operands_not_executed']
    assert int(bss['start'], 16) == base+len(kernel)
    assert int(bss['end_exclusive'], 16)-int(bss['start'], 16) == bss['bytes'] == 370796

    expected_md5 = ['YDFQucyXKvK/A5CHlRB/LA==', '9aHG28OfRwq9OzaVRo9gLw==']
    for row, expected in zip(download['files'], expected_md5):
        raw = (root/row['path']).read_bytes()
        assert len(raw) == row['bytes'] and h.im.sha(raw) == row['sha256']
        assert base64.b64encode(hashlib.md5(raw).digest()).decode() == expected
    archive = root/download['files'][0]['path']
    with tarfile.open(archive, 'r:gz') as source:
        assert len(source.getmembers()) == 43921
        assert len(vendor['source_members']) == 12
        member_text = {}
        for name, row in vendor['source_members'].items():
            info = source.getmember(row['archive_member'])
            assert info.isfile() and info.size < 200000
            raw = source.extractfile(info).read()
            assert len(raw) == row['bytes'] and h.im.sha(raw) == row['sha256']
            member_text[name] = raw.decode().splitlines()
        for excerpt in vendor['selected_excerpts']:
            for number, line in excerpt['lines']:
                assert member_text[excerpt['member']][number-1] == line
    assert vendor['source_label'] == 'FX3 7.00' and vendor['source_kernel_version'] == '4.9.337'
    assert not vendor['whole_source_build_or_7_02_exact_source_match_verified']
    abi = vendor['driver_init_ABI']
    assert abi['register_argument_is_driver_pointer_array']
    assert abi['init_callback_argument_is_driver_data_not_driver_object']
    assert abi['ops_field_offset'] == '0x38' and abi['callback_data_field_offset'] == '0x40'
    assert abi['original_callback_data_value'] == '0x0'
    for row in abi['actual_kernel_callback_prefix_not_executed']:
        offset = int(row['offset'], 16)
        assert kernel[offset:offset+4].hex() == row['bytes']
    for service in vendor['original_registration_services_not_executed']:
        pc = int(service['original_BL'], 16)
        word = int.from_bytes(kernel[pc-base:pc-base+4], 'little')
        assert word & 0xfc000000 == 0x94000000
        delta = word & 0x3ffffff
        if delta & (1 << 25):
            delta -= 1 << 26
        assert pc+delta*4 == int(service['decoded_target'], 16)
    timing = vendor['threaded_registration_correlation']
    assert timing['original_priority_immediate'] == timing['reference_config_160_minus70'] == 90
    assert timing['original_completion_timeout_jiffies'] == timing['reference_5min_times_HZ100'] == 30000
    assert not timing['real_thread_completion_scheduler_or_timeout_execution']

    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': 'Same-agent source, byte, hash, original instruction and receipt readback. Not independent physical acceptance.',
        'prior23_sealed_files_and_canonical_verified': True,
        'four_input_roundtrips_unchanged': True,
        'attempt1_eight_receipts_preserved_in_attempt2': True,
        'attempt2_received_files': 13,
        'Windows_compile_x64_ABI': 'PASS',
        'Windows_DryRun': 'POLICY_BLOCKED_BEFORE_SCRIPT_BODY',
        'original_CachedAssociations_Collect_calls': 0,
        'Windows_camera_handles_commands': 0,
        'native_startup': 'Two independent five-instruction components; not boot or resumed OSAL request',
        'original_binary_and_12_vendor_members_verified': True,
        'GPL_archives_size_SHA256_official_MD5_verified': True,
        'vendor_version_limit': 'Public source label7.00, original binary7.02; selected ABI correlation only',
        'downloaded_vendor_code_executed': False,
        'camera_operations_or_full_emulator_or_recovery_acceptance': False,
        'native_PnP_followup': 'Dispatched and observed processing in existing Windows Codex; result reviewed separately',
        'previous_goal_turn_classification': 'progress',
        'this_goal_turn_classification': 'progress',
        'goal_complete': False,
        'persistent_write_release': False,
    }
    h.im.write_json(s/'coordinator-observations.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
