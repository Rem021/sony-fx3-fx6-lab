#!/usr/bin/env python3
"""Bounded structure checks on new type3 donor; no guessed cipher/key tests."""
import bz2,collections,hashlib,json,math,struct,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
PIN='93d01601322e3d1931a76b1c6f4f3bfdfb9a0745cfc0ec4eecb253c694b30d5c'
def sha(b):return hashlib.sha256(b).hexdigest()
def positions(b,token):
    start=0;out=[]
    while (start:=b.find(token,start))>=0:out.append(start);start+=len(token)
    return out
def main():
    target=HERE/'payload-structure-results.json';assert not target.exists()
    b=(HERE/'outer-members/VENICE/DATA23213').read_bytes();assert sha(b)==PIN
    count=collections.Counter(b[:1048576]);entropy=-sum(n/1048576*math.log2(n/1048576) for n in count.values())
    magic={name:positions(b,token) for name,token in [('ELF',b'\x7fELF'),('XZ',b'\xfd7zXZ\x00'),('SquashFS',b'hsqs'),
        ('UBI',b'UBI#'),('CPIO',b'070701'),('tar_ustar',b'ustar'),('ZIP',b'PK\x03\x04'),('zstd',b'\x28\xb5\x2f\xfd')]}
    gzip=[];bzip=[]
    for at in positions(b,b'\x1f\x8b\x08'):
        row=dict(offset=at)
        try:
            decoder=zlib.decompressobj(31);out=decoder.decompress(b[at:at+1048576],16*1048576)
            row.update(output_bytes=len(out),complete_stream=decoder.eof,valid_complete_stream=decoder.eof)
        except zlib.error as e:row.update(valid_complete_stream=False,rejection=str(e))
        gzip.append(row)
    for at in positions(b,b'BZh'):
        row=dict(offset=at,level_byte=b[at+3])
        if b[at+3] not in b'123456789':row.update(valid_complete_stream=False,rejection='invalid bzip2 block-size marker')
        else:
            try:
                decoder=bz2.BZ2Decompressor();out=decoder.decompress(b[at:at+1048576],max_length=16*1048576)
                row.update(output_bytes=len(out),complete_stream=decoder.eof,valid_complete_stream=decoder.eof)
            except OSError as e:row.update(valid_complete_stream=False,rejection=str(e))
        bzip.append(row)
    assert not any(r['valid_complete_stream'] for r in gzip+bzip)
    n=len(b);v=struct.unpack_from('<Q',b,n-16)[0]
    old=json.loads((TASK/'donor-20261028/donor-inner-source-inventory.json').read_text())['files'];relations=[]
    for label,raw in [('VENICE_V630_type3',b)]+[(r['version']+'_type4',Path(r['path']).read_bytes()) for r in old]:
        if label!='VENICE_V630_type3':assert sha(raw)==next(r['sha256'] for r in old if label==r['version']+'_type4')
        value=struct.unpack_from('<Q',raw,len(raw)-16)[0]
        relations.append(dict(version=label,bytes=len(raw),sha256=sha(raw),last16_hex=raw[-16:].hex(),
            footer_little_endian_u64=value,residual_after_rounding_to8=len(raw)-((value+7)//8*8)))
    assert all(r['residual_after_rounding_to8']==296 for r in relations)
    out=dict(type3_payload_sha256=PIN,bytes=n,first_1MiB_entropy_bits_per_byte=entropy,
        signatures=magic,gzip_candidates=gzip,bzip2_candidates=bzip,
        clear_colour_marker_hits={s:positions(b,s.encode()) for s in ['WhiteBalance','S-Gamut3','demosaic','BinaryPackProperty','ProductCodeVersion']},
        cross_generation_footer_relations=relations,
        scope='New official type3 payload structure only. Candidate gzip/bzip2 streams are bounded and not accepted without valid completion. Shared footer relation and entropy do not identify cipher, signature, key or decryption. No private keys, native Sony code, device, generated firmware or whole-ISP recovery.')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(payload_bytes=n,XML_type='type3',gzip_candidates=len(gzip),bzip_candidates=len(bzip),
        validated_compressed_streams=0,footer_relation_compared_versions=len(relations),residual296=True,complete_ISP_recovered=False)))
if __name__=='__main__':main()
