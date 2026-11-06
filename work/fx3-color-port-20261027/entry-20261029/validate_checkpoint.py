#!/usr/bin/env python3
"""Verify source pins, new slice hashes, results, links and the prior seal."""
from pathlib import Path
import ast,hashlib,json,re,sys
import io
from elftools.elf.elffile import ELFFile
from inspect_app_crypto_calls import PATH,PIN,HERE
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    previous=HERE.parent/'ap-input-20261029';receipt=previous/'final-receipt.json';old=json.loads(receipt.read_text())
    for item in old['files']:
        p=previous/item['path'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],str(p)
    parsed=0
    for path in HERE.glob('*.py'):ast.parse(path.read_text());parsed+=1
    json_count=0
    for path in HERE.rglob('*.json'):json.loads(path.read_text());json_count+=1
    src=sources()+[dict(path=str(PATH),sha256=PIN)]
    for card in ['msc-server-source.json','usb-extcmd-source.json','external-command-sources.json']:
        records=json.loads((HERE/card).read_text());records=records if isinstance(records,list) else [records]
        for item in records:
            p=HERE/item['output'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256']
            if p.suffix!='.ko':src.append(dict(path=str(p),sha256=item['sha256']))
    views={s['sha256']:View(s['path'],s['sha256']) for s in src};slices=0
    for name in ['entry-static-results.json','loader-gates-selected-results.json','external-command-static-results.json']:
        for row in json.loads((HERE/name).read_text())['fragments']:
            v=views[row['source_sha256']];assert hashlib.sha256(v.read(int(row['va'],16),row['bytes'])).hexdigest()==row['sha256'];assert (HERE/row['disassembly']).is_file();slices+=1
    for row in json.loads((HERE/'app-crypto-call-results.json').read_text())['call_sites']:
        assert hashlib.sha256(views[PIN].read(int(row['range_start'],16),row['bytes'])).hexdigest()==row['sha256'];slices+=1
    kernel_card=json.loads((HERE/'usb-extcmd-source.json').read_text())
    kernel=ELFFile(io.BytesIO((HERE/kernel_card['output']).read_bytes()))
    for row in json.loads((HERE/'usb-extcmd-static-results.json').read_text())['functions']:
        code=kernel.get_section_by_name(row['section']).data();offset=int(row['offset'],16)
        assert hashlib.sha256(code[offset:offset+row['bytes']]).hexdigest()==row['sha256'];slices+=1
    routes=json.loads((HERE/'execute-update-guest-results.json').read_text())['cases'];assert len(routes)==9
    assert next(r for r in routes if r['case']=='process_failure_not_propagated')['typed_result']==0
    for row in routes:
        dispatch=[e for e in row['events'] if e['operation']=='original_ufp_dispatch'];assert len(dispatch)==1 and dispatch[0]['command']=={0:3,1:9,2:12}[row['mode']]
    media=json.loads((HERE/'media-length-guest-results.json').read_text())['cases'];assert len(media)==4
    assert media[0]['result']==3 and media[0]['boundary'] is None
    assert next(e['value'] for e in media[0]['events'] if e['operation']=='original_parser_length')==811876624
    assert media[1]['boundary']['requested_bytes']==2097152 and media[2]['result']==3
    links=[]
    for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if '://' in target:continue
        dest=(HERE/target.split('#')[0]).resolve()
        if dest.name not in ['final-receipt.json','validation-results.json']:assert dest.exists(),target
        links.append(target)
    result=dict(status='PASS',previous_sealed_files_verified=len(old['files']),previous_receipt_sha256=digest(receipt),python_ast_files=parsed,json_files_parsed_before_validation_output=json_count,pinned_elf_views=len(views),new_slice_hashes_verified=slices,original_guest_cases=13,local_readme_links=len(links),source_layout_checks='Kernel ET_REL source and five slice hashes verified by named section offsets; these offsets are not runtime addresses.',camera_actions=0,full_modified_package_emitted=False,termination_condition_met=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
