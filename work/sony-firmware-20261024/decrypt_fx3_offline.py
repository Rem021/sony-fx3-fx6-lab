"""Offline-only FX3 official update inspection. No USB, no device writes or execution.
FDAT block format follows pinned public fwtool source; AST literal keys only.
"""
import ast, datetime, hashlib, io, json, pathlib, struct, tarfile, time, urllib.request, zlib
from Crypto.Cipher import AES
ROOT=pathlib.Path(__file__).resolve().parent
PIN='3955d7890fc38daf942bb52827599bfe35de4a14'
SRC='https://raw.githubusercontent.com/DavidBuchanan314/fwtool.py/'+PIN+'/fwtool/sony/constants.py'
start=time.monotonic();src=urllib.request.urlopen(SRC,timeout=15).read();keys={}
for n in ast.parse(src).body:
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Name) and t.id in ['key_aes','key_cxd90057_k8']:keys[t.id]=ast.literal_eval(n.value)
meta=json.loads((ROOT/'ufu-header-analysis.json').read_text())['packages']['fx3-7.02']
p=ROOT/'fx3-7.02-BODYDATA.DAT';outp=ROOT/'fx3-7.02-decrypted.fdat'
size=p.stat().st_size
with p.open('rb') as f:
 crc=0;remaining=size-12
 while remaining:
  b=f.read(min(4*1024*1024,remaining));remaining-=len(b);crc=zlib.crc32(b,crc)
 sz,typ,expected=struct.unpack('>I4sI',f.read(12))
 assert sz==4 and typ==b'DEND' and expected==crc, 'Full UFU CRC mismatch'
with p.open('rb') as f:
 offset=meta['fdat_payload_offset'];encrypted_size=meta['fdat_payload_size']-0x110
 assert encrypted_size%1024==0
 f.seek(offset+encrypted_size);iv=f.read(16)
 f.seek(offset);cipher=AES.new(keys['key_cxd90057_k8'],AES.MODE_CBC,iv)
 blocks=encrypted_size//1024;done=0;h=hashlib.sha256();out_size=0
 with outp.open('wb') as out:
  while done<blocks:
   n=min(4096,blocks-done);enc=f.read(n*1024)
   if done==0:dec=AES.new(keys['key_aes'],AES.MODE_ECB).decrypt(enc[:512])+cipher.decrypt(enc[512:])
   else:dec=cipher.decrypt(enc)
   pieces=[]
   for i in range(n):
    block=dec[i*1024:(i+1)*1024];checksum,flags=struct.unpack_from('<HH',block)
    assert sum(struct.unpack('<511H',block[2:]))&0xffff==checksum, f'FDAT checksum {done+i}'
    assert bool(flags&0x8000)==(done+i==blocks-1), f'FDAT end flag {done+i}'
    assert flags&0x7fff<=1020
    pieces.append(block[4:4+(flags&0x7fff)])
   data=b''.join(pieces);out.write(data);h.update(data);out_size+=len(data);done+=n
   if done%131072==0:print('verified decrypted blocks',done,'/',blocks,flush=True)
assert out_size==meta['fdathdr']['firmware_offset']+meta['fdathdr']['firmware_size']
class Slice(io.RawIOBase):
 def __init__(self,path,start,size):self.f=path.open('rb');self.start=start;self.size=size;self.pos=0
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,n,whence=0):
  self.pos=n if whence==0 else self.pos+n if whence==1 else self.size+n
  if not 0<=self.pos<=self.size:raise ValueError('seek outside view')
  return self.pos
 def read(self,n=-1):
  n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
  self.f.seek(self.start+self.pos);b=self.f.read(n);self.pos+=len(b);return b
 def close(self):self.f.close();super().close()
firm=meta['fdathdr'];view=Slice(outp,firm['firmware_offset'],firm['firmware_size']);magic=view.read(512);view.seek(0)
members=[]
with tarfile.open(fileobj=view,mode='r:*') as tar:
 for m in tar:
  members.append({'name':m.name,'size':m.size,'type':m.type.decode('ascii'),'data_offset_in_tar':m.offset_data})
manifest={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_update':str(p),'source_sha256':json.loads((ROOT/'fx3-7.02-download-receipt.json').read_text())['sha256'],'tool_source_commit':PIN,'constants_source':SRC,'constants_source_sha256':hashlib.sha256(src).hexdigest(),'outer_crc32_matches':True,'outer_crc32':hex(crc),'decrypted_blocks':blocks,'all_block_checksums_match':True,'all_end_flags_match':True,'decrypted_fdat_size':out_size,'decrypted_fdat_sha256':h.hexdigest(),'firmware_tar_offset':firm['firmware_offset'],'firmware_tar_size':firm['firmware_size'],'firmware_tar_first512_sha256':hashlib.sha256(magic).hexdigest(),'tar_members':members,'seconds':round(time.monotonic()-start,2),'scope':'complete official update FDAT decrypted and tar enumerated; embedded file systems not yet unpacked; no firmware executed/repacked/flashed; no camera connected'}
(ROOT/'fx3-7.02-offline-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(manifest,indent=2,ensure_ascii=False))
