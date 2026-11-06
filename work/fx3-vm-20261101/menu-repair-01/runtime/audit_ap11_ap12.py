"""Reconstruct the two observed fault callers from same-model pinned ELF bytes."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import plistlib
import subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
ROOT = Path(__file__).resolve().parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
manifest = ROOT.parent/'original-uipc/ap-projection/full-v4/projection-manifest-full-v4.json'
x = json.loads(manifest.read_text())
cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
def image(guest):
    row = next(r for r in x['members'] if r['guest_path']==guest)
    b = Path(row['local_file']).read_bytes()
    assert hashlib.sha256(b).hexdigest()==row['sha256']
    e = ELFFile(BytesIO(b))
    def read(va, n):
        for seg in e.iter_segments():
            if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=va and va+n<=seg['p_vaddr']+seg['p_filesz']:
                off=seg['p_offset']+va-seg['p_vaddr'];return b[off:off+n]
        raise ValueError(hex(va))
    rela=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt');sym=e.get_section(rela['sh_link'])
    mp={plt['sh_addr']+32+i*16:sym.get_symbol(r['r_info_sym']).name for i,r in enumerate(rela.iter_relocations())}
    def dis(va,n):
        out=[]
        for i in cs.disasm(read(va,n),va):
            r={'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str}
            if i.mnemonic=='bl' and i.op_str.startswith('#'):r['plt_symbol']=mp.get(int(i.op_str[1:],16))
            out.append(r)
        return out
    return row,read,dis
obj,read,dis=image('/usr/lib/libObj.so')
result={'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(), 'grm':{
 'source_sha256':obj['sha256'],'actual_run':'runs/ap11filtered-f7feec76',
 'libObj_base':'0x7f6a70c000','runtime_return':'0x7f6a80e2e0','elf_return':hex(0x7f6a80e2e0-0x7f6a70c000),
 'check':dis(0x102264,164),'init_caller':dis(0xfeefc,44),
 'proc_path':read(0x1e2234,14).split(b'\0')[0].decode(),'required_prefix':read(0x1e2242,8).split(b'\0')[0].decode(),
 'interpretation':'fopen /proc/modules succeeds; no prefix grm_ma -> w19=-9999 -> fclose -> abort. Caller is original grm_init. Original kernel grm_ma not loaded in AP11.'}}
row,read,dis=image('/usr/lib/libResourceBluetooth.so')
result['bluetooth']={'source_sha256':row['sha256'],'actual_run':'runs/ap12grm-2c0cbb6d','base':'0x7f98155000','runtime_return':'0x7f98156454','elf_return':hex(0x7f98156454-0x7f98155000),'caller':dis(0x13c0,208),'init':dis(0x1c04,100),'interpretation':'Observed user stack returns to this original library+0x1454, ioctl request c0104702 reaches kernel DABT. Hardware behavior is not modeled. grm_ma load RC0 is separate observed evidence.'}
out=ROOT/'ap11-ap12-fault-proof.json';out.write_text(json.dumps(result,indent=2)+'\n');print(out);print(json.dumps(result['bluetooth'],indent=2))
