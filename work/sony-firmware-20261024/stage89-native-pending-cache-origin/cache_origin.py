#!/usr/bin/env python3
"""Bounded native pending-cache initialization and existing-buffer relay.

The raw metadata, already owned handles and scheduling remain declared inputs.
No fresh buffer allocation, refcount change, backend merge or ACK is simulated.
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
sys.path.insert(0,str(BASE/'stage88-native-frame-publication-and-gop-gate'))
import gate_event as old
im,u,reg,cs,IMAGE=old.im,old.u,old.reg,old.cs,old.IMAGE
PRIOR_SHA='9104b8d2f6a5abb8a2470d3cfbfeac4da25fccaac15ecb8bbdfcf318cdf0914a'
SOURCEFRAME_PA,SOURCEFRAME=0x01e00000,0x81e00000
SOURCEPACK_PA,SOURCEPACK=0x01f00000,0x81f00000
OWNER_PA,OWNER=0x01100000,0x81100000
RAW_PA,RAW=0x01000000,0x81000000
PRODUCER_SP,WORK_SP=0x82006000,0x8200a000
LIMITS=old.LIMITS+((0x1351b0,0x1351c0),(0x131818,0x131888),
    (0x131b38,0x131b68),(0x1409fc,0x140a58),(0x140c08,0x140d04),
    (0x140de4,0x140e64),(0x13c2d8,0x13c31c),(0x13c434,0x13c43c))
STOPS={**old.STOPS,
    0x131888:'source_frame_pointer_bound_before_unexecuted_header_work',
    0x131ca8:'same_owned_handle_before_unexecuted_backend_merge',
    0x131cb8:'raw_update_bit_off_before_other_frame_header_store',
    0x131b68:'different_handle_before_unknown_GP_refcount_work',
    0x140d04:'pending_bit_set_before_unknown_GP_new_cache_allocation',
    0x140e64:'after_cache_bit_check_or_copy_before_backend_transfer',
    0x13c31c:'empty_eight_byte_record_initialized_before_other_constructor_work',
    0x13c408:'insufficient_declared_arena_before_following_constructor_work'}
word=old.word
DATA=(old.GOP_PA,old.INFRAME_PA,old.OUTFRAME_PA,old.INPACK_PA,old.OUTPACK_PA,
      old.DESC_PA,old.HANDLE_PA,old.MANAGER_PA,old.RECORD_PA,old.BACKEND_PA,old.PAYLOAD_PA)


class Guest(old.Guest):
    def __init__(self,blob,source):
        super().__init__(blob,source,0)
        for at in (old.RECORD_PA,old.PAYLOAD_PA):
            self.uc.mem_protect(at,4096,u.UC_PROT_READ|u.UC_PROT_WRITE)
        self.immutable=[old.DESC_PA,old.HANDLE_PA,old.BACKEND_PA]
        self.stack_expected=bytearray([0xd7])*65536

    def replace(self,at,raw):
        self.initial[at]=bytes(raw);self.uc.mem_write(at,bytes(raw))

    def code(self,uc,pc,size,user):
        self.pcs.append(pc);off=pc-IMAGE
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<20000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0','eret',
            'wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic)

    def run(self,label,entry,preserve=False,**regs):
        init={} if preserve else {'sp':WORK_SP,'ra':0x83000000}
        for name,value in {**init,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in STOPS.values() and not self.interrupts,self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack_expected
        for at in self.immutable:assert self.read(at)==self.initial[at],hex(at)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
            'sp':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
            'ra':hex(self.uc.reg_read(reg.UC_MIPS_REG_RA)),
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'original_image_immutable_inputs_and_exact_expected_full_stack_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,
            'MMIO_code_replacement_or_fake_return':False}

    def check(self,want):
        for at,raw in want.items():assert self.read(at)==bytes(raw),hex(at)


def initialize_record(blob,source,available):
    m=Guest(blob,source);seed=source['seed'];cursor=0x20
    manager=bytearray(m.initial[old.MANAGER_PA])
    struct.pack_into('<III',manager,0,old.RECORD,cursor+available,cursor)
    struct.pack_into('<I',manager,0xc90,0xa6a6a6a6)
    arena=bytearray([seed])*4096
    m.replace(old.MANAGER_PA,manager);m.replace(old.RECORD_PA,arena)
    want={at:bytearray(m.initial[at]) for at in DATA}
    success=available>=8
    if success:
        struct.pack_into('<I',want[old.MANAGER_PA],8,cursor+8)
        struct.pack_into('<I',want[old.MANAGER_PA],0xc90,old.RECORD+cursor)
        want[old.RECORD_PA][cursor]=0
        struct.pack_into('<I',want[old.RECORD_PA],cursor+4,0)
    else:struct.pack_into('<I',want[old.MANAGER_PA],0xc90,0)
    event=m.run('native eight-byte pending-record arena allocation and zero initialization',
                0x13c2d8,s1=old.MANAGER)
    assert event['stop']==STOPS[0x13c31c if success else 0x13c408]
    m.check(want)
    return {'seed':seed,'declared_available_bytes':available,'cursor_before':cursor,
        'manager_after_hex':m.read(old.MANAGER_PA).hex(),
        'arena_after_hex':m.read(old.RECORD_PA).hex(),
        'record_after_hex':m.read(old.RECORD_PA)[cursor:cursor+8].hex() if success else None,
        'record_handle_is_null':success,'events':[event],
        'kernel_or_cache_payload_allocation_or_full_constructor_completed':False}


def relay(blob,source,event,kind):
    m=Guest(blob,source)
    for at,prot in ((SOURCEFRAME_PA,u.UC_PROT_READ|u.UC_PROT_WRITE),
                    (SOURCEPACK_PA,u.UC_PROT_READ),(OWNER_PA,u.UC_PROT_READ),(RAW_PA,u.UC_PROT_READ)):
        m.uc.mem_map(at,4096,prot)
    raw=bytearray([0x75])*4096;raw[0x50]=event
    struct.pack_into('<I',raw,0x54,old.HANDLE+(12 if kind=='different_source_handle' else 20))
    owner=bytearray([0x81])*4096;struct.pack_into('<H',owner,0x28,0x4321)
    sourceframe=bytearray([0x93])*4096;sourceframe[0x4c4]=0
    struct.pack_into('<I',sourceframe,0x4c8,old.HANDLE+20)
    sourcepack=bytearray([0x94])*4096;sourcepack[0xec:0x11c]=m.metadata
    handles=bytearray(m.initial[old.HANDLE_PA]);struct.pack_into('<II',handles,16,SOURCEFRAME_PA,SOURCEPACK_PA)
    desc=bytearray(m.initial[old.DESC_PA]);struct.pack_into('<I',desc,0x110,old.HANDLE+16)
    payload=bytearray(m.initial[old.PAYLOAD_PA]);payload[0xec:0x11c]=bytes([0x37])*48
    record=bytearray(m.initial[old.RECORD_PA])
    if kind=='missing_cache_handle':struct.pack_into('<I',record,4,0)
    for at,buf in ((RAW_PA,raw),(OWNER_PA,owner),(SOURCEFRAME_PA,sourceframe),
                   (SOURCEPACK_PA,sourcepack),(old.HANDLE_PA,handles),(old.DESC_PA,desc),
                   (old.PAYLOAD_PA,payload),(old.RECORD_PA,record)):m.replace(at,buf)
    m.immutable += [RAW_PA,OWNER_PA,SOURCEPACK_PA]
    want={at:bytearray(m.initial[at]) for at in DATA+(SOURCEFRAME_PA,SOURCEPACK_PA,OWNER_PA,RAW_PA)}
    events=[];snapshots=[]
    # Exact expected native saves: wrapper plus producer. The intervening body
    # remains unexecuted. The original frame and return address are preserved.
    frame=PRODUCER_SP-0x80
    struct.pack_into('<I',m.stack_expected,PRODUCER_SP-0x10-(old.STACK_PA+IMAGE),0x83000000)
    for off in (0x40,0x44,0x48,0x4c,0x50,0x54,0x58):
        struct.pack_into('<I',m.stack_expected,frame+off-(old.STACK_PA+IMAGE),0)
    struct.pack_into('<I',m.stack_expected,frame+0x5c-(old.STACK_PA+IMAGE),IMAGE+0x1351c0)
    events.append(m.run('original wrapper JAL and producer descriptor-to-frame pointer binding',
        0x1351b0,sp=PRODUCER_SP,a0=OWNER,a1=old.DESC+0x100,a2=RAW,
        **{f's{i}':0 for i in range(7)}))
    assert events[-1]['stop']==STOPS[0x131888]
    assert m.uc.reg_read(reg.UC_MIPS_REG_S0)==SOURCEFRAME
    assert m.uc.reg_read(reg.UC_MIPS_REG_S1)==OWNER and m.uc.reg_read(reg.UC_MIPS_REG_S4)==RAW
    assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==frame and m.uc.reg_read(reg.UC_MIPS_REG_RA)==IMAGE+0x1351c0
    m.check(want)
    events.append(m.run('original raw metadata update byte and identical-owned-handle check',0x131b38,preserve=True))
    if event:want[SOURCEFRAME_PA][0x4c4]=event
    expected_stop=0x131b68 if kind=='different_source_handle' else (0x131ca8 if event else 0x131cb8)
    assert events[-1]['stop']==STOPS[expected_stop]
    assert events[-1]['sp']==hex(frame) and events[-1]['ra']==hex(IMAGE+0x1351c0)
    m.check(want)
    snapshots.append({'phase':'source_metadata_to_frame','source_frame_bit4':bool(event),
                      'cache_record_bit4':False,'GOP_gate':False})
    copied=False;before_pack=None
    if kind!='different_source_handle':
        events.append(m.run('original frame-descriptor load, counter increment and pending-cache writer',
                            0x1409fc,s2=old.MANAGER,s4=old.DESC+0x100))
        struct.pack_into('<H',want[old.MANAGER_PA],0xca0,0x1235)
        if event:want[old.RECORD_PA][0]|=0x10
        if event and kind!='missing_cache_handle':want[old.PAYLOAD_PA][0xec:0x11c]=m.metadata
        assert events[-1]['stop']==STOPS[0x140d04 if kind=='missing_cache_handle' else 0x140e64]
        m.check(want)
        snapshots.append({'phase':'cache_writer','cache_record_bit4':bool(event),
            'cache_payload_copied':bool(event) and kind!='missing_cache_handle','GOP_gate':False})
        if kind!='missing_cache_handle':
            events.append(m.run('original backend predicate and cached-record publication',
                                0x141128,s2=old.MANAGER,s4=old.DESC))
            struct.pack_into('<H',want[old.INFRAME_PA],0xe0,0x1235)
            if event:
                want[old.INFRAME_PA][0x4c4]|=0x10;want[old.INPACK_PA][0xec:0x11c]=m.metadata
            assert events[-1]['stop']==old.STOPS[0x141664 if event else 0x141668]
            m.check(want)
            snapshots.append({'phase':'published_cached_record','input_frame_bit4':bool(event),'GOP_gate':False})
            events.append(m.run('original HEVC metadata ingestion after unexecuted common callback',
                                0xd9000,s0=old.GOP,s3=old.INFRAME))
            gop=want[old.GOP_PA]
            if event:
                gop[0xbf4:0xc24]=m.metadata;gop[0x7c:0x80]=m.metadata[:4]
                struct.pack_into('<I',gop,0x84,(word(gop,0x84)&~(1<<15))|((m.metadata[5]&1)<<15))
                gop[0x8b]=m.metadata[6];gop[0xe0:0xe4]=m.metadata[8:12]
                struct.pack_into('<I',gop,0xd8,(word(gop,0xd8)&~15)|(m.metadata[12]&15))
                struct.pack_into('<I',gop,0xe8,word(gop,0xe8)|1);gop[0xf4:0x114]=m.metadata[16:48]
            assert events[-1]['stop']==old.STOPS[0xd9110 if event else 0xd9204]
            m.check(want)
            snapshots.append({'phase':'HEVC_ingestion','GOP_gate':bool(event)})
            before_pack=bytes(gop)
            events.append(m.run('original GOP gate test, output copy, flag publication and gate clear',
                                0xd95a4,s1=old.GOP,s2=old.OUTFRAME))
            if event:
                want[old.OUTPACK_PA][0x14:0xb0]=gop[0x78:0x114]
                want[old.OUTPACK_PA][0xec:0x11c]=gop[0xbf4:0xc24]
                want[old.OUTFRAME_PA][0x4c4]|=0x10
                struct.pack_into('<I',gop,0xe8,word(gop,0xe8)&~1);copied=True
            assert events[-1]['stop']==old.STOPS[0xd98b8 if event else 0xd98c0]
            m.check(want)
            snapshots.append({'phase':'gated_output','GOP_gate':False,'output_frame_bit4':bool(event)})
    return {'seed':source['seed'],'source_kind':source['kind'],'source_label':source['source_label'],
        'kind':kind,'declared_raw_metadata_flag':event,'metadata48_hex':m.metadata.hex(),
        'source_GOP_hex':m.gop.hex(),'GOP_before_pack_hex':before_pack.hex() if before_pack else None,
        'final_pages':{hex(at):m.read(at).hex() for at in want},
        'source_native_saved_frame_preserved':True,'source_saved_frame_sha256':im.sha(m.stack_expected),
        'snapshots':snapshots,'events':events,
        'decoded_output_target':old.old.prev.a.prev.p.a.decode(word(want[old.OUTPACK_PA],0x64)) if copied else None,
        'host_sets_source_frame_cache_record_or_GOP_update_bit':False,
        'raw_metadata_real_producer_refcount_backend_merge_or_scheduling_executed':False,
        'module_ACK_MAIN_hardware_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage88-native-frame-publication-and-gop-gate/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source_path=BASE/'stage86-hevc-vui-mode-conversion/run-20261026/vui-mode-results.json'
    sources=json.loads(source_path.read_text())['cases']
    get=lambda seed,kind:next(c for c in sources if c['seed']==seed and c['kind']==kind and c['source_label']=='selected1_raw5')
    blob_path=old.old.prev.a.prev.p.a.v.VCD_PATH
    blob=blob_path.read_bytes();assert im.sha(blob)==im.PINS[str(blob_path.relative_to(BASE))]
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    arena=[];cases=[]
    try:
        for seed in (0xa5,0xc3):
            for available in (0,7,8,16):arena.append(initialize_record(blob,get(seed,'captured'),available))
        for seed in (0xa5,0xc3):
            for kind in ('captured','target20M'):
                for event in (0,0x10):cases.append(relay(blob,get(seed,kind),event,'normal'))
        for seed in (0xa5,0xc3):
            for kind in ('different_source_handle','missing_cache_handle'):
                cases.append(relay(blob,get(seed,'captured'),0x10,kind))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'error':traceback.format_exc(),'completed_arena_cases':len(arena),
            'completed_relay_cases':len(cases),'scope':'Mac offline only; no device operations.'})
        raise
    j={'status':'PASS_NATIVE_PENDING_CACHE_INIT_AND_DECLARED_EXISTING_BUFFER_RELAY',
       'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
                        'prior_manifest_sha256':PRIOR_SHA,'stage86_result_sha256':im.sha(source_path.read_bytes())},
       'arena_cases':arena,'relay_cases':cases,'bounded_phases':sum(len(c['events']) for c in arena+cases),
       'provenance_refinement':'manager+c90 is an eight-byte pending cache. Its bit4 can be copied from existing frame metadata. '
           'A cache flag or GOP gate is not an encoder-success ACK. Raw metadata+50/+54 and owned buffers remain declared inputs.',
       'scope':'Independent bounded entries with a preserved native source-producer frame; unexecuted middle body, '
           'backend merge/transfer, refcount/allocation, common/virtual callbacks and scheduling. '
           'Fresh empty record has null payload handle; relay uses a separately declared already-owned buffer.',
       'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'cache-origin-results.json',j)
    print(json.dumps({'status':j['status'],'arena_cases':len(arena),'relay_cases':len(cases),
        'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
