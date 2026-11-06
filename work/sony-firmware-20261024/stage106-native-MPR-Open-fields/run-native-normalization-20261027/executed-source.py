#!/usr/bin/env python3
"""Original MPR type selection and conditional Open-field production.

Every logging gap starts a separately declared experiment with the carried
register/memory input. Logger effects are unexecuted, not fabricated. Pure
helpers return by original instructions. No normal whole-Open claim is made.
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
sys.path.insert(0,str(BASE/'stage105-native-main-parameter-producer'))
import main_parameter as prev
pp,r,im=prev.pp,prev.r,prev.im
MPR=pp.MPR
SP=prev.SP
INPUT=pp.SCRATCH+0x1000
OUTPUT=pp.SCRATCH+0x3000
PRIOR=prev.STAGE/'final-receipt.json'
PRIOR_SHA='8d8592a8fdffb4e029d868ba2e7b61f66cd21f10c14c68d7ab458319e8ed824c'
MPR_SHA='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
ENTRIES=(0xcd40c,0xd13f8,0xcf7bc,0xcf884,0xd1338,0x2c0d04,
         0xcf984,0xd0758,0xd0d1c,0xd0800,0xd11b0,0xd1274,0x282390,0x2823a0)
PROFILES=(('target_HEVC_HD420',6,6,3),('HEVC_UHD420_control',5,13,3),
          ('HEVC_UHD422_control',7,6,3),('AVC_HD8_control',1,6,3),
          ('table_row8_negative_control',8,6,3))


def sha(d):return hashlib.sha256(d).hexdigest()


def ranges():
    out=[]
    for a in ENTRIES:
        s=next(s for s in MPR.symbols.values() if s['va']==a and s['size'])
        out.append((a,a+s['size']))
    return out


class Guest(pp.StrictMicro):
    def __init__(self,seed):
        super().__init__(MPR,ranges(),resolve=True)
        self.allowed.append((0x282b08,0x282b20))
        self.uc.mem_write(pp.STACK_BASE,bytes([seed])*pp.STACK_SIZE)
        self.uc.mem_write(pp.SCRATCH,bytes([seed^0x3c])*0x10000)
        self.log_entries={}
        for a,z in self.allowed:
            for i in MPR.md.disasm(MPR.read(a,z-a),a):
                if i.mnemonic=='bl' and i.op_str=='#0xc8c70':self.log_entries[i.address+4]=i.address
        self.log_gaps=[]
        self.reads=[]
        self.hooks.append(self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe))
        self.original_relocated_image=[(s['p_vaddr'],bytes(self.uc.mem_read(s['p_vaddr'],s['p_memsz']))) for s in MPR.segments]

    def observe(self,u,access,at,size,value,user):
        table=MPR.symbols['_ZN3mpr16g_videoParamCombE'];a=table['va'];z=a+table['size']
        if at<z and at+size>a:
            assert a<=at and at+size<=z
            self.reads.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
                'table_offset':hex(at-a),'size':size,'actual_guest_bytes':bytes(u.mem_read(at,size)).hex()})

    def code(self,u,pc,size,user):
        if pc==0x282b20:
            self.pcs.append(hex(pc));self.abort('boundary: before_unexecuted_Codec_Open_global_state');return
        if pc==0xc8c70:
            self.pcs.append(hex(pc));self.abort('boundary: original_logger_unexecuted');return
        return super().code(u,pc,size,user)

    def phase(self,label,entry,outputs=(),**regs):
        stack_before=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        scratch_before=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for name,v in regs.items():self.uc.reg_write(getattr(r.reg,'UC_ARM64_REG_'+name.upper()),v)
        self.reason=None;self.steps=0;self.pcs=[];self.stores=[];self.calls=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=10000,timeout=1000000)
        assert self.reason is not None
        assert self.reason in ('returned','boundary: original_logger_unexecuted',
            'boundary: before_unexecuted_Codec_Open_global_state'),self.reason
        for w in self.stores:
            a,n=int(w['address'],16),w['size']
            assert SP-0x200<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        stack_after=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert stack_after[:SP-0x200-pp.STACK_BASE]==stack_before[:SP-0x200-pp.STACK_BASE]
        assert stack_after[SP-pp.STACK_BASE:]==stack_before[SP-pp.STACK_BASE:]
        scratch_after=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        changed=[pp.SCRATCH+i for i,(a,b) in enumerate(zip(scratch_before,scratch_after)) if a!=b]
        assert all(any(a<=q<z for a,z in outputs) for q in changed)
        assert all('stub' not in c for c in self.calls)
        for a,d in self.original_relocated_image:assert bytes(self.uc.mem_read(a,len(d)))==d
        return {'label':label,'entry':hex(entry),'reason':self.reason,
            'stop_pc':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
            'SP_after':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
            'pcs':self.pcs,'original_local_PLT_and_return_observations':self.calls,
            'stores':self.stores,'original_table_reads':self.reads,
            'whole_stack_outside_200_byte_declared_frame_unchanged':True,
            'whole_scratch_outside_declared_outputs_unchanged':True,
            'whole_original_relocated_ELF_image_unchanged':True,
            'stubs_logger_or_success_return_adapters_executed':False}

    def call_slices(self,label,entry,args,outputs=()):
        # Each boundary is a real original log call. Subsequent entry is a new
        # independent post-log experiment, not execution/return of that logger.
        saved={i:self.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,30)}
        regs={'sp':SP,'x30':pp.STOP}
        regs.update({'x'+str(i):v for i,v in enumerate(args)})
        events=[self.phase(label+' original prologue',entry,outputs,**regs)]
        for n in range(40):
            if events[-1]['reason']=='returned':break
            lr=self.uc.reg_read(r.reg.UC_ARM64_REG_X30)
            assert lr in self.log_entries,hex(lr)
            gap={'original_callsite':hex(self.log_entries[lr]),'new_independent_entry':hex(lr),
                'all_current_register_and_memory_values_declared_carried_inputs':True,
                'actual_logger_effects_or_normal_continuity_proven':False}
            self.log_gaps.append(gap)
            events.append(self.phase(label+' independent input after log '+str(n+1),lr,outputs))
        assert events[-1]['reason']=='returned'
        assert self.uc.reg_read(r.reg.UC_ARM64_REG_SP)==SP
        assert all(self.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))==v for i,v in saved.items())
        return events,self.uc.reg_read(r.reg.UC_ARM64_REG_X0)

    def close(self):
        for h in self.hooks:self.uc.hook_del(h)


def produce(seed,profile):
    label,vpc,quality,frame=profile;m=Guest(seed)
    try:
        queries=[]
        for stream in (0,1):
            e,value=m.call_slices('original format category stream '+str(stream),0xcd40c,[vpc,stream])
            assert value==((15 if vpc in (5,6,7,8) else 5) if stream==0 else (18 if vpc in (5,6,7,8) else 17))
            queries.append({'stream_selector':stream,'native_file_format_category':value,'events':e,
                'category_not_same_instance_or_actual_encoder_binding':True})
        inp=bytearray(0x7a0)
        struct.pack_into('<III',inp,0x764,vpc,quality,frame)
        struct.pack_into('<I',inp,0x770,0) # declared audio combination, not audio capture
        inp[0x774]=2
        struct.pack_into('<H',inp,0x778,1) # declared active-video condition
        m.uc.mem_write(INPUT,bytes(inp));m.uc.mem_write(OUTPUT,bytes([seed])*0x98)
        events,ret=m.call_slices('original MPR SetEncOpenParam',0xd13f8,[INPUT,OUTPUT],[(OUTPUT,OUTPUT+0x98)])
        before_normalization=bytes(m.uc.mem_read(OUTPUT,0x98))
        e=m.phase('independent original Codec Open audio/quality normalization body',0x282b08,
            [(OUTPUT,OUTPUT+0x98)],x19=OUTPUT)
        events.append(e);assert e['reason']=='boundary: before_unexecuted_Codec_Open_global_state'
        raw=bytes(m.uc.mem_read(OUTPUT,0x98));assert bytes(m.uc.mem_read(INPUT,len(inp)))==bytes(inp)
        assert raw[0x82]==before_normalization[0x82]
        assert struct.unpack_from('<HH',raw,0x68)==((3840,2160) if vpc in (5,7) else (1920,1080))
        assert raw[0x94]==(254 if vpc==8 else (2 if vpc==7 else 0))
        assert raw[0x95]==(254 if vpc==8 else (0 if vpc==1 else 1))
        assert raw[0x66]==(3 if vpc==1 else 15)
        written=set()
        for e in events:
            for w in e['stores']:
                a=int(w['address'],16)-OUTPUT
                if a<0x98 and a+w['size']>0:written.update(range(max(0,a),min(0x98,a+w['size'])))
        return {'label':label,'seed':seed,'declared_core_vpc_quality_frame':[vpc,quality,frame],
            'category_queries':queries,'raw98_hex':raw.hex(),
            'raw98_before_codec_normalization_hex':before_normalization.hex(),
            'original_builder_events':events,
            'log_gaps':m.log_gaps,'local_ELF_relocations_count':len(m.resolved),
            'local_ELF_relocations_sha256':sha(json.dumps(m.resolved,separators=(',',':')).encode()),
            'unwritten_output_offsets':[hex(i) for i in range(0x98) if i not in written],
            'core_fields':{'geometry':list(struct.unpack_from('<HH',raw,0x68)),
                'video_codec66':raw[0x66],'frame80':raw[0x80],'scan81':raw[0x81],
                'quality82':raw[0x82],'chroma94':raw[0x94],'depth95':raw[0x95]},
            'runtime_buffer_addresses_owners_and_active_video_state_not_bound':True,
            'complete_valid_Open_packet_normal_logging_or_recording_proven':False}
    finally:m.close()


def classify(blob,producer):
    # Original scalar consumers with exact extracted fields, not a submitted Open.
    chain=prev.prev.prev.src.prev
    source=bytes.fromhex(producer['raw98_hex']);m=chain.Guest(blob,producer['seed'])
    fmt=producer['category_queries'][0]['native_file_format_category']
    specs=(('coding',0x134d44,0x134ec0,fmt,source[0x66],0x27dd14,0x27dd38),
        ('frame',0x134bf4,0x134cc4,source[0x80],source[0x7a],0x27dcf0,0x27dd14),
        ('quality',0x134fcc,0x1352f8,source[0x82],0,0x27dd64,0x27dd88),
        ('chroma',0x1352f8,0x13538c,source[0x94],0,0x27debc,0x27dee0),
        ('depth',0x13538c,0x135400,source[0x95],0,0x27dee0,0x27df04))
    m.ranges.extend((chain.V+a,chain.V+z) for _,a,z,_,_,c,d in specs for a,z in ((a,z),(c,d)))
    decoded={};events=[]
    for name,a,z,first,second,c,d in specs:
        e=m.phase('original avcam scalar conversion '+name,a,x0=chain.r.ARENA,x1=first,x2=second)
        events.append(e);assert e['reason']=='returned';value=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)
        e=m.phase('original avcam enum name '+name,c,x0=value);events.append(e);assert e['reason']=='returned'
        ptr=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)
        decoded[name]={'scalar_inputs':[first,second],'native_enum':value,'original_name':im.cstring(blob,ptr-chain.V,180)}
    vpc=producer['declared_core_vpc_quality_frame'][0]
    assert decoded['coding']['original_name']==('XAVCS_MP4' if vpc==1 else 'HEVC_MP4'),decoded
    if vpc!=8:
        assert decoded['chroma']['original_name']==('CHROMA_422' if vpc==7 else 'CHROMA_420')
        assert decoded['depth']['original_name']==('BIT_DEPTH_8' if vpc==1 else 'BIT_DEPTH_10')
    else:
        assert decoded['chroma']['original_name'] not in ('CHROMA_420','CHROMA_422')
        assert decoded['depth']['original_name'] not in ('BIT_DEPTH_8','BIT_DEPTH_10')
    assert decoded['frame']['original_name']=='29_97'
    return {'label':producer['label'],'seed':producer['seed'],'original_MPR_file_format':fmt,
        'decoded':decoded,'events':events,'scalar_values_not_edited_between_original_producer_and_consumers':True,
        'full_receiver_builder_or_real_SPS_MAIN_hardware_or_recovery_proven':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    assert sha(MPR.path.read_bytes())==MPR_SHA
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        produced=[produce(seed,p) for seed in (0xa5,0xc3) for p in PROFILES]
        chain=prev.prev.prev.src.prev;blob=chain.IMAGE.read_bytes()
        (a.out/'producer-checkpoint.json').write_text(json.dumps(produced,ensure_ascii=False,indent=2)+'\n')
        classified=[classify(blob,p) for p in produced]
        retained=[]
        for profile in PROFILES:
            x,y=[p for p in produced if p['label']==profile[0]]
            assert x['core_fields']==y['core_fields']
            retained.append({'label':profile[0],'seed_dependent_offsets':[hex(i) for i,(a,b) in enumerate(zip(bytes.fromhex(x['raw98_hex']),bytes.fromhex(y['raw98_hex']))) if a!=b],
                'caller_memset_and_real_buffers_unexecuted_not_a_firmware_defect':True})
        phases=sum(len(p['original_builder_events'])+sum(len(q['events']) for q in p['category_queries']) for p in produced)+sum(len(c['events']) for c in classified)
        j={'status':'PASS_ORIGINAL_MPR_OPEN_FIELDS_CLASSIFY_TARGET_AS_HEVC_MP4_HD42010',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_mpr_sha256':MPR_SHA,'original_avcam_sha256':sha(blob),'produced':produced,
            'native_classifications':classified,'retained_output_scope':retained,'bounded_phases':phases,
            'all_log_gaps_are_independent_declared_inputs_not_actual_log_returns':True,
            'same_ELF_resolved_local_GOT_is_guest_fixture_not_actual_camera_loader':True,
            'upstream_MAIN_producer_gap_from_stage105_not_solved':True,
            'actual_codec_Open_instance_SPS_16M_hardware_audio_longrun_recovery_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'mpr-open-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'profiles':len(produced),'classifications':len(classified),'bounded_phases':phases}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise


if __name__=='__main__':main()
