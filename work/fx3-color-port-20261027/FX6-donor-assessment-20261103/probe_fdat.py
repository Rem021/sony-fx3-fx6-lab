"""Read-only first FDAT block check; public upstream constants never printed or saved."""
import ast,base64,hashlib,json,pathlib,struct,subprocess,urllib.request,zlib
from Crypto.Cipher import AES
P=pathlib.Path(__file__).resolve().parent
pin='3955d7890fc38daf942bb52827599bfe35de4a14'
u=f'https://api.github.com/repos/DavidBuchanan314/fwtool.py/contents/fwtool/sony/constants.py?ref={pin}'
s=base64.b64decode(json.load(urllib.request.urlopen(u,timeout=30))['content'])
keys={}
for node in ast.parse(s).body:
 if isinstance(node,ast.Assign):
  for target in node.targets:
   if isinstance(target,ast.Name) and target.id in ('key_aes','key_cxd90057_k0','key_cxd90057_k8'):keys[target.id]=ast.literal_eval(node.value)
b=(P/'fx6-prefix-curl.bin').read_bytes();off=84;size=847081744;total=847081840
start=off+size-0x110
url='https://di.update.sony.net/NEX/Dobb4b83c7/BODYDATA.DAT'
tail=subprocess.check_output(['curl','-fsSL','--max-time','40','--range',f'{start}-{total-1}',url])
assert len(tail)==total-start
(P/'fx6-tail.bin').write_bytes(tail)
enc=b[off:off+1024];first=AES.new(keys['key_aes'],AES.MODE_ECB).decrypt(enc[:512]);matches=[]
for name in ('key_cxd90057_k0','key_cxd90057_k8'):
 t=first+AES.new(keys[name],AES.MODE_CBC,tail[:16]).decrypt(enc[512:]);expected,flags=struct.unpack_from('<HH',t);d=t[4:]
 if sum(struct.unpack('<511H',t[2:]))&65535==expected and d[:8]==b'UDTRFIRM':
  slots=[]
  for i in range(28):
   at=64+16*i
   if d[at]:
    offset,length=struct.unpack_from('<II',d,at+4)
    slots.append({'slot':i,'mode':d[at:at+1].decode(errors='replace'),'offset':offset,'bytes':length})
  matches.append({'scheme':name,'magic':d[:8].decode(),'version_tag':d[12:16].decode(errors='replace'),'firmware_version':f'{d[33]:x}.{d[32]:02x}','model_id':hex(struct.unpack_from('<I',d,36)[0]),'filesystem_count':struct.unpack_from('<I',d,56)[0],'filesystem_slots':slots,'header_crc_matches':zlib.crc32(d[12:512])==struct.unpack_from('<I',d,8)[0],'block_checksum_matches':True})
r={'constants_source_commit':pin,'constants_sha256':hashlib.sha256(s).hexdigest(),'prefix_sha256':hashlib.sha256(b).hexdigest(),'tail_sha256':hashlib.sha256(tail).hexdigest(),'matches':matches,'scope':'first block only; neither full firmware extraction nor signature verification nor RAW/ISP compatibility'}
(P/'fdat-probe.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
