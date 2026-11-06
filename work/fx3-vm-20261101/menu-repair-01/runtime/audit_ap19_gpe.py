from pathlib import Path
from io import BytesIO
import re,json,hashlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
R=Path(__file__).resolve().parent
run=R/'runs/ap19utimer-b3e92417';s=(run/'serial.log').read_text(errors='replace')
base=int(re.search(r'([0-9a-f]+)-[0-9a-f]+ r-x 0x0+ libgpe.so',s)[1],16)
pc=int(re.search(r' pc: (0x[0-9a-f]+)',s)[1],16);va=pc-base
manifest=R.parent/'original-uipc/ap-projection/full-v4/projection-manifest-full-v4.json';x=json.loads(manifest.read_text());row=next(m for m in x['members'] if m['guest_path']=='/usr/lib/libgpe.so');b=Path(row['local_file']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'];e=ELFFile(BytesIO(b));a=va-48;n=112
for seg in e.iter_segments():
 if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a and a+n<=seg['p_vaddr']+seg['p_filesz']:
  off=seg['p_offset']+a-seg['p_vaddr'];break
cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);ins=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[off:off+n],a)]
result={'run':str(run),'serial_sha256':hashlib.sha256((run/'serial.log').read_bytes()).hexdigest(),'libgpe_sha256':row['sha256'],'library_runtime_base':hex(base),'fault_runtime_pc':hex(pc),'fault_elf_va':hex(va),'instructions':ins,'actual_module_load_gates':{m:m in s for m in ['FX3_UTIMER_RC=0','FX3_STREAM_RC=0','FX3_STREAM2_RC=0','FX3_DMM_RC=0','FX3_GRM_MA_RC=0']},'interpretation':'original MPGRM_GPE0 thread reaches libgpe hardware register access; all five original provider modules now loaded. Not software rendering or original UI frame proof.'}
(R/'ap19-gpe-fault-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
