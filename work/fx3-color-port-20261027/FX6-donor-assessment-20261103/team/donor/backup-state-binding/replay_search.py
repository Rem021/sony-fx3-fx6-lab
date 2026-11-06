#!/usr/bin/env python3
"""Original Data_SearchId/Data_GetSize only, with an explicit loader-state fixture."""
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_X0, UC_ARM64_REG_X30

from parse_bk4 import SOURCES, read_record

HERE = Path(__file__).resolve().parent
MODULES = {
    "fx6": (HERE.parent / "nflasha15-files/kmod/backup.ko", "0fe57e43eb9b868f7011c4ea02ad002f0860d9d10fc2a644c772a074fc7532e6"),
    "fx3": (HERE.parents[5] / "work/sony-firmware-20261024/stage208-Backup-record-routing/originals/kmod/backup.ko", "8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d"),
}
CODE = 0x10000000
STATE = 0x20000000
RECORD = 0x30000000
RET = 0x50000000


def first_sentinel(data: bytes, base: int) -> int:
    ns, np = struct.unpack_from("<II", data, base + 0x10)
    table = base + 0x100 + ns * 6
    for sub in range(ns):
        count, ix = struct.unpack_from("<HI", data, base + 0x100 + sub * 6)
        for unit in range(count):
            if struct.unpack_from("<I", data, table + (ix + unit) * 6 + 2)[0] == 0xFFFFFFFF:
                return (sub << 16) | unit
    raise ValueError("no sentinel ID in pinned record")


def load_module(path: Path, expected: str):
    blob = path.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != expected:
        raise ValueError("module SHA mismatch")
    with path.open("rb") as fp:
        elf = ELFFile(fp)
        text = bytearray(elf.get_section_by_name(".text").data())
        syms = {s.name: s for s in elf.get_section_by_name(".symtab").iter_symbols()}
        relocs = {r["r_offset"]: r for r in elf.get_section_by_name(".rela.text").iter_relocations()}
        search = syms["Data_SearchId"]["st_value"]
        size = syms["Data_GetSize"]["st_value"]
        patches = []
        for off in (search + 0x60, size + 0x40):
            r = relocs[off]
            assert r["r_info_type"] == 257 and r["r_addend"] == 0x28
            old = bytes(text[off:off+8])
            struct.pack_into("<Q", text, off, STATE + 0x28)
            patches.append({"section_offset": off, "file_offset": elf.get_section_by_name(".text")["sh_offset"] + off, "original_hex": old.hex(), "guest_relocated_hex": bytes(text[off:off+8]).hex(), "relocation_type": 257, "addend": 0x28})
        return text, search, size, patches, digest, elf.get_section_by_name(".text")["sh_offset"]


def run_func(code: bytearray, entry: int, record: bytes, base: int, ns: int, arg: int):
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(CODE, (len(code)+4095)&~4095)
    uc.mem_write(CODE, bytes(code))
    uc.mem_map(STATE, 0x1000)
    uc.mem_map(RECORD, (len(record)+4095)&~4095)
    uc.mem_write(RECORD, record)
    uc.mem_map(RET, 0x1000)
    uc.mem_write(STATE+0x28, struct.pack("<QQQ", RECORD+base, RECORD+base+0x100, RECORD+base+0x100+ns*6))
    uc.reg_write(UC_ARM64_REG_X0,arg)
    uc.reg_write(UC_ARM64_REG_X30,RET)
    pcs=[];writes=[]
    def on_code(_uc,addr,size,_):
        if addr==RET:
            _uc.emu_stop();return
        if len(pcs)>=120:
            raise RuntimeError("instruction budget exceeded")
        pcs.append(addr)
    def on_write(_uc,access,addr,size,value,_):
        writes.append([addr,size,value])
    uc.hook_add(UC_HOOK_CODE,on_code)
    uc.hook_add(UC_HOOK_MEM_WRITE,on_write)
    uc.emu_start(CODE+entry,RET+4,count=121)
    if uc.reg_read(UC_ARM64_REG_PC)!=RET or writes:
        raise RuntimeError("return PC or write-set violation")
    return {"returned_x0": uc.reg_read(UC_ARM64_REG_X0), "return_pc": RET, "instruction_count": len(pcs), "pc_section_offsets": [x-CODE for x in pcs], "writes": writes, "budget": 120}


def main():
    output={"scope":"original .text Data_SearchId and Data_GetSize; explicit relocated literal and BSS state fixture; no module loader or runtime Backup body", "cases":[],"modules":{}}
    for model, source in (("fx6","fx6_chaplin_ntsc"),("fx3","fx3_official_seed")):
        path,digest=MODULES[model]
        code,search,size,patches,module_digest,text_file=load_module(path,digest)
        src,expected=SOURCES[source]
        data=src.read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError("BK4 SHA mismatch")
        output["modules"][model]={"path":str(path),"sha256":module_digest,"text_file_offset":text_file,"Data_SearchId_section_offset":search,"Data_GetSize_section_offset":size,"guest_text_base":CODE,"guest_state_base":STATE,"guest_record_base":RECORD,"patched_guest_literals_only":patches}
        for index,base in enumerate([0,((read_record(data,0)[1]+4095)&~4095)]):
            parsed,_=read_record(data,base)
            ns=parsed["subsystem_count"]
            selected=parsed["selected"]
            assert selected["present"] and selected["length"]==1
            positive=run_func(code,search,data,base,ns,0x02AE0000)
            expected_ptr=RECORD+selected["table_file_offset"]
            if positive["returned_x0"]!=expected_ptr:raise RuntimeError("positive pointer mismatch")
            length=run_func(code,size,data,base,ns,expected_ptr)
            if length["returned_x0"]!=1:raise RuntimeError("length mismatch")
            missing_sub=run_func(code,search,data,base,ns,ns<<16)
            missing_unit=run_func(code,search,data,base,ns,0x02AEFFFF)
            sentinel_id=first_sentinel(data,base)
            sentinel=run_func(code,search,data,base,ns,sentinel_id)
            if any(r["returned_x0"] for r in (missing_sub,missing_unit,sentinel)):
                raise RuntimeError("negative case returned nonzero")
            output["cases"].append({"model":model,"source":source,"source_sha256":expected,"record_index":index,"record_file_offset":base,"target_id":"0x02ae0000","expected_data_file_offset":selected["data_file_offset"],"expected_byte":selected["raw_hex"],"positive":positive,"size":length,"missing_subsystem":{"id":hex(ns<<16),**missing_sub},"missing_unit":{"id":"0x02aeffff",**missing_unit},"sentinel":{"id":hex(sentinel_id),**sentinel}})
    output["status"]="PASS"
    print(json.dumps(output,indent=2))

if __name__=="__main__":main()
