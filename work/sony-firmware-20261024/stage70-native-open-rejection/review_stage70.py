#!/usr/bin/env python3
"""Scope-specific review: original rejection, conditional Close, file initial state."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume();s=STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    prior=s.parent/'stage69-native-16M-callpath/final-receipt.json'
    assert h.im.sha(prior.read_bytes())=='417033856d0b31e1019bd64b932199d826ebdefcc9321a96dae1334fae8c1d8e'
    p=json.loads(prior.read_text());assert len(p['files'])==50
    assert all(h.im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in p['files'])
    assert (s/'goal-status-before.json').read_bytes()==(h.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=s/'run-storage-scope-controls-20261026';r=json.loads((run/'open-rejection-results.json').read_text())
    assert r['source_receipt']['script_sha256']==h.im.sha((s/'open_rejection.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(s/'open_rejection.py').read_bytes()
    assert r['bounded_fragments']==28 and len(r['cases'])==3
    assert r['actual_Sony_failure_cleanup_complete'] is False and not r['UU_Windows_camera_operations']
    counts={'unexecuted_storage_release':0,'file_initial_conditional_local_release':0}
    for c in r['cases']:
        assert c['original_code_callsites_unchanged'] and c['FH_common_descriptor_preserved']
        assert c['matcher_return_signed']==-1 and c['common_return_sentinel']==255 and c['factory_return_u32']==0
        assert not c['private_writer_adapter_or_kernel_services_executed'] and not c['callback_or_full_cleanup_or_retry_or_recovery_executed']
        before=c['before_pending_message_callback']
        assert [before[k] for k in ('free_ID_count','free_MAIN_count','free_MAIN_map_nodes')]==[7,5,5]
        assert before['dispatcher_pending']==0 and before['first_COMMON_channel_byte']==255 and before['message_first_pointer']=='0x0'
        close=c['independent_original_Close']
        assert close['independent_entry_not_pending_message_delivery'] and close['original_Open_not_resumed_after_independent_Close']
        assert not close['callback_receipt_real_shared_lock_or_hardware_close_verified']
        assert set(close['resource_IDs_before_close'].values())=={0xffffffff}
        if c['seed'] in (0xa5,0xc3):
            counts['unexecuted_storage_release']+=1
            pattern=hex(c['seed']*0x0101010101010101)
            assert before['first_COMMON_storage_pointer']==before['first_COMMON_storage_extent_raw_u64']==pattern
            assert close['local_release_complete'] is False
            boundary=close['unexecuted_manager_storage_release']
            assert boundary['pc']=='0xffffffc00122da80' and boundary['LR']=='0xffffffc00121f730'
            assert boundary['x0_x2']==['0x11020000',pattern,pattern] and not boundary['body_executed']
            assert len(close['actual_original_close_path'])==2
        else:
            assert c['seed']==0
            counts['file_initial_conditional_local_release']+=1
            assert close['local_release_complete'] and close['conditional_on_declared_zero_storage_input']
            after=close['after_local_release']
            assert [after[k] for k in ('free_ID_count','free_MAIN_count','free_MAIN_map_nodes')]==[8,6,6]
            assert after['MAIN_tree_root']=='0x0' and after['first_COMMON_request_word']==255
            assert sorted(close['free_IDs'])==list(range(8))
            assert len(set(close['free_handlers']))==len(set(close['free_map_nodes']))==6
            assert close['post_release_lookup_return']==0 and close['second_Close_not_executed']
            assert len(close['actual_original_close_path'])==5
        for index,e in enumerate(c['events']):
            assert int(e['SP_after'],16)%16==0
            if index==0:assert e['native_output_or_return_adapter'] is False
            else:
                assert e['native_output_or_PC_return_adapter'] is False
                slices=e['same_instance_observation_slices']
                assert sum(x['executed'] for x in slices)==len(e['pcs'])<=2000000
                assert all(a['end_pc']==b['start_pc'] for a,b in zip(slices,slices[1:]))
                assert slices[-1]['reason']==e['reason']
    assert counts=={'unexecuted_storage_release':2,'file_initial_conditional_local_release':1}
    blob=(s.parent/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert h.im.sha(blob)==h.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    init=json.loads((s/'storage-file-initial-provenance.json').read_text())
    start=int(init['static_source_factory_offset'],16);size=init['factory_bytes'];raw=blob[start:start+size]
    assert start==0x562930 and size==0xa34b0 and raw==bytes(size)
    assert h.im.sha(raw)==init['factory_region_sha256']
    for row in init['static_buffer_fields']:
        at=int(row['field_offset'],16);raw=blob[at:at+row['bytes']]
        assert raw==bytes(16) and h.im.sha(raw)==row['sha256']
    static=json.loads((s/'failure-contract-static.json').read_text())
    assert static['avcam_sha256']==h.im.sha(blob) and static['static_only']
    for row in static['diagnostic_and_source_strings']:
        at=int(row['offset'],16);raw=row['ASCII'].encode()+b'\0'
        assert blob[at:at+len(raw)]==raw and h.im.sha(raw)==row['sha256']
    assert any(row['ASCII']=='[ENCHANDLER]expect enc_close.' for row in static['diagnostic_and_source_strings'])
    retained=[]
    for name in ('run-20261026','run-independent-close-20261026'):
        p=s/name;assert p.exists();retained.append(name)
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_SCOPE_LIMITED_ORIGINAL_REJECTION_CONDITIONAL_CLOSE_AND_INITIAL_FILE_BYTES',
        'previous_stage69_sealed_files_verified':50,'formal_cases':3,'bounded_fragments':28,'case_counts':counts,
        'original_firmware_callsites_pristine_during_formal_execution':True,'private16M_writer_executed':False,
        'original_message_callback_executed':False,'legitimate_retry_executed':False,'modified16M_runtime_rollback_verified':False,
        'static_factory_initial_bytes_zero':668848,'static_buffer_field_slots_verified':6,
        'file_initial_state_is_not_WBI_coldboot_or_current_owner_proof':True,
        'two_prior_runs_retained':retained,'actual_cleanup_or_recording_or_recovery_proven':False,
        'Windows_state':'User says Windows unavailable; proceed on Mac only. No further UU checks or task dispatch.',
        'Windows_argument_audit':'Prepared/transferred earlier, submission and execution not observed; deferred by user, no relay request pending for current work.',
        'authorization_unchanged':True,'goal_complete':False,'persistent_write_release':False}
    h.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'cases':counts,'fragments':28,'Windows':'deferred_Mac_only','goal_complete':False}))


if __name__=='__main__':main()
