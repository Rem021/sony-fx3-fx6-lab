#!/usr/bin/env python3
"""Verify sources, strict no-register-read boundary, query producers and full domain."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN
def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
    previous=TASK/'frame-route-20261029';receipt=previous/'final-receipt.json'
    assert sha(receipt.read_bytes())=='ab686ac5273122b91557a076c7e382ecfd41cb581599e321e8fcd52ed70e2539'
    manifest=json.loads(receipt.read_text());assert len(manifest['files'])==23
    for row in manifest['files']:
        raw=(previous/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    raw=image();assert sha(raw)==PIN
    scripts=list(HERE.glob('*.py'));assert len(scripts)==5
    for p in scripts:ast.parse(p.read_text(),filename=str(p))
    source=json.loads((HERE/'stp-buffer-source-results.json').read_text());assert source['cp_sha256']==PIN
    assert len(source['source_fragments'])==17 and len(source['switch_tables'])==3 and len(source['field_15d8_candidates'])==52
    for row in source['source_fragments']:
        at=int(row['file_offset'],16);assert sha(raw[at:at+row['bytes']])==row['sha256'] and (HERE/row['listing']).is_file()
    for row in source['switch_tables']:
        at=int(row['va'],16)-BASE;assert sha(raw[at:at+row['bytes']])==row['sha256']
    assert source['switch_tables'][0]['selected_targets']=={'0x22':'0x474306','0x23':'0x474316','0x24':'0x474326','0x25':'0x474336'}
    stp=json.loads((HERE/'stp-prefix-results.json').read_text());assert stp['cp_sha256']==PIN and len(stp['cases'])==3
    for row in stp['source_spans']:
        at=int(row['file_offset'],16);assert sha(raw[at:at+row['bytes']])==row['sha256']
    before,free,busy=stp['cases']
    assert before['boundary']['operation']=='before_original_lock_wait' and not before['original_stp_global_writes']
    assert free['boundary']==dict(operation='before_first_fixed_register_read',pc='0x474306',address='0xf5410828',bytes=4,address_mapped_in_guest=False,register_value_supplied=False,native_read=False)
    assert free['stp_output_at_boundary']=='0x50001' and not free['original_stp_return_values'] and free['return_value'] is None
    writes=free['original_stp_global_writes']
    assert writes==[dict(address='0x1491214',bytes=4,value='0x50001',pc='0x48316e'),dict(address='0x1491224',bytes=4,value='0xff00',pc='0x4831a2')]
    assert free['stp_adapter_events']==[dict(adapter='declared RAM lock wait',result=0)]
    assert busy['returned'] and busy['return_value']==0 and busy['original_stp_return_values']==['0xffffffff']
    assert busy['stp_adapter_events']==[dict(adapter='declared RAM lock wait',result=0),dict(adapter='declared RAM lock release',result=0)]
    assert all(int(w['address'],16)<0x1491214 for w in busy['original_stp_global_writes'])
    query=json.loads((HERE/'buffer-query-results.json').read_text());assert query['cp_sha256']==PIN and len(query['cases'])==4
    for row in query['source_spans']:
        at=int(row['file_offset'],16);assert sha(raw[at:at+row['bytes']])==row['sha256']
    cases=query['cases'];assert [r['original_buffer_kind'] for r in cases]==[1,4,4,3]
    expected=[('0x9cecb8',['0x3','0x204','0x0']),('0x403a78',['0x3','0x440','0x0']),('0x403a78',['0x3','0x614','0x0']),('0x429a0c',['0x51000000','0x51001248'])]
    for row,(target,args) in zip(cases,expected):
        assert row['original_record_mode']==row['declared_mode'] and row['original_bss_parameter_pointer']=='0x51004de0'
        assert any(w['offset']=='0xc' and w['value']=='0x51004de0' and w['pc']=='0x9d7226' for w in row['original_bss_vector_writes'])
        writes=row['original_producer_writes']
        assert any(w['offset']=='0x4b0' and w['value']==row['declared_mode'] and w['pc']=='0x40824e' for w in writes)
        assert any(w['offset']=='0x440' and int(w['value'],16)==row['declared_parameter_968'] and w['pc']=='0x408286' for w in writes)
        kind_writes=[w for w in writes if w['offset']=='0x15d8'];assert len(kind_writes)==1
        assert kind_writes[0]['value']==hex(row['original_buffer_kind']) and kind_writes[0]['pc'] in ['0x40b760','0x40f06a','0x40b196']
        assert len(row['commands'])==1 and row['commands'][0][1]==22
        assert [p['phase']['commands'] for p in row['phases']]==[0,1]
        for phase in row['phases']:
            boundary=phase['boundary'];assert boundary['pc']==target and boundary['registers'][:len(args)]==args
            assert not boundary['query_result_supplied'] and not boundary['native_call']
    domain=json.loads((HERE/'mode-default-domain-results.json').read_text());assert domain['cp_sha256']==PIN
    assert domain['input_domain']==dict(lower=0,upper=65535,count=65536) and domain['output_word4_histogram']=={'0':65536}
    assert domain['return_histogram']=={'1':40,'0':65496} or domain['return_histogram']=={'0':65496,'1':40}
    assert len(domain['supported_inputs'])==40 and len({r['input'] for r in domain['supported_inputs']})==40
    assert all(r['output_word4']==0 for r in domain['supported_inputs']) and domain['original_instructions']==1601033
    assert domain['source']['sha256']==sha(raw[0x149fa4:0x14a17e]) and domain['source']['bytes']==0x1da
    attempt=json.loads((HERE/'attempts/mode-kind-expectation.json').read_text());assert len(attempt['observations'])==3
    assert all(r['original_buffer_kind']==1 for r in attempt['observations'])
    links=[]
    for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if link.startswith('https://') or link in ['validation-results.json','final-receipt.json']:continue
        assert (HERE/link).exists(),link;links.append(link)
    result=dict(previous_files_verified=len(manifest['files']),previous_receipt_sha256=sha(receipt.read_bytes()),python_ast_files=len(scripts),cp_sha256=PIN,
                original_source_fragments=17,switch_tables_verified=3,field_candidates=52,
                case_counts=dict(STP=3,image_query=4,uint16_domain=1,total=8),uint16_samples=65536,recognized_uint16_modes=40,
                original_stp_handle_and_exact_register_boundary_verified=True,register_value_or_STP_success_fabricated=False,
                original_mode_and_query_producers_verified=True,actual_getter_bss_vector_initialized_by_original_code=True,
                incorrect_type2_expectation_preserved_and_corrected=True,local_links_verified=len(links),
                boundary=dict(physical_register_reads=0,device_actions=0,native_target_execution=False,full_STP_completion=False,real_buffers=False,MAIN_pixels=False,complete_donor_ISP=False,firmware_output=False,goal_complete=False,termination_condition_met=False),
                conclusion='Strict STP prefix stops before unmapped fixed-register read. Independent original query windows reach unreplied image/frame queries; normal modes, resources, pixels and modified firmware flashability remain unproven.')
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n');assert (HERE/'validation-results.json').is_file()
    print(json.dumps(result))

if __name__=='__main__':main()
