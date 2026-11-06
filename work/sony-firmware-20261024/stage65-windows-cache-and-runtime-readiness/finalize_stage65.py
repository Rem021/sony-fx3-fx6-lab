#!/usr/bin/env python3
"""Seal reviewed stage65, recording native PnP followup as pending at sealing."""
import datetime
import json
import prepare_handoff as h


def main():
    h.im.volume()
    s, root, im = h.STAGE, h.ROOT, h.im
    assert not (s/'final-receipt.json').exists()
    before = (s/'goal-status-before.json').read_bytes()
    canonical = h.BASE/'GOAL_STATUS.json'
    assert canonical.read_bytes() == before
    assert im.sha(before) == '383864bbaf766fc5e5a6c5b550a1f9499d9288097c1a36991621c6c2d340ca22'
    review = json.loads((s/'coordinator-observations.json').read_text())
    assert review['prior23_sealed_files_and_canonical_verified']
    assert review['Windows_compile_x64_ABI'] == 'PASS'
    assert review['original_CachedAssociations_Collect_calls'] == 0
    assert review['GPL_archives_size_SHA256_official_MD5_verified']
    assert (s/'README.md').is_file()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel = str(s.relative_to(root))
    gui = {
        'observed_utc': now,
        'observation_method': 'CUA native UU window AX plus screenshots; task submit verified by new purple user bubble and processing indicator',
        'host': 'Existing DESKTOP-262CR7C and existing FX3 Codex conversation',
        'user_UI_scope': 'Main screen permitted while computer unused, supersedes earlier virtual-only gaming constraint',
        'Mac_UU_permissions_or_keyboard_mapping_changed_this_phase': False,
        'input_finding': 'Mac Command+V arrived as Windows clipboard-history UI. Exact task-prefix entry selected after restoration reorder, draft inspected, 180ms click verified send.',
        'attempt2_returned_file_count': 13,
        'attempt2_original_four_inputs_and_attempt1_eight_files_unchanged': True,
        'native_followup_tag': 'FX3_NATIVE_PNP_20261026T160454Z',
        'native_followup_prompt': rel+'/WINDOWS_NATIVE_PNP_PROMPT.txt',
        'native_followup_prompt_sha256': im.sha((s/'WINDOWS_NATIVE_PNP_PROMPT.txt').read_bytes()),
        'native_followup_dispatched': True,
        'native_followup_observed_progress': 'Windows agent reports local PnPUtil help supports options and execution-policy list recorded; then matching-node enumeration pending. Temporary model reconnect2/5 visible.',
        'native_followup_final_files_retrieved_or_reviewed_at_seal': False,
        'native_followup_result': 'PENDING; no claim of candidate, binding or driver pass',
        'next_result_collection': 'Retrieve only public subdirectory into a new phase. Keep host private raw IDs and interface paths local.',
        'Windows_public_target': 'C:/Users/owo/Documents/Codex/2026-10-16/rea-2/outputs/fx3-native-pnp-20261026T160454Z/public',
        'camera_authorization': 'Cached PnP metadata only, unchanged',
        'camera_interface_open_commands_auth_modes_driver_media_files_modules_WBI_flash': False,
    }
    im.write_json(s/'UU-native-followup-observation.json', gui)
    summary = {
        'created_utc': now,
        'status': 'BOUNDED_OFFLINE_RUNTIME_ABI_AND_WINDOWS_COMPILE_PASS_POLICY_BLOCKED_COLLECTION_NATIVE_FOLLOWUP_PENDING',
        'prior_sealed_files_verified': 23,
        'Windows_received_attempt2_files': 13,
        'Windows_compile_x64_ABI': 'PASS',
        'original_DryRun': 'POLICY_BLOCKED_BEFORE_SCRIPT_BODY',
        'original_CachedAssociations_Collect_calls': 0,
        'native_PnP_followup': 'DISPATCHED_PENDING_RESULT_REVIEW',
        'original_startup_component_cases': 2,
        'original_instructions_per_component': 5,
        'native_full_boot_scheduler_allocator_OR_HAL': False,
        'vendor_source_label': 'FX3 7.00; selected ABI correlation with original7.02 kernel only',
        'vendor_kernel_version': '4.9.337',
        'vendor_members_readback_verified': 12,
        'complete_FX3_hardware_emulator_or_safe_flash_or_recovery_proven': False,
        'goal_complete': False,
        'persistent_write_release': False,
    }
    im.write_json(s/'summary.json', summary)
    old = json.loads(before)
    g = json.loads(before)
    g['updated_utc'] = now
    g['latest_stage'] = s.name
    g['research_activity'] = 'offline_runtime_analysis_and_authorized_Windows_cached_metadata_preparation'
    g['progress_audit'] = {
        'classification': 'progress',
        'previous_goal_turn_classification': 'progress',
        'basis': [
            'stage64封存23件及canonical重新校验；四件缓存包UU传入及回传逐字节一致，首轮八件回执保留。',
            'Windows首轮JavaScript封装失败发生在进程前；第二轮C#编译和x64 ABI通过，PS1 DryRun被执行策略阻止，正文未运行，Collect累计0次。未调整执行策略或提权。',
            '系统PnPUtil替代路线已按微软原文审核并提交，已观察本机help/策略列表步骤；最终缓存父子关联、唯一候选和驱动结果仍待回传核对，不标PASS。',
            '两个独立客体各运行5条原7.02 kernel启动指令，原SP与SP_EL0由原代码生成；BSS范围仅静态核对，不恢复上轮OSAL请求，不宣称Linux启动或硬件仿真完成。',
            'Sony公开7.00 Linux4.9.337源码归档MD5/SHA256及12成员校验；vendor任务结构、UDIF数组注册/回调data参数、真实线程创建/唤醒/完成等待与7.02原字节选点核对。不是整个源码构建精确匹配。',
            '用户已允许闲置时操作主屏；相机授权仍仅缓存元数据。16项目标、实录/音画长录、同机健康备份/冷启动/恢复与独立救援未降低，未刷写。',
        ],
        'completion_not_claimed': True,
    }
    g['latest_stage_evidence']['stage65_windows_cache_and_runtime_readiness'] = {
        'readme': rel+'/README.md',
        'summary': rel+'/summary.json',
        'review': rel+'/coordinator-observations.json',
        'boot_component': rel+'/boot-context-audit.json',
        'vendor_source_crosscheck': rel+'/vendor-source-runtime-crosscheck.json',
        'Windows_attempt2': rel+'/from-windows-host-attempt-2/receipt-attempt2.json',
        'native_followup': rel+'/UU-native-followup-observation.json',
        'scope': 'Original five-instruction boot component plus selected public vendor ABI; Windows compile-only pass, PS1 policy rejection and native metadata followup pending.',
        'goal_complete': False,
        'authorization_unchanged': True,
    }
    for req in g['requirements']:
        if req['id'] in ('G02', 'G08', 'G10', 'G11', 'G15'):
            req['evidence'].extend([rel+'/boot-context-audit.json', rel+'/vendor-source-runtime-crosscheck.json'])
            req['remaining'] += ' stage65原启动5条指令的2个独立客体和公开7.00源码选定ABI核对通过；原7.02完整Linux线程/调度/分配/完成通知、真实16M接合与实机主录/同机恢复仍缺。'
    dep = g['external_dependencies']['Windows_cached_association_handoff']
    dep.update({
        'status': 'host_online_transfer_and_compile_verified_PS1_policy_blocked_native_PnP_followup_pending',
        'user_response': '已恢复；后明确电脑不用了，可直接用主屏。',
        'latest_host_state': 'UU main-screen online, existing FX3 Codex conversation; native cached-metadata task processing',
        'UI_scope': 'Main screen permitted while computer unused; camera cached-only scope unchanged',
        'new_remote_attempts_this_stage': True,
        'cached_only_authorization_unchanged': True,
        'active_camera_authorization_granted': False,
        'source_compile_x64_ABI': 'PASS',
        'original_cached_collection': 'NOT_RUN; DryRun PS1 blocked before body; Collect calls0',
        'pending_native_task_tag': gui['native_followup_tag'],
        'policy_or_elevation_change': False,
    })
    g['next_authorized_cached_metadata_action'].update({
        'prepared_handoff': rel+'/windows-cache-handoff/sha256-manifest.json',
        'action': 'Review pending native PnPUtil enum-only result and retrieve public receipts into a new phase. No rerun of blocked PS1, policy bypass or camera interface access.',
        'current_external_dependency': 'UU online; original FX3 Windows Codex task submitted. Native help/policy steps observed; final FX3 parent-child/interface/driver result not yet retrieved or verified.',
        'whole_goal_blocked': False,
        'active_query_ready': False,
        'active_query_permission_request': False,
    })
    g['next_safe_offline_actions'][0] = '以公开vendor源码与7.02原字节选定ABI为依据，继续真实线程创建/唤醒/完成通知、分配器与UIPC初始化依赖。原启动任务/SP_EL0与两段5指令不构成完整Linux，不能用伪任务、假IRQ或分配/同步回复替代；保留目标16M真实资源接合及全部实机验收。'
    g['next_safe_offline_actions'][5] = '跟踪已提交Windows原生PnPUtil缓存枚举的最终脱敏回执，另目录传回核对；不要重试被执行策略阻止的PS1，不提权、不弱化策略。相机接口/认证/模块/媒体/WBI/写入仍未授权。'
    for key in ('objective', 'authorization', 'completion_rule'):
        assert g[key] == old[key]
    assert len(g['requirements']) == 16
    assert [(x['id'],x['status']) for x in g['requirements']] == [(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json', g)
    after = (s/'goal-status-after.json').read_bytes()
    index = root/'README.md'
    ib = index.read_bytes()
    entry = '- [2026-10-26 FX3 Windows缓存准备与原运行环境](<work/sony-firmware-20261024/stage65-windows-cache-and-runtime-readiness/README.md>)：UU交接和x64编译通过；PS1采集被策略阻止，原生PnP枚举待回执；原启动5指令与公开vendor ABI核对通过，完整Linux、硬件主录和恢复仍未验收。'
    text = ib.decode()
    assert entry not in text and text.count('## 相机与固件研究\n') == 1
    ia = text.replace('## 相机与固件研究\n', '## 相机与固件研究\n\n'+entry, 1).encode()
    assert canonical.read_bytes() == before and index.read_bytes() == ib
    canonical.write_bytes(after)
    index.write_bytes(ia)
    files = [{'path':str(p.relative_to(root)), 'bytes':p.stat().st_size, 'sha256':im.sha(p.read_bytes())}
             for p in sorted(s.rglob('*')) if p.is_file()]
    final = {
        'schema': 'fx3-stage65-windows-cache-runtime-readiness/1',
        'created_utc': now,
        'volume_uuid': im.VOLUME,
        'files': files,
        'previous_manifest_sha256': im.sha((h.BASE/'stage64-osal-offline-link/final-receipt.json').read_bytes()),
        'mutable_progress': {'path':str(canonical), 'before_sha256':im.sha(before), 'after_sha256':im.sha(after)},
        'readme_index_entry': entry,
        'readme_index_before_sha256': im.sha(ib),
        'readme_index_after_sha256': im.sha(ia),
        'operations': {
            'original_firmware_unchanged': True,
            'UU_transfer_and_existing_Windows_Codex_dispatch': True,
            'Windows_compile_cached_only_source_and_ABI': True,
            'original_PS1_body_or_Collect_executed': False,
            'native_metadata_followup_result_at_seal': 'PENDING_REVIEW',
            'security_policy_mapping_or_elevation_changed': False,
            'camera_interface_commands_auth_mode_driver_files_module_WBI_flash': False,
            'downloaded_vendor_source_executed': False,
            'complete_kernel_boot_hardware_recording_or_recovery': False,
            'goal_complete': False,
            'persistent_write_release': False,
        },
    }
    im.write_json(s/'final-receipt.json', final)
    assert all(im.sha((root/x['path']).read_bytes()) == x['sha256'] for x in files)
    assert canonical.read_bytes() == after and index.read_bytes() == ia
    print(json.dumps({'sealed_files':len(files), 'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name, 'requirements_retained':16, 'goal_complete':False,
                      'Windows_native_followup':'pending final receipt review'}))


if __name__ == '__main__':
    main()
