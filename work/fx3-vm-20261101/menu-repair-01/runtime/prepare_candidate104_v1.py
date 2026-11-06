from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
from cpio_audit import parse,audit
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap104-v1-completion-trace';assert not D.exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=R/'ap103-r2-soft-ldec/candidate.json';assert sha(base)=='5d2155cb3e208ba182caa1c57e8c03f05b140e575ec9ea7c9b8e2743993aefe7';v=json.loads(base.read_text());replacement='fx3-gpe-observe-v25-complete104.so';assert sha(H/replacement)==json.loads((H/'fx3-gpe-observe-v25-complete104-build.json').read_text())['output_sha256']
data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16)for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n=='simulation/fx3-gpe-observe-v7.so':b=(H/replacement).read_bytes();changed.append(n)
 if n=='init':
  s=b.decode();needle='echo FX3_PROC_MODULES_BEGIN\n';assert s.count(needle)==1;s=s.replace(needle,'echo FX3_UIPC104_TEXT_BASE=$(/bin/busybox cat /sys/module/osal_uipc/sections/.text)\necho FX3_UIPC104_BSS_BASE=$(/bin/busybox cat /sys/module/osal_uipc/sections/.bss)\n'+needle);b=s.encode();changed.append(n)
 entries.append((n,f,b))
assert set(changed)=={'init','simulation/fx3-gpe-observe-v7.so'};D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();s=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(s);out.extend(b'070701'+''.join(f'{x:08x}'for x in f).encode()+s);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b)in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,_,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items']if k=='node'and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out))))if k=='prop'and q[0]=='linux,initrd-end'else(k,q)for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)}
v['scope']='AP104 passive observation only per msg_b94a0dacc3e4: same AP103-r2 original inputs and device/Backup/pixel models. Added original dynamic owner store/release, native SyncCallback/SendDrawComp probes and exact-once adapter callback/send/dynamic_id logs. Completion semantics and ordering unchanged. Stop at first native unfetched; preserve source and API cleanup acknowledgment.'
v['ap104_contract']={'authority':'msg_b94a0dacc3e4','baseline':str(base),'baseline_SHA256':sha(base),'original_proof':{'path':str(R/'ap104-observer-original-proof-v1.json'),'sha256':sha(R/'ap104-observer-original-proof-v1.json')},'completion_semantics_unchanged':True,'device_models_unchanged':True,'native_owner_writes_only_original_instructions':True,'no_stat_msgq_or_new_fetch':True,'new_GPE_observer':replacement,'API_cleanup':'restore_api103_v1 acknowledged original16, bounded20s','not_based_on_test_delay_candidate':True}
v['required_markers']+=['FX3_UIPC104_TEXT_BASE=','FX3_GPE104_LIB_BIND']
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert set(bm)==set(am);diff=[n for n in bm if bm[n]!=am[n]];assert set(diff)==set(changed);assert am['simulation/fx3-sync100-shutdown.sh']==bm['simulation/fx3-sync100-shutdown.sh'];ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'init-reviewed.sh').write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(D/'init-reviewed.sh')],check=True);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_SHA256':sha(base),'changed_member_bodies':diff,'all_other_existing_members_unchanged':True,'DTB_only_initrd_end':True,'original_shutdown_script_unchanged':True,'no_device_or_Backup_or_pixel_math_changes':True,'added_passive_completion_logging_only':True},indent=2)+'\n');print(D/'candidate.json')
