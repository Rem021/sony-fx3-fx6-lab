#!/usr/bin/env python3
"""Cross-check physical load descriptors against original CP address table/files."""
import hashlib,json,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'CP-file-address-bindings.json';assert not out.exists()
    cp=TASK.parent/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
    raw=cp.read_bytes();assert sha(raw)=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
    data=raw[0xb54930-0x108000:0xb54930-0x108000+128]
    ranges=[struct.unpack_from('<4Q',data,i*32) for i in range(4)]
    assert ranges[1]==(0x800000000,0,0,0x80000000)
    source=json.loads((HERE/'load-descriptor-sources.json').read_text())
    bank=next(x for x in source['templates'] if x['member']==source['canonical_template'])['banks'][1]
    rows=[]
    for path,file,expected_va in [
        ('\\DmmCfg.bin',TASK/'dmm-config-20261029/original-files/DmmCfg.bin',0x09a08e00),
        ('\\tomco.txt',TASK/'dmm-backup-20261029/tomco.txt',0x00100000),
        ('\\cpapp-b.bin',cp,0x00108000)]:
        entry=next(x for x in bank['entries'] if x['path']==path)
        physical=int(entry['start'],16);matched=[r for r in ranges if r[0]<=physical<r[0]+r[3]]
        assert len(matched)==1
        translated=matched[0][1]+physical-matched[0][0];assert translated==expected_va
        b=file.read_bytes();rows.append(dict(original_load_descriptor=entry,original_file=str(file),file_bytes=len(b),
            file_sha256=sha(b),CP_constant_table_translation=hex(translated),
            scope='Original constant-table arithmetic only; no actual physical RAM or live CPU mapping is supplied.'))
    result=dict(CP_source=str(cp),CP_sha256=sha(raw),original_range_table_VA='0xb54930',
        original_range_table_sha256=sha(data),original_range_rows=[list(map(hex,r)) for r in ranges],bindings=rows,
        scope='Links original file descriptors to previously used CP addresses through original CP table. It does not show normal boot selection, actual FAT I/O, cache/TLB synchronization, file bytes at candidate RAM or pixels.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(path=x['original_load_descriptor']['path'],physical=x['original_load_descriptor']['start'],
        CP_translation=x['CP_constant_table_translation'],file_bytes=x['file_bytes']) for x in rows]))
if __name__=='__main__':main()
