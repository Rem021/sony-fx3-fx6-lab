#!/usr/bin/env python3
"""Read original ELF files and emit static evidence; never execute Sony code."""
from pathlib import Path
from hashlib import sha256
import io, json, plistlib, subprocess
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'work/fx3-color-port-20261027/input-20261028/engine-rootfs/2.05'
BODY = ROOT / 'work/fx3-color-port-20261027/package-20261028/updaterfs'

# Half-open original virtual-address intervals. Slices retain objdump's raw opcodes.
RANGES = {
    'libsdfileinputupdaterapi.so': (OLD/'usr/lib/libsdfileinputupdaterapi.so', [
        ('manager-init',0x7d10,0x7f8c),('manager-verify',0x81e0,0x8314),
        ('manager-burn',0x8374,0x8750),('sd-signature-before-stream',0x95b8,0x9820),
        ('sd-bodyloader-current',0x9c90,0x9d78),('sd-condition-comparisons',0x9fd4,0xa02c),
        ('sd-get-information',0xa054,0xa0e8),('sd-search-fdat',0xa0e8,0xa360),
        ('sd-condition-order',0xa360,0xa3fc),('sd-update-information',0xa3fc,0xa634)]),
    'libupdatercommon.so': (OLD/'usr/lib/libupdatercommon.so', [
        ('metadata-read',0x72a4,0x7494),('metadata-write',0x7494,0x7618),
        ('metadata-paths',0x7618,0x7734),('flag-existence',0x908c,0x90b4),
        ('complete-flag-path',0x9278,0x92b0)]),
    'libupdatercorecommon.so': (OLD/'usr/lib/libupdatercorecommon.so', [
        ('current-information',0xc060,0xc338),('switch-verskip',0xc59c,0xc740),
        ('current-validity',0xc9d4,0xcb50),('current-fields',0xcd30,0xce88)]),
    'libupdaterapi.so': (OLD/'usr/lib/libupdaterapi.so', [
        ('current-valid-api',0xfc68,0xff50),('verskip-factory',0x10af8,0x10bc0),
        ('cached-validity',0x111ac,0x111b4),('cache-current-information',0x11664,0x116f0)]),
    'sauu': (OLD/'usr/bin/sauu', [
        ('sauu-factory-selection',0x405288,0x4053d8),('sauu-options',0x405824,0x4058a8),
        ('sauu-version-admission',0x405b54,0x405c64),
        ('sauu-model-region',0x405c64,0x405cd4),('sauu-guard-order',0x405cd4,0x405ebc)]),
    'sdfileinput.elf': (OLD/'usr/bin/sdfileinput.elf', [('sd-main',0x400970,0x400adc)]),
    'libupdaterbody-7.02.so': (BODY/'bodylib/libupdaterbody.so', [
        ('body-execute',0x122a4,0x12968),('body-version-write',0x19ad4,0x19b50),
        ('body-start-flags',0x19bdc,0x19f88),('body-complete-flags',0x1a2f0,0x1ab18)]),
}

def read_va(elf, data, address, size):
    for seg in elf.iter_segments():
        if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=address and address+size<=seg['p_vaddr']+seg['p_filesz']:
            offset=seg['p_offset']+address-seg['p_vaddr']
            return data[offset:offset+size]
    raise ValueError(hex(address))

