from pathlib import Path
import sys,struct,json,hashlib,io,re
from capstone import *
from elftools.elf.elffile import ELFFile
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac'); OUT=Path(__file__).resolve().parent
P=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection'
FILES={'ap':P/'regular-files/usr/lib/appFw.so','cp':ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'}
DATA={k:p.read_bytes() for k,p in FILES.items()}; ELF=ELFFile(io.BytesIO(DATA['ap']))
def offset(k,v):
 if k=='cp':return v-0x108000
 s=next(s for s in ELF.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v<s['p_vaddr']+s['p_filesz']);return s['p_offset']+v-s['p_vaddr']
def va(k,o):
 if k=='cp':return o+0x108000
 return next((o-s['p_offset']+s['p_vaddr'] for s in ELF.iter_segments() if s['p_type']=='PT_LOAD' and s['p_offset']<=o<s['p_offset']+s['p_filesz']),o)
def read(k,v,n):o=offset(k,v);return DATA[k][o:o+n]
def string(k,v):return read(k,v,2048).split(b'\0')[0].decode(errors='replace')
def dis(k,v,n):
 c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(read(k,v,n),v)]
def cfg(raw):
 at=0;out={}
 def take(n):
  nonlocal at
  o=at;at+=n;assert at<=len(raw);return o,raw[o:at]
 for phase in ['roots','rules']:
  groups=[]
  while True:
   o,h=take(80);typ,sel=struct.unpack_from('<II',h,8)
   if typ==0xffffffff:break
   rows=[]
   while True:
    r,d=take(20);w=list(struct.unpack('<5I',d))
    if w[2]==0xffffffff:break
    rows.append({'offset':hex(r),'words':w})
   groups.append({'offset':hex(o),'type':typ,'selector':sel,'header':h.hex(),'rows':rows})
  out[phase]=groups
 units=[]
 while True:
  o,d=take(8);u,a=struct.unpack('<II',d)
  if u==0xffffffff:break
  refs=[]
  while True:
   _,d=take(4);v=int.from_bytes(d,'little')
   if v==0xffffffff:break
   refs.append(v)
  units.append({'offset':hex(o),'unit':hex(u),'attribute':a,'extents':refs})
 _,v=take(44);assert at==len(raw);out.update(units=units,version=v.decode());return out
CFGFILES={'AP':P/'regular-files/setting/DmmCfg.bin','CP':ROOT/'work/sony-firmware-20261024/stage128-DMM-provider-and-config/inputs/DmmCfg.bin'}
if len(sys.argv)>1:
 k=sys.argv[1]
 if k=='cfg':
  for name,p in CFGFILES.items():
   c=cfg(p.read_bytes());us=[u for u in c['units'] if int(u['unit'],16) in list(range(0x1d9,0x1df))+[0x70817,0x63a]];ex={e for u in us for e in u['extents']}
   print(name,json.dumps({'units':us,'rules':[dict(g,rows=[r for r in g['rows'] if r['words'][2] in ex]) for g in c['rules'] if any(r['words'][2] in ex for r in g['rows'])],'roots':c['roots']},indent=2))
 elif sys.argv[2]=='str':
  for v in sys.argv[3:]:print(v,string(k,int(v,16)))
 elif sys.argv[2]=='find':
  needle=sys.argv[3].encode();d=DATA[k];o=0
  while (o:=d.find(needle,o))>=0:print(hex(va(k,o)),d[max(0,o-80):o+180]);o+=1
 else:
  for a in sys.argv[2:]:
   v,n=[int(s,16) for s in a.split(':')]
   for i in dis(k,v,n):print(i['va'],i['instruction'])
 sys.exit()

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def fdt(p):
 d=p.read_bytes();h=struct.unpack_from('>10I',d);assert h[0]==0xd00dfeed
 _,total,off,strings,rsv,*_=h;assert total==len(d)
 reserve=[]
 while True:
  a,n=struct.unpack_from('>QQ',d,rsv);rsv+=16
  if a==n==0:break
  reserve.append({'address':hex(a),'size':hex(n)})
 nodes={};stack=[];at=off
 while True:
  token=struct.unpack_from('>I',d,at)[0];at+=4
  if token==1:
   end=d.index(0,at);name=d[at:end].decode();at=(end+4)&~3;stack.append(name);nodes['/'+('/'.join(stack[1:]))]={}
  elif token==2:stack.pop()
  elif token==3:
   n,no=struct.unpack_from('>II',d,at);at+=8;end=d.index(0,strings+no);name=d[strings+no:end].decode();nodes['/'+('/'.join(stack[1:]))][name]=d[at:at+n];at=(at+n+3)&~3
  elif token==4:continue
  elif token==9:break
  else:raise AssertionError(token)
 memory=[];reserved=[]
 for path,props in nodes.items():
  if path.startswith('/memory@') or path.startswith('/reserved-memory/'):
   reg=props.get('reg',b'');assert len(reg)%16==0
   rows=[{'address':hex(a),'size':hex(n)} for a,n in struct.iter_unpack('>QQ',reg)]
   (memory if path.startswith('/memory@') else reserved).append({'node':path,'reg':rows,'no-map':'no-map' in props})
 boot=nodes.get('/chosen',{}).get('bootargs',b'').rstrip(b'\0').decode()
 cmd=[{'address':hex(int(a,16)),'size':hex(int(n,16)),'attribute':attr or None} for n,a,attr in re.findall(r'memrsv=0x([0-9a-fA-F]+)@0x([0-9a-fA-F]+)(?::([a-z]+))?',boot)]
 return {'source':source(p),'memory':memory,'reservation_map':reserve,'reserved_memory':reserved,'cmdline_memrsv':cmd,'bootargs':boot}
