#!/usr/bin/env python3
"""Pinned static AP loading/symbol/guard contract. Never executes guest code."""
import hashlib, importlib.util, json, mmap, posixpath, re, stat, struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
DONOR=HERE.parent
MAC=HERE.parents[5]
PRIOR=DONOR/'hybrid-assessment'
FX6=DONOR/'nflasha15-files'
CPIO=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
HELP=MAC/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
RUN=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/fx6-entry-no-key-20261103/runs/fx6entry-a39715a8'
V_ELF=PRIOR/'actual_cpio_preflight.py'
PINS={
 'cpio':'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d',
 'prior':'96742cf3ba840bd5f76d37dd76364371b2f150167e0f367de8396940f1c5c647',
 'entry_receipt':'29319c645a435fb8e5606b8bbccea6fd710a0fb77f5f559da99d4ad4267fd603',
 'parser':'e5dd8763a84a9aea27fda56e356c7c4557bf0b6e04bdab176f8a8943cb3d320a',
 'im':'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec',
 'bootin':'72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6',
 'imdb':'a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896',
 'fx3_sim_imdb':'d475e9f423f90edea6c2f188d1defec638d816c2ace945e95592d159654c26bd',
 'ap':'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
 'libobj':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
 'fx3_mpr':'9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c',
 'mpr':'814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e',
 'skd_source':'2d0a30d5a1e56ca3cd1956c7c24af51d07ffd660832e635ff8d9ffb2a03669e8',
 'capid_source':'8d65d6907c38e0f6767f7127e74de29e703e927aa0dc0be08deb9081d36bb7e7',
 'preset_source':'32bb3b5ae43ddab667c655941784daf028f26ce4c9ce6cca7e91268c4bb72663',
 'ui_source':'bb6650761764f2990650243b9e81ef7f4434c165faef8701afa1033cb961261c',
 'run_receipt':'426bd282bd1f35a51ba42fddfa4d9b8302bd23ad797e5b3a7f90d55e15deb032',
 'run_command':'91ff6ffb5d4f1c233f317654390851f72d9593064f6ff2926d3d989947bff9a6',
 'run_serial':'caecd00446ad09840606d63d199978683787ebf0fe276476ffac12e36f41a23c',
}
def sha(d):return hashlib.sha256(d).hexdigest()
def file_sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pin(p,key):
 d=p.read_bytes()
 if sha(d)!=PINS[key]:raise ValueError(f'SHA mismatch {key}: {p}')
 return d
def image_offset(d,va,size=1):
 po=struct.unpack_from('<Q',d,32)[0];entsz,count=struct.unpack_from('<HH',d,54)
 for i in range(count):
  typ,fl,off,start,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',d,po+i*entsz)
  if typ==1 and start<=va and va+size<=start+filesz:return off+va-start
 raise ValueError('VA not backed by PT_LOAD: '+hex(va))
def cstr(d,va):
 off=image_offset(d,va);end=d.index(b'\0',off)
 return {'va':hex(va),'file_offset':hex(off),'value':d[off:end].decode()}
