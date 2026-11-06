#!/usr/bin/env python3
"""Discriminate two metadata layouts and bound the original frame caller.

No copied non-null handle is consumed after an unexecuted reference increment.
Caller experiments use separate explicitly declared already-owned inputs.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage89-native-pending-cache-origin'))
import cache_origin as prev
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='957337948b6af99a3bcc7f8d20ec867c71851967c5b88a167d9b3ba1d78a5daf'
SRC_PA,SRC=0x01000000,0x81000000
DST_PA,DST=0x01100000,0x81100000
OWNER_PA,OWNER=0x01200000,0x81200000
INSTANCE_PA,INSTANCE=0x01300000,0x81300000
HANDLES_PA,HANDLES=0x01400000,0x81400000
FRAME_PA,FRAME=0x01500000,0x81500000
PACK_PA,PACK=0x01600000,0x81600000
STACK_PA,STACK=0x02000000,0x82000000
TRAP_PA,TRAP=0x03000000,0x83000000
SP=STACK+0x8000
GP=0x8024eb58
PAGES=(SRC_PA,DST_PA,OWNER_PA,INSTANCE_PA,HANDLES_PA,FRAME_PA,PACK_PA)
LIMITS=((0x1cb92c,0x1cba1c),(0x1f399c,0x1f3ae4),
    (0x1cb17c,0x1cb1c4),(0x1cb24c,0x1cb274),(0x1cb300,0x1cb320),
    (0x1cb3a8,0x1cb3b4),(0x1cb43c,0x1cb448),(0x1cb4d0,0x1cb4dc),
    (0x1cb564,0x1cb59c),(0x144124,0x1441d8),(0x134f8c,0x134fac),
    (0x131e34,0x131e60),(0x1351b0,0x1351c0),(0x131818,0x131888))
STOPS={0x1f3b40:'non_null_parameter_handle_copied_before_unexecuted_GP_reference_increment',
    0x131e60:'owner_geometry_written_before_unexecuted_geometry_builder_call',
    0x131888:'caller_bound_frame_owner_and_raw_metadata_before_header_body'}


def word(raw,off):return struct.unpack_from('<I',raw,off)[0]


def app_gp(blob):
    hi,lo=struct.unpack_from('<II',blob,0x930c)
    assert hi>>26==15 and (hi>>16)&31==28
    assert lo>>26==9 and (lo>>21)&31==28 and (lo>>16)&31==28
    result=((hi&0xffff)<<16)+struct.unpack('<h',struct.pack('<H',lo&0xffff))[0]
    assert result&0xffffffff==GP
    return GP


class Guest:
    def __init__(self,blob,seed,flag,handle):
        self.blob=blob;self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        rw=u.UC_PROT_READ|u.UC_PROT_WRITE;ro=u.UC_PROT_READ
        self.uc.mem_map(0,(len(blob)+4095)&-4096,ro|u.UC_PROT_EXEC);self.uc.mem_write(0,blob)
        for at in PAGES:self.uc.mem_map(at,4096,rw if at in (DST_PA,OWNER_PA,FRAME_PA) else ro)
        self.uc.mem_map(STACK_PA,65536,rw)
        self.uc.mem_map(TRAP_PA,4096,ro|u.UC_PROT_EXEC);self.uc.mem_write(TRAP_PA,bytes(4096))
        source=bytearray((0x23+i*7)&255 for i in range(4096));source[0x50]=flag
        struct.pack_into('<I',source,0x54,handle)
        # Explicit null nested references isolate the complete no-share copy.
        for off in range(0x5c,0x80,4):struct.pack_into('<I',source,off,0)
        struct.pack_into('<I',source,0x80,0x12345678);struct.pack_into('<I',source,0x84,0)
        owner=bytearray([0x61])*4096
        struct.pack_into('<HH',owner,0x24,0xaaaa,0xbbbb)
        instance=bytearray([0x62])*4096;struct.pack_into('<I',instance,4,OWNER)
        handles=struct.pack('<II',FRAME_PA,PACK_PA)+bytes(4088)
        packet=bytearray([0x84])*4096;struct.pack_into('<HH',packet,0xec,119,67)
        self.initial={SRC_PA:bytes(source),DST_PA:bytes([seed])*4096,OWNER_PA:bytes(owner),
            INSTANCE_PA:bytes(instance),HANDLES_PA:handles,FRAME_PA:bytes([0x73])*4096,PACK_PA:bytes(packet)}
        for at,raw in self.initial.items():self.uc.mem_write(at,raw)
        self.stack=bytearray([0xd7])*65536;self.uc.mem_write(STACK_PA,bytes(self.stack))
        self.uc.hook_add(u.UC_HOOK_CODE,self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID,self.invalid)
        self.uc.hook_add(u.UC_HOOK_INTR,self.interrupt)

    def invalid(self,uc,access,address,size,value,user):
        self.reason='invalid:'+hex(address);uc.emu_stop();return False

    def interrupt(self,uc,number,user):
        self.interrupts.append(number);self.reason='native_interrupt';uc.emu_stop()

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<10000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0','eret',
            'wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic)

    def read(self,at):return bytes(self.uc.mem_read(at,4096))

    def save(self,va,value):struct.pack_into('<I',self.stack,va-STACK,value)

    def run(self,label,entry,**registers):
        for name,value in {'sp':SP,'ra':TRAP,'gp':GP,**{f's{i}':0 for i in range(8)},'fp':0,**registers}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in set(STOPS.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(STACK_PA,65536))==self.stack
        assert bytes(self.uc.mem_read(TRAP_PA,4096))==bytes(4096)
        for at in (SRC_PA,INSTANCE_PA,HANDLES_PA,PACK_PA):assert self.read(at)==self.initial[at]
        assert self.uc.reg_read(reg.UC_MIPS_REG_GP)==GP
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
            'SP':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),'RA':hex(self.uc.reg_read(reg.UC_MIPS_REG_RA)),
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'exact_entire_stack_image_and_immutable_inputs_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,
            'MMIO_instruction_patch_or_fake_return':False}

    def check(self,want):
        for at,raw in want.items():assert self.read(at)==bytes(raw),hex(at)


def contrast(blob,seed,flag):
    m=Guest(blob,seed,flag,HANDLES+4);source=m.initial[SRC_PA]
    want={at:bytearray(raw) for at,raw in m.initial.items()};dst=want[DST_PA]
    for lo,hi in ((0,0x13),(0x14,0x17),(0x18,0x1b),(0x1c,0x38)):
        dst[0x3c+lo:0x3c+hi]=source[0x3c+lo:0x3c+hi]
    event=m.run('candidate A4 nested-field copier retains high byte of offset54',
                0x1cb92c,a0=DST+0x3c,a1=SRC+0x3c)
    assert event['stop']=='returned_via_original_jr_ra'
    assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==SP
    m.check(want)
    assert word(dst,0x54)==((seed<<24)|((HANDLES+4)&0xffffff)) and word(dst,0x54)!=HANDLES+4
    return {'seed':seed,'declared_source_flag':flag,'source_handle_word':HANDLES+4,
        'destination_word54':word(dst,0x54),'destination_high_byte_preserved':True,
        'copy_is_raw_parameter_handle_ownership_transfer':False,
        'source_page_hex':source.hex(),'destination_page_hex':bytes(dst).hex(),'events':[event]}


def raw_copy(blob,seed,flag,nonnull):
    handle=HANDLES+4 if nonnull else 0
    m=Guest(blob,seed,flag,handle);source=m.initial[SRC_PA]
    want={at:bytearray(raw) for at,raw in m.initial.items()};dst=want[DST_PA]
    for lo,hi in ((0,0xd),(0x10,0x3e),(0x40,0x51),(0x54,0x58)):
        dst[lo:hi]=source[lo:hi]
    copy_sp=SP-0x30
    for off in (0x20,0x24,0x28):m.save(copy_sp+off,0)
    m.save(copy_sp+0x2c,TRAP)
    if not nonnull:
        nested_sp=copy_sp-0x50
        for off in (0x28,0x2c,0x30,0x34,0x38,0x3c,0x40):m.save(nested_sp+off,0)
        m.save(nested_sp+0x20,DST);m.save(nested_sp+0x24,SRC)
        m.save(nested_sp+0x44,IMAGE+0x1f3aac)
        struct.pack_into('<I',dst,0x58,GP-0x5d58)
        dst[0x5c:0x84]=source[0x5c:0x84]
        dst[0x84:0x8c]=source[0x84:0x8c]
    event=m.run('original raw metadata copy constructor with explicit null nested references',
                0x1f399c,a0=DST,a1=SRC)
    assert event['stop']==(STOPS[0x1f3b40] if nonnull else 'returned_via_original_jr_ra')
    assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==(copy_sp if nonnull else SP)
    if not nonnull:
        for i in range(8):assert m.uc.reg_read(getattr(reg,f'UC_MIPS_REG_S{i}'))==0
        assert m.uc.reg_read(reg.UC_MIPS_REG_FP)==0 and m.uc.reg_read(reg.UC_MIPS_REG_RA)==TRAP
    m.check(want)
    assert word(dst,0x54)==handle and dst[0x50]==flag
    return {'seed':seed,'declared_source_flag':flag,'nonnull_parameter_handle':nonnull,
        'source_handle_word':handle,'destination_word54':word(dst,0x54),
        'source_page_hex':source.hex(),'destination_page_hex':bytes(dst).hex(),
        'native_constructor_returned':not nonnull,'nonnull_reference_increment_completed':False,
        'copied_nonnull_handle_consumed_after_stop':False,'events':[event]}


def caller(blob,seed,flag):
    # Separate owned-input experiment, never uses the unshared output above.
    m=Guest(blob,seed,flag,HANDLES+4);want={at:bytearray(raw) for at,raw in m.initial.items()}
    # Descriptor at SP+10, handle at descriptor+10, is an explicit existing input.
    m.save(SP+0x20,HANDLES);m.uc.mem_write(STACK_PA,bytes(m.stack))
    if flag:
        m.save(SP-0x10,IMAGE+0x1441c8);m.save(SP-0x30,IMAGE+0x134fa0)
        struct.pack_into('<HH',want[OWNER_PA],0x24,120,68)
    else:
        m.save(SP-0x10,IMAGE+0x1441d8)
        base=SP-0x80
        for off in (0x40,0x4c,0x50,0x54,0x58):m.save(base+off,0)
        m.save(base+0x44,SRC);m.save(base+0x48,INSTANCE);m.save(base+0x5c,IMAGE+0x1351c0)
    event=m.run('original caller checks raw flag and obtains geometry or binds frame arguments',
                0x144124,s1=SRC,s2=INSTANCE)
    assert event['stop']==STOPS[0x131e60 if flag else 0x131888]
    if flag:
        assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==SP-0x40
        assert m.uc.reg_read(reg.UC_MIPS_REG_RA)==IMAGE+0x134fa0
    else:
        assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==SP-0x80
        assert m.uc.reg_read(reg.UC_MIPS_REG_RA)==IMAGE+0x1351c0
        assert m.uc.reg_read(reg.UC_MIPS_REG_S0)==FRAME
        assert m.uc.reg_read(reg.UC_MIPS_REG_S1)==OWNER and m.uc.reg_read(reg.UC_MIPS_REG_S4)==SRC
    m.check(want)
    return {'seed':seed,'declared_raw_flag':flag,'owned_inputs_separate_from_copy_experiment':True,
        'declared_payload_ec_ee':[119,67],'owner_u16_24_26_after':list(struct.unpack_from('<HH',want[OWNER_PA],0x24)),
        'final_pages':{hex(at):m.read(at).hex() for at in PAGES},'events':[event],
        'geometry_builder_or_full_frame_header_body_or_actual_MAIN_executed':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage89-native-pending-cache-origin/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    blob_path=prev.old.old.prev.a.prev.p.a.v.VCD_PATH
    blob=blob_path.read_bytes();assert im.sha(blob)==im.PINS[str(blob_path.relative_to(BASE))]
    app_gp(blob)
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    contrasts=[];copies=[];callers=[]
    try:
        for seed in (0xa5,0xc3):
            for flag in (0,0x10):contrasts.append(contrast(blob,seed,flag))
        for seed in (0xa5,0xc3):
            for flag in (0,0x10):
                for nonnull in (False,True):copies.append(raw_copy(blob,seed,flag,nonnull))
        for seed in (0xa5,0xc3):
            for flag in (0,0x10):callers.append(caller(blob,seed,flag))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),
            'completed_contrast':len(contrasts),'completed_raw_copy':len(copies),'completed_caller':len(callers)})
        raise
    result={'status':'PASS_DISTINCT_LAYOUT_RAW_COPY_REFERENCE_BOUNDARY_AND_ORIGINAL_CALLER',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
                          'prior_manifest_sha256':PRIOR_SHA,'declared_app_GP_from_original_pair':hex(GP)},
        'contrast_cases':contrasts,'raw_copy_cases':copies,'caller_cases':callers,
        'bounded_entries':len(contrasts)+len(copies)+len(callers),
        'scope':'The A4 candidate field copier is not substituted for the 8C raw metadata copy. '
            'Non-null raw handles stop before GP/refcount work and are not consumed; null-only constructor can return. '
            'Separate caller starts after unexecuted frame allocation, with declared owned inputs and existing descriptor. '
            'Raw producer, ownership, queue/dispatch, geometry body, MAIN, hardware and recovery remain unproved.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'metadata-source-results.json',result)
    print(json.dumps({'status':result['status'],'cases':result['bounded_entries'],'output':str(out)}))


if __name__=='__main__':main()
