#!/usr/bin/env python3
"""Check scope-matched proof and retrieved Windows public bytes, no rerun."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def leaves(obj):
    if isinstance(obj,str):yield obj
    elif isinstance(obj,dict):
        for x in obj.values():yield from leaves(x)
    elif isinstance(obj,list):
        for x in obj:yield from leaves(x)


def main():
    h.im.volume();s=STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    prior=s.parent/'stage68-current-USB-associations/final-receipt.json'
    assert h.im.sha(prior.read_bytes())=='ac0ed314014b7dce271478f3038d0cbe8b27be7ea94906886c93565524da3880'
    p=json.loads(prior.read_text());assert len(p['files'])==17
    assert all(h.im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in p['files'])
    assert (s/'goal-status-before.json').read_bytes()==(h.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    # Validate the actually reused original linker and two compiled objects.
    checked=[]
    for name in ('stage64-osal-offline-link','stage58-native-match-call-frame','stage57-native-resource-alias'):
        m=json.loads((s.parent/name/'final-receipt.json').read_text())
        for row in m['files']:
            if row['path'].endswith(('.py','.c','.inc','.a64.o')):
                assert h.im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
                checked.append(row['path'])
    run=s/'run-same-instance-slices-20261026'
    proof=json.loads((run/'channel-callpath-results.json').read_text())
    assert proof['source_receipt']['script_sha256']==h.im.sha((s/'channel_callpath.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(s/'channel_callpath.py').read_bytes()
    assert (run/'compiled-source.c').read_bytes()==(s/'channel_adapter.c').read_bytes()
    assert proof['source_receipt']['C_source_sha256']==h.im.sha((s/'channel_adapter.c').read_bytes())
    assert proof['adapter']['object_sha256']==h.im.sha((run/'channel_adapter.a64.o').read_bytes())
    assert proof['bounded_fragments']==58 and len(proof['cases'])==9
    assert len(proof['two_guest_BL_changes'])==2 and not proof['goal_complete'] and not proof['persistent_write_release']
    counts={'positive_target':0,'stock_or_artificial_control':0,'our_rejection':0};slice_count=0
    for c in proof['cases']:
        assert c['original_source_and_common_descriptor_preserved'] and not c['completion_or_rollback_notifications_synthesized']
        assert not c['actual_camera_hook_Linux_services_HAL_or_recording']
        for index,e in enumerate(c['events']):
            if index==0:
                assert e['label']=='original LIRO copy through original exported kernel memcpy'
                assert e['reason']=='boundary: after_original_kernel_memcpy_before_next_diagnostic'
                assert e['native_output_or_return_adapter'] is False
                assert int(e['SP_after'],16)%16==0
            else:
                assert e['native_output_or_PC_return_adapter'] is False
                assert int(e['SP_before'],16)%16==int(e['SP_after'],16)%16==0
            if 'same_instance_observation_slices' in e:
                slices=e['same_instance_observation_slices'];slice_count+=len(slices)
                assert sum(x['executed'] for x in slices)==len(e['pcs'])
                assert len(e['pcs'])<=e['instruction_limit']==2000000
                assert all(a['end_pc']==b['start_pc'] for a,b in zip(slices,slices[1:]))
                assert all(x['reason'] is None for x in slices[:-1])
                assert slices[-1]['reason']==e['reason']
        if c['negative']:
            counts['our_rejection']+=1
            assert len(c['our_unexecuted_rejection_entries'])==1 and not c['actual_original_channel_entries']
            assert not c['resource_messages'] and c['control_at_stop']['live']==0
        else:
            assert len(c['resource_messages'])==len(c['kernel_service_boundary'])==1
            assert c['kernel_service_boundary'][0]['names']==['_raw_spin_lock_irqsave']
            if c['target']:
                counts['positive_target']+=1
                assert c['actual_original_rate_returns'][0]['trace_target_cpb']==[25999360,16000000,26000000]
                assert len(c['actual_writer_calls_from_adapter'])==1
                assert c['control_at_stop']['phase']==c['control_at_stop']['live']==1 and c['control_at_stop']['lock']==0
            else:
                counts['stock_or_artificial_control']+=1
                assert not c['actual_writer_calls_from_adapter'] and c['control_at_stop']['live']==0
    assert counts=={'positive_target':2,'stock_or_artificial_control':2,'our_rejection':5}
    static=json.loads((s/'original-channel-failure-branch.json').read_text())
    assert static['static_only'] and static['our_rejection_boundary_is_not_original_cleanup']
    assert static['instructions'][1]['asm']=='tbnz w0, #0, #0xffffffc00121eef0'
    assert static['instructions'][15]['offset']=='0x21eef0'
    assert not static['executed_false_branch_or_actual_recovery']
    pub=s/'from-windows-root-review'
    expected={'commands.json','nodes.json','receipt.json','summary.txt','private-sha256.json','public-sha256.json'}
    assert {p.name for p in pub.iterdir()}==expected
    manifest=json.loads((pub/'public-sha256.json').read_text());assert manifest['manifest_excludes_itself']
    assert {x['relative_path'] for x in manifest['files']}==expected-{'public-sha256.json'}
    for x in manifest['files']:
        raw=(pub/x['relative_path']).read_bytes();assert len(raw)==x['bytes'] and h.im.sha(raw)==x['sha256']
    receipt=json.loads((pub/'receipt.json').read_text());nodes=json.loads((pub/'nodes.json').read_text())
    assert receipt['qualified_saved_CIM_usb_roots']==1 and receipt['new_pnputil_root_matches']==0
    assert len(receipt['commands'])==1 and receipt['commands'][0]['exit_code']==0
    assert receipt['current_disk_candidate_count']=='UNKNOWN' and receipt['uniqueness_gate_applies_to_usb_roots_not_disks']
    assert nodes['branch_states']['connected_device_tree']=='NOT_RUN_NO_CURRENT_PNPUTIL_ROOT'
    assert nodes['branch_states']['connected_disk_queries']=='NOT_RUN_NO_CURRENT_PNPUTIL_ROOT'
    assert not receipt['preflight']['reparse_network_camera_redirect'] and not receipt['preflight']['administrator_token']
    b=receipt['boundaries'];assert b['camera_commands']==b['card_media_camera_file_reads']==0
    assert not any(b[k] for k in ['CIM_query_repeated','old_hardware_id_query_repeated','new_probe_generated_or_run',
        'automatic_retry','scan_refresh','elevation','policy_driver_or_mode_change','camera_disk_volume_interface_opened',
        'authentication','module_upload','WBI_or_flash'])
    for path in pub.glob('*.json'):
        for value in leaves(json.loads(path.read_text())):
            assert not value.startswith('\\\\?\\') and not re.match(r'^(?:USB|USBSTOR)\\[^\\]+\\',value,re.I)
    task=(s/'WINDOWS_ARGUMENT_AUDIT.txt').read_bytes();assert task==(s/'handoff-argument/WINDOWS_ARGUMENT_AUDIT.txt').read_bytes()
    assert h.im.sha(task)=='1a4e1a7e8349b82adb6e020994b531ca2e9587cf0a051ae813250d1acc2f7e48'
    failures=[p.parent.name for p in s.glob('run-*/attempt-failure.json')];assert len(failures)==4
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_COMPLETED_GUEST_CALLPATH_AND_WINDOWS_PUBLIC_RECEIPT_SCOPE',
        'prior_stage68_sealed_files':17,'reused_sources_objects_verified':checked,
        'callpath_cases':counts,'bounded_fragments':58,'same_guest_observation_slices':slice_count,
        'current_source_matches_executed_source':True,'target_rate_from_original_getter':[25999360,16000000,26000000],
        'two_guest_only_BL_changes':True,'live_target_producer_lease_preserved':True,'real_rollback_or_rejection_ABI_verified':False,
        'retained_failed_runs':failures,'windows_public_files':6,'public_manifest_five_file_hashes_verified':True,
        'private_raw_files_transferred':0,'private_hashes_independently_recomputed_on_Mac':False,
        'fresh_root_query_count':1,'fresh_root_matches':0,'disk_candidate_count':'UNKNOWN_NOT_QUERIED',
        'earlier_CIM_versus_later_PnPUtil_cause':'UNKNOWN; actual argv audit pending',
        'offline_argument_task_transferred':'UU success, counter68, exact new remote filename',
        'offline_argument_task_submission':'PENDING_USER_RELAY; one new paste not visible in input, no message sent',
        'task_sha256':h.im.sha(task),'authorization_unchanged':True,'camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    h.im.write_json(out,result)
    print(json.dumps({'status':result['status'],'native_cases':counts,'windows_root_matches':0,
                      'disk_candidates':'UNKNOWN','goal_complete':False}))


if __name__=='__main__':main()
