#!/usr/bin/env python3
"""Original NRT metadata initialization/conversion and format classification.

Setter tuples, writer-state storage and original-map-derived node fixtures are
declared inputs. No native output/printf/allocator/return adapters or camera I/O.
The map fixture is not a claim of executing C++ global constructors/allocation.
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
sys.path.insert(0,str(BASE/'stage54-native-open-matcher-input'))
import open_matcher_input as prev
im,pp=prev.im,prev.pp
r=prev.r
MPR=pp.MPR
S=pp.SCRATCH
INPUT=S+0x1000
VIDEO=S+0x3000
AUDIO=S+0x4000
WIRE=S+0x5000
NODES=S+0x6000
MAP=0x3b4958
PRIOR_SHA='c19cee953e4977dee1a2f1825e07dfb491e8bbc965ef5a6e488ff3deb4db939f'
RANGES=[(0x115e18,0x116794),(0x2c0de8,0x2c0e98),(0x2c0f28,0x2c0f4c),
  (0x117a6c,0x117ae0),(0x242b84,0x242c4c),(0x24d79c,0x24d844),
  (0x247b14,0x247b6c),(0x24d394,0x24d40c)]
# Native initializer callsites, its literal inputs, and its value-MOV sites.
MAP_SOURCES=[(0x24b67c,7680,4320,1,11,0x24b684),
  (0x24b6b4,7680,4320,1,10,0x24b6bc),
  (0x24b6e4,3840,2160,1,9,0x24b6ec),
  (0x24b714,3840,2160,1,8,0x24b71c),
  (0x24b748,3840,2160,1,7,0x24b750),
  (0x24b778,3840,2160,2,9,0x24b780),
  (0x24b7a8,3840,2160,2,8,0x24b7b0),
  (0x24b7d8,3840,2160,2,7,0x24b7e0)]


def instructions(a,z):
    return [{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
      for i in MPR.md.disasm(MPR.read(a,z-a),a)]


class Guest(pp.StrictMicro):
    def __init__(self):
        super().__init__(MPR,list(RANGES),resolve=True)
        self.boundaries={0x24d6a4:'before_alternate_record_format_classifier',
          0x24d458:'before_unbound_map_insertion'}
        self.input_reads=[]
        self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe_read)

    def code(self,u,address,size,user):
        if address in self.boundaries:
            self.pcs.append(hex(address));self.steps+=1
            self.abort('boundary: '+self.boundaries[address]);return
        return super().code(u,address,size,user)

    def observe_read(self,u,access,address,size,value,user):
        if INPUT<=address and address+size<=INPUT+0x200:
            self.input_reads.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
              'state_offset':hex(address-INPUT),'size':size})


def phase(m,label,entry,args):
    # Keep hooks for successive original functions on the same guest. The old
    # one-shot Micro.run removes them, so it is deliberately not called here.
    m.reason=None;m.pcs=[];m.steps=0;m.calls=[];m.writes=[];m.packet_writes=[];m.stores=[]
    m.log_proofs=[];m.pending_log=None;m.input_reads=[]
    m.uc.reg_write(r.reg.UC_ARM64_REG_SP,pp.STACK)
    m.uc.reg_write(r.reg.UC_ARM64_REG_LR,pp.STOP)
    for i,value in enumerate(args):m.uc.reg_write(getattr(r.reg,'UC_ARM64_REG_X'+str(i)),value)
    m.uc.emu_start(entry,0,count=20000,timeout=1000000)
    assert m.reason is not None,'bounded execution finished without an approved stop'
    e={'label':label,'entry':hex(entry),'reason':m.reason,
      'stop_pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
      'return_u64':m.uc.reg_read(r.reg.UC_ARM64_REG_X0),
      'SP_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
      'pcs':list(m.pcs),'calls':list(m.calls),'stores':list(m.stores),
      'input_state_reads':list(m.input_reads),
      'independent_function_entry_inputs':True,'native_output_printf_allocator_PC_return_adapter':False}
    if m.reason=='returned':assert e['SP_after']==hex(pp.STACK)
    if m.reason=='unapproved PLT printf':
        e['printf_arguments']=[hex(m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in (0,1)]
    global LAST_PHASE
    LAST_PHASE=e
    return e


def assert_code(m):
    for seg in MPR.segments:
        if seg['p_flags']&1:assert bytes(m.uc.mem_read(seg['p_vaddr'],seg['p_filesz']))==seg.data()


def original_map_pairs():
    m=Guest();pairs=[];events=[]
    for site,w,h,profile,level,id_site in MAP_SOURCES:
        call=instructions(site,site+4)[0]
        assert call['asm']=='bl #0x242b84'
        mov=instructions(id_site,id_site+4)[0]
        assert mov['asm'].startswith('mov w0, #')
        value=int(mov['asm'].split('#')[1],0)
        packed=w|(h<<16)|(profile<<32)
        e=phase(m,'original HEVC key from initializer literals '+hex(site),0x242b84,[packed,level])
        assert e['reason']=='returned' and e['return_u64']!=(1<<64)-1
        events.append(e);pairs.append({'width':w,'height':h,'profile_enum':profile,'level_enum':level,
          'native_key':e['return_u64'],'map_value':value,'source_key_call':hex(site),
          'source_value_mov':mov})
    assert len({p['native_key'] for p in pairs})==8
    assert [p['map_value'] for p in pairs]==list(range(0x8b,0x93))
    assert_code(m)
    return pairs,events


def fixture_map(m,pairs):
    rows=sorted(pairs,key=lambda p:p['native_key'])
    addresses=[NODES+i*0x40 for i in range(len(rows))]
    sentinel=MAP+8
    # A declared balanced lookup tree. Original default pairs supply keys and
    # values; node allocation, balancing and global construction are unexecuted.
    m.uc.mem_write(MAP,bytes(0x30))
    def branch(lo,hi,parent):
        if lo>=hi:return 0
        mid=(lo+hi)//2;at=addresses[mid]
        left=branch(lo,mid,at);right=branch(mid+1,hi,at)
        data=bytearray(0x30)
        struct.pack_into('<QQQQI',data,8,parent,left,right,rows[mid]['native_key'],rows[mid]['map_value'])
        m.uc.mem_write(at,bytes(data));return at
    top=branch(0,len(rows),sentinel)
    m.uc.mem_write(MAP+0x10,struct.pack('<4Q',top,addresses[0],addresses[-1],len(rows)))
    return {'global_map_header':hex(MAP),'node_storage':hex(NODES),'entries':8,
      'original_default_pairs':rows,'native_map_ctor_allocator_or_balancing_executed':False}


def fields(raw):
    u=lambda at:struct.unpack_from('<I',raw,at)[0]
    return {'valid_byte0':raw[0],'record_format_enum4':u(4),'profile_enum8':u(8),
      'level_enum14':u(0x14),'rate_2c_30':list(struct.unpack_from('<2I',raw,0x2c)),
      'rate_34_38':list(struct.unpack_from('<2I',raw,0x34)),
      'width_height_3c_3e':list(struct.unpack_from('<2H',raw,0x3c)),
      'bitrate_raw40':u(0x40),'interlace_byte44':raw[0x44],
      'byte45':raw[0x45],'alternate_classifier_byte46':raw[0x46]}


def one_case(label,triple,seed,pairs,input4=0):
    m=Guest();events=[];vpc,quality,frame=triple
    state=bytearray(0x200);struct.pack_into('<I',state,4,input4)
    struct.pack_into('<5I',state,0x11c,frame,vpc,quality,0,0)
    m.uc.mem_write(INPUT,bytes(state));m.uc.mem_write(VIDEO,bytes([seed])*0x48)
    m.uc.mem_write(AUDIO,bytes([seed])*0x64)
    for entry,address,name in ((0x115e18,VIDEO,'video'),(0x115e54,AUDIO,'eight-slot audio')):
        e=phase(m,'original '+name+' metadata initializer '+label,entry,[address])
        assert e['reason']=='returned';events.append(e)
    init_video=bytes(m.uc.mem_read(VIDEO,0x48))
    e=phase(m,'complete original writer metadata converter '+label,0x115fec,[0,INPUT,VIDEO,AUDIO])
    events.append(e);raw=bytes(m.uc.mem_read(VIDEO,0x48));audio=bytes(m.uc.mem_read(AUDIO,0x64))
    out=fields(raw);wire=None;classified=None;map_info=None
    written=set()
    for ev in events:
        for st in ev['stores']:
            at=int(st['address'],16);size=st['size']
            written.update(range(max(0,at-VIDEO),min(0x48,at+size-VIDEO)))
    untouched=[i for i in range(0x48) if i not in written]
    if quality==8:
        assert e['reason']=='unapproved PLT printf' and out['valid_byte0']==0
        assert hex(0x115ee8) in e['pcs'] and out['bitrate_raw40']==25000
    else:
        assert e['reason']=='returned' and e['return_u64']==0 and out['valid_byte0']==1
        assert e['pcs'][-2]=='0x116768'
        expected_geometry=[3840,2160] if vpc==5 else [1920,1080]
        assert out['width_height_3c_3e']==expected_geometry
        assert out['bitrate_raw40']=={6:16000,26:9000,13:150000}[quality]
        assert out['rate_2c_30']==out['rate_34_38']==([60000,1001] if frame==7 else [30000,1001])
        assert out['record_format_enum4']==5 and out['alternate_classifier_byte46']==input4
        m.uc.mem_write(WIRE,struct.pack('<I',0xa5a5a5a5))
        e2=phase(m,'original MPF profile/level conversion '+label,0x117a6c,
          [0,vpc,out['level_enum14'],out['profile_enum8'],WIRE]);events.append(e2)
        assert e2['reason']=='returned';wire=int.from_bytes(m.uc.mem_read(WIRE,4),'little')
        map_info=fixture_map(m,pairs)
        e3=phase(m,'original record-format classification on source-derived map fixture '+label,0x24d79c,[VIDEO])
        events.append(e3)
        if input4:
            assert e3['reason']=='boundary: before_alternate_record_format_classifier'
        else:
            assert e3['reason']=='returned'
            classified=e3['return_u64']&0xffffffff
            assert classified==(0x8e if vpc==5 else 0x97)
        assert bytes(m.uc.mem_read(VIDEO,0x48))==raw
    assert bytes(m.uc.mem_read(INPUT,len(state)))==bytes(state)
    assert_code(m)
    return {'label':label,'input_vpc_quality_frame':triple,'declared_state4':input4,
      'prior_metadata_seed':seed,'initialized_video_hex':init_video.hex(),
      'video_metadata_hex':raw.hex(),'audio_metadata_hex':audio.hex(),'observed_fields':out,
      'metadata_span_observed_bytes':0x48,'bytes_not_written_by_initializers_or_converter':untouched,
      'untouched_bytes_not_globally_unused_or_safe_to_overwrite':True,
      'native_MPF_profile_level_enum':wire,'native_record_format_classification_enum':classified,
      'map_fixture':map_info,'original_events':events,
      'full_writer_state_binding_MP4_mux_open_file_output_or_real_audio_encoding':False}


def run(out):
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    source=BASE/'stage12-prototype/profile/profile-results.json';old=json.loads(source.read_text())
    target=old['experimental_target_setter']['output_vpc_quality_frame'];assert target==[6,6,3]
    stock=[x['stock_setter']['output_vpc_quality_frame'] for x in old['legitimate_HS_cases']
      if x['case']=={'frame':0,'q60':12}];assert stock==[[5,13,7]]
    pairs,key_events=original_map_pairs()
    cases=[one_case('target16M priorA5',target,0xa5,pairs),
      one_case('target16M priorC3',target,0xc3,pairs),
      one_case('artificial upperFF quality8',[6,8,3],0xa5,pairs),
      one_case('off-target HD9M control',[6,26,3],0xa5,pairs),
      one_case('stock UHD150M control',stock[0],0xa5,pairs),
      one_case('target16M alternate input4 control',target,0xa5,pairs,input4=1)]
    assert cases[0]['observed_fields']==cases[1]['observed_fields']
    regions=[('original video/audio initializers',0x115e18,0x115e78),
      ('VPC quality level helper',0x115e78,0x115fec),('full metadata converter prefix',0x115fec,0x1161d8),
      ('full metadata converter video fields',0x1161d8,0x1162a0),
      ('full metadata converter normal completion',0x116730,0x116794),
      ('MPF profile/level conversion',0x117a6c,0x117ae0),
      ('record format classifier',0x24d79c,0x24d844),('HEVC format key',0x242b84,0x242c4c),
      ('default HEVC map initializer',0x24b634,0x24b808),
      ('actual caller initializers before metadata conversion',0x11d8ac,0x11d8d0),
      ('actual caller passes output buffers',0x11d910,0x11d92c)]
    proof={'status':'PASS_ORIGINAL_MUX_METADATA_WITH_HD_FORMAT_CLASSIFICATION_GAP',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_fragments':len(key_events)+sum(len(x['original_events']) for x in cases),
      'original_key_events':key_events,'original_default_map_pairs':pairs,'cases':cases,
      'original_regions':[{'name':name,'instructions':instructions(a,z)} for name,a,z in regions],
      'target_setter_output_supplied_to_writer_state_as_explicit_input_not_full_runtime_handoff':True,
      'target16M_metadata_converts_with_original_initializers_normal_return':True,
      'upperFF_quality8_enters_original_Conv_ERROR_printf_boundary':True,
      'HEVC_key_function_rejects1920_width_and_target_level5':True,
      'HD_classifier_fallback97_on_original_default_pairs_fixture_not_full_global_ctor':True,
      'fallback_effect_on_actual_mux_admission_description_or_file_writing_unresolved':True,
      'original_MPR_code_unchanged':True,'native_output_printf_allocator_PC_return_adapter':False,
      'camera_UU_Windows_files_module_WBI_flash':False,
      'hardware_recording_backup_restore_or_independent_recovery':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'mux-identity-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'MPR_sha256':im.sha(MPR.blob),'APP_sha256':im.sha(pp.APP.blob),
      'setter_result_sha256':im.sha(source.read_bytes()),'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'original_fragments':proof['original_fragments'],
      'cases':[(x['label'],x['observed_fields']['bitrate_raw40'],x['native_record_format_classification_enum']) for x in cases],
      'goal_complete':False}))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in globals():im.write_json(out/'last-phase-at-failure.json',LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
