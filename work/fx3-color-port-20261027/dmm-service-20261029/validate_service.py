#!/usr/bin/env python3
"""Independent checkpoint consistency/readback; do not rerun sealed guests."""
import hashlib,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
sys.path.insert(0,str(HERE))
from service_guest import image,BASE,PIN

def main():
    target=HERE/'validation-results.json';assert not target.exists()
    raw=image();assert hashlib.sha256(raw).hexdigest()==PIN
    review=json.loads((HERE/'source-and-goal-review.json').read_text())
    previous=TASK/'dmm-request-20261029/final-receipt.json'
    assert hashlib.sha256(previous.read_bytes()).hexdigest()=='8a51be060874e07da4133944125a6beb6b83c377bc699570d2b15dbe625c73d2'
    rows=json.loads(previous.read_text())['files']
    for r in rows:
        b=(previous.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    for r in review['source_fragments']:
        a=int(r['va'],16)-BASE;b=raw[a:a+r['bytes']];assert hashlib.sha256(b).hexdigest()==r['sha256']
        assert (HERE/r['listing']).is_file()
    t=review['static_message_dispatch'];b=raw[int(t['table_va'],16)-BASE:int(t['table_va'],16)-BASE+46*4]
    assert hashlib.sha256(b).hexdigest()==t['table_sha256'] and struct.unpack_from('<I',b,0x20*4)[0]==0xab6191
    result=json.loads((HERE/'service-results.json').read_text());cases=result['cases'];assert len(cases)==4
    for case in cases[:3]:
        assert case['registration']['result']['returned'] and case['registration']['result']['raw_r0']=='0x0'
        record=[int(v,16) for v in case['registration']['record_words']]
        assert record[2]==0xa874e3 and record[5:7]==[0xab95e1,0]
        assert case['send_prefix']['boundary']['pc']=='0x52bd1c' and not case['send_prefix']['returned']
        callback=case['callback_prefix']['boundary'];assert callback['pc']=='0xab71cc'
        assert callback['registers'][:3]==['0x9005601f',case['packet']['boundary']['payload_pointer'],'0xd8']
        assert case['separate_callback_entry'] and not case['original_send_completed']
        assert not callback['provider_reply_supplied'] and not callback['kernel_return_supplied']
        assert case['inherited_context_adapters'] and case['critical_adapters']
    strict=cases[3];assert strict['registration_prefix']['boundary']['pc']=='0x52c488'
    assert not strict['inherited_context_adapters'] and not strict['critical_adapters']
    assert strict['snapshot']['used_metadata_blocks']==0
    public=json.loads((HERE/'public-source-readback.json').read_text());success=0;errors=0
    for r in public['records']:
        if 'error' in r:
            errors+=1;assert r['absence_inferred'] is False;continue
        success+=1;b=(HERE/r['file']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
        assert hashlib.sha256((HERE/r['text_file']).read_bytes()).hexdigest()==r['text_sha256']
    correction=review['public_readback']['venice_text_correction']
    assert hashlib.sha256((HERE/correction['file']).read_bytes()).hexdigest()==correction['sha256']
    for r in review['existing_evidence_pins']:
        b=(TASK/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert all(not g['passed'] for g in review['complete_goal_gates'])
    assert not review['goal_complete'] and not review['flashable_package_produced'] and review['device_actions']==0
    out=dict(status='PASS_BOUNDED_ORIGINAL_REGISTRATION_AND_SEPARATE_CALLBACK_PREFIX',previous_sealed_files_verified=len(rows),
        original_CP_source_windows_verified=len(review['source_fragments']),static_dispatch_entries_verified=46,
        adapted_original_registrations=3,strict_affinity_boundary_cases=1,original_send_kernel_boundaries=3,
        separate_original_callback_prefixes=3,service_replies_supplied=0,official_HTTP_pages_hashed=success,
        official_HTTP_errors_kept_as_gaps=errors,existing_gate_evidence_pins_verified=len(review['existing_evidence_pins']),
        full_goal_gates_passed=0,old_guest_mains_rerun=False,sony_native_programs_executed=0,device_actions=0,
        scope='Consistency of original source/table and recorded bounded RAM executions. No complete normal send, real allocation, pixels, donor ISP or flashability acceptance.')
    target.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
