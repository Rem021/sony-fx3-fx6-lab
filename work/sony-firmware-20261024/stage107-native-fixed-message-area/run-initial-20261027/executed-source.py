#!/usr/bin/env python3
"""Original fixed-area descriptors, getter and full message-metadata constructor.

The post-Mmap initializer input is explicitly declared, never a fake Mmap return.
OSAL allocation/transport and the actual Open-payload copy remain unexecuted.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage106-native-MPR-Open-fields'))
import mpr_open as prev
pp,r,im,MPR=prev.pp,prev.r,prev.im,prev.MPR
SP=prev.SP
INPUT=pp.SCRATCH+0x1000
DEST=pp.SCRATCH+0x400
GETOUT=pp.SCRATCH+0x800
VBASE=pp.SCRATCH+0x2000
PBASE=0x490000000
RECORD=0x456118
PRIOR=prev.STAGE/'final-receipt.json'
PRIOR_SHA='90f7694ba5e29660eac6febd0655a0d5c649b0811eadd709b596d094b59ae978'


def sha(d):return hashlib.sha256(d).hexdigest()


class Guest(pp.StrictMicro):
    def __init__(self,seed):
        super().__init__(MPR,[(0x2c0be4,0x2c0ce0),(0x2c0a44,0x2c0af8),
            (0x27deac,0x27df44),(0x2829a4,0x282a10),(0x282cfc,0x282d00),
            (0x282d38,0x282d6c),(0x27e0cc,0x27e0fc),(0x27e150,0x27e168)],resolve=True)
        self.uc.mem_write(pp.STACK_BASE,bytes([seed])*pp.STACK_SIZE)
        self.uc.mem_write(pp.SCRATCH,bytes([seed^0x3c])*0x10000)
        assert bytes(self.uc.mem_read(RECORD,0xa0))==bytes(0xa0)
        self.uc.mem_protect(RECORD&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
        self.image=[(s['p_vaddr'],bytes(self.uc.mem_read(s['p_vaddr'],s['p_memsz']))) for s in MPR.segments]
        self.boundaries={0x7dde0:'before_unexecuted_Mmap',0x27dba8:'before_original_Codec_logger',
            0x282d00:'after_original_payload_stride_MOV',0x282d6c:'before_original_Open_payload_copy',
            0x7e350:'before_unexecuted_OSAL_allocation',0x27e168:'after_original_header_copy'}
        self.reads=[];self.hooks.append(self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe))

    def observe(self,u,access,at,n,value,user):
        if at<RECORD+0xa0 and at+n>RECORD:
            assert RECORD<=at and at+n<=RECORD+0xa0
            self.reads.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
                'record_offset':hex(at-RECORD),'size':n,'bytes':bytes(u.mem_read(at,n)).hex()})

    def code(self,u,pc,n,user):
        if pc in self.boundaries:
            self.pcs.append(hex(pc));self.abort('boundary: '+self.boundaries[pc]);return
        return super().code(u,pc,n,user)

    def phase(self,label,entry,outputs=(),record_writes=False,**regs):
        before_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        before_scratch=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        record_before=bytes(self.uc.mem_read(RECORD,0xa0))
        for name,value in regs.items():self.uc.reg_write(getattr(r.reg,'UC_ARM64_REG_'+name.upper()),value)
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=3000,timeout=1000000)
        assert self.reason is not None
        assert self.reason=='returned' or self.reason.startswith('boundary: '),self.reason
        for w in self.stores:
            at,n=int(w['address'],16),w['size']
            assert SP-0x800<=at and at+n<=SP or any(a<=at and at+n<=z for a,z in outputs) or record_writes and RECORD<=at and at+n<=RECORD+0xa0,w
        after_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert after_stack[:SP-0x800-pp.STACK_BASE]==before_stack[:SP-0x800-pp.STACK_BASE]
        assert after_stack[SP-pp.STACK_BASE:]==before_stack[SP-pp.STACK_BASE:]
        after_scratch=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        changed=[pp.SCRATCH+i for i,(a,b) in enumerate(zip(before_scratch,after_scratch)) if a!=b]
        assert all(any(a<=q<z for a,z in outputs) for q in changed)
        if not record_writes:assert bytes(self.uc.mem_read(RECORD,0xa0))==record_before
        for at,old in self.image:
            new=bytes(self.uc.mem_read(at,len(old)));lo=max(0,RECORD-at);hi=min(len(old),RECORD+0xa0-at)
            if lo<hi:assert new[:lo]==old[:lo] and new[hi:]==old[hi:]
            else:assert new==old
        assert all('stub' not in x for x in self.calls)
        return {'label':label,'entry':hex(entry),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
            'pcs':self.pcs,'stores':self.stores,'record_reads':self.reads,'original_local_PLT_and_return_observations':self.calls,
            'whole_stack_outside_800_byte_declared_range_unchanged':True,
            'whole_scratch_outside_declared_outputs_unchanged':True,
            'whole_relocated_ELF_outside_original_fixed_records_unchanged':True,
            'fixed_records_unchanged_or_original_initializer_only':True,
            'Mmap_OSAL_IO_logs_or_success_return_adapters_executed':False}

    def close(self):
        for h in self.hooks:self.uc.hook_del(h)


def initialize(m,seed,span):
    # A5/C3 marks old descriptor/padding state only; not camera initialization.
    m.uc.mem_write(RECORD,bytes([seed])*0xa0)
    saved={i:m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,30)}
    events=[m.phase('original fixed-area initializer prologue',0x2c0be4,
        sp=SP,x30=pp.STOP,x0=PBASE,x1=span)]
    assert events[-1]['reason']=='boundary: before_unexecuted_Mmap'
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X19)==PBASE
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X20)==PBASE+span
    # Independent input after unexecuted mapping. No fake syscall return.
    events.append(m.phase('independent original descriptor generation with declared virtual base',0x2c0c04,
        record_writes=True,x0=VBASE))
    assert events[-1]['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_SP)==SP
    assert all(m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))==v for i,v in saved.items())
    records=bytes(m.uc.mem_read(RECORD,0xa0))
    expected_offsets=[(0x200,0x8000),(0,0x200),(0x8200,0x400),(0x8600,0x400),(0x8a00,0x400)]
    initialized=5 if span==0x8e00 else 3
    for n,(off,length) in enumerate(expected_offsets[:initialized]):
        assert struct.unpack_from('<QQI',records,n*32)==(VBASE+off,PBASE+off,length)
        assert struct.unpack_from('<Q',records,n*32+24)[0]==(VBASE-PBASE)&0xffffffffffffffff
    if span==0x8200:assert records[0x60:]==bytes([seed])*0x40
    return {'declared_mapping_virtual_base':hex(VBASE),'declared_physical_base':hex(PBASE),
        'declared_span':span,'original_records_hex':records.hex(),'events':events,
        'actual_Mmap_backup_values_or_physical_mapping_proven':False}


def get_area(m,kind):
    saved={i:m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,30)}
    e=m.phase('original complete GetFixedArea type '+str(kind),0x2c0a44,
        outputs=[(GETOUT,GETOUT+20)],sp=SP,x30=pp.STOP,x0=kind,x1=GETOUT,x2=GETOUT+8,x3=GETOUT+16)
    assert e['reason']=='returned'
    assert all(m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))==v for i,v in saved.items())
    out=bytes(m.uc.mem_read(GETOUT,20));virt,phys,length=struct.unpack('<QQI',out)
    return {'type':kind,'virtual':hex(virt),'physical':hex(phys),'extent_word':length,'events':[e]}


def message(m,raw,fmt,count,view,dest,span):
    m.uc.mem_write(INPUT,raw)
    events=[m.phase('original Codec Open prologue before logging',0x2829a4,
        sp=SP,x30=pp.STOP,x0=INPUT,x1=0x20,x2=fmt,x3=count,x4=view,x5=0)]
    assert events[-1]['reason']=='boundary: before_original_Codec_logger'
    fp=m.uc.reg_read(r.reg.UC_ARM64_REG_X29);assert fp==SP-0xd0
    events.append(m.phase('independent original98-byte stride instruction',0x282cfc))
    assert events[-1]['reason']=='boundary: after_original_payload_stride_MOV'
    events.append(m.phase('independent original metadata preparation and full CreateMessage/GetFixedArea',0x282d38))
    assert events[-1]['reason']=='boundary: before_original_Open_payload_copy'
    payload=fp+0xa0;header=bytes(m.uc.mem_read(payload,0x30))
    length=struct.unpack_from('<I',header,0x10)[0]
    virt=struct.unpack_from('<Q',header,8)[0];phys=struct.unpack_from('<Q',header,0x28)[0]
    # The getter's third output is a local length at CreateMessage FP+5c.
    # It is NOT header+1a: that field receives the ninth caller argument ViewId.
    extent=struct.unpack('<I',bytes(m.uc.mem_read(SP-0xf4,4)))[0]
    view_word=struct.unpack_from('<H',header,0x1a)[0]
    mid=struct.unpack_from('<I',header,0x24)[0]
    assert length==count*0x98 and mid==(0x1610 if count>1 else 0x210)
    assert header[0x18]==0x20 and header[0x1c]==fmt and header[0x19]==header[0x1e]==0
    assert struct.unpack_from('<H',header,2)[0]==0
    assert view_word==view and extent==(0x400 if span else 0)
    assert any(int(w['address'],16)==SP-0xf4 and w['value']==extent for w in events[-1]['stores'])
    assert bytes(m.uc.mem_read(INPUT,len(raw)))==raw
    pending=bytes(m.uc.mem_read(SP-0xe0,0xe0))
    events.append(m.phase('independent original SendMsg prologue before OSAL allocation',0x27e0cc,
        sp=SP-0x400,x30=pp.STOP,x0=payload,x1=0))
    assert events[-1]['reason']=='boundary: before_unexecuted_OSAL_allocation'
    # X0 is an explicit capture buffer, not an allocator result placed in a slot.
    events.append(m.phase('independent native48-byte header copy to declared capture buffer',0x27e150,
        outputs=[(dest,dest+0x30)],x0=dest))
    assert events[-1]['reason']=='boundary: after_original_header_copy'
    copied=bytes(m.uc.mem_read(dest,0x30));assert copied==header
    assert bytes(m.uc.mem_read(SP-0xe0,0xe0))==pending
    return {'format':fmt,'count':count,'declared_view':view,'native_message_ID':mid,
        'native_payload_length':length,'native_virtual_pointer':hex(virt),'native_physical_pointer':hex(phys),
        'native_fixed_extent_local_not_header':extent,'native_ViewId_field1a':view_word,
        'header30_hex':header.hex(),'copied_header30_hex':copied.hex(),
        'payload_fits_recorded_extent':bool(virt and length<=extent),
        'recorded_extent_inside_declared_mapping':bool(virt and VBASE<=virt and virt+extent<=VBASE+span),
        'pending_Codec_frame_preserved':True,'events':events,
        'actual_payload_copy_allocation_transport_or_valid_runtime_request_proven':False}


def one(seed,mode,raw,fmt):
    m=Guest(seed)
    try:
        init=None;areas=[]
        span=0 if mode=='no_initializer' else (0x8200 if mode=='short_declared_mapping' else 0x8e00)
        if span:init=initialize(m,seed,span)
        if mode=='normal_declared_mapping':
            areas=[get_area(m,i) for i in range(6)]
            assert [a['extent_word'] for a in areas]==[0x200,0x8000,0x400,0x400,0x400,0]
        specs=[(fmt,1,0),(18,1,1),(fmt,2,0),(fmt,7,0)] if mode=='normal_declared_mapping' else [(fmt,1,0)]
        messages=[message(m,raw,f,n,v,DEST+i*0x40,span) for i,(f,n,v) in enumerate(specs)]
        if mode=='no_initializer':assert messages[0]['native_virtual_pointer']==messages[0]['native_physical_pointer']=='0x0'
        else:
            assert all(int(x['native_virtual_pointer'],16)==VBASE+0x8200 and int(x['native_physical_pointer'],16)==PBASE+0x8200 for x in messages)
        if mode=='normal_declared_mapping':
            assert len({x['native_virtual_pointer'] for x in messages})==1
            assert messages[0]['copied_header30_hex']!=messages[1]['copied_header30_hex']
            assert messages[0]['payload_fits_recorded_extent'] and not messages[-1]['payload_fits_recorded_extent']
        if mode=='short_declared_mapping':assert not messages[0]['recorded_extent_inside_declared_mapping']
        return {'seed':seed,'mode':mode,'initializer':init,'area_getters':areas,'messages':messages,
            'original_pool_initialized_or_current_camera_mapping_proven':False,
            'same_fixed_pointer_not_owned_copy_or_real_race_proof':True}
    finally:m.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        source=BASE/'stage106-native-MPR-Open-fields/run-negative-boundaries-20261027/mpr-open-results.json'
        old=json.loads(source.read_text());rows=[]
        for seed in (0xa5,0xc3):
            p=next(p for p in old['produced'] if p['label']=='target_HEVC_HD420' and p['seed']==seed)
            raw=bytes.fromhex(p['raw98_hex']);fmt=p['category_queries'][0]['native_file_format_category']
            rows.extend(one(seed,mode,raw,fmt) for mode in ('normal_declared_mapping','no_initializer','short_declared_mapping'))
        phases=sum((len(c['initializer']['events']) if c['initializer'] else 0)+sum(len(x['events']) for x in c['area_getters']+c['messages']) for c in rows)
        j={'status':'PASS_ORIGINAL_FIXED_AREA_METADATA_AND_CAPACITY_SCOPE_NOT_RUNTIME_ALLOCATION',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_mpr_sha256':sha(MPR.path.read_bytes()),'source_profile_sha256':sha(source.read_bytes()),
            'source_profile':str(source.relative_to(ROOT)),'cases':rows,'bounded_phases':phases,
            'Mmap_after_gap_virtual_base_is_explicit_input_not_fabricated_return':True,
            'header_copy_capture_buffer_not_OSAL_allocation_result':True,
            'actual_Backup_reads_Mmap_OSAL_messages_payload_copy_or_camera_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'fixed-area-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'cases':len(rows),'bounded_phases':phases}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise


if __name__=='__main__':main()
