#!/usr/bin/env python3
"""Validate source pins, lifecycle receipts, declared boundaries and local links."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN

def main():
    raw=image();source=json.loads((HERE/'lifecycle-source-results.json').read_text())
    results=json.loads((HERE/'registry-results.json').read_text());rows=results['cases']
    assert source['cp_sha256']==results['cp_sha256']==PIN
    previous=TASK/'stp-buffer-20261029';receipt=previous/'final-receipt.json'
    pin='7bde51a229f4915d542756ff348a07b1eb6cc8a07a61b34a7a433967b5166ea9'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==source['previous_receipt_sha256']==pin
    files=json.loads(receipt.read_text())['files']
    for f in files:
        b=(previous/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
    for f in source['source_fragments']+source['config_tables']+results['source_spans']:
        a=int(f['va'],16)-BASE;b=raw[a:a+f['bytes']]
        assert hashlib.sha256(b).hexdigest()==f['sha256']
        if 'listing' in f:assert (HERE/f['listing']).is_file()
        if 'words' in f:assert list(struct.unpack('<4I',b))==f['words']
    assert len(source['source_fragments'])==15 and len(source['config_tables'])==2
    assert len(rows)==13 and len({r['case'] for r in rows})==13
    by={r['case']:r for r in rows}
    init=by['original_registry_constructor_240_records']['result']
    assert init['original_initialized_records']==240 and init['record_bytes']==0x88 and init['untouched_padding_preserved']
    assert init['boundary']['pc']=='0x5579d4'
    for label in ['future_frame_kept','upper_marker_keeps_descriptor','expired_owned_descriptor_stops_before_release']:
        r=by[label];assert r['record_before']==r['record_after']
    cleared=bytes.fromhex(by['expired_borrowed_descriptor']['record_after'])
    assert cleared[:4]==b'\xff'*4 and cleared[0x10:0x50]==b'\0'*0x40
    assert by['expired_owned_descriptor_stops_before_release']['result']['boundary']['pc']=='0x44de7c'
    assert by['empty_descriptor_cleanup_noop']['entries'].get('descriptor_release_or_clear',0)==0
    for label in ['cached_440_passes_original_payload','cached_614_passes_original_payload']:
        r=by[label];assert r['declared_descriptor_fixture']['owned_byte']==1
        assert not r['declared_descriptor_fixture']['plane_memory_mapped']
        for t in r['temporary_cleanup_inputs']:assert t['owned_byte']==0 and t['handle']=='0x12345678'
        assert len(r['temporary_cleanup_inputs'])==2
        for phase in r['caller']['phases']:
            b=phase['boundary'];assert b['pc']=='0x428f0c'
            assert [b['argument2_selected_fields'][key] for key in ['0x28','0x2c','0x30']]==['0x52000100','0x12340','0x56780']
    boundary_count=0
    for row in rows:
        all_boundaries=[]
        result=row.get('result',{})
        if result.get('boundary'):all_boundaries.append(result['boundary'])
        caller=row.get('caller')
        if caller:
            assert [p['phase'] for p in caller['phases']]==[dict(state=1,look=0,pending=0,commands=0),dict(state=2,look=22,pending=1,commands=1)]
            all_boundaries.extend(p['boundary'] for p in caller['phases'])
        for b in all_boundaries:
            assert not b['native_call'] and not b['service_reply_supplied'];boundary_count+=1
    assert boundary_count==16
    for label in ['fresh_entry_stops_at_handle_operation','cached_status_pending_stops_at_handle_operation','mismatched_key_borrowed_clears_then_acquires']:
        for phase in by[label]['caller']['phases']:
            b=phase['boundary'];assert b['pc']=='0x4a032c' and b['registers'][:2]==['0x2a','0x5'] and b['request_input_word']=='0x2'
    attempt=json.loads((HERE/'attempts/payload-offset-assertion.json').read_text())
    assert attempt['formal_cases']==0 and attempt['debug_observations']==1
    python_files=list(HERE.glob('*.py'))
    for path in python_files:ast.parse(path.read_text())
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https:'):continue
        path=HERE/target;assert path.is_file() or target in ['final-receipt.json','validation-results.json'],target
        links.append(target)
    out=dict(cp_sha256=PIN,previous_files_verified=len(files),previous_receipt_sha256=pin,python_ast_files=len(python_files),
             source_windows=15,config_tables=2,case_counts=dict(registry_initialization=1,threshold_cleanup=5,caller_handoff=7,total=13),
             constructor_records_verified=240,unreplied_boundaries_verified=boundary_count,local_links_verified=len(links),
             corrected_frame_query_interpretation=True,original_copied_descriptor_ownership_cleared=True,
             boundary=dict(native_target_execution=False,device_actions=0,service_replies=0,real_pixel_buffers=False,
                           normal_MAIN_pixels=False,full_donor_ISP=False,firmware_output=False,modified_firmware_flashable=False,
                           goal_complete=False,termination_condition_met=False),
             conclusion='Original registry construction, frame-threshold cleanup, cached-descriptor handoff and unreplied handle boundaries verified. Full colour transplant and normal modified firmware admission remain unproven.')
    (HERE/'validation-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))

if __name__=='__main__':main()