def dyn_export_va(d,name):
 shoff=struct.unpack_from('<Q',d,40)[0];entsz,n=struct.unpack_from('<HH',d,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',d,shoff+i*entsz) for i in range(n)]
 for s in sections:
  if s[1]!=11:continue
  strings=sections[s[6]];blob=d[strings[4]:strings[4]+strings[5]]
  for off in range(s[4],s[4]+s[5],s[9]):
   nm,info,other,ndx,va,size=struct.unpack_from('<IBBHQQ',d,off)
   if ndx and blob[nm:blob.find(b'\0',nm)]==name.encode():return va
 raise ValueError('missing dynamic export '+name)
def relocation_index(d, names):
 shoff=struct.unpack_from('<Q',d,40)[0];entsz,n=struct.unpack_from('<HH',d,58)
 ss=[struct.unpack_from('<IIQQQQIIQQ',d,shoff+i*entsz) for i in range(n)]
 namesec=ss[struct.unpack_from('<H',d,62)[0]];sn=d[namesec[4]:namesec[4]+namesec[5]]
 sections={sn[s[0]:sn.find(b'\0',s[0])].decode():s for s in ss}
 symsec=sections['.dynsym'];strsec=ss[symsec[6]];strings=d[strsec[4]:strsec[4]+strsec[5]]
 syms=[]
 for p in range(symsec[4],symsec[4]+symsec[5],symsec[9]):
  no=struct.unpack_from('<I',d,p)[0];syms.append(strings[no:strings.find(b'\0',no)].decode('utf-8','replace'))
 out={x:{} for x in names}
 for section in ('.rela.dyn','.rela.plt'):
  s=sections[section]
  for p in range(s[4],s[4]+s[5],s[9]):
   va,info,addend=struct.unpack_from('<QQq',d,p);symbol=syms[info>>32]
   if symbol not in out:continue
   kind=info&0xffffffff;key=f'{section}:R_AARCH64_{kind}'
   row=out[symbol].setdefault(key,{'count':0,'first_relocation_va':hex(va),'first_relocation_file_offset':hex(p)})
   row['count']+=1
 return out
def newc_index(mm):
 out={};p=0;order=[]
 while True:
  if mm[p:p+6]!=b'070701':raise ValueError('bad newc header at '+hex(p))
  v=[int(mm[p+6+8*i:p+14+8*i],16) for i in range(13)]
  mode,size,n=v[1],v[6],v[11];raw=mm[p+110:p+110+n]
  if not raw.endswith(b'\0'):raise ValueError('bad name')
  name=raw[:-1].decode();off=(p+110+n+3)&~3
  if off+size>len(mm):raise ValueError('truncated member')
  if name=='TRAILER!!!':break
  if name in out or name.startswith('/') or '..' in name.split('/'):raise ValueError('bad path')
  out[name]={'offset':off,'bytes':size,'mode':mode};order.append(name);p=(off+size+3)&~3
 if len(order)!=1140:raise ValueError('wrong member count')
 return out
def member(mm,index,path):
 row=index[path];return mm[row['offset']:row['offset']+row['bytes']]
def resolve(mm,index,path):
 path=posixpath.normpath(path).lstrip('/')
 for _ in range(32):
  if path not in index:return None
  row=index[path]
  if stat.S_IFMT(row['mode'])!=stat.S_IFLNK:return path
  target=member(mm,index,path).decode()
  path=posixpath.normpath(target if target.startswith('/') else posixpath.join(posixpath.dirname(path),target)).lstrip('/')
 raise ValueError('symlink loop')
def main():
 for p,k in [(CPIO,'cpio'),(PRIOR/'actual-cpio-receipt.json','prior'),(PRIOR/'entry-candidate-review/receipt.json','entry_receipt'),(V_ELF,'parser')]:
  if file_sha(p)!=PINS[k]:raise ValueError('pin '+k)
 spec=importlib.util.spec_from_file_location('fixed_elf',V_ELF);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 prior=json.loads((PRIOR/'actual-cpio-receipt.json').read_text())
 entry=json.loads((PRIOR/'entry-candidate-review/receipt.json').read_text())
 if not entry['effective_entry_delta']['im_pt_load_equal']:raise ValueError('IM loadable equality pin lost')
 im=pin(FX6/'bin/im.elf','im');bootin=pin(FX6/'bin/bootin.elf','bootin');db=pin(FX6/'lib/libIMDB.so','imdb');ap=pin(FX6/'lib/appFw.so','ap');mpr=pin(FX6/'lib/libmpr.so','mpr')
 if cstr(bootin,0x403a08)['value']!='LD_PRELOAD':raise ValueError('bootin environment string changed')
 boot_env_vas=[0x402ed4,0x402ed8,0x402ee0,0x402ee4]
 boot_env=[{'va':hex(v),'file_offset':hex(image_offset(bootin,v,4)),'word':hex(struct.unpack_from('<I',bootin,image_offset(bootin,v,4))[0])} for v in boot_env_vas]
 # libIMDB's exported imdb_raw is VA 0x1e870; find_entry returns +0x100 + 0x48*i.
 idx=151;record_va=0x1e870+0x100+0x48*idx;record_off=image_offset(db,record_va,72)
 words=struct.unpack_from('<4I',db,record_off);ptrs=struct.unpack_from('<7Q',db,record_off+16)
 if words!=(0x20000004,1,0xffffff9f,0x83) or [cstr(db,x)['value'] for x in (ptrs[0],ptrs[1],ptrs[5],ptrs[6])] != ['appFw.so','Application_System_Init','AdjChkConfig.so','AppConfig.so']:
  raise ValueError('IMDB AP record changed')
 flags_va=0x41973c;flags_off=image_offset(im,flags_va,4);default_flags=struct.unpack_from('<I',im,flags_off)[0]
 if default_flags!=0x101:raise ValueError('IM default dlopen flags changed')
 # AArch64 instruction words: dispatch -> loader, path/flag/dlsym/call, mutable setter.
 instruction_vas=[0x406274,0x406284,0x405e3c,0x405ea4,0x405eac,0x405f08,0x405f0c,0x405f34,0x405f44,0x4057b4,0x4057b8]
 instructions=[{'va':hex(v),'file_offset':hex(image_offset(im,v,4)),'word':hex(struct.unpack_from('<I',im,image_offset(im,v,4))[0])} for v in instruction_vas]
 # Dynamic export identity of dlsym target, not a call-success claim.
 ap_elf=mod.VElf(ap)
 if not any(x['symbol']=='Application_System_Init' for x in ap_elf.exports):raise ValueError('AP entry not exported')
 entry_export=dyn_export_va(ap,'Application_System_Init')
 unknown=[x for x in prior['roots']['appFw.so']['nodes']['appFw.so']['strong_imports'] if x['status']=='UNVERSIONED_GLOBAL_SCOPE_UNKNOWN']
 known=[x for x in prior['roots']['appFw.so']['nodes']['appFw.so']['strong_imports'] if x['status']=='MATCHED_SYMBOL_VERSION_STATIC']
 if len(unknown)!=557 or len(known)!=343 or prior['roots']['appFw.so']['nodes']['appFw.so']['weak_import_count']!=9:raise ValueError('prior import inventory changed')
 with CPIO.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
  index=newc_index(mm)
  init=member(mm,index,'init').decode();line=init.splitlines()[287]
  if '/usr/bin/bootin.elf' not in line:raise ValueError('init entry changed')
  preloads=re.search(r'LD_PRELOAD=([^ ]+)',line).group(1).split(':')
  libpath=re.search(r'LD_LIBRARY_PATH=([^ ]+)',line).group(1).split(':')
  if len(preloads)!=17 or libpath!=['/simulation','/usr/lib','/lib']:raise ValueError('init loader contract changed')
  preload_paths=[resolve(mm,index,p) for p in preloads]
  if any(p is None for p in preload_paths):raise ValueError('missing preload')
  for row,p in zip(prior['preload_order'],preload_paths):
   if row['resolved']!=p or row['sha256']!=sha(member(mm,index,p)):raise ValueError('preload SHA/order changed')
  def lib(name):
   for directory in libpath:
    p=resolve(mm,index,directory+'/'+name)
    if p:return p
   return None
  # Startup dependency order is extracted from original IM DT_NEEDED BFS.
  q=[('im.elf',im)];startup=[];cache={}
  while q:
   name,data=q.pop(0)
   if name in startup:continue
   startup.append(name);e=mod.VElf(data);cache[name]=e
   for dep in e.needed:
    p=lib(dep)
    if p is None:raise ValueError('IM dependency absent '+dep)
    q.append((p,member(mm,index,p)))
  if set(startup)!=set(prior['roots']['im.elf']['nodes']):raise ValueError('IM closure changed')
  fx3_db_path=lib('libIMDB.so');fx3_db=member(mm,index,fx3_db_path)
  if fx3_db_path!='simulation/libIMDB.so' or sha(fx3_db)!=PINS['fx3_sim_imdb']:raise ValueError('actual guest IMDB changed')
  fx3_db_base=dyn_export_va(fx3_db,'imdb_raw');fx3_idx=143;fx3_record_va=fx3_db_base+0x100+0x48*fx3_idx
  fx3_record_off=image_offset(fx3_db,fx3_record_va,72)
  fx3_words=struct.unpack_from('<4I',fx3_db,fx3_record_off);fx3_ptrs=struct.unpack_from('<7Q',fx3_db,fx3_record_off+16)
  if fx3_words!=words or [cstr(fx3_db,x)['value'] for x in (fx3_ptrs[0],fx3_ptrs[1],fx3_ptrs[5],fx3_ptrs[6])]!=['appFw.so','Application_System_Init','AdjChkConfig.so','AppConfig.so']:
   raise ValueError('fixed FX3 IMDB AP entry differs')
  obj_path=lib('libObj.so')
  if not obj_path:raise ValueError('FX3 libObj missing')
  obj=member(mm,index,obj_path)
  if sha(obj)!=PINS['libobj']:raise ValueError('FX3 libObj SHA changed')
  fx3_mpr_path=lib('libmpr.so');fx3_mpr=member(mm,index,fx3_mpr_path)
  if fx3_mpr_path!='usr/lib/libmpr.so' or sha(fx3_mpr)!=PINS['fx3_mpr']:raise ValueError('actual FX3 libmpr changed')
  # Global startup order depends on bootin preserving LD_PRELOAD for IM.
  global_if_inherited=['im.elf']+preload_paths+[x for x in startup if x!='im.elf']
  global_without_inherited=startup
  for p in preload_paths:cache[p]=mod.VElf(member(mm,index,p))
  optional={'fx3_libObj_prior_global':mod.VElf(obj),'fx3_libmpr_prior_global':mod.VElf(fx3_mpr),'fx6_libmpr_prior_global':mod.VElf(mpr)}
  def exported(e,symbol):
   hits=[x for x in e.exports if x['symbol']==symbol and not x['hidden_version']]
   return 'strong' if any(not x['weak'] for x in hits) else 'weak' if hits else None
  reloc=relocation_index(ap,{x['symbol'] for x in unknown})
  rows=[];counts={'startup_global_candidate':0,'conditional_libObj_candidate':0,'conditional_fx3_libmpr_candidate':0,'conditional_fx6_libmpr_only_candidate':0,'no_candidate_in_examined_scope':0}
  for imp in unknown:
   symbol=imp['symbol'];with_pre=[{'provider':p,'binding':exported(cache[p],symbol)} for p in global_if_inherited if exported(cache[p],symbol)]
   without=[{'provider':p,'binding':exported(cache[p],symbol)} for p in global_without_inherited if exported(cache[p],symbol)]
   obj_binding=exported(optional['fx3_libObj_prior_global'],symbol);fx3_mpr_binding=exported(optional['fx3_libmpr_prior_global'],symbol);fx6_mpr_binding=exported(optional['fx6_libmpr_prior_global'],symbol)
   if without:cls='startup_global_candidate'
   elif obj_binding:cls='conditional_libObj_candidate'
   elif fx3_mpr_binding:cls='conditional_fx3_libmpr_candidate'
   elif fx6_mpr_binding:cls='conditional_fx6_libmpr_only_candidate'
   else:cls='no_candidate_in_examined_scope'
   counts[cls]+=1
   rows.append({'symbol':symbol,'classification':cls,'startup_candidates_with_preload_inherited':with_pre,'startup_candidates_without_preload':without,
                'first_startup_if_inherited':with_pre[0] if with_pre else None,'first_startup_without_inherited':without[0] if without else None,
                'fx3_libObj_prior_global':obj_binding,'fx3_libmpr_prior_global':fx3_mpr_binding,'fx6_libmpr_prior_global':fx6_mpr_binding,
                'relocations':reloc[symbol],'later_dlopen_or_dlsym_unknown':True})
  # The previous 557 were absent from AP's own DT_NEEDED plus preload scope.
  if any(x['startup_candidates_with_preload_inherited']!=x['startup_candidates_without_preload'] for x in rows):
   raise ValueError('unexpected preload provider for prior unknown inventory')
  weak_exports={'startup_first_weak':sum(bool(x['first_startup_without_inherited'] and x['first_startup_without_inherited']['binding']=='weak') for x in rows),
                'fx3_libObj_weak':sum(x['fx3_libObj_prior_global']=='weak' for x in rows),
                'fx3_libmpr_weak':sum(x['fx3_libmpr_prior_global']=='weak' for x in rows),
                'fx6_libmpr_weak':sum(x['fx6_libmpr_prior_global']=='weak' for x in rows)}
  eager=[{'symbol':x['symbol'],'class':x['classification'],'fx3_libObj':x['fx3_libObj_prior_global'],
          'fx3_libmpr':x['fx3_libmpr_prior_global'],'relocations':x['relocations']}
         for x in rows if any(k.startswith('.rela.dyn:') for k in x['relocations'])]
  if len(eager)!=47:raise ValueError('eager relocation inventory changed')
  guard=[]
  fx3=member(mm,index,'usr/lib/appFw.so')
  for label,source,pat_off,pat_word,n in [
   ('preset48',HELP/'fx3-preset-context-v6-save102.c',r'U addresses\[48\]=\{(.*?)\}',r'W words\[48\]=\{(.*?)\}',48),
   ('ui60',HELP/'fx3-ui-gate-v11.c',r'const U offsets\[60\]=\{(.*?)\};',r'const W words\[60\]=\{(.*?)\};',60)]:
   src=pin(source,'preset_source' if label=='preset48' else 'ui_source').decode()
   offs=[int(x,16) for x in re.findall(r'0x[0-9a-f]+',re.search(pat_off,src)[1])]
   vals=[int(x,16) for x in re.findall(r'0x[0-9a-f]+',re.search(pat_word,src)[1])]
   if len(offs)!=n or len(vals)!=n:raise ValueError('guard array length')
   matches={'fx3':0,'fx6':0};first=None
   for i,(va,w) in enumerate(zip(offs,vals)):
    item={'index':i,'va':hex(va),'expected':hex(w)}
    for key,d in [('fx3',fx3),('fx6',ap)]:
     try:
      off=image_offset(d,va,4);got=struct.unpack_from('<I',d,off)[0]
      item[key]={'file_offset':hex(off),'actual':hex(got),'match':got==w};matches[key]+=got==w
     except ValueError:item[key]={'file_offset':None,'actual':None,'match':False}
    if first is None and not item['fx6']['match']:first=item
   guard.append({'name':label,'source_sha256':sha(src.encode()),'count':n,'matches':matches,'first_fx6_mismatch':first})
  if [(x['matches']['fx3'],x['matches']['fx6']) for x in guard]!=[(48,0),(60,2)]:raise ValueError('guard match drift')
  init_sha=sha(member(mm,index,'init'))
  preload_order=[{'path':p,'guest_sha256':sha(member(mm,index,q))} for p,q in zip(preloads,preload_paths)]
 sources={}
 for name,key in [('skd','skd_source'),('capid','capid_source')]:
  p=HELP/('fx3-skd-hw-unavailable-v1.c' if name=='skd' else 'fx3-capid-v49-touch100.c')
  sources[name]={'path':str(p),'sha256':sha(pin(p,key))}
 # Historical owner-run evidence: two FX6 entry files but still original FX3 AP.
 rr=json.loads(pin(RUN/'receipt.json','run_receipt'))
 cmd=json.loads(pin(RUN/'command.json','run_command'))
 serial=pin(RUN/'serial.log','run_serial')
 if cmd['candidate_sha256']!='ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40' or cmd['frozen_argv_changed_indices']!=[20,31] or rr['serial']['sha256']!=PINS['run_serial']:
  raise ValueError('owner run candidate/platform identity drift')
 for item in rr['serial']['first'].values():
  if item is not None:
   lo,hi=item['byte_range']
   if serial[lo:hi].decode()!=item['raw']:raise ValueError('owner run byte-range mismatch')
 lines=serial.decode('utf-8','replace').splitlines()
 def first_line(text):
  return next((i+1 for i,line in enumerate(lines) if text in line),None)
 map_start=first_line('FX3_AP_IM_ENDMAPS_237_BEGIN');map_end=first_line('FX3_AP_IM_ENDMAPS_237_END')
 if not map_start or not map_end:raise ValueError('IM maps boundary absent')
 maps='\n'.join(lines[map_start-1:map_end])
 if not all(p in maps for p in preloads) or '/simulation/libIMDB.so' not in maps or '/usr/bin/im.elf' not in maps:
  raise ValueError('actual IM maps lacked startup payload')
 observed={'verify_rc_line':first_line('FX3_TRACE_ABI_VERIFY_RC=0'),'list_rc_line':first_line('FX3_TRACE_ABI_LIST_RC=0'),
  'true_rc_line':first_line('FX3_TRACE_ABI_TRUE_RC=0'),'natural_bootin_line':first_line('FX3_AP_NATURAL_BOOTIN_BEGIN'),
  'im_maps_begin_line':map_start,'im_maps_end_line':map_end,'im_maps_all_17_preloads':True,
  'im_maps_simulation_imdb':True,'fx3_libobj_dlopen_line':first_line('FX3_GPE_LOAD name=/usr/lib/libObj.so flags=0x101'),
  'fx3_ui_guard_bound_line':first_line('FX3_UI_GATE_BOUND count=60'),'fx3_preset_guard_bound_line':first_line('FX3_PRESET_CONTEXT_BOUND points=48'),
  'first_fx3_ap_caller_line':first_line('FX3_PROVIDER_CALLER module=/usr/lib/appFw.so'),
  'first_fx3_mpr_caller_line':first_line('module=/usr/lib/libmpr.so'),
  'first_fx3_ipc_send_line':first_line('FX3_BOOT_QUEUE_SEND')}
 if not all(observed.values()):raise ValueError('owner run marker changed')
 out={'status':'STATIC_CONTRACT_WITH_HISTORICAL_FX3_AP_RUN','input_sha256':{k:PINS[k] for k in ('cpio','prior','entry_receipt','parser','bootin','im','imdb','fx3_sim_imdb','ap','libobj','fx3_mpr','mpr','run_receipt','run_command','run_serial')},
  'cpio_members':len(index),'init_sha256':init_sha,'init_ap_line':288,'ld_preload_order':preload_order,'ld_library_path':libpath,
  'imdb_ap_record':{'library_sha256':PINS['imdb'],'record_index':idx,'record_va':hex(record_va),'record_file_offset':hex(record_off),'record_words':[hex(x) for x in words],
    'name':cstr(db,ptrs[0]),'entry_symbol':cstr(db,ptrs[1]),'config_when_bit4000':cstr(db,ptrs[5]),'config_other':cstr(db,ptrs[6])},
  'actual_guest_imdb_ap_record':{'path':fx3_db_path,'library_sha256':PINS['fx3_sim_imdb'],'record_index':fx3_idx,'record_va':hex(fx3_record_va),'record_file_offset':hex(fx3_record_off),
   'record_words':[hex(x) for x in fx3_words],'name':cstr(fx3_db,fx3_ptrs[0]),'entry_symbol':cstr(fx3_db,fx3_ptrs[1]),'config_when_bit4000':cstr(fx3_db,fx3_ptrs[5]),'config_other':cstr(fx3_db,fx3_ptrs[6])},
  'im_loader':{'im_sha256':PINS['im'],'record_dispatch_type':'0x20000004','dispatcher_va':'0x406274','loader_va':'0x405e24',
   'dlopen_plt_va':'0x402150','dlsym_plt_va':'0x402080','indirect_entry_call_va':'0x405f44',
   'flags_initial':hex(default_flags),'flags_va':hex(flags_va),'flags_file_offset':hex(flags_off),'flags_setter_va':'0x4057b4',
   'namespace_inference':'dlopen from IM, no dlmopen on this edge; same caller link-map namespace if glibc semantics apply; live namespace/flags not observed',
   'entry_export_va':hex(entry_export),'entry_export_file_offset':hex(image_offset(ap,entry_export,4)),'instruction_words':instructions,
   'natural_record_selection':'unknown until original IMDB request ID/target bit and preceding load state observed'},
  'bootin_env':{'ld_preload_name':cstr(bootin,0x403a08),'conditional_unsetenv_instructions':boot_env,
   'condition':'0x402ed8 tbz bit 6 skips 0x402ee4 unsetenv(LD_PRELOAD); runtime option and inherited IM environment unobserved'},
  'ap_imports':{'strong_root':900,'weak_root':9,'weak_imports':[x['symbol'] for x in ap_elf.imports if x['weak']],
   'previous_local_static_match':343,'previous_unknown_unversioned':557,
   'startup_scope_order_if_preloads_inherited':global_if_inherited,'startup_scope_order_without_preloads':global_without_inherited,
   'conditional_extra_providers':['FX3 libObj if earlier RTLD_GLOBAL dlopen','actual FX3 libmpr if earlier RTLD_GLOBAL dlopen','FX6 libmpr only after explicit software replacement and earlier global load'],
   'classification_counts':counts,'weak_export_candidates':weak_exports,'eager_relocation_symbols':eager,'rows':rows,
   'resolution_limit':'Order is static ELF DT_NEEDED BFS, not guest link_map; same names may have different ABI; lazy resolution, dlsym and later dlopen remain unknown'},
  'guards':guard,'helper_sources':sources,
  'historical_owner_run':{'candidate_sha256':cmd['candidate_sha256'],'duration_seconds':rr['duration_seconds'],'stop_cause':rr['stop_cause'],
   'qemu_exit':rr['qemu_exit'],'API16_restored':rr['cleanup']['API16_restored'],'locks_free':all(x['free'] for x in rr['locks']),
   'serial_sha256':PINS['run_serial'],'serial_lines':observed,
   'evidence_limit':'FX6 bootin + IM file (IM PT_LOAD same FX3); FX3 appFw, libObj and helpers remained. No FX6 AP load or symbol resolution proved.'},
  'scope':['no new QEMU run','no new guest execution','no changed CPIO or helpers','no claim of natural FX6 AP selection or ABI success']}
 (HERE/'receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'ap_record':out['imdb_ap_record'],'flag_initial':hex(default_flags),'unversioned_counts':counts,'guards':[(x['name'],x['matches']) for x in guard]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
