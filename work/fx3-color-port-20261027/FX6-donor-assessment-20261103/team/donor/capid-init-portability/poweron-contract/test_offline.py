import sys
sys.dont_write_bytecode=True
from extract import *
from offline import *
# Constants are decoded from original MOVZ instructions, not trusted handwritten fixtures.
def movz(k,va):
 w=int.from_bytes(bytes.fromhex(E[k].mapping(va)['bytes_le']),'little');assert w&0xff800000==0x52800000
 return (w>>5)&0xffff
assert movz('fx3_mpr',0xb55fc)==FX3_EVENT
assert movz('fx6_mpr',0x129ec4)==FX6_EVENT
assert movz('fx6_ap',0x2144678)==FX6_EVENT
assert movz('fx6_ap',0x2144730)==0xbd
assert E['fx3_mpr'].mapping(0xb5618)['bytes_le']==E['fx6_mpr'].mapping(0x129ee0)['bytes_le']=='bf1b00b9'
table=E['fx6_ap'].mapping(0x2622138,18);assert bytes.fromhex(table['bytes_le'])[0]==0
cases=[]
# Echo words are symbolic test operands, NOT runtime captures or evidence of enum meaning.
for echo in [0,1,0xffffffff,0x80000000]:
 source=struct.pack('<III',movz('fx3_mpr',0xb55fc),echo,0)
 donor=struct.pack('<III',movz('fx6_mpr',0x129ec4),echo,0)
 translated=translate(source);assert translated==donor and translated[4:]==source[4:]
 p={'key':FX6_EVENT,'request_echo':echo,'phase':'pending'}
 s=consume_fx6(translated,p);assert s['request_result']==0 and p['phase']=='pending'
 # Known original FX6 mismatch branch must remain nonzero.
 mismatch=consume_fx6(translated,dict(p,request_echo=echo^1));assert mismatch['request_result']==0xbd
 cases.append({'source_hex':source.hex(),'translated_hex':translated.hex(),'donor_reference_hex':donor.hex(),'echo_is_symbolic_operand':True,'matched':s,'mismatch':mismatch})
rejections=[]
for label,fn in [('unaltered_fx3_event',lambda:consume_fx6(source,p)),('wrong_event',lambda:translate(struct.pack('<III',0x1025,1,0))),('nonzero_result',lambda:translate(struct.pack('<III',FX3_EVENT,1,3))),('negative_result_bits',lambda:translate(struct.pack('<III',FX3_EVENT,1,0xffffffff))),('short',lambda:translate(source[:-1])),('long',lambda:translate(source+b'\0')),('mutable',lambda:translate(bytearray(source))),('duplicate',lambda:consume_fx6(translated,s)),('no_pending_key',lambda:consume_fx6(translated,dict(p,key=0)))]:
 try:fn()
 except Unproven as e:rejections.append({'case':label,'reason':str(e)})
 else:raise AssertionError(label)
out={'status':'PASS_OFFLINE_LOCAL_CONTRACT_ONLY','instruction_derived_event_constants':[FX3_EVENT,FX6_EVENT],'constant_zero_result_proven_by_str_wzr':True,'cases':cases,'rejections':rejections,'limits':'Does not execute firmware, queue, allocator, promise ABI, wait, actual binding or native synchronization; symbolic fixtures are not captured runtime packets.'}
(H/'offline-receipt.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
