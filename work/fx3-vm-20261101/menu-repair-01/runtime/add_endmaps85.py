from pathlib import Path
import json,hashlib,struct,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap85-osd-software-ring-r2';p=D/'candidate85-r2.json';assert not any(json.loads(q.read_text()).get('candidate')==str(p) for q in (R/'runs').glob('*/receipt.json'));v=json.loads(p.read_text());b=Path(v['initrd']['path']).read_bytes();entries=[];o=0;changed=[];sha=lambda b:hashlib.sha256(b).hexdigest()
while True:
 f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='init':
  s=data.decode();needle='while true; do /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null; /bin/busybox sleep 1; done';repl='''while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done''';assert needle in s;s=s.replace(needle,repl);data=s.encode();(D/'init-reviewed.sh').write_text(s);changed.append(name)
 entries.append((name,f,data))
out=bytearray()
def add(n,f,b,i):
 f=f.copy();z=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(z);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+z);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);Path(v['initrd']['path']).write_bytes(out);v['initrd']['sha256']=sha(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);dt=Path(v['dtb']['path']);t,p0,res,meta=m.parse(dt.read_bytes());c=next(n for k,n in t['items'] if k=='node' and n['name']=='chosen');c['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in c['items']];dt.write_bytes(m.encode(t,res,meta));v['dtb']['sha256']=sha(dt.read_bytes());v['scope']+=' Read-only compact im.elf maps/PID/uptime every existing1s observer loop to substantiate actual end-window liveness.';v['required_markers']+=['FX3_AP_IM_ENDMAPS_'];p.write_text(json.dumps(v,indent=2)+'\n');q=D/'build-receipt.json';d=json.loads(q.read_text());d['pre_first_run_readonly_addition']='compact im.elf maps/PID/uptime in existing1s stats loop, no guest app changed';d['candidate_sha256']=sha(p.read_bytes());q.write_text(json.dumps(d,indent=2)+'\n');print('AP85R2_ENDMAPS_ADDED_BEFORE_FIRST_RUN')
