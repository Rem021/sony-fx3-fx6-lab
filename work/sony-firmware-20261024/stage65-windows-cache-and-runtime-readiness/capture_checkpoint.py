#!/usr/bin/env python3
"""Record the reviewed handoff and observed limits, without a Windows claim."""
import datetime
import json
import re
import prepare_handoff as h


def main():
    im = h.im
    im.volume()
    stage = h.STAGE
    out = stage / 'checkpoint-main-screen-and-user-relay.json'
    assert not out.exists()
    prior = h.BASE / 'stage64-osal-offline-link/final-receipt.json'
    assert im.sha(prior.read_bytes()) == '0bf042fe283fe4a56c9146bbe9eb5cd8cc750847877922cecf45d69355220b6a'
    rows = json.loads(prior.read_text())['files']
    assert len(rows) == 23
    for row in rows:
        assert im.sha((h.ROOT / row['path']).read_bytes()) == row['sha256']
    canonical = h.BASE / 'GOAL_STATUS.json'
    assert canonical.read_bytes() == (prior.parent / 'goal-status-after.json').read_bytes()
    goal = json.loads(canonical.read_text())
    assert len(goal['requirements']) == 16
    assert not goal['goal_complete'] and not goal['persistent_write_release']
    package = stage / 'windows-cache-handoff'
    prep = json.loads((stage / 'handoff-preparation.json').read_text())
    assert set(x.name for x in package.iterdir()) == set(prep['four_file_hashes'])
    for name, digest in prep['four_file_hashes'].items():
        assert im.sha((package / name).read_bytes()) == digest
    manifest = json.loads((package / 'sha256-manifest.json').read_text())
    assert manifest['windows_project_root'] == h.WINDOWS_PROJECT
    assert manifest['windows_new_output_project_relative_path'] == h.WINDOWS_OUTPUT
    for field in (manifest['windows_project_root'], manifest['windows_new_output_project_relative_path']):
        assert '\\\\' not in field
    cs = (package / 'Fx3CachedAssociations.cs').read_text()
    ps = (package / 'Review-Fx3Msc.ps1').read_text()
    libraries = re.findall(r'\[DllImport\("([^"]+)"', cs)
    assert set(libraries) == {'setupapi.dll', 'cfgmgr32.dll'} and len(libraries) == 9
    externs = re.findall(r'static extern \w+ (\w+)\(', cs)
    assert len(externs) == 9
    assert not {'CreateFileW', 'DeviceIoControl', 'ReadFile', 'WriteFile'} & set(externs)
    assert ps.index("if ($Mode -eq 'DryRun')") < ps.index('exit 0') < ps.index('Add-Type -Path')
    assert '[IO.FileMode]::CreateNew' in ps
    record = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'state': 'PREPARED_REVIEWED_WAITING_FOR_HOST_DIRECTORY_AND_TRANSFER',
        'prior_sealed_files_verified': len(rows),
        'canonical_latest_stage': goal['latest_stage'],
        'canonical_not_modified_for_unverified_remote_result': True,
        'package_hashes_verified': prep['four_file_hashes'],
        'windows_output': prep['windows_output'],
        'source_review': {
            'reviewer': 'Same agent manual source read plus import/hash/guard checks; not a Windows compiler or device test',
            'native_libraries': sorted(set(libraries)),
            'native_metadata_entry_points': externs,
            'no_device_handle_or_command_entry_points_in_CSharp': True,
            'DryRun_returns_before_AddType': True,
            'new_host_local_output_only': True,
            'Windows_compilation_or_execution_verified': False,
            'active_INQUIRY_source_in_package': False,
        },
        'observed_UU': {
            'connected_host': 'DESKTOP-262CR7C',
            'main_display': 'PG34WCDM',
            'user_now_allows_main_screen_while_computer_unused': True,
            'virtual_screen_only_restriction_superseded_by_user': True,
            'prior_virtual_screen_observation': 'Desktop only; no FX3 Codex window visible',
            'main_screen_observation': 'UU and NVIDIA windows; existing FX3 session not yet located',
            'remote_mouse_verified': True,
            'remote_keyboard': 'One Codex search appeared, subsequent text and paste attempts had no visible result',
            'file_transfer': 'Four local files selected via native keyboard; destination still existing outputs; transfer count remained legacy ten',
            'new_destination_directory_verified': False,
            'four_file_transfer_verified': False,
            'Windows_task_dispatched_or_run_verified': False,
            'user_relay': 'User volunteered to relay text; supplied a host-local-directory-only prompt, awaiting result',
        },
        'fresh_public_recovery_observation': {
            'url': 'https://github.com/QAQLeonard/a7c2-fl23-research/issues/31',
            'observed_date': '2026-10-26',
            'page_comment_count_observed': 17,
            'new_self_report': 'Oct26 dt-nb reports success after Oct25 movie/P workaround; no independent verification',
            'other_Oct26_comments': 'Original author plans to try; another commenter discusses service/third-party quotes without confirmed restored outcome',
            'repair_costs_or_outcomes_independently_verified': False,
            'FX3_applicability_proven': False,
            'reason_not_a_recovery_guarantee': 'A7C2 still-path modification could leave movie boot usable; this project targets the FX3 movie path itself',
            'attachments_downloaded_or_executed': False,
        },
        'camera_operations': {
            'interface_open_auth_mode_driver_media_file_module_WBI_flash': False,
            'authorization': 'Windows cached PnP metadata only',
            'requirements_retained': 16,
            'hardware_recording_or_same_body_recovery_verified': False,
            'goal_complete': False,
        },
    }
    im.write_json(out, record)
    assert canonical.read_bytes() == (prior.parent / 'goal-status-after.json').read_bytes()
    print(json.dumps({'checkpoint': str(out), 'sha256': im.sha(out.read_bytes()),
                      'transfer_or_execution_verified': False, 'requirements_retained': 16}))


if __name__ == '__main__':
    main()
