from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap100-v1-touch-backup-sync';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();authority='msg_db11d2266751'
for old,new in [('gate_input99.py','gate_input100.py'),('key_readback99.py','key_readback100.py'),('run_candidate99_r2.py','run_candidate100_v1.py'),('ap99_decide_v1.py','ap100_decide_v1.py')]:
 p=R/new;assert not p.exists();s=(R/old).read_text().replace('gate_input99','gate_input100').replace('key_readback99','key_readback100').replace('ap99-','ap100-').replace('msg_fa0d4b6ae7b5',authority)
 if new=='gate_input100.py':
  s+='''
 def shutdown_control(self):
  self.connect();address=0x41d400030;magic=bytes.fromhex(self.packet('m41d400000,8'))
  if magic!=b'F100FILE':raise RuntimeError('new observer reservation identity mismatch')
  data=struct.pack('<Q',0x100c1ea9)
  if self.packet(f'M{address:x},8:{data.hex()}')!='OK' or bytes.fromhex(self.packet(f'm{address:x},8'))!=data:raise RuntimeError('shutdown observer control readback failed')
  (self.run/'ap100-shutdown-control.json').write_text(json.dumps({'physical':hex(address),'bytes':8,'written_hex':data.hex(),'readback_verified':True,'software_observer_only':True,'reason':'after observation and final snapshots, stop owned guest AP then restore native deviceAPI; keep main module resident'},indent=2)+'\\n')
'''
 if new=='run_candidate100_v1.py':
  s=s.replace("'key_readback100.py','gate_input100.py']","'key_readback100.py','gate_input100.py','file_readback100.py']")
  s=s.replace('from gate_input100 import InputGate,valid_command','from gate_input100 import InputGate,valid_command\nfrom file_readback100 import capture as capture_native_file')
  s=s.replace('            phaseA_proof={}\n','            phaseA_proof={}\n            next_native_file=guest_start+20\n            native_file_reads=[]\n')
  s=s.replace("                if 'FX3_DATE99_REJECT' in serial_now:","                if re.search(r'FX3_SYNC100_REJECT|FX3_SYNC100_DISABLED|FX3_TOUCH100_REJECT|FX3_PRESET_CONTEXT_BIND_REJECT|FX3_SYNC100_API_BIND[^\\n]*result=-',serial_now):\n                    early_stop_reason='AP100 new device contract or observer binding rejected; no further input';break\n                if time.monotonic()>=next_native_file:\n                    qmp('stop');native_file_reads.append(capture_native_file(qmp,run,'periodic-%02d'%len(native_file_reads)));qmp('cont');next_native_file=time.monotonic()+20\n                if 'FX3_DATE99_REJECT' in serial_now:")
  s=s.replace("                    (run/'ap100-backup-after-setup-v2.json').write_text", "                    native_file_reads.append(capture_native_file(qmp,run,'before-menu'))\n                    (run/'ap100-backup-after-setup-v2.json').write_text")
  needle="                qmp('query-status')\n                qmp('query-cpus-fast')\n                qmp('quit')";assert needle in s
  s=s.replace(needle,"""                native_file_reads.append(capture_native_file(qmp,run,'final-before-shutdown'))
                (run/'ap100-native-file-readbacks.json').write_text(json.dumps(native_file_reads,indent=2)+'\\n')
                shutdown={'observation_complete':True,'serial_bytes_before_cleanup':(run/'serial.log').stat().st_size,'cleanup_is_after_acceptance_window':True}
                (run/'ap100-cleanup-phase.json').write_text(json.dumps(shutdown,indent=2)+'\\n')
                if 'FX3_FILE100_OBSERVER_READY' in kernel_text:
                    input_gate.shutdown_control();qmp('cont');time.sleep(3);qmp('stop')
                    native_file_reads.append(capture_native_file(qmp,run,'after-device-restore'))
                    qmp('human-monitor-command',{'command-line':'memsave 0xffffff80083220c8 0x10 "'+str(run/'pcidma-original16-restored.bin')+'"'})
                    (run/'ap100-native-file-readbacks.json').write_text(json.dumps(native_file_reads,indent=2)+'\\n')
                qmp('query-status')
                qmp('query-cpus-fast')
                qmp('quit')""")
 p.write_text(s);compile(s,str(p),'exec')
