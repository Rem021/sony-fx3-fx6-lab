#!/usr/bin/env python3
"""Original owner defaults, metadata classification, geometry and frame caller.

No IRQ instruction is emulated. Input metadata and an existing owned frame
descriptor remain declared, with two separate outer entry points.
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
sys.path.insert(0,str(BASE/'stage91-native-type4-first-cache-buffer'))
import type4_cache as prev
old=prev.prev
im,u,reg,cs,IMAGE=old.im,old.u,old.reg,old.cs,old.IMAGE
PRIOR_SHA='466c63970bff04d0f484433974280ccf1a4d3880620119e5cdecfe236a42a233'
SP_SEL,SP_CALL=old.STACK+0x6000,old.STACK+0xa000
STOPS={0x1315d0:'original_geometry_builder_returned_before_message_packet_work',
       0x131888:'original_geometry_setter_returned_and_frame_arguments_bound_before_header_body'}
LIMITS=((0x1352f0,0x135358),(0x131590,0x1315d0),(0x13179c,0x1317b0),
    (0x13380c,0x1338c4),(0x66bb8,0x66c2c),(0x1345c8,0x134644),
    (0x134748,0x134838),(0x134838,0x1348d4),
    (0x144124,0x1441d8),(0x134f8c,0x134fac),(0x131e34,0x131e74),
    (0x1351b0,0x1351c0),(0x131818,0x131888))


class Guest(old.Guest):
    def __init__(self,blob,seed,mode,flag,units):
        super().__init__(blob,seed,flag,old.HANDLES+4)
        self.initial[old.OWNER_PA]=bytes([seed])*4096
        raw=bytearray(self.initial[old.SRC_PA])
        raw[0xd]=0;raw[0xe]=mode;raw[0x10]=0;raw[0x13]=0
        struct.pack_into('<HH',raw,0x14,*units)
        packet=bytearray(self.initial[old.PACK_PA]);struct.pack_into('<HH',packet,0xec,units[0]-1,units[1]-1)
        self.initial[old.SRC_PA]=bytes(raw);self.initial[old.PACK_PA]=bytes(packet)
        for at in (old.OWNER_PA,old.SRC_PA,old.PACK_PA):self.uc.mem_write(at,self.initial[at])
        self.want={at:bytearray(raw) for at,raw in self.initial.items()}

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==old.TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
        assert len(self.pcs)<15000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        if ins.mnemonic=='break':assert off==0x13489c
        else:assert ins.mnemonic not in {'syscall','cache','sync','mfc0','mtc0','eret',
            'wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic)
        if off==0x66bb8:
            self.geometry_arguments.append({n:uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper())) for n in ('a0','a1','a2')})

    def run(self,label,entry,sp=SP_SEL,extra_stops=None,allow_interrupt=False,**regs):
        for name,value in {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,
                **{f's{i}':0 for i in range(8)},**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.geometry_arguments=[]
        self.stops={**STOPS,**(extra_stops or {})}
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        if allow_interrupt:assert self.reason=='native_interrupt' and self.interrupts==[18]
        else:assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
            'SP':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),'RA':hex(self.uc.reg_read(reg.UC_MIPS_REG_RA)),
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'native_geometry_helper_arguments':self.geometry_arguments,
            'original_image_all_pages_and_entire_stack_exact_poststate_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,
            'MMIO_instruction_patch_or_fake_return':False}

    def defaults(self):
        o=self.want[old.OWNER_PA]
        for off,value in ((0,0),(1,1),(2,1),(3,0),(4,0),(5,1),(6,1),(7,1),(8,2),
                          (0x14,2),(0x15,0),(0x16,0),(0x17,0),(0x24,0),(0x25,0),(0x26,0)):
            o[off]=value
        for off,value in ((0xc,16),(0x10,16),(0x18,1),(0x1c,0),(0x20,0)):
            struct.pack_into('<I',o,off,value)
        return self.run('complete original owner-default initializer',0x1352f0,a0=old.OWNER)

    def geometry_stack(self,before_sp,src,dst,old_s0,old_s1,old_s2,return_pc,classes):
        base=before_sp-0x40
        for off,value in ((0x30,old_s0),(0x34,old_s1),(0x38,return_pc),(0x10,base+0x21)):
            self.save(base+off,value)
        self.stack[base+0x20-old.STACK]=classes[0]
        self.stack[base+0x21-old.STACK]=classes[1]
        small=base-0x20
        self.save(small+0x10,dst);self.save(small+0x14,IMAGE+0x133894)
        layout=base-0x30
        for off,value in ((0x20,dst),(0x24,src),(0x28,IMAGE+0x1338a4)):self.save(layout+off,value)
        divide=layout-0x30
        for off,value in ((0x10,dst),(0x14,src),(0x18,old_s2),(0x1c,0),(0x20,IMAGE+0x134814)):
            self.save(divide+off,value)

    def expected_geometry(self,units,mode):
        # Reference for these explicit fixtures; no claim about actual input
        # mode semantics or the final visible/cropped recording dimensions.
        width=units[0]*16;height=units[1]*(16 if mode else 32)
        classes=(4,4 if width*height>0x1fe000 else 2)
        exponents=(2,2 if classes[1]==4 else 1)
        data=bytes([exponents[0],exponents[1],0,0,
                    (units[0]+(1<<exponents[0])-1)>>exponents[0],
                    (units[1]+(1<<exponents[1])-1)>>exponents[1],0,1])
        self.want[old.OWNER_PA][8:16]=data
        return data,classes,(width,height)

    def classify_and_build(self,units,mode):
        base=SP_SEL-0x60
        for off in (0x50,0x54,0x58):self.save(base+off,0)
        self.save(base+0x5c,old.TRAP)
        struct.pack_into('<I',self.want[old.OWNER_PA],0x9c,mode)
        data,classes,dimensions=self.expected_geometry(units,mode)
        self.geometry_stack(base,old.SRC,old.OWNER+8,old.SRC,base+0x20,old.OWNER,IMAGE+0x1315d0,classes)
        e=self.run('original raw mode classification and complete geometry builder to caller',
                   0x131590,a0=old.OWNER,a1=old.SRC)
        assert e['stop']==STOPS[0x1315d0]
        assert e['SP']==hex(base) and e['RA']==hex(IMAGE+0x1315d0)
        assert [(x['a0'],x['a1']) for x in e['native_geometry_helper_arguments']]==[dimensions]
        return e,data

    def caller(self,units,mode,flag):
        self.save(SP_CALL+0x20,old.HANDLES)
        # This is the only caller input placed on its otherwise original stack.
        self.uc.mem_write(old.STACK_PA+SP_CALL+0x20-old.STACK,struct.pack('<I',old.HANDLES))
        if flag:
            self.save(SP_CALL-0x10,IMAGE+0x1441c8);self.save(SP_CALL-0x30,IMAGE+0x134fa0)
            struct.pack_into('<HH',self.want[old.OWNER_PA],0x24,*units)
            data,classes,dimensions=self.expected_geometry(units,mode)
            self.geometry_stack(SP_CALL-0x40,old.OWNER+0x10,old.OWNER+8,
                                0,old.SRC,old.INSTANCE,IMAGE+0x131e68,classes)
        else:dimensions=None
        # Native wrapper and producer saves occur after all geometry returns.
        self.save(SP_CALL-0x10,IMAGE+0x1441d8)
        base=SP_CALL-0x80
        for off in (0x40,0x4c,0x50,0x54,0x58):self.save(base+off,0)
        self.save(base+0x44,old.SRC);self.save(base+0x48,old.INSTANCE);self.save(base+0x5c,IMAGE+0x1351c0)
        e=self.run('actual original caller through complete geometry returns and original frame wrapper',
                   0x144124,sp=SP_CALL,s1=old.SRC,s2=old.INSTANCE)
        assert e['stop']==STOPS[0x131888] and e['SP']==hex(base) and e['RA']==hex(IMAGE+0x1351c0)
        assert self.uc.reg_read(reg.UC_MIPS_REG_S0)==old.FRAME
        assert self.uc.reg_read(reg.UC_MIPS_REG_S1)==old.OWNER and self.uc.reg_read(reg.UC_MIPS_REG_S4)==old.SRC
        assert [(x['a0'],x['a1']) for x in e['native_geometry_helper_arguments']]==([dimensions] if flag else [])
        return e


def calibration(blob):
    rows=[]
    for divisor in (2,4,0):
        m=Guest(blob,0xa5,1,0x10,(120,68));m.want[old.OWNER_PA][8]=0
        e=m.run('original geometry DIVU/BEQL/BREAK observer calibration',0x134890,
            s0=121,v0=divisor,s2=old.OWNER+8,s3=old.OWNER+9,
            extra_stops={0x1348a0:'before_original_quotient_consumption'},allow_interrupt=divisor==0)
        assert hex(IMAGE+0x13489c) in e['CODE_observed_PCs']
        if divisor:
            assert m.uc.reg_read(reg.UC_MIPS_REG_LO)==121//divisor
            assert m.uc.reg_read(reg.UC_MIPS_REG_HI)==121%divisor
        rows.append({'numerator':121,'declared_divisor':divisor,'event':e})
    return rows


def one(blob,seed,mode,flag,units):
    m=Guest(blob,seed,mode,flag,units);es=[m.defaults()]
    e,data=m.classify_and_build(units,mode);es.append(e)
    es.append(m.caller(units,mode,flag))
    return {'seed':seed,'declared_raw_mode_byte0e':mode,'declared_raw_byte10':0,
        'declared_update_byte50':flag,'declared_units':list(units),
        'native_owner_mode9c':old.word(m.want[old.OWNER_PA],0x9c),
        'native_geometry8_hex':data.hex(),'final_pages':{hex(at):m.read(at).hex() for at in m.want},
        'events':es,'full_geometry_return_and_actual_JAL_frame_binding':True,
        'outer_mode_setup_message_work_and_actual_scheduling_completed':False,
        'real_MAIN_cropped_dimensions_hardware_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage91-native-type4-first-cache-buffer/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    path=prev.prev.prev.old.old.prev.a.prev.p.a.v.VCD_PATH
    blob=path.read_bytes();assert im.sha(blob)==im.PINS[str(path.relative_to(BASE))]
    assert old.app_gp(blob)==old.GP and blob[0x24817a:0x24817c]==bytes([1,2])
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    cases=[]
    try:
        probes=calibration(blob)
        for seed in (0xa5,0xc3):
            for mode in (1,0):
                for flag in (0,0x10):cases.append(one(blob,seed,mode,flag,(120,68)))
        cases.append(one(blob,0xa5,1,0x10,(119,67)))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_NATIVE_COMPLETE_GEOMETRY_BUILDER_RETURNS_THROUGH_ACTUAL_FRAME_CALLER',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),'prior_manifest_sha256':PRIOR_SHA},
        'observer_calibration':probes,'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'scope':'Native owner defaults and raw-mode9c classification; full pure geometry helper and actual setter return/JAL chain. '
            'Raw metadata, existing owned frame/buffer and outer caller context declared. Source mode-setup message work, '
            'full frame header, real queue/MAIN, cropped 1080 dimensions, hardware, IRQ and recovery not proven.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'geometry-builder-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'phases':j['bounded_phases'],'calibrations':len(probes),'output':str(out)}))


if __name__=='__main__':main()