def direct_xrefs(targets):
 hits={hex(x):[] for x in targets}
 for seg in ELF.iter_segments():
  if seg['p_type']!='PT_LOAD' or not(seg['p_flags']&1):continue
  d=seg.data()
  for o,(w,) in enumerate(struct.iter_unpack('<I',d[:len(d)//4*4])):
   if w&0xfc000000 not in (0x94000000,0x14000000):continue
   imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;v=seg['p_vaddr']+o*4;t=v+imm*4
   if hex(t) in hits:hits[hex(t)].append(hex(v))
 return hits

def main():
 p={'scope':'Offline static audit only; no QEMU, original or runtime mutation; only this directory written.','sources':{k:source(v) for k,v in FILES.items()}}
 assert p['sources']['ap']['sha256']=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
 assert p['sources']['cp']['sha256']=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
 ranges={'ap':[(0x2d1b388,0x54),(0x2d1b580,0x29ac),(0x2d1df2c,0xa80),(0x2d2e950,0xe4),(0x2d2f268,0x50),(0x2d2fed8,0xc),(0x2d139e0,0xe0),(0x2931484,0xf0),(0x2dda334,0x80),(0x2dda3f4,0xc0),(0x2dda5b4,0x80),(0x2dd4734,0x40),(0x2dd8b14,0x80),(0x2e41e20,0x168),(0x2e4efb8,0x2c8),(0x2e4f280,0x1f8),(0x2e4f488,0x2f8),(0x2e4f7b8,0x244),(0x2e50150,0x2f8),(0x2e15a18,0x104)]}
 p['blocks']={k:{hex(v):dis(k,v,n) for v,n in rs} for k,rs in ranges.items()}
 checks=[(0x2d2fedc,'bl #0x2d1b580'),(0x2d1b67c,'mov w0, #0x1d9'),(0x2d1b69c,'bl #0x2dda334'),(0x2d1b6b4,'str w0, [x28, #0x338]'),(0x2d1b6b8,'ldr w0, [x29, #0x16c]'),(0x2d1b77c,'mov w0, #0x1da'),(0x2d1b87c,'mov w0, #0x1db'),(0x2d1b97c,'mov w0, #0x1d9'),(0x2d1bd04,'mov w23, #0x1dc'),(0x2d1ca0c,'bl #0x15937b0'),(0x2d1ca40,'ldr x3, [x0, x20]'),(0x2d1ca64,'b.eq #0x2d1caa4'),(0x2d1caa4,'mov w0, #0x1a20'),(0x2d1cad4,'mov x2, #0xc800'),(0x2d1d3e0,'bl #0x2dd4734'),(0x2d1d4fc,'bl #0x2dd4734'),(0x2d1d988,'bl #0x2dd4734'),(0x2d1dc18,'bl #0x2dd8b14'),(0x2d1ddc0,'bl #0x2dd8b54'),(0x2d1e074,'bl #0x2dda474'),(0x2e4f490,'mov w2, #0'),(0x2e4f99c,'stp x29, x30, [sp, #-0x20]!'),(0x2e4f9b0,'mov w1, #0'),(0x2e4f354,'mov w1, #0x23')]
 for v,expected in checks:assert dis('ap',v,4)[0]['instruction']==expected,(hex(v),dis('ap',v,4))
 p['checked_instructions']=[{'VA':hex(v),'instruction':expected,'bytes':read('ap',v,4).hex()} for v,expected in checks]
 addrs=[0x3937540,0x3937760,0x39377c0,0x3920bce,0x3920be6,0x3920c18,0x3920c01,0x3920c64,0x3920c7e,0x3920cab,0x3920cf7,0x3936694,0x3910e58,0x3936619,0x39366ee,0x3936784,0x3936598]
 p['strings']={hex(v):string('ap',v) for v in addrs}
 p['names']={'0x2d1b580':'void model::sequence_mode_transition::common_preparation_sequence_of_face_registration()','0x2d1b6a0':'return address of remote 1d9 alloc in common_preparation, not an independent function entry','0x2d2e950':'virtual void model::sequence_mode_transition::run()','0x2d2fee0':'return-address/tail block in run, call at 0x2d2fedc','0x2d1df2c':'void model::sequence_mode_transition::common_finalization_sequence_of_face_registration()'}
 assert p['strings']['0x3937760']==p['names']['0x2d1b580']
 p['configurations']={}
 for name,path in CFGFILES.items():
  c=cfg(path.read_bytes());us=[u for u in c['units'] if int(u['unit'],16) in [0x1d9,0x1da,0x1db,0x1dc,0x70817,0x63a]];ex={e for u in us for e in u['extents']}
  rules=[dict(g,rows=[r for r in g['rows'] if r['words'][2] in ex]) for g in c['rules'] if any(r['words'][2] in ex for r in g['rows'])]
  u=next(u for u in us if u['unit']=='0x1d9');assert u['extents']==[547] and u['attribute']==0
  rr=[r for g in rules for r in g['rows'] if r['words'][2]==547];assert len(rr)==1 and rr[0]['words']==[0,8,547,0x64000,0x10f]
  p['configurations'][name]={'source':source(path),'version':c['version'],'units':us,'rules':rules,'roots':c['roots'],'native_alignment':'UNPROVEN: row flags 0x10f and type8 not decoded as byte alignment','native_dynamic_selection':'UNPROVEN; these are static candidate-rule geometries, not execution receipt'}
 # Relocatable kernel addresses are .text offsets, not loaded VAs.
 ko=P/'full-v4/payloads/1e28a4921b36cd8866330a6670d72627d347c556dbea8568cd5b3ab60853e65a';e=ELFFile(io.BytesIO(ko.read_bytes()));sy=e.get_section_by_name('.symtab');rel={r['r_offset']:sy.get_symbol(r['r_info_sym']).name for r in e.get_section_by_name('.rela.text').iter_relocations()};d=e.get_section_by_name('.text').data()
 p['sources']['dmm.ko']=source(ko);p['kernel_blocks']={}
 for v,n in [(0x5280,0x58),(0x5488,0x200),(0x9fb8,0x38),(0x9ff8,0xd4),(0xbd48,0x334)]:
  p['kernel_blocks'][hex(v)]=[{'text_offset':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'relocation':rel.get(i.address)} for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(d[v:v+n],v)]
 assert rel[0x5560]=='dmm_unit_ctrl_Alloc' and rel[0x52b0]=='dmm_unit_ctrl_Open'
 # Original AP kernel confirms option0 skips Open; zero segment/padding bytes below are the software model contract, not claims about native uninitialized padding.
 ap_root=p['configurations']['AP']['roots'][0]['rows'][0]['words'];ap_root_address=ap_root[0]+((ap_root[1]>>16)<<32);assert ap_root_address==0x424000000
 p['AP_1d9_root_range']={'source_offset':'0x50','root_type':29,'base':hex(ap_root_address),'size':hex(ap_root[3]),'decode_evidence':'dmm.ko.text+a09c..a0b8; CP address conversion intentionally not applied'}
 p['dmm_semantics']={'padding_contract':'Zero segment storage and unused bytes deterministically; original CP unused/padding bytes are not known.', 'option0':'allocate only; allocated=true, opens=0; option0 skips Open at kernel.text+528c..52a4','option1':'allocate+Open; returns one segment; increments opens','release_common':'remote1d9 finalized via AP2d1e074->2dda474->2e4f99c->2e4f280 op23 option0, not option2','close_temporary_views':'AP2dda434->2e4f7b8 op25; distinct from op23 free','handle':'low10 index, bits10..14 generation proved by kernel.text+9fb8; AP2e4f2b8 routes bit15. generation1..31 wrap is existing software-model policy; original CP wrap implementation not established.'}
 runtime=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime';candidate=runtime/'ap82-uud-second-pin-graph'
 p['fdt']=fdt(candidate/'guest.dtb');p['candidate']=source(candidate/'candidate82.json')
 base=0x41dd00000;end=base+0x90000
 all_rsv=p['fdt']['reservation_map']+p['fdt']['cmdline_memrsv']+[r for n in p['fdt']['reserved_memory'] for r in n['reg']]
 for r in all_rsv:
  a,n=int(r['address'],16),int(r['size'],16);assert end<=a or a+n<=base,(hex(base),r)
 mem=[r for n in p['fdt']['memory'] for r in n['reg']];assert any(int(r['address'],16)<=base and end<=int(r['address'],16)+int(r['size'],16) for r in mem)
 p['reservation_proposal']={'status':'proposal only; not yet reserved or integrated','AP_base':hex(base),'total':hex(end-base),'end_exclusive':hex(end),'alignment_choice':hex(0x10000),'fits_FDT_RAM':True,'disjoint_all_FDT_and_cmdline_ranges':True,'AP_existing_DmmCfg_local_scratch':'not moved; uses existing native kernel allocator/reserved roots','slots':[{'unit':hex(u),'handle_first_generation':hex(0x8408+i),'remote_index':8+i,'AP_backing':hex(a),'CP_wire':hex(a-0x400000000),'advertised_size':hex(n),'reserved_stride':hex(stride)} for i,(u,a,n,stride) in enumerate([(0x1d9,base,0x64000,0x70000),(0x1da,base+0x70000,0xc800,0x10000),(0x1db,base+0x80000,0xd100,0x10000)])]}
 raw=bytes.fromhex('20000000d901000000000000ffffffff000000000000000000000000000000000000000000000000');assert len(raw)==40
 p['captured_request']={'hex':raw.hex(),'op':0x20,'unit':0x1d9,'domain':1,'option_at22':struct.unpack_from('<H',raw,22)[0],'correlation_at20':0,'destination':'0x9061003c','source':'0x81cf61c2'}
 def reply(op,h,unit=0,addr=0,n=0,count=0,corr=0):
  b=bytearray(40);struct.pack_into('<HhHHHHII',b,0,op|0x8000,0,0,corr,count,0,h,unit);struct.pack_into('<QI',b,24,addr,n);return b.hex()
 p['exact_wire_templates']={}
 for sl in p['reservation_proposal']['slots']:
  h=int(sl['handle_first_generation'],16);u=int(sl['unit'],16);a=int(sl['CP_wire'],16);n=int(sl['advertised_size'],16)
  p['exact_wire_templates'][sl['unit']]={'8020_option0_corr0':reply(0x20,h,u),'8020_option1_corr0_optional':reply(0x20,h,u,a,n,1),'802a_corr0':reply(0x2a,h,0,a,n,1),'8023_option0_corr0':reply(0x23,h),'notes':'40B. 8020 option0 has zero segment count/address/size; 802a exposes retained extent even when allocated with opens0. Copy actual correlation, route reply to original source, unique lease and no duplicate completion.'}
 p['transfer_contract']={'AP_direct_access_remote_1d9':'No mmap/read/write of remote1d9 found in full common-preparation body; fields stored, local handles mapped, remote receives ICDT bytes. Does not prove absence in all future AP functions.','file':'/setting/facerec%d.bin each0xe220; checksum sums low32 of 8-byte loads over full record then compares backup per-person checksum atAP2d1ca40..64. Missing/short/checksum mismatch removes that entry, not immediate assert.','copy_partition':'valid record first0x1a20 -> local1db[id*0x1a20]; next0xc800 -> local1d9[id*0xc800]; capacity8records. ICDT local1d9->remote1d9 length0x64000 at2d1d3b0..3e0.','other_transfers':'local1db->remote1db0xd100 at2d1d4d0..4fc; local1da(/setting/facedmy.bin)->remote1da0xc800 at2d1d95c..988','minimum_honest_VM':'validate live handle/domain/generation/offset+length; copy actual local bytes into remote backing, preserving metadata; sync accept+one asynchronous callback via existing ICDT ABI. Muted-beep zeroing is NOT valid for arbitrary face data. If no hardware processing exists retain registration/state and report unavailable for unsupported compute/output.','CP_next':'2d1dc18 -> 2dd8b14 ->2e41f0c sends 12B 0207; 2d1ddc0 ->2dd8b54 ->2e41e20 sends24B0206(unit1db, opened handle, count, IDs), both destination90060197. Only 1db handle explicitly sent in this body; CP1d9 consumer linkage not fully resolved.','not_evidenced':'No GPE/encoder invocation in audited common body. Exact CP hardware touch of unit1d9 and complete 0206/0207 consumer semantics remain unproven; CP coincidences of immediate1d9 are not treated as DMM evidence.','fatality':'DMM alloc/open/transfer/release error branches reach original assert path; /dev/mem open errors are checked, while mmap MAP_FAILED is not explicitly checked in this helper; model unsupported status-3 is fatal in AP82. Missing/short face files are nonfatal branches. The shown 0206/0207 wrappers do not wait for CP response and set their output0 after send; successful return does not prove CP processing.'}
 log=runtime/'runs/ap82uud-9377b622/serial.log';ls=log.read_bytes().decode(errors='replace').splitlines();p['runtime']={'source':source(log),'evidence':[{'line':i+1,'text':s} for i,s in enumerate(ls) if any(t in s for t in ['memrsv:','Kernel command line:','raw='+raw.hex(),'status=-3 handle=0xffffffff','relative=0x2d1b6a0','relative=0x2d2fee0','notify_model_system_error','FX3_UUD_FACE_RETURN'])]}
 p['direct_branch_xrefs']=direct_xrefs([0x2931484,0x2d1b580,0x2d1df2c])
 # Pin current model source without treating it as native firmware evidence.
 p['existing_models']={n:source(runtime/'helpers'/n) for n in ['fx3-dmm-model.c','fx3-capid-v37.c','fx3-adf-file-model.c'] if (runtime/'helpers'/n).exists()}
 p['validation']={'instruction_checks':len(checks),'configurations_checked':len(p['configurations']),'proposal_slots_checked':len(p['reservation_proposal']['slots'])}
 p['unproven']=['Native alignment decoding and dynamic rule selection; CP physical root/address translation','Whole-program absence of AP remote mapping, future consumers of global parameters1f1..1f6','Complete CP90060197 dispatch and whether/how1d9 is consumed by a face hardware engine','OriginalCP generation wrap policy; software proposal follows existing model','Runtime success of new allocation/ICDT callbacks/CP registration/finalization; all integration and menu/device acceptance excluded']
 (OUT/'dmm-unit-1d9-proof.json').write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n')
 print(f'PASS: pinned images; {len(checks)} native instruction checks; AP/CP 1d9 single0x64000 geometry; FDT/RAM/nonoverlap; option0/2a/23 bytes; lifecycle and transfer evidence rebuilt')
if __name__=='__main__':main()
