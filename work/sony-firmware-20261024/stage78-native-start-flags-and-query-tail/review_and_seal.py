#!/usr/bin/env python3
"""Review native fragment evidence and seal its limited claim."""
from pathlib import Path
from fractions import Fraction
import datetime
import json
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE))
import start_flags as a
im, BASE, ROOT, V = a.im, a.BASE, a.ROOT, a.V


def main():
    im.volume()
    s = STAGE
    assert not (s/'final-receipt.json').exists()
    prior = BASE/'stage77-upstream-recovery-boundaries/final-receipt.json'
    assert im.sha(prior.read_bytes()) == '44971a4749e8838b4f7a1edb5b289ae836bc612f4141f80cee24f4cba624e0c4'
    rows = json.loads(prior.read_text())['files']
    assert len(rows) == 18
    for row in rows:
        assert im.sha((ROOT/row['path']).read_bytes()) == row['sha256']
    before = (s/'goal-status-before.json').read_bytes()
    canonical = BASE/'GOAL_STATUS.json'
    assert before == canonical.read_bytes() == (prior.parent/'goal-status-after.json').read_bytes()
    result_path = s/'run-20261026/start-flags-results.json'
    j = json.loads(result_path.read_text())
    assert j['source_receipt']['script_sha256'] == im.sha((s/'start_flags.py').read_bytes())
    for filename, key in (('resource_alias.a64.o', 'writer_object_sha256'),
                          ('channel_adapter.a64.o', 'adapter_object_sha256')):
        assert im.sha((a.p.STAGE/'run-20261026'/filename).read_bytes()) == j['source_receipt'][key]
    assert im.sha((a.p.STAGE/'private_storage.py').read_bytes()) == j['source_receipt']['storage_runner_sha256']
    assert (s/'run-20261026/executed-source.py').read_bytes() == (s/'start_flags.py').read_bytes()
    assert j['status'] == 'PASS_NATIVE_LOWER_QUERY_START_FLAGS_OPTIONAL_RATE_AND_TAIL_COPY'
    assert len(j['cases']) == 2 and j['bounded_fragments'] == 44
    assert [x['seed'] for x in j['cases']] == [0xa5, 0xc3]
    for x in j['cases']:
        assert x['suspended_Open_not_resumed'] and not x['actual_main_recording_or_recovery_proven']
        assert len(x['cases']) == 4
        q = x['events'][-1]
        assert q['reason'] == 'returned'
        assert all(hex(V+pc) in q['pcs'] for pc in (0x2304f0, 0x228c64, 0x227870, 0x225b7c))
        assert x['query_written_offsets'] == sorted(set(range(0x34))-set(range(0x2e, 0x30)))
        assert x['corrected_adapter_query']['saved_LR_unchanged']
        assert [z['decoded_optional_target'] for z in x['cases']] == [None, 16000000, 20000000, None]
        assert [z['extra_mask'] for z in x['cases']] == [0, 0x80, 0x80, 0x100]
        assert [z['start_first5_hex'] for z in x['cases']] == ['0001000200']+['0001010200']*3
        for i, z in enumerate(x['cases']):
            assert z['original_pending_stack_query_and_selected16M_preset_preserved']
            assert not z['actual_live_component_shared_lock_Start_transport_or_recording_proven']
            e = z['events'][-1]
            assert e['reason'] == 'returned' and e['start_pc'] == hex(V+0x246274)
            assert all(hex(V+pc) in e['pcs'] for pc in (0x248d64, 0x249544, 0x246418))
            assert e['whole_arena_outside_declared_state_and_outputs_unchanged']
            if i:
                assert hex(V+0x249524) in e['pcs'] and hex(V+0x249528) in e['pcs']
            else:
                assert hex(V+0x249524) not in e['pcs']
        assert x['cases'][3]['copied_tail_fields'] == [8008, 240000]
    assert Fraction(240000, 8008) == Fraction(30000, 1001) != Fraction(30, 1)
    assert not j['Windows_UU_camera_operations'] and not j['goal_complete'] and not j['persistent_write_release']
    blob = (BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob) == im.PINS['stage2/extraction/files/nflasha3/av-cam.bin'] == j['source_receipt']['avcam_sha256']
    def ins(pc):
        return im.dump(blob, pc, pc+4, V)[0]['asm']
    for pc, target in ((0x22b3a8, 0x230470), (0x230474, 0x228abc), (0x228ae8, 0x21f7f4)):
        assert hex(V+target) in ins(pc)
    assert '#0x80' in ins(0x21f93c) and '#0x300' in ins(0x21f988)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel = str(s.relative_to(ROOT))
    static = {
        'created_utc': now, 'scope': 'ORIGINAL_BYTES_STATIC_CHAIN_NOT_EXECUTED_START',
        'locked_query_and_Start_wrappers_executed': False,
        'original_query_caller_space_bytes': 56,
        'query_tail_copy': {'query2c_to_QoS1e': 8008, 'query30_to_QoS20': 240000,
                            'exact_ratio': '30000/1001', 'hardware_timing_or_official_field_names_proven': False},
        'Start_parameter_copy_order': ['common64', 'codec448', 'QoS128', 'other768'],
        'QoS_block_directly_overwrote_codec448_here': False,
        'actual_downstream_precedence_or_VCD_hardware_acceptance_proven': False,
        'regions': [{'start': hex(lo), 'end': hex(hi), 'instructions': im.dump(blob, lo, hi, V)}
                    for lo, hi in ((0x24ce54, 0x24cec0), (0x22b358, 0x22b3d0),
                                   (0x230470, 0x230478), (0x228abc, 0x228aec),
                                   (0x21f85c, 0x21f99c), (0x2494d4, 0x249548))],
    }
    im.write_json(s/'original-start-chain.json', static)
    review = {
        'created_utc': now, 'status': 'PASS_NATIVE_QUERY_TO_COMPLETE_START_FLAGS_HELPER_ONLY',
        'prior_sealed_files_verified': 18, 'bounded_fragments': 44, 'settings_cases': 8,
        'native_owner_lookup_and_16M_query': True, 'complete_original246274_and248d64_returned': True,
        'optional20M_generated_while_selected_preset_remains16M': True,
        'native_pending_settings_clear_path_executed_not_retry_safety_proven': True,
        'query_tail_preserved_and_copied': [8008, 240000],
        'static_Start_copies_separate128_and448_blocks_not_an_observed_override': True,
        'full_Start_legal_reentrancy_concurrency_shared_lock_hardware_recording_or_recovery_proven': False,
        'Windows_UU_camera_operations': False, 'goal_complete': False, 'persistent_write_release': False,
        'reviewer_scope': 'Same agent source/trace/byte review; no independent implementation or physical replay.',
    }
    im.write_json(s/'completed-evidence-review.json', review)
    im.write_json(s/'summary.json', review)
    im.write_json(s/'coordinator-observations.json', {
        'recorded_utc': now, 'previous_goal_turn_classification': 'progress',
        'previous_evidence': 'stage77 sealed18 files and canonical verified; public-source/input-bound review only.',
        'new_evidence': 'Native owner lookup/query and complete Start flag/QoS preparation; optional20M and query-tail copy differentiated from selected16M. Actual Start copy chain static only.',
        'not_new_discovery': 'stage34 already established QoS numerical conversion. New here is actual current guest lookup/query source and complete parameter-preparation helper.',
        'Windows_UU_actions_this_turn': 0, 'camera_operations': False,
        'full_goal_requirements_retained': 16, 'goal_complete': False, 'persistent_write_release': False,
    })
    old = json.loads(before)
    g = json.loads(before)
    g['updated_utc'] = now
    g['latest_stage'] = s.name
    g['research_activity'] = 'Mac_only_native_owner_rate_query_to_complete_Start_flags_QoS_preparation'
    g['progress_audit'] = {
        'classification': 'progress', 'previous_goal_turn_classification': 'progress',
        'basis': [
            'stage77封存18件与canonical核对；本轮复用修正56容器/独立副本C对象，无C代码改动，原Open仍挂起。',
            '原2304f0/228c64/227870按原登记ID0取owner再调用225b7c，得到原16M预置查询；完整246274/248d64含原静音日志/原内存清理正常返回，8例44段。',
            '可选关闭/16M/20M/尾字段复制对照区分预置和另128字节QoS参数源，所选预置始终16M；8008/240000实际复制但不作字段正式命名或硬件29.97/精确30证明。stage34已有独立QoS转换，不重复称新发现。',
            '静态Start分别复制64/448/128/768字节，未证明QoS已经覆盖448块或硬件优先级。锁/真实组件/并发代次/完整Start/HAL及全部成片/同机恢复仍缺。',
        ],
        'completion_not_claimed': True,
    }
    g['latest_stage_evidence']['stage78_native_start_flags_and_query_tail'] = {
        'readme': rel+'/README.md', 'review': rel+'/completed-evidence-review.json',
        'result': rel+'/run-20261026/start-flags-results.json', 'static_chain': rel+'/original-start-chain.json',
        'scope': 'Independent native owner lookup and complete parameter-preparation helper; separate stack, declared component/settings, no locked wrapper/full Start/hardware proof.',
        'authorization_unchanged': True, 'goal_complete': False,
    }
    for req in g['requirements']:
        if req['id'] in ('G02', 'G08', 'G10'):
            req['evidence'].extend([rel+'/run-20261026/start-flags-results.json', rel+'/original-start-chain.json'])
            req['stage78_scope'] = '原登记owner/16M查询接完整启动标志及QoS helper，8例44段；可选20M块与16M预置并存，尾8008/240000实际复制。原Open挂起/独立栈/组件设置声明，真实共享同步/Start参数合并/硬件优先级/成片及恢复未证。'
    g['next_safe_offline_actions'].append(
        'stage78继续128字节QoS块的真实下游消费/与448字节codec块合并和优先顺序、清理后重试/后续策略更新，以及原共享同步/可信配置代次。预置查询16M与可选20M块可同时存在，不以任一份参数、待处理清理或helper返回1当硬件已应用/完整Start/安全重试；查询尾8008/240000的正式语义须追实际消费者。')
    for key in ('objective', 'authorization', 'completion_rule', 'current_user_operational_constraint',
                'external_dependencies', 'current_guest_adapter_prototype'):
        assert g[key] == old[key]
    assert len(g['requirements']) == 16
    assert [(x['id'], x['status']) for x in g['requirements']] == [(x['id'], x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json', g)
    after = (s/'goal-status-after.json').read_bytes()
    index = ROOT/'README.md'
    ib = index.read_bytes()
    entry = '- [2026-10-26 FX3 原启动参数与QoS尾字段](<work/sony-firmware-20261024/stage78-native-start-flags-and-query-tail/README.md>)：原登记查询接完整参数准备，区分16M预置与可选20M块，8例44段；完整Start/硬件优先级/主录/恢复未证，仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n') == 1
    ia = ib.decode().replace('## 相机与固件研究\n', '## 相机与固件研究\n\n'+entry, 1).encode()
    assert canonical.read_bytes() == before and index.read_bytes() == ib
    canonical.write_bytes(after)
    index.write_bytes(ia)
    files = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': im.sha(p.read_bytes())}
             for p in sorted(s.rglob('*')) if p.is_file()]
    final = {
        'schema': 'fx3-stage78-native-start-flags-and-query-tail/1', 'created_utc': now,
        'volume_uuid': im.VOLUME, 'files': files, 'previous_manifest_sha256': im.sha(prior.read_bytes()),
        'mutable_progress': {'path': str(canonical), 'before_sha256': im.sha(before), 'after_sha256': im.sha(after)},
        'readme_index_entry': entry, 'readme_index_before_sha256': im.sha(ib), 'readme_index_after_sha256': im.sha(ia),
        'operations': review, 'requirements_retained': 16, 'authorization_unchanged': True,
    }
    im.write_json(s/'final-receipt.json', final)
    assert all(im.sha((ROOT/x['path']).read_bytes()) == x['sha256'] for x in files)
    assert canonical.read_bytes() == after and index.read_bytes() == ia
    print(json.dumps({'sealed_files': len(files), 'manifest_sha256': im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage': s.name, 'hardware_recording_or_recovery_proven': False, 'goal_complete': False}))


if __name__ == '__main__':
    main()
