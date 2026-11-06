#!/usr/bin/env python3
"""Build TRY2 from the validated cold-reload candidate with AP104 readiness ordering."""
from pathlib import Path
import hashlib, json, plistlib, struct, subprocess, sys, importlib.util

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[3] / 'menu-repair-01/runtime'
LIFE = HERE.parent / 'lifecycle-repair'
sys.path.insert(0, str(RUNTIME))
from cpio_audit import parse, audit

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def add(out, name, fields, body, index):
    fields = fields.copy(); filename = name.encode()+b'\0'
    fields[0], fields[6], fields[11] = index, len(body), len(filename)
    out.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode()+filename)
    out.extend(b'\0'*(-len(out)%4)); out.extend(body); out.extend(b'\0'*(-len(out)%4))

def main():
    assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    destination=HERE/'vmopt-20261103-try2-v1'; assert not destination.exists()
    base=LIFE/'vmopt-20261103-reload-v1/candidate.json'; candidate=json.loads(base.read_text())
    old_cpio=Path(candidate['initrd']['path']); assert sha(old_cpio)==candidate['initrd']['sha256']
    observer=RUNTIME/'helpers/fx3-file100-observer-v2'; expected=json.loads((RUNTIME/'helpers/fx3-file100-observer-v2-build.json').read_text())['output_sha256']; assert sha(observer)==expected
    data=old_cpio.read_bytes(); offset=0; entries=[]; observer_mode=None
    late=' /simulation/fx3-file100-observer-v1 &\n echo FX3_FILE100_OBSERVER_PID=$!\n'
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
        fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        name=data[offset+110:offset+110+fields[11]-1].decode(); offset=(offset+110+fields[11]+3)&~3
        body=data[offset:offset+fields[6]]; offset=(offset+fields[6]+3)&~3
        if name=='TRAILER!!!':break
        if name=='simulation/fx3-file100-observer-v1':observer_mode=fields.copy()
        if name=='init':
            script=body.decode(); assert script.count(late)==1 and script.count(' echo FX3_BACKUP_CP_INSMOD_BEGIN\n')==1
            script=script.replace(late,'').replace(' echo FX3_BACKUP_CP_INSMOD_BEGIN\n',barrier+' echo FX3_BACKUP_CP_INSMOD_BEGIN\n')
            body=script.encode()
        entries.append((name,fields,body))
    assert observer_mode is not None and not any(n=='simulation/fx3-file100-observer-v2' for n,_,_ in entries)
    entries.append(('simulation/fx3-file100-observer-v2',observer_mode,observer.read_bytes()))
    destination.mkdir(); out=bytearray()
    for i,(n,f,b) in enumerate(entries,1):add(out,n,f,b,i)
    add(out,'TRAILER!!!',[0]*13,b'',len(entries)+1)
    cp=destination/'guest.cpio';cp.write_bytes(out)
    spec=importlib.util.spec_from_file_location('fdt',RUNTIME.parents[1]/'fx3-audit/prepare_virt_dtb.py');fdt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fdt)
    tree,_,reserved,meta=fdt.parse(Path(candidate['dtb']['path']).read_bytes())
    chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen')
    chosen['items']=[(k,(v[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and v[0]=='linux,initrd-end' else (k,v) for k,v in chosen['items']]
    dtb=destination/'guest.dtb';dtb.write_bytes(fdt.encode(tree,reserved,meta))
    candidate['dtb']={'path':str(dtb),'sha256':sha(dtb)};candidate['initrd']={'path':str(cp),'sha256':sha(cp)}
    candidate['try2_contract']={'base':str(base),'base_sha256':sha(base),'readiness_source':str(RUNTIME/'prepare_candidate104_v2.py'),'readiness_source_sha256':sha(RUNTIME/'prepare_candidate104_v2.py'),'observer_v2_sha256':sha(observer),'ready_before_CP_binding':True,'matching_live_PID':True,'original_guest_receive_timeout_ms':5000,'original_seed_untouched':True,'changed_existing_CPIO_member':['init'],'added_CPIO_member':['simulation/fx3-file100-observer-v2'],'DTB_only_initrd_end':True}
    candidate['required_markers']=list(dict.fromkeys(candidate['required_markers']+['FX3_FILE103_READY_CONFIRMED']))
    manifest=destination/'candidate.json';manifest.write_text(json.dumps(candidate,indent=2)+'\n')
    _,before=parse(old_cpio);_,after=parse(cp)
    assert set(after)-set(before)=={'simulation/fx3-file100-observer-v2'} and not set(before)-set(after)
    assert [n for n in before if before[n]!=after[n]]==['init']
    assert after['simulation/fx3-sync100-shutdown.sh']==before['simulation/fx3-sync100-shutdown.sh']
    assert after['init'].index(b'FX3_FILE103_READY_CONFIRMED')<after['init'].index(b'FX3_BACKUP_CP_INSMOD_BEGIN')
    (destination/'init-reviewed.sh').write_bytes(after['init']);subprocess.run(['/bin/sh','-n',str(destination/'init-reviewed.sh')],check=True)
    result=audit(cp,Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'))
    assert result['safe_to_unpack'];(destination/'cpio-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    receipt={'candidate':str(manifest),'candidate_sha256':sha(manifest),'initrd_sha256':sha(cp),'dtb_sha256':sha(dtb),'base':str(base),'base_sha256':sha(base),'changed_existing_members':['init'],'added_members':['simulation/fx3-file100-observer-v2'],'all_other_existing_members_unchanged':True,'DTB_only_initrd_end':True,'original_shutdown_script_unchanged':True,'observer_v2_sha256':sha(observer),'source_diff_sha256':sha(RUNTIME/'prepare_candidate104_v2.py')}
    (destination/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
