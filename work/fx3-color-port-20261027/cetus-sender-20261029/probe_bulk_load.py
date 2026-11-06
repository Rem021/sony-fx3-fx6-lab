#!/usr/bin/env python3
"""Strict original bulk-loader prefixes, stopped before unknown boot metadata."""
import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
PREVIOUS=TASK/'nor-backup-selection-20261029'
receipt=PREVIOUS/'final-receipt.json'
assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='4e1dceb5d8bf1a148e0dcd959fb020432b7f997bb8b6644c3200cbadaef44301'
helper=PREVIOUS/'backup_state_guest.py';pin=next(x for x in json.loads(receipt.read_text())['files'] if x['path']==helper.name)
assert hashlib.sha256(helper.read_bytes()).hexdigest()==pin['sha256']
spec=importlib.util.spec_from_file_location('original_backup_state_guest',helper)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def main():
    out=HERE/'bulk-loader-prefix-results.json';assert not out.exists()
    raw,record,source,bank=old.inputs();cases=[]
    for name,entry in [('ospi_load_cp_app_b_pre',0xfe05a2b4),('ospi_load_cp_app_b',0xfe05a1b4)]:
        g=old.Guest(raw,record);r=g.call(entry)
        assert r['boundary']==dict(reason='unmapped_external_state',PC='0xfe05885c',address='0xfe040140',bytes=4)
        cases.append(dict(name=name,result=r,boot_metadata_supplied=False,flash_or_file_data_reply_supplied=False))
    result=dict(NOR_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,
        scope='Only original prefix instructions in bounded RAM; both stop at the original slot5 boot-metadata read. No table value, clock, OSPI register, storage result, image bytes, native Sony process or device action is supplied.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(name=x['name'],boundary=x['result']['boundary']) for x in cases]))
if __name__=='__main__':main()
