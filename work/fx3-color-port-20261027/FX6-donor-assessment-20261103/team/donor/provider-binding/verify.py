#!/usr/bin/env python3
"""Dependency-free receipt verification for the bounded offline stage."""
import hashlib
import json
import pathlib
import struct

HERE = pathlib.Path(__file__).resolve().parent
DONOR = HERE.parent
MAC = HERE.parents[5]
INPUTS = {
    'fx6_av': DONOR / 'fat-files/nflasha3/av-cam.bin',
    'fx3_av': MAC / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin',
    'fx6_im': DONOR / 'nflasha15-files/bin/im.elf',
    'fx6_kernel': DONOR / 'fat-files/nflasha3/vmlinux.bin',
    'fx6_wbi': DONOR / 'tree/0700_part_image/dev/nflasha5',
    'fx6_prior_init': DONOR / 'cp-av-analysis/init-routing/init-trace.json',
    'fx3_prior_init': MAC / 'work/fx3-color-port-20261027/initializer-guest-results.json',
    'grm_ma': DONOR / 'nflasha15-files/kmod/grm_ma.ko',
    'osal_uipc': DONOR / 'nflasha15-files/kmod/osal_uipc.ko',
    'stream': DONOR / 'nflasha15-files/kmod/stream.ko',
    'stream2': DONOR / 'nflasha15-files/kmod/stream2.ko',
    'prior_caller_static': DONOR / 'cp-av-analysis/init-routing/caller-selection/static-evidence.json',
    'prior_caller_replay': DONOR / 'cp-av-analysis/init-routing/caller-selection/caller-replay.json',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    binding = json.loads((HERE / 'binding-evidence.json').read_text())
    replay = json.loads((HERE / 'provider-replay.json').read_text())
    adapter = json.loads((HERE / 'adapter-receipt.json').read_text())
    assert set(binding['pins']) == set(INPUTS)
    for key, path in INPUTS.items():
        assert sha(path) == binding['pins'][key], key
    assert replay['source_sha256'] == {'FX6_6.01': binding['pins']['fx6_av'],
                                        'FX3_7.02': binding['pins']['fx3_av']}
    assert adapter['binding_input_sha256'] == sha(HERE / 'binding-evidence.json')
    models = binding['models']
    assert models['FX6_6.01']['look22']['normalized_70_payloads_sha256'] == \
           models['FX3_7.02']['look22']['normalized_70_payloads_sha256']
    assert all(len(models[n]['look22']['rows']) == 70 for n in models)
    assert len(replay['cases']) == 6
    checks = []
    for case in replay['cases']:
        assert not case['violations'] and len(case['stub_calls']) == 1
        assert case['event_unchanged'] and all(case['stack_canaries_preserved'])
        assert all(case['mode_result']['callee_saved_preserved'].values())
        assert case['mode_instructions'] < replay['instruction_budget_per_stage']
        assert case['dispatch_instructions'] < replay['instruction_budget_per_stage']
        if case['fixture_status'] == 0:
            assert case['builder'] is None and case['mode_result']['mode'] == 2
        elif case['fixture_word'] == '0x30':
            assert case['mode_result']['mode'] == 3 and case['mode_result']['flag'] == 0
            assert case['builder']['count'] == 70 and case['builder']['x20'] == 22
        else:
            assert case['fixture_word'] == '0x31'
            assert case['mode_result']['mode'] == 3 and case['mode_result']['flag'] == 1
            assert case['builder']['count'] == 84 and case['builder']['x20'] == 31
        # All original CPU writes must be stack or this model's flag/mode word.
        cfg = models[case['name']]
        valid = {0xffffffc001000000 + int(cfg['flag_offset'], 16),
                 0xffffffc001000000 + int(cfg['mode_offset'], 16)}
        for w in case['writes']:
            addr = int(w['address'], 16)
            if w['stage'] != 'host_provider_stub':
                assert 0x50000000 <= addr < 0x50010000 or addr in valid
        checks.append({'model': case['name'], 'provider_status': case['fixture_status'],
                       'provider_word': case['fixture_word'], 'stop': case['stop'],
                       'builder_count': case['builder']['count'] if case['builder'] else None,
                       'mode_instructions': case['mode_instructions'],
                       'dispatch_instructions': case['dispatch_instructions']})
    assert len(adapter['negatives']) == 5 and all(n['rejected'] for n in adapter['negatives'])
    assert adapter['positive']['not_executable_as_firmware']
    assert adapter['positive']['fx3_backend_boundary']['event_callback_at_0x10'].startswith('unbound')
    assert not replay['hardware_submitted'] and not replay['natural_provider_identified']
    output = {'status': 'PASS', 'original_and_prior_pins_checked': len(INPUTS),
              'source_sha256': {name: sha(HERE / name) for name in
                  ('analyze.py', 'replay.py', 'adapter.py', 'verify.py', 'prepare.sh')},
              'output_sha256': {name: sha(HERE / name) for name in
                  ('binding-evidence.json', 'provider-replay.json', 'adapter-receipt.json')},
              'cases': checks, 'negative_adapter_cases': len(adapter['negatives']),
              'evidence_scope': 'static original byte decode and isolated CPU replay with explicit synthetic provider; no natural selector, kernel provider implementation, DMA, VM or camera proof'}
    (HERE / 'run-receipt.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'pins': len(INPUTS),
                      'cpu_cases': len(checks), 'adapter_negatives': len(adapter['negatives'])}))


if __name__ == '__main__':
    main()
