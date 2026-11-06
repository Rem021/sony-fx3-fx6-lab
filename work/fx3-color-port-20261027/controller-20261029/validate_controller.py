#!/usr/bin/env python3
"""Readback of saved controller/CLI evidence without repeating their main loops."""
import ast,hashlib,json,re,sys
from pathlib import Path
from controller_guest import HERE,sources
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources as ap_sources

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    prior=HERE.parent/'xml-20261029';receipt=prior/'final-receipt.json';pin='de915656908a08aa2be3b366575a3e74823ea3dd298b7fd09664266b8cf2c8ab'
    assert digest(receipt)==pin
    previous=json.loads(receipt.read_text())['files'];assert len(previous)==42
    for r in previous:
        p=prior/r['path'];assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256']
    syntax=[]
    for p in sorted(HERE.glob('*.py')):ast.parse(p.read_text(),filename=str(p));syntax.append(p.name)
    json_files=[]
    for p in sorted(HERE.rglob('*.json')):
        if p.name in ['validation-results.json','final-receipt.json']:continue
        json.loads(p.read_text());json_files.append(str(p.relative_to(HERE)))
    views={str(v.path):v for base,v in sources()}
    for row in ap_sources():
        if Path(row['path']).name in ['crypter.elf','libupdaterufp.so','libcryptfileinputupdaterapi.so']:views[row['path']]=View(row['path'],row['sha256'])
    contract=json.loads((HERE/'controller-contract-results.json').read_text());spans=[]
    for key,count in [('original_controller_unique_function_bodies',135),('selected_fragments',20)]:
        assert len(contract[key])==count
        for r in contract[key]:
            view=views[r['source']];assert hashlib.sha256(view.raw).hexdigest()==r['source_sha256']
            raw=view.read(int(r['va'],16),r['bytes']);assert hashlib.sha256(raw).hexdigest()==r['sha256']
            if 'disassembly' in r:assert (HERE/r['disassembly']).is_file()
            spans.append(dict(kind=key,source_sha256=r['source_sha256'],va=r['va'],bytes=len(raw)))
    controller=json.loads((HERE/'controller-guest-results.json').read_text())['cases'];cli_results=json.loads((HERE/'crypter-arguments-guest-results.json').read_text());cli=cli_results['cases']
    assert len(controller)==4 and len(cli)==4
    assert [r['case'] for r in controller]==['new_group','same_group','malformed_xml','bad_tar_checksum']
    assert [r['boundary']['operation'] for r in controller]==['system_request_boundary','before_original_join','original_exception_boundary','original_exception_boundary']
    assert [r['consumed_bytes'] for r in controller]==[4096,5120,3072,0]
    assert [len(r['system_requests']) for r in controller]==[2,1,1,1]
    for row in controller:
        assert 0<row['total_instructions']<1000000 and row['stream_bytes']==5120
        assert row['system_requests'][0]['role']=='startup_result_fixture' and row['system_requests'][0]['fixture_wait_status']==0
        assert all(r['native_execution'] is False for r in row['system_requests'])
        assert row['environment_fixture']['entries']==0 and row['startup_errno_fixture']==0
        assert any('UpdaterBody::Execute(' in label for label in row['original_function_entries'])
        for event in row['ring_adapter_events']:
            if event['operation']=='RAM ring advance':assert event['requested']%512==0
        for event in row['original_empty_string_zero_writes']:
            address=int(event['address'],16);assert event['value']==0 and 0x30021468<=address and address+event['bytes']<=0x30021480
    assert controller[2]['boundary']['code']==controller[3]['boundary']['code']=='0x30002'
    assert [r['boundary']['file_chunk'] for r in cli[:3]]==[0,1,0]
    assert cli[3]['boundary'] is None and cli[3]['return_value_if_returned']==1
    for row in cli:
        assert [r['entry'] for r in row['executable_initializers']]==['0x400a98','0x401028']
        assert all(r['file_chunk_after']==0 for r in row['executable_initializers'])
        for r in row['original_bss_writes']:
            address=int(r['address'],16);assert 0x412088<=address and address+r['bytes']<=0x4124a8
    table=cli_results['original_ufp_argv_table'];v=views[table['source']];raw=v.read(int(table['va'],16),table['bytes']);assert hashlib.sha256(raw).hexdigest()==table['sha256']
    assert table['argv']==cli[0]['argv']
    attempts=sorted((HERE/'attempts').glob('*.json'));assert len(attempts)==7
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https://'):continue
        if target not in ['validation-results.json','final-receipt.json']:assert (HERE/target).exists(),target
        links.append(target)
    result=dict(status='PASS_BOUNDED_ORIGINAL_CONTROLLER_AND_CLI',previous_xml_receipt_sha256=pin,previous_sealed_files_verified=42,
                syntax_files=syntax,json_files=json_files,source_span_checks=spans,guest_case_counts=dict(tar_controller=4,crypter_main_and_executable_initializers=4),guest_cases_total=8,
                preserved_failed_integration_attempts=6,preserved_metadata_validation_failures=1,local_readme_links=links,startup_system_status_is_fabricated=True,whole_external_input_executed=False,original_manager_initialization_executed=False,
                actual_device_or_process_state_proven=False,complete_venice_port_proven=False,full_modified_package_emitted=False,native_system_calls=0,camera_actions=0,
                goal_completion_claimed=False,termination_condition_met=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],previous_files=42,function_bodies=135,fragments=20,guest_cases=8,camera_actions=0)))

if __name__=='__main__':main()
