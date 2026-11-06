#!/usr/bin/env python3
"""Validate saved XML guest evidence and original-byte provenance without reruns."""
import ast,hashlib,json,re
from pathlib import Path
from xml_guest import HERE,sources

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    prior=HERE.parent/'marker-20261029';receipt=prior/'final-receipt.json'
    pin='13e29141891316bff46003ff91c1f3bce69eb7f745d2ee977af57f019ab8d3a9';assert digest(receipt)==pin
    previous=json.loads(receipt.read_text())['files'];assert len(previous)==43
    for r in previous:
        p=prior/r['path'];assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256']
    syntax=[]
    for p in sorted(HERE.glob('*.py')):ast.parse(p.read_text(),filename=str(p));syntax.append(p.name)
    parsed=[]
    for p in sorted(HERE.rglob('*.json')):
        if p.name in ['validation-results.json','final-receipt.json']:continue
        json.loads(p.read_text());parsed.append(str(p.relative_to(HERE)))
    views={str(v.path):v for base,v in sources()};contract=json.loads((HERE/'xml-contract-results.json').read_text())
    checked=[]
    for key,count in [('unique_function_bodies_entered',87),('selected_fragments',23)]:
        rows=contract[key];assert len(rows)==count
        for r in rows:
            v=views[r['source']];assert hashlib.sha256(v.raw).hexdigest()==r['source_sha256']
            raw=v.read(int(r['va'],16),r['bytes']);assert hashlib.sha256(raw).hexdigest()==r['sha256']
            if 'disassembly' in r:assert (HERE/r['disassembly']).is_file()
            checked.append(dict(kind=key,source_sha256=r['source_sha256'],va=r['va'],bytes=len(raw)))
    xml=json.loads((HERE/'xml-guest-results.json').read_text())['cases'];dispatch=json.loads((HERE/'dispatch-guest-results.json').read_text())['cases'];post=json.loads((HERE/'post-config-guest-results.json').read_text())['cases']
    assert [len(xml),len(dispatch),len(post)]==[4,3,3]
    assert [r['loads'][-1]['return_value'] for r in xml]==[1,1,0,0]
    assert [r['matches'] for r in xml[1]['keys']]==[True,True,False]
    assert [bool(r['boundary']) for r in dispatch]==[True,True,False]
    assert post[0]['dispatch']['boundary']['command'].endswith('; probe.txt')
    assert post[1]['user_file_open_requests']==0 and not post[1]['key_check']['matches']
    assert post[2]['post_callback']['exception_boundary']['code']=='0x30002'
    global_writes=0
    for row in xml+dispatch+post:
        assert 0<row['total_instructions']<=1000000
        assert any('DomDocument::Parse(' in name for name in row['original_function_entries'])
        assert row['host_import_counts'].get('pthread_create',0)==0
        for write in row['original_empty_string_zero_writes']:
            assert write['symbol']=='Updater::Xml::TiXmlString::nullrep_' and write['value']==0
            address=int(write['address'],16);assert 0x30021468<=address and address+write['bytes']<=0x30021480
            global_writes+=1
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https://'):continue
        if target not in ['validation-results.json','final-receipt.json']:assert (HERE/target).exists(),target
        links.append(target)
    source=json.loads((HERE/'xml-source.json').read_text());assert source['bytes']==72784 and source['sha256']=='22e19c05a5816b6d358a8d037297a9472cc53230c2045051b830316c59902acd'
    result=dict(status='PASS_BOUNDED_ORIGINAL_XML_COMPONENT_CHAIN',previous_marker_receipt_sha256=pin,previous_sealed_files_verified=43,
                syntax_files=syntax,json_files=parsed,source_span_checks=checked,guest_case_counts=dict(xml_load_and_key=4,guardless_queue_and_dispatch=3,config_post_callback=3),guest_cases_total=10,
                permitted_global_zero_write_events=global_writes,local_readme_links=links,native_system_calls=0,native_target_loading=0,camera_actions=0,
                whole_tar_controller_executed=False,external_input_admission_proven=False,real_loader_and_recovery_proven=False,complete_venice_color_port_proven=False,
                goal_completion_claimed=False,termination_condition_met=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],previous_files=43,function_bodies=87,fragments=23,guest_cases=10,camera_actions=0)))

if __name__=='__main__':main()
