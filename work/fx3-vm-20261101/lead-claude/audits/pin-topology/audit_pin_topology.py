#!/usr/bin/env python3
"""Read-only AP/CP static audit; no guest execution. Writes adjacent proof only."""
from pathlib import Path
import io, json, struct, hashlib, re, sys, subprocess, plistlib
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT=Path(__file__).resolve().parent
LIB=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib'
PATHS={'ap':LIB/'appFw.so','cp':ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin','df':LIB/'dataflowInfraFramework.so'}
# Dataflow library spelling is resolved from the actual projection.
if not PATHS['df'].exists():
 candidates=[p for p in LIB.iterdir() if 'dataflow' in p.name.lower()]
 if len(candidates)==1:PATHS['df']=candidates[0]
DATA={k:p.read_bytes() for k,p in PATHS.items() if p.exists()}
ELF={k:ELFFile(io.BytesIO(b)) for k,b in DATA.items() if k!='cp'}
def read(k,a,n,zero=False):
 if k=='cp':
  assert 0x108000<=a and a+n<=0x108000+len(DATA[k]);return DATA[k][a-0x108000:a-0x108000+n]
 for seg in ELF[k].iter_segments():
  if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a and a+n<=seg['p_vaddr']+seg['p_memsz']:
   off=a-seg['p_vaddr'];nb=max(0,min(n,seg['p_filesz']-off))
   assert zero or nb==n,(k,hex(a),n,'NOBITS')
   return DATA[k][seg['p_offset']+off:seg['p_offset']+off+nb]+b'\0'*(n-nb)
 raise ValueError((k,hex(a),n))
def dis(k,a,n):
 c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM);c.skipdata=True
 return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(read(k,a,n),a)]
def string(k,a):return read(k,a,256).split(b'\0')[0].decode(errors='replace')
def u32(k,a):return struct.unpack('<I',read(k,a,4))[0]
def u64(k,a):return struct.unpack('<Q',read(k,a,8))[0]
def ctor(seed=0):
 """Evaluate only a closed, branch-free set of integer assignment instructions.
 No Unicorn/QEMU, no OS calls, and no Sony function invoked. Addresses are symbolic.
 """
 regs={f'x{i}':seed+i for i in range(31)};regs['sp']=0x100000000
 mem={};writes={};trace=dis('ap',0x1694028,0x323c)
 def get(r):
  if r in ('xzr','wzr'):return 0
  return regs.get('x'+r[1:] if r.startswith('w') else r,0)&((1<<(32 if r.startswith('w') else 64))-1)
 def put(r,v):
  if r not in ('xzr','wzr'):regs['x'+r[1:] if r.startswith('w') else r]=v&((1<<(32 if r.startswith('w') else 64))-1)
 def val(t):return int(t[1:],0) if t.startswith('#') else get(t)
 def store(a,v,n,va):
  assert 0x9ab0000<=a<a+n<=0x9ab6000 or 0xffff0000<=a<a+n<=0x100000000,(hex(a),va)
  for i,x in enumerate((v&((1<<(n*8))-1)).to_bytes(n,'little')):mem[a+i]=x;writes[a+i]=va
 def load(a,n):
  assert all(a+i in mem for i in range(n)),('uninitialized load',hex(a),n)
  return int.from_bytes(bytes(mem[a+i] for i in range(n)),'little')
 for row in trace:
  va=row['va'];m,op=row['instruction'].split(' ',1)
  if m=='ret':continue
  if m in ('adrp','mov','movk','add'):
   pp=op.split(', ');r=pp[0]
   if m=='adrp':v=int(pp[1][1:],0)
   elif m=='mov':v=val(pp[1])
   elif m=='add':v=val(pp[1])+val(pp[2])
   else:
    shift=int(pp[2].split('#')[1]);v=(get(r)&~(0xffff<<shift))|(val(pp[1])<<shift)
   put(r,v);continue
  assert m in ('str','stp','ldr','ldp'),row
  match=re.fullmatch(r'(.+), \[(\w+)(?:, #(-?0x[0-9a-f]+|-?\d+))?\](!)?(?:, #(0x[0-9a-f]+))?',op);assert match,row
  rr,base,offset,pre,post=match.groups();offset=int(offset or '0',0);a=get(base)+offset
  if pre:put(base,a)
  for j,r in enumerate(rr.split(', ')):
   n=4 if r.startswith('w') else 8
   if m in ('str','stp'):store(a+j*n,get(r),n,va)
   else:put(r,load(a+j*n,n))
  if post:put(base,get(base)+int(post,0))
 def rd(a,n):return bytes(mem.get(a+i,0) for i in range(n))
 return rd,writes,trace
