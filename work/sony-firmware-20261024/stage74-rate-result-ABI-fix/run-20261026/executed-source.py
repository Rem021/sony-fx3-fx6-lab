#!/usr/bin/env python3
"""Reproduce old result overwrite, then validate corrected guest-only caller.

Neither baseline nor fixed adapter is deployed. Original kernel services and
hardware remain stopping boundaries. No channel return is synthesized.
"""
from pathlib import Path
import argparse
import datetime
import json
import re
import struct
import subprocess
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage69-native-16M-callpath'))
import channel_callpath as c
r,im,V,n,f=c.r,c.im,c.V,c.n,c.f
BASE,ROOT=c.BASE,c.ROOT
RATE=V+0x225b7c


def layout(adapter):
    from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);start=adapter[2]['fx3_channel_adapter']
    rows=list(md.disasm(adapter[0][start-c.BRIDGE:start-c.BRIDGE+24],start))
    first=rows[0];assert first.mnemonic=='sub'
    match=re.fullmatch(r'sp, sp, #0x([0-9a-f]+)',first.op_str);assert match
    size=int(match[1],16);slots=[]
    for ins in rows:
        if ins.mnemonic!='stp':continue
        m=re.fullmatch(r'(x[0-9]+), (x[0-9]+), \[sp, #0x([0-9a-f]+)\]',ins.op_str)
        if m:
            off=int(m[3],16)
            slots.extend([{'register':m[1],'offset':off},{'register':m[2],'offset':off+8}])
    assert {x['register'] for x in slots}=={'x19','x20','x21','x22','x29','x30'}
    return {'frame_size':size,'saved_register_slots':slots,
            'original_compiled_prologue':[{'pc':hex(x.address),'asm':x.mnemonic+' '+x.op_str} for x in rows]}


class ABIWatchGuest(c.Guest):
    def __init__(self,*args):
        super().__init__(*args)
        self.query_frame=None;self.query_writes=[];self.query_proof=None

    def code(self,u,pc,size,user):
        rr=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
        if pc==RATE:
            sp=u.reg_read(r.reg.UC_ARM64_REG_SP)
            entry=int(self.adapter_entries[-1]['SP'],16)
            assert entry-sp==self.compiled_layout['frame_size']
            self.query_frame={'start':sp,'end':entry,'result':rr(8),
                'before':self.read(sp,entry-sp),'before_LR':self.adapter_entries[-1]['LR']}
            assert sp<=rr(8) and rr(8)+self.result_container_size<=entry
        if pc in self.rate_return_pcs:
            q=self.query_frame;assert q and u.reg_read(r.reg.UC_ARM64_REG_SP)==q['start']
            after=self.read(q['start'],q['end']-q['start']);lo=q['result']-q['start']
            diff=[i for i,(a,b) in enumerate(zip(q['before'],after)) if a!=b]
            saved=[]
            for slot in self.compiled_layout['saved_register_slots']:
                off=slot['offset'];a=q['before'][off:off+8];b=after[off:off+8]
                saved.append({**slot,'before_hex':a.hex(),'after_hex':b.hex(),'unchanged':a==b})
            lr=[x for x in saved if x['register']=='x30'][0]
            assert hex(int.from_bytes(bytes.fromhex(lr['before_hex']),'little'))==q['before_LR']
            outside=[x for x in self.query_writes if not (q['result']<=int(x['address'],16) and
                     int(x['address'],16)+x['bytes']<=q['result']+self.result_container_size)]
            covered=set()
            for x in self.query_writes:
                a=int(x['address'],16)-q['result'];covered.update(range(a,a+x['bytes']))
            assert covered==set(range(0x34))-set(range(0x2e,0x30))
            self.query_proof={'result_pointer':hex(q['result']),'container_bytes':self.result_container_size,
                'original_result_written_span_bytes':0x34,'actual_written_bytes':len(covered),
                'written_offsets':sorted(covered),'unwritten_inside_span':[0x2e,0x2f],
                'frame_start':hex(q['start']),'frame_end':hex(q['end']),
                'frame_before_hex':q['before'].hex(),'frame_after_hex':after.hex(),
                'frame_changed_offsets':diff,'saved_register_slots':saved,
                'original_result_stores':self.query_writes,'stores_outside_declared_container':outside,
                'full_frame_outside_container_unchanged':all(lo<=i<lo+self.result_container_size for i in diff),
                'saved_LR_unchanged':lr['unchanged'],
                'decoded_trace_target_CPB':list(struct.unpack('<3Q',self.read(q['result'],24))),
                'raw_result_container_hex':self.read(q['result'],self.result_container_size).hex()}
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        pc=u.reg_read(r.reg.UC_ARM64_REG_PC);q=self.query_frame
        if q and RATE<=pc<V+0x225e40 and q['start']<=address and address+size<=q['end']:
            self.query_writes.append({'pc':hex(pc),'address':hex(address),'bytes':size})
        return super().store(u,access,address,size,value,user)


