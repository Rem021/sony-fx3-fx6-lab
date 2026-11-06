#!/usr/bin/env python3
"""Verify original workspace use and bounds of the relocated trial copy."""
from pathlib import Path
import datetime
import json
import struct
import private_storage as p


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
    p.im.volume();s=p.STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    prior=p.t.STAGE/'final-receipt.json'
    assert p.im.sha(prior.read_bytes())=='97807cfbfd33a2cedb88a71e579dec44b4b40264e66fdb63ab39502e91621a13'
    j=json.loads(prior.read_text());assert len(j['files'])==21
    for x in j['files']:assert p.im.sha((p.ROOT/x['path']).read_bytes())==x['sha256']
    assert (s/'goal-status-before.json').read_bytes()==(p.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    root=s/'run-20261026';r=json.loads((root/'private-storage-results.json').read_text())
    assert r['source_receipt']['script_sha256']==p.im.sha((s/'private_storage.py').read_bytes())
    assert (root/'executed-source.py').read_bytes()==(s/'private_storage.py').read_bytes()
    old=(p.c.old.STAGE/'resource_alias.c').read_bytes();new=(s/'resource_alias.c').read_bytes()
    assert new==old.replace(b'u8 *copy=o+0xe010;',
        b'u8 *copy=(u8*)0x113a1000ULL; /* dedicated single-controller guest trial storage */').replace(
        b'if (!c || c->magic!=MAGIC) return BAD_ABI;',
        b'if (!c || (u64)c!=0x113a0000ULL || c->magic!=MAGIC) return BAD_ABI;')
    assert (s/'channel_adapter.c').read_bytes()==(p.t.STAGE/'channel_adapter.c').read_bytes()
    for name in ('resource_alias.c','channel_adapter.c'):
        assert (root/('compiled-'+name)).read_bytes()==(s/name).read_bytes()
    for c in json.loads((root/'compile-receipts.json').read_text()):assert c['returncode']==0 and not c['stderr']
    assert len(r['targets'])==len(r['independent_native_workspace_cases'])==len(r['regression_controls'])==2
    assert r['bounded_fragments']==37
    for case in r['targets']:
        phases(case);assert len(case['events'])==8
        assert case['original_common_workspace_before_hex']==case['original_common_workspace_after_hex']
        assert case['original_common_workspace_untouched'] and case['entire_other_common_unchanged']
        a=bytes.fromhex(case['guards_before_hex']);z=bytes.fromhex(case['guards_after_hex'])
        assert a[:64]==z[:64] and a[-64:]==z[-64:]
        query=case['original_query_frame_proof']
        assert query['container_bytes']==56 and query['original_result_written_span_bytes']==52
        assert query['saved_LR_unchanged'] and query['full_frame_outside_container_unchanged']
        assert all(x['unchanged'] for x in query['saved_register_slots']) and not query['stores_outside_declared_container']
        assert query['decoded_trace_target_CPB']==[25999360,16000000,26000000]
        assert case['dedicated_guest_buffer']=='0x113a1000' and case['control_at_stop']['live']==1
        assert case['kernel_service_boundary'][0]['names']==['_raw_spin_lock_irqsave']
        assert not case['real_camera_owned_allocation_shared_lock_consumers_or_recording']
        assert len(case['channel_entry_observations'])==2 and case['channel_entry_observations'][0]==case['channel_entry_observations'][1]
        assert not any(p.NATIVE_WORKSPACE<=int(x['address'],16)<p.NATIVE_WORKSPACE+256 for x in case['compiled_writer_stores'])
    for case in r['independent_native_workspace_cases']:
        phases(case);assert len(case['events'])==4
        assert case['original_workspace_before_hex']!=case['original_workspace_after_hex']
        assert case['original_selected_pointer']==hex(p.NATIVE_WORKSPACE)
        assert case['dedicated_guest_buffer_and_controller_unchanged'] and case['source_descriptor_unchanged']
        assert case['independent_entry_not_target_natural_path']
        assert not case['runtime_concurrency_mutual_exclusion_or_actual_target_mode_interference_proven']
    for case in r['regression_controls']:
        phases(case)
        assert not case['actual_original_rate_calls']
        assert not any(p.PRIVATE<=int(x['address'],16)<p.PRIVATE+256 for x in case['writer_native_stores'])
    guard=json.loads((s/'controller-identity-result.json').read_text());phases(guard)
    assert guard['script_sha256']==p.im.sha((s/'controller_guard.py').read_bytes())
    assert guard['writer_object_sha256']==p.im.sha((root/'resource_alias.a64.o').read_bytes())
    assert guard['result']==1 and guard['entire_arena_unchanged'] and guard['bounded_fragments']==3
    assert all(p.r.STACK<=int(x['address'],16)<p.r.STACK+p.r.STACK_SIZE for x in guard['data_reads'])
    blob=(p.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert p.im.sha(blob)==r['source_receipt']['avcam_sha256']==p.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for region in r['original_regions']:
        assert region['instructions']==p.im.dump(blob,int(region['start'],16),int(region['end'],16),p.V)
    checks={0x22639c:'mov w8, #0xe010',0x2263a0:'add x20, x19, x8',
            0x2263ac:'mov w2, #0x100',0x2263b4:'bl #0xffffffc00127da84',
            0x226384:'add x21, x19, #0xe, lsl #12',0x226394:'str xzr, [x21]',
            0x2265c0:'str x20, [x21]',0x21ebb8:'bl #0xffffffc001226364'}
    for at,asm in checks.items():assert p.im.dump(blob,at,at+4,p.V)[0]['asm']==asm
    label=0x43d228;text='[ENCHANDLER]create_imola_enc_start_param() stream_type... err'
    assert blob[label:blob.index(b'\0',label,label+150)].decode()==text
    audit={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'native_workspace':{'offset':hex(0xe010),'length':256,'native_function':hex(0x226364),
            'original_copy_source_offset':hex(0x3d8798),'original_copy_source_sha256':p.im.sha(blob[0x3d8798:0x3d8898]),
            'original_direct_callsite':hex(0x21ebb8),'original_diagnostic':text},
        'important_remaining_shared_state':'Moving the copy does not protect COMMON+e000 selected pointer. Original function clears/replaces it; runtime exclusion, config epoch and all consumers still require proof.',
        'independent_native_entry_is_not_actual_target_mode_or_concurrency_proof':True,
        'dedicated_slot_is_harness_storage_not_a_camera_allocation':True,
        'single_controller_identity':'113a0000; wrong controller rejected before dereference',
        'goal_complete':False,'persistent_write_release':False}
    p.im.write_json(s/'native-workspace-and-shared-selection-audit.json',audit)
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_ORIGINAL_WORKSPACE_USE_AND_SEPARATED_GUEST_COPY',
        'prior_sealed_files_verified':21,'target_cases':2,'native_workspace_cases':2,'regression_controls':2,
        'controller_guard_cases':1,'total_bounded_fragments':40,
        'original_workspace_not_exclusive_scratch':True,'actual_target_natural_collision_proven':False,
        'guest_target_workspace_other_owner_and_guards_unchanged':True,
        'fixed56_result_ABI_retained_saved_slots_preserved':True,
        'single_controller_guard_rejects_before_dereference':True,
        'COMMONe000_selected_pointer_original_writers_still_require_synchronization':True,
        'actual_owned_allocation_shared_lock_completed_consumers_main_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    p.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'bounded_fragments':40,'actual_camera_allocation_proven':False}))


if __name__=='__main__':main()
