"""Two-byte-record prototype and bounded instruction-semantics cases.
No ELF function is called, no firmware is emitted, no VM, no stubs.
The comparison is a symbolic transcription checked against pinned machine words.
Only finite positive FPS and unsigned 32-bit frame counters are modelled.
"""
import sys
sys.dont_write_bytecode=True
import math, struct, json
from trace import E,H,sha
FX3_CTOR=0x11b9dc
FX6_XAVCS_CTOR=0x1b3284
FX6_MXF_CTOR=0x199de4
class Unsupported(ValueError):pass

def convert_fixed_fx6_xavcs_u16(record, *, source_ctor, target_ctor):
 """Return only a two-byte local record, conditional on proven constructor identities.
 Does not determine mode, construct an Init record, perform callbacks, or bind code.
 """
 if type(record) is not bytes or len(record)!=2:raise Unsupported('exactly two bytes required')
 if source_ctor != FX6_XAVCS_CTOR:raise Unsupported('source writer path not covered; Mxf is explicitly rejected')
 if target_ctor != FX3_CTOR:raise Unsupported('target writer constructor not covered')
 if struct.unpack('<H',record)[0]!=1440:raise Unsupported('not the fixed FX6 AP producer value')
 return struct.pack('<H',780)

def original_store(k,va,raw,offset):
 """Execute only verified LDRH or MOVZ followed by STRH, into a bounded bytearray."""
 words=struct.unpack('<II',bytes.fromhex(E[k].mapping(va,8)['bytes_le']))
 expected={('fx3_mpr',0x1197c8):(0x79403280,0x79004a60),('fx6_mpr',0x194124):(0x79403280,0x7900f260),('fx6_mpr',0x1b0f44):(0x52806180,0x7900ea60)}
 assert words==expected[(k,va)]
 assert len(raw)==2
 if words[0]==0x79403280:value=struct.unpack('<H',raw)[0]
 elif words[0]==0x52806180:value=(words[0]>>5)&0xffff
 else:raise Unsupported('unmodelled instruction')
 store_offset=((words[1]>>10)&0xfff)*2;assert store_offset==offset
 obj=bytearray([0xa5]*(offset+4));struct.pack_into('<H',obj,offset,value)
 assert obj[:offset]==b'\xa5'*offset and obj[offset+2:]==b'\xa5\xa5'
 return struct.unpack_from('<H',obj,offset)[0]

def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def predicate(u16,frames,*,num=25,den=1,stream=0,already_notified=0):
 if not 0<=u16<=65535 or not 0<=frames<=0xffffffff:raise Unsupported('integer domain')
 if num<=0 or den<=0 or not math.isfinite(num/den):raise Unsupported('FPS domain')
 fps=f32(f32(num)/f32(den))
 if not math.isfinite(fps) or fps<=0:raise Unsupported('FPS domain')
 seconds=f32(f32(frames)/fps)
 threshold=((60*u16)-60)&0xffffffffffffffff
 return {'threshold_u64_seconds':threshold,'threshold_f32_seconds':f32(threshold),'elapsed_f32_seconds':seconds,'emit_0x40000005':not already_notified and stream==0 and not(seconds<f32(threshold))}