TABLES=[0x9ab0d70,0x9ab1258,0x9ab1708,0x9ab1bb8,0x9ab2068,0x9ab2518,0x9ab29c8,0x9ab2e78,0x9ab3328,0x9ab3a08,0x9ab41b8,0x9ab4668,0x9ab4b18]
def tables():
 rd,writes,trace=ctor();out={}
 for a in TABLES:
  rows=[]
  for i in range(50):
   v=a+i*24;src,state,pad,dst=struct.unpack('<QIIQ',rd(v,24))
   def pin(p):return {'va':hex(p),'words':[hex(x) for x in struct.unpack('<4I',rd(p,16))]} if p else None
   rows.append({'index':i,'va':hex(v),'name':string('ap',u64('ap',0x4117648+i*8)),'source':pin(src),'state':state,'padding':pad,'destination':pin(dst),'stores':sorted(set(writes.get(v+j,'ELF_BSS_ZERO') for j in range(24)))})
  out[hex(a)]=rows
 return out,trace

def select(inp):
 mode,option,proxy,remote,network,stream=inp
 # Reconstruct actual signed-byte branch tables, not a guessed enum order.
 opt_target=0x2ebeb0c+4*struct.unpack('<b',read('ap',0x39a4708+option,1))[0] if 0<=option<=15 else 0x2ebec8c
 target=opt_target
 if target==0x2ebeb0c:
  target=0x2ebeb30+4*struct.unpack('<b',read('ap',0x39a4718+mode,1))[0] if 0<=mode<=5 else 0x2ebec40
 direct={0x2ebeb30:(0x9ab1258,1),0x2ebec18:(0x9ab1708,0),0x2ebec5c:(0x9ab1bb8,0),
         0x2ebec6c:(0x9ab2518,0),0x2ebec7c:(0x9ab3328,0),0x2ebebb4:(0x9ab2e78,0)}
 if target==0x2ebeb78:return (0x9ab3a08 if not proxy else (0x9ab41b8 if not network else 0x9ab2068)),0
 if target==0x2ebebdc:return (0x9ab4b18 if stream else 0x9ab29c8),0
 return direct.get(target,(None,None))

def pinwords(p):return tuple(int(x,16) for x in p['words'])
def wire(p):return (p[1],p[2],p[3],p[0])
def header(cmd,n):return struct.pack('<4H',0x1000,cmd,n,2)
def request(cmd,p,q=None):
 return header(cmd,40 if cmd==1 else 24)+struct.pack('<'+('8I' if cmd==1 else '4I'),*(wire(p)+wire(q) if cmd==1 else wire(p)[:3]+(0,)))
def response(cmd,p,state=1,status=0):
 # p is AP order [owner,type,direction,index]; wire descriptor rotates owner last.
 words=(p[1],p[2],p[3],state,p[0],status&0xffffffff) if cmd==0 else wire(p)+(status&0xffffffff,0)
 return header(0x8000|cmd,32)+struct.pack('<6I',*words)
def envelope(b,reply_id=0):return struct.pack('<IIHHIII',reply_id,0xa0a0a0a0,1,len(b)+24,24,len(b)+24,0)+b
def get_reply_id(provider):return provider if provider in (0x9284074a,0x9080003b) else 0

