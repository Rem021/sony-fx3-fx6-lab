#!/usr/bin/env python3
"""Search every decoded FDAT byte for plain EXBL candidates; no boot execution."""
import hashlib,json,mmap,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;FW=TASK.parent/'sony-firmware-20261024'
FDAT=FW/'fx3-7.02-decrypted.fdat';PIN='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
def main():
    out=HERE/'FDAT-EXBL-candidate-scan.json';assert not out.exists()
    h=hashlib.sha256()
    with FDAT.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    assert FDAT.stat().st_size==808704512 and h.hexdigest()==PIN
    manifest=json.loads((FW/'fx3-7.02-offline-manifest.json').read_text())
    members=[]
    for x in manifest['tar_members']:
        if x['type']=='0':
            at=manifest['firmware_tar_offset']+x['data_offset_in_tar'];members.append((at,at+x['size'],x['name']))
    candidates=[]
    expected=[4,0xfe040800,0x21800,0xfe049000]
    with FDAT.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
        start=0
        while (at:=data.find(b'EXBL',start))>=0:
            start=at+1
            member=next(((lo,hi,n) for lo,hi,n in members if lo<=at<hi),None)
            block=data[at:at+0x800];values=[struct.unpack_from('<I',block,off)[0] for off in [0x68,0x6c,0x74,0x78]] if len(block)>=0x7c else []
            plausible=bool(values and values[0]>0 and values[0]<0x1000000 and 0<values[2]<=0x1000000 and values[2]%512==0
                and values[1]%4==0 and values[1]<=values[3]<values[1]+values[2])
            candidates.append(dict(FDAT_offset=hex(at),member=member[2] if member else None,
                member_relative_offset=hex(at-member[0]) if member else None,
                complete_0x800_within_member=bool(member and at+0x800<=member[1]),
                candidate_prefix_sha256=hashlib.sha256(block).hexdigest(),candidate_fields=list(map(hex,values)),
                matches_current_CP_pformat_primary_fields=values==expected,
                bounded_plausibility_filter=plausible,
                filter_scope='Heuristic only: positive results would require original FX3 field/use verification, not be accepted as a boot0 image.'))
    result=dict(FDAT_source=str(FDAT),FDAT_bytes=808704512,FDAT_sha256=PIN,
        searched_pattern='EXBL',plain_magic_candidates=len(candidates),candidates=candidates,
        bounded_plausible_candidates=sum(x['bounded_plausibility_filter'] for x in candidates),
        current_CP_pformat_field_matches=sum(x['matches_current_CP_pformat_primary_fields'] for x in candidates),
        expected_CP_pformat_fields=list(map(hex,expected)),
        scope='Exact byte search across one original decrypted public FDAT container. It does not inspect separately compressed/encrypted representations or live boot0/NOR. No-match/invalid candidates do not prove no EXBL data exists elsewhere. No code, keys, updater, device or native Sony program executed.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['plain_magic_candidates','bounded_plausible_candidates','current_CP_pformat_field_matches','candidates']}))
if __name__=='__main__':main()
