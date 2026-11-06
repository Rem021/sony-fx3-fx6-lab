#!/usr/bin/env python3
"""Validate stored AP/CP service evidence; no replay of completed guests."""
import ast,hashlib,json,re,struct,sys
from pathlib import Path
from find_lens_service import HERE,FS
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    prior=HERE.parent/'legacy-stream-20261029';receipt=prior/'final-receipt.json';pin='d976b2e1f9065f48afd2fba268b69582b4749c20dcbd9dca3f38068b1390d4b8'
    assert digest(receipt)==pin
    previous=json.loads(receipt.read_text())['files'];assert len(previous)==40
    for row in previous:
        p=prior/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    syntax=[]
    for p in sorted(HERE.glob('*.py')):ast.parse(p.read_text(),filename=str(p));syntax.append(p.name)
    json_files=[]
    for p in sorted(HERE.rglob('*.json')):
        if p.name in ['validation-results.json','final-receipt.json']:continue
        json.loads(p.read_text());json_files.append(str(p.relative_to(HERE)))
    locations=json.loads((HERE/'service-location-results.json').read_text());assert locations['arm64_elf_files']==532 and len(locations['ap_mov_wide_matches'])==172
    for row in locations['ap_mov_wide_matches']:
        if row['path'].endswith('.ko'):assert row['address_kind']=='section-relative' and row['va'] is None
    peers=json.loads((HERE/'peer-constant-results.json').read_text());assert len(peers['matches'])==29
    cp_rows=[r for r in peers['matches'] if r['target']=='0x912503d0'];assert [r['cp_va'] for r in cp_rows]==['0x391b5e','0x391c84']
    raw_files={}
    for row in peers['scans']:
        p=Path(row['path'])
        if str(p) not in raw_files:
            raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['source_sha256'];raw_files[str(p)]=raw
    for row in peers['matches']:
        raw=raw_files[row['path']];start=int(row['span_file_offset'],16)
        assert hashlib.sha256(raw[start:start+row['span_bytes']]).hexdigest()==row['span_sha256']
    contract=json.loads((HERE/'lens-contract-results.json').read_text());assert len(contract['fragments'])==19
    checked=[];views={}
    for row in contract['fragments']:
        p=Path(row['source']);assert digest(p)==row['source_sha256']
        if row['architecture']=='Thumb':
            raw=raw_files[str(p)];start=int(row['file_offset'],16);span=raw[start:start+row['bytes']]
        else:
            v=views.setdefault(str(p),View(p,row['source_sha256']));span=v.read(int(row['va'],16),row['bytes'])
        assert hashlib.sha256(span).hexdigest()==row['sha256'] and (HERE/row['disassembly']).is_file()
        checked.append(dict(source_sha256=row['source_sha256'],architecture=row['architecture'],va=row['va'],bytes=row['bytes']))
    cp=raw_files[str(FS/'files/nflasha8/cpapp-b.bin')]
    for row in contract['cp_data_tables'].values():
        start=int(row['va'],16)-0x108000;assert hashlib.sha256(cp[start:start+row['bytes']]).hexdigest()==row['sha256']
    assert contract['cp_data_tables']['reply_bytes']['values']==[20,12,40,8,8]
    members=json.loads((HERE/'original-member-results.json').read_text());assert len(members)==2
    for row in members:
        p=HERE/row['output'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    cached=json.loads((HERE/'cached-metadata-results.json').read_text())['cases'];peer=json.loads((HERE/'cp-peer-guest-results.json').read_text())['cases'];bridge=json.loads((HERE/'ap-cp-bridge-results.json').read_text())['cases']
    assert [len(cached),len(peer),len(bridge)]==[8,4,7]
    assert [r['result'] for r in cached[:7]]==['0x1','0x142','0x142','0x140','0x141','0x1','0x140']
    assert cached[-1]['boundary']['message_bytes']==20 and len(cached[-1]['original_cached_metadata_writes'])==3
    assert [len(bytes.fromhex(r['reply_hex'])) for r in peer[:3]]==[8,12,20] and peer[-1]['reply_hex'] is None
    assert [r['return_value'] for r in bridge]==[None,7,6,5,None,7,None]
    assert [r['original_ap_version_skip'] for r in bridge]==[0,0,0,0,1,0,0]
    for i,row in enumerate(bridge):
        requests=[struct.unpack_from('<I',bytes.fromhex(r['request_hex']))[0] for r in row['ram_bus'] if r['adapter']=='RAM AP-to-CP delivery']
        assert requests==([3] if i==6 else [3,1,0])
        if i in [0,4]:assert row['boundary']['operation']=='before_next_dynamic_body_service' and row['boundary']['native_call'] is False
        if i==6:assert row['boundary']['operation']=='RAM_bus_no_reply_boundary' and 'lens_handler' not in row['cp_original_entry_counts']
    writes=[w for w in bridge[4]['original_global_writes'] if w['address']=='0x400252b8'];assert writes==[dict(address='0x400252b8',bytes=4,value=1,pc='0x40003020')]
    attempts=sorted((HERE/'attempts').glob('*.json'));assert len(attempts)==2
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https://'):continue
        if target not in ['validation-results.json','final-receipt.json']:assert (HERE/target).exists(),target
        links.append(target)
    result=dict(status='PASS_ORIGINAL_AP_CP_RAM_LENS_CHAIN',previous_legacy_stream_receipt_sha256=pin,previous_sealed_files_verified=40,syntax_files=syntax,json_files=json_files,
                original_fragment_checks=checked,ap_elf_scan_count=532,ap_mov_candidates=172,cp_mov_candidates=29,cp_lens_service_candidates=2,
                case_counts=dict(cached_comparisons_and_query_boundary=8,cp_reply_loop=4,ap_cp_bridge=7),guest_cases_total=19,
                cp_reply_payloads_built_by_original_code=True,physical_cp_lens_state_is_synthetic=True,osal_bus_is_synthetic=True,next_body_service_reply_proven=False,
                native_ipc_calls=0,native_target_loading=0,device_actions=0,camera_actions=0,firmware_file_output=0,
                complete_venice_color_port_proven=False,goal_completion_claimed=False,termination_condition_met=False,preserved_failed_attempts=2,local_readme_links=links)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],previous_files=40,fragments=19,cases=19,camera_actions=0)))

if __name__=='__main__':main()
