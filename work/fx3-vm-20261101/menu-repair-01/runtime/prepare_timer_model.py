from pathlib import Path
import hashlib,json,plistlib,subprocess
R=Path(__file__).resolve().parent; S=R/'qemu-display-build/sources/qemu-11.1.2'; O=R/'timer-model'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
p=R.parent/'success-cases/display-reuse/supplemental-source/source/qemu-sony-native.patch';lines=p.read_text().splitlines();start=lines.index('+++ b/hw/timer/sony_hwtimer.c')+2;end=next(i for i in range(start,len(lines)) if lines[i].startswith('--- '));source='\n'.join(l[1:] for l in lines[start:end] if l.startswith('+'))+'\n';assert len(source.splitlines())==157
changes=[]
def change(path,new):
 old=path.read_bytes() if path.exists() else b''
 dst=O/(path.name+'.before');assert not dst.exists();dst.write_bytes(old);path.write_bytes(new);changes.append({'path':str(path),'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(new).hexdigest()})
path=S/'hw/arm/virt.c';old=path.read_text();assert hashlib.sha256(path.read_bytes()).hexdigest()=='c87dcfffc0934812284dba05fd525ab0f400b0021b3b90896371f455f6f3289d'
a='    create_gic(vms, sysmem);';assert old.count(a)==1
loop='''
    /* Explicit timer-only model, adapted from pinned public Sony QEMU case.
     * No catch-all peripheral reads, crypto stubs, or CP execution implied. */
    if (g_strcmp0(g_getenv("FX3_VM_SONY_TIMER"), "1") == 0) {
        for (unsigned i = 0; i < 4; i++) {
            DeviceState *dev = qdev_new("sony-hwtimer");
            SysBusDevice *sbd = SYS_BUS_DEVICE(dev);
            sysbus_realize_and_unref(sbd, &error_fatal);
            memory_region_add_subregion_overlap(sysmem, 0xf1042000 + i * 0x1000,
                                                 sysbus_mmio_get_region(sbd, 0), 1);
            sysbus_connect_irq(sbd, 0, qdev_get_gpio_in(vms->gic, 200 + i));
        }
    }
'''
change(path,old.replace(a,a+loop).encode());path=S/'hw/timer/meson.build';change(path,path.read_bytes()+b"\nsystem_ss.add(when: 'CONFIG_ARM_VIRT', if_true: files('sony_hwtimer.c'))\n");change(S/'hw/timer/sony_hwtimer.c',source.encode());(O/'model-receipt.json').write_text(json.dumps({'upstream_patch_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'selected_file':'hw/timer/sony_hwtimer.c','changes':changes,'irq_basis':'Sony FX3 7.00 GPL irqs.h non-FPGA IRQ_TIMER_BASE232 -> GIC SPI index200; exact7.02 runtime initialization/interrupt acceptance not yet verified','guest_or_UI_tested':False,'excluded_upstream_models':['catch-all bus','crypto','USB','native key bridge','warmboot aliases']},indent=2)+'\n');print(changes)
