#!/usr/bin/env python3
"""Read-only static derivation of four FX3 Jiritsu command routes."""
from pathlib import Path
import importlib.util,sys,json,hashlib,struct,csv,io
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;B=P.parents[1]
sp=importlib.util.spec_from_file_location('static_service',B/'stage7-entry/firmware/static_service.py')
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
n=m.Native('/usr/lib/libJiritsu.so');c=m.Native('/usr/lib/libsencore.so')
assert hashlib.sha256(n.blob).hexdigest()=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
assert hashlib.sha256(c.blob).hexdigest()=='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
def branch(base,pc,index):
 raw=n.data(base+index,1);return raw.hex(),pc+struct.unpack('<b',raw)[0]*4
rows=[]
for cmd,fn,va,call,second in [
 (15,'adj_cmd_set_file_path',0x89b4,0xacb4,(0x11b14,0xac50,6)),
 (16,'adj_cmd_set_file2',0x9528,0xacc4,(0x11b14,0xac50,6)),
 (17,'adj_cmd_get_file2',0x9e74,0xb20c,(0x11b20,0xb168,8)),
 (18,'cmd_file_delete2',0xa29c,0xb464,None)]:
 b,target=branch(0x11b2c,0xb2b8,cmd-1)
 ins=next(n.md.disasm(n.data(call,4),call));plt=int(ins.op_str[1:],16)
 assert ins.mnemonic=='bl' and n.plt[plt]==fn
 sym=next(a for a in n.syms if a['name']==fn and a['defined']);assert sym['va']==va
 record=c.data(0x31d94+(cmd-15)*0x48,0x48)
 mid,fam,internal=struct.unpack_from('<IHH',record)
 assert mid==0x016f0480 and fam==0x1001 and internal==(0x4000|cmd)
 row={'command':cmd,'core_record_VA':hex(0x31d94+(cmd-15)*0x48),'core_record_hex':record.hex(),
  'record_name':record[8:].split(b'\0',1)[0].decode(),'record_message_id':hex(mid),'record_family':hex(fam),
  'record_internal_command':hex(internal),'dispatcher':'0xb278','table_VA':'0x11b2c','index':cmd-1,
  'table_byte':b,'first_target':hex(target),'handler_symbol':fn,'handler_entry':hex(va),
  'real_call_VA':hex(call),'real_call_bytes':n.data(call,4).hex(),'PLT_target':hex(plt)}
 if second:
  tb,branchbase,low=second;b2,t2=branch(tb,branchbase,cmd-low)
  row['secondary']={'table':hex(tb),'index':cmd-low,'byte':b2,'target':hex(t2)}
 rows.append(row)
result={'scope':'Pure static command→handler derivation; not a device protocol test',
 'library_SHA256':hashlib.sha256(n.blob).hexdigest(),'core_SHA256':hashlib.sha256(c.blob).hexdigest(),
 'outer_record_active_lookup':'unproved in this bounded pass',
 'external_wire_serializer_and_auth':'not verified','rows':rows,
 'control_proof':{'full_table_hex':n.data(0x11b2c,18).hex(),
  'dispatcher_entry24':n.data(0xb278,24).hex(),'callback_registration_call':'0x6dbc',
  'callback_queue_id':'0x016f0480','callback_address':'0xb278',
  'MakeOsalMessage_narrowing_instructions':{'0xf07c':c.data(0xf07c,4).hex(),'0xf080':c.data(0xf080,4).hex()}}}
(P/'command-handler-table.json').write_text(json.dumps(result,indent=2)+'\n')
fields=['command','record_name','record_family','record_internal_command','table_byte','first_target','handler_symbol','handler_entry','real_call_VA']
s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
(P/'command-handler-table.csv').write_text(s.getvalue())
print('PASS: 4 original tables, symbolic PLT targets, actual handler symbols and core record bytes agree.')
