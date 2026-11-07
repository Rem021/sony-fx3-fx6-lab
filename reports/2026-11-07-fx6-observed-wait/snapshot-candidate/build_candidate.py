#!/usr/bin/env python3
"""Offline-only derivation from the sealed observer-295; never starts a VM."""
import datetime, difflib, hashlib, io, json, mmap, os, plistlib, posixpath, re, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'fx6-observer-integration-20261107'
PARENT_MANIFEST_SHA='d5732c03c54f76f676a5fbf42fd2256715ae2afce42f9f6ddbf4e537d6c954fe'
PARENT_CPIO_SHA='d02c7909458dcf8dff73fdf426953d07034cb386f8c8bd0bbd40a9440d32569e'
ZIG=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig')
SDK=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/guest-sdk/lib')
SDK_SHA={'libc-2.25.so':'f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9','ld-2.25.so':'90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a'}
def sha(b):return hashlib.sha256(b).hexdigest()
def fp(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def save(name,value):
 (HERE/name).write_text(json.dumps(value,indent=2)+'\n');return fp(HERE/name)
def scan(b):
 rows=[];pos=0;nonzero=re.compile(b'[^\x00]')
 while pos+110<=len(b):
  if b[pos]==0:
   m=nonzero.search(b,pos)
   if not m:break
   pos=m.start()
  assert b[pos:pos+6]==b'070701',pos
  v=[int(b[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
  n=b[pos+110:pos+110+v[11]];assert len(n)==v[11] and n[-1:]==b'\0'
  start=(pos+110+v[11]+3)&~3;end=(start+v[6]+3)&~3;assert end<=len(b)
  rows.append({'name':n[:-1].decode(),'header':pos,'offset':start,'bytes':v[6],'end':end,'fields':v,'sha256':sha(b[start:start+v[6]]),'raw_sha256':sha(b[pos:end])});pos=end
 assert not any(b[pos:]);return rows
def new_record(name,payload,ino):
 n=name.encode()+b'\0';v=[ino,0o100555,0,0,1,0,len(payload),0,0,0,0,len(n),0]
 h=b'070701'+b''.join(f'{x:08x}'.encode() for x in v)+n;h+=b'\0'*(-len(h)%4)
 return h+payload+b'\0'*(-len(payload)%4)
def elf_info(data):
 e=ELFFile(io.BytesIO(data));dyn=e.get_section_by_name('.dynsym');vs=e.get_section_by_name('.gnu.version');required={};defined={}
 vn=e.get_section_by_name('.gnu.version_r')
 if vn:
  for version,aux in vn.iter_versions():
   for item in aux:required[item['vna_other']]=(version.name,item.name)
 vd=e.get_section_by_name('.gnu.version_d')
 if vd:
  for version,aux in vd.iter_versions():defined[version['vd_ndx']]=next(aux).name
 imports=[];exports=set()
 for i,s in enumerate(dyn.iter_symbols()):
  if not s.name:continue
  v=vs.get_symbol(i)['ndx'] if vs else 'VER_NDX_GLOBAL'
  if isinstance(v,int):v &= 0x7fff
  if s['st_shndx']=='SHN_UNDEF':
   library,version=required.get(v,(None,None));imports.append({'name':s.name,'version':version,'provider':library,'weak':s['st_info']['bind']=='STB_WEAK'})
  else:exports.add((s.name,defined.get(v)))
 needed=[t.needed for t in e.get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag=='DT_NEEDED']
 interp=next((s.get_interp_name() for s in e.iter_segments() if s['p_type']=='PT_INTERP'),None)
 return {'machine':e['e_machine'],'type':e['e_type'],'needed':needed,'interpreter':interp,'imports':imports},exports
def verify_abi(raw,rows,helper):
 by={r['name']:r for r in rows};providers={};edges=[]
 def provider(soname):
  for directory in ['lib','usr/lib']:
   n=directory+'/'+soname
   if n not in by:continue
   chain=[]
   while by[n]['fields'][1]&0o170000==0o120000:
    assert n not in chain;chain.append(n);r=by[n];target=raw[r['offset']:r['offset']+r['bytes']].decode();n=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(n),target))
   r=by[n];data=raw[r['offset']:r['offset']+r['bytes']]
   if n not in providers:
    info,exports=elf_info(data);providers[n]={'member':n,'bytes':len(data),'sha256':sha(data),'symlink_chain':chain,**info,'exports':exports}
   return n
  raise ValueError('missing actual guest provider '+soname)
 root,_=elf_info(helper);assert root['machine']=='EM_AARCH64' and root['type']=='ET_EXEC' and root['interpreter']=='/lib/ld-linux-aarch64.so.1'
 assert set(root['needed'])=={'libc.so.6'}
 assert {x['version'] for x in root['imports'] if x['version']}=={'GLIBC_2.17'}
 assert not {'fork','vfork','clone','execve','execv','system','popen','kill'} & {x['name'] for x in root['imports']}
 pending=['helper'];allinfo={'helper':root};complete=set()
 while pending:
  label=pending.pop(0)
  if label in complete:continue
  info=allinfo.get(label) or providers[label]
  if info['interpreter']:provider(posixpath.basename(info['interpreter']))
  for soname in info['needed']:
   p=provider(soname);edges.append({'consumer':label,'needed':soname,'actual_member':p});pending.append(p)
  complete.add(label)
 checks=[]
 for label,info in {**allinfo,**providers}.items():
  for sym in info['imports']:
   names=[provider(sym['provider'])] if sym['provider'] else list(providers)
   hits=[p for p in names if (sym['name'],sym['version']) in providers[p]['exports'] or (sym['version'] is None and any(n==sym['name'] for n,v in providers[p]['exports']))]
   assert hits or sym['weak'],(label,sym);checks.append({'consumer':label,**sym,'actual_providers':hits,'satisfied':bool(hits)})
 for info in providers.values():del info['exports']
 for name,expected in SDK_SHA.items():assert providers['lib/'+name]['sha256']==expected
 return {'schema':'fx6-wait-snapshot-abi-v1','root_object':root,'actual_guest_providers':providers,'dependency_edges':edges,'symbol_checks':checks,'required_imports_satisfied':True,'guest_executed':False}
def main():
 vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert vol.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 assert fp(PARENT/'candidate-manifest.json')['sha256']==PARENT_MANIFEST_SHA
 parent=json.loads((PARENT/'candidate-manifest.json').read_text());base=Path(parent['initrd']['path']);assert fp(base)['sha256']==PARENT_CPIO_SHA
 for n,h in SDK_SHA.items():assert fp(SDK/n)['sha256']==h
 env=os.environ.copy();env.update(ZIG_LOCAL_CACHE_DIR=str(HERE/'zig-local-cache'),ZIG_GLOBAL_CACHE_DIR=str(HERE/'zig-global-cache'))
 commands=[]
 def run(c,label):
  r=subprocess.run(c,env=env,capture_output=True,text=True);(HERE/(label+'-stdout.txt')).write_text(r.stdout);(HERE/(label+'-stderr.txt')).write_text(r.stderr);r.check_returncode();commands.append(c);return r.stdout
 run(['/usr/bin/clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-pedantic',str(HERE/'snapshot_core.c'),str(HERE/'test_snapshot_core.c'),'-o',str(HERE/'test_snapshot_core')],'host-compile')
 test_output=run([str(HERE/'test_snapshot_core')],'host-test')
 for source in ['snapshot_core.c','wait_snapshot.c','entry.S']:
  run([str(ZIG),'cc','-target','aarch64-linux-gnu.2.17','-O2','-fno-pie','-fno-sanitize=all','-fno-stack-protector','-fno-builtin','-Wall','-Wextra','-Werror','-c',str(HERE/source),'-o',str(HERE/(source+'.o'))],'compile-'+source)
 run([str(ZIG),'ld.lld','-o',str(HERE/'fx6-wait-snapshot'),'-e','_start','--dynamic-linker=/lib/ld-linux-aarch64.so.1','--no-undefined','--no-allow-shlib-undefined','--hash-style=both','-z','noexecstack','-z','relro','-z','now',*[str(HERE/(s+'.o')) for s in ['snapshot_core.c','wait_snapshot.c','entry.S']],'--as-needed',str(SDK/'libc-2.25.so'),str(SDK/'ld-2.25.so')],'link')
 helper=(HERE/'fx6-wait-snapshot').read_bytes();out=HERE/'guest-wait-snapshot295.cpio'
 with base.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
  rows=scan(raw);assert len([r for r in rows if r['name']=='TRAILER!!!'])==2 and rows[-1]['name']=='TRAILER!!!'
  assert not any(r['name']=='usr/bin/fx6-wait-snapshot' for r in rows)
  r=next(r for r in rows if r['name']=='init');old=raw[r['offset']:r['offset']+r['bytes']].decode()
  marker='while true; do\n for t in /proc/$appfw_pid/task/*; do';assert old.count(marker)==1
  replacement='''fx6_wait_snapshot_done=0
while true; do
 if [ "$fx6_wait_snapshot_done" = 0 ]; then
  read fx6_wait_uptime fx6_wait_idle < /proc/uptime
  if [ "${fx6_wait_uptime%%.*}" -ge 20 ]; then
   fx6_wait_snapshot_done=1
   echo FX6_WAIT_SNAPSHOT_INIT_BEGIN pid=$appfw_pid uptime=$fx6_wait_uptime
   /usr/bin/fx6-wait-snapshot "$appfw_pid"
   echo FX6_WAIT_SNAPSHOT_INIT_END rc=$?
  fi
 fi
 for t in /proc/$appfw_pid/task/*; do'''
  new=old.replace(marker,replacement,1);(HERE/'parent-init.sh').write_text(old);(HERE/'candidate-init.sh').write_text(new)
  (HERE/'init-only.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='observer295-init',tofile='wait-snapshot-init')))
  run(['/bin/sh','-n',str(HERE/'candidate-init.sh')],'shell-syntax')
  abi=verify_abi(raw,rows,helper);save('abi-closure-verification.json',abi)
  cursor=0
  with out.open('wb') as fo:
   for i,r in enumerate(rows):
    fo.write(raw[cursor:r['header']])
    if i==len(rows)-1:fo.write(new_record('usr/bin/fx6-wait-snapshot',helper,max(z['fields'][0] for z in rows)+1))
    if r['name']=='init':
     payload=new.encode();header=bytearray(raw[r['header']:r['header']+110]);header[54:62]=f'{len(payload):08x}'.encode();fo.write(header);fo.write(raw[r['header']+110:r['offset']]);fo.write(payload);fo.write(b'\0'*(-len(payload)%4))
    else:fo.write(raw[r['header']:r['end']])
    cursor=r['end']
   fo.write(raw[cursor:])
 with out.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:after=scan(raw)
 assert len(after)==len(rows)+1 and after[-2]['name']=='usr/bin/fx6-wait-snapshot'
 original_after=[r for r in after if r['name']!='usr/bin/fx6-wait-snapshot'];assert [r['name'] for r in rows]==[r['name'] for r in original_after]
 changes=[]
 for a,z in zip(rows,original_after):
  if a['name']=='init':
   assert a['sha256']!=z['sha256'];assert [x for i,x in enumerate(a['fields']) if i!=6]==[x for i,x in enumerate(z['fields']) if i!=6]
   changes.append({'member':'init','before':{k:a[k] for k in ['bytes','sha256']},'after':{k:z[k] for k in ['bytes','sha256']},'reason':'once-only uptime20 gate and helper invocation in existing diagnostic loop'})
  else:assert a['raw_sha256']==z['raw_sha256'],a['name']
 added=after[-2];assert added['sha256']==sha(helper)
 first=next(i for i,r in enumerate(rows) if r['name']=='TRAILER!!!')
 proof={'schema':'fx6-wait-snapshot-member-diff-v1','parent_observer_cpio':fp(base),'derived_cpio':fp(out),'changed_existing_members':changes,'added_member':{k:added[k] for k in ['name','bytes','sha256']},'before_records':len(rows),'after_records':len(after),'before_trailers':2,'after_trailers':2,'both_original_trailer_records_byte_identical':True,'original_order_preserved':True,'all_other_raw_records_byte_identical':True,'parent_records_after_first_trailer':len(rows)-first-1,'appfw_launcher_observer_shim_backup_unchanged':True,'guest_executed':False}
 proof_fp=save('member-diff-verification.json',proof)
 manifest=dict(parent);manifest.update(schema='fx6-wait-snapshot-candidate-v1',status='PREPARED_WAIT_SNAPSHOT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mode='wait-snapshot',scope='single bounded ptrace register/stack snapshot of existing appfw TIDs; no VM execution by builder',parent_observer_manifest=fp(PARENT/'candidate-manifest.json'),parent_observer_initrd=fp(base),initrd=fp(out),input_member_diff_verification=proof_fp,abi_verification=fp(HERE/'abi-closure-verification.json'),snapshot_helper=fp(HERE/'fx6-wait-snapshot'),snapshot_trigger={'guest_uptime_min_s':20,'poll':'existing3sdiagnosticloop','once':True,'target':'appfw_pid_only','max_enumerated_tids':512,'per_tid_wait_ms':200,'cleanup_wait_ms':250,'global_alarm_s':6,'hard_cleanup_grace_s':1,'max_fp_frames':20},diagnostic_interference='SEIZE+INTERRUPT temporarily pauses one thread at a time; scheduling and syscall timing may change; all stops logged; no PTRACE_SET/POKE or message edits')
 manifest['diagnostic_changes']=parent['diagnostic_changes']+['once-only bounded ptrace snapshot helper and existing init diagnostic-loop invocation']
 argv=parent['candidate_argv_before_observer_serial_retarget'].copy();count=0
 for i,arg in enumerate(argv):
  if arg.startswith('loader,file=') and str(base) in arg:argv[i]=arg.replace(str(base),str(out));count+=1
 assert count==1;manifest['candidate_argv_before_observer_serial_retarget']=argv
 manifest_fp=save('candidate-manifest.json',manifest);(HERE/'candidate-manifest.sha256').write_text(manifest_fp['sha256']+'\n')
 receipt={'schema':'fx6-wait-snapshot-build-v1','compiler':fp(ZIG),'compiler_version':subprocess.check_output([str(ZIG),'version'],text=True).strip(),'sources':[fp(HERE/n) for n in ['snapshot_core.h','snapshot_core.c','wait_snapshot.c','entry.S','test_snapshot_core.c','build_candidate.py']],'sdk_libraries':[fp(SDK/n) for n in SDK_SHA],'commands':commands,'host_test':test_output.strip(),'helper':fp(HERE/'fx6-wait-snapshot'),'manifest':manifest_fp,'member_proof':proof_fp,'abi_proof':fp(HERE/'abi-closure-verification.json'),'source_scope':{'no_fork_exec':True,'no_ptrace_poke_set':True,'peekdata_only_current_sp_stack':True,'sequential_stop_detach':True},'guest_executed':False}
 save('build-receipt.json',receipt)
 assert fp(PARENT/'candidate-manifest.json')['sha256']==PARENT_MANIFEST_SHA and fp(base)['sha256']==PARENT_CPIO_SHA
 print(json.dumps({'manifest':manifest_fp,'initrd':fp(out),'helper':fp(HERE/'fx6-wait-snapshot'),'strong_imports_verified':sum(not c['weak'] for c in abi['symbol_checks']),'host_test':test_output.strip(),'trailers_preserved':2,'guest_executed':False},indent=2))
if __name__=='__main__':main()
