#!/usr/bin/env python3
"""Execute a bounded original INQUIRY handler against declared RAM fixtures only.

This starts after dispatch. It does not model USB, Linux, a driver instance,
an actual LUN, media, a host storage stack, or recovery/recording behavior.
"""
from pathlib import Path
import collections
import datetime
import io
import json
import struct
import sys
import unicorn as uc
from unicorn import arm64_const as reg
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h

MODULE_SHA='b43130dbc3d9b72dc03c3acb7993639e1cefcbb43621fef809f6f617cb30b255'
KERNEL_SHA='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
LIB_SHA='6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396'
K=h.prev.n.K
TEXT=K+0x3000000
CTX,UNIT,DRIVE,CDB,SOURCE,DEST,STACK=[0x10000000+i*0x10000 for i in range(7)]
STOP=0x1fff0000


def templates(raw):
    e=ELFFile(io.BytesIO(raw));s=e.get_section_by_name('.dynsym');result=[]
    for symbol in s.iter_symbols():
        if not symbol.name.startswith('INQUIRY_DATA_') or symbol['st_size']==8:continue
        a,n=symbol['st_value'],symbol['st_size']
        segs=[p for p in e.iter_segments() if p['p_type']=='PT_LOAD' and p['p_vaddr']<=a and a+n<=p['p_vaddr']+p['p_filesz']]
        assert len(segs)==1
        off=segs[0]['p_offset']+a-segs[0]['p_vaddr'];blob=raw[off:off+n]
        assert blob[8:16]==b'Sony    ' and blob[32:36]==b'1.00'
        result.append((symbol.name,blob))
    assert len(result)==3
    return sorted(result)


