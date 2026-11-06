#!/usr/bin/env python3
"""Sequential independent native reselection/packing, not real concurrency.

The original queued request stays suspended at the corrected query-return
boundary. Independent work uses another stack; no kernel reply, completed
consumer, adapter return, data restoration or code unload is synthesized.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage75-private-preset-storage'))
import private_storage as p
c,r,im,V,n,f=p.c,p.r,p.im,p.V,p.n,p.f
BASE,ROOT=p.BASE,p.ROOT
PACK_A=r.ARENA+0x3d0000
PACK_B=PACK_A+0x100
INPUT=PACK_A+0x1000
INDEPENDENT_SP=r.STACK+0x2000


def native_pack(m,label,destination,expected):
    m.uc.mem_write(destination,b'\xa5'*64)
    m.uc.mem_write(INPUT,bytes(0x100))
    before=m.read(r.ARENA,r.ARENA_SIZE);stores=[]
    def observe(u,access,address,size,value,user):
        assert (destination<=address and address+size<=destination+0x38) or (
            r.STACK<=address and address+size<=INDEPENDENT_SP),(hex(address),size)
        stores.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
                       'address':hex(address),'bytes':size})
    hook=m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE,observe)
    e=c.phase(m,label,V+0x221fd0,sp=INDEPENDENT_SP,x21=c.COMMON,x22=destination,x20=INPUT)
    m.uc.hook_del(hook)
    assert e['reason']=='boundary: after_original_rate_fields_before_other_inputs',e['reason']
    packet=m.read(destination,64);words=struct.unpack_from('<3I',packet,0x2c)
    decoded=(((words[1]>>8)+1)<<(6+(words[1]&255)),
             ((words[0]>>8)+1)<<(6+(words[0]&255)),
             ((words[2]>>8)+1)<<(4+(words[2]&255)))
    assert decoded==(25999360,expected,26000000)
    after=m.read(r.ARENA,r.ARENA_SIZE);lo=destination-r.ARENA;hi=lo+64
    assert before[:lo]==after[:lo] and before[hi:]==after[hi:] and packet[0x38:]==b'\xa5'*8
    e.update(destination=hex(destination),partial_packet64_hex=packet.hex(),
             decoded_trace_target_CPB=list(decoded),actual_stores=stores,
             standalone_fragment_not_complete_Start_or_submission=True)
    return e


def one_case(assets,modules,providers,adapter,descriptor,seed,reselect):
    m,events=p.linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    c.prepare(m,events,descriptor,seed,None)
    m.uc.mem_write(p.PRIVATE-p.GUARD,bytes([seed])*(256+2*p.GUARD))
    e=c.phase(m,'original queued target to corrected query return before independent work',V+0x22f34c,x0=f.last.CTX)
    events.append(e);assert e['reason']=='boundary: after_original_rate_query_with_dedicated_guest_preset'
    assert m.query_proof['saved_LR_unchanged'] and m.query_proof['decoded_trace_target_CPB']==[25999360,16000000,26000000]
    assert m.read(c.COMMON+0xe000,8)==r.p64(p.PRIVATE)
    assert len(m.rate_entries)==1 and not m.admitted_channel_entries and not m.kernel_service_entries
    private_before=m.read(p.PRIVATE-p.GUARD,256+2*p.GUARD)
    pending_start=m.uc.reg_read(r.reg.UC_ARM64_REG_SP);pending_end=r.SP+0x1000
    assert pending_start>INDEPENDENT_SP
    pending=m.read(pending_start,pending_end-pending_start)
    control_before=m.read(c.old.CONTROL,296);state_before=c.old.control(m)
    assert state_before['live']==state_before['phase']==1 and state_before['fault']==0
    first=native_pack(m,'independent original rate-pack fragment before reselection',PACK_A,16000000)
    events.append(first);packet_before=m.read(PACK_A,64)
    selection_before=m.read(c.COMMON+0xe000,8)
    native_stores=[]
    if reselect:
        original_arena=m.read(r.ARENA,r.ARENA_SIZE)
        allowed=[(c.COMMON+0xdff8,c.COMMON+0xe010),(c.COMMON+0xe458,c.COMMON+0xe45c),
                 (r.STACK,INDEPENDENT_SP)]
        def observe(u,access,address,size,value,user):
            assert any(a<=address and address+size<=z for a,z in allowed),(hex(address),size)
            native_stores.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
                                  'address':hex(address),'bytes':size})
        hook=m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE,observe)
        e=c.phase(m,'independent original selector reselects same presetID and declared type2',V+0x2261a4,
                  sp=INDEPENDENT_SP,x0=c.COMMON,x1=0x19450,x2=2)
        events.append(e);m.uc.hook_del(hook)
        assert e['reason']=='returned'
        after=m.read(r.ARENA,r.ARENA_SIZE)
        delta=[i+r.ARENA for i,(a,b) in enumerate(zip(original_arena,after)) if a!=b]
        assert all(any(a<=i<z for a,z in allowed[:-1]) for i in delta)
        assert m.read(c.COMMON+0xe000,8)==r.p64(V+0x3c5798)
    assert m.read(c.old.CONTROL,296)==control_before
    assert m.read(PACK_A,64)==packet_before
    assert m.read(p.PRIVATE-p.GUARD,256+2*p.GUARD)==private_before
    second=native_pack(m,'independent original rate-pack fragment after optional reselection',PACK_B,
                       24498176 if reselect else 16000000)
    events.append(second)
    assert m.read(PACK_A,64)==packet_before
    assert m.read(c.old.CONTROL,296)==control_before
    arena_before_reentry=m.read(r.ARENA,r.ARENA_SIZE)
    selected_after=m.read(c.COMMON+0xe000,8)
    m.prototype_stores=[]
    e=c.phase(m,'independent compiled writer re-entry after optional original reselection',m.functions['fx3_candidate'],
              sp=INDEPENDENT_SP,x0=c.old.CONTROL,x1=0,x2=0,x3=0,x4=c.old.EPOCH,x5=c.old.SESSION)
    events.append(e);expected=13 if reselect else 0
    assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==expected
    state_after=c.old.control(m)
    if reselect:
        assert state_after['fault']==13 and state_after['gate']==0 and state_after['live']==state_after['phase']==1
    else:
        assert state_after['fault']==0 and state_after['gate']==1 and state_after['live']==2 and state_after['phase']==1
    assert state_after['lock']==0
    arena_after=m.read(r.ARENA,r.ARENA_SIZE);a=c.old.CONTROL-r.ARENA;z=a+296
    assert arena_before_reentry[:a]==arena_after[:a] and arena_before_reentry[z:]==arena_after[z:]
    assert m.read(c.COMMON+0xe000,8)==selected_after
    assert m.read(p.PRIVATE-p.GUARD,256+2*p.GUARD)==private_before
    assert m.read(pending_start,pending_end-pending_start)==pending
    assert m.read(c.COMMON+0xe110,136)==descriptor and m.read(c.COMMON+0xe470,4)==struct.pack('<I',0x19450)
    assert not m.kernel_service_entries and not m.message_entries and not m.admitted_channel_entries
    c.assert_images(m)
    return {'seed':seed,'reselected':reselect,'events':events,
        'selection_before':hex(int.from_bytes(selection_before,'little')),
        'selection_after':hex(int.from_bytes(selected_after,'little')),
        'original_selector_stores':native_stores,
        'control_before':state_before,'control_after':state_after,
        'original_selector_did_not_update_private_control':True,
        'first_packet_unchanged_after_original_reselection':True,
        'second_packet64_hex':m.read(PACK_B,64).hex(),
        'packet_changed_offsets':[i for i,(a,b) in enumerate(zip(packet_before,m.read(PACK_B,64))) if a!=b],
        'pending_original_query_result_and_stack_unchanged':True,
        'dedicated_preset_and_guards_unchanged':True,'source_FH_and_presetID_unchanged':True,
        'corrected_query_frame':m.query_proof,'writer_reentry_result':expected,
        'writer_reentry_stores':m.prototype_stores,
        'sequential_independent_entries_not_real_concurrency_or_legal_reentrant_API_proof':True,
        'actual_Start_transport_completion_main_recording_or_recovery_proven':False}


def run(out):
    prior=p.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes())=='e0cf1c37bc032542958e19b9a4c42ee50949a570d8cd80908c25274bd857b2df'
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    mods,providers,kernel=c.d.link.build()
    code,ro,_=f.f58.object_image((f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wpath=p.STAGE/'run-20261026/resource_alias.a64.o';apath=p.STAGE/'run-20261026/channel_adapter.a64.o'
    wcode,wro,functions,_=c.old.object_image(wpath.read_bytes());adapter=c.object_image(apath.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets=blob,liro,kernel,code,ro,wcode,wro,functions;descriptor=c.d.p.inputs()[0][1]
    cases=[one_case(assets,mods,providers,adapter,descriptor,seed,True) for seed in (0xa5,0xc3)]
    cases.append(one_case(assets,mods,providers,adapter,descriptor,0xc3,False))
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_NATIVE_RESELECTION_PARTIAL_PACKET_DIVERGENCE_AND_WRITER_OWNER_GUARD',
        'cases':cases,'bounded_fragments':sum(len(x['events']) for x in cases),
        'original_regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in
            [(0x21ee80,0x21eeb8),(0x2261a4,0x226364),(0x221fd0,0x22211c)]],
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
            'storage_runner_sha256':im.sha((p.STAGE/'private_storage.py').read_bytes()),
            'writer_object_sha256':im.sha(wpath.read_bytes()),'adapter_object_sha256':im.sha(apath.read_bytes()),
            'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel)},
        'scope':['Sequential independent selector/partial-packer entries use a separate stack while the corrected original queued request remains suspended.',
            'Same-ID original reselection restores static default pointer. Existing private copy and prepared16M packet persist; new partial packet encodes24,498,176.',
            'Private controller epoch/live state does not automatically follow the original selector. Compiled writer re-entry detects foreign pointer, closes its own gate and preserves live dependency/external selection.',
            'No-reselection control still encodes16M and admits another declared producer, not a completed or hardware consumer.',
            'No real concurrent interleaving, legal runtime reentrancy, complete Start or transport, shared lock/epoch, physical main recording or recovery proof.'],
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'reselection-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':3,'bounded_fragments':result['bounded_fragments'],
                      'real_concurrency_or_recording_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-12:]]})
        raise


if __name__=='__main__':main()