class SoftwarePins:
 """Proposed empty-queue software reference model, NOT Sony code execution.
 No frames, DMA buffers, physical output, or CP runtime are fabricated.
 """
 def __init__(self,pins):
  self.pins={p:{'peer':None,'state':1,'inflight':set(),'pending_hardware':True} for p in pins}
  self.leases={};self.next_lease=1
 def get(self,p):
  return response(0,p,state=self.pins[p]['state'],status=0) if p in self.pins else response(0,(0,255,255,0),state=255,status=-32)
 def connect(self,p,q):
  if p not in self.pins or q not in self.pins:return response(1,p,status=-32)
  a,b=self.pins[p],self.pins[q]
  if p[1]!=q[1]:return response(1,p,status=-23)
  if (p[2],q[2]) not in ((2,1),(3,3),(1,2)):return response(1,p,status=-22)
  if a['state']==2 or b['state']==2:return response(1,p,status=-24)
  if a['peer']==q and b['peer']==p:return response(1,p,status=0)
  if a['peer'] is not None or b['peer'] is not None:return response(1,p,status=-25)
  # One atomic software transaction replaces the CP's peer handshake ONLY for
  # endpoints explicitly owned by this software backend. Both queues stay empty.
  a.update(peer=q,state=0);b.update(peer=p,state=0)
  return response(1,p,status=0)
 def disconnect(self,p):
  if p not in self.pins:return response(2,p,status=-32)
  a=self.pins[p];q=a['peer']
  if a['state']==2:return response(2,p,status=-24)
  if q is None:return response(2,p,status=-26)
  b=self.pins[q]
  if a['inflight'] or b['inflight']:return response(2,p,status=-24)
  a.update(peer=None,state=1);b.update(peer=None,state=1)
  return response(2,p,status=0)
 def lease(self,p,q):
  # Synthetic ownership-test token, never a firmware DMM/unit handle or pixels.
  assert self.pins[p]['peer']==q and self.pins[q]['peer']==p
  n=self.next_lease;self.next_lease+=1;self.leases[n]=(p,q)
  self.pins[p]['inflight'].add(n);self.pins[q]['inflight'].add(n);return n
 def release(self,n):
  p,q=self.leases.pop(n)
  self.pins[p]['inflight'].remove(n);self.pins[q]['inflight'].remove(n)

BLOCKS={
 'ap':[(0x2b679dc,0x94),(0x2de1f84,0x40),(0x2ebe9c0,0x2fc),(0x2ebed60,0x25c),(0x2ebe188,0x5e0),(0x2ebe12c,0x5c),
       (0x2e106ec,0x54),(0x2e109d0,0x1a8),(0x2e10c80,0xf8),(0x2e10d78,0xb54),(0x2ebf3b0,0x94)],
 'cp':[(0x1bcaf2,0x28),(0x1bcfb6,0x160),(0x1bd2cc,0x82),(0x1bd34e,0x3c),(0x1bd5bc,0x40),
       (0x1bd6aa,0xb8),(0x1bd770,0x10),(0x5ba99a,0x5a),(0x5ba9f4,0x23c),(0x5badd0,0xe0),
       (0x5baeb0,0x170),(0x5bb1a2,0xde),(0x5bb7ce,0x3a),(0x18f408,0x4c),(0x5bbc86,0x10c),
       (0x608100,0x44),(0x608316,0x4a),(0x1e71d0,0xa6),(0x1e72ac,0x10c),(0x1e7400,0x112),
       (0x60b0c4,0x84),(0x1fb734,0x94),(0x1fb7f4,0xfc),(0x62dd4c,0x82),
       (0x4ead2c,0x9e),(0x5aa2f2,0x140),(0x56dcee,0xce),(0x15111c,0x5e),(0x56e866,0x66),
       (0x4ace28,0xbe),(0x4acf34,0x52),(0x21886c,0x60),(0x218a6a,0x2a),(0x65a554,0x8c),
       (0x56dc44,0xaa),(0x5ba3c0,0xb0),(0x5ba598,0x54),(0x6293c0,0x6e),(0x62d39c,0x5c),
       (0xac71a8,0x70),(0xac838a,0x6a),(0x60ed16,0x78),(0x61103a,0x90),(0x4ad2de,0x26),
       (0x62d4a0,0x2a),(0x4e0f64,0x26),(0x180d78,0x1d0),(0x180f9c,0x140)],
 'df':[(0x32278,0x2c),(0x32368,0x68),(0x33998,0x18),(0x320e8,0x3c)]}