def main():
    disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert disk['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    fragments=OUT/'fragments'; fragments.mkdir(exist_ok=True)
    pins=[]; ranges=[]; tables=[]
    for label,(source,entries) in RANGES.items():
        data=source.read_bytes(); elf=ELFFile(io.BytesIO(data))
        pins.append(dict(path=str(source.relative_to(ROOT)),bytes=len(data),sha256=sha256(data).hexdigest()))
        asm=OUT/'disassembly'/(label+'.txt')
        lines=asm.read_text().splitlines()
        for name,start,end in entries:
            raw=read_va(elf,data,start,end-start); selected=[]
            for line in lines:
                try: address=int(line.split(':')[0].strip(),16)
                except ValueError: continue
                if start<=address<end: selected.append(line)
            assert len(selected)==(end-start)//4,(name,len(selected))
            output=fragments/(label+'-'+name+'.txt')
            output.write_text(f'# {source.relative_to(ROOT)}\n# SHA256 {sha256(data).hexdigest()}\n# VA [{start:#x}, {end:#x}) raw slice SHA256 {sha256(raw).hexdigest()}\n'+'\n'.join(selected)+'\n')
            ranges.append(dict(source=str(source.relative_to(ROOT)),name=name,va=hex(start),end=hex(end),bytes=len(raw),sha256=sha256(raw).hexdigest(),output=str(output.relative_to(OUT))))
        symtab=elf.get_section_by_name('.dynsym')
        symbols=list(symtab.iter_symbols())
        demangled=subprocess.check_output(['c++filt'],input=('\n'.join(s.name for s in symbols)).encode()).decode().splitlines()
        names={s.name:n for s,n in zip(symbols,demangled)}
        relocs={r['r_offset']:r for sec in elf.iter_sections() if sec['sh_type']=='SHT_RELA' for r in sec.iter_relocations()}
        desired=['SDFileInputUpdaterManager','SDUUDConditionChecker','SDDecryptorModule','UpdaterManager','CurrentFirmware','Firmware','FlagFirmwareInformationHandler']
        for sym,pretty in zip(symbols,demangled):
            if not any(pretty=='vtable for Updater::'+n for n in desired): continue
            start=sym['st_value']+16; slots=[]
            for a in range(start,sym['st_value']+sym['st_size'],8):
                r=relocs.get(a)
                if not r: continue
                target=symtab.get_symbol(r['r_info_sym']).name if r['r_info_sym'] else hex(r['r_addend'])
                slots.append(dict(slot=hex(a-start),relocation_at=hex(a),target=names.get(target,target),relocation_type=r['r_info_type']))
            tables.append(dict(source=label,vtable=pretty,vptr_base=hex(start),slots=slots))
    for source in [OLD/'usr/bin/execute_ufp.sh',OLD/'usr/bin/UdtrMain.sh',OLD/'usr/bin/common.src',OLD/'usr/bin/up.sh',
                   BODY/'usr/lib/libupdatercommon.so',BODY/'bin/us_crc32sum_appli.sh',BODY/'bin/endupdate.sh',BODY/'bin/startupdate.sh']:
        data=source.read_bytes();pins.append(dict(path=str(source.relative_to(ROOT)),bytes=len(data),sha256=sha256(data).hexdigest()))
    comparisons=[]
    for suffix in ['usr/lib/libsdfileinputupdaterapi.so','usr/lib/libupdatercommon.so','usr/lib/libupdatercorecommon.so','usr/lib/libupdaterapi.so','usr/bin/sdfileinput.elf','usr/bin/sauu']:
        a=OLD/suffix;b=OLD.parent/'2.04'/suffix
        ab=a.read_bytes();bb=b.read_bytes()
        comparisons.append(dict(path_a=str(a.relative_to(ROOT)),path_b=str(b.relative_to(ROOT)),sha256_a=sha256(ab).hexdigest(),sha256_b=sha256(bb).hexdigest(),byte_equal=ab==bb))
    with (ROOT/'work/sony-firmware-20261024/fx3-7.02-decrypted.fdat').open('rb') as f: header=f.read(512)
    header_note=dict(source='work/sony-firmware-20261024/fx3-7.02-decrypted.fdat',span='[0,512)',sha256=sha256(header).hexdigest(),udtr_header_version_offset='0x20',raw_le_version_bytes=header[0x20:0x22].hex(),major=header[0x21],minor=header[0x20],model=hex(int.from_bytes(header[0x24:0x28],'little')),region=hex(int.from_bytes(header[0x28:0x2c],'little')),note='Decoded FDAT reference only; not fed to old checker, not current camera metadata.')
    # Original body jump table: action values 3..7; signed byte x4 relative 0x19d20.
    body_data=RANGES['libupdaterbody-7.02.so'][0].read_bytes();be=ELFFile(io.BytesIO(body_data))
    jump=read_va(be,body_data,0x1c25c,5)
    body_start_actions=[dict(action=3+i,raw_jump_byte=hex(b),destination=hex(0x19d20+int.from_bytes(bytes([b]),'little',signed=True)*4)) for i,b in enumerate(jump)]
    result=dict(scope='Static reads and host objdump only; no Sony ELF/script, guest/emulator, updater, device or write-to-camera execution.',volume_uuid=disk['VolumeUUID'],sources=pins,fragments=ranges,vtables=tables,old_204_205_comparisons=comparisons,decoded_current_header=header_note,body_start_actions=body_start_actions)
    (OUT/'static-admission-evidence.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print('STATIC_EVIDENCE',len(pins),'sources',len(ranges),'ranges',len(tables),'vtables')
    print('2.04/2.05 exact equality:',[(r['path_a'].split('/')[-1],r['byte_equal']) for r in comparisons])
    print('body start action dispatch:',body_start_actions)
    print('7.02 decoded header:',header_note)

if __name__=='__main__': main()