def run_case(text,entry,size,memcpy,memcpy_bytes,label,blob,allocation,capacity,variant='standard'):
    m=uc.Uc(uc.UC_ARCH_ARM64,uc.UC_MODE_ARM)
    m.mem_map(TEXT,(len(text)+4095)&-4096,uc.UC_PROT_READ|uc.UC_PROT_EXEC);m.mem_write(TEXT,text)
    page=memcpy&-4096;assert memcpy+len(memcpy_bytes)<=page+4096
    m.mem_map(page,4096,uc.UC_PROT_READ|uc.UC_PROT_EXEC);m.mem_write(memcpy,memcpy_bytes)
    initial={CTX:bytearray(4096),UNIT:bytearray(4096),DRIVE:bytearray(4096),CDB:bytearray(4096),
             SOURCE:bytearray(4096),DEST:bytearray(b'\xa5'*4096),STACK:bytearray(4096)}
    struct.pack_into('<Q',initial[CTX],0,UNIT)
    struct.pack_into('<Q',initial[CTX],0x10,CDB)
    struct.pack_into('<II',initial[CTX],0x1c,2 if variant=='data_out' else 1,capacity)
    struct.pack_into('<Q',initial[CTX],0x28,DEST)
    initial[CTX][0x30]=0xcc;struct.pack_into('<I',initial[CTX],0x34,0xdeadbeef)
    struct.pack_into('<Q',initial[UNIT],0x28,DRIVE)
    initial[UNIT][0x68:0x6b]=b'\xcc'*3
    struct.pack_into('<I',initial[DRIVE],0xc,len(blob));struct.pack_into('<Q',initial[DRIVE],0x10,SOURCE)
    initial[CDB][:6]=bytes([0x12,0,1 if variant=='invalid_page' else 0,allocation>>8,allocation&255,
                           1 if variant=='link' else 4 if variant=='naca' else 0])
    initial[SOURCE][:len(blob)]=blob
    for address,data in initial.items():
        writable=address in (CTX,UNIT,DEST,STACK)
        m.mem_map(address,4096,uc.UC_PROT_READ|(uc.UC_PROT_WRITE if writable else 0));m.mem_write(address,bytes(data))
    instructions=[];writes=[];memcpy_calls=[]
    def inside(a,n,lo,hi):return lo<=a and a+n<=hi
    def code(u,pc,n,_):
        assert inside(pc,n,entry,entry+size) or inside(pc,n,memcpy,memcpy+len(memcpy_bytes)),hex(pc)
        instructions.append(pc)
        assert len(instructions)<=300
        if pc==memcpy:
            args=[u.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(i))) for i in range(3)]
            memcpy_calls.append([hex(args[0]),hex(args[1]),args[2]])
            assert args==[DEST,SOURCE,min(allocation,len(blob))]
    def memory(u,access,a,n,value,_):
        allowed=[(CTX,CTX+0x38),(UNIT,UNIT+0x6b),(DRIVE,DRIVE+0x18),(CDB,CDB+6),
                 (SOURCE,SOURCE+len(blob)),(DEST,DEST+96),(STACK+0xfe0,STACK+0x1000)]
        assert any(inside(a,n,lo,hi) for lo,hi in allowed),(hex(a),n,access)
        if access==uc.UC_MEM_WRITE:
            assert any(inside(a,n,lo,hi) for lo,hi in [(CTX+0x30,CTX+0x31),(CTX+0x34,CTX+0x38),
                       (UNIT+0x68,UNIT+0x6b),(DEST,DEST+min(allocation,len(blob))),
                       (STACK+0xfe0,STACK+0x1000)]),(hex(a),n)
            writes.append({'pc':hex(u.reg_read(reg.UC_ARM64_REG_PC)),'address':hex(a),'bytes':n})
    m.hook_add(uc.UC_HOOK_CODE,code)
    m.hook_add(uc.UC_HOOK_MEM_READ|uc.UC_HOOK_MEM_WRITE,memory)
    m.reg_write(reg.UC_ARM64_REG_X0,CTX);m.reg_write(reg.UC_ARM64_REG_SP,STACK+0x1000)
    m.reg_write(reg.UC_ARM64_REG_X30,STOP)
    m.emu_start(entry,STOP,count=301)
    assert m.reg_read(reg.UC_ARM64_REG_PC)==STOP and m.reg_read(reg.UC_ARM64_REG_X0)==0
    assert m.reg_read(reg.UC_ARM64_REG_SP)==STACK+0x1000
    status=m.mem_read(CTX+0x30,1)[0];transferred=struct.unpack('<I',m.mem_read(CTX+0x34,4))[0]
    sense=bytes(m.mem_read(UNIT+0x68,3))
    count=min(allocation,len(blob));success=variant=='standard' and capacity>=count
    expected_status=0 if success else 1 if variant in ('invalid_page','link','naca') else 2
    expected_sense=bytes([5,0x24,0]) if expected_status==1 else bytes([5,0x20,0]) if variant=='data_out' else bytes(3)
    assert status==expected_status and transferred==(count if success else 0) and sense==expected_sense
    assert len(memcpy_calls)==int(success)
    expected=bytearray(initial[DEST])
    if success:expected[:count]=blob[:count]
    assert bytes(m.mem_read(DEST,4096))==bytes(expected)
    for a in (DRIVE,CDB,SOURCE):assert bytes(m.mem_read(a,4096))==bytes(initial[a])
    for a,slots in [(CTX,[(0x30,0x31),(0x34,0x38)]),(UNIT,[(0x68,0x6b)]),(STACK,[(0xfe0,0x1000)])]:
        after=m.mem_read(a,4096)
        assert all(x==y or any(lo<=i<hi for lo,hi in slots) for i,(x,y) in enumerate(zip(initial[a],after)))
    return {'template':label,'variant':variant,'allocation':allocation,'declared_capacity':capacity,
            'instructions':len(instructions),'command_status':status,'transferred':transferred,'sense_hex':sense.hex(),
            'actual_original_memcpy_calls':memcpy_calls,'writes':writes,'RAM_guards_passed':True}


