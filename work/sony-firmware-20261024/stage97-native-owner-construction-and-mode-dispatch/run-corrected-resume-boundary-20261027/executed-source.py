#!/usr/bin/env python3
"""Original manager owner allocation/constructor and natural mode table dispatch.

Correct the earlier local-parameter-initializer role. Stop at the first trace
global read, without disabling trace or supplying MMIO. Factory callback gap
and pre-binding heap state remain explicit; no real MAIN acceptance.
"""
from pathlib import Path
import argparse,datetime,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage96-native-bootstrap-and-manager-routing'))
import manager_routing as prev
old=prev.old
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='cfa14417f6b910fc678ddb8b5952e5c6f6f58db96a8983f3c001c80a30787558'
STOPS={**prev.STOPS,0x7a2d4:'original_owner_allocation_and_constructor_return_before_callback_object_factory',
    0x12f84c:'native_mode_owner_history_stored_before_first_unbound_trace_global_read'}
LIMITS=prev.LIMITS+((0x7a2ac,0x7a2d4),(0x12f21c,0x12f2e8),(0x1f3858,0x1f399c),
    (0x7af58,0x7af60),(0x143f38,0x143f7c),(0x134d40,0x134dbc),(0x12f7dc,0x12f84c))


def owner_initial_bytes(seed,address,id0,id2):
    o=bytearray([seed])*0xf2c
    struct.pack_into('<HHI',o,0,id0,id2,0);o[8:0x10]=bytes(8)
    raw=bytearray(0x70);raw[0]=255;raw[0xf]=raw[0x10]=raw[0x6e]=1;raw[0x11]=6
    o[0x10:0x80]=raw;o[0x80]=0;o[0x94]=1
    for off in (0x84,0x88,0x8c,0x90,0x98,0x9c,0x19c,0x198,0x1a8,0x1a0,0x1a4,0xf28,0xf24):struct.pack_into('<I',o,off,0)
    for off,value in ((0x190,address+0xa0),(0x194,address+0xa0),(0xf1c,address+0xecc),(0xf20,address+0xecc)):
        struct.pack_into('<I',o,off,value)
    return bytes(o)


