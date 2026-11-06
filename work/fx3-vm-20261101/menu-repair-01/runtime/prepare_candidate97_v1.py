from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap97-v1-repeat-panel-enum2';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();authority='msg_1866471baef3'
for old,new in [('gate_input96.py','gate_input97.py'),('key_readback96.py','key_readback97.py'),('run_candidate96.py','run_candidate97.py'),('ap96_decide_v1.py','ap97_decide_v1.py')]:
 p=R/new;assert not p.exists();s=(R/old).read_text().replace('gate_input96','gate_input97').replace('key_readback96','key_readback97').replace('ap96-','ap97-').replace('msg_48dccc7b7d3d',authority)
 if new=='run_candidate97.py':
  needle="                serial_now=(run/'serial.log').read_text(errors='replace')"
  assert needle in s;s=s.replace(needle,needle+"\n                if re.search(r'assert at|Assertion|exception monitor|FX3_SIGNAL_OBSERVE[^\\n]*signal=6(?: |$)',serial_now,re.I):\n                    early_stop_reason='AP97 native assertion/abort/exception marker; stop before any further key';break")
 p.write_text(s);compile(s,str(p),'exec')
base=R/'ap96-v1-setup-replay-input-diag/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
proc='''  native97_round=$(( ${native97_round:-0} + 1 ))
  if [ -r /tmp/fx3-keyworker96.identity ]; then
   read native97_pid native97_tid < /tmp/fx3-keyworker96.identity
   echo FX3_PROC97_STATUS_BEGIN pid=$native97_pid round=$native97_round
   /bin/busybox cat /proc/uptime /proc/$native97_pid/status /proc/$native97_pid/stat
   echo FX3_PROC97_STATUS_END
   if [ $((native97_round % 10)) -eq 0 ]; then
    echo FX3_PROC97_ALL_THREAD_STAT_BEGIN pid=$native97_pid round=$native97_round
    /bin/busybox cat /proc/uptime /proc/$native97_pid/task/*/stat
    echo FX3_PROC97_ALL_THREAD_STAT_END
   fi
  fi
'''
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n=='simulation/fx3-capid-v1.so':b=(H/'fx3-capid-v48-panel97.so').read_bytes();changed.append(n)
 if n=='init':
  s=b.decode();needle=' (while true; do\n';assert s.count(needle)==1;s=s.replace(needle,needle+proc);b=s.encode();changed.append(n)
 entries.append((n,f,b))
assert set(changed)=={'simulation/fx3-capid-v1.so','init'};D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)};v['host_step_contract']['authority']=authority;v['scope']='AP97 repeat frozen enum2 panel28B each genuine native request. Exact bytes/source-local/owner guards preserved; native first-boot-only context is diagnostic provenance, no stale TID gate. Each transaction reapplies control3/osdRev0 with generation++ and readback before one native1119 reply to its own source. Eight separate native reply leases allow concurrent requests; per-lease issuedgeneration/transaction/tid/destination retires earlier generations correctly. Allocation/send failure rollback retained; other fields/enums unsupported. No original UI/business/threshold modification. AP96 GPE19r4/backend5/OSDv6/replayRAM191924ef/workerV7 diagnostics retained. Additional independent process status and all task/stat snapshots throughout window. Native assert/Assertion/exception monitor/signal6 stop before further input.';v['required_markers']+=['FX3_PANEL_CONFIG_V2_COMMIT','FX3_PROC97_STATUS_BEGIN','FX3_PROC97_ALL_THREAD_STAT_BEGIN'];(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);diff=[n for n in bm if bm[n]!=am[n]];assert set(diff)==set(changed);ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');init=D/'init-reviewed.sh';init.write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(init)],check=True)
(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':diff,'all_other_members_unchanged':True,'DTB_only_initrd_end':True,'native_ASan_UBSan_log':str(H/'check-panel97-transport.log'),'native_ASan_UBSan_log_sha256':sha(H/'check-panel97-transport.log'),'helper_sha256':sha(H/'fx3-capid-v48-panel97.so'),'helper_source_sha256':sha(H/'fx3-capid-v48-panel97.c'),'panel_core_v2_sha256':sha(H/'fx3-panel-config-core-v2.c'),'authority':authority},indent=2)+'\n');print(D/'candidate.json')
