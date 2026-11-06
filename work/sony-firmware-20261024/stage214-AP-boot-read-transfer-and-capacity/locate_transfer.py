"""Locate original ET_REL transfer/field code, without target execution."""
from pathlib import Path
from hashlib import sha256
import json
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;P=H.parent/'stage213-AP-eMMC-boot-asset-search'
src=P/'originals/current-p3-initrd/kmod/emmc.ko'
assert sha256(src.read_bytes()).hexdigest()=='14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d'
rels=json.loads((P/'driver-relocations-detailed.json').read_text());lookup={(r['section'],r['offset']):r for r in rels}
with src.open('rb') as f:
    e=ELFFile(f);cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    ranges=[('.text',0x10ec0,0x11300),('.text',0xf618,0xf790)]
    for name,lo,hi in ranges:
        sec=e.get_section_by_name(name);data=sec.data();rows=[]
        for at in range(lo,hi,4):
            raw=data[at:at+4];ins=list(cs.disasm(raw,at,count=1));line=f'{at:08x}: {raw.hex()} '+(ins[0].mnemonic+' '+ins[0].op_str if ins else '.word')
            if (name,at) in lookup:line+=' ; '+str(lookup[(name,at)])
            rows.append(line)
        (H/(name.strip('.')+'-'+hex(lo)+'-locator.txt')).open('x').write('\n'.join(rows)+'\n')
    fields=[]
    for name in ['.text','.init.text']:
        sec=e.get_section_by_name(name);data=sec.data()
        for at in range(0,len(data),4):
            ins=list(cs.disasm(data[at:at+4],at,count=1))
            if ins and ins[0].mnemonic.startswith(('str','stp')) and '#0xdc]' in ins[0].op_str:
                fields.append(dict(section=name,offset=hex(at),bytes=data[at:at+4].hex(),instruction=ins[0].mnemonic+' '+ins[0].op_str))
    (H/'state-dc-store-locator.json').open('x').write(json.dumps(dict(status='CANDIDATES_ONLY_NOT_COMPLETE_ALIAS_OR_CFG_PROOF',candidates=fields),indent=2)+'\n')
    print(json.dumps(fields))
