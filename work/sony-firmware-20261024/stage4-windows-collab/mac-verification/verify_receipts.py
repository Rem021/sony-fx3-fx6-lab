#!/usr/bin/env python3
"""Standard-library receipt consistency check; does NOT repeat CPU emulation."""
from pathlib import Path
import hashlib, json, struct, zipfile

P=Path(__file__).resolve().parent
B=P.parents[1]
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def elfbytes(blob,va,n):
    assert blob[:6]==b'\x7fELF\x02\x01'
    off=struct.unpack_from('<Q',blob,32)[0]
    size,count=struct.unpack_from('<HH',blob,54)
    assert size==56 and count<100
    for i in range(count):
        typ,flags,o,v,phys,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',blob,off+i*size)
        if typ==1 and v<=va and va+n<=v+filesz:
            assert o+va-v+n<=len(blob)
            return blob[o+va-v:o+va-v+n]
    raise ValueError('Unmapped ELF file VA')

def main():
    receipt=json.loads((P/'source-receipt.json').read_text())
    for r in receipt['sources']:
        path=Path(r['path'])
        assert path.stat().st_size==r['bytes'] and digest(path)==r['sha256']
    zpath=P.parent/'FX3-7.02-4K30-H265离线研究证据.zip'
    assert digest(zpath)=='785c3b3fdb5e879dd7acda3b782001f09e3dce8210c71d6104ce141d77ba4865'
    with zipfile.ZipFile(zpath) as z:
        for r in json.loads(z.read('file-manifest.json')):
            raw=z.read(r['path'])
            assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
        previous=json.loads(z.read('converter-emulation-results.json'))['cases']
    current=json.loads((P/'offline-results.json').read_text())
    assert len(current['converter_cases'])==len(previous)==80
    fields=['input_frame_ordinal','input_record_setting_ordinal','candidate_memory_patch',
            'reason','VideoParamComb','DefStruct_FrameRate','DefStruct_VQuality']
    assert all(all(a[k]==b[k] for k in fields) for a,b in zip(current['converter_cases'],previous))
    assert all(current['checks'].values())
    app=(B/'stage2/extraction/files/nflasha15/lib/appFw.so').read_bytes()
    assert elfbytes(app,0x39895ae,1)==b'\x0a'
    mpr=(B/'stage2/extraction/files/nflasha15/lib/libmpr.so').read_bytes()
    # Independent read of original bitmap-immediate instructions. These constants
    # omit VPC8 even though the generic combination table contains an entry8.
    word=struct.unpack('<I',elfbytes(mpr,0xd1204,4))[0]
    assert word & 0xffe0001f==0xd2800001 and (word>>5)&0xffff==0x168c
    word=struct.unpack('<I',elfbytes(mpr,0xd12d0,4))[0]
    assert word & 0xffe0001f==0xd2800000 and (word>>5)&0xffff==0x16fc
    assert not (0x168c & (1<<8)) and not (0x16fc & (1<<8))
    for r in json.loads((P/'package-provenance.json').read_text()):
        assert digest(P/'wheels'/r['wheel'])==r['sha256']
    print('PASS: original input SHA; ZIP manifest; 80 recorded cases; raw VPC8 bitmap exclusion; pinned wheel hashes.')
    print('Receipt verification only. To repeat AArch64 CPU execution run offline_verify.py in the pinned venv.')

if __name__=='__main__': main()
