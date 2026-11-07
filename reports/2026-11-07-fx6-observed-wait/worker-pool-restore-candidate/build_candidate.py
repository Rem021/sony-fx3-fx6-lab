#!/usr/bin/env python3
"""Restore only native worker-pool creation suppressed by Candidate295 shim."""
import datetime, difflib, io, json, mmap, os, plistlib, posixpath, re, struct, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from candidate_tools import fp,sha,scan,elf_info
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'fx6-wait-snapshot-20261107'
ZIG=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig')
PARENT_MANIFEST_SHA='df39ee856ea9c667d786920c0ec9c12b43992fbc17525870cbd53b38f5c8da42'
PARENT_CPIO_SHA='453890e36e7e6b4cd66641707cf80bd7754a0a37d6fba8dfce2af55fc169c926'
BASE_SOURCE_SHA='e9f7f234e40b0119c25d27b0c595497693377c30ec7001e22d6d8855a9721829'
BASE_SHIM_SHA='c58b6509e451a32474a6e2ace7c680a58427a5b685eaf27ece9a51153c2a3f45'
MEMBER='usr/lib/libgrm-fbinit9.so'
BEFORE=[0x12d824c,0x12d8250,0x12d8254,0x12d825c,0xc09e50]
AFTER=[x for x in BEFORE if x!=0x12d825c]
def save(name,value):
 (HERE/name).write_text(json.dumps(value,indent=2)+'\n');return fp(HERE/name)