def linked(assets,modules,providers,adapter,container):
    m=ABIWatchGuest(assets,modules,providers,adapter)
    m.compiled_layout=layout(adapter);m.result_container_size=container
    events=[n.link(m)]
    for b in m.import_bindings:
        assert m.read(int(b['actual_avcam_slot'],16),8)==r.p64(int(b['original_module_target'],16))
    m.uc.mem_write(f.f58.SITE,m.patch);m.uc.mem_write(c.SITE,m.adapter_patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for at,value in m.expected_data.items():assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&-4096,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=c.phase(m,'original mute setter for result ABI audit',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    lo=f.G&-4096;hi=(f.G+f.GSIZE+4095)&-4096
    m.uc.mem_protect(lo,hi-lo,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    m.boundaries[m.rate_return_pcs[0]]='after_original_rate_writes_before_adapter_uses_result'
    return m,events


def target_case(assets,modules,providers,adapter,descriptor,seed,fixed):
    size=56 if fixed else 24
    m,events=linked(assets,modules,providers,adapter,size)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    c.prepare(m,events,descriptor,seed,None)
    e=c.phase(m,'original queued request and '+('fixed56' if fixed else 'old24')+' result ABI to query return boundary',
              V+0x22f34c,x0=f.last.CTX)
    events.append(e)
    assert e['reason']=='boundary: after_original_rate_writes_before_adapter_uses_result'
    assert m.real_returns[0]['W0']==386 and len(m.writer_entries)==len(m.rate_entries)==len(m.rate_returns)==1
    proof=m.query_proof;assert proof and proof['decoded_trace_target_CPB']==[25999360,16000000,26000000]
    assert m.read(c.COMMON+0xe110,136)==descriptor
    if fixed:
        assert not proof['stores_outside_declared_container'] and proof['saved_LR_unchanged']
        assert proof['full_frame_outside_container_unchanged'] and all(x['unchanged'] for x in proof['saved_register_slots'])
        pc=m.rate_return_pcs[0];m.boundaries.pop(pc)
        e=c.phase(m,'same fixed adapter uses result and forwards original channel arguments',pc,independent=False)
        events.append(e);assert e['reason']=='boundary: before_original_buffer_channel_preparation'
        assert len(m.admitted_channel_entries)==1
        assert m.admitted_channel_entries[0]['x0_x3']==m.adapter_entries[0]['x0_x3']
        before=m.read(c.old.CONTROL,296)
        m.boundaries.pop(c.SONY['sony_channel'])
        e=c.phase(m,'same fixed original request to existing kernel service boundary',c.SONY['sony_channel'],independent=False)
        events.append(e);assert e['reason']=='boundary: before_original_unexecuted_kernel_service'
        assert m.kernel_service_entries[0]['names']==['_raw_spin_lock_irqsave']
        assert len(m.module_alloc_entries)==len(m.message_entries)==1
        assert m.read(c.old.CONTROL,296)==before
    else:
        assert proof['stores_outside_declared_container'] and not proof['saved_LR_unchanged']
        assert not proof['full_frame_outside_container_unchanged']
        assert not m.admitted_channel_entries and not m.kernel_service_entries and not m.message_entries
    assert c.old.control(m)['live']==1 and c.old.control(m)['phase']==1
    c.assert_images(m)
    return {'label':('corrected56' if fixed else 'quarantined_old24')+' prior'+hex(seed),
        'seed':seed,'corrected_container':fixed,'original_query_result_write_audit':proof,
        'compiled_layout':m.compiled_layout,'events':events,
        'original_adapter_entry':m.adapter_entries[0],
        'actual_original_rate_entry':m.rate_entries[0],'actual_original_rate_return':m.rate_returns[0],
        'original_channel_entries':m.admitted_channel_entries,'resource_messages':m.message_entries,
        'kernel_service_entries':m.kernel_service_entries,'control_at_stop':c.old.control(m),
        'original_FH_descriptor_preserved':True,'producer_lease_still_live':True,
        'actual_channel_return_adapter_unwind_hardware_or_recovery_proven':False}


def run(out):
    prior=BASE/'stage73-native-free-message-path/final-receipt.json'
    assert im.sha(prior.read_bytes())=='ad9808d60e977f22db80f43eedbbd9e8e8da263a231e8fe85fae35e499c418f7'
    for x in json.loads(prior.read_text())['files']:assert im.sha((ROOT/x['path']).read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    cmd=['/usr/bin/clang',*c.old.old.FLAGS,'-c',str(STAGE/'channel_adapter.c'),'-o',str(out/'channel_adapter.a64.o')]
    done=subprocess.run(cmd,capture_output=True,text=True)
    im.write_json(out/'compile-receipt.json',{'command':cmd,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr})
    assert done.returncode==0 and not done.stderr
    new=c.object_image((out/'channel_adapter.a64.o').read_bytes())
    oldpath=c.STAGE/'run-same-instance-slices-20261026/channel_adapter.a64.o'
    old=c.object_image(oldpath.read_bytes())
    mods,providers,kernel=c.d.link.build()
    code,ro,_=f.f58.object_image((f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wcode,wro,functions,_=c.old.object_image((c.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o').read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets=blob,liro,kernel,code,ro,wcode,wro,functions
    inputs=c.d.p.inputs();target=inputs[0][1]
    baseline=[target_case(assets,mods,providers,old,target,seed,False) for seed in (0xa5,0xc3)]
    corrected=[target_case(assets,mods,providers,new,target,seed,True) for seed in (0xa5,0xc3)]
    controls=[c.one_case(assets,mods,providers,new,'stock UHD with corrected container',inputs[3][1],0xc3,431),
              c.one_case(assets,mods,providers,new,'closed gate with corrected container',target,0xc3,386,True,'closed')]
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_OLD_CALLER_STACK_OVERWRITE_REPRODUCED_FIXED_CONTAINER_BOUNDED',
        'quarantined_old_baseline':baseline,'corrected_target_cases':corrected,'regression_controls':controls,
        'bounded_fragments':sum(len(x['events']) for x in baseline+corrected+controls),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
            'old_C_source_sha256':im.sha((c.STAGE/'channel_adapter.c').read_bytes()),
            'corrected_C_source_sha256':im.sha((STAGE/'channel_adapter.c').read_bytes()),
            'original_runner_sha256':im.sha((c.STAGE/'channel_callpath.py').read_bytes()),
            'old_object_sha256':im.sha(oldpath.read_bytes()),'corrected_object_sha256':im.sha((out/'channel_adapter.a64.o').read_bytes()),
            'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel)},
        'original_getter_full_function':im.dump(blob,0x225b7c,0x225e40,V),
        'ABI_scope':'56-byte compiled result container covers this original function observed write span52 with alignment8; remaining fields/padding unclassified, no claim Sony sizeof is proven.',
        'prior_correction':'stage69 old24 result writes corrupt saved LR/register slots before its kernel stop. Its numeric prefix observations survive, but no safe caller/return claim may be drawn from that old adapter.',
        'inert_old_adapter_in_stages70_73':'Those original-only stages never entered the mapped adapter; their original queue/free/exit observations remain separate.',
        'Windows_UU_camera_operations':False,'real_main_recording_or_recovery':False,
        'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'rate-ABI-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    (out/'compiled-source.c').write_bytes((STAGE/'channel_adapter.c').read_bytes())
    print(json.dumps({'status':result['status'],'baseline':2,'corrected':2,'controls':2,
                      'bounded_fragments':result['bounded_fragments'],'physical_recording_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args()
    im.volume();out=Path(a.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(p) for p in m.pcs[-10:]],'query_proof':m.query_proof})
        raise


if __name__=='__main__':main()
