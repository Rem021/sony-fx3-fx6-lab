#!/usr/bin/env python3
"""Read-only FX3/FX6 AP ELF and one bounded colorimetry dataflow edge audit."""
import hashlib
import json
from pathlib import Path
import struct

WORK=Path('/Volumes/KAFU2T/AI/Projects/Mac/work')
DONOR=WORK/'fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor'
FX3=WORK/'fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v5/projection-manifest-full-v5.json'
NAMES=['appFw.so','libIMDB.so','libmpr.so','libInfraSKD.so','libInfraAvbbc.so',
       'dataflowInfraFramework.so','libbackup.so','libosal_uipc.so','im.elf']

class ELF:
 def __init__(self,path):
  self.path=Path(path);self.b=self.path.read_bytes()
  assert self.b[:6]==b'\x7fELF\x02\x01'
  self.machine=struct.unpack_from('<H',self.b,18)[0]
  self.etype=struct.unpack_from('<H',self.b,16)[0]
  phoff=struct.unpack_from('<Q',self.b,32)[0];es,n=struct.unpack_from('<HH',self.b,54)
  self.loads=[]
  for i in range(n):
   t,fl,o,v,_,fs,ms,_=struct.unpack_from('<IIQQQQQQ',self.b,phoff+i*es)
   if t==1:self.loads.append((v,o,fs))
  off=struct.unpack_from('<Q',self.b,40)[0];es,n,ni=struct.unpack_from('<HHH',self.b,58)
  sh=[struct.unpack_from('<IIQQQQIIQQ',self.b,off+i*es) for i in range(n)]
  names=self.b[sh[ni][4]:sh[ni][4]+sh[ni][5]]
  self.sec={names[s[0]:].split(b'\0')[0].decode():s for s in sh}
 def at(self,va,n):
  for v,o,sz in self.loads:
   if v<=va and va+n<=v+sz:return self.b[o+va-v:o+va-v+n],o+va-v
  raise ValueError(hex(va))
 def string(self,va):
  for v,o,sz in self.loads:
   if v<=va<v+sz:return self.b[o+va-v:o+sz].split(b'\0')[0].decode(errors='replace')
  return None
 def dynsymbols(self):
  sy=self.sec['.dynsym'];st=self.sec['.dynstr'];out=[]
  for i in range(0,sy[5],sy[9]):
   off=sy[4]+i;name,info,other,shndx,value,size=struct.unpack_from('<IBBHQQ',self.b,off)
   begin=st[4]+name;n=self.b[begin:self.b.find(b'\0',begin)].decode(errors='replace')
   if n:out.append({'name':n,'defined':shndx!=0,'value':value,'type':info&15})
  return out
 def needed(self):
  dy=self.sec['.dynamic'];st=self.sec['.dynstr'];out=[]
  for i in range(0,dy[5],16):
   tag,val=struct.unpack_from('<QQ',self.b,dy[4]+i)
   if tag==1:
    begin=st[4]+val;out.append(self.b[begin:self.b.find(b'\0',begin)].decode())
  return out
 def reloc(self,where):
  for key in ('.rela.dyn','.rela.plt'):
   s=self.sec.get(key)
   if not s:continue
   for i in range(0,s[5],24):
    off,info,add=struct.unpack_from('<QQq',self.b,s[4]+i)
    if off==where:return {'section':key,'type':info&0xffffffff,'symbol_index':info>>32,'addend':add}
  return None

dm=json.loads((DONOR/'nflasha15-manifest.json').read_text())['entries']
fm=json.loads(FX3.read_text())['members']
pair={}
for name in NAMES:
 guest=('/usr/bin/' if name=='im.elf' else '/usr/lib/')+name
 fx3=next(x for x in fm if x.get('guest_path')==guest and x.get('type')=='regular')
 source_path=('/bin/' if name=='im.elf' else '/lib/')+name
 fx6=next(x for x in dm if x['path']==source_path and x['kind']=='file')
 p3=Path(fx3['local_file']);p6=DONOR/'nflasha15-files'/fx6['stored_path']
 assert hashlib.sha256(p3.read_bytes()).hexdigest()==fx3['sha256']
 assert hashlib.sha256(p6.read_bytes()).hexdigest()==fx6['sha256']
 e3,e6=ELF(p3),ELF(p6)
 s3,s6=e3.dynsymbols(),e6.dynsymbols()
 imp3={x['name'] for x in s3 if not x['defined']};imp6={x['name'] for x in s6 if not x['defined']}
 exp3={x['name'] for x in s3 if x['defined']};exp6={x['name'] for x in s6 if x['defined']}
 pair[name]={'fx3':{'path':str(p3),'sha256':fx3['sha256'],'elf_type':e3.etype,'machine':e3.machine,
                    'imports':len(imp3),'exports':len(exp3),'needed':e3.needed()},
             'fx6':{'path':str(p6),'original_path':source_path,'stored_path':fx6['stored_path'],
                    'sha256':fx6['sha256'],'elf_type':e6.etype,'machine':e6.machine,
                    'imports':len(imp6),'exports':len(exp6),'needed':e6.needed()},
             'same_sha256':fx3['sha256']==fx6['sha256'],
             'imports_only_fx6_count':len(imp6-imp3),'exports_only_fx6_count':len(exp6-exp3),
             'imports_only_fx3_count':len(imp3-imp6),'exports_only_fx3_count':len(exp3-exp6)}
 pair[name]['fx3'].pop('needed') if name not in ('appFw.so','im.elf') else None
 pair[name]['fx6'].pop('needed') if name not in ('appFw.so','im.elf') else None

