#!/usr/bin/env python3
"""Dependency-free rehash and assertions for bounded caller-selection receipts."""
import hashlib
import json
import pathlib
import platform

ROOT = pathlib.Path(__file__).resolve().parent
AV = ROOT.parents[2] / 'fat-files/nflasha3/av-cam.bin'
FX3 = ROOT.parents[5]
PIN = '56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'
FX3_RECEIPTS = {
    'initializer-guest-results.json': '29c76396ae58e8caca2bd96e0eb0408854c163e60556b5d27b4da9d6bd76ab95',
    'look-consumer-guest-results.json': '6443be58aaa2a547aa7488a7551452ab4ce995bc108e8cb9244f7892b7b84a4f',
}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load(name):
    return json.loads((ROOT / name).read_text())


def main():
    assert sha(AV) == PIN
    image = AV.read_bytes()
    # Older FX3 material is used as a pinned comparison reference only, never rerun here.
    fx3_pins = {name: sha(FX3 / name) for name in FX3_RECEIPTS}
    assert fx3_pins == FX3_RECEIPTS
    static = load('static-evidence.json')
    replay = load('caller-replay.json')
    assert static['source']['sha256'] == replay['source_sha256'] == PIN
    assert static['source']['base'] == replay['base'] == '0xffffffc001000000'
    for region in static['regions'].values():
        start, end = int(region['start'],16), int(region['end_exclusive'],16)
        assert hashlib.sha256(image[start:end]).hexdigest() == region['sha256']
        for ins in region['instructions']:
            offset = int(ins['file_offset'],16)
            assert image[offset:offset+len(bytes.fromhex(ins['bytes_le']))].hex() == ins['bytes_le']
    calls = static['direct_branch_index']['0x2a7978']
    assert [x['file_offset'] for x in calls] == [
        '0x2a74e4', '0x2a75ac', '0x2a7600', '0x2a7690', '0x2a7748']
    assert not static['dma_builder_address_refs']['exact_qword_offsets']
    assert not static['dma_builder_address_refs']['simple_pc_relative_refs']
    assert [x['provider_slot'] for x in static['runtime_provider_edges']] == ['0x3c0','0x4c0']
    by = {x['name']: x for x in replay['cases']}
    assert len(by) == 5 and replay['hardware_submitted'] is False
    for name, ip in [('look22_ip0',0),('look22_ip1',1)]:
        c=by[name]
        assert c['stop']=='0x2a74e4' and not c['violations'] and c['error'] is None
        assert c['builder_arguments']['ip']==ip and c['builder_arguments']['count']==70
        assert c['builder_arguments']['descriptor_va']=='0xffffffc001aa2ca0'
        assert c['lookup_before']==c['lookup_after']
        assert all(c['flag_before'][k]==c['flag_after'][k] for k in ('X19','X20','X21','SP'))
        assert c['flag_after']['w0']==0 and c['event_unchanged'] and all(c['stack_canaries_preserved'])
    assert by['override_forces_31']['builder_arguments']['count']==84
    assert by['override_forces_31']['builder_arguments']['descriptor_va']=='0xffffffc001a822b8'
    assert by['other_event_kind']['stop']=='0x2a7574'
    assert by['original_mode_reaches_logger']['stop']=='0x2a65f8'
    files = ['analyze.py','replay_caller.py','prepare.sh','static-evidence.json','caller-replay.json']
    result = {
        'result': 'PASS', 'python': platform.python_version(), 'fx6_av_sha256': PIN,
        'fx3_comparison_only_sha256': fx3_pins,
        'artifact_sha256': {name: sha(ROOT / name) for name in files},
        'checks': {'direct_dma_calls':len(calls), 'direct_event_dispatch_calls':len(static['direct_branch_index']['0x2a7374']),
                   'bounded_cpu_cases':len(by), 'fixture_look22_ip0_instructions':by['look22_ip0']['instruction_count'],
                   'runtime_provider_slots':['0x3c0','0x4c0'], 'hardware_submitted':False},
        'scope': 'static original-byte index and bounded CPU guest to pre-builder call, synthetic event/mode state; no VM, device, DMA submit, pixel proof',
    }
    (ROOT/'run-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'result':'PASS','checks':result['checks']}))


if __name__=='__main__':main()