CHECKS=[('ap',0x2b67a44,'bl #0x2de1f84'),('ap',0x2ebeb3c,'bl #0x2ebe188'),
 ('ap',0x2ebe30c,'cmp x22, #0x32'),('ap',0x2ebe40c,'bl #0x2e113f0'),('ap',0x2ebe5e8,'bl #0x2e11138'),
 ('ap',0x2ebe628,'cbz w22, #0x2ebe454'),('ap',0x2e10cc4,'mov w3, #-1'),
 ('ap',0x2e10eb4,'ldr w4, [x29, #0x8c]'),('ap',0x2e110e4,'ldr w4, [x29, #0x50]'),
 ('ap',0x2e11814,'ldr w4, [x29, #0x78]'),('ap',0x2e118c0,'mov w21, #0'),('ap',0x2e106f4,'cmp w3, w2'),
 ('ap',0x2e11644,'ldr w0, [x29, #0x58]'),('ap',0x2e1164c,'ldr w0, [x29, #0x5c]'),
 ('cp',0x1bd0d0,'beq.w #0x1bd2cc'),('cp',0x1bd0d6,'beq.w #0x1bd34e'),
 ('cp',0x1bd778,'bl #0x5ba9f4'),('cp',0x1bd5c4,'bl #0x5baeb0'),
 ('cp',0x1bd6b2,'bl #0x5bb7ce'),('cp',0x1bd71c,'bl #0x5bbaa4'),
 ('cp',0x5ba9ce,'str r1, [r0, #0x28]'),('cp',0x5badf4,'strh.w r0, [sp, #0xa]'),
 ('cp',0x5bae42,'str.w ip, [sp, #0x20]'),('cp',0x5bb222,'str r0, [sp, #0x20]'),
 ('cp',0x5bab0a,'mvn sb, #0x17'),('cp',0x5baba6,'mvn sb, #0x18'),
 ('cp',0x5bb0f0,'mvn sb, #0x19'),('cp',0x18f440,'mvn r4, #0x16'),
 ('cp',0x18f420,'mvn r4, #0x15'),('cp',0x1e736c,'bl #0x5ba9f4'),
 ('cp',0x2188c6,'b.w #0x5ba9f4')]

