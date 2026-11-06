#!/usr/bin/env python3
"""Verify original result-write footprint and old/new caller frame integrity."""
from pathlib import Path
import datetime
import json
import struct
import rate_abi_fix as t


def phases(case):
    for i,e in enumerate(case['events']):
        assert int(e['SP_after'],16)%16==0
        if i==0:assert e['native_output_or_return_adapter'] is False
        else:
            assert e['native_output_or_PC_return_adapter'] is False
            chunks=e['same_instance_observation_slices']
            assert sum(x['executed'] for x in chunks)==len(e['pcs'])<=2000000
            assert all(a['end_pc']==b['start_pc'] for a,b in zip(chunks,chunks[1:]))
            assert chunks[-1]['reason']==e['reason']


def main():
    t.im.volume();s=t.STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    pins={'stage69-native-16M-callpath':'417033856d0b31e1019bd64b932199d826ebdefcc9321a96dae1334fae8c1d8e',
          'stage73-native-free-message-path':'ad9808d60e977f22db80f43eedbbd9e8e8da263a231e8fe85fae35e499c418f7'}
    counts={}
    for stage,digest in pins.items():
        p=t.BASE/stage/'final-receipt.json';assert t.im.sha(p.read_bytes())==digest
        j=json.loads(p.read_text());counts[stage]=len(j['files'])
        for row in j['files']:assert t.im.sha((t.ROOT/row['path']).read_bytes())==row['sha256']
    assert counts=={'stage69-native-16M-callpath':50,'stage73-native-free-message-path':18}
    assert (s/'goal-status-before.json').read_bytes()==(t.BASE/'GOAL_STATUS.json').read_bytes()==(t.BASE/'stage73-native-free-message-path/goal-status-after.json').read_bytes()
    p=s/'run-20261026/rate-ABI-results.json';j=json.loads(p.read_text())
    raw=(s/'rate_abi_fix.py').read_bytes();assert t.im.sha(raw)==j['source_receipt']['script_sha256']
    assert (p.parent/'executed-source.py').read_bytes()==raw
    old=(t.c.STAGE/'channel_adapter.c').read_bytes();new=(s/'channel_adapter.c').read_bytes()
    assert new==old.replace(b'typedef struct { u64 trace,target,cpb; } Rate;',
            b'typedef struct { u64 trace,target,cpb; u8 unclassified_tail[32]; } Rate;').replace(
            b'_Static_assert(sizeof(Rate)==24,"indirect rate result");',
            b'_Static_assert(sizeof(Rate)==56,"covers original 52-byte write span with 8-byte alignment");')
    assert (p.parent/'compiled-source.c').read_bytes()==new
    assert t.im.sha(old)==j['source_receipt']['old_C_source_sha256']
    assert t.im.sha(new)==j['source_receipt']['corrected_C_source_sha256']
    assert t.im.sha((p.parent/'channel_adapter.a64.o').read_bytes())==j['source_receipt']['corrected_object_sha256']
    compiled=json.loads((p.parent/'compile-receipt.json').read_text())
    assert compiled['returncode']==0 and not compiled['stderr']
    assert len(j['quarantined_old_baseline'])==len(j['corrected_target_cases'])==len(j['regression_controls'])==2
    assert j['bounded_fragments']==41
    for fixed,key in [(False,'quarantined_old_baseline'),(True,'corrected_target_cases')]:
        for case in j[key]:
            phases(case);assert case['corrected_container']==fixed
            assert len(case['events'])==(8 if fixed else 6)
            q=case['original_query_result_write_audit'];size=56 if fixed else 24
            assert q['container_bytes']==size and q['original_result_written_span_bytes']==52
            assert q['actual_written_bytes']==50 and q['written_offsets']==sorted(set(range(52))-{46,47})
            assert q['decoded_trace_target_CPB']==[25999360,16000000,26000000]
            assert q['saved_LR_unchanged']==fixed and q['full_frame_outside_container_unchanged']==fixed
            lr=[x for x in q['saved_register_slots'] if x['register']=='x30'][0]
            before=int.from_bytes(bytes.fromhex(lr['before_hex']),'little')
            assert hex(before)==case['original_adapter_entry']['LR']
            if fixed:
                assert not q['stores_outside_declared_container']
                assert all(x['unchanged'] for x in q['saved_register_slots'])
                assert len(case['original_channel_entries'])==len(case['resource_messages'])==len(case['kernel_service_entries'])==1
                assert case['kernel_service_entries'][0]['names']==['_raw_spin_lock_irqsave']
                assert case['events'][-1]['reason']=='boundary: before_original_unexecuted_kernel_service'
            else:
                assert sum(x['bytes'] for x in q['stores_outside_declared_container'])==26
                assert before!=int.from_bytes(bytes.fromhex(lr['after_hex']),'little')
                assert not case['original_channel_entries'] and not case['resource_messages'] and not case['kernel_service_entries']
                assert case['events'][-1]['reason']=='boundary: after_original_rate_writes_before_adapter_uses_result'
            assert case['control_at_stop']['live']==1 and case['producer_lease_still_live']
            assert case['original_FH_descriptor_preserved']
            assert not case['actual_channel_return_adapter_unwind_hardware_or_recovery_proven']
    for case in j['regression_controls']:
        phases(case)
        assert not case['actual_original_rate_calls'] and not case['actual_original_rate_returns']
        if case['negative']:
            assert case['negative']=='closed' and case['our_unexecuted_rejection_entries'][0]['reason']==3
            assert len(case['events'])==6
        else:
            assert case['row']==431 and len(case['events'])==7
            assert case['kernel_service_boundary'][0]['names']==['_raw_spin_lock_irqsave']
    blob=(t.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert t.im.sha(blob)==j['source_receipt']['avcam_sha256']==t.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    assert j['original_getter_full_function']==t.im.dump(blob,0x225b7c,0x225e40,t.V)
    assert t.im.dump(blob,0x225e24,0x225e28,t.V)[0]['asm']=='str w10, [x19, #0x30]'
    q=json.loads((s/'prior-adapter-quarantine.json').read_text())
    assert q['prior_Rate_size']==24 and q['original_final_store_end_offset']==52 and not q['old_adapter_camera_use_permitted']
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_OLD_RESULT_OVERFLOW_REPRODUCED_FIXED_FRAME_RESULT_SCOPE',
        'prior_sealed_file_counts':counts,'old_baseline_cases':2,'fixed_target_cases':2,'regression_controls':2,
        'total_bounded_fragments':41,'old24_original_result_stores_outside_container_bytes':26,
        'old24_saved_LR_and_register_slots_corrupted':True,
        'fixed56_all_original52_span_writes_contained':True,'fixed56_all_saved_register_slots_unchanged':True,
        'fixed_target_original_channel_arguments_and_kernel_boundary':True,
        'old_numeric_prefix_is_not_safe_adapter_evidence':True,
        'original_getter_complete_type_size_or_tail_field_semantics_proven':False,
        'prior_original_only_stages_with_inert_adapter_invalidated':False,
        'channel_return_unwind_real_OSAL_hardware_main_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    t.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'bounded_fragments':41,'old_saved_LR_corrupted':True,
                      'corrected_saved_register_slots_preserved':True}))


if __name__=='__main__':main()
