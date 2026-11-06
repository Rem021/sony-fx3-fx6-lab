#!/usr/bin/env python3
"""Pin source bytes and emit a compact AV event / Backup registration trace."""
import hashlib
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

from replay_search import MODULES

HERE = Path(__file__).resolve().parent
AV = HERE.parent / "fat-files/nflasha3/av-cam.bin"
AV_SHA = "56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf"
FX3_AV = HERE.parents[5] / "work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin"
FX3_AV_SHA = "0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf"
LIRO = HERE.parent / "nflasha15-files/kmod/liro.ko"
LIRO_SHA = "8a7cfcaef07ad18ca2a97847d44d31bb9152f57c0fcbccd96056ad683649f2e1"
MD = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
AV_BASE = 0xffffffc001000000
ID_MOV_MASK = 0x52a055c0


def pinned(path, expected=None):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if expected is not None and sha != expected:
        raise ValueError(f"SHA mismatch {path}: {sha}")
    return data, sha


def span(blob, start, end, section_file_offset=0, va_base=0):
    raw = blob[start:end]
    return {"section_offset": start, "file_offset": section_file_offset+start, "va": hex(va_base+start) if va_base else None, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "instructions": [{"section_offset": i.address, "file_offset": section_file_offset+i.address, "va": hex(va_base+i.address) if va_base else None, "bytes": i.bytes.hex(), "mnemonic": i.mnemonic, "operands": i.op_str} for i in MD.disasm(raw,start)]}


def direct_bl_callers(blob, target, lo, hi):
    hits=[]
    for off in range(lo,hi,4):
        word=struct.unpack_from("<I",blob,off)[0]
        if word&0xfc000000!=0x94000000:continue
        imm=word&0x3ffffff
        if imm&0x2000000:imm-=0x4000000
        if off+4*imm==target:hits.append(off)
    return hits


def module_trace(model, path, expected):
    raw,sha=pinned(path,expected)
    with path.open("rb") as fp:
        e=ELFFile(fp)
        text=e.get_section_by_name(".text")
        tblob=text.data()
        sym=e.get_section_by_name(".symtab")
        names={s.name:s for s in sym.iter_symbols()}
        rel=e.get_section_by_name(".rela.text")
        refs={}
        for r in rel.iter_relocations():
            s=sym.get_symbol(r["r_info_sym"])
            if s.name in ("Data_init","backupfile_init","Data_SearchId","Data_GetSize","Data_GetDataPt","Backup_nread","Backup_write","backup_sharedcb_send_msg","memcpy"):
                refs.setdefault(s.name,[]).append({"text_section_offset":r["r_offset"],"file_offset":text["sh_offset"]+r["r_offset"],"symbol_value":s["st_value"],"type":r["r_info_type"]})
        selected={}
        for name in ("Data_init","Data_SearchId","Data_GetSize","Data_GetDataPt","Backup_nread","Backup_write","backupfile_init"):
            s=names[name]
            selected[name]=span(tblob,s["st_value"],s["st_value"]+s["st_size"],text["sh_offset"])
        inner=0x700 if model=="fx6" else 0x760
        selected["nread_inner"]=span(tblob,inner,inner+0x118,text["sh_offset"])
        write_inner=0xd8
        selected["write_inner_start"]=span(tblob,write_inner,write_inner+0x12c,text["sh_offset"])
        return {"path":str(path),"sha256":sha,"elf_type":e["e_type"],"machine":e["e_machine"],"text_file_offset":text["sh_offset"],"symbols":selected,"call26_and_memcpy_relocations":refs}


def bounded_id_mov_scan(av):
    donor = HERE.parent / "nflasha15-files"
    result={"pattern":"AArch64 MOVZ/MOV alias exact word 0x02ae0000, any W register; one instruction form only", "av_hits":[], "ap_elfs_scanned":0,"ap_hits":[],"scope":"AV aligned [0,0x370000); AP bin/lib/kmod regular ELF under 20MB, executable sections only"}
    for off in range(0,0x370000,4):
        if struct.unpack_from("<I",av,off)[0]&~31==ID_MOV_MASK:
            result["av_hits"].append(off)
    for folder in ("bin","lib","kmod"):
        for p in (donor/folder).glob("*"):
            if not p.is_file() or p.stat().st_size>20_000_000:continue
            try:
                with p.open("rb") as fp:
                    e=ELFFile(fp)
                    result["ap_elfs_scanned"]+=1
                    for section in e.iter_sections():
                        if not (section["sh_flags"]&4) or section["sh_size"]<4:continue
                        b=section.data()
                        for off in range(0,len(b)-3,4):
                            if struct.unpack_from("<I",b,off)[0]&~31==ID_MOV_MASK:
                                result["ap_hits"].append({"path":str(p),"section":section.name,"section_offset":off,"file_offset":section["sh_offset"]+off})
            except Exception:
                continue
    return result


