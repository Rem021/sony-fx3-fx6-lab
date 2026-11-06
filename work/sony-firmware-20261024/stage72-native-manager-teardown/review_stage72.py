#!/usr/bin/env python3
"""Independent readback of original local-exit observations and scope."""
from pathlib import Path
import datetime
import json
import struct
import manager_teardown as t


def main():
    t.im.volume();s=t.STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    previous=t.BASE/'stage71-native-buffer-record-fifo/final-receipt.json'
    assert t.im.sha(previous.read_bytes())=='0418d0922bf7b2b6fd433009d01e6072ca20c894a114bb2378a4a71b1ebbf101'
    manifest=json.loads(previous.read_text());assert len(manifest['files'])==19
    for row in manifest['files']:
        assert t.im.sha((t.ROOT/row['path']).read_bytes())==row['sha256']
    assert (s/'goal-status-before.json').read_bytes()==(previous.parent/'goal-status-after.json').read_bytes()==(t.BASE/'GOAL_STATUS.json').read_bytes()
    p=s/'run-through-original-ret-20261026/manager-teardown-results.json'
    result=json.loads(p.read_text());source=(s/'manager_teardown.py').read_bytes()
    assert result['source_receipt']['script_sha256']==t.im.sha(source)
    assert (p.parent/'executed-source.py').read_bytes()==source
    assert result['source_receipt']['original_queue_helper_sha256']==t.im.sha((t.q.STAGE/'buffer_record_fifo.py').read_bytes())
    assert result['source_receipt']['runner_sha256']==t.im.sha((t.c.STAGE/'channel_callpath.py').read_bytes())
    assert len(result['cases'])==8 and result['bounded_fragments']==40
    expected_kinds={'sentinel_with_pending_record','zero_ID_negative_control',
                    'shared_reference_two','last_reference_one_boundary'}
    for seed in (0xa5,0xc3):
        cases=[x for x in result['cases'] if x['seed']==seed]
        assert {x['kind'] for x in cases}==expected_kinds and len(cases)==4
        for case in cases:
            assert len(case['events'])==5
            for i,e in enumerate(case['events']):
                assert int(e['SP_after'],16)%16==0
                if i==0:assert e['native_output_or_return_adapter'] is False
                else:
                    assert e['native_output_or_PC_return_adapter'] is False
                    chunks=e['same_instance_observation_slices']
                    assert sum(x['executed'] for x in chunks)==len(e['pcs'])<=2000000
                    assert all(a['end_pc']==b['start_pc'] for a,b in zip(chunks,chunks[1:]))
                    assert chunks[-1]['reason']==e['reason']
            assert case['queue_not_drained_or_modified']
            assert case['whole_arena_unchanged_except_explicit_descriptor_cache_fields']
            assert case['before']['queue']==case['after']['queue']
            assert case['after']['queue']['count']==1
            assert case['descriptor_cache_inputs_are_declared_not_successful_allocation_evidence']
            assert not case['actual_physical_free_transport_reply_or_record_referent_access']
            observations=case['original_function_observations']
            logs=[x['format'] for x in case['original_logger_raw_calls']]
            assert logs[0]=="didn't return all RIO_MAP queue elements qsize:%d"
            assert all(x['generic_raw_observation_not_matcher_signature'] for x in case['original_logger_raw_calls'])
            kind=case['kind'];last=case['events'][-1]
            if kind=='sentinel_with_pending_record':
                assert last['reason']=='returned' and last['x0_after']=='0x0'
                assert case['before']==case['after'] and not observations
            elif kind=='zero_ID_negative_control':
                assert last['reason']=='returned' and last['x0_after']=='0x0'
                assert case['before']['master_ID']=='0x0' and case['after']['master_ID']=='0xffffffff'
                helper=[x for x in observations if x['pc']==hex(t.V+0x22dbb4)][0]
                assert helper['x0_x3'][0]=='0x1'
                assert helper['state']['master_descriptor_hex']==case['before']['master_descriptor_hex']
                assert any(x['pc']==hex(t.V+0x27c28c) for x in observations)
                assert 'free_unit error err:0x%X\n' in logs and 'destroy mem pool error vcd_sw:%d' in logs
            elif kind=='shared_reference_two':
                assert last['reason']=='returned' and last['x0_after']=='0x0'
                assert case['before']['first_cache_reference_count']==2 and case['after']['first_cache_reference_count']==1
                assert case['after']['first_cache_ID']=='0x12345' and case['after']['master_ID']=='0xffffffff'
                assert not any(x['pc']==hex(t.UNIT) for x in observations)
            else:
                assert last['reason']=='boundary: before_original_unit_free_request_no_transport_executed'
                assert last['stop_pc']==hex(t.UNIT)
                assert case['before']['first_cache_reference_count']==1 and case['after']['first_cache_reference_count']==0
                assert case['after']['first_cache_ID']=='0xffffffff'
                assert case['before']['master_descriptor_hex']==case['after']['master_descriptor_hex']
                unit=[x for x in observations if x['pc']==hex(t.UNIT)][0]
                assert unit['x0_x3'][1:3]==['0x2','0x806800f3']
            # No observed transport entry is hidden in a function's trace.
            assert all(hex(t.TRANSPORT) not in e.get('pcs',[]) for e in case['events'])
    blob=(t.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert t.im.sha(blob)==result['source_receipt']['avcam_sha256']==t.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for row in result['static_scope']['original_strings']:
        at=int(row['offset'],16);raw=row['ASCII'].encode()+b'\0'
        assert blob[at:at+len(raw)]==raw and t.im.sha(raw)==row['sha256_including_NUL']
    regions=result['static_scope']['regions']
    for row in regions:
        assert row['instructions']==t.im.dump(blob,int(row['start'],16),int(row['end'],16),t.V)
    # Check the exact original field-copy correspondence without executing any
    # synchronization, address translation, submission or fabricated reply.
    checks={0x21e7ac:'add x8, sp, #0x78',0x21e7b4:'add x21, x8, #0x18',
            0x21ea04:'add x0, sp, #0x28',0x21ea08:'mov w2, #0x50',
            0x21ea0c:'mov x1, x21',0x21ea10:'add x21, sp, #0x28',
            0x21ea14:'bl #0xffffffc001000d80',0x21ea38:'stp x29, x21, [sp, #8]',
            0x21ea40:'bl #0xffffffc00126adbc',0x26adbc:'sub sp, sp, #0x70',
            0x26addc:'ldr x19, [sp, #0x80]',0x26aff8:'ldr x8, [x19, #0x40]',
            0x26b074:'str x8, [x19, #0x40]',0x26b0d0:'add x0, x20, #0x28',
            0x26b0dc:'mov w2, #0x50',0x26b0e0:'mov x1, x19',
            0x26b0e4:'bl #0xffffffc001000d80',0x26b0ec:'mov x1, x20',
            0x26b0f0:'bl #0xffffffc00127470c',0x27c2b0:'ret '}
    for at,asm in checks.items():assert t.im.dump(blob,at,at+4,t.V)[0]['asm']==asm,(hex(at),asm)
    assert 0x58-0x18==0x40 and 0x28+0x40==0x68 and 0x60-0x18+0x28==0x70
    # The retained first attempt was a fixture allow-range boundary error at
    # the native ret, not a camera/firmware failure or passing result.
    failed=s/'run-20261026'
    first_source=(failed/'attempt-source.py').read_bytes()
    assert first_source==source.replace(b'(UNIT,V+0x27c2b4)',b'(UNIT,V+0x27c2b0)').replace(
        b'(0x27c1a8,0x27c2b4)',b'(0x27c1a8,0x27c2b0)')
    failure=json.loads((failed/'failure-state.json').read_text())
    assert failure['pc']==hex(t.V+0x27c2b0) and failure['reason']=='unapproved execution '+hex(t.V+0x27c2b0)
    assert not json.loads((failed/'attempt-failure.json').read_text())['passing_result']
    assert not (failed/'manager-teardown-results.json').exists()
    g=json.loads((s/'goal-status-before.json').read_text())
    assert g['current_user_operational_constraint']['current_scope']=='Mac offline research and reversible local preparation only'
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_ORIGINAL_LOCAL_EXIT_AND_STATIC_REQUEST_REFERENCE_SCOPE',
        'prior_sealed_files_verified':19,'cases':8,'total_bounded_fragments':40,
        'pending_ROI_record_unchanged_in_all_cases':True,
        'zero_ID_negative_control_original_helper_error_master_clear_outer_return0':True,
        'reference2_to1_retains_cache_skips_unit_free':True,
        'reference1_to0_cache_clear_before_unexecuted_request_master_still_live':True,
        'static_output58_to_request68_and_output60_to_request70_checked':True,
        'static_reference_translation_or_request_submission_executed':False,
        'Sony_code_patches_native_return_or_reply_adapters':False,
        'first_attempt_retained':'Guest allow-range excluded original27c2b0 ret; only the two end bounds extended4 bytes; rerun then passed. Not a firmware or camera failure.',
        'declared_fixtures_are_not_successful_allocation_or_actual_owner_proof':True,
        'physical_release_completed_consumers_main_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    t.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'cases':8,'bounded_fragments':40,'Mac_only':True}))


if __name__=='__main__':main()
