#!/usr/bin/env python3
"""Original streaming Open profile fields and native scalar classification.

Only a post-DMM producer body executes. Output address, source Open fields and
model state are explicit. No allocation result, memset, transport, log return,
normal Open, real encoder instance, actual stream or card MAIN is synthesized.
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
sys.path.insert(0,str(BASE/'stage102-native-app-qos-producer'))
import app_qos as prev
r,im,APP,pp=prev.r,prev.im,prev.APP,prev.pp
PARAM=pp.SCRATCH+0x100
RESULT=pp.SCRATCH+0x400
RAW=pp.SCRATCH+0x2000
PRIOR=BASE/'stage102-native-app-qos-producer/final-receipt.json'
PRIOR_SHA='4098a2dc80d5681415a1e35f36fef4ca2489bf61d2f0eb389e402f0eedd6596b'
PROFILES=(
    ('HEVC_HD_base0',2,0,1,1),('HEVC_HD_base1',2,1,1,1),
    ('AVC_HD_base0',2,0,0,1),('HEVC_UHD_base0',0,0,1,1))


def sha(raw):return hashlib.sha256(raw).hexdigest()


class AppOpenGuest(prev.AppGuest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0x2de7364,0x2de73b8),(0x2de74a8,0x2de7fc0)])
        self.boundaries[0x2f6fe3c]='before_original_input_diagnostic'


def parameter(resolution,frame,codec,kind):
    # This is not the whole preceding mc_enc_open producer or a DMM mapping.
    # The original parent clears a B8-byte temporary and sets these offsets;
    # the caller's real object values and actual buffer ownership are unknown.
    p=bytearray(0xb8)
    for at,value in ((8,0x50000000),(0x20,0x51000000),(0x48,0x52000000),
                     (0x58,0x53000000),(0x68,0x54000000),(0x80,0x55000000),(0x98,0x56000000)):
        struct.pack_into('<Q',p,at,value)
    for at,value in ((0x10,0x400000),(0x28,0x80000),(0x50,0x80),(0x60,0x80),(0x70,0x100),
                     (0xa8,resolution),(0xac,frame),(0xb0,codec),(0xb4,kind)):
        struct.pack_into('<I',p,at,value)
    return bytes(p)


def build(seed,profile):
    label,resolution,frame,codec,kind=profile
    p=parameter(resolution,frame,codec,kind)
    m=AppOpenGuest(seed)
    try:
        m.uc.mem_write(PARAM,p);m.uc.mem_write(RAW,bytes([seed])*0x98)
        events=[m.phase('original mc_avsc_enc_open_i prologue before first logger',0x2de7364,
                        stack_bytes=0x150,sp=prev.APP_SP,x30=pp.STOP,x0=PARAM,x1=RESULT)]
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X20)==PARAM
        fp=m.uc.reg_read(r.reg.UC_ARM64_REG_X29)
        assert fp==prev.APP_SP-0x150
        # Independent post-DMM address: do not fill a fabricated successful
        # allocator result or claim the omitted map/header calls completed.
        events.append(m.phase('independent post-DMM original profile producer',0x2de74a8,
                              stack_bytes=0x150,scratch_outputs=[(RAW,RAW+0x98)],x19=RAW))
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        raw=bytes(m.uc.mem_read(RAW,0x98))
        fmt=bytes(m.uc.mem_read(fp+0xe4,1))[0]
        assert fmt==(0x31 if codec==1 else 0x30)
        assert raw[0x66]==(0x10 if codec==1 else 4)
        assert struct.unpack_from('<HH',raw,0x68)==((1920,1080) if resolution==2 else (3840,2160))
        assert raw[0x94:0x96]==bytes(2)
        assert raw[0x96:0x98]==bytes([seed])*2
        assert bytes(m.uc.mem_read(PARAM,len(p)))==p
        return {'label':label,'seed':seed,'declared_parameter_B8_hex':p.hex(),
                'declared_controls':{'resolution_a8':resolution,'frame_ac':frame,'codec_b0':codec,'kind_b4':kind},
                'original_produced_format_byte':fmt,'raw98_at_first_dump_hex':raw.hex(),
                'raw_source_fields':{'codec66':raw[0x66],'width':struct.unpack_from('<H',raw,0x68)[0],
                    'height':struct.unpack_from('<H',raw,0x6a)[0],'scalar7a':raw[0x7a],
                    'frame80':raw[0x80],'scan81':raw[0x81],'quality82':raw[0x82],
                    'chroma94':raw[0x94],'depth95':raw[0x95]},
                'events':events,'DMM_address_declared_not_native_allocated':hex(RAW),
                'whole_raw_packet_initialization_or_normal_Open_proven':False}
    finally:m.close()


def classify(blob,producer):
    source=bytes.fromhex(producer['raw98_at_first_dump_hex'])
    m=prev.src.prev.Guest(blob,producer['seed'])
    specifications=(
        ('coding',0x134d44,0x134ec0,producer['original_produced_format_byte'],source[0x66],0x27dd14,0x27dd38),
        ('frame',0x134bf4,0x134cc4,source[0x80],source[0x7a],0x27dcf0,0x27dd14),
        ('scan',0x134cc4,0x134d44,source[0x81],0,0x27dd38,0x27dd64),
        ('quality',0x134fcc,0x1352f8,source[0x82],0,0x27dd64,0x27dd88),
        ('chroma',0x1352f8,0x13538c,source[0x94],0,0x27debc,0x27dee0),
        ('depth',0x13538c,0x135400,source[0x95],0,0x27dee0,0x27df04))
    m.ranges.extend((prev.src.V+a,prev.src.V+z) for _,a,z,_,_,s,e in specifications for a,z in ((a,z),(s,e)))
    result={};events=[]
    for name,start,end,first,second,lookup,lookup_end in specifications:
        e=m.phase('independent original scalar converter '+name,start,x0=r.ARENA,x1=first,x2=second)
        events.append(e);assert e['reason']=='returned'
        value=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)
        e=m.phase('original diagnostic enum-name lookup '+name,lookup,x0=value)
        events.append(e);assert e['reason']=='returned'
        pointer=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)
        text=r.im.cstring(blob,pointer-prev.src.V,180)
        result[name]={'scalar_inputs':[first,second],'native_enum':value,'original_name':text}
    assert result['coding']['original_name']==('STREAMING_HEVC_BSF' if producer['declared_controls']['codec_b0']==1 else 'STREAMING_AVC_BSF')
    assert result['chroma']['original_name']=='CHROMA_420'
    assert result['depth']['original_name']=='BIT_DEPTH_8'
    assert result['frame']['original_name']==('29_97' if producer['declared_controls']['frame_ac']==0 else '25')
    return {'label':producer['label'],'seed':producer['seed'],'source_fields':producer['raw_source_fields'],
            'decoded':result,'events':events,
            'scalar_arguments_extracted_without_edits_from_original_app_fields':True,
            'whole_receiver_descriptor_builder_instance_or_real_SPS_proven':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    out=Path(parser.parse_args().output).resolve()
    im.volume();assert out.parent==STAGE and not out.exists()
    assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        b=(ROOT/f['path']).read_bytes();assert len(b)==f['bytes'] and sha(b)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    assert sha(APP.blob)==prev.APP_SHA
    blob=prev.src.prev.IMAGE.read_bytes();assert sha(blob)==prev.src.prev.IMAGE_SHA
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        produced=[build(seed,p) for seed in (0xa5,0xc3) for p in PROFILES]
        classified=[classify(blob,p) for p in produced]
        pairs=[]
        for profile in PROFILES:
            a,b=[p for p in produced if p['label']==profile[0]]
            assert a['raw_source_fields']==b['raw_source_fields']
            aa,bb=bytes.fromhex(a['raw98_at_first_dump_hex']),bytes.fromhex(b['raw98_at_first_dump_hex'])
            pairs.append({'label':profile[0],'old_seed_dependent_byte_offsets':[hex(n) for n,(x,y) in enumerate(zip(aa,bb)) if x!=y],
                          'scope':'Retained bytes in declared post-DMM output; omitted allocator/clear may initialize them. Not a Sony uninitialized-memory defect.'})
        result={'status':'PASS_ORIGINAL_STREAMING_OPEN_FIELDS_CLASSIFY_AS_STREAMING_420_8_NOT_TARGET_MAIN_420_10',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'previous_manifest_sha256':PRIOR_SHA,'original_app_sha256':prev.APP_SHA,
            'original_avcam_sha256':sha(blob),'produced_profiles':produced,'native_classifications':classified,
            'old_value_scope':pairs,'bounded_phases':sum(len(c['events']) for c in produced+classified),
            'scope':'Original app prologue/post-DMM Open profile body with declared output/parameters; scalar arguments from produced bytes into original avcam converters and original enum-name lookups. No full Open, allocation/header/memset/log/transport/state/MAIN/hardware or actual bitstream-depth acceptance.',
            'actual_stream_or_card_MAIN_SPS_recovery_or_safe_patch_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (out/'open-profile-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'profiles':len(produced),'classifications':len(classified),
                          'bounded_phases':result['bounded_phases'],'output':str(out)}))
    except Exception:
        (out/'attempt-failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'passing_result':False},indent=2)+'\n')
        raise


if __name__=='__main__':main()