if __name__=='__main__':
 # The target decisions are computed; there are no call stubs.
 # Operand/register changes in the three binaries do not change arithmetic words.
 checks=[]
 for k,start in [('fx3_mpr',0x11facc),('fx6_mpr',0x1b67a0),('fx6_mpr',0x199498)]:
  expect=[0x92800761,0x52800780,0x9ba20400,0x1e281821,0x9e230000,0x1e202030]
  got=struct.unpack('<6I',bytes.fromhex(E[k].mapping(start,24)['bytes_le']));assert list(got)==expect
  checks.append({'binary':k,'start':hex(start),'words':[f'{v:08x}' for v in got]})
 # 25/1 is emitted by the original conversion function, not an assumed 30 FPS enum.
 assert struct.unpack('<I',bytes.fromhex(E['fx3_mpr'].mapping(0x2c0e2c)['bytes_le']))[0]==0x52800320
 rows=[]
 for u in [0,1,780,1440,65535]:
  raw=struct.pack('<H',u)
  eff={'fx3_xavcs':original_store('fx3_mpr',0x1197c8,raw,0x24),'fx6_xavcs':original_store('fx6_mpr',0x1b0f44,raw,0x74),'fx6_mxf':original_store('fx6_mpr',0x194124,raw,0x78)}
  assert eff=={'fx3_xavcs':u,'fx6_xavcs':780,'fx6_mxf':u}
  rows.append({'input_hex':raw.hex(),'input_u16':u,'effective':eff})
 frames=[0,1168499,1168500,1168501,2160000,2158500,0xffffffff]
 cases=[]
 for frame in frames:
  cases.append({'frame_counter':frame,'fps':[25,1],'fx3_direct_1440':predicate(1440,frame),'fx3_preserve_780':predicate(780,frame),'fx6_xavcs':predicate(780,frame),'fx6_mxf':predicate(1440,frame)})
 assert not cases[1]['fx3_preserve_780']['emit_0x40000005']
 assert cases[2]['fx3_preserve_780']['emit_0x40000005'] and not cases[2]['fx3_direct_1440']['emit_0x40000005']
 assert all(c['fx3_preserve_780']==c['fx6_xavcs'] for c in cases)
 assert predicate(0,0xffffffff)['threshold_u64_seconds']==2**64-60
 assert not predicate(0,0xffffffff)['emit_0x40000005']
 assert predicate(1,0)['emit_0x40000005']
 assert not predicate(780,1168500,stream=1)['emit_0x40000005']
 assert not predicate(780,1168500,already_notified=1)['emit_0x40000005']
 # Native enum 4 maps to 50/1 in both tables; Mxf alone halves it here.
 assert bytes.fromhex(E['fx3_mpr'].mapping(0x2e0a58,1)['bytes_le'])==b'\x0d'
 assert bytes.fromhex(E['fx6_mpr'].mapping(0xec0cb0,1)['bytes_le'])==b'\x0d'
 assert struct.unpack('<4I',bytes.fromhex(E['fx6_mpr'].mapping(0xcc0400,16)['bytes_le']))==(0x121e7800,0x7100101f,0x1a9f17e0,0xd65f03c0)
 assert struct.unpack('<2I',bytes.fromhex(E['fx6_mpr'].mapping(0x198c8c,8)['bytes_le']))==(0x1e2c1000,0x1e200908)
 interlace={'conditional_same_enum_and_counter':True,'enum':4,'frame_counter':2158500,'fx6_mxf_effective_fps':25,'fx3_xavcs_effective_fps':50,'source':predicate(1440,2158500,num=25),'direct_target':predicate(1440,2158500,num=50),'ideal_target_u16_rational':'1441/2 (720.5), not representable as u16'}
 assert interlace['source']['emit_0x40000005'] and not interlace['direct_target']['emit_0x40000005']
 out=convert_fixed_fx6_xavcs_u16(b'\xa0\x05',source_ctor=FX6_XAVCS_CTOR,target_ctor=FX3_CTOR);assert out==b'\x0c\x03'
 rejected=[]
 for label,record,s,t in [('mxf',b'\xa0\x05',FX6_MXF_CTOR,FX3_CTOR),('unknown source',b'\xa0\x05',0,FX3_CTOR),('unknown target',b'\xa0\x05',FX6_XAVCS_CTOR,0),('empty',b'',FX6_XAVCS_CTOR,FX3_CTOR),('oversize',b'\xa0\x05\0',FX6_XAVCS_CTOR,FX3_CTOR),('zero',b'\0\0',FX6_XAVCS_CTOR,FX3_CTOR),('nonfixed 780',b'\x0c\x03',FX6_XAVCS_CTOR,FX3_CTOR)]:
  try:convert_fixed_fx6_xavcs_u16(record,source_ctor=s,target_ctor=t)
  except Unsupported as exc:rejected.append({'case':label,'reason':str(exc)})
  else:raise AssertionError(label)
 receipt={'kind':'OFFLINE_BYTE_RECORD_AND_BOUNDED_ORIGINAL_INSTRUCTION_SEMANTICS','elf_function_execution':False,'stubs':[],'arithmetic_words':checks,'original_initializer_cases':rows,'comparison_cases':cases,'mxf_interlace_counterexample':interlace,'converter':{'input':'a005','output':out.hex(),'source_ctor':hex(FX6_XAVCS_CTOR),'target_ctor':hex(FX3_CTOR),'rejections':rejected},'limits':['not complete Init conversion','no runtime mode selection or PLT binding proof','FP32 round-to-nearest finite test domain only; no FPCR/exceptions emulation','predicate point reached is an explicit precondition; no recording success inferred']}
 (H/'fixture-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'result':'PASS','initializer_inputs':len(rows),'threshold_cases':len(cases),'rejections':len(rejected),'stub_count':0,'counterexample_frames':1168500,'fps':25,'fx6_xavcs_effective':780,'direct_1440_changes_event':True}))
