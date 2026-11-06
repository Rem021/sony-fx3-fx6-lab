"""Read all audit records and check every original instruction against ELF bytes."""
from pathlib import Path
import hashlib,json,struct,collections,plistlib,subprocess
D=Path(__file__).resolve().parent
P=D.parents[1]/'audits/gpe-blend-p3/gpe-blend-proof.json'
d=json.loads(P.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out={'proof_sha256':sha(P),'checks':d['checks'],'libraries':{},'cases':{},'gate':d['p3_implementation_gate'],'scope':'Read-only audit validation; no execution of original binaries or pixel engine'}
for name,lib in d['libraries'].items():
 p=Path(lib['path']);data=p.read_bytes();assert sha(p)==lib['sha256']
 phoff=struct.unpack_from('<Q',data,32)[0];phsz,phnum=struct.unpack_from('<HH',data,54)
 ph=[struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsz) for i in range(phnum)]
 count=0
 for block,instructions in lib['blocks'].items():
  last=None
  for ins in instructions:
   va=int(ins['va'],16);raw=bytes.fromhex(ins['bytes']);assert len(raw)==4 and va%4==0 and ins['asm']
   assert last is None or va==last+4;last=va
   seg=next(s for s in ph if s[0]==1 and s[3]<=va and va+4<=s[3]+s[5])
   off=seg[2]+va-seg[3];assert data[off:off+4]==raw
   count+=1
 out['libraries'][name]={'sha256':sha(p),'blocks':len(lib['blocks']),'instructions_verified':count}
for key in ['cases','flag_cases','conversion_cases','png_cpu_cases','flip_cpu_cases']:
 records=d[key]
 for r in records:
  for w in r.get('register_writes',[]):
   assert int(w['reg'],16)>=0 and 0<=w['value']<=0xffffffff and int(w['caller_va'],16)%4==0
 out['cases'][key]={'count':len(records),'status_counts':dict(collections.Counter(r.get('status','CPU_result') for r in records))}
# Visit every value, including complete descriptors, flags, mode tables,
# libObj instructions, PNG resource records and limitations.
def visit(v):
 if isinstance(v,dict):return 1+sum(visit(x) for x in v.values())
 if isinstance(v,list):return 1+sum(visit(x) for x in v)
 return 1
out['json_nodes_read']=visit(d)
out['full_u8_alpha_sweep']=d['full_u8_alpha_sweep']
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
(D/'proof-readback.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['proof_sha256','libraries','json_nodes_read']},indent=2))
