#!/usr/bin/env python3
"""Verify controller source, original-list and bounded-allocation receipts."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN

def main():
    raw=image();source=json.loads((HERE/'controller-source-results.json').read_text())
    calls=json.loads((HERE/'controller-results.json').read_text());nrv=json.loads((HERE/'nrv-acquire-results.json').read_text())
    assert source['cp_sha256']==calls['cp_sha256']==nrv['cp_sha256']==PIN
    prev=TASK/'image-lifecycle-20261029';receipt=prev/'final-receipt.json'
    pin='e28d5ae72a65d7e71f34a026569e914900ed4228edb003659228bea03ec453d4'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==source['previous_receipt_sha256']==pin
    previous=json.loads(receipt.read_text())['files']
    for f in previous:
        b=(prev/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
    for f in source['source_fragments']+calls['source_spans']+nrv['source_spans']:
        at=int(f['va'],16)-BASE;b=raw[at:at+f['bytes']];assert hashlib.sha256(b).hexdigest()==f['sha256']
        if 'listing' in f:assert (HERE/f['listing']).is_file()
    assert len(source['source_fragments'])==30 and len(source['rtti'])==3
    for r in source['rtti']:
        at=int(r['typeinfo_va'],16)-BASE;b=raw[at:at+r['bytes']];assert hashlib.sha256(b).hexdigest()==r['sha256']
        assert [hex(v[0]) for v in struct.iter_unpack('<I',b)]==r['words']
        at=int(r['name_va'],16)-BASE;b=raw[at:at+r['name_bytes']]
        assert hashlib.sha256(b).hexdigest()==r['name_sha256'] and b.decode().rstrip('\0')==r['mangled_name']
    assert len(calls['cases'])==8 and len(calls['list_lookup_cases'])==1 and len(nrv['cases'])==3
    casts=errors=0
    for r in calls['cases']:
        registered=r['case'].startswith('registered_candidate');kind=r['caller']['original_buffer_kind'];split=r['explicit_split_flag']
        assert kind in [3,4] and split in [0,1]
        assert r['explicit_object_controller_id']==(1 if registered else 0) and r['explicit_object_70_invalid_handle']
        assert not r['manager']['candidate_object_constructed']
        assert len(r['manager']['initialized']['original_free_nodes'])==16
        assert r['original_pointer_production']['fields_8d8_8dc_8e0']==['0x0','0x13c4abc','0x13c5134']
        assert len(r['original_wrapper_arguments'])==2 and r['output_entries']['controller_lookup']==2
        assert [p['phase'] for p in r['caller']['phases']]==[dict(state=1,look=0,pending=0,commands=0),dict(state=2,look=22,pending=1,commands=1)]
        for p in r['caller']['phases']:
            b=p['boundary'];assert not b['native_call'] and not b['service_reply_supplied'] and not b['cast_result_supplied']
            if registered:
                assert b['pc']=='0x4ec038' and b['registers'][0]=='0x5100b000'
                assert b['registers'][1]=='0xbadc28' and b['registers'][2]==('0xbae48c' if split else '0xbaddc8')
                assert not b['candidate_object_constructed'];casts+=1
            else:
                assert b['pc']==('0x53ce98' if kind==3 else '0x9d1b4c');errors+=1
        if not registered:assert [x['raw_r1'] for x in r['original_output_return_codes']]==[2,2]
    assert casts==8 and errors==8
    lookup=calls['list_lookup_cases'][0]
    assert lookup['matched']==dict(boundary=None,raw_r0='0x5100b000',returned=True)
    assert lookup['missing']==dict(boundary=None,raw_r0='0x0',returned=True)
    for r in nrv['cases']:
        c=r['declared_context'];entries=r['original_entries'];b=r['unreplied_boundary']
        assert entries[0]['registers']==['0x0',hex({1:0,5:4,7:6}[c]),'0x0','0x4']
        assert entries[1]['registers']==['0x117adf0','0x4af','0x1','0x0']
        assert b['pc']=='0x4a032c' and b['registers'][:2]==['0x2a','0x5'] and b['input_word']=='0x2'
        assert not b['native_call'] and not b['service_reply_supplied'] and not r['normal_controller_handle_produced']
    for f in HERE.glob('*.py'):ast.parse(f.read_text())
    attempts=list((HERE/'attempts').glob('*.json'));assert len(attempts)==2
    assert all(json.loads(f.read_text())['formal_cases']==0 for f in attempts)
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https:'):continue
        assert (HERE/target).is_file() or target in ['validation-results.json','final-receipt.json'],target
        links.append(target)
    out=dict(cp_sha256=PIN,previous_receipt_sha256=pin,previous_files_verified=len(previous),python_ast_files=len(list(HERE.glob('*.py'))),
             source_windows=30,rtti_name_and_typeinfo_records=3,case_counts=dict(caller=8,list_lookup=1,nrv_prefix=3,total=12),
             explicit_unreplied_boundaries=dict(dynamic_cast=casts,error_cleanup=errors,common_handle=3,total=19),
             original_manager_free_nodes=16,original_pointer_getter_verified=True,original_nrv_allocation_key='0x4af',local_links_verified=len(links),
             boundary=dict(native_target_execution=False,device_actions=0,cast_results_supplied=0,resource_replies_supplied=0,
                           candidate_controller_constructed=False,normal_NRV_controller_handle=False,MAIN_recording_pixels=False,
                           complete_donor_ISP=False,firmware_output=False,modified_firmware_flashable=False,goal_complete=False,termination_condition_met=False),
             conclusion='Original output wrappers select EE/SplitEE RTTI through original controller-list lookup; normal NRV resource acquisition stops before handle operation. No constructed controller, main recording, full donor transplant or modified firmware admission established.')
    (HERE/'validation-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