db3=ELF(pair['libIMDB.so']['fx3']['path']);db6=ELF(pair['libIMDB.so']['fx6']['path'])
def app_entry(e,base):
 rows=[]
 for i in range(400):
  va=base+0x100+i*0x48
  try:raw,fo=e.at(va,0x48)
  except ValueError:break
  ptr=struct.unpack_from('<Q',raw,0x10)[0]
  if e.string(ptr)=='appFw.so':
   entry={'index':i,'va':hex(va),'file_offset':hex(fo),'kind':hex(struct.unpack_from('<I',raw)[0]),
          'target_mask':hex(struct.unpack_from('<I',raw,8)[0]),'path':'appFw.so',
          'init':e.string(struct.unpack_from('<Q',raw,0x18)[0]),
          'path_relocation':e.reloc(va+0x10),'init_relocation':e.reloc(va+0x18)}
   rows.append(entry)
 assert len(rows)==1,rows
 return rows[0]
entry3=app_entry(db3,0x1cd38);entry6=app_entry(db6,0x1e870)
assert entry3['init']==entry6['init']=='Application_System_Init'

app6=ELF(pair['appFw.so']['fx6']['path']);flow6=ELF(pair['dataflowInfraFramework.so']['fx6']['path'])
flow3=ELF(pair['dataflowInfraFramework.so']['fx3']['path'])
symbol='_ZN33C_DataflowInfra_Entry_YcStateInfo19SetData_ColorimetryEh'
assert symbol in {x['name'] for x in app6.dynsymbols() if not x['defined']}
provider=next(x for x in flow6.dynsymbols() if x['name']==symbol and x['defined'])
assert provider['value']==0x382ec
assert flow6.at(0x382ec,8)[0].hex()=='01740039c0035fd6' # strb w1,[x0,#0x1d]; ret
provider3=next(x for x in flow3.dynsymbols() if x['name']==symbol and x['defined'])
assert provider3['value']==0x37968 and flow3.at(0x37968,8)[0]==flow6.at(0x382ec,8)[0]
def word(e,va):return struct.unpack('<I',e.at(va,4)[0])[0]
def bl(e,va):
 w=word(e,va);assert w>>26==0b100101
 imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 return va+4*imm
assert word(app6,0x20fa668)==0xb9404e60 # ldr w0,[x19,#0x4c]
assert word(app6,0x20fa500)==0xaa0003f3 # x19 <- input x0
assert bl(app6,0x20d1f64)==0x20fa4f0 # caller -> payload builder
assert bl(app6,0x20fa66c)==0x20ee044 # bounded enum converter
assert bl(app6,0x20fa678)==0xb18160 # SetData_Colorimetry PLT
assert app6.reloc(0x2ef19b8)['type']==1026
assert 'extern_BKID_APP_EXTERN_BASE_ISO' in app6.string(0x25364f8)
assert word(app6,0x1a6845c)==0xd0005662 and word(app6,0x1a68464)==0x9113e042
assert bl(app6,0x1a68470)==0x2167784
color={'caller_va':'0x20d1f64','builder_va':'0x20fa4f0',
       'builder_input_va':'0x20fa500','source_field':'[x19+0x4c] uint32','source_load_va':'0x20fa668',
       'conversion_call_va':'0x20fa66c','conversion_target_va':'0x20ee044',
       'setter_call_va':'0x20fa678','setter_plt_va':'0xb18160',
       'setter_jump_slot_va':'0x2ef19b8','setter_relocation':app6.reloc(0x2ef19b8),
       'provider':str(flow6.path),'provider_sha256':pair['dataflowInfraFramework.so']['fx6']['sha256'],
       'provider_va':'0x382ec','consumer_write':'strb w1,[x0,#0x1d]',
       'fx3_provider_va':'0x37968','fx3_setter_same_8_bytes':True,
       'input_meaning':'YcStateInfo colorimetry enum, not proven Cine EI or white balance setting',
       'ipc_or_av_consumption':'not bound'}
print(json.dumps({'schema':'fx3-fx6-ap-abi-comparison-v1','level':'static original bytes',
                  'libraries':pair,'imdb_app_entry':{'fx3':entry3,'fx6':entry6},
                  'bounded_colorimetry_edge':color,
                  'cine_ei_candidate':{'diagnostic_string_va':'0x25364f8',
                    'diagnostic_xref_va':'0x1a6845c','diagnostic_call_va':'0x1a68470',
                    'diagnostic_target_va':'0x2167784',
                    'status':'function-name diagnostic reference only; setter and IPC not identified'},
                  'direct_app_dependencies_delta':{
                     'fx6_only':sorted(set(pair['appFw.so']['fx6']['needed'])-set(pair['appFw.so']['fx3']['needed'])),
                     'fx3_only':sorted(set(pair['appFw.so']['fx3']['needed'])-set(pair['appFw.so']['fx6']['needed']))},
                  'scope':'ELF architecture/import-export names are screening, not binary ABI equivalence',
                  'requested_cine_ei_or_wb_to_ipc_closed':False,
                  'unknown':['Cine EI/white balance producer to IPC/AV consumer not yet bound',
                             'FX6 private ISP ABI and FX3 sensor coupling','runtime mixing and cold-start identity'],
                  'install_ready':False},ensure_ascii=False,indent=2))