def main():
    h.im.volume();out=STAGE/'inquiry-handler-emulation.json';assert not out.exists()
    original=STAGE.parent/'stage67-connected-native-pnp/official-files/nflasha15'
    module=(original/'kmod/usbg_storage.ko').read_bytes();lib=(original/'lib/libInfraUsbCmn.so').read_bytes()
    kernel=(h.prev.n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assert h.im.sha(module)==MODULE_SHA and h.im.sha(kernel)==KERNEL_SHA and h.im.sha(lib)==LIB_SHA
    e=ELFFile(io.BytesIO(module));s=e.get_section_by_name('.symtab')
    syms=[x for x in s.iter_symbols() if x.name=='inquiry_std'];assert len(syms)==1
    fn=syms[0];assert fn['st_value']==0x6d60 and fn['st_size']==632
    text=bytearray(e.get_section(fn['st_shndx']).data())
    rels=[r for sec in e.iter_sections() if sec['sh_type']=='SHT_RELA' and sec['sh_info']==fn['st_shndx']
          for r in sec.iter_relocations() if fn['st_value']<=r['r_offset']<fn['st_value']+fn['st_size']]
    assert len(rels)==1
    r=rels[0];assert r['r_info_type']==283 and r['r_offset']==0x6ed0 and r['r_addend']==0
    assert s.get_symbol(r['r_info_sym']).name=='memcpy'
    candidates=h.prev.audit.export_candidates(kernel,'memcpy');assert len(candidates)==1
    memcpy=int(candidates[0]['value'],16);assert memcpy==K+0x1efe80
    memcpy_bytes=kernel[memcpy-K:0x1effd4]
    assert memcpy_bytes[-4:]==bytes.fromhex('c0035fd6')
    original_word=struct.unpack_from('<I',text,r['r_offset'])[0]
    assert original_word&0xfc000000==0x94000000
    delta=memcpy-(TEXT+r['r_offset']);assert delta%4==0 and -(1<<27)<=delta<(1<<27)
    patched=(original_word&0xfc000000)|((delta//4)&0x3ffffff)
    struct.pack_into('<I',text,r['r_offset'],patched)
    displacement=patched&0x3ffffff
    if displacement&(1<<25):displacement-=1<<26
    assert TEXT+r['r_offset']+displacement*4==memcpy
    # Only this original CALL26 relocation is changed in guest RAM.
    raw_text=e.get_section(fn['st_shndx']).data()
    assert all(a==b or r['r_offset']<=i<r['r_offset']+4 for i,(a,b) in enumerate(zip(raw_text,text)))
    cases=[];ts=templates(lib)
    for label,blob in ts:
        for allocation in (0,4,36,96):
            for capacity in (0,35,96):
                cases.append(run_case(bytes(text),TEXT+fn['st_value'],fn['st_size'],memcpy,memcpy_bytes,label,blob,allocation,capacity))
    for variant in ('invalid_page','link','naca','data_out'):
        cases.append(run_case(bytes(text),TEXT+fn['st_value'],fn['st_size'],memcpy,memcpy_bytes,*ts[0],96,96,variant))
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_BOUNDED_ORIGINAL_INQUIRY_HANDLER_RAM_ONLY','script_sha256':h.im.sha(Path(__file__).read_bytes()),
            'original_module_sha256':MODULE_SHA,'original_kernel_sha256':KERNEL_SHA,'original_template_library_sha256':LIB_SHA,
            'module_function_section_offset':hex(fn['st_value']),'function_bytes':fn['st_size'],
            'function_unrelocated_sha256':h.im.sha(raw_text[fn['st_value']:fn['st_value']+fn['st_size']]),
            'guest_CALL26_relocation':{'section_offset':hex(r['r_offset']),'original':hex(original_word),'relocated':hex(patched),
                                     'resolved_memcpy_candidate':candidates[0]},
            'kernel_memcpy_body_bytes':len(memcpy_bytes),'kernel_memcpy_body_sha256':h.im.sha(memcpy_bytes),
            'templates':[{'name':label,'bytes':len(blob),'sha256':h.im.sha(blob)} for label,blob in ts],
            'case_count':len(cases),'status_counts':dict(collections.Counter(x['command_status'] for x in cases)),
            'actual_memcpy_body_used':True,'return_or_memcpy_adapter':False,'memory_and_instruction_guards':True,'cases':cases,
            'scope':['Already-dispatched inquiry_std only, using declared per-drive context and original initial templates.',
                     'Actual original kernel memcpy bytes run in emulator; symbol resolution is static, not live kernel state.',
                     'Standard positive cases copy min(allocation, configured template length) and clear sense; negative guards fail locally.',
                     'All inputs, addresses, direction and capacity are fixtures, not captured USB/LUN state.',
                     'This does not execute command dispatch, extension handling, USB transport, hardware drivers, media or a Linux boot.',
                     'It does not verify the active camera driver, dynamic INQUIRY data, body firmware version or physical LUN selection.'],
            'camera_handles_commands_media_auth_modes_modules_WBI_flash':False,'Windows_device_control':False,
            'goal_complete':False,'persistent_write_release':False}
    h.im.write_json(out,result)
    print(json.dumps({k:result[k] for k in ('status','case_count','status_counts','actual_memcpy_body_used','goal_complete')}))


if __name__=='__main__':main()
