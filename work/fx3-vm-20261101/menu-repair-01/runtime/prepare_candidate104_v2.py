from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
from cpio_audit import parse,audit
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap104-r2-observer-ready';assert not D.exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=R/'ap104-v1-completion-trace/candidate.json';v=json.loads(base.read_text());exe=H/'fx3-file100-observer-v2';assert sha(exe)==json.loads((H/'fx3-file100-observer-v2-build.json').read_text())['output_sha256']
data=Path(v['initrd']['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==v['initrd']['sha256'];off=0;entries=[];mode=None
barrier=''' /simulation/fx3-file100-observer-v2 &
 file103_pid=$!
 echo FX3_FILE100_OBSERVER_PID=$file103_pid
 file103_ready=0
 file103_wait=0
 while [ "$file103_wait" -lt 200 ]; do
  if [ -r /tmp/fx3-file100-ready-v2 ]; then
   if read file103_signature file103_ready_pid < /tmp/fx3-file100-ready-v2 && [ "$file103_signature" = F100FILE_READY_V2 ] && [ "$file103_ready_pid" = "$file103_pid" ] && /bin/busybox kill -0 "$file103_pid"; then file103_ready=1; break; fi
  fi
  if ! /bin/busybox kill -0 "$file103_pid"; then break; fi
  /bin/busybox sleep 0.05
  file103_wait=$((file103_wait + 1))
 done
 if [ "$file103_ready" != 1 ]; then echo FX3_FILE103_READY_FAILED before_CP_API_bind=1; while true; do /bin/busybox sleep 1; done; fi
 echo FX3_FILE103_READY_CONFIRMED pid=$file103_pid before_CP_API_bind=1
'''
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16)for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n=='simulation/fx3-file100-observer-v1':mode=f.copy()
 if n=='init':
  s=b.decode();late=' /simulation/fx3-file100-observer-v1 &\n echo FX3_FILE100_OBSERVER_PID=$!\n';assert s.count(late)==1;s=s.replace(late,'')
  needle=' echo FX3_BACKUP_CP_INSMOD_BEGIN\n';assert s.count(needle)==1;s=s.replace(needle,barrier+needle);b=s.encode()
 entries.append((n,f,b))
assert mode is not None;assert not any(n=='simulation/fx3-file100-observer-v2'for n,_,_ in entries);entries.append(('simulation/fx3-file100-observer-v2',mode,exe.read_bytes()));D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();s=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(s);out.extend(b'070701'+''.join(f'{x:08x}'for x in f).encode()+s);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b)in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,_,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items']if k=='node'and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out))))if k=='prop'and q[0]=='linux,initrd-end'else(k,q)for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)}
v['scope']+=' AP104-r2 starts the same read-only file/control observer before CP API binding, requires a matching live PID readiness marker, and removes its late duplicate startup. New observer only adds readiness after header initialization; original shutdown script, CP/GPE/Backup/LDEC models unchanged.'
v['ap104_readiness_fix']={'authority':'msg_45f1419f7e5e','base':str(base),'base_sha256':sha(base),'ready_before_CP_binding':True,'readiness_matches_live_PID':True,'wait_bound_guest_seconds':10,'observer':str(exe),'observer_sha256':sha(exe),'late_duplicate_removed':True,'API_cleanup':'restore_api103_v2: original/no pending request never resumes; otherwise ack plus exact original16'}
v['required_markers']+=['FX3_FILE103_READY_CONFIRMED'];(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert set(am)-set(bm)=={'simulation/fx3-file100-observer-v2'};assert not set(bm)-set(am);diff=[n for n in bm if bm[n]!=am[n]];assert diff==['init'];assert am['simulation/fx3-sync100-shutdown.sh']==bm['simulation/fx3-sync100-shutdown.sh'];assert b'/simulation/fx3-file100-observer-v1 &'not in am['init'];assert am['init'].index(b'FX3_FILE103_READY_CONFIRMED')<am['init'].index(b'FX3_BACKUP_CP_INSMOD_BEGIN')
ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'init-reviewed.sh').write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(D/'init-reviewed.sh')],check=True);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_SHA256':sha(base),'changed_existing_member_bodies':diff,'added_member':'simulation/fx3-file100-observer-v2','all_other_existing_members_unchanged':True,'DTB_only_initrd_end':True,'original_shutdown_script_unchanged':True,'CP_GPE_Backup_LDEC_models_unchanged':True,'control_transport_ready_before_API_bind':True},indent=2)+'\n');print(D/'candidate.json')
