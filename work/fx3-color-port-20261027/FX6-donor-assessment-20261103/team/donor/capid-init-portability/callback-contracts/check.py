import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,struct,hashlib
from projection import project,UnknownContract
H=Path(__file__).resolve().parent;inputs=json.loads((H/'inputs.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
for k,p in inputs['paths'].items():assert sha(Path(p).read_bytes())==inputs['hashes'][k]
assert sha((H.parent/'receipt.json').read_bytes())==inputs['parent_receipt_sha256']
assert sha((H.parent/'callback-fields.json').read_bytes())==inputs['parent_matrix_sha256']
cases=[]
for status in [0,1,0xffffffff,0x80000000]:
 b=bytearray(20);struct.pack_into('<II',b,8,status,0xfedcba98)
 actual=project('load_still_observed_fields',bytes(b));assert actual=={'opaque_u32_at_c':0xfedcba98,'zero_test_at_8':int(status==0)}
 cases.append({'status':status,'input_sha256':sha(b),'result':actual})
rejected=[]
for kind,b in [('mpr_Init',bytes(656)),('unknown_callback',bytes(20)),('load_still_observed_fields',bytes(19)),('load_still_observed_fields',bytes(21)),('load_still_observed_fields',bytearray(20))]:
 try:project(kind,b)
 except UnknownContract as e:rejected.append({'kind':kind,'length':len(b),'reason':str(e)})
 else:raise AssertionError('unknown accepted')
rows=json.loads((H/'matrix.json').read_text());assert len(rows)==57
assert sum(r['callbacks']['fx6_ap'] is None for r in rows)==11
assert sum(r['status'].startswith('LEAF') for r in rows)==4
# Explicit counterexample: equal field offset or callback symbol never sets acceptance.
assert all(r['status']!='PASS' for r in rows)
out={'status':'PASS_OFFLINE_PROJECTION_ONLY','cases':cases,'rejections':rejected,'full_adapter_accepted':False,'original_hashes_unchanged':True,'parent_reports_unchanged':True,'counterexamples':['same symbol PbGps: FX3 memcpy 0x90 from arg+4 vs FX6 RET','u16 representable 0x30c and 0x5a0 does not establish semantic range','Init registration GOT windows are not callback invocations','pointer or same field offset is not compatibility proof']}
(H/'checks.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
