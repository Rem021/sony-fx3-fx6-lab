#!/usr/bin/env python3
"""Bounded V2.01 format checks and explicit counterexample to a footer hypothesis."""
import bz2,collections,hashlib,json,math,struct,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
PIN='498d047ca2f6f11d54c502a399e2c5a9f4740e6fae4913eba1aaaf486349c785'
def sha(b):return hashlib.sha256(b).hexdigest()
def positions(b,needle):
    out=[];at=0
    while (at:=b.find(needle,at))>=0:out.append(at);at+=len(needle)
    return out
def main():
    dest=HERE/'early-payload-structure.json';assert not dest.exists()
    b=(HERE/'outer-members/VENICE/DATA23213').read_bytes();assert sha(b)==PIN
    sample=b[:1024*1024];counts=collections.Counter(sample)
    entropy=-sum(n/len(sample)*math.log2(n/len(sample)) for n in counts.values())
    magic={n:positions(b,t) for n,t in [('ELF',b'\x7fELF'),('XZ',b'\xfd7zXZ\x00'),('SquashFS',b'hsqs'),
        ('UBI',b'UBI#'),('CPIO',b'070701'),('tar_ustar',b'ustar'),('ZIP',b'PK\x03\x04'),('zstd',b'\x28\xb5\x2f\xfd')]}
    candidates=[]
    for kind,needle in [('gzip',b'\x1f\x8b\x08'),('bzip2',b'BZh')]:
        for at in positions(b,needle):
            row=dict(kind=kind,offset=at,input_limit_bytes=1048576,output_limit_bytes=16*1048576)
            try:
                if kind=='gzip':
                    d=zlib.decompressobj(31);data=d.decompress(b[at:at+1048576],16*1048576)
                else:
                    d=bz2.BZ2Decompressor();data=d.decompress(b[at:at+1048576],max_length=16*1048576)
                row.update(output_bytes=len(data),complete_stream=d.eof)
            except (zlib.error,OSError) as e:row.update(complete_stream=False,rejection=str(e))
            candidates.append(row)
    old=json.loads((TASK/'donor-20261028/donor-inner-source-inventory.json').read_text())['files']
    sources=[dict(version='VENICE_V201',XML_type='type3',path=str(HERE/'outer-members/VENICE/DATA23213'),sha256=PIN),
        dict(version='VENICE_V630',XML_type='type3',path=str(TASK/'donor-venice1-20261029/outer-members/VENICE/DATA23213'),sha256='93d01601322e3d1931a76b1c6f4f3bfdfb9a0745cfc0ec4eecb253c694b30d5c')]
    sources += [dict(version='VENICE2_'+r['version'],XML_type='type4',path=r['path'],sha256=r['sha256']) for r in old]
    relations=[]
    for s in sources:
        raw=Path(s['path']).read_bytes();assert sha(raw)==s['sha256']
        n=len(raw);v=struct.unpack_from('<Q',raw,n-16)[0]
        relations.append(dict(**s,bytes=n,footer_little_endian_u64=v,footer_last8_hex=raw[-8:].hex(),
            N_minus_L=n-v,rounded_residuals={str(q):n-((v+q-1)//q*q) for q in [8,16,32]},
            fits_old_round8_plus296=n==((v+7)//8*8)+296,
            fits_round16_plus296=n==((v+15)//16*16)+296))
    result=dict(original_payload_bytes=len(b),original_payload_sha256=PIN,entropy_first_1MiB=entropy,magic_candidates=magic,
        compressed_candidates=candidates,valid_complete_compressed_streams=sum(r['complete_stream'] for r in candidates),
        clear_markers={t:positions(b,t.encode()) for t in ['WhiteBalance','S-Gamut3','demosaic','BinaryPackProperty','ProductCodeVersion']},
        footer_comparison=relations,
        correction=dict(old_scope='Four previously inspected payloads satisfy round8(L)+296; original sealed observations remain valid.',
            new_counterexample='VENICE V2.01 type3: N=169621368, L=169621057; round8 residual304, not296.',
            universal_round8_rule_supported=False,universal_round16_rule_supported=False,
            limited_observation='Two type3 samples fit round16(L)+296; three type4 samples fit round8(L)+296. This is not a proven format or cipher.'),
        scope='Host-only structural measurements of pinned original payloads; high entropy, alignment and absent markers do not identify encryption or signature. No cipher/key trials, private signing material, native Sony execution, device actions, whole ISP recovery or modified firmware.')
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(bytes=len(b),entropy=entropy,magic_counts={k:len(v) for k,v in magic.items()},
        gzip_candidates=sum(r['kind']=='gzip' for r in candidates),bzip2_candidates=sum(r['kind']=='bzip2' for r in candidates),
        valid_complete_compressed_streams=result['valid_complete_compressed_streams'],
        relations=[{k:r[k] for k in ['version','rounded_residuals','fits_old_round8_plus296','fits_round16_plus296']} for r in relations]),ensure_ascii=False))
if __name__=='__main__':main()
