from pathlib import Path
import json,hashlib,struct,subprocess,plistlib,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap90-gpe-v16-resource-interval';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
base=R/'ap89-r2-backup-helper-replay/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();entries=[];off=0;changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;body=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='simulation/fx3-gpe-observe-v7.so':body=(H/'fx3-gpe-observe-v16-resources.so').read_bytes();changed.append(name)
 entries.append((name,f,body))
assert changed==['simulation/fx3-gpe-observe-v7.so'];D.mkdir();out=bytearray()
def add(name,f,body,ino):
 f=f.copy();n=name.encode()+b'\0';f[0]=ino;f[6]=len(body);f[11]=len(n);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+n);out.extend(b'\0'*(-len(out)%4));out.extend(body);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));sha=lambda b:hashlib.sha256(b).hexdigest();v['dtb']={'path':str(dt),'sha256':sha(dt.read_bytes())};v['initrd']={'path':str(cp),'sha256':sha(out)};v['required_markers']+=['FX3_GPE_RESOURCE_BOUND','FX3_GPE_RESOURCE_REGISTER','FX3_GPE_SCOPE'];v['scope']='AP90 sole change fromAP89r2: GPEv16 retainsv15earlybind/nativeFIFO/completion/snapshotguard, observesoriginal libObjallocation/release throughprefixguardedabsoluteentrytrampolines andregisterscurrentnativeallocationintervals; sourceRO/destinationtrueextentid81RW, spanpreflight. Restrictedmodelapproved: nochildbitmaplease/compaction/queuedABAclaim; nativeallocationchangesmarked. Explicitapproximatefmt0sourceover, fmt2A8foregroundcandidate/op14 strictsubset andneareststretch. BackupRAMreplay/originalCPmodels/seed/module/initunchanged; nohardwarepixeloracle/menuinputclaim.'
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changed_CPIO_members':changed,'originals_unchanged':True,'init_unchanged':True,'protocol_models_unchanged':True,'dtb_only_initrd_end_changed':True,'gpe_v16_sha256':sha((H/'fx3-gpe-observe-v16-resources.so').read_bytes()),'approval':'Lead ask reply msg_cannot_assume_id; parentwholefunctionreturn/status0state10 plusrestrictedintervalmodel approvedinCLIask2026-11-02','host_checks':str(R/'ap90-host-check.json')},indent=2)+'\n')
s=(R/'run_candidate89_r2.py').read_text();s=s.replace("'FX3_PRESET_CONTEXT_BIND_REJECT',","'FX3_GPE_RESOURCE_BIND_REJECT','FX3_PRESET_CONTEXT_BIND_REJECT',")
needle="                if any(x in serial_now for x in ['Unhandled fault:'"
s=s.replace(needle,"                if re.search(r'FX3_GPE_CMD [^\\n]* result=[1-9][0-9]* ',serial_now):\n                    early_stop_reason='AP90 first new GPE rejection; quiesce and review without further changes'\n                    break\n"+needle)
(R/'run_candidate90.py').write_text(s);print(D/'candidate.json')
