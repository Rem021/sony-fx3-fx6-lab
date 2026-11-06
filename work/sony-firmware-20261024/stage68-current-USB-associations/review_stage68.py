#!/usr/bin/env python3
"""Review retrieved public cache evidence and bounded original-code result."""
from pathlib import Path
import datetime
import json
import re
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def strings(obj):
    if isinstance(obj,str):yield obj
    elif isinstance(obj,dict):
        for v in obj.values():yield from strings(v)
    elif isinstance(obj,list):
        for v in obj:yield from strings(v)


def main():
    h.im.volume();out=STAGE/'completed-evidence-review.json';assert not out.exists()
    old=STAGE.parent/'stage67-connected-native-pnp'
    prior=json.loads((old/'final-receipt.json').read_text())
    assert h.im.sha((old/'final-receipt.json').read_bytes())=='74a63d7ac2cbb7167c5b11c53f5a54e0e3b57447d1d17b4455b6e1f20f59bd8a'
    assert len(prior['files'])==27
    assert all(h.im.sha((h.ROOT/r['path']).read_bytes())==r['sha256'] for r in prior['files'])
    assert (STAGE/'goal-status-before.json').read_bytes()==(old/'goal-status-after.json').read_bytes()==(h.BASE/'GOAL_STATUS.json').read_bytes()
    pub=STAGE/'from-windows-presence'
    expected={'summary.txt','receipt.json','nodes.json','commands.json','private-sha256.json'}
    assert {x.name for x in pub.iterdir()}==expected
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':h.im.sha(p.read_bytes())} for p in sorted(pub.iterdir())]
    receipt=json.loads((pub/'receipt.json').read_text());nodes=json.loads((pub/'nodes.json').read_text())
    commands=json.loads((pub/'commands.json').read_text())['commands']
    assert receipt['command_count']==len(commands)==1 and commands==receipt['commands']
    assert commands[0]['exit_code']==0 and commands[0]['started_utc']<commands[0]['finished_utc']
    assert receipt['preflight']['system_C_local_fixed_NTFS'] and receipt['preflight']['ordinary_directory']
    assert not receipt['preflight']['reparse_network_camera_redirect'] and not receipt['preflight']['administrator_token']
    assert receipt['actual_usb_vid_pid']['vid']=='054C' and receipt['actual_usb_vid_pid']['pid']=='0DA1'
    root=nodes['prior_identity_matched_usb_nodes'];disks=nodes['explicit_model_camera_nodes']
    assert len(root)==1 and len(disks)==3 and not nodes['limit_reached']
    assert root[0]['node_sha256']=='1ce16c7e029a23fb1890f095ea738228e16e35118558aa6f47175660344d14dd'
    assert root[0]['same_as_old_fx3_root'] and root[0]['service']=='USBSTOR'
    for row in root+disks:
        assert row['present'] is True and row['status']=='OK' and row['config_manager_error_code']==0
    assert len({d['node_sha256'] for d in disks})==3
    assert all(d['service']=='disk' and d['name']=='Sony DSC USB Device' for d in disks)
    assert receipt['pnputil_branch']['queries_issued']==0
    assert nodes['started_status'].startswith('UNKNOWN') and nodes['interface_enable_state']=='UNKNOWN'
    assert nodes['driver_inf']=='UNKNOWN' and nodes['physical_camera_count']=='UNKNOWN'
    b=receipt['boundaries']
    assert b['cached_pnp_only'] and b['interface_handles_opened']==b['camera_commands']==b['card_or_media_or_camera_file_reads']==0
    assert not any(b[x] for x in ['authentication','mode_or_driver_or_policy_change','elevation','scan_or_refresh',
                                  'automatic_retry','probe_generation_or_execution','module_upload','WBI_or_flash'])
    for p in pub.glob('*.json'):
        for value in strings(json.loads(p.read_text())):
            assert not value.startswith('\\\\?\\')
            assert not re.match(r'^(?:USB|USBSTOR)\\[^\\]+\\',value,re.I),p.name
    private=json.loads((pub/'private-sha256.json').read_text())
    assert len(private['files'])==2 and receipt['private_files_not_uploaded']
    assert not any(p.name=='01-sony-camera-cache.private.json' for p in STAGE.rglob('*'))
    task=(STAGE/'WINDOWS_ROOT_CLARIFICATION.txt').read_bytes()
    assert task==(STAGE/'handoff-root/WINDOWS_ROOT_CLARIFICATION.txt').read_bytes()
    assert h.im.sha(task)=='172b2402dfd8eb73f7c728f65d1a2e91c68be580e9a37dd56f9e9c159c3b03e0'
    em=json.loads((STAGE/'inquiry-handler-emulation.json').read_text())
    assert em['script_sha256']==h.im.sha((STAGE/'emulate_standard_inquiry.py').read_bytes())
    assert em['case_count']==len(em['cases'])==40 and em['status_counts']=={'0':21,'2':16,'1':3}
    assert all(c['RAM_guards_passed'] for c in em['cases']) and em['actual_memcpy_body_used'] and not em['return_or_memcpy_adapter']
    assert not em['camera_handles_commands_media_auth_modes_modules_WBI_flash'] and not em['Windows_device_control']
    assert not em['goal_complete'] and not em['persistent_write_release']
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_COMPLETED_PUBLIC_CACHE_AND_BOUNDED_OFFLINE_HANDLER_SCOPE',
            'previous_sealed_files_verified':27,'canonical_unchanged_before_finalize':True,'received_public_files':files,
            'current_CIM_query_count':1,'current_CIM_USB_roots_matching_prior_identity':1,'current_CIM_Sony_DSC_disk_nodes':3,
            'all_four_present_OK_error0':True,'CIM_parent_interface_started_driver_fields':'UNKNOWN_NOT_QUERIED',
            'earlier_PnPUtil_difference_cause':'UNKNOWN; retain both times/snapshots',
            'PnPUtil_followup_in_presence_task':0,'raw_private_files_transferred':0,
            'private_hashes_are_Windows_reported_not_independently_recomputed':True,
            'public_raw_instance_or_interface_path_check':'PASS_FOR_RETRIEVED_JSON',
            'root_clarification_source_sha256':h.im.sha(task),'root_clarification_transfer':'UU showed filename, ordinary C destination, sent success, counter61',
            'root_clarification_submission':'PENDING_USER_RELAY; no new user bubble observed at latest UI check',
            'root_clarification_is_not_active_interface_selection':True,'root_clarification_result':'NOT_RETRIEVED_NOT_CLAIMED',
            'original_handler_RAM_cases':40,'original_memcpy_body_used':True,'Windows_or_camera_protocol_validation':False,
            'authorization_unchanged':True,'goal_complete':False,'persistent_write_release':False}
    h.im.write_json(out,result)
    print(json.dumps({'status':result['status'],'current_root_count':1,'current_disk_node_count':3,
                      'offline_handler_cases':40,'root_followup':'pending_user_relay','camera_operations':False}))


if __name__=='__main__':main()
