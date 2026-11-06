#!/usr/bin/env python3
"""Verify pinned input checkpoints, source slices and seven original guest cases."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    previous=TASK/'body-state-20261029';receipt=previous/'final-receipt.json'
    assert sha(receipt.read_bytes())=='55a132887d05e33101540709bd8660049a39aaedb8737d148363fa00111c377f'
    verified={}
    for directory in [previous,TASK/'binding-20261028']:
        manifest=json.loads((directory/'final-receipt.json').read_text())
        for row in manifest['files']:
            raw=(directory/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
        verified[directory.name]=dict(files=len(manifest['files']),receipt_sha256=sha((directory/'final-receipt.json').read_bytes()))
    assert verified['body-state-20261029']['files']==27 and verified['binding-20261028']['files']==63
    raw=image();assert sha(raw)==PIN
    scripts=list(HERE.glob('*.py'));assert len(scripts)==4
    for p in scripts:ast.parse(p.read_text(),filename=str(p))
    fields=json.loads((HERE/'scene-field-candidates.json').read_text());assert fields['cp_sha256']==PIN
    assert len(fields['store_candidates'])==127 and len(fields['load_candidates'])==221
    vector=json.loads((HERE/'vector-source-results.json').read_text());assert vector['cp_sha256']==PIN
    assert len(vector['source_fragments'])==8 and len(vector['direct_call_candidates'])==6
    assert sum(r['value'] in ['0x118b6c0','0x118b788'] for r in vector['constant_references'])==129
    for record in vector['source_fragments']:
        at=int(record['file_offset'],16);assert sha(raw[at:at+record['bytes']])==record['sha256']
        assert (HERE/record['listing']).is_file()
    for record in fields['store_candidates']+vector['constant_references']+vector['direct_call_candidates']:
        at=int(record['span_file'],16);assert sha(raw[at:at+record['span_bytes']])==record['span_sha256']
    assert [r['value'] for r in vector['diagnostic_source_names']]==['GetInfo.cpp','ImageParam_Sync.cpp']
    for record in vector['diagnostic_source_names']:
        at=int(record['file_offset'],16);body=record['value'].encode()+b'\0'
        assert raw[at:at+len(body)]==body and sha(body)==record['sha256']
    result=json.loads((HERE/'scene-context-results.json').read_text());assert result['cp_sha256']==PIN and len(result['cases'])==7
    for record in result['source_spans']:
        at=int(record['file_offset'],16);assert sha(raw[at:at+record['bytes']])==record['sha256']
    cases=result['cases']
    assert [r['constructor_type_14'] for r in cases]==[0,1,1,3,2,2,2]
    assert [r['sync_fields_1210_1214_1218_121c'] for r in cases]==[[0,0,0,0],[8,8,1,1],[8,10,1,2],[1,1,1,1],[1,5,1,2],[5,7,2,4],[1,1,1,1]]
    for row in cases:
        assert row['original_memcpy_calls']==2 and row['vector_parameter_pointer']=='0x51004de0'
        assert row['parameter_900']==row['raw_graph_argument'] and row['parameter_908']==row['constructor_type_14']
        writes=row['original_constructor_writes']
        graph=[r for r in writes if r['offset']=='0xc'];kind=[r for r in writes if r['offset']=='0x14']
        assert len(graph)==1 and graph[0]['pc']=='0x9d10e0' and int(graph[0]['value'],16)==row['parameter_900']
        assert len(kind)==1 and kind[0]['pc']=='0x9d11f4' and int(kind[0]['value'],16)==row['parameter_908']
        assert all(0x9d1038<=int(r['pc'],16)<0x9d1442 for r in writes)
    assert cases[-1]['constructor_argument_origin']=='original caller fragment'
    assert cases[-1]['raw_constructor_stage_pointer']=='0x40fc09' and cases[-1]['raw_graph_argument']==0
    assert [r['resource_result']['group'] for r in cases[3:]]==[0,5,4,0]
    for row in cases[3:]:
        assert row['resource_result']['command'][1]==22
        assert row['resource_result']['phase']==dict(state=2,look=22,pending=1,commands=1)
    for row in cases[1:3]:assert row['resource_result']==dict(status=0,allocations=0,output_slot_unchanged=True)
    assert 'boundary' in cases[0]['resource_result']
    public=json.loads((HERE/'public-source-review.json').read_text());assert len(public['sources'])==5 and public['downloads']==0
    links=[]
    for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if link.startswith('https://') or link in ['validation-results.json','final-receipt.json']:continue
        assert (HERE/link).exists(),link;links.append(link)
    output=dict(previous_checkpoints_verified=verified,python_ast_files=len(scripts),cp_sha256=PIN,original_source_fragments=8,
                candidate_scans_verified=dict(store=127,load=221,vector=129,direct_branch=6),
                case_counts=dict(default_zero=1,without_vfx=2,constructor_through_colour_sdk=4,total=7),
                original_caller_fragment_supplies_stage_and_graph=True,
                original_parameter_record_writes_verified=True,original_two_copies_per_case=True,
                original_vector_constructor_used=True,local_links_verified=len(links),public_sources_reviewed=5,
                boundary=dict(normal_scene_or_main_routing=False,pixel_output=False,native_target_execution=False,device_actions=0,firmware_output=False,goal_complete=False,termination_condition_met=False),
                conclusion='One original parameter-production layer recovered. Normal callback/argument selection, source pixel domain, donor complete ISP and flashability remain unproven.')
    (HERE/'validation-results.json').write_text(json.dumps(output,indent=2)+'\n')
    assert (HERE/'validation-results.json').is_file()
    print(json.dumps(output))

if __name__=='__main__':main()