base=R/'ap99-r2-user-backup-nread/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
replacements={'simulation/fx3-cp-backup-reset-v1.ko':'fx3-cp-backup-v4-sync100.ko','simulation/fx3-capid-v1.so':'fx3-capid-v49-touch100.so','simulation/fx3-backup-return-v1.so':'fx3-backup-return-v4-sync100.so','simulation/fx3-preset-context-v2-screen.so':'fx3-preset-context-v5-sync100.so'}
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n in replacements:b=(H/replacements[n]).read_bytes();changed.append(n)
 if n=='init':
  text=b.decode();needle=' FX3_RM_EMPTY=cache-replay-v1';assert text.count(needle)==1;text=text.replace(needle,' FX3_TOUCH_PANEL=headless_touch_config'+needle)
  needle=' echo FX3_AP_NATURAL_BOOTIN_BEGIN';assert needle in text;text=text.replace(needle,' /simulation/fx3-file100-observer-v1 &\n echo FX3_FILE100_OBSERVER_PID=$!\n'+needle);b=text.encode();changed.append(n)
 entries.append((n,f,b))
assert set(changed)==set(replacements)|{'init'}
mode=[0]*13;mode[1]=0o100755;mode[4]=1
for n in ['fx3-file100-observer-v1','fx3-sync100-unbind-v1.ko']:entries.append(('simulation/'+n,mode.copy(),(H/n).read_bytes()))
shutdown=b'''#!/bin/sh
echo FX3_AP100_CONTROLLED_CLEANUP_BEGIN acceptance_window_closed=1
for p in $(/bin/busybox pidof im.elf); do /bin/busybox kill -STOP "$p"; done
/bin/busybox sleep 1
/bin/busybox insmod /simulation/fx3-sync100-unbind-v1.ko
rc=$?
echo FX3_AP100_CONTROLLED_CLEANUP_END unbind_result=$rc primary_module_resident=1
exit $rc
'''
entries.append(('simulation/fx3-sync100-shutdown.sh',mode.copy(),shutdown));D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());reserved=[struct.unpack_from('>QQ',res,i) for i in range(0,len(res)-16,16)];a,n=0x41d400000,0x300000;assert all(a+n<=x or x+y<=a for x,y in reserved);res=res[:-16]+struct.pack('>QQ',a,n)+bytes(16)
chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');new=[]
for k,q in chosen['items']:
 if k=='prop' and q[0]=='linux,initrd-end':q=(q[0],struct.pack('>Q',0x440000000+len(out)))
 if k=='prop' and q[0]=='bootargs':q=(q[0],q[1][:-1]+b' memrsv=0x00300000@0x41d400000:uc\0')
 new.append((k,q))
chosen['items']=new;dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)};v['host_step_contract']['authority']=authority;v['scope']='AP100 baselineAP99-r2; exact VDF0146 ON1 accepted software config pending hardware, per-native-reply lease and rollback; existing single CPowner exact op30(3,1)/(0,1) genuine4096 reply, frozen current CPmodel backing fullbank snapshot, real copy+readback toAPsecondbank, originalcallback once; explicit source_alias_destination=1 synthetic_cp_backup_sync=1 original_CP=0. Native pcidma device API binding through native synchronized text patch, exact original16 guard; non-target uses relocated original API. Passive seven original user points, actual Backup_sync_all return, guest O_RDONLY Backup.bin double read to new observer-only reservation41d400000/300000. After600 acceptance snapshot, stopownedguestAP and restoredeviceAPI leavingmainmodule resident beforeQEMUquit. No original firmware input modification, no business parameter/force/busy writes or synthetic UI readiness.'
v['required_markers']+=['FX3_SYNC100_BACKEND_BOUND','FX3_TOUCH100_COMMIT','FX3_TOUCH100_CONSUMED','FX3_SYNC100_DMA_COPY','FX3_SYNC100_NATIVE_CALLBACK_RETURN','FX3_FILE100_OBSERVER_READY'];v['ap100_contract']={'authority':[authority,'msg_e26a15170c50'],'base':str(base),'source_alias_destination':True,'file_observer_reservation':{'physical':hex(a),'bytes':n},'original_16_hex':'000b00b4fd7bbba9fd030091f35301a9','restoration_required':True};(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);diff=[n for n in bm if bm[n]!=am[n]];assert set(diff)==set(changed);ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');init=D/'init-reviewed.sh';init.write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(init)],check=True);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':diff,'new_members':[n for n in am if n not in bm],'all_other_members_unchanged':True,'DTB_delta':'initrd-end plus new observer-only reservation/memrsv','authority':authority},indent=2)+'\n');print(D/'candidate.json')
