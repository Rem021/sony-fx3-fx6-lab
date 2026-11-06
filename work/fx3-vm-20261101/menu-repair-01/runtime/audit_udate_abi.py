from pathlib import Path
from io import BytesIO
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,hashlib
R=Path(__file__).resolve().parent;p=R.parent/'original-uipc/original-modules/udate.ko';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='a3cbb9977915259a5a9d5e16e49adbb58f26c43d2ad2c63381c60e1103d205bb';e=ELFFile(BytesIO(b));sy=e.get_section_by_name('.symtab');t=e.get_section_by_name('.text').data();refs={r['r_offset']:sy.get_symbol(r['r_info_sym']).name for r in e.get_section_by_name('.rela.text').iter_relocations()};cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);funcs={}
for s in sy.iter_symbols():
 if s.name not in ['udate_open_kif','udate_get_localtime','udate_set_date']:continue
 funcs[s.name]=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'relocation_symbol':refs.get(i.address)} for i in cs.disasm(t[s['st_value']:s['st_value']+s['st_size']],s['st_value'])]
result={'source_sha256':hashlib.sha256(b).hexdigest(),'functions':funcs,'native_layout_facts':['udate_open_kif registers90013d through original OSAL','set_date requires reserved timezone field+4 ==0, TD and DST signed16 each in -1440..1440 or7fff sentinel','get_localtime with running state1 queries original utimer910042 and adds (TD+DST)*60000 milliseconds to the UTC date base'],'FX3_default_observation':{'run':'runs/ap30date-b340a0b7','native_default_local_date':'2021-01-01T00:00:00','TD_minutes':540,'DST':0,'reserved':0},'normalization_validation':{'run':'runs/ap31date-acedcfcb','input_UTC':'2020-12-31T15:00:00','readback_local':'2021-01-01T00:00:02','TD_preserved':540,'native_status':0,'native_elapsed_seconds':2,'not_wall_clock_accuracy_test':True},'scope':'default-source virtual clock only; no host clock/RTC/device/CP time sync acceptance'};(R/'udate-abi-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(R/'udate-abi-proof.json')
