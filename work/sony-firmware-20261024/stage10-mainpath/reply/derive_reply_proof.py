#!/usr/bin/env python3
"""Static FX3 lookup/serializer receipts; no emulation, syscall or device use."""
from pathlib import Path
import importlib.util,sys,json,struct,hashlib
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;B=P.parents[1]
sp=importlib.util.spec_from_file_location('static_service',B/'stage7-entry/firmware/static_service.py')
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
c=m.Native('/usr/lib/libsencore.so');j=m.Native('/usr/lib/libJiritsu.so')
assert hashlib.sha256(c.blob).hexdigest()=='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
assert hashlib.sha256(j.blob).hexdigest()=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
def block(n,a,z):
 rows=[]
 for i in n.md.disasm(n.data(a,z-a),a):
  name=''
  if i.mnemonic in ('b','bl'):
   try:name=n.plt.get(int(i.op_str[1:],16),'')
   except ValueError:pass
  rows.append({'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'PLT_symbol':name})
 return {'library':n.path,'start':hex(a),'end':hex(z),'instructions':rows}
records=[]
for cmd in range(15,19):
 a=0x31d98+(cmd-15)*0x48;b=c.data(a,0x48);family,code=struct.unpack_from('<HH',b);queue=struct.unpack_from('<I',b,0x44)[0]
 assert (a-0x17698)%0x48==0 and family==0x1001 and code==0x4000+cmd and queue==0x016f0480
 records.append({'command_low8':cmd,'record_start':hex(a),'lookup_index':(a-0x17698)//0x48,
  'family':hex(family),'flags_and_command':hex(code),'name':b[4:].split(b'\0',1)[0].decode(),
  'queue_id':hex(queue),'raw_record_0x48_hex':b.hex()})
blocks=[block(c,a,z) for a,z in [(0xc108,0xc184),(0xe9f4,0xea6c),(0x10344,0x104ec),
 (0xfddc,0xfeb8),(0xff58,0x10020),(0xf94c,0xf9d8),(0xf784,0xf850),
 (0xb4c0,0xb64c),(0xcf98,0xcff0),(0xd3f8,0xd40c),(0xd704,0xd724)]]
blocks += [block(j,0x9fc0,0x9fe8),block(j,0xa118,0xa254)]
proof={'method':'fixed-source static byte/disassembly only','sources':{n.path:hashlib.sha256(n.blob).hexdigest() for n in [c,j]},
 'active_lookup':{'family_key_base':'0x17698','stride':'0x48','count_bound':'0x6c6','record_fields':{'family':'0x00','flags_and_command':'0x02','name':'0x04','queue_id':'0x44'},'records':records},
 'correction_of_stage9':{'old_slice_start_for_cmd15':'0x31d94','correct_record_start':'0x31d98','old_leading_u32':'previous record tail queueID; adjacent Jiritsu records share it','record_0x4000':'permission flags, not outer pFunc0x40'},
 'runtime_gates':['onComplete selects pFunc/adjCodeLevel at runtime; current body not observed','Jiritsu entries0x400f..0x4012 pass level2 with bit15 clear, and level3; level1 fails nonzero0xe000 flags','OSAL callback must have been registered and queue/drivers remain operational'],
 'serializer':{'header_bytes':'0x0c','size_at':'0x00','forced_byte':'0x08 = 0x03','payload_round_max':'0x100000','send_callback_max':'0x8000','continuation_size':'remaining logical bytes at start of round; excludes0x0c header','other_header_bytes':'SendResponse does not clear0x04..0x07,0x09,0x0a; operation path controls0x0b'},
 'blocks':blocks,'not_proven':['current authentication level or callback registration','real USB reachability/transfer/ZLP completion','all error and encrypted/file modes','independent recovery after appFw failure','actual HEVC encode or persistent firmware write safety']}
(P/'final-reply-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print('PASS static records:',[(r['lookup_index'],r['record_start'],r['queue_id']) for r in records])
print('Sources unchanged; no device interaction or firmware execution.')
