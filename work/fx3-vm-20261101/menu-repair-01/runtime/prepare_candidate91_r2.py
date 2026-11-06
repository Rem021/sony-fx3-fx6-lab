from pathlib import Path
import json,hashlib,struct,subprocess,plistlib,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap91-r2-delayed-libobj';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
base=R/'ap90-r2-gpe-malloc-parent/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();entries=[];off=0;changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;body=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='simulation/fx3-capid-v1.so':body=(H/'fx3-capid-v46-keys.so').read_bytes();changed.append(name)
 if name=='simulation/fx3-preset-context-v2-screen.so':body=(H/'fx3-preset-context-v3-keys.so').read_bytes();changed.append(name)
 if name=='init':
  s=body.decode();needle=' FX3_OSD_QUEUE_OWNER=native-receiver-v1';assert s.count(needle)==1;s=s.replace(needle,' FX3_SYNTH_KEYS=ap91-script-v1 '+needle.lstrip());body=s.encode();changed.append(name)
 entries.append((name,f,body))
assert sorted(changed)==sorted(['init','simulation/fx3-capid-v1.so','simulation/fx3-preset-context-v2-screen.so']);D.mkdir();out=bytearray()
def add(name,f,body,ino):
 f=f.copy();n=name.encode()+b'\0';f[0]=ino;f[6]=len(body);f[11]=len(n);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+n);out.extend(b'\0'*(-len(out)%4));out.extend(body);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));sha=lambda b:hashlib.sha256(b).hexdigest();v['dtb']={'path':str(dt),'sha256':sha(dt.read_bytes())};v['initrd']={'path':str(cp),'sha256':sha(out)};v['required_markers']+=['FX3_SYNTH_KEY_ARM','FX3_KEY_INPUT_RECV','FX3_SYNTH_KEY_SCRIPT_DONE'];v['scope']='AP91 explicitsyntheticphysicalkeys scriptintheexistingimprocess: originalOSAL20B/source410025/dst807a0020; waitnative2c7open+5s/nativeinputreceiver/keytable, ENTER/MENU/DOWN/DOWN/RIGHT/MENU down100msup/gap4s. OriginalCPkeydetection=0; passivephysical/internal/event/cacheobservations, screenobserverexportonly; GPEv16r2/Backup/CPmodelsunchangedAP90. PerstepquiescedQMPreadbackat+2shostafterupmarker; nativeinputandvisiblemenuresultsseparate.'
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changed_CPIO_members':changed,'all_originals_unchanged':True,'GPE_and_Backup_CP_models_unchanged':True,'DTBonlyinitrdend':True,'capid_sha256':sha((H/'fx3-capid-v46-keys.so').read_bytes()),'screen_observer_sha256':sha((H/'fx3-preset-context-v3-keys.so').read_bytes()),'approval':'msg_06a958bf1094 AP91 keyinjectioncontract','input_is_synthetic':True},indent=2)+'\n')
s=(R/'run_candidate90_r2.py').read_text().replace('from osd_ring85_v3 import RingReader','from osd_ring85_v3 import RingReader\nfrom key_readback91 import capture_step')
s=s.replace("'cpio_audit.py', 'decode_printk_ring.py', 'osd_ring85_v3.py'","'cpio_audit.py', 'decode_printk_ring.py', 'osd_ring85_v3.py', 'key_readback91.py'")
s=s.replace('32 * 1024 * 1024, 32 * 1024 * 1024','64 * 1024 * 1024, 64 * 1024 * 1024')
s=s.replace('            replay_input_verified = False','            replay_input_verified = False\n            step_up_seen={}\n            step_captures=[]')
needle="                serial_now=(run/'serial.log').read_text(errors='replace')\n";extra='''                if re.search(r'unknown\\s+key|invalid\\s+from_type',serial_now,re.I) or 'FX3_SYNTH_KEY_REJECT' in serial_now:
                    early_stop_reason='AP91 native input rejection or synthetic transport failure; stop all subsequent injection'
                    break
                for match in re.finditer(r'FX3_SYNTH_KEY step=(\\d+) key=(0x[0-9a-f]+) status=0 [^\\n]*result=0 ',serial_now):
                    step=int(match[1]);key=int(match[2],0)
                    if step not in step_up_seen:step_up_seen[step]=(time.monotonic(),key)
                for step,(at,key) in sorted(step_up_seen.items()):
                    if not any(x['step']==step for x in step_captures) and time.monotonic()-at>=2:
                        qmp('stop');ring_reader.poll();captured=capture_step(qmp,run,step,key,at);step_captures.append(captured)
                        (run/'ap91-step-readbacks.json').write_text(json.dumps(step_captures,ensure_ascii=False,indent=2)+'\\n')
                        if captured.get('error'):
                            early_stop_reason='AP91 per-step readback failed; preserve evidence'
                            break
                        qmp('cont')
                if early_stop_reason:break
''';assert needle in s;s=s.replace(needle,needle+extra);(R/'run_candidate91_r2.py').write_text(s);print(D/'candidate.json')