def rebuild():
 assert hashlib.sha256(DATA['ap']).hexdigest()=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
 assert hashlib.sha256(DATA['cp']).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
 ts,tr=tables();rd,writes,_=ctor();rd2,_,_=ctor(0x1234567800000000)
 assert rd(0x9ab0000,0x6000)==rd2(0x9ab0000,0x6000),'constructor globals depend on entry registers'
 inp=(1,0,1,0,1,0);selected,flags=select(inp)
 assert (selected,flags)==(0x9ab1258,1)
 assert u64('ap',0x3d20828)==0x1694028
 old=ts['0x9ab0d70'];new=ts[hex(selected)]
 assert all(r['source'] and r['state']==0 and r['destination'] is None for r in old)
 assert all(new[i]['source']==old[i]['source'] for i in range(50))
 diffs=[i for i in range(50) if (new[i]['state'],new[i]['destination'])!=(old[i]['state'],old[i]['destination'])]
 active=[i for i in diffs if new[i]['state']==1]
 assert diffs==[1,4,5,7,10,13,14,18,20,21,22,23,24,29]
 assert active==[7,10,13,14,18,20,21,22,23,24,29]
 proof={'scope':'Read-only static reconstruction and existing AP79 passive captures. No QEMU, guest code execution, camera, runtime mutation, lock, or Git.',
        'evidence_levels':{'tables':'branch-free assignment evaluator, checked against all 100 live selected/current rows after ASLR normalization',
           'runtime':'Only first GET is captured; projected later packets require the model replies and are not observed traffic',
           'model':'Proposed explicit empty-queue software backend, self checks only; no production implementation or CP execution'},
        'sources':{},'checks':[],'blocks':{},'constructor':{'init_array_va':'0x3d20828','function':'0x1694028','entry_register_independence_checked_twice':True,'instructions':tr},
        'tables':ts,'selection':{'input':list(inp),'table':hex(selected),'check_existing':flags,
          'option_jump_bytes':read('ap',0x39a4708,16).hex(),'mode_jump_bytes':read('ap',0x39a4718,6).hex(),
          'mode_option_matrix':[{'mode':m,'option':o,'selected':hex(t) if t else None,'check':f} for m in range(6) for o in range(16) for t,f in [select((m,o,1,0,1,0))]]},
        'differences':[new[i] for i in diffs], 'disconnect_requests_from_cold_state':[], 'projected_cold_software_requests':[]}
 def source(name,p):
  b=p.read_bytes();proof['sources'][name]={'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
 for k,p in PATHS.items():source(k,p)
 run=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap79tail-17293cc1'
 lb=source('AP79_serial',run/'serial.log');lines=lb.decode(errors='replace').split('\n')
 ev=[{'line':i+1,'text':l} for i,l in enumerate(lines) if any(x in l for x in ('FX3_CHANGE_MODE_INPUT','FX3_PIN_TOPOLOGY_',
     'FX3_BOOT_TAIL_REQUEST tid=327 destination=0x9284074a','FX3_BOOT_TAIL_FRAME destination=0x9284074a'))]
 proof['AP79_serial_evidence']=ev
 cap=next(r for r in ev if 'FX3_BOOT_TAIL_REQUEST' in r['text'])
 captured=bytes.fromhex(re.search(r'raw=([0-9a-f]+)',cap['text'])[1]);assert len(captured)==48
 assert captured==envelope(request(0,pinwords(new[7]['source'])),0x81cf61c0)
 ram=source('AP79_passive_RAM',run/'ui-gate-counters.bin');head=struct.unpack_from('<8Q',ram,0x8000)
 assert head[0]==0x31504f5447583346 and head[5:7]==(1,14)
 assert ram[0x7800:0x7818]==struct.pack('<6I',*inp)
 base=head[3]-0x9ab0d70;assert head[2]-base==selected
 captures=[]
 for off,a in ((0x8040,selected),(0x84f0,0x9ab0d70)):
  raw=ram[off:off+1200];normalized=bytearray(raw)
  for i in range(50):
   for j in (0,16):
    p=struct.unpack_from('<Q',raw,i*24+j)[0]
    if p:struct.pack_into('<Q',normalized,i*24+j,p-base)
  assert bytes(normalized)==rd(a,1200),(hex(a),'full 50-row capture differs')
  captures.append({'table_va':hex(a),'RAM_offset':hex(off),'raw':raw.hex(),'normalized':normalized.hex(),'all_50_rows_equal':True})
 proof['AP79_full_table_readback']={'ASLR_base':hex(base),'header':[hex(x) for x in head],'captures':captures}
 for k,aa in BLOCKS.items():
  proof['blocks'][k]={}
  for a,n in aa:
   ins=dis(k,a,n);assert sum(len(bytes.fromhex(r['bytes'])) for r in ins)==n
   proof['blocks'][k][hex(a)]={'raw':read(k,a,n).hex(),'instructions':ins,'may_contain_literals':k=='cp'}
 for k,a,want in CHECKS:
  got=dis(k,a,4)[0];assert got['instruction']==want,(k,hex(a),want,got)
  proof['checks'].append({'image':k,**got})
 e=ELF['ap'];sy=e.get_section_by_name('.dynsym');plt=e.get_section_by_name('.plt')
 symbols={plt['sh_addr']+32+j*16:sy.get_symbol(r['r_info_sym']).name for j,r in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}
 assert symbols[0x1594060]=='__assert_fail'
 proof['AP_assert_fail_binding']={'plt':'0x1594060','symbol':symbols[0x1594060],'call':'0x2ebf420'}
 proof['CP_classes']={}
 for nm in ('N3VDF18PinMemMgrCmdPinGetE','N3VDF29PinMemMgrCmdPinRequestConnectE','N3VDF32PinMemMgrCmdPinRequestDisconnectE',
            'N3VEF15SystemCmdPinGetE','N15NS_SCALAR_INFRA15SystemCmdPinGetE'):
  b=DATA['cp'];p=b.index(nm.encode()+b'\0')+0x108000;ti=b.index(struct.pack('<I',p))+0x108000-4;vt=b.index(struct.pack('<I',ti))+0x108000+4
  proof['CP_classes'][nm]={'name_va':hex(p),'typeinfo':hex(ti),'vtable':hex(vt),'slots':[hex(x) for x in struct.unpack('<6I',read('cp',vt,24))]}
 proof['CP_native_pin_objects']={'InfraBB_pointer_table_va':'0xefa624','InfraBB_objects':[hex(x) for x in struct.unpack('<21I',read('cp',0xefa624,84))],
       'DrawInfoPinCtrl_vtable':'0xb65900','DrawInfoPinCtrl_typeinfo':hex(u32('cp',0xb658fc)),
       'DrawInfoPinCtrl_RTTI':string('cp',u32('cp',u32('cp',0xb658fc)+4))}
 pairs=[(pinwords(new[i]['source']),pinwords(new[i]['destination'])) for i in active]
 backend=SoftwarePins({p for pair in pairs for p in pair})
 for i,(p,q) in zip(active,pairs):
  for label,cmd,dest,req,rep in [('GET_SOURCE',0,p[0],request(0,p),backend.get(p)),('GET_DESTINATION',0,q[0],request(0,q),backend.get(q))]:
   proof['projected_cold_software_requests'].append({'order':len(proof['projected_cold_software_requests'])+1,'row':i,'kind':label,
       'destination':hex(dest),'business_request':req.hex(),'business_reply':rep.hex(),'response_source':hex(dest),
       'reply_payload56':envelope(rep,get_reply_id(dest)).hex(),'outer_reply_id':hex(get_reply_id(dest)),
       'status_offset':28,'reply_queue':'request.outer.reply_id, never a constant'})
  rep=backend.connect(p,q);assert struct.unpack_from('<i',rep,24)[0]==0
  proof['projected_cold_software_requests'].append({'order':len(proof['projected_cold_software_requests'])+1,'row':i,'kind':'REQUEST_CONNECT',
       'destination':hex(p[0]),'business_request':request(1,p,q).hex(),'business_reply':rep.hex(),'response_source':hex(p[0]),
       'reply_payload56':envelope(rep).hex(),'status_offset':24,'reply_queue':'request.outer.reply_id, never a constant'})
 assert len(proof['projected_cold_software_requests'])==33
 proof['model_after_11_connections']=[{'pin':list(map(hex,p)),'peer':list(map(hex,r['peer'])),'state':r['state'],
      'queue':[],'buffer_handles':[],'pending_hardware':True} for p,r in sorted(backend.pins.items())]
 p,q=pairs[0];r=(q[0],8,1,4);unknown=(p[0],99,2,1)
 test=SoftwarePins({p,q,r,(q[0],p[1],2,1),(q[0],p[1],1,7)})
 cases=[]
 def case(name,rep,offset,status):
  assert len(rep)==32 and struct.unpack_from('<i',rep,offset)[0]==status
  cases.append({'case':name,'status':status,'business_reply':rep.hex(),'offset':offset})
 case('known_disconnected_GET_reports_state1',test.get(p),28,0);assert struct.unpack_from('<I',test.get(p),20)[0]==1
 case('unknown_GET_rejected',test.get(unknown),28,-32)
 case('type_mismatch_no_graph_change',test.connect(p,r),24,-23)
 case('direction_mismatch_no_graph_change',test.connect(p,(q[0],p[1],2,1)),24,-22)
 case('connect_owned_empty_endpoints',test.connect(p,q),24,0)
 case('idempotent_same_edge',test.connect(p,q),24,0)
 case('occupied_source_to_other_peer',test.connect(p,(q[0],p[1],1,7)),24,-25)
 case('GET_connected_state0',test.get(p),28,0);assert struct.unpack_from('<I',test.get(p),20)[0]==0
 lease=test.lease(p,q);case('disconnect_inflight_refuses_without_release',test.disconnect(p),24,-24)
 assert test.pins[p]['peer']==q;test.release(lease)
 case('disconnect_after_all_leases_returned',test.disconnect(p),24,0)
 case('already_disconnected_returns_minus26',test.disconnect(p),24,-26)
 assert test.pins[p]['peer'] is None and test.pins[q]['peer'] is None and not test.leases
 proof['software_model_checks']=cases
 proof['reply_schemas']={'GET':{'header':'0010008020000200','offsets':{'8':'type32','12':'direction32','16':'index32','20':'CP_connection_state32:0connected,1disconnected,2transition','24':'provider_OSAL_ID32','28':'signed_status32'}},
       'CONNECT_DISCONNECT':{'header':'1000/(8001|8002)/32/flags2','offsets':{'8':'type32','12':'direction32','16':'index32','20':'provider_OSAL_ID32','24':'signed_status32','28':'reserved0'}},
       'Dataflow_reply':'24B envelope +32B business =56B; +0 provider SID for InfraBB/OSD GET, zero for the other audited GET and generic REQUEST_CONNECT/DISCONNECT replies; +4 magic a0a0a0a0,+8 u16 count1,+10u16 total56,+12read24,+16write56,+20reserved0 chosen; OSAL source=provider, target=active request.reply_id'}
 proof['design_reference']={'scope':'Read-only source design comparison; not FX3 evidence and not executed',
       'commit':'b3d7c1fed349f1d918acc4259f1d2b3a7c52a500','repository':'https://github.com/chocotan/a7c2-qemu',
       'pin_registry_core_c_sha256':'c9e1cfa23766caea09ef2080882681ddb698c31bc421e5b28a7ec279a144523d','bytes':12217,
       'checked':'2026-11-02 UTC','notes':['per-owner keys/full-key/type-only policy, 8 reply leases, sender-bound canonical GET retirement',
       'pin_registry_dispatch accepts GET only and explicitly refuses CONNECT; connections require separate control dispatcher',
       'FX3 own CP proves InfraBB/OSD GET outer reply SID distinction; do not transplant A7C2 counts, masks, addresses or old state']}
 proof['unproven']=['No pin reply consumed by AP79 and no remaining 32 projected packets captured.',
       'No original CP execution, camera sensor/RAW/YC/audio buffers, hardware queue, DMA, panel output, or UI/menu acceptance.',
       'Software model is a proposal and pure Python ownership check, not integrated guest backend.',
       'Logical connect must not assert physical producer readiness or fabricate downstream events; DMM/OSD and in-flight ownership require independent implementation.',
       'Other mode/input runtime values and concurrent topology mutations are outside this AP79 snapshot.']
 out=OUT/'pin-topology-proof.json';out.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'result':'PASS','proof':str(out),'ctor_instructions':len(tr),'tables':len(ts),'rows_per_table':50,'all_live_rows_matched':100,
        'differences':diffs,'logical_connections':len(active),'projected_requests':33,'checks':len(CHECKS),'model_cases':len(cases)},ensure_ascii=False))
if __name__=='__main__':
 p=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert p['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 if len(sys.argv)>1:
  if sys.argv[1]=='tables':
   ts,tr=tables()
   print('CTOR',len(tr),'last',tr[-1])
   for a,rows in ts.items():
    print('TABLE',a,'states',[r['state'] for r in rows]);print(*[r for r in rows if r['state']==1],sep='\n')
  else:
   for spec in sys.argv[1:]:
    k,a,n=spec.split(':')
    for r in dis(k,int(a,16),int(n,16)):print(r['va'],r['instruction'])
 else:
  rebuild()
