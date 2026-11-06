#!/usr/bin/env python3
"""Review completed stage67 evidence without replaying extraction or native queries."""
from pathlib import Path
import datetime
import io
import json
import re
import sys
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    im,root=h.im,h.ROOT
    im.volume()
    prior=STAGE.parent/'stage66-native-pnp-cache-review/final-receipt.json'
    assert im.sha(prior.read_bytes())=='0369c6a18e2c319d58120b0d7467d309a45b93d340e84f9e5207c49a0eea229f'
    assert len(load(prior)['files'])==18
    for row in load(prior)['files']:
        raw=(root/row['path']).read_bytes()
        assert len(raw)==row['bytes'] and im.sha(raw)==row['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(h.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    extraction=load(STAGE/'usb-original-extraction.json')
    assert extraction['script_sha256']==im.sha((STAGE/'extract_usb_reference.py').read_bytes())
    assert len(extraction['files'])==7 and not extraction['camera_or_module_execution_mount_or_modified_firmware']
    for row in extraction['files']:
        raw=(root/row['output']).read_bytes()
        assert len(raw)==row['bytes'] and im.sha(raw)==row['sha256']
    usb=load(STAGE/'usb-inquiry-source-correlation.json')
    assert usb['script_sha256']==im.sha((STAGE/'audit_usb_inquiry.py').read_bytes())
    assert len(usb['static_inquiry_templates'])==3 and len(usb['static_pointer_aliases'])==5
    assert all(x['initial_revision']=='1.00' and x['initial_product']=='blank spaces' for x in usb['static_inquiry_templates'])
    assert all(x['static_ELF_target']=='INQUIRY_DATA_DEFAULT' for x in usb['static_pointer_aliases'])
    raw=(STAGE/'official-files/nflasha15/kmod/usbg_storage.ko').read_bytes()
    elf=ELFFile(io.BytesIO(raw))
    for row in usb['original_functions']:
        section=elf.get_section_by_name(row['section'])
        start=int(row['section_offset'],16)
        assert im.sha(section.data()[start:start+row['bytes']])==row['sha256'] and not row['executed']
        for call in row['CALL26_relocations']:
            off=int(call['offset'],16)
            assert start<=off<start+row['bytes']
            assert int.from_bytes(section.data()[off:off+4],'little')&0xfc000000==0x94000000
    public=STAGE/'from-windows-public'
    assert {p.name for p in public.iterdir()}=={'summary.txt','receipt.json','nodes.json','commands.json','private-sha256.json'}
    receipt,nodes,commands=load(public/'receipt.json'),load(public/'nodes.json'),load(public/'commands.json')['commands']
    assert receipt['task_state']=='CACHED_ONLY_COMPLETE_NO_CURRENT_MATCH'
    assert receipt['query_count']==len(commands)==1 and receipt['commands']==commands
    assert commands[0]['exit_code']==0
    assert r'USB\VID_054C&PID_0DA1' in commands[0]['command_public']
    assert r'USB\\VID_054C&PID_0DA1' not in commands[0]['command_public']
    assert receipt['root_count']==nodes['root_count']==0
    assert receipt['current_disk_candidate_count']==nodes['current_disk_candidate_count']=='UNKNOWN'
    assert receipt['binding_status']=='MISSING_CURRENT_ROOT' and not receipt['binding_unique']
    assert nodes['branch_states']['device_tree']=='NOT_RUN_NO_UNIQUE_CURRENT_ROOT'
    assert nodes['branch_states']['disk_queries']=='NOT_RUN_NO_UNIQUE_CURRENT_ROOT'
    assert not any(v for k,v in receipt['boundaries'].items() if k!='hardware_validation')
    private=load(public/'private-sha256.json')['files']
    assert len(private)==2 and all(re.fullmatch('[0-9a-f]{64}',p['sha256']) for p in private)
    source=(STAGE/'WINDOWS_PRESENCE_CROSSCHECK.txt').read_bytes()
    assert source==(STAGE/'handoff-presence/WINDOWS_PRESENCE_CROSSCHECK.txt').read_bytes()
    assert im.sha(source)=='c3a5c02b8e1f3609a49b73d7a7e47571d73d29f45780e443ce85ede3da37f078'
    report={
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer':'Same-agent original ELF/hash/relocation-field and host-produced public receipt review. No independent hardware or private raw-output review.',
        'previous18_sealed_files_and_canonical_verified':True,
        'new_original_USB_files_verified':7,
        'initial_inquiry_templates':3,'ABS64_pointer_aliases_not_extra_headers':5,
        'original_module_functions_static_only':3,
        'reported_connected_hardware_ID_filter_queries':1,'reported_exit_code':0,
        'matched_roots':0,'disk_candidate_count':'UNKNOWN_NOT_QUERIED',
        'physical_connection_inferred_from_no_match':False,
        'query_public_hardware_ID_string_has_single_backslash':True,
        'new_public_files_received':5,'UU_transfer_counter_before':49,'after_task_file_send':50,'after_public_receive':55,
        'private_raw_files_not_transferred':2,
        'crosscheck_task_file_send_verified':True,
        'user_reported_relay_submitted':True,
        'crosscheck_new_message_and_processing_observed_in_UU':True,
        'crosscheck_final_result_covered_by_this_review':False,
        'camera_interface_commands_auth_mode_driver_media_module_WBI_flash':False,
        'source7_00_exact7_02_build_or_current_runtime_driver_proven':False,
        'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',report)
    print(json.dumps(report))


if __name__=='__main__':
    main()
