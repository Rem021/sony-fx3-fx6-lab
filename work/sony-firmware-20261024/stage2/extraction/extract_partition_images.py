#!/usr/bin/env python3
"""Bounded read-only carve from already verified FDAT, not a camera updater."""
import json,pathlib,hashlib,zlib
BASE=pathlib.Path(__file__).resolve().parent
SOURCE=BASE.parent.parent/'fx3-7.02-decrypted.fdat'
META=BASE.parent.parent/'fx3-7.02-offline-manifest.json'
ALLOWED={f'0700_part_image/dev/nflasha{n}':f'nflasha{n}.img' for n in [15,3,5,7,8]}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def main():
 d=json.loads(META.read_text());assert digest(SOURCE)==d['decrypted_fdat_sha256'];total=SOURCE.stat().st_size;rows=[]
 with SOURCE.open('rb') as f:
  for e in d['tar_members']:
   if e['name'] not in ALLOWED:continue
   off=d['firmware_tar_offset']+e['data_offset_in_tar'];size=e['size'];assert e['type']=='0' and off>=0 and 0<size<=total-off
   dest=BASE/ALLOWED[e['name']];assert dest.resolve().parent==BASE;f.seek(off);h=hashlib.sha256();crc=0;remaining=size
   with dest.open('wb') as out:
    while remaining:
     b=f.read(min(1024*1024,remaining));assert b;out.write(b);h.update(b);crc=zlib.crc32(b,crc);remaining-=len(b)
   row={'source_member':e['name'],'source_FDAT_offset':off,'output':str(dest),'size':size,'sha256':h.hexdigest(),'crc32':hex(crc&0xffffffff)};rows.append(row)
 (BASE/'partition-carve-manifest.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
