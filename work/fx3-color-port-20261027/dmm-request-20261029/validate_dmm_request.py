#!/usr/bin/env python3
"""Verify original request fields, allocation evidence and unreplied boundaries."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN

def main():
    raw=image();source=json.loads((HERE/'dmm-request-source-results.json').read_text())
    result=json.loads((HERE/'dmm-request-results.json').read_text());rows=result['cases'];by={r['case']:r for r in rows}
    assert source['cp_sha256']==result['cp_sha256']==PIN and len(rows)==len(by)==7
    previous=TASK/'dynamic-id-20261029';receipt=previous/'final-receipt.json'
    pin='4a899628f47fe3ca66c66d0d00fa39637427fd43a14aac57bc781cb665330cb6'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==source['previous_receipt_sha256']==pin
    old=json.loads(receipt.read_text())['files']
    for f in old:
        b=(previous/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
    for f in source['source_fragments']+result['source_spans']:
        a=int(f['va'],16)-BASE;b=raw[a:a+f['bytes']];assert hashlib.sha256(b).hexdigest()==f['sha256']
        if 'listing' in f:assert (HERE/f['listing']).is_file()
    for r in source['function_identity']['literals']+source['unbound_candidates']['cp_literals']:
        a=int(r['va'],16)-BASE;b=raw[a:a+r['bytes']]
        assert hashlib.sha256(b).hexdigest()==r['sha256'] and b==(r['text']+'\0').encode()
        if 'enclosing_literal' in r:
            e=r['enclosing_literal'];a=int(e['va'],16)-BASE;b=raw[a:a+e['bytes']]
            assert hashlib.sha256(b).hexdigest()==e['sha256'] and e['text']=='[DmmWrapper]'+r['text']
    av=(TASK.parent/'sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert hashlib.sha256(av).hexdigest()==source['unbound_candidates']['av_sha256']
    for r in source['unbound_candidates']['av_file_hints']:
        a=int(r['file_offset'],16);b=av[a:a+r['bytes']]
        assert hashlib.sha256(b).hexdigest()==r['sha256'] and b==(r['text']+'\0').encode()
    t=source['unbound_candidates']['command_reference_window'];a=int(t['va'],16)-BASE
    assert hashlib.sha256(raw[a:a+t['bytes']]).hexdigest()==t['sha256']
    assert len(source['source_fragments'])==8 and not source['static_reply_requirements']['executed']
    expected_mask=bytearray(216)
    for r in source['original_request_contract']['fields']:
        a=int(r['offset'],16);expected_mask[a:a+r['bytes']]=b'\1'*r['bytes']
    assert sum(expected_mask)==14
    boundaries=0;critical_enter=critical_exit=0
    for r in rows:
        b=r['result'].get('boundary')
        if b:
            boundaries+=1;assert not b['native_call']
            if b['pc']=='0xa878ca':assert not b['submission_executed'] and not b['service_reply_supplied']
            else:assert not b['resource_reply_supplied'] and not b['affinity_register_value_supplied']
        for a in r['critical_adapters']:assert a['va'] in ['0x53fea0','0x53ffec'] and a['declared_return']==0
        for a in r['inherited_context_adapters']:assert a==['declared_context_query',0]
        enters=sum(a['va']=='0x53fea0' for a in r['critical_adapters']);exits=sum(a['va']=='0x53ffec' for a in r['critical_adapters'])
        assert enters-exits==(1 if r['case']=='variable_pool_lock_busy' else 0)
        critical_enter+=enters;critical_exit+=exits
        if 'initialization' in r:
            init=r['initialization'];assert init['original_fragment']=='0x49dbea..0x49dc1a'
            assert init['original_variable_pool_bytes']==0x80000 and init['original_variable_pool_base']=='0x53000400'
            assert len(init['original_free_chain'])==16
    for c in [1,5,7]:
        r=by[f'original_NRV_context{c}_DMM_packet'];b=r['result']['boundary']
        assert b['pc']=='0xa878ca' and b['registers'][0]=='0x61003c' and b['payload_bytes']==216
        assert b['original_payload_fields']==dict(word0='0x20',key4='0x4af',wordC='0x0',word14='0x55',word16='0x1')
        assert b['original_header_fields']==dict(block_count=4,flags='0x1',reference_count=1,reply_ID='0x9005601f',length=216,guard='0x55555555')
        assert b['tail_guard']=='0x77777777' and b['payload_pointer']=='0x53080318'
        body=bytes.fromhex(b['payload_hex']);mask=bytes.fromhex(b['original_payload_write_mask'])
        assert len(body)==len(mask)==216 and mask==expected_mask and b['original_payload_written_bytes']==14
        assert all(v==0xa7 for v,m in zip(body,mask) if not m)
        for f in source['original_request_contract']['fields']:
            a=int(f['offset'],16);assert int.from_bytes(body[a:a+f['bytes']],'little')==int(f['value'],16)
        assert r['snapshot']['used_metadata_blocks']==7 and r['snapshot']['variable_pool']['free_bytes']==0x7ff00
        allocations=r['original_message_allocation_returns'];assert len(allocations)==1 and allocations[0]['raw_return']=='0x0' and allocations[0]['output_word']==b['payload_pointer']
        assert len(r['original_dynamic_ID_results'])==1 and r['original_dynamic_ID_results'][0]['output_word']==b['original_header_fields']['reply_ID']
    strict=by['strict_context_after_original_pool_fragment'];assert strict['result']['boundary']['pc']=='0x52c488'
    assert not strict['critical_adapters'] and not strict['inherited_context_adapters']
    assert by['variable_pool_exhausted']['result']['boundary']['pc']=='0x49e0ac'
    assert by['variable_pool_lock_busy']['result']['boundary']['pc']=='0xa870c4'
    invalid=by['original_message_length_limit'];assert invalid['result']['returned'] and invalid['result']['raw_r0']=='0xfffffc00' and invalid['output_sentinel_unchanged']
    assert not invalid['critical_adapters'] and not invalid['inherited_context_adapters'] and boundaries==6
    py=list(HERE.glob('*.py'))
    for f in py:ast.parse(f.read_text())
    attempts=list((HERE/'attempts').glob('*.json'));assert len(attempts)==3
    assert all(json.loads(f.read_text())['formal_cases']==0 for f in attempts)
    links=[]
    for t in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if t.startswith('https:'):continue
        assert (HERE/t).is_file() or t in ['validation-results.json','final-receipt.json'],t
        links.append(t)
    out=dict(cp_sha256=PIN,av_sha256=source['unbound_candidates']['av_sha256'],previous_receipt_sha256=pin,previous_files_verified=len(old),
             python_ast_files=len(py),source_windows=8,DmmWrapper_literal_pins=4,candidate_CP_literals=3,candidate_AV_literals=2,
             case_counts=dict(original_request=3,strict_context=1,allocation_negative=2,original_length_guard=1,total=7),
             unreplied_boundaries_verified=boundaries,critical_adapters_declared=dict(enter=critical_enter,exit=critical_exit),
             original_message_payload_bytes=216,original_payload_written_bytes=14,remaining_fixture_payload_bytes=202,original_variable_pool_bytes=0x80000,
             local_links_verified=len(links),
             boundary=dict(native_target_execution=False,device_actions=0,message_allocation_pointers_fabricated=0,dynamic_ID_results_fabricated=0,
                           submission_executed=False,provider_replies_supplied=0,QID_receiver_proven=False,unit_4af_layout_proven=False,
                           physical_image_buffers=False,MAIN_recording_pixels=False,complete_donor_ISP=False,firmware_output=False,
                           modified_firmware_flashable=False,goal_complete=False,termination_condition_met=False),
             conclusion='Original RAM pool/message allocation and 14 core DmmWrapper AllocNew request bytes verified before submission. Static reply checks and unbound DMM candidates are not provider responses or full image/firmware acceptance.')
    (HERE/'validation-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
