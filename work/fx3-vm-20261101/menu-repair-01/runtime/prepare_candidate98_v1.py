from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap98-v1-date-readonly';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();authority='msg_de25f58b89eb'
for old,new in [('gate_input97_r2.py','gate_input98.py'),('key_readback97_r2.py','key_readback98.py'),('run_candidate97_r2.py','run_candidate98.py'),('ap97r2_decide_v1.py','ap98_decide_v1.py')]:
 p=R/new;s=(R/old).read_text().replace('gate_input97_r2','gate_input98').replace('key_readback97_r2','key_readback98').replace('ap97r2-','ap98-').replace('msg_155b0cf9b5b7',authority)
 if new=='run_candidate98.py':
  needle="        if (address, size) == (0x41df00000, 0x10000):";assert needle in s;s=s.replace(needle,needle+"\n            snapshots.append({'address':0x41df01000,'size':0x6000,'name':'date98-trace-final.bin','scope':'Read-only observer-output copy only, native user32 and kernel44; first4K input unchanged'})")
  needle="                        captured=capture_frame(qmp,run,f'step-{step:02d}-key-{key:03x}',step,key,at)";assert needle in s;s=s.replace(needle,needle+'''
                        trace_path=run / ('date98-trace-step-%02d.bin' % step)
                        qmp('human-monitor-command',{'command-line':'pmemsave 0x41df01000 0x6000 '+chr(34)+str(trace_path)+chr(34)})''')
  # One extra read-only snapshot in the same pause as explicitly requested UI readback.
  needle="extra=capture_frame(qmp,run,label,host_step,0,time.monotonic());qmp('cont')";assert needle in s;s=s.replace(needle,"extra=capture_frame(qmp,run,label,host_step,0,time.monotonic());qmp('human-monitor-command',{'command-line':'pmemsave 0x41df01000 0x6000 '+chr(34)+str(run / ('date98-trace-'+label+'.bin'))+chr(34)});qmp('cont')")
 p.write_text(s);compile(s,str(p),'exec')
base=R/'ap97-r2-const-alpha-date-observe/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
replacements={'simulation/fx3-preset-context-v2-screen.so':'fx3-preset-context-v4-date98.so','simulation/fx3-cp-backup-reset-v1.ko':'fx3-cp-backup-reset-v2-date98.ko'}
proc='''  if [ -r /tmp/fx3-date98-active.identity ]; then
   read date98_pid date98_tid date98_event date98_pointer date98_bytes < /tmp/fx3-date98-active.identity
   echo FX3_DATE98_THREAD_BEGIN pid=$date98_pid tid=$date98_tid event=$date98_event pointer=$date98_pointer bytes=$date98_bytes
   /bin/busybox cat /proc/uptime /proc/$date98_pid/task/$date98_tid/status /proc/$date98_pid/task/$date98_tid/wchan /proc/$date98_pid/task/$date98_tid/stack
   echo FX3_DATE98_THREAD_END
  fi
'''
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n in replacements:b=(H/replacements[n]).read_bytes();changed.append(n)
 if n=='init':s=b.decode();needle=' (while true; do\n';assert s.count(needle)==1;s=s.replace(needle,needle+proc);b=s.encode();changed.append(n)
 entries.append((n,f,b))
assert set(changed)==set(replacements)|{'init'};D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)};v['host_step_contract']['authority']=authority;v['scope']='AP98 passive date observation only, AP97-r2 model bodies otherwise unchanged. Preset4 adds original instruction-verified clock initial setting2b725c8/call2b72680/return2b72684, common sync front/back, force clear and Backup_write returns. Fresh selfmem/live values at native screen opens; caller-owned exact32 original sync request copied before/after with pid/tid/result/errno, no altered body/result. Existing CP Backup publicsender same fallback return0/no-free/no-reply, adds target909005c5 native44B read-only capture. Software observer output only41df01000/6000 within existing reservation, leaves first4K input/diag untouched; QMP readback perstep/final and independent target-thread proc status. No date replies, flag writes, checksum or model changes.';v['required_markers']=[m for m in v['required_markers'] if m!='FX3_DATE97_POINT']+['FX3_DATE98_TRACE_BOUND','FX3_DATE98_KERNEL_OBSERVE_READY','FX3_DATE98_LIVE'];v['date_observer_contract']={'authority':[authority,'msg_2c43f8a7ac82'],'software_output':{'physical':'0x41df01000','bytes':0x6000,'cap':64,'record_bytes':320,'native_request_reply_max_bytes':64},'kernel_target':'0x909005c5','kernel_bytes':44,'user_target':'0x80900141','user_bytes':32,'reply_or_setter_added':False,'after_return_conditional_not_required_marker':True,'clock_initial_call_and_result':['0x2b72680','0x2b72684']};(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);diff=[n for n in bm if bm[n]!=am[n]];assert set(diff)==set(changed);ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');init=D/'init-reviewed.sh';init.write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(init)],check=True)
(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':diff,'all_other_members_unchanged':True,'DTB_only_initrd_end':True,'tests':{str(H/x):sha(H/x) for x in ['check-date98-user-v1.log','check-date98-kernel-v1.log','check-date98-core-v1.log']},'helpers':{n:{'body':x,'sha256':sha(H/x)} for n,x in replacements.items()},'authority':[authority,'msg_2c43f8a7ac82']},indent=2)+'\n');print(D/'candidate.json')