def main():
    av,sha=pinned(AV,AV_SHA)
    event_spans={
        "consumer_receive_release":(0x2a72b8,0x2a7350),
        "producer_type0":(0x2991f4,0x2992d0),
        "producer_type1":(0x29a4e4,0x29a5b0),
        "producer_type2":(0x299ea4,0x299f74),
        "producer_type3":(0x29a610,0x29a6d0),
        "producer_type4":(0x29a740,0x29a810),
        "producer_type5":(0x29a848,0x29a900),
        "send_common":(0x2a7eac,0x2a7fe8),
        "type0_upstream_command3":(0x29b58c,0x29b5e8),
        "type0_upstream_command4":(0x29d990,0x29da2c),
        "backup_state_consumer":(0x29b290,0x29b308),
        "provider_send_thunks":(0x2eda4,0x2ee58),
    }
    avcuts={k:span(av,a,b,0,AV_BASE) for k,(a,b) in event_spans.items()}
    sends=direct_bl_callers(av,0x2a7eac,0x10000,0x370000)
    type0=direct_bl_callers(av,0x2991f4,0x10000,0x370000)
    assert sends==[0x2992c4,0x299f68,0x29a5a4,0x29a6c4,0x29a804,0x29a8f0]
    assert type0==[0x29b5d4,0x29da08]
    fx3av,fx3sha=pinned(FX3_AV,FX3_AV_SHA)
    fx3_sends=direct_bl_callers(fx3av,0x2c4cc8,0x10000,0x390000)
    fx3_type0=direct_bl_callers(fx3av,0x2b5ffc,0x10000,0x390000)
    assert fx3_sends==[0x2b60cc,0x2b6d70,0x2b73ac,0x2b74cc,0x2b760c,0x2b76f8]
    assert fx3_type0==[0x2b83fc,0x2ba830]
    liro,liro_sha=pinned(LIRO)
    with LIRO.open("rb") as fp:
        e=ELFFile(fp);sym=e.get_section_by_name(".symtab");rs=e.get_section_by_name(".rela.init.data")
        byoff={r["r_offset"]:sym.get_symbol(r["r_info_sym"]).name for r in rs.iter_relocations()}
        assert byoff[0x360]=="osal_snd_msg" and byoff[0x398]=="osal_valloc_msg_wait"
        liro_binding={"path":str(LIRO),"sha256":liro_sha,"source_init_data_0x360":"osal_snd_msg","source_init_data_0x398":"osal_valloc_msg_wait","AV_provider_slots":{"0x3a8":"osal_snd_msg","0x3e0":"osal_valloc_msg_wait"},"basis":"LIRO original .rela.init.data plus prior proven +0x48 provider copy"}
    result={"status":"PASS","evidence":"original static bytes/ELF relocations, no loader or OSAL runtime", "av":{"path":str(AV),"sha256":sha,"base_va":hex(AV_BASE),"code_scan":"aligned [0x10000,0x370000) BL immediate target search; not all indirect callers", "send_common_direct_callers":[hex(x) for x in sends],"type0_direct_callers":[hex(x) for x in type0],"spans":avcuts},"fx3_av":{"path":str(FX3_AV),"sha256":fx3sha,"base_va":hex(AV_BASE),"send_common_direct_callers":[hex(x) for x in fx3_sends],"type0_direct_callers":[hex(x) for x in fx3_type0],"spans":{"type0":span(fx3av,0x2b5ffc,0x2b60d4,0,AV_BASE),"send_common":span(fx3av,0x2c4cc8,0x2c4dfc,0,AV_BASE)}},"liro":liro_binding,"backup_modules":{name:module_trace(name,*row) for name,row in MODULES.items()},"limited_id_writer_scan":bounded_id_mov_scan(av)}
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
