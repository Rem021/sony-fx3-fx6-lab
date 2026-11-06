#!/usr/bin/env python3
"""Read-only, hash-pinned FX6 standalone vs FX3-port boot readiness inventory."""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path

from elf64 import ELF64
from fdt import parse_fdt

HERE=Path(__file__).resolve().parent
DONOR=HERE.parent
ROOT=HERE.parents[5]
FX3PROJ=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files'
VMBASE=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability'
VM=VMBASE/'vmopt-20261103-try2-long-media-gap-v2'
RUN=VMBASE/'runs/try2gapinternal-47e2924a'
FIXED={
    'candidate':(VM/'candidate.json','67eb81401a457bf7ffecb21f7367e7819b5bf3e13aef39dd8a4c9001ce408417'),
    'cpio_audit':(VM/'cpio-audit.json','cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847'),
    'run_command':(RUN/'command.json',None),
    'run_receipt':(RUN/'receipt.json','50d317dee9de7eff4b7e238a384565357c491e5a5de078508888d0c676e2184d'),
    'run_serial':(RUN/'serial.log','8157737391d2d8e3acf46790312826b0084539bda82e2bbe228bc1f1d6f1d16b'),
    'qemu_virt_maintainer_doc':(ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/sources/qemu-11.1.2/docs/system/arm/virt.rst','9fbcc9fc3040ef695e3058cd4bab05e10f6282ab7ba0846a93ee9f524933e3e1'),
    'fx6_kernel':(DONOR/'fat-files/nflasha3/vmlinux.bin','bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'),
    'fx3_kernel':(ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin','da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'),
    'fx6_updater_boot_dtb':(DONOR/'fat-files/nflasha1/boot/cxd90057.dtb','87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca'),
    'fx6_application_setting_dtb':(DONOR/'tree/0800_appli/setting/cxd90057.dtb','c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280'),
    'guest_dtb':(VM/'guest.dtb','b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7'),
    'fx6_av':(DONOR/'fat-files/nflasha3/av-cam.bin','56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'),
    'fx3_av':(ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin','0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'),
    'fx6_cp':(DONOR/'fat-files/nflasha8/cpapp-b.bin','60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668'),
    'fx6_system_partition':(DONOR/'tree/0700_part_image/dev/nflasha3','a78c28d835b0cc9c3105332d82f7f404e319d3bf289146935482fd0c887c9b02'),
    'fx6_cp_partition':(DONOR/'tree/0700_part_image/dev/nflasha8','7fbf12865eef11ea4db2d822af88deb0b95e565d10dbf80eee31f23689858315'),
    'fx6_usr_partition':(DONOR/'tree/0700_part_image/dev/nflasha15','c62b1775a2fe36669b644a55cac7eab9ce2636e6fb8469cbf791d00b8ed6fc6a'),
    'fx6_im':(DONOR/'nflasha15-files/bin/im.elf','87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec'),
    'fx3_im':(ROOT/'work/sony-firmware-20261024/stage218-fixed-shell-process-filter/originals/im.elf','5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91'),
    'fx6_init':(DONOR/'nested-files/nflasha3-initrd/sbin/init',None),
    'fx6_init2':(DONOR/'nested-files/nflasha3-initrd/sbin/init2',None),
    'fx6_fstab':(DONOR/'nested-files/nflasha3-initrd/sbin/initrc/fstab',None),
    'fx6_setup_nflash':(DONOR/'nested-files/nflasha3-initrd/sbin/initrc/setup_nflash',None),
    'fx6_drv1':(DONOR/'nested-files/nflasha3-initrd/sbin/initrc/insmod_drv1','22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591'),
    'fx6_drv2':(DONOR/'nested-files/nflasha3-initrd/sbin/initrc/insmod_drv2','19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e'),
    'fx3_drv1':(FX3PROJ/'sbin/initrc/insmod_drv1','22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591'),
    'fx3_drv2':(FX3PROJ/'sbin/initrc/insmod_drv2','19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e'),
}
SYMBOLS={
    'dma330_mem_transfer_async':'kmod/dma330.ko',
    'pciatu_map':'usr/kmod/pcieatu.ko',
    'pciatu_unmap':'usr/kmod/pcieatu.ko',
    'interchip_transfer_async':'usr/kmod/icdt.ko',
}
MODULES=['usr/kmod/liro.ko','kmod/dma330.ko','usr/kmod/pcieatu.ko','usr/kmod/icdt.ko']


def sha_file(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as fp:
        for chunk in iter(lambda:fp.read(4*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def source(path, expected=None):
    actual=sha_file(path)
    if expected and actual!=expected:raise ValueError(f'SHA mismatch {path}: {actual}')
    return {'path':str(path),'sha256':actual,'bytes':path.stat().st_size}


def module_info(path:Path, expected:str):
    meta=source(path,expected)
    e=ELF64(path)
    if e.etype!=1 or e.machine!=183:raise ValueError('module not AArch64 ET_REL')
    info=e.section_bytes('.modinfo')
    depends=next((x.decode().removeprefix('depends=') for x in info.split(b'\0') if x.startswith(b'depends=')),None)
    syms={s['name']:s for s in e.symbols() if s['name'] in SYMBOLS}
    targets={}
    for name,s in syms.items():
        defined=s['shndx']!=0
        section=e.sections[s['shndx']] if defined and s['shndx']<len(e.sections) else None
        if section and s['value']+s['size']>section['size']:
            raise ValueError('symbol section bounds')
        code=(e.data[section['offset']+s['value']:section['offset']+s['value']+s['size']] if section and section['type']!=8 and s['size'] else b'')
        targets[name]={'defined':defined,'section_index':s['shndx'],'section_name':section['name'] if section else None,'section_offset':s['value'],'size':s['size'],'file_offset':section['offset']+s['value'] if section else None,'body_sha256':hashlib.sha256(code).hexdigest() if code else None,'symtab_file_offset':s['sym_file_offset'],'export_string_present':e.exported_name(name)}
    meta.update({'elf_type':'ET_REL','machine':'AArch64','modinfo_depends':depends,'target_symbols':targets})
    return meta


def image_header(path):
    b=path.read_bytes()[:64]
    if struct.unpack_from('<I',b,0x38)[0]!=0x644d5241:raise ValueError('not arm64 Image')
    return {'text_offset':struct.unpack_from('<Q',b,8)[0],'image_size_header':struct.unpack_from('<Q',b,16)[0],'flags':struct.unpack_from('<Q',b,24)[0]}


def main():
    fixed={name:source(path,pin) for name,(path,pin) in FIXED.items()}
    candidate=json.loads(FIXED['candidate'][0].read_text())
    audit=json.loads(FIXED['cpio_audit'][0].read_text())
    command=json.loads(FIXED['run_command'][0].read_text())
    serial=FIXED['run_serial'][0].read_bytes()
    members={m['path']:m for m in audit['members']}
    if audit['member_count']!=len(members) or audit['baseline_ELF_changed_or_missing']:
        raise ValueError('CPIO member count or baseline mismatch')
    if audit['candidate_cpio_sha256']!=candidate['initrd']['sha256']:
        raise ValueError('CPIO audit/candidate mismatch')
    fixed['guest_cpio']=source(Path(candidate['initrd']['path']),candidate['initrd']['sha256'])
    if command['candidate_sha256']!=fixed['candidate']['sha256'] or command['args'][command['args'].index('-kernel')+1]!=str(FIXED['fx3_kernel'][0]):
        raise ValueError('run/candidate/kernel mismatch')
    init=audit['init_text']
    member_checks={name:({'present':name in members,'bytes':members[name]['bytes'],'sha256':members[name]['sha256']} if name in members else {'present':False}) for name in ['usr/kmod/liro.ko','usr/kmod/backup.ko','kmod/dma330.ko','usr/kmod/pciedma.ko','usr/kmod/pci_ep_cp.ko','usr/kmod/pcieatu.ko','usr/kmod/icdt.ko','usr/bin/im.elf','usr/bin/bootin.elf','setting/Backup.bin','system/av-cam.bin','usr/sabin/sa_sabin_cp_cam_post.bin']}
    variants={}
    for model in ('fx3','fx6'):
        sourcepaths={
            'usr/kmod/liro.ko':FX3PROJ/'usr/kmod/liro.ko' if model=='fx3' else DONOR/'nflasha15-files/kmod/liro.ko',
            'kmod/dma330.ko':FX3PROJ/'kmod/dma330.ko' if model=='fx3' else DONOR/'nested-files/nflasha3-initrd/kmod/dma330.ko',
            'usr/kmod/pcieatu.ko':FX3PROJ/'usr/kmod/pcieatu.ko' if model=='fx3' else DONOR/'nflasha15-files/kmod/pcieatu.ko',
            'usr/kmod/icdt.ko':FX3PROJ/'usr/kmod/icdt.ko' if model=='fx3' else DONOR/'nflasha15-files/kmod/icdt.ko',
        }
        variants[model]={}
        for name,path in sourcepaths.items():
            expected=members[name]['sha256'] if model=='fx3' and name in members else None
            variants[model][name]=module_info(path,expected)
        liro=variants[model]['usr/kmod/liro.ko']['target_symbols']
        for symbol,provider in SYMBOLS.items():
            if liro[symbol]['defined'] or not variants[model][provider]['target_symbols'][symbol]['defined'] or not variants[model][provider]['target_symbols'][symbol]['export_string_present']:
                raise ValueError(f'provider edge not verified: {model}:{symbol}')
    logs={}
    for text in [b'dma330_mem_transfer_async',b'pciatu_unmap',b'pciatu_map',b'interchip_transfer_async',b'FX3_BACKUP_INSMOD_RC=0',b'FX3_AP_NATURAL_BOOTIN_BEGIN',b'FX3_AP_IM_PROCESS=',b'av-cam.bin',b'ORIL']:
        off=serial.find(text)
        logs[text.decode()]={'present':off>=0,'byte_offset':off,'context':serial[max(0,off-60):off+len(text)+35].decode('utf-8','replace') if off>=0 else None}
    assert all(logs[x]['present'] for x in ['dma330_mem_transfer_async','pciatu_unmap','pciatu_map','interchip_transfer_async'])
    assert fixed['fx6_drv1']['sha256']==fixed['fx3_drv1']['sha256'] and fixed['fx6_drv2']['sha256']==fixed['fx3_drv2']['sha256']
    assert not member_checks['system/av-cam.bin']['present'] and member_checks['usr/kmod/liro.ko']['present']
    fstab=[]
    for line in FIXED['fx6_fstab'][0].read_text().splitlines():
        if not line or line.startswith('#'):continue
        row=line.split()
        if len(row)>=3:fstab.append({'source':row[0],'target':row[1],'type':row[2]})
    native_order=[]
    for script in ('fx6_drv1','fx6_drv2'):
        for line_no,line in enumerate(FIXED[script][0].read_text().splitlines(),1):
            parts=line.split()
            if len(parts)>=2 and parts[0]=='insmod':
                member=parts[1].lstrip('/')
                native_order.append({'source':script,'line':line_no,'module':member,'present_in_guest_cpio':member in members})
    return {'status':'PASS_OFFLINE_PRECHECK_ONLY','fixed_sources':fixed,'vm':{'candidate_initrd_sha256':candidate['initrd']['sha256'],'cpio_member_count':audit['member_count'],'baseline_original_ELF_changed_or_missing':audit['baseline_ELF_changed_or_missing'],'member_checks':member_checks,'init_explicit_refs':{q:[i for i,line in enumerate(init.splitlines(),1) if q in line] for q in ['liro.ko','av-cam.bin','dma330.ko','pciedma.ko','pcieatu.ko','icdt.ko','backup.ko','bootin.elf']},'qemu_machine_args':command['args'][command['args'].index('-machine')+1],'qemu_cpu_args':command['args'][command['args'].index('-cpu')+1],'qemu_smp':command['smp'],'qemu_memory_mib':candidate['memory_mib'],'observed_serial_fragments':logs},'modules':variants,'native_insmod_scripts_byte_identical':True,'native_insmod_order':native_order,'fx6_fstab_mounts':fstab,'fx6_im_loader_argument_file_offset':FIXED['fx6_im'][0].read_bytes().find(b'fn=/system/av-cam.bin load=1 debug=1'),'fx3_im_loader_argument_file_offset':FIXED['fx3_im'][0].read_bytes().find(b'fn=/system/av-cam.bin load=1 debug=1'),'fx6_updater_boot_dtb':parse_fdt(FIXED['fx6_updater_boot_dtb'][0].read_bytes()),'fx6_application_setting_dtb':parse_fdt(FIXED['fx6_application_setting_dtb'][0].read_bytes()),'guest_dtb':parse_fdt(FIXED['guest_dtb'][0].read_bytes()),'linux_image_headers':{'fx6':image_header(FIXED['fx6_kernel'][0]),'fx3':image_header(FIXED['fx3_kernel'][0])},'runtime_ORIL_AV_loaded_proven':False,'runtime_FX6_kernel_tested':False,'new_VM_or_device_operations':0}


if __name__=='__main__':
    print(json.dumps(main(),indent=2,ensure_ascii=False))
