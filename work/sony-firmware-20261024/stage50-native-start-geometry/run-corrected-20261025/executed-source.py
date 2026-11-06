#!/usr/bin/env python3
"""Original encoder-side metadata/geometry production and paired predicates.

Channel records, profile metadata and object identities are declared RAM fixtures.
Original setter/getter/copy/selection/packing instructions produce the start-input;
the host does not patch its missing geometry after production. Mandatory log and
wrapper/lock boundaries remain. Independent post-log fragments use another guest
and explicitly copied fixtures, never a fake native return.
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
sys.path.insert(0,str(BASE/'stage49-vcd-consumer-validation'))
import vcd_consumer as v
import baseband_probe as bb
c,im,r,V=v.c,v.im,v.c.r,v.c.V
STATE=r.ARENA+0x180000
RECORDS=r.ARENA+0x200000
MSG=r.ARENA+0x2e0000
META=r.ARENA+0x2e1000
IDENTITY=r.ARENA+0x2e2000
ROW_SIZE=0xd18
START_INPUT=r.SP+0xb8
PRIOR_SHA='607d89313fbd18e8bcf5742e1d4d6bd1a51f45c78cbef4d9a2d7442e5ce7ee34'
EXTRA=[(0x246138,0x246154),(0x24ce04,0x24ce94),
  (0x24cec0,0x24cedc),(0x24cf2c,0x24cfb8),
  (0x24cfb8,0x24d110),(0x24d160,0x24d1c4),
  (0x27b9a8,0x27b9c8),(0x27b7ac,0x27b81c)]


class Guest(c.Guest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,module,kernel)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.update({V+0x24ce94:'before_unexecuted_default_query_wrapper',
          V+0x24cedc:'before_unexecuted_first_geometry_diagnostic',
          V+0x24cfb4:'before_unexecuted_geometry_dump',
          V+0x24d1c0:'before_real_locked_start_wrapper'})
        self.geometry_reads=[]
        self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.geometry_read)

    def geometry_read(self,u,access,address,size,value,user):
        if RECORDS<=address and address+size<=RECORDS+2*ROW_SIZE:
            self.geometry_reads.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
              'address':hex(address),'size':size,'record_index':(address-RECORDS)//ROW_SIZE})


def linked(blob,module,kernel):
    m=Guest(blob,module,kernel);event=c.n.link(m)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    return m,event


def phase(m,label,start,independent=True,**regs):
    m.geometry_reads=[]
    event=c.phase(m,label,V+start,independent=independent,**regs)
    event['geometry_reads']=list(m.geometry_reads)
    global LAST_PHASE
    LAST_PHASE=event
    return event


def independent_guest(source,blob,module,kernel,regs):
    m,loaded=linked(blob,module,kernel)
    m.uc.mem_write(r.ARENA,source.read(r.ARENA,r.ARENA_SIZE))
    m.uc.mem_write(r.STACK,source.read(r.STACK,r.STACK_SIZE))
    for i in range(19):m.regs(**{f'x{i}':0})
    m.regs(x30=r.STOP);m.regs(**regs)
    return m,loaded


def capture(m):
    result={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,30)}
    result['sp']=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    return result


def row(width,height,raw_format=5,packing_flag=1):
    b=bytearray(ROW_SIZE)
    # Actual live record origin/type/lifetime remains unbound. These declared
    # inputs let original encoder-side code choose, copy, and convert fields.
    struct.pack_into('<BB',b,0x28,raw_format,packing_flag)
    struct.pack_into('<10H',b,0x36,width,height,0,0,width,height,0,0,width,height)
    return bytes(b)


def case(blob,module,kernel,vcd,descriptor,label,selected=1,width=1920,height=1080,fmt=5,alter_other=False):
    m,load=linked(blob,module,kernel);events=[load]
    # Native storage shape from official slot0, relocated into declared arena;
    # full common construction was proved separately in stage48, not claimed here.
    slot=blob[0x562970:0x562970+c.STRIDE]
    assert set(slot)=={0};m.uc.mem_write(c.A,slot)
    m.uc.mem_write(c.w.DESC,descriptor)
    e=phase(m,'original codec descriptor copy and stack clear',0x21e26c,x0=c.A,x1=c.w.DESC)
    assert e['reason']=='boundary: after_original_descriptor_copy_and_stack_clear';events.append(e)
    e=phase(m,'independent original row386 preset selection',0x21edc8,x19=c.A,x20=c.w.ROWBLOCK,
      x21=c.w.DESC,x26=V+c.w.v.CREATE_TABLE+386*0x90,x22=c.w.ID)
    assert e['reason']=='boundary: before_actual_buffer_and_channel_preparation';events.append(e)
    private=bytearray(m.read(c.w.PRESET,0x100));struct.pack_into('<I',private,0xb0,249999)
    struct.pack_into('<I',private,0xac,0)
    m.uc.mem_write(c.w.COPY,bytes(private));m.uc.mem_write(c.A+0xe000,r.p64(c.w.COPY))
    m.uc.mem_write(STATE,bytes(0x32000));m.uc.mem_write(STATE,r.p64(IDENTITY))
    m.uc.mem_write(IDENTITY,struct.pack('<I',0x805700f9))
    m.uc.mem_write(STATE+0x20+0x720,descriptor)
    metadata=bytearray(0x88);struct.pack_into('<Q',metadata,0x18,RECORDS)
    struct.pack_into('<I',metadata,0x6c,1) # Explicit input field copied to start-input+fc.
    m.uc.mem_write(META,bytes(metadata))
    m.uc.mem_write(RECORDS,row(3840,2160,8) if alter_other else row(1280,720,5))
    m.uc.mem_write(RECORDS+ROW_SIZE,row(width,height,fmt))
    m.uc.mem_write(MSG,bytes(0x40));m.uc.mem_write(MSG+0x14,struct.pack('<I',selected))
    e=phase(m,'complete original metadata setter into common+7a8',0x246138,x0=STATE+0x20,x1=META)
    assert e['reason']=='returned' and m.read(STATE+0x20+0x7a8,0x88)==bytes(metadata);events.append(e)
    e=phase(m,'original descriptor and metadata copies into stack start-input',0x24ce04,x19=STATE,x20=MSG)
    assert e['reason']=='boundary: before_unexecuted_default_query_wrapper'
    assert m.read(START_INPUT+8,0x88)==descriptor and m.read(START_INPUT+0x90,0x88)==bytes(metadata)
    events.append(e)
    e=phase(m,'independent original metadata getters and channel-index load',0x24cec0,x19=STATE,x20=MSG,x21=STATE+0x20)
    assert e['reason']=='boundary: before_unexecuted_first_geometry_diagnostic';events.append(e)
    regs=capture(m)
    assert regs['x26']==selected and regs['x27']==RECORDS
    # The omitted diagnostic is not executed, skipped, or given a return. This
    # starts a distinct guest at the next explicit post-diagnostic fragment.
    pick,load2=independent_guest(m,blob,module,kernel,regs);events.append(load2)
    e=phase(pick,'independent original record arithmetic and geometry-dump arguments',0x24cf2c,
      independent=False,**regs)
    assert e['reason']=='boundary: before_unexecuted_geometry_dump';events.append(e)
    regs=capture(pick)
    assert regs['x26']==RECORDS+selected*ROW_SIZE+0x48
    assert regs['x27']==RECORDS+selected*ROW_SIZE+0x36
    produced,load3=independent_guest(pick,blob,module,kernel,regs);events.append(load3)
    e=phase(produced,'independent original geometry and format packer after dump',0x24cfb8,
      independent=False,**regs)
    events.append(e)
    raw=produced.read(START_INPUT,0x170)
    source_width,source_height=(1280,720) if selected==0 and not alter_other else (width,height)
    assert struct.unpack_from('<HH',raw,0xe8)==(source_width,source_height)
    native_rows=[rr['record_index'] for z in events for rr in z.get('geometry_reads',[])]
    assert native_rows and set(native_rows)=={selected}
    result={'label':label,'selected_record_fixture':selected,'raw_format_fixture':fmt,
      'other_record_mutated_fixture':alter_other,'start_input_hex':raw.hex(),
      'produced_geometry':list(struct.unpack_from('<8H',raw,0xe0)),
      'produced_f4_f8_fc':list(struct.unpack_from('<3I',raw,0xf4)),
      'producer_stop':e['reason'],'geometry_rows_read':sorted(set(native_rows)),
      'private16M_preset_is_explicit_host_data_fixture':True,
      'host_post_production_geometry_edit':False,'original_fragments':events,
      'actual_live_metadata_registration_and_current_main_channel':False,
      'whole_action_default_query_flags_diagnostics_or_locked_start_executed':False}
    if e['reason']!='boundary: before_real_locked_start_wrapper':
        assert selected==0 and e['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert e['stop_pc']==hex(V+0x27d528)
        result['scope']='Shorter source enters original padding path then stops before its diagnostic. Not a rejection/success or complete padded request.'
        return result
    # Separate normal builder entry, reading the unchanged produced stack input.
    entry=phase(produced,'normal original builder entry consumes native-produced start-input',
      0x221b50,x0=c.A,x1=START_INPUT,x2=c.COMMON,x3=c.CODEC)
    assert entry['reason']=='boundary: after_original_common_64byte_clear';events.append(entry)
    produced.boundaries.pop(V+0x221b8c)
    pre=phase(produced,'same-PC original builder continuation to diagnostic',0x221b8c,independent=False)
    events.append(pre);result['builder_prefix_stop']=pre['reason']
    if width==1921 or fmt==8:
        assert pre['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        result['scope']='Native-produced unsupported/alignment control stops at original builder diagnostic. No error-return/success adapter.'
        return result
    assert pre['reason']=='boundary: before_unexecuted_unconditional_diagnostic'
    regs=capture(produced);post,load4=independent_guest(produced,blob,module,kernel,regs);events.append(load4)
    fin=phase(post,'independent original post-diagnostic builder body on produced-input fixture',
      0x221f50,independent=False,**regs)
    assert fin['reason']=='boundary: post_diagnostic_body_success_marker_before_epilogue';events.append(fin)
    common=post.read(c.COMMON,0x40);codec=post.read(c.CODEC,0x1c0)
    assert struct.unpack_from('<2I',common,0xc)==(width,height)
    words=struct.unpack_from('<3I',codec,0x2c)
    assert ((words[0]>>8)+1)<<(6+(words[0]&255))==16000000
    a=bb.BasebandGuest(vcd,common)
    a.uc.reg_write(v.reg.UC_MIPS_REG_A1,0);a.uc.reg_write(v.reg.UC_MIPS_REG_A2,0)
    basecheck=a.run(label+' original VCD baseband predicate',0x1a81cc)
    configcheck=v.Guest(vcd,codec).run(label+' original VCD config predicate')
    assert basecheck['native_v0']==configcheck['native_v0']=='0x0'
    result.update(common_hex=common.hex(),codec_hex=codec.hex(),
      common_geometry=list(struct.unpack_from('<2I',common,0xc)),
      common_format=common[0x28],common_pitch=struct.unpack_from('<I',common,0x24)[0],
      VCD_baseband_predicate=basecheck,VCD_config_predicate=configcheck,
      decoded_target=16000000,
      scope='Original encoder-side selected-record packing feeds separate builder fragments and original pure VCD predicates. Declared metadata/indices/flags/owner and post-log inputs remain fixtures; not whole Start, actual live record, clocks, encoding or recovery.')
    assert produced.read(START_INPUT,0x170)==raw and post.read(START_INPUT,0x170)==raw
    c.assert_image(produced,blob);c.assert_image(post,blob)
    return result


def run(out):
    prior=v.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(c.n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(c.n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    vcd=v.VCD_PATH.read_bytes();assert im.sha(vcd)==im.PINS[str(v.VCD_PATH.relative_to(BASE))]
    descriptor=bytes.fromhex(json.loads((BASE/'stage33-imola-format-matcher/run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    cases=[]
    for label,kw in [('selected1_raw5',{}),('selected1_raw6',{'fmt':6}),
      ('selected1_unrelated_row_changed',{'alter_other':True}),
      ('selected0_shorter_source_padding',{'selected':0}),
      ('selected1_width1921',{'width':1921}),('selected1_raw8',{'fmt':8})]:
        cases.append(case(blob,module,kernel,vcd,descriptor,label,**kw))
    assert cases[0]['start_input_hex']==cases[2]['start_input_hex']
    assert cases[0]['common_hex']==cases[2]['common_hex'] and cases[0]['codec_hex']==cases[2]['codec_hex']
    assert cases[0]['common_pitch']==2400 and cases[1]['common_pitch']==2880
    assert cases[0]['common_format']==13 and cases[1]['common_format']==14
    regions=[('original metadata setter and getters',0x246138,0x246154),
      ('original stack input copies',0x24ce04,0x24ce94),
      ('original channel index and array pointer getters',0x24cec0,0x24cedc),
      ('original selected-record address calculation',0x24cf2c,0x24cf68),
      ('original geometry-format production',0x24cfb8,0x24d0bc),
      ('original handoff to real locked start wrapper',0x24d1a8,0x24d1c4),
      ('original geometry consumer',0x221df0,0x221e24),
      ('raw metadata format conversion',0x27b9a8,0x27b9c8),
      ('metadata setter caller',0x24c1c0,0x24c1dc)]
    proof={'status':'PASS_ORIGINAL_SELECTED_RECORD_PRODUCER_AND_PAIRED_PREDICATES_WITH_RUNTIME_GAPS',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':cases,
      'original_A64_fragments':sum(len(z['original_fragments']) for z in cases),
      'original_MIPS_predicates':sum(2 for z in cases if 'VCD_baseband_predicate' in z),
      'encoder_source_name':im.cstring(blob,0x443dc5),
      'rejected_same_offset_source':{'address':'0x23d964','source_name':im.cstring(blob,0x43f3fd),
        'reason':'Decoder source is not used as the MAIN encoder input producer; similar offsets alone do not bind owners.'},
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'slot_graph':'metadata setter stores88bytes in(STATE+20)+7a8; getter returns it; +18 is channel-array pointer. Start-message+14 supplies index; originalmadd usesstride d18. This graph is a declared RAM fixture, not actual channel registration.',
      'geometry_origin':'selected record+3e/+40 -> start-input+e8/+ea -> COMMON+c/+10; produced by original instructions, no host geometry repair.',
      'general_native_start_input_producer_or_full_valid_start_request_complete':False,
      'source_record_origin_live_MAIN_slot_flag_setup_default_query_order_locks_logs_Hal_unbound':True,
      'configuration_predicates_do_not_prove_numeric16M_or_hardware':True,
      'UU_Windows_camera_module_WBI_or_flash':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'start-geometry-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'VCD_sha256':im.sha(vcd),'kernel_sha256':im.sha(kernel),'LIRO_sha256':im.sha(module),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_A64_fragments','original_MIPS_predicates',
      'general_native_start_input_producer_or_full_valid_start_request_complete','goal_complete')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in globals():im.write_json(out/'last-phase-at-failure.json',LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
