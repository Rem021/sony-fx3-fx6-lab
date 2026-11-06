#!/usr/bin/env python3
"""Read-only decode of fixed Sony UFU/FDAT using pinned fwtool methods."""
import hashlib, json, pathlib, shutil, sys

ROOT=pathlib.Path(__file__).resolve().parent
UP=ROOT/'fwtool.py-3955d7890fc38daf942bb52827599bfe35de4a14'
sys.path.insert(0,str(UP))
from fwtool.sony import dat,fdat,constants

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()

def main():
 p=ROOT/'BODYDATA.DAT'
 receipt=json.loads((ROOT/'download-receipt.json').read_text())
 assert p.stat().st_size==847081840 and sha(p)==receipt['sha256']
 with p.open('rb') as inp:
  data=dat.readDat(inp)  # full UFU DEND CRC32
  encrypted=data.firmwareData
  assert encrypted.size==847081744
  plain=ROOT/'firmware.fdat'
  crypter=fdat.AesCbcCrypter(constants.key_aes,constants.key_cxd90057_k0)
  with plain.open('wb') as out:
   source=crypter.decrypt(encrypted)
   blocks=0
   while b:=source.read(1020*4096):
    out.write(b);blocks+=len(b)//1020
    if blocks%65536<4096:print('decrypted blocks',blocks,flush=True)
  with plain.open('rb') as f:
   assert fdat.isFdat(f)
   obj=fdat.readFdat(f) # header CRC and mode/offset checks
   assert obj.version=='6.01' and obj.model==0x91040086
   metadata={'model':hex(obj.model),'version':obj.version,'region':obj.region,
             'crypter':'CXD90057_k0','fdat_sha256':sha(plain),
             'fdat_bytes':plain.stat().st_size,
             'ufU_crc32':'verified by pinned fwtool dat.readDat',
             'fdat_header_crc32':'verified by pinned fwtool fdat.readFdat',
             'fdat_block_checksums':'all verified by pinned fwtool AesCbcCrypter',
             'official_signature':'not verified'}
   for attr,name in [('fs','updater.img'),('firmware','firmware.tar')]:
    part=getattr(obj,attr); dest=ROOT/name
    with dest.open('wb') as o: shutil.copyfileobj(part,o,8*1024*1024)
    metadata[name]={'bytes':dest.stat().st_size,'sha256':sha(dest)}
   (ROOT/'unpack-receipt.json').write_text(json.dumps(metadata,indent=2)+'\n')
   print(json.dumps(metadata),flush=True)

if __name__=='__main__':main()
