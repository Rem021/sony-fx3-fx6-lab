#!/usr/bin/env python3
"""Verify the body loader checkpoint without rerunning sealed guest scripts."""
from pathlib import Path
import ast,hashlib,json,re
from assemble_body_guest import HERE,AP,View,sources

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    previous=HERE.parent/'entry-20261029';receipt=previous/'final-receipt.json';old=json.loads(receipt.read_text())
    for r in old['files']:
        p=previous/r['path'];assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],r['path']
    ast_count=0
    for p in HERE.glob('*.py'):ast.parse(p.read_text());ast_count+=1
    for p in HERE.rglob('*.json'):json.loads(p.read_text())
    card=json.loads((HERE/'obj-source.json').read_text());assert digest(HERE/card['output'])==card['sha256']
    views={s['sha256']:View(s['path'],s['sha256']) for s in sources()}
    obj=View(HERE/card['output'],card['sha256']);fragments=0
    origin=json.loads((HERE/'image-origin-results.json').read_text());assert origin['regular_files_read']==797
    expected='62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa'
    assert origin['preinstalled_updater_image']['sha256']==expected
    for r in origin['selected_fragments']:
        v=views[r['source_sha256']];assert hashlib.sha256(v.read(int(r['va'],16),r['bytes'])).hexdigest()==r['sha256'];fragments+=1
    for r in json.loads((HERE/'obj-marker-reference-results.json').read_text())['windows']:
        assert hashlib.sha256(obj.read(int(r['range_start'],16),r['bytes'])).hexdigest()==r['sha256'];assert (HERE/r['disassembly']).stat().st_size>0;fragments+=1
    assembled=json.loads((HERE/'body-assembly-guest-results.json').read_text());assert assembled['image_bytes']==1253376 and assembled['image_sha256']==expected
    choices=json.loads((HERE/'image-selection-guest-results.json').read_text())['cases'];assert len(choices)==2
    assert choices[0]['marker_fixture'] is False and choices[0]['selected_image']=='/usr/bin/udtrbody.bin'
    assert choices[1]['marker_fixture'] is True and choices[1]['selected_image']=='/tmp_updater/updater/bodyimg'
    assert all(r['assembled_image_sha256']==expected for r in choices)
    links=0
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if '://' in target:continue
        if target not in ['validation-results.json','final-receipt.json']:assert (HERE/target).exists(),target
        links+=1
    result=dict(status='PASS',previous_entry_files_verified=len(old['files']),previous_entry_receipt_sha256=digest(receipt),python_ast_files=ast_count,new_static_slice_hashes_verified=fragments,original_guest_cases=3,assembled_and_preinstalled_image_sha256=expected,local_readme_links=links,runtime_marker_state_observed=False,native_mounts=0,native_loader_calls=0,camera_or_usb_actions=0,full_modified_package_emitted=False,termination_condition_met=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
