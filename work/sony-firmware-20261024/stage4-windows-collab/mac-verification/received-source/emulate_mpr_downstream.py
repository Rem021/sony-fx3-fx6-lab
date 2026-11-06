from emulate_h265_converter import Micro,ROOT,OUT,mpr,SCRATCH,STOP,STACK,p32,u32
import json,struct
from unicorn.arm64_const import UC_ARM64_REG_X0

def run_case(name,entry,args,ranges,prepare=None):
    def log_stub(m):m.ret(0)
    micro=Micro(mpr,ranges+[(0x2cb000,0x2f0000)],{0xc8c70:log_stub})
    if prepare:prepare(micro.uc)
    for i,value in enumerate(args):micro.uc.reg_write(UC_ARM64_REG_X0+i,value)
    reason=micro.run(entry)
    return {'case':name,'entry_ELF_VA':hex(entry),'args':[hex(v) for v in args],'reason':reason,'return_x0':micro.uc.reg_read(UC_ARM64_REG_X0)&0xffffffff,'scratch_first48_hex':bytes(micro.uc.mem_read(SCRATCH,48)).hex(),'steps':micro.steps},micro

cases=[]
for vpc in [5,7]:
    for frame,quality in [(0,12),(3,12),(7,12),(12,12),(3,255)]:
        def prepare(uc,vpc=vpc,frame=frame,quality=quality):
            uc.mem_write(SCRATCH,b'\0'*0x400)
            uc.mem_write(SCRATCH+0x170,struct.pack('<III',vpc,quality,frame))
        row,micro=run_case('CheckMovieRecParam',0xcc4d4,[SCRATCH],[(0xcc4d4,0xcc824)],prepare)
        row.update({'VideoParamComb':vpc,'FrameRate':frame,'VQuality':quality,'accepted_by_basic_validator':row['reason']=='returned' and row['return_x0']==0})
        cases.append(row)
    row,micro=run_case('ConvertVPCToLevel_29.97',0x115e78,[0,vpc,12,3,SCRATCH],[(0x115e78,0x115fec)])
    row.update({'VideoParamComb':vpc,'FrameRate':3,'VQuality':12,'level_enum_written':u32(micro.uc,SCRATCH)})
    cases.append(row)

row,micro=run_case('ConvertFrameRateToNumerAndDenom_29.97',0x2c0de8,[3,SCRATCH,SCRATCH+4],[(0x2c0de8,0x2c0e98)])
row['numerator']=u32(micro.uc,SCRATCH);row['denominator']=u32(micro.uc,SCRATCH+4);cases.append(row)
row,micro=run_case('GetVideoBitrate_100M',0x2c0ce0,[12],[(0x2c0ce0,0x2c0d04)]);cases.append(row)
row,micro=run_case('ConvertFrameRateForCodec_29.97',0x2c0d04,[3,SCRATCH,SCRATCH+8,SCRATCH+9],[(0x2c0d04,0x2c0de8)])
row['FramePerSec_raw_u32']=u32(micro.uc,SCRATCH);row['byte_flags']=list(micro.uc.mem_read(SCRATCH+8,2));cases.append(row)
checks={
 'normal_candidate_pairs_pass_basic_MPR_validator':all(r['accepted_by_basic_validator'] for r in cases if r['case']=='CheckMovieRecParam' and r['FrameRate']==3 and r['VQuality']==12),
 'invalid_frame_and_quality_rejected':all(not r['accepted_by_basic_validator'] for r in cases if r['case']=='CheckMovieRecParam' and (r['FrameRate']==12 or r['VQuality']==255)),
 'both_HEVC_profiles_have_29_97_metadata_level':all(r['reason']=='returned' and r['level_enum_written']==7 for r in cases if r['case']=='ConvertVPCToLevel_29.97'),
 'proper_30000_over_1001_timebase':any(r.get('numerator')==30000 and r.get('denominator')==1001 and r['reason']=='returned' for r in cases),
 '100M_quality_bitrate_value_is_100000_kbps':any(r['case']=='GetVideoBitrate_100M' and r['reason']=='returned' and r['return_x0']==100000 for r in cases),
}
result={'scope':'Real selected libmpr.so functions. Only logging is stubbed. Basic struct validation, metadata and timebase are not hardware encoder or bitstream validation.','cases':cases,'checks':checks}
(OUT/'mpr-downstream-emulation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for r in cases:print(r)
print('Checks',checks)
if not all(checks.values()):raise SystemExit('Downstream hypothesis did not pass all checks')