def nop_table(data):
 e=ELFFile(io.BytesIO(data));s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name=='fx6_patch_blocking_calls.offs');sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];return list(struct.unpack('<'+'Q'*(s['st_size']//8),data[off:off+s['st_size']]))
def symbol_contract(data):
 e=ELFFile(io.BytesIO(data));return sorted((s.name,s['st_info']['bind'],s['st_info']['type'],s['st_other']['visibility'],s['st_shndx']=='SHN_UNDEF') for s in e.get_section_by_name('.dynsym').iter_symbols() if s.name)
def sections_proof(old,new):
 a=ELFFile(io.BytesIO(old));z=ELFFile(io.BytesIO(new));names=['.text','.rodata','.got','.got.plt'];alloc=[s.name for s in a.iter_sections() if s['sh_flags']&2];out=[]
 for n in dict.fromkeys(names+alloc):
  s,t=a.get_section_by_name(n),z.get_section_by_name(n);same_absent=s is None and t is None
  r={'name':n,'present_before':s is not None,'present_after':t is not None,'absent_both':same_absent}
  if same_absent:r['equal']=True
  else:
   assert s is not None and t is not None
   r.update(type_before=s['sh_type'],type_after=t['sh_type'],flags_before=s['sh_flags'],flags_after=t['sh_flags'],vma_before=hex(s['sh_addr']),vma_after=hex(t['sh_addr']),bytes_before=s['sh_size'],bytes_after=t['sh_size'])
   equal=all(s[k]==t[k] for k in ['sh_type','sh_flags','sh_addr','sh_size'])
   if s['sh_type']!='SHT_NOBITS':r.update(sha256_before=sha(s.data()),sha256_after=sha(t.data()));equal=equal and s.data()==t.data()
   r['equal']=equal
  assert r['equal'],r;out.append(r)
 return names,alloc,out
def verify_abi(raw,rows,old,new):
 a,ae=elf_info(old);z,ze=elf_info(new);assert symbol_contract(old)==symbol_contract(new)
 assert a['needed']==z['needed']==[] and a['imports']==z['imports']
 assert all(x['version'] is None for x in z['imports'])
 assert ae==ze
 wanted=['libc.so.6','libdl.so.2','libgcc_s.so.1'];by={r['name']:r for r in rows};providers={}
 for soname in wanted:
  name=next(d+'/'+soname for d in ['lib','usr/lib'] if d+'/'+soname in by);chain=[]
  while by[name]['fields'][1]&0o170000==0o120000:
   assert name not in chain;chain.append(name);r=by[name];target=raw[r['offset']:r['offset']+r['bytes']].decode();name=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(name),target))
  r=by[name];data=raw[r['offset']:r['offset']+r['bytes']];info,exports=elf_info(data);providers[name]={'member':name,'bytes':len(data),'sha256':sha(data),'needed':info['needed'],'symlink_chain':chain,'exports':exports}
 checks=[]
 for sym in z['imports']:
  matches=[name for name,p in providers.items() if any(n==sym['name'] for n,v in p['exports'])]
  assert matches or sym['weak'],sym;checks.append({**sym,'actual_provider_members':matches,'satisfied':bool(matches)})
 for p in providers.values():del p['exports']
 return {'schema':'fx6-worker-pool-shim-abi-v1','dynsym_contract_identical':True,'defined_symbol_set_identical':True,'undefined_symbol_contract_identical':True,'dt_needed_before':a['needed'],'dt_needed_after':z['needed'],'version_requirements_identical':True,'all_imports_unversioned_as_baseline':True,'actual_parent_cpio_providers':providers,'symbol_checks':checks,'required_imports_satisfied':True,'closure_note':'Preserves original shim no-DT_NEEDED lazy global resolution. Actual launcher loads libc/libdl; appFw needs libgcc_s for __clear_cache. No provider code is copied or changed.','guest_executed':False}
def main():
 vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert vol.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 parent_path=PARENT/'candidate-manifest.json';assert fp(parent_path)['sha256']==PARENT_MANIFEST_SHA
 parent=json.loads(parent_path.read_text());cpio=Path(parent['initrd']['path']);assert fp(cpio)['sha256']==PARENT_CPIO_SHA
 source=HERE/'libgrm-fbinit25-295.baseline.c';assert fp(source)['sha256']==BASE_SOURCE_SHA
 old_source=source.read_text();old_line='static const unsigned long offs[5] = {0x12d824cUL, 0x12d8250UL, 0x12d8254UL, 0x12d825cUL, 0xc09e50UL};';new_line='static const unsigned long offs[4] = {0x12d824cUL, 0x12d8250UL, 0x12d8254UL, 0xc09e50UL};'
 assert old_source.count(old_line)==1
 start=old_source.index('static void fx6_patch_blocking_calls(void *real_init) {');finish=old_source.index('\n}\n',start)+3;body=old_source[start:finish]
 assert body.count('for (int i = 0; i < 5; i++) {')==1
 new_body=body.replace(old_line,new_line,1).replace('for (int i = 0; i < 5; i++) {','for (int i = 0; i < 4; i++) {',1)
 new_source=old_source[:start]+new_body+old_source[finish:];restored_source=HERE/'libgrm-fbinit25-295.worker-pool-restore.c';restored_source.write_text(new_source)
 diff=''.join(difflib.unified_diff(old_source.splitlines(True),new_source.splitlines(True),fromfile=source.name,tofile=restored_source.name));(HERE/'source-change.diff').write_text(diff)
 with cpio.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
  rows=scan(raw);matches=[r for r in rows if r['name']==MEMBER];assert len(matches)==1;r=matches[0];old=raw[r['offset']:r['offset']+r['bytes']];assert sha(old)==BASE_SHIM_SHA;assert (HERE/'baseline-shim.so').read_bytes()==old
  assert nop_table(old)==BEFORE
 env=os.environ.copy();env.update(ZIG_LOCAL_CACHE_DIR=str(HERE/'zig-local-cache'),ZIG_GLOBAL_CACHE_DIR=str(HERE/'zig-global-cache'))
 flags=['-target','aarch64-linux-gnu','-shared','-fPIC','-nostdlib','-fno-sanitize=all','-fno-stack-protector','-O0','-g','-Wl,-soname,libgrm-fbinit9.so']
 commands=[]
 for src,out,label in [(source,HERE/'baseline-reproduced.so','baseline'),(restored_source,HERE/'libgrm-fbinit9.worker-pool-restore.so','restored')]:
  command=[str(ZIG),'cc',*flags,str(src),'-o',str(out)];r=subprocess.run(command,env=env,capture_output=True,text=True);(HERE/(label+'-compile-stdout.txt')).write_text(r.stdout);(HERE/(label+'-compile-stderr.txt')).write_text(r.stderr);r.check_returncode();commands.append(command)
 reproduced=(HERE/'baseline-reproduced.so').read_bytes();names,alloc,checks=sections_proof(old,reproduced)
 repro_ref=save('baseline-reproduction.json',{'schema':'fx6-worker-pool-baseline-reproduction-v1','actual_shim':fp(HERE/'baseline-shim.so'),'reproduced_shim':fp(HERE/'baseline-reproduced.so'),'source':fp(source),'sections_identical':True,'section_names':names,'all_allocated_section_names':alloc,'sections':checks,'command':commands[0],'command_provenance':'Reconstructed flags proven by exact original allocated sections; not an archived historical command.','guest_executed':False})
 restored=HERE/'libgrm-fbinit9.worker-pool-restore.so';new=restored.read_bytes();assert nop_table(new)==AFTER and len(set(AFTER))==4 and 0x12d825c not in nop_table(new)
 with cpio.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
  abi=verify_abi(raw,rows,old,new)
  app=next(r for r in rows if r['name']=='usr/lib/appFw.so');appdata=raw[app['offset']:app['offset']+app['bytes']];ae=ELFFile(io.BytesIO(appdata));va=0x12d825c;s=next(s for s in ae.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va< s['p_vaddr']+s['p_filesz']);off=s['p_offset']+va-s['p_vaddr'];word=struct.unpack_from('<I',appdata,off)[0];assert word&0xfc000000==0x94000000;imm=word&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;target=va+imm*4;assert target==0x1d96370
 abi_ref=save('abi-verification.json',abi)
 shim_build_ref=save('shim-build-receipt.json',{'schema':'fx6-worker-pool-shim-build-v1','source':fp(restored_source),'output':fp(restored),'command':commands[1],'compiler':fp(ZIG),'flags':flags,'baseline_reproduction':repro_ref,'abi_verification':abi_ref,'guest_executed':False})
 source_ref=save('source-change-verification.json',{'schema':'fx6-worker-pool-source-change-v1','baseline_source':fp(source),'restored_source':fp(restored_source),'source_diff':fp(HERE/'source-change.diff'),'baseline_shim':fp(HERE/'baseline-shim.so'),'restored_shim':fp(restored),'before_nop_offsets':[hex(n) for n in BEFORE],'after_nop_offsets':[hex(n) for n in AFTER],'removed_nop_offsets':['0x12d825c'],'all_other_source_bytes_identical':True,'changed_source_lines':2,'reason_for_second_line':'Array size and loop bound both hard-coded5; both become4, no implicit zero element or duplicate NOP offset.','baseline_reproduction':repro_ref,'build_receipt':shim_build_ref,'abi_verification':abi_ref,'guest_memory_callsite_readback':False})
 out=HERE/'guest-worker-pool-restore295.cpio'
 with cpio.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw,out.open('wb') as fo:
  cursor=0
  for r in rows:
   fo.write(raw[cursor:r['header']])
   if r['name']==MEMBER:
    header=bytearray(raw[r['header']:r['header']+110]);header[54:62]=f'{len(new):08x}'.encode();fo.write(header);fo.write(raw[r['header']+110:r['offset']]);fo.write(new);fo.write(b'\0'*(-len(new)%4))
   else:fo.write(raw[r['header']:r['end']])
   cursor=r['end']
  fo.write(raw[cursor:])
 with out.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:after=scan(raw)
 assert len(after)==len(rows) and [r['name'] for r in rows]==[r['name'] for r in after]
 for a,z in zip(rows,after):
  if a['name']==MEMBER:
   assert a['sha256']==sha(old) and z['sha256']==sha(new);assert [v for i,v in enumerate(a['fields']) if i!=6]==[v for i,v in enumerate(z['fields']) if i!=6]
  else:assert a['raw_sha256']==z['raw_sha256'],a['name']
 assert sum(r['name']=='TRAILER!!!' for r in after)==2
 proof_ref=save('member-diff-verification.json',{'schema':'fx6-worker-pool-restore-member-diff-v1','parent_snapshot_manifest':fp(parent_path),'parent_snapshot_cpio':fp(cpio),'derived_cpio':fp(out),'changed_existing_members':[MEMBER],'changed_member_payload':{'member':MEMBER,'before':fp(HERE/'baseline-shim.so'),'after':fp(restored)},'source_change_verification':source_ref,'all_other_raw_records_byte_identical':True,'original_order_preserved':True,'both_original_trailer_records_byte_identical':True,'before_records':len(rows),'after_records':len(after),'before_trailers':2,'after_trailers':2,'native_restored_callsite':{'appfw_member_sha256':sha(appdata),'elf_va':hex(va),'file_offset':hex(off),'original_four_bytes_hex':appdata[off:off+4].hex(),'instruction_word':hex(word),'decoded_bl_target':hex(target),'guest_memory_readback_performed':False},'new_shim_nop_table':[hex(n) for n in nop_table(new)],'guest_executed':False})
 manifest=dict(parent);manifest.update(schema='fx6-worker-pool-restore-candidate-v1',status='PREPARED_WORKER_POOL_RESTORE',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mode='worker-pool-restore',scope='restore original45worker creation by removing only295 shim NOP at0x12d825c',parent_snapshot_manifest=fp(parent_path),parent_snapshot_initrd=fp(cpio),initrd=fp(out),input_member_diff_verification=proof_ref,source_change_verification=source_ref,shim_abi_verification=abi_ref,restored_shim=fp(restored),intentional_restore={'native_callsite':'0x12d825c','native_target':'0x1d96370','native_worker_count':45,'removed_shim_nop_only':True},frozen_behavior=['original appFw payload','remaining four NOP sites0x12d824c/0x12d8250/0x12d8254/0xc09e50','all other shim source and behavior including Backup and MWF guard','observer library and explicit recv GOT diagnostic launcher','snapshot helper and init','timeouts and model environment','120s wall budget and original key/capture sequence'])
 manifest['diagnostic_changes']=parent['diagnostic_changes'];argv=parent['candidate_argv_before_observer_serial_retarget'].copy();count=0
 for i,arg in enumerate(argv):
  if arg.startswith('loader,file=') and str(cpio) in arg:argv[i]=arg.replace(str(cpio),str(out));count+=1
 assert count==1;manifest['candidate_argv_before_observer_serial_retarget']=argv
 manifest_ref=save('candidate-manifest.json',manifest);(HERE/'candidate-manifest.sha256').write_text(manifest_ref['sha256']+'\n')
 save('candidate-build-receipt.json',{'schema':'fx6-worker-pool-candidate-build-v1','manifest':manifest_ref,'source_change_verification':source_ref,'member_diff':proof_ref,'shim_build':shim_build_ref,'baseline_reproduction':repro_ref,'abi_verification':abi_ref,'builder':fp(HERE/'build_candidate.py'),'tools':fp(HERE/'candidate_tools.py'),'guest_executed':False})
 assert fp(parent_path)['sha256']==PARENT_MANIFEST_SHA and fp(cpio)['sha256']==PARENT_CPIO_SHA
 print(json.dumps({'manifest':manifest_ref,'initrd':fp(out),'restored_shim':fp(restored),'changed_existing_members':[MEMBER],'removed_nop_offsets':['0x12d825c'],'baseline_allocated_sections_identical':True,'imports_verified':len(abi['symbol_checks']),'guest_executed':False},indent=2))
if __name__=='__main__':main()
