"""Small ELF64 LE file-only reader; no loader or guest execution."""
from pathlib import Path
import struct,hashlib,json
O=Path(__file__).resolve().parent
class ELF:
 def __init__(self,p):
  self.path=Path(p);self.data=self.path.read_bytes();d=self.data
  assert d[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',d,18)[0]==183
  off=struct.unpack_from('<Q',d,40)[0];ents,n,st=struct.unpack_from('<HHH',d,58);raw=[struct.unpack_from('<IIQQQQIIQQ',d,off+i*ents) for i in range(n)];names=d[raw[st][4]:raw[st][4]+raw[st][5]]
  def z(b,o):return b[o:b.find(b'\0',o)].decode()
  self.sections={}
  for r in raw:
   name=z(names,r[0]);self.sections[name]={'type':r[1],'flags':r[2],'address':r[3],'offset':r[4],'size':r[5],'link':r[6],'entry_size':r[9],'data':d[r[4]:r[4]+r[5]] if r[1]!=8 else b''}
  self.raw=raw;self.symbols={}
  for index,r in enumerate(raw):
   if r[1] not in (2,11):continue
   strings=d[raw[r[6]][4]:raw[r[6]][4]+raw[r[6]][5]]
   for a in range(r[4],r[4]+r[5],r[9]):
    no,info,other,section,value,size=struct.unpack_from('<IBBHQQ',d,a);name=z(strings,no)
    if name:self.symbols.setdefault(name,[]).append({'info':info,'section':section,'address':value,'size':size,'table':r[1]})
  ds=self.sections['.dynstr']['data'];self.needed=[];self.soname=None
  for a in range(0,len(self.sections['.dynamic']['data']),16):
   tag,value=struct.unpack_from('<QQ',self.sections['.dynamic']['data'],a)
   if tag==1:self.needed.append(z(ds,value))
   if tag==14:self.soname=z(ds,value)
 def describe(self):return {'path':str(self.path),'bytes':len(self.data),'sha256':hashlib.sha256(self.data).hexdigest(),'needed':self.needed,'soname':self.soname,'sections':{n:{k:v for k,v in s.items() if k!='data'}|{'sha256':hashlib.sha256(s['data']).hexdigest()} for n,s in self.sections.items()}}
if __name__=='__main__':
 actual=ELF(json.loads((O/'BINDING.json').read_text())['actual_helper']);base=ELF(O/'build/gpe-r41-baseline.so');cand=ELF(O/'build/gpe-r41-candidate.so')
 diffs={n:{'actual_bytes':s['size'],'baseline_bytes':base.sections.get(n,{}).get('size'),'same_data':s['data']==base.sections.get(n,{}).get('data'),'same_address':s['address']==base.sections.get(n,{}).get('address')} for n,s in actual.sections.items() if s['flags']&2}
 print(json.dumps({'actual_to_rebuilt_alloc_sections':diffs,'descriptions':[e.describe() for e in (actual,base,cand)]},indent=2))
