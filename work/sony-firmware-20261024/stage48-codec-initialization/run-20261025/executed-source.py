#!/usr/bin/env python3
"""Original common-handler construction and codec-byte origin, offline only.

The fresh-file storage is relocated into declared guest RAM. The factory prefix
constructs six handlers but stops before its remaining registration. Preparation,
post-match selection and parameter-builder calls are separate bounded fragments.
The unconditional diagnostic is NOT implemented, skipped, or given a fake return:
the post-diagnostic body runs in another guest on explicitly copied fixtures.
The optional 16M copy/pointer is HOST data setup, not a new native writer/hook.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage47-runtime-provider-binding'))
import native_initialization as n
sys.path.insert(0,str(BASE/'stage38-imola-parameter-copy'))
import parameter_copy as t
r,im,V=n.r,n.im,n.V
w=t.w
A=w.A
FACTORY=A-0x40
SOURCE_FACTORY=0x562930
STRIDE=0xe518
SLOTS=6
COMMON=A+0xe198
CODEC=A+0xe1d8
LENGTH=0x1c0
EXPECTED_UNWRITTEN=[0xe,0xf,0x10,0x11,0x12,0x13,0x19,
  *range(0x44,0x4c),0x4e,0x4f,0x61,0x62,0x63,*range(0x1a0,0x1c0)]
PRIOR_SHA='036f95e0d4840d1543ad2fc4affe7f55b6c4fef208a5f921a688c23625f75898'
EXTRA=[(0x21d9e0,0x21dc68),(0x21dcb4,0x21dd18),
  (0x22c450,0x22c4e8),(0x226778,0x2267fc),(0x226d2c,0x226d78),
  (0x221b50,0x221b8c),(0x27da9c,0x27dab4)]


class Guest(n.Guest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,module,kernel)
        self.ranges.extend((V+a,V+z) for a,z in [*w.RANGES,*t.EXTRA,*EXTRA])
        self.boundaries.update({V+0x226d78:'after_six_handlers_before_rest_of_factory',
          V+0x21e2c0:'after_original_descriptor_copy_and_stack_clear',
          V+0x21dd54:'before_actual_buffer_and_channel_preparation',
          V+0x221b8c:'after_original_common_64byte_clear',
          V+0x221eec:'before_unexecuted_unconditional_diagnostic',
          V+0x2227b0:'post_diagnostic_body_success_marker_before_epilogue',
          V+0x27d528:'before_unexecuted_diagnostic_acquire'})
        self.clear_calls=[];self.constructor_calls=[];self.pool_calls=[]

    def code(self,u,pc,size,user):
        if pc==V+0x2f67c:
            self.clear_calls.append({k:hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_'+k.upper())))
              for k in ('x0','x1','x2')})
        if pc==V+0x21d9e0:
            self.constructor_calls.append(hex(u.reg_read(r.reg.UC_ARM64_REG_X0)))
        if pc==V+0x21dcb4:
            self.pool_calls.append(hex(u.reg_read(r.reg.UC_ARM64_REG_X0)))
        return super().code(u,pc,size,user)


def phase(m,label,start,independent=True,**regs):
    m.reason=None;m.pcs=[];m.writes=[];m.cpu_events=[]
    m.clear_calls=[];m.constructor_calls=[];m.pool_calls=[]
    if independent:m.regs(sp=r.SP,x30=r.STOP)
    m.regs(**regs)
    before_sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    m.uc.emu_start(start,0,count=2000000,timeout=15000000)
    assert m.reason is not None,'bounded instruction/time limit without approved stop'
    return {'label':label,'start_pc':hex(start),'reason':m.reason,
      'stop_pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
      'SP_before':hex(before_sp),'SP_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
      'x0_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_X0)),
      'pcs':[hex(p) for p in m.pcs],'writes':list(m.writes),
      'native_clear_calls':list(m.clear_calls),'common_constructor_calls':list(m.constructor_calls),
      'pool_constructor_calls':list(m.pool_calls),'CPU_events':list(m.cpu_events),
      'independent_entry_fixture':independent,'native_output_or_PC_return_adapter':False}


def linked_guest(blob,module,kernel):
    m=Guest(blob,module,kernel);event=n.link(m)
    # Embedded original memcpy is in the first page. Preserve READ and execute;
    # remove WRITE after the original loader has initialized only import data.
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    assert sum(int.from_bytes(m.read(V+0x1ec+i*8,8),'little')!=0 for i in range(211))==1
    return m,event


def touched(events,at,length):
    found=set()
    for event in events:
        for z in event['writes']:
            lo=int(z['address'],16);hi=lo+z['size']
            found.update(range(max(lo,at)-at,min(hi,at+length)-at))
    return sorted(found)


def assert_image(m,blob):
    assert m.read(V,0x1ec)==blob[:0x1ec]
    assert m.read(V+0x884,len(blob)-0x884)==blob[0x884:]
    assert m.read(V+0x1ec,0x698)==m.read(n.MDATA,0x698)


def construct(m,blob,seed):
    if seed is None:
        storage=blob[SOURCE_FACTORY:SOURCE_FACTORY+0x40+SLOTS*STRIDE]
        assert len(storage)==0x40+SLOTS*STRIDE and set(storage)=={0}
        m.uc.mem_write(FACTORY,storage)
        event=phase(m,'original factory prefix constructs six file-derived handler slots',
          V+0x226d2c,x0=FACTORY,x1=r.ARENA+0x90000)
        assert event['reason']=='boundary: after_six_handlers_before_rest_of_factory'
        assert event['SP_after']==hex(r.SP-0x40)
        assert event['common_constructor_calls']==[hex(A+i*STRIDE) for i in range(SLOTS)]
        slots=SLOTS
    else:
        storage=bytes([seed])*STRIDE
        m.uc.mem_write(A,storage)
        event=phase(m,'complete original common-handler constructor on prior-content control '+hex(seed),
          V+0x21d9e0,x0=A)
        assert event['reason']=='returned' and event['SP_after']==hex(r.SP)
        assert event['common_constructor_calls']==[hex(A)]
        slots=1
    expected=0 if seed is None else seed
    assert len(event['pool_constructor_calls'])==slots*15
    for i in range(slots):
        owner=A+i*STRIDE
        assert m.read(owner,8)==r.p64(V+0x37bda8)
        assert m.read(owner+0xe1d8,LENGTH)==bytes([expected])*LENGTH
        assert not touched([event],owner+0xe1d8,LENGTH)
    event.update(codec448_preserved_in_every_constructed_slot=True,
      seed_source='original file-derived static storage relocated to guest arena' if seed is None else 'artificial prior-content control',
      seed_byte=hex(expected),constructed_slots=slots,
      scope='Complete original common-handler constructor bodies; factory prefix only. Actual boot, singleton guard, live MAIN slot selection, registration and later lifecycles unexecuted.')
    return event


def case(blob,module,kernel,descriptor,label,seed,candidate):
    m,load=linked_guest(blob,module,kernel);events=[load]
    constructor=construct(m,blob,seed);events.append(constructor)
    before=m.read(CODEC,LENGTH)
    m.uc.mem_write(w.DESC,descriptor)
    prepare=phase(m,'original prepare entry through descriptor copy and actual stack clear',
      V+0x21e26c,x0=A,x1=w.DESC)
    assert prepare['reason']=='boundary: after_original_descriptor_copy_and_stack_clear'
    assert m.read(A+0xe110,0x88)==descriptor
    prepare_sp=int(prepare['SP_after'],16)
    assert m.read(prepare_sp+0x78,0x88)==bytes(0x88)
    assert prepare['native_clear_calls']==[{'x0':hex(prepare_sp+0x78),'x1':'0x0','x2':'0x88'}]
    assert m.read(CODEC,LENGTH)==before
    events.append(prepare)
    selection=phase(m,'independent original post-match row386 preset selection',V+0x21edc8,
      x19=A,x20=w.ROWBLOCK,x21=w.DESC,x26=V+w.v.CREATE_TABLE+386*0x90,x22=w.ID)
    assert selection['reason']=='boundary: before_actual_buffer_and_channel_preparation'
    assert m.read(A+0xe000,8)==r.p64(w.PRESET)
    assert m.read(CODEC,LENGTH)==before
    events.append(selection)
    if candidate:
        private=bytearray(m.read(w.PRESET,0x100))
        assert im.sha(private)=='f5cb9ba1652bdad279e55ed0d61d43b0581c19bec9ad18983f9c31959cffbf71'
        struct.pack_into('<I',private,0xb0,249999)
        struct.pack_into('<I',private,0xac,0)
        m.uc.mem_write(w.COPY,bytes(private));m.uc.mem_write(A+0xe000,r.p64(w.COPY))
    raw=bytearray(0x170)
    struct.pack_into('<I',raw,0x20,14)
    struct.pack_into('<HH',raw,0xe0,1920,1080)
    struct.pack_into('<I',raw,0xfc,1)
    m.uc.mem_write(t.INPUT,bytes(raw))
    preclear=phase(m,'original builder entry and real 64-byte common clear',V+0x221b50,
      x0=A,x1=t.INPUT,x2=COMMON,x3=CODEC)
    assert preclear['reason']=='boundary: after_original_common_64byte_clear'
    assert m.read(COMMON,0x40)==bytes(0x40)
    assert preclear['native_clear_calls']==[{'x0':hex(COMMON),'x1':'0x0','x2':'0x40'}]
    assert m.read(CODEC,LENGTH)==before
    events.append(preclear)
    m.boundaries.pop(V+0x221b8c)
    prefix=phase(m,'same-PC continuation from common clear to original mandatory diagnostic',
      V+0x221b8c,independent=False)
    assert prefix['reason']=='boundary: before_unexecuted_unconditional_diagnostic'
    assert prefix['SP_before']==preclear['SP_after']==prefix['SP_after']
    events.append(prefix)
    captured={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,30)}
    captured['sp']=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    assert (captured['x26'],captured['x27'],captured['x29'])==(1,0,0)
    # This is a second guest, not a resumed call past the missing diagnostic.
    post,load2=linked_guest(blob,module,kernel);events.append(load2)
    post.uc.mem_write(r.ARENA,m.read(r.ARENA,r.ARENA_SIZE))
    post.uc.mem_write(r.STACK,m.read(r.STACK,r.STACK_SIZE))
    for i in range(19):post.regs(**{f'x{i}':0})
    post.regs(x30=r.STOP)
    continuation=phase(post,'independent post-diagnostic body in another guest with explicit copied fixtures',
      V+0x221f50,independent=False,**captured)
    assert continuation['reason']=='boundary: post_diagnostic_body_success_marker_before_epilogue'
    assert continuation['x0_after']=='0x1'
    continuation.update(separate_guest=True,
      fixtures='Host copies stopped-prefix arena/stack, sets captured X19-X29/SP and zero caller-saved registers. Diagnostic was not executed or adapted; this is not full builder/Open execution.')
    events.append(continuation)
    written=touched([preclear,prefix,continuation],CODEC,LENGTH)
    unwritten=sorted(set(range(LENGTH))-set(written))
    assert unwritten==EXPECTED_UNWRITTEN and len(written)==396 and len(unwritten)==52
    payload=post.read(CODEC,LENGTH)
    assert all(payload[i]==before[i] for i in unwritten)
    words=struct.unpack_from('<3I',payload,0x2c)
    target=((words[0]>>8)+1)<<(6+(words[0]&255))
    trace=((words[1]>>8)+1)<<(6+(words[1]&255))
    cpb=((words[2]>>8)+1)<<(4+(words[2]&255))
    assert (target,trace,cpb)==(16000000 if candidate else 24498176,25999360,26000000)
    assert_image(m,blob);assert_image(post,blob)
    return {'label':label,'seed':None if seed is None else hex(seed),'candidate_16M_host_data_fixture':candidate,
      'constructor_slots':constructor['constructed_slots'],'original_fragments':events,
      'pre_builder_codec_hex':before.hex(),'payload_hex':payload.hex(),
      'common_hex':post.read(COMMON,0x40).hex(),'decoded_target':target,'decoded_trace':trace,'decoded_cpb':cpb,
      'written_byte_offsets':[hex(i) for i in written],'unwritten_byte_offsets':[hex(i) for i in unwritten],
      'captured_post_prefix_registers':{k:hex(v) for k,v in captured.items()},
      'artificial_quality24_descriptor_hex':descriptor.hex(),'input_fixture_hex':bytes(raw).hex(),
      'original_common_clear_executed':True,'codec52_prior_values_preserved':True,
      'whole_builder_or_complete_Open_Start_or_current_MAIN_owner_verified':False}


def static_evidence(blob,module):
    # These are fixed original call-site/address anchors, not runtime reachability.
    assert im.cstring(blob,0x32e1a0)=='N5imola28imola_common_api_enc_handlerE'
    assert struct.unpack_from('<Q',blob,0x37bda0)[0]==V+0x32e1d0
    source_slots=[]
    for i in range(SLOTS):
        owner=SOURCE_FACTORY+0x40+i*STRIDE
        raw=blob[owner+0xe1d8:owner+0xe1d8+LENGTH]
        assert len(raw)==LENGTH and raw==bytes(LENGTH)
        source_slots.append({'index':i,'owner_file_offset':hex(owner),'codec_file_offset':hex(owner+0xe1d8),
          'bytes':LENGTH,'sha256':im.sha(raw),'all_zero':True,'actual_current_MAIN_slot_unbound':True})
    regions=[('singleton fixed storage call',0x22a710,0x22a73c),
      ('outer object subobject call',0x22a680,0x22a6c4),
      ('nested factory address calculation',0x22e95c,0x22e9ec),
      ('six common handler constructor loop',0x226d2c,0x226d78),
      ('base handler constructor',0x22c450,0x22c4e8),
      ('common handler constructor first half',0x21d9e0,0x21db30),
      ('common handler constructor second half',0x21db30,0x21dc68),
      ('pool constructor',0x21dcb4,0x21dd18),
      ('pool initialization',0x226778,0x2267fc),
      ('original builder entry',0x221b50,0x221b8c),
      ('mandatory diagnostic and post diagnostic entry',0x221eec,0x221f54),
      ('original common clear wrapper',0x27da9c,0x27dab4)]
    elf=n.ELFFile(n.io.BytesIO(module));init=elf.get_section_by_name('.init.text').data()
    condition=im.dump(init,0x218,0x258,0)
    return {'source_slots':source_slots,'source_factory_file_offset':hex(SOURCE_FACTORY),
      'source_factory_address_arithmetic':'0x541b20 + 0x20a80 + 0x390 = 0x562930; handlers at factory+0x40 + i*0xe518, i=0..5',
      'type_name':'N5imola28imola_common_api_enc_handlerE','vtable_address_point':hex(V+0x37bda8),
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'LIRO_conditional_file_load_instructions':condition,
      'load_condition_scope':'LIRO checks load field and can branch over file-read path. File zero bytes do not establish retained-memory/WBI/current-owner reinitialization.',
      'consumer_tail_field_semantics_or_later_clear_not_established':True}


def run(out):
    prior=BASE/'stage47-runtime-provider-binding/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/e['path']).read_bytes())==e['sha256'],e['path']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    descriptor=bytes.fromhex(json.loads((BASE/'stage33-imola-format-matcher/run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    static=static_evidence(blob,module)
    cases=[]
    for label,seed,candidate in [('fresh_file_stock',None,False),('fresh_file_private16M',None,True),
      ('prior_A5_private16M',0xa5,True),('prior_C3_private16M',0xc3,True)]:
        cases.append(case(blob,module,kernel,descriptor,label,seed,candidate))
    payloads=[bytes.fromhex(c['payload_hex']) for c in cases]
    rate_diff=[i for i,(a,b) in enumerate(zip(*payloads[:2])) if a!=b]
    seed_diff=[i for i,(a,b) in enumerate(zip(*payloads[2:])) if a!=b]
    assert rate_diff==[0x2d,0x2e,0x2f] and seed_diff==EXPECTED_UNWRITTEN
    assert all(payloads[1][i]==0 for i in EXPECTED_UNWRITTEN)
    assert all(payloads[2][i]==0xa5 and payloads[3][i]==0xc3 for i in EXPECTED_UNWRITTEN)
    proof={'status':'PASS_FILE_ORIGIN_COMMON_CONSTRUCTORS_NATIVE_CLEARS_AND_PRIOR_CONTENT_CONTROLS',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'static_evidence':static,'cases':cases,
      'original_fragment_count':sum(len(c['original_fragments']) for c in cases),
      'complete_common_handler_constructor_bodies':sum(c['constructor_slots'] for c in cases),
      'stock_vs_private_rate_diff_offsets':[hex(i) for i in rate_diff],
      'A5_vs_C3_payload_diff_offsets':[hex(i) for i in seed_diff],
      'fresh_file_zero_origin_closed_in_declared_fixture':True,
      'general_runtime_initialization_reuse_or_complete_request_validity_closed':False,
      'important_scope':'The52bytes retain prior values. Six official static slots are zero in the file; complete common constructors do not write their448byte codec blocks. Fresh-file input preserves zero; arbitrary retained controls preserve A5/C3. This is not a demonstrated camera defect or proof that a real slot is reused without another clear.',
      'private16M_scope':'Explicit host private-data copy only. Native compiled writer was separately studied in stage37; no actual Sony hook/loader path implemented here.',
      'no_fake_native_output_or_log_lock_Hal_return':True,
      'whole_kernel_or_firmware_emulation':False,'full_builder_Open_Start_or_Hal':False,
      'real_file_audio_sync_thermal_longrun':False,'actual_camera_or_UU_or_Windows_action':False,
      'current_same_body_backup_or_independent_recovery':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'codec-initialization-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'liro_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_fragment_count','complete_common_handler_constructor_bodies',
      'fresh_file_zero_origin_closed_in_declared_fixture','general_runtime_initialization_reuse_or_complete_request_validity_closed','goal_complete')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();im.volume()
    out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
