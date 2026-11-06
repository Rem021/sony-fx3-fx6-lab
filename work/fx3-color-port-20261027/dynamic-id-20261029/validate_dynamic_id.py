#!/usr/bin/env python3
"""Check original dynamic-ID source pins and bounded evidence, not device acceptance."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN

def main():
    raw=image();source=json.loads((HERE/'dynamic-id-source-results.json').read_text())
    result=json.loads((HERE/'dynamic-id-results.json').read_text());rows=result['cases'];by={r['case']:r for r in rows}
    assert source['cp_sha256']==result['cp_sha256']==PIN and len(rows)==len(by)==8
    prev=TASK/'controller-route-20261029';receipt=prev/'final-receipt.json'
    pin='9d224c3b33220bb20930e89d9579f161ad7a76cbf5d4586402688d1e0079def9'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==source['previous_receipt_sha256']==pin
    old=json.loads(receipt.read_text())['files']
    for f in old:
        b=(prev/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
    for f in source['source_fragments']+source['literals']+source['initial_ID_banks']+result['source_spans']:
        at=int(f['va'],16)-BASE;b=raw[at:at+f['bytes']];assert hashlib.sha256(b).hexdigest()==f['sha256']
        if 'listing' in f:assert (HERE/f['listing']).is_file()
        if 'text' in f:assert b==(f['text']+'\0').encode()
        if 'words' in f:assert [hex(v[0]) for v in struct.iter_unpack('<I',b)]==f['words']
    assert len(source['source_fragments'])==15 and len(source['literals'])==4 and len(source['initial_ID_banks'])==3
    assert source['function_identity']['identity']=='osal_dynamic_id'
    strict=by['strict_original_context_stops_before_CP15']
    assert strict['result']['boundary']['pc']=='0x52c488' and strict['snapshot']['used_metadata_blocks']==0
    assert not strict['critical_adapters'] and not strict['inherited_context_adapters']
    boundaries=0;critical_enter=critical_exit=0
    for r in rows:
        init=r['initialization'];blocks=init['declared_bytes']//64
        assert init['original_free_chain']==[hex(0x53000000+64*i) for i in range(blocks)]
        for e in r['inherited_context_adapters']:assert e==['declared_context_query',0]
        for a in r['critical_adapters']:
            assert a['declared_return']==0 and a['va'] in ['0x53fea0','0x53ffec']
        enters=sum(a['va']=='0x53fea0' for a in r['critical_adapters']);exits=sum(a['va']=='0x53ffec' for a in r['critical_adapters'])
        assert enters-exits==(1 if r['case']=='busy_original_spinlock' else 0)
        critical_enter+=enters;critical_exit+=exits
        b=r.get('result',{}).get('boundary')
        if b:
            assert not b['native_call'] and not b['resource_reply_supplied'] and not b['affinity_register_value_supplied'];boundaries+=1
    for c in [1,5,7]:
        r=by[f'original_NRV_context{c}_to_message_allocation'];b=r['result']['boundary'];m=r['original_dynamic_ID_results']
        assert b['pc']=='0x49f80c' and b['registers'][0]=='0x61003c' and b['registers'][2:]==['0xd8','0x0']
        assert len(m)==1 and m[0]['raw_return']=='0x0' and m[0]['output_word']=='0x9005601f'
        assert m[0]['slot_context_pointer']=='0x53000000'
        snap=r['snapshot'];assert snap['free_metadata_bytes']==704 and snap['used_metadata_blocks']==5
        assert snap['bitmap_first_words'][0]=='0x80000000' and snap['original_lazy_object_count']==1 and snap['original_index_block_count']==3
    r=by['two_original_dynamic_ID_allocations'];assert r['ids']==['0x9005601f','0x9005601e']
    assert r['snapshot']['free_metadata_bytes']==576 and r['snapshot']['used_metadata_blocks']==7 and r['snapshot']['bitmap_first_words'][0]=='0xc0000000'
    for label in ['empty_metadata_pool','full_dynamic_ID_bitmap','busy_original_spinlock']:
        r=by[label];assert r['output_sentinel_unchanged'] and r['snapshot']['used_metadata_blocks']==0
        assert r['result']['boundary']['pc']==('0xa870c4' if label=='busy_original_spinlock' else '0x49e0ac')
    assert boundaries==7
    py=list(HERE.glob('*.py'))
    for f in py:ast.parse(f.read_text())
    attempts=list((HERE/'attempts').glob('*.json'));assert len(attempts)==4
    assert all(json.loads(f.read_text())['formal_cases']==0 for f in attempts)
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https:'):continue
        assert (HERE/target).is_file() or target in ['validation-results.json','final-receipt.json'],target
        links.append(target)
    out=dict(cp_sha256=PIN,previous_receipt_sha256=pin,previous_files_verified=len(old),python_ast_files=len(py),
             source_windows=15,literal_pins=4,initial_bank_pins=3,case_counts=dict(strict_context=1,nrv_prefix=3,sequential_ID=1,negative=3,total=8),
             unreplied_boundaries_verified=boundaries,critical_adapters_declared=dict(enter=critical_enter,exit=critical_exit),
             original_dynamic_ID_results=['0x9005601f','0x9005601e'],original_metadata_block_bytes=64,next_original_message_request=dict(QID='0x61003c',bytes=216),
             local_links_verified=len(links),
             boundary=dict(native_target_execution=False,device_actions=0,affinity_register_reads=0,dynamic_ID_results_fabricated=0,
                           resource_replies_supplied=0,actual_message_buffer=False,service_send_receive=False,real_pixel_buffers=False,
                           normal_controller_constructed=False,MAIN_recording_pixels=False,complete_donor_ISP=False,firmware_output=False,
                           modified_firmware_flashable=False,goal_complete=False,termination_condition_met=False),
             conclusion='Original RAM metadata/ID allocation replaces the former unreplied boundary under explicit environment adapters. Strict execution still stops before CP15; adapted NRV prefixes stop before message-buffer allocation. Full colour transplant and modified firmware admission remain unproven.')
    (HERE/'validation-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
