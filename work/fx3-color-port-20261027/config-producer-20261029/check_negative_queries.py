#!/usr/bin/env python3
"""Meaningful original BK4 rejection checks, without original-file mutation."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from nor_descriptor_guest import Guest,BACKUP,OUT,PIN
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
def main():
    out=HERE/'NOR-negative-query-results.json';assert not out.exists()
    raw=(HERE/'original-files/loader_nor.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    record=(TASK/'dmm-backup-20261029/original-records/canonical-bank1.bin').read_bytes()
    source=json.loads((HERE/'load-descriptor-sources.json').read_text())
    bank=next(x for x in source['templates'] if x['member']==source['canonical_template'])['banks'][1]
    assert hashlib.sha256(record).hexdigest()==bank['record_sha256']
    g=Guest(raw,record);init=g.call(0xfe04d63c,[BACKUP]);assert init['registers'][0]=='0x0'
    missing=g.call(0xfe04c7b4,[0xfaffff,OUT]);assert missing['boundary']['reason']=='returned' and missing['registers'][0]=='0xffffffff'
    assert bytes(g.u.mem_read(OUT,0x4000))==b'\xa7'*0x4000
    bad=bytearray(record);bad[12]=ord('X')
    g=Guest(raw,bytes(bad));rejected=g.call(0xfe04d63c,[BACKUP])
    assert rejected['boundary']['reason']=='returned' and rejected['registers'][0]=='0xffffffff'
    result=dict(NOR_sha256=PIN,original_record_sha256=bank['record_sha256'],checks=[
        dict(name='missing_parameter_FAFFFF',result=missing,entire_output_canary_unchanged=True),
        dict(name='bad_BK4_signature_in_explicit_RAM_input',mutation_offset=12,original_byte=record[12],fixture_byte=bad[12],result=rejected)],
        scope='Original-code rejection paths only. Bad signature exists solely in isolated RAM input; official source files are untouched. No body data or physical/device execution.')
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([dict(name=x['name'],R0=x['result']['registers'][0]) for x in result['checks']]))
if __name__=='__main__':main()
