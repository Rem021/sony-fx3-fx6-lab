#!/usr/bin/env python3
"""Review original record FIFO and independent handoff at their actual scopes."""
from pathlib import Path
import datetime
import json
import sys
import buffer_record_fifo as q


def phases(case):
    for index,e in enumerate(case['events']):
        assert int(e['SP_after'],16)%16==0
        if index==0:assert e['native_output_or_return_adapter'] is False
        else:
            assert e['native_output_or_PC_return_adapter'] is False
            slices=e['same_instance_observation_slices']
            assert sum(x['executed'] for x in slices)==len(e['pcs'])<=2000000
            assert all(a['end_pc']==b['start_pc'] for a,b in zip(slices,slices[1:]))
            assert slices[-1]['reason']==e['reason']


def main():
    q.im.volume();s=q.STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    prior=q.BASE/'stage70-native-open-rejection/final-receipt.json'
    assert q.im.sha(prior.read_bytes())=='ec99ebf0d9cdbb5c80bba00e4c54635f30d57f14e4055ea8b51f08845a6e6b78'
    p=json.loads(prior.read_text());assert len(p['files'])==18
    assert all(q.im.sha((q.ROOT/x['path']).read_bytes())==x['sha256'] for x in p['files'])
    assert (s/'goal-status-before.json').read_bytes()==(q.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    fifo_path=s/'run-generic-log-decoder-20261026/buffer-record-fifo-results.json'
    fifo=json.loads(fifo_path.read_text())
    assert fifo['source_receipt']['script_sha256']==q.im.sha((s/'buffer_record_fifo.py').read_bytes())
    assert (fifo_path.parent/'executed-source.py').read_bytes()==(s/'buffer_record_fifo.py').read_bytes()
    assert len(fifo['cases'])==2 and fifo['bounded_fragments']==56
    for case in fifo['cases']:
        phases(case)
        assert len(case['events'])==28
        assert case['dequeued_in_original_FIFO_order']==case['declared_records']
        assert case['initial']['count']==case['initial']['head']==case['initial']['tail']==0
        assert [case['full'][k] for k in ('count','head','tail')]==[8,0,0]
        assert [case['wrapped'][k] for k in ('count','head','tail')]==[8,3,3]
        assert [case['empty'][k] for k in ('count','head','tail')]==[0,3,3]
        assert case['logical_empty_retains_old_slot_bytes'] and case['data_words_are_unmapped_numeric_fixtures_not_verified_buffers']
        assert [x['format'] for x in case['original_logger_raw_calls']]==['roi_map_queue empty','roi_map_queue full','roi_map_queue empty']
        assert all(x['generic_raw_observation_not_matcher_signature'] for x in case['original_logger_raw_calls'])
        assert not case['formatter_entries'] and not case['real_allocation_deallocation_pointer_validation_ownership_or_transport_executed']
        for e in case['events'][3:]:
            assert e['reason']=='returned' and e['expected_result'] in (0,1)
            if e['expected_result']==1:assert e['queue_before']==e['queue_after']['raw144_hex']
    hpath=s/'run-handoff-20261026/handoff-tail-results.json';handoff=json.loads(hpath.read_text())
    assert handoff['source_receipt']['script_sha256']==q.im.sha((s/'handoff_tail.py').read_bytes())
    assert handoff['source_receipt']['queue_helper_sha256']==q.im.sha((s/'buffer_record_fifo.py').read_bytes())
    assert (hpath.parent/'executed-source.py').read_bytes()==(s/'handoff_tail.py').read_bytes()
    assert len(handoff['cases'])==2 and handoff['bounded_fragments']==16
    for case in handoff['cases']:
        phases(case)
        assert case['standalone_tail_entry'] and case['only_declared_common_and_output_fields_changed']
        assert case['after_output_pointer']==case['declared_numeric_record'][0]
        assert case['after_output_second_low32']=='0x12345678'
        assert case['queue_state']['count']==0
        a=bytes.fromhex(case['after_common16_hex']);b=bytes.fromhex(case['before_common16_hex'])
        assert a[:12]==bytes(12) and a[12:]==b[12:] and a[12:]!=bytes(4)
        assert not case['original_channel_allocation_return_or_later_flag_branch_executed']
        assert not case['actual_output_consumer_completion_or_pointer_referent_access']
    blob=(q.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert q.im.sha(blob)==q.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for row in fifo['static_provenance']['rows']:
        off=int(row['row_offset'],16);raw=blob[off:off+0x90]
        assert q.im.sha(raw)==row['row_sha256'] and raw[0x8a]==row['row_plus8a']==0
    names=json.loads((s/'roi-map-name-and-backing-scope.json').read_text())
    assert names['static_only'] and names['avcam_sha256']==q.im.sha(blob)
    for row in names['diagnostic_names']:
        off=int(row['offset'],16);raw=row['ASCII'].encode()+b'\0'
        assert blob[off:off+len(raw)]==raw and q.im.sha(raw)==row['sha256_including_NUL']
    assert names['script_sha256']==q.im.sha((s/'audit_roi_scope.py').read_bytes())
    g=json.loads((s/'goal-status-before.json').read_text())
    assert g['current_user_operational_constraint']['current_scope']=='Mac offline research and reversible local preparation only'
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_ORIGINAL_FIFO_AND_INDEPENDENT_HANDOFF_SCOPE_NOT_BUFFER_OWNERSHIP',
            'prior_sealed_files_verified':18,'FIFO_cases':2,'FIFO_fragments':56,'handoff_cases':2,'handoff_fragments':16,
            'total_bounded_fragments':72,'generic_original_muted_logger_executed':True,
            'queue_raw_word_pair_not_pointer_validation':True,'FIFO_full_empty_wrap_checked':True,
            'COMMON12_clear_preserves_upper32_and_output_pointer':True,'original_roi_queue_names_verified':True,
            'stage70_boundary_name_refined_not_physical_free':True,'target_static_row_flag':0,'target_later_flag_branch_executed':False,
            'buffer_master_descriptor_and_teardown':'STATIC_ONLY_NOT_EXECUTED',
            'retained_failure':'Initial queue diagnostic was incorrectly decoded as matcher arguments; failed source/receipt retained; generic raw decoder now used without changing logger execution.',
            'current_user_operational_scope':'Mac only, no Windows/UU action this turn',
            'actual_main_recording_callback_buffer_origin_consumer_exit_or_recovery_proven':False,
            'goal_complete':False,'persistent_write_release':False}
    q.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'bounded_fragments':72,'Windows_UU_camera_operations':False,'goal_complete':False}))


if __name__=='__main__':main()
