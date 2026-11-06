#!/usr/bin/env python3
"""Validate immutable parent, original source and bounded gate/queue evidence."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    previous=TASK/'scene-binding-20261029';receipt=previous/'final-receipt.json'
    assert sha(receipt.read_bytes())=='8692416fe7833eff1203ed3dee90c7926a9b7dfe868cee7a3e42edc88e1e26f5'
    manifest=json.loads(receipt.read_text());assert len(manifest['files'])==18
    for row in manifest['files']:
        body=(previous/row['path']).read_bytes();assert len(body)==row['bytes'] and sha(body)==row['sha256']
    raw=image();assert sha(raw)==PIN
    scripts=list(HERE.glob('*.py'));assert len(scripts)==4
    for path in scripts:ast.parse(path.read_text(),filename=str(path))
    source=json.loads((HERE/'frame-route-source-results.json').read_text());assert source['cp_sha256']==PIN
    assert len(source['source_fragments'])==13 and len(source['direct_branch_candidates'])==33 and len(source['callback_pointer_candidates'])==1
    for row in source['source_fragments']:
        at=int(row['file_offset'],16);assert sha(raw[at:at+row['bytes']])==row['sha256'] and (HERE/row['listing']).is_file()
    for row in source['direct_branch_candidates']+source['callback_pointer_candidates']:
        at=int(row['span_file'],16);assert sha(raw[at:at+row['span_bytes']])==row['span_sha256']
    assert source['callback_pointer_candidates'][0]['value']=='0x9d3455' and source['callback_pointer_candidates'][0]['file_offset']=='0x8cb27c'
    for row in source['diagnostic_source_names']:
        at=int(row['va'],16)-BASE;body=row['value'].encode()+b'\0';assert raw[at:at+len(body)]==body and sha(body)==row['sha256']
    allocation=json.loads((HERE/'mask-acquisition-results.json').read_text());assert allocation['cp_sha256']==PIN and len(allocation['cases'])==3
    fresh,repeated,stp=allocation['cases']
    assert fresh['returned'] and fresh['return_value']==1 and fresh['original_owner_word']=='0x80000001' and fresh['nonzero_mask_ids']==[]
    assert [r['kind'] for r in fresh['resource_requests']]==[15,16] and not fresh['mask_original_writes']
    assert repeated['returned'] and repeated['return_value']==0 and repeated['nonzero_mask_ids']==[]
    assert not stp['returned'] and stp['return_value'] is None and stp['boundary']['pc']=='0x483078'
    assert stp['boundary']['registers']==['0x1','0x5','0x5000ef40','0x1a']
    assert [r['kind'] for r in stp['resource_requests']]==[15,16] and len(stp['broker_arguments'])==2
    gate=json.loads((HERE/'caller-gate-results.json').read_text());assert gate['cp_sha256']==PIN and len(gate['cases'])==7 and len(gate['registration_cases'])==1
    for row in gate['source_spans']:
        at=int(row['file_offset'],16);assert sha(raw[at:at+row['bytes']])==row['sha256']
    rows={r['case']:r for r in gate['cases']}
    for name in ['original_fresh_empty_mask','declared_mask_original_record']:
        row=rows[name];assert len(row['phases'])==2 and len(row['commands'])==1
        assert row['phases'][0]['phase']==dict(state=1,look=0,pending=0,commands=0)
        assert row['phases'][1]['phase']==dict(state=2,look=22,pending=1,commands=1)
        assert all(p['boundary']['operation']=='before_next_image_helper' and p['boundary']['pc']=='0x4285c4' for p in row['phases'])
        assert row['commands'][0][1]==22
    assert not rows['original_fresh_empty_mask']['declared_mask_resource22']
    for name in ['selected_word0_nonzero','selected_byte5_zero','selected_byte4_nonzero','prelatched']:
        row=rows[name];phase=row['phases'][0]
        assert phase['boundary']['operation']=='before_object_virtual_dispatch' and phase['latch']==1 and not row['commands']
        assert phase['entry_delta'].get('mlut_controller',0)==0
        if name=='prelatched':assert phase['entry_delta'].get('resource_checker',0)==0
        else:
            assert phase['entry_delta']['resource_checker']==1
            assert any(w['address']=='0x5100120a' and w['bytes']==1 and w['value']=='0x1' and w['pc']=='0x9d41c8' for w in row['original_latch_writes'])
    recovery=rows['failure_latch_and_original_sync_clear'];assert [p['latch'] for p in recovery['phases']]==[1,1,0]
    assert recovery['phases'][1]['entry_delta'].get('resource_checker',0)==0 and recovery['phases'][2]['entry_delta']['mlut_controller']==1
    assert any(w['value']=='0x0' and 0x558af4<=int(w['pc'],16)<0x558c30 for w in recovery['original_latch_writes'])
    packet=gate['registration_cases'][0]
    assert packet['operation']=='before_original_dispatcher' and packet['pc']=='0x44d438' and packet['dispatch_object_va']=='0x13d7dd8'
    assert packet['packet_words']==['0x9d36c1','0x0','0x9d3455','0x0','0x0'] and not packet['native_dispatch']
    attempt=json.loads((HERE/'attempts/parent-repeat-assertion.json').read_text());assert attempt['device_actions']==0 and not attempt['sealed_files_modified']
    links=[]
    for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if link.startswith('https://') or link in ['validation-results.json','final-receipt.json']:continue
        assert (HERE/link).exists(),link;links.append(link)
    result=dict(previous_checkpoint_files_verified=len(manifest['files']),previous_receipt_sha256=sha(receipt.read_bytes()),python_ast_files=len(scripts),cp_sha256=PIN,
                original_source_fragments=13,direct_branch_candidates=33,callback_pointer_candidates=1,
                case_counts=dict(allocation=3,gate_and_reset=7,callback_record=1,total=11),
                original_failure_latch_and_original_clear_verified=True,original_callback_packet_verified=True,
                repeat_allocation_not_falsely_accepted=True,stp_allocator_success_not_fabricated=True,local_links_verified=len(links),
                boundary=dict(real_resource_state=False,full_frame_or_buffers=False,real_queue_delivery=False,MAIN_pixels=False,complete_donor=False,native_target_execution=False,device_actions=0,firmware_output=False,goal_complete=False,termination_condition_met=False),
                conclusion='MLUT caller gate and registration record recovered. Empty-mask and STP-stub limits are explicit; normal frame/buffer/MAIN routing and flashability remain unproven.')
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    assert (HERE/'validation-results.json').is_file()
    print(json.dumps(result))

if __name__=='__main__':main()