class Guest(prev.Guest):
    def __init__(self,blob,metadata,seed,selected,e,ten):
        super().__init__(blob,metadata,seed,1,selected,True,False)
        self.id0,self.id2=(0,0) if seed==0xa5 else (17,33)
        source=self.want[old.SRC_PA];struct.pack_into('<H',source,0,self.id0);struct.pack_into('<H',source,4,self.id2)
        self.uc.mem_write(old.SRC_PA,bytes(source))
        message=self.want[prev.MSG_PA];message[0x16]=e;message[0x18]=ten
        self.history=(0x11223344,0x89abcdef,0xfedcba98) if seed==0xa5 else (0xa1b2c3d4,0x76543210,0x01020304)
        struct.pack_into('<3I',message,0x30,*self.history);self.uc.mem_write(prev.MSG_PA,bytes(message))
        self.owner=None;self.mode_e,self.mode_ten=e,ten;self.constructor_snapshot=None

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==old.TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off==0x7a2cc:
            assert self.owner is not None
            raw=bytes(uc.mem_read(self.owner-IMAGE,0xf2c))
            assert raw==owner_initial_bytes(self.seed,self.owner,self.id0,self.id2)
            self.constructor_snapshot={'point':'native_owner_constructor_return_to_original_manager',
                'owner':hex(self.owner),'sha256':im.sha(raw),'native_dispatch_index4':old.word(raw,4)}
        if off==0x12f7dc:
            self.entries.append({'point':'native_owner_mode_handler_entry',
                **{n:hex(uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('a0','a1','sp','ra')}})
        if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
        assert len(self.pcs)<20000 and any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None);assert ins is not None,hex(pc)
        assert ins.mnemonic not in {'break','syscall','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'},(hex(pc),ins.mnemonic)
        if ins.mnemonic=='jalr':
            register=reg.UC_MIPS_REG_V1 if off==0x134da8 else reg.UC_MIPS_REG_V0
            target=uc.reg_read(register)
            expected={0x7af58:IMAGE+0x143f38,0x134da8:IMAGE+0x12f7dc}
            assert off in expected and target==expected[off],(hex(pc),hex(target))
            self.indirect.append({'call_PC':hex(pc),'target':hex(target),
                'A0_before_delay':hex(uc.reg_read(reg.UC_MIPS_REG_A0)),'A1':hex(uc.reg_read(reg.UC_MIPS_REG_A1))})

    def run(self,label,entry,sp=prev.SP_FACTORY,preserve=False,**regs):
        # The original manager callback-object construction remains an explicit
        # gap. Its declared S3=0 is not evidence of a valid runtime callback.
        if entry==0x7a304:regs['s4']=self.owner
        initial={} if preserve else {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**initial,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.indirect=[];self.entries=[]
        self.stops=dict(STOPS)
        if entry==0x7af58:self.stops.pop(0x7af58)
        self.uc.emu_start(IMAGE+entry,0,timeout=2000000,count=0)
        assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        image=bytearray(self.blob)
        for at,value in {prev.prev.prev.CELL:self.cell,**self.image_words}.items():struct.pack_into('<I',image,at,value)
        assert bytes(self.uc.mem_read(0,len(self.blob)))==bytes(image)
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            **{n.upper():hex(self.uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('pc','sp','ra','v0')},
            'CODE_observed_PCs':[hex(p) for p in self.pcs],'indirect_calls':self.indirect,'native_entries':self.entries,
            'owner_constructor_snapshot':self.constructor_snapshot,
            'image_all_regions_and_entire_stack_exact_poststate_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,'MMIO_instruction_patch_or_fake_return':False}

    def allocate_owner(self):
        self.owner=self.allocate_expected(0xf2c,prev.SP_FACTORY,IMAGE+0x7a2b8,0,old.SRC)
        assert self.owner==prev.prev.HEAP+0x10
        h=self.want[prev.prev.HEAP_PA];at=self.owner-prev.prev.HEAP
        h[at:at+0xf2c]=owner_initial_bytes(self.seed,self.owner,self.id0,self.id2)
        child=prev.SP_FACTORY-0x20
        self.save(child+0x10,0);self.save(child+0x14,IMAGE+0x7a2cc)
        struct.pack_into('<I',self.want[prev.MGR_PA],0x10,self.owner);self.want[prev.MGR_PA][0xc]=0
        e=self.run('original manager allocates f2c owner and calls actual owner constructor',0x7a2ac,
                   s0=0,s1=old.SRC,s2=prev.MGR)
        assert e['stop']==STOPS[0x7a2d4] and self.constructor_snapshot is not None
        return e

    def initialize_object_expected(self,obj,private,kind):
        super().initialize_object_expected(obj,private,kind)
        struct.pack_into('<I',self.want[prev.prev.HEAP_PA],obj-prev.prev.HEAP+4,self.owner)

    def continue_mode_callback(self):
        object_address=old.word(self.want[prev.MGR_PA],0x20)
        flag=int(self.mode_e==1 and self.mode_ten==0)
        h=self.want[prev.prev.HEAP_PA]
        struct.pack_into('<I',h,object_address-prev.prev.HEAP+0x10,flag)
        # Original selector, base-object wrapper, owner wrapper and owner
        # handler retain one continuous CPU/stack state across the stop.
        self.save(prev.SP_SELECT-0x60,IMAGE+0x7af60)
        self.save(prev.SP_SELECT-0x80,IMAGE+0x143f5c)
        body=prev.SP_SELECT-0xf0
        for off,value in ((0x54,prev.MSG),(0x50,prev.MGR),(0x58,IMAGE+0x134db0)):self.save(body+off,value)
        scratch=body+0x10-old.STACK
        self.stack[scratch]=1;flagword=old.word(self.stack,scratch)
        for off,value in ((0x14,self.history[0]),(0x18,self.history[1]),(0x1c,self.history[2]),(0x20,0)):
            self.save(body+off,value)
        owner_at=self.owner-prev.prev.HEAP
        struct.pack_into('<5I',h,owner_at+0x80,flagword,*self.history,0)
        struct.pack_into('<I',h,owner_at+0x98,0)
        e=self.run('continuous original selected mode callback and native owner-table dispatch',0x7af58,preserve=True)
        assert e['stop']==STOPS[0x12f84c]
        assert [x['target'] for x in e['indirect_calls']]==[hex(IMAGE+0x143f38),hex(IMAGE+0x12f7dc)]
        assert e['native_entries']==[{'point':'native_owner_mode_handler_entry','a0':hex(self.owner),
            'a1':hex(prev.MSG+8),'sp':hex(prev.SP_SELECT-0x90),'ra':hex(IMAGE+0x134db0)}]
        return e,flag,flagword


def one(blob,metadata,seed,selected,e,ten):
    m=Guest(blob,metadata,seed,selected,e,ten);es=[m.heap_init(),m.allocate_owner(),m.factory_suffix(),m.select()]
    event,flag,flagword=m.continue_mode_callback();es.append(event)
    owner_at=m.owner-prev.prev.HEAP;h=m.want[prev.prev.HEAP_PA]
    return {'seed':seed,'declared_selector_byte':selected,'declared_mode_payload0e':e,'declared_mode_payload10':ten,
        'declared_constructor_ids':[m.id0,m.id2],'declared_history_words':list(m.history),
        'native_owner_VA':hex(m.owner),'native_owner_index4':old.word(h,owner_at+4),
        'native_controller_flag10':flag,'native_stored_history_flag_word':hex(flagword),
        'objects':{k:hex(v) for k,v in m.objects.items()},'current_manager_pointer':hex(old.word(m.want[prev.MGR_PA],0x20)),
        'native_allocations':m.allocations,'owner_after_hex':bytes(h[owner_at:owner_at+0xf2c]).hex(),
        'final_regions':{hex(at):bytes(raw).hex() for at,raw in m.want.items()},'events':es,
        'explicit_gaps':['manager callback-object allocation/construction7a2d4..7a300',
            'normal boot and heap callback binding','first trace global/MMIO and remaining owner mode handler'],
        'normal_mode_callback_return_MAIN_video_hardware_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage96-native-bootstrap-and-manager-routing/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source=prior.parent/'run-initial-20261027/manager-routing-results.json'
    case=json.loads(source.read_text())['cases'][0];pool=bytes.fromhex(case['final_regions'][hex(prev.prev.prev.POOL_PA)])
    at=prev.prev.prev.PHYS4-prev.prev.prev.POOL_PA+0xec;metadata=pool[at:at+48]
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==im.PINS[str(path.relative_to(BASE))]
    assert struct.unpack_from('<II',blob,old.GP-IMAGE-0x6a94)==(IMAGE+0x12f7dc,0)
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());cases=[]
    try:
        for seed in (0xa5,0xc3):
            for selected in (0,1):
                for e,ten in ((0,0),(1,0),(1,1)):cases.append(one(blob,metadata,seed,selected,e,ten))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_ACTUAL_OWNER_CONSTRUCTOR_AND_NATIVE_ZERO_INDEX_MODE_DISPATCH_TO_TRACE_BOUNDARY',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage96_result_sha256':im.sha(source.read_bytes())},
        'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'earlier1352f0_is_not_complete_GOP_owner_constructor':True,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'owner-mode-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
