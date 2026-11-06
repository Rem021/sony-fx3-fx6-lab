#!/usr/bin/env python3
"""Read-only ELF/callsite audit. Writes only adjacent proof JSON."""
from pathlib import Path
import io,json,hashlib,struct,subprocess,bisect,re,plistlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
O=Path(__file__).resolve().parent
R=next(p for p in O.parents if (p/'work/sony-firmware-20261024').is_dir())
E=R/'work/sony-firmware-20261024/stage2/extraction'
A=R/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files'
cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def elf(p): return ELFFile(io.BytesIO(p.read_bytes()))
def syms(e):
 s=e.get_section_by_name('.dynsym'); return list(s.iter_symbols()) if s else []
def needed(e):
 s=e.get_section_by_name('.dynamic');return [t.needed for t in s.iter_tags() if t.entry.d_tag=='DT_NEEDED'] if s else []
def dis(e,a,n):
 s=next((s for s in e.iter_sections() if s['sh_addr']<=a<s['sh_addr']+s['sh_size'] and s['sh_type']=='SHT_PROGBITS'),None)
 return [{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(s.data()[a-s['sh_addr']:a-s['sh_addr']+n],a)] if s else []
def pltmap(e):
 s=e.get_section_by_name('.rela.plt');p=e.get_section_by_name('.plt');d=e.get_section_by_name('.dynsym')
 return {p['sh_addr']+32+16*i:d.get_symbol(r['r_info_sym']).name for i,r in enumerate(s.iter_relocations())} if s and p else {}
p=A/'usr/lib/appFw.so';e=elf(p);b=p.read_bytes();symbols=syms(e);pm=pltmap(e)
funs=sorted((s['st_value'],s['st_size'],s.name) for s in symbols if s['st_info']['type']=='STT_FUNC' and s['st_shndx']!='SHN_UNDEF')
# Stripped local functions: detect standard frame setup; retain names as unknown.
textsec=e.get_section_by_name('.text');td=textsec.data();tb=textsec['sh_addr'];pro=[]
for off in range(0,len(td)-7,4):
 w,z=struct.unpack_from('<II',td,off)
 if z==0x910003fd and (w&0xffc07fff)==0xa9807bfd:pro.append(tb+off)
exported_end=max((x[0]+x[1] for x in funs),default=0)
for i,v in enumerate(pro[:-1]):
 if v>exported_end:funs.append((v,pro[i+1]-v,'local_'+hex(v)))
funs.sort()
starts=[x[0] for x in funs]
names=[x[2] for x in funs];dem=subprocess.run(['c++filt'],input='\n'.join(names),text=True,capture_output=True).stdout.splitlines();dm=dict(zip(names,dem))
def owner(a):
 j=bisect.bisect_right(starts,a)-1
 if j<0:return None
 v,n,s=funs[j];return {'va':hex(v),'size':n,'mangled':s,'demangled':dm.get(s,s),'contains':a<v+n}
# Decode direct BL/B in executable sections without disassembling entire 60MB library.
calls=[];allbranches=[]
for s in e.iter_sections():
 if not s['sh_flags']&4:continue
 data=s.data();base=s['sh_addr']
 for off in range(0,len(data)-3,4):
  w=struct.unpack_from('<I',data,off)[0]
  if w&0x7c000000==0x14000000:
   imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;a=base+off;t=a+imm*4
   allbranches.append((a,t))
   if pm.get(t,'').startswith('iCrypt_'):calls.append({'symbol':pm[t],'va':hex(a),'plt':hex(t),'owner':owner(a),'instructions':dis(e,max(base,a-64),128)})
blocks={}
for c in calls:
 o=c['owner']
 if o and o['contains']:blocks[o['va']]={'owner':o,'instructions':dis(e,int(o['va'],16),o['size'])}
# Direct callers of wrappers, then their callers (two levels).
front={int(x,16) for x in blocks};up=[]
for depth in range(3):
 nxt=set()
 for a,t in allbranches:
  if t in front:
   o=owner(a);up.append({'depth':depth,'va':hex(a),'target':hex(t),'owner':o,'instructions':dis(e,a-24,56)})
   if o:nxt.add(int(o['va'],16))
 front=nxt
# All extracted ELF definitions are used as the supply universe (not merely direct dependencies).
records=[];exports=set();hints=[];scanned=0
roots=[E/'files',A,A.parent/'full-v4/regular-files',A.parent/'full-v5/regular-files',R/'work/fx3-vm-20261101/fx3-audit/original-members']
fullmanifest=json.loads((A.parent/'full-v5/projection-manifest-full-v5.json').read_text())
virtual={Path(x['local_file']):Path(x['guest_path']).name for x in fullmanifest['members'] if x.get('type')=='regular' and x.get('local_file')}
paths=sorted(set(p for root in roots if root.exists() for p in root.rglob('*'))|set(virtual))
for p in paths:
 if not p.is_file():continue
 data=p.read_bytes();scanned+=1
 matches=[]
 for pattern in [rb'iCrypt',rb'libicrypt',rb'libCertificateManager',rb'libInfraSKD',rb'/dev/tee',rb'libtee',rb'OP-TEE',rb'TrustZone']:
  for m in list(re.finditer(pattern,data))[:50]:
   lo=max(0,data.rfind(b'\0',0,m.start())+1);hi=data.find(b'\0',m.end());hi=min(len(data),m.end()+160) if hi<0 else min(hi,m.end()+160)
   matches.append({'offset':hex(m.start()),'context':data[lo:hi].decode('utf8','replace')[-300:]})
 if matches:hints.append({'path':str(p.relative_to(R)),'matches':matches})
 if data[:4]!=b'\x7fELF':continue
 try:
  el=ELFFile(io.BytesIO(data));ss=syms(el)
  defs={x.name for x in ss if x.name and x['st_shndx']!='SHN_UNDEF' and x['st_info']['bind'] in ('STB_GLOBAL','STB_WEAK') and x['st_other']['visibility'] in ('STV_DEFAULT','STV_PROTECTED')}
  und=[{'name':x.name,'binding':x['st_info']['bind'],'type':x['st_info']['type']} for x in ss if x.name and x['st_shndx']=='SHN_UNDEF']
  exports.update(defs);records.append({'path':str(p.relative_to(R)),'basename':virtual.get(p,p.name),'machine':el['e_machine'],'needed':needed(el),'undefined':und,'definitions':sorted(defs)})
 except Exception as ex:raise RuntimeError(str(p)) from ex
# im.elf dependency closure, account for guest projection too (includes libc).
by={}
for x in records:
 if x['machine']=='EM_AARCH64':
  by.setdefault(x['basename'],x)
  for al in [x['basename'].split('.so.')[0]+'.so.'+x['basename'].split('.so.')[1].split('.')[0]] if '.so.' in x['basename'] else []:by.setdefault(al,x)
# glibc SONAMEs differ from file basenames (e.g. libc-2.25.so).
for root in roots:
 if not root.exists():continue
 for pp in root.rglob('*'):
  if not pp.is_file():continue
  rec=next((x for x in records if x['path']==str(pp.relative_to(R))),None)
  if rec:
   el=elf(pp);ds=el.get_section_by_name('.dynamic')
   if ds:
    for tag in ds.iter_tags():
     if tag.entry.d_tag=='DT_SONAME':by.setdefault(tag.soname,rec)
log=R/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap70lcd-f61554d9/serial.log'
lines=log.read_text(errors='replace').splitlines()
observed=sorted(set(Path(m.group(1)).name for l in lines if (m:=re.search(r'FX3_GPE_LOAD name=(\S+)',l))))
manifest=json.loads((A.parent/'projection-manifest-v2.json').read_text())
cryptrow=next(x for x in manifest['imdb']['rows'] if x.get('strings_by_pointer_slot',{}).get('2')=='libInfraCrypt.so')
# Conservative stock namespace: every IMDB library, plus observed loads and dependencies.
stock=[x.get('strings_by_pointer_slot',{}).get('2','') for x in manifest['imdb']['rows']]
stock=[Path(x).name for x in stock if Path(x).name in by]
closure=[];todo=['im.elf','appFw.so']+observed+stock;seen=set();absent=[]
while todo:
 n=todo.pop(0)
 if n in seen:continue
 seen.add(n)
 rec=by.get(n)
 if rec is None:
  pp=next((p for p in A.rglob(n) if p.is_file()),None)
  if pp:
   el=elf(pp);ss=syms(el);rec={'path':str(pp.relative_to(R)),'basename':n,'needed':needed(el),'undefined':[{'name':x.name,'binding':x['st_info']['bind'],'type':x['st_info']['type']} for x in ss if x.name and x['st_shndx']=='SHN_UNDEF'],'definitions':[x.name for x in ss if x['st_shndx']!='SHN_UNDEF']}
 if rec is None:absent.append(n);continue
 closure.append(rec);todo.extend(rec['needed'])
# Separate original extracted absence from closure absence; version compatibility is not assumed.
ce=set().union(*(set(x['definitions']) for x in closure));missing=[]
for rec in closure:
 for u in rec['undefined']:
  if u['name'] not in exports:
   risk=0 if u['name']=='iCrypt_HasPublicKey' else 1 if u['name'].startswith('iCrypt_') else 3 if u['binding']=='STB_WEAK' else 2
   missing.append(dict(u,importer=rec['path'],rank=risk,provided_by_projection_closure=u['name'] in ce))
missing.sort(key=lambda x:(x['rank'],x['name'],x['importer']))
log=R/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap70lcd-f61554d9/serial.log';lines=log.read_text(errors='replace').splitlines()
out={'schema':1,'appFw':str((A/'usr/lib/appFw.so').relative_to(R)),'appFw_sha256':hashlib.sha256(b).hexdigest(),'icrypt_plt':{n:hex(a) for a,n in pm.items() if n.startswith('iCrypt_')},'calls':calls,'wrapper_functions':blocks,'wrapper_callers':up,'inventory':{'files_scanned':scanned,'elf_count':len(records),'elf_paths':[x['path'] for x in records],'elf_needed':[{'path':x['path'],'needed':x['needed']} for x in records]},'provider_hints':hints,'im_needed_closure':[{'path':x['path'],'needed':x['needed']} for x in closure],'unlocated_needed':absent,'missing_in_extracted_partitions':missing,'namespace_roots':{'observed_loads':observed,'stock_imdb_available':stock,'original_preload_found':False},'crypt_imdb_row':cryptrow,'missing_in_im_closure':[dict(u,importer=x['path']) for x in closure for u in x['undefined'] if u['name'] not in ce],'all_ap_elf_missing':[dict(u,importer=x['path']) for x in records if x['machine']=='EM_AARCH64' for u in x['undefined'] if u['name'] not in exports],'log':{'path':str(log.relative_to(R)),'sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'failure':[{'line':i+1,'text':l} for i,l in enumerate(lines) if 'iCrypt' in l]},'limitations':['Direct branches only: indirect calls cannot be exhaustively enumerated.','DT_NEEDED closure is static; dlopen providers must be considered separately.','Symbol presence comparison ignores symbol versions and runtime scope.','No guest, device or crypto operations performed.']}
# Full instruction evidence for upper callers and contextual log strings.
extra={0x2e10048:0x138,0x2b61f00:0x900,0x2b7c6e0:0xb00,0x2d629b4:0x650}
for item in up:
 o=item['owner']
 if o and o['contains'] and item['depth']<=1:extra[int(o['va'],16)]=o['size']
out['upper_blocks']={hex(a):dis(e,a,n) for a,n in extra.items()}
# Resolve ADRP+ADD address pairs to printable C strings, preserving VA.
def cstr(a):
 for seg in e.iter_segments():
  if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a<seg['p_vaddr']+seg['p_filesz']:
   off=seg['p_offset']+a-seg['p_vaddr'];raw=b[off:b.find(b'\0',off)]
   if 3<=len(raw)<=1000 and all(x in (9,10,13) or 32<=x<127 for x in raw):return raw.decode()
strings={}
for instr in list(out['upper_blocks'].values())+[x['instructions'] for x in blocks.values()]:
 regs={}
 for ins in instr:
  asm=ins['asm'];m=re.match(r'adrp (x\d+), #(0x[0-9a-f]+)',asm)
  if m:regs[m[1]]=int(m[2],16)
  m=re.match(r'add (x\d+), (x\d+), #(0x[0-9a-f]+)',asm)
  if m and m[2] in regs:
   a=regs[m[2]]+int(m[3],16);st=cstr(a)
   if st:strings[hex(a)]=st
out['resolved_app_strings']=strings
out['providers']={}
for nm in ['libInfraCrypt.so','libInfraCryptCore.so','libsecvlt.so','libCertificateManager.so','libInfraSKD.so']:
 pp=A/'usr/lib'/nm
 if not pp.exists():continue
 pe=elf(pp);pb=pp.read_bytes();ss=syms(pe)
 out['providers'][nm]={'path':str(pp.relative_to(R)),'sha256':hashlib.sha256(pb).hexdigest(),'needed':needed(pe),'exports':{x.name:{'va':hex(x['st_value']),'size':x['st_size'],'instructions':dis(pe,x['st_value'],x['st_size'])} for x in ss if x['st_shndx']!='SHN_UNDEF' and ('iCrypt' in x.name or 'secvlt' in x.name)},'device_strings':sorted(set(x.decode(errors='replace') for x in re.findall(rb'/dev/[A-Za-z0-9_/.-]+',pb))),'dlopen_import':any(x.name=='dlopen' and x['st_shndx']=='SHN_UNDEF' for x in ss)}
# Attach all direct calls to truly absent appFw imports, for next-risk ordering.
absnames={x['name'] for x in missing}
out['absent_appFw_calls']=[{'va':hex(a),'plt':hex(t),'symbol':pm[t],'owner':owner(a),'instructions':dis(e,a-16,40)} for a,t in allbranches if pm.get(t) in absnames]
im=elf(A/'usr/bin/im.elf');out['im_loader_blocks']={'dlopen':dis(im,0x405e98,0x78)}
# A second closure models observed dlopens plus recommended original crypt preload.
actual=[];todo=['im.elf','appFw.so','libInfraCrypt.so']+[x for x in observed if x in by];seen=set()
while todo:
 n=todo.pop(0)
 if n in seen:continue
 seen.add(n)
 if n not in by:continue
 rec=by[n];actual.append(rec);todo.extend(rec['needed'])
actualexports=set().union(*(set(x['definitions']) for x in actual))
out['observed_plus_original_crypt_preload']={'libraries':[x['path'] for x in actual],'missing_any_provider':[dict(u,importer=x['path']) for x in actual for u in x['undefined'] if u['name'] not in exports],'not_in_this_namespace':[dict(u,importer=x['path'],provider_exists_in_firmware=u['name'] in exports) for x in actual for u in x['undefined'] if u['name'] not in actualexports]}
out['full_projection_manifest_sha256']=hashlib.sha256((A.parent/'full-v5/projection-manifest-full-v5.json').read_bytes()).hexdigest()
out['source_scope']=[str(x.relative_to(R)) for x in roots]
out['startup_interpretation']={'static_path':'model::sequence_boot::license_get_i -> 0x2de2484 -> infra_wrapper_crypt::has_public_key -> iCrypt_HasPublicKey','caller_vas':['0x2b62140','0x2b62640'],'thread':'Not proven: serial linker error has no TID or PC backtrace','timing':'after kernel 585.798531 printk; approximately 10 s after LCD completion','no_key_path':'iCrypt bool false -> wrapper out[0]=1,out[1]=0 -> license loop records missing state and continues; no Create called in license_get_i','create_failure':'sequence_create_key_for_digital_signature CreatePrivate failure at 0x2b7c86c -> 0x2b7ce5c; fatal diagnostic and 0x2ebf3b0; not safe as generic failure stub'}
out['signature_inference']={
'iCrypt_HasPublicKey':'bool/u8 (u32 id); low8 zero absent, nonzero present',
'iCrypt_HasPrivateKey':'bool/u8 (u32 id); low8 zero absent, nonzero present',
'iCrypt_CreatePrivateKey':'u32 status(u32 id); 0 or 0x8000000c accepted by wrapper',
'iCrypt_DeletePrivateKey':'u32 status(u32 id); 0 or 0x8000000b accepted',
'iCrypt_DeletePublicKey':'u32 status(u32 id); 0 or 0x8000000d accepted',
'iCrypt_CreatePublicKey':'u32 status(u32 id, void **out, u64 *out_length); zero success',
'iCrypt_GetPublicKey':'u32 status(u32 id, void **out, u64 *out_length); zero success',
'iCrypt_ExtractPublicKeyBodyData':'u32 status(u32 id, const void *input, u64 input_length, void **out, u64 *out_length); zero success',
'iCrypt_FreeData':'u32 status(u32 id, void *allocated_data); zero success'}
assert set(out['icrypt_plt'])<=set(out['providers']['libInfraCrypt.so']['exports'])
out['stock_config_scan']={'manifest_guest_paths_with_profile_preload':[x['guest_path'] for x in fullmanifest['members'] if any(t in x['guest_path'] for t in ['/etc/profile','ld.so.preload','systemd'])],'init2_bootin_line':64,'note':'No stock preload config found in full projection; stock IMDB dlopen is positive evidence.'}
(O/'icrypt-proof.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
assert len(out['icrypt_plt'])==9 and calls
print(json.dumps({'icrypt_calls':len(calls),'wrappers':len(blocks),'missing':len(missing),'closure':len(closure),'unlocated_needed':absent}))
