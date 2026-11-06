#!/usr/bin/env python3
"""Original trace descriptor initialization, then real mode code to MMIO boundary.

No trace disable, synthetic timer, CACHE implementation or mode-return injection.
"""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage97-native-owner-construction-and-mode-dispatch'))
import owner_mode as prev
old=prev.old
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='014f8c61bac623be15fdba01f6f11290227ac1ba26a3cd29fe4c65104495df26'
BSS_PA,BSS_SIZE=0x00a72000,0x3b000
SP_TRACE=old.STACK+0x4000
TABLE=0x214148
TRACE_CONTROL=0x80a8f07c
TRACE_END=0x80a8fc84
STOPS={**prev.STOPS,0x61ffc:'original_all_trace_buffers_initialized_before_unexecuted_CACHE',
    0x12f880:'original_mode_trace_state_consumed_before_unexecuted_hardware_timer_read'}


class Guest(prev.Guest):
    def __init__(self,blob,metadata,seed,selected,e,ten):
        super().__init__(blob,metadata,seed,selected,e,ten)
        self.uc.mem_map(BSS_PA,BSS_SIZE,u.UC_PROT_READ|u.UC_PROT_WRITE)
        raw=bytes([seed])*BSS_SIZE;self.uc.mem_write(BSS_PA,raw)
        self.want[BSS_PA]=bytearray(raw);self.sizes[BSS_PA]=BSS_SIZE;self.trace_decode={}
        self.descriptors=[struct.unpack_from('<10I',blob,TABLE+i*40) for i in range(69)]

    def code(self,uc,pc,size,user):
        off=pc-IMAGE
        if 0x61f3c<=off<=0x61ffc or 0x62090<=off<0x620c0 or 0x67f08<=off<0x67fa8 or 0x12f84c<=off<=0x12f880:
            self.pcs.append(pc)
            if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
            assert len(self.pcs)<300000
            ins=self.trace_decode.get(pc)
            if ins is None:
                ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
                assert ins is not None,hex(pc);self.trace_decode[pc]=ins
            assert ins.mnemonic not in {'break','syscall','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic)
        else:super().code(uc,pc,size,user)

    def run(self,label,entry,sp=prev.prev.SP_FACTORY,preserve=False,**regs):
        if entry==0x7a304:regs['s4']=self.owner
        initial={} if preserve else {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**initial,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.indirect=[];self.entries=[]
        self.stops=dict(STOPS)
        self.stops.pop(entry,None)
        self.uc.emu_start(IMAGE+entry,0,timeout=20000000,count=0)
        assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        image=bytearray(self.blob)
        for at,value in {prev.prev.prev.prev.CELL:self.cell,**self.image_words}.items():struct.pack_into('<I',image,at,value)
        assert bytes(self.uc.mem_read(0,len(self.blob)))==bytes(image)
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        compressed=entry==0x61f3c
        counts=collections.Counter(self.pcs)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            **{n.upper():hex(self.uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('pc','sp','ra','v0','a1','a2','v1','t0')},
            'CODE_observed_PCs':[hex(p) for p in sorted(counts)] if compressed else [hex(p) for p in self.pcs],
            'CODE_total_observations':len(self.pcs),'CODE_trace_compressed_to_unique_PCs':compressed,
            'CODE_pc_counts':{hex(p):n for p,n in sorted(counts.items())} if compressed else None,
            'CODE_ordered_trace_sha256':hashlib.sha256(b''.join(struct.pack('<I',p) for p in self.pcs)).hexdigest(),
            'indirect_calls':self.indirect,'native_entries':self.entries,'owner_constructor_snapshot':self.constructor_snapshot,
            'image_all_regions_and_entire_stack_exact_poststate_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,'MMIO_instruction_patch_or_fake_return':False}

    def init_trace(self):
        b=self.want[BSS_PA];intervals=[]
        for i,r in enumerate(self.descriptors):
            assert r[0]==i
            if not r[1]:continue
            at=r[1]-IMAGE-BSS_PA;n=16 if i==0 else r[2]*r[3]+8
            assert at>=0 and at+n<=BSS_SIZE
            b[at:at+n]=bytes(n)
            if i==0:b[at:at+12]=self.blob[0x247380:0x247388]+self.blob[0x24738c:0x247390]
            else:struct.pack_into('<I',b,at,r[1]+8)
            intervals.append((r[1],r[1]+n))
        assert all(a1==b0 for (_,a1),(b0,_) in zip(intervals,intervals[1:]))
        base=SP_TRACE-0x40
        for off,value in ((0x28,0),(0x20,0),(0x30,old.TRAP),(0x2c,0),(0x24,0)):self.save(base+off,value)
        event=self.run('original69-entry trace table initializes62 buffers to CACHE boundary',0x61f3c,sp=SP_TRACE)
        assert event['stop']==STOPS[0x61ffc]
        at=TRACE_CONTROL-IMAGE-BSS_PA
        assert old.word(b,at)==TRACE_CONTROL+8 and b[at+4:at+8]==bytes(4)
        return event

    def resume_real_trace(self):
        event=self.run('same original mode handler consumes natively initialized trace state',0x12f84c,preserve=True)
        assert event['stop']==STOPS[0x12f880]
        assert event['A2']==hex(TRACE_CONTROL+8) and event['A1']==hex(TRACE_CONTROL+12)
        assert event['T0']==hex(TRACE_END)
        assert event['V1']==hex(TRACE_CONTROL+0x20)
        return event


def one(blob,metadata,seed,selected,e,ten):
    m=Guest(blob,metadata,seed,selected,e,ten)
    es=[m.init_trace(),m.heap_init(),m.allocate_owner(),m.factory_suffix(),m.select()]
    event,flag,flagword=m.continue_mode_callback();es.append(event);es.append(m.resume_real_trace())
    at=TRACE_CONTROL-IMAGE-BSS_PA
    return {'seed':seed,'declared_selector_byte':selected,'declared_mode_payload0e':e,'declared_mode_payload10':ten,
        'native_owner':hex(m.owner),'native_local_control_flag':flag,'native_history_flag_word':hex(flagword),
        'native_trace_cursor':hex(old.word(m.want[BSS_PA],at)),'native_trace_flag4':m.want[BSS_PA][at+4],
        'native_trace_wrap5':m.want[BSS_PA][at+5],
        'events':es,'final_regions':{hex(p):bytes(raw).hex() for p,raw in m.want.items()},
        'trace_initializer_CACHE_and_tail_unexecuted':True,'trace_disable_or_timer_value_injected':False,
        'complete_boot_mode_MAIN_video_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage97-native-owner-construction-and-mode-dispatch/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source=prior.parent/'run-corrected-resume-boundary-20261027/owner-mode-results.json'
    case=json.loads(source.read_text())['cases'][0];pool=bytes.fromhex(case['final_regions'][hex(prev.prev.prev.prev.POOL_PA)])
    at=prev.prev.prev.prev.PHYS4-prev.prev.prev.prev.POOL_PA+0xec;metadata=pool[at:at+48]
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==im.PINS[str(path.relative_to(BASE))]
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());cases=[]
    try:
        for seed in (0xa5,0xc3):
            for selected in (0,1):
                for e,ten in ((0,0),(1,0),(1,1)):
                    cases.append(one(blob,metadata,seed,selected,e,ten))
                    print(json.dumps({'completed_cases':len(cases)}),flush=True)
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_NATIVE_TRACE_DESCRIPTOR_INITIALIZATION_AND_MODE_LOG_PATH_TO_ACTUAL_MMIO_BOUNDARY',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage97_result_sha256':im.sha(source.read_bytes())},
        'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'trace-origin-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
