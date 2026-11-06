from pathlib import Path
import json,hashlib,subprocess,plistlib,os,shutil
O=Path(__file__).resolve().parent;R=O.parent;S=R/'qemu-display-build/sources/qemu-11.1.2';B=R/'qemu-display-build/build';sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
changes=[]
def change(p,new):
 old=p.read_bytes() if p.exists() else b'';bp=O/(p.name+'.before');assert not bp.exists();bp.write_bytes(old);p.write_bytes(new);changes.append({'path':str(p),'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':sha(p)})
p=S/'hw/arm/virt.c';old=p.read_text();assert sha(p)=='577f142313acf95099aae6d872fc889d891cd12066ce1b0564c659bad682b20b';anchor='    create_gic(vms, sysmem);';assert old.count(anchor)==1
block='''
    /* Experimental AP-only request-register bank; peer ACK is never synthesized. */
    if (g_strcmp0(g_getenv("FX3_VM_SCU_REQUEST"), "1") == 0) {
        DeviceState *dev = qdev_new("fx3-scu-request");
        SysBusDevice *sbd = SYS_BUS_DEVICE(dev);
        sysbus_realize_and_unref(sbd, &error_fatal);
        sysbus_mmio_map(sbd, 0, 0xf1388f50);
    }
'''
change(p,old.replace(anchor,anchor+block).encode());p=S/'hw/misc/meson.build';change(p,p.read_bytes()+b"\nsystem_ss.add(when: 'CONFIG_ARM_VIRT', if_true: files('fx3_scu_request.c'))\n");change(S/'hw/misc/fx3_scu_request.c',(O/'fx3_scu_request.c').read_bytes());(O/'source-change.json').write_text(json.dumps({'changes':changes,'semantics':'Explicit inference from UPM consumer.32bit exact20byte bank,no CP peer ACK,no broad SCU model.'},indent=2)+'\n')
oldbin=B/'qemu-system-aarch64';assert sha(oldbin)=='f20d944821a857aecb17f58492bf76ef02a1f6b019562e107cf3731602aade19';retain=O/'qemu-timer-original-pinned';assert not retain.exists();shutil.copyfile(oldbin,retain);retain.chmod(0o755)
conf=json.loads((R/'qemu-display-build/configure-command.json').read_text());env=os.environ.copy();env.update(conf['env']);args=['/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/build-venv/bin/ninja','-C',str(B),'-j','4','qemu-system-aarch64'];rec={'args':args,'original_sha256':sha(retain)}
try:
 with (O/'build.log').open('w') as log:p=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT)
 rec['exit']=p.returncode
 if not p.returncode:
  dest=R/'qemu-display-build/bin';dest.mkdir(exist_ok=True);h=sha(oldbin);dst=dest/('qemu-scu-'+h[:16]);assert not dst.exists();shutil.copyfile(oldbin,dst);dst.chmod(0o755);rec['binary']={'path':str(dst),'sha256':h}
finally:
 shutil.copyfile(retain,oldbin);oldbin.chmod(0o755);rec['old_timer_binary_restored']=sha(oldbin)==rec['original_sha256'];(O/'build-result.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec,indent=2))
