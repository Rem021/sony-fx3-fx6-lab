"""Own CPU backends only for bounded read0 header failure localization."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import hmac,importlib.util,json,os,struct,subprocess,sys
sys.dont_write_bytecode=True
import flow_receiver as F
H=Path(__file__).resolve().parent
assert os.getuid()==os.geteuid()==501
out=H/'artifacts/read0-candidate'
argv=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
 '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(H),
 str(H/'stream.c'),str(H/'transition_identity.c'),str(H/'unit.c'),'-o',str(out)]
p=subprocess.run(argv,capture_output=True,text=True);assert p.returncode==0,p.stderr
deps=subprocess.check_output(['/usr/bin/otool','-L',str(out)],text=True);assert 'IOKit'not in deps
builds=dict(candidate=dict(argv=argv,returncode=p.returncode,stderr=p.stderr,sha256=sha256(out.read_bytes()).hexdigest(),dependencies=deps))

expected_cases=[
 (3,0,0,1,0,'ok'),
 (3,1,7,3,0x01,'size_mismatch'),
 (3,2,7,4,0x02,'pfunc_mismatch'),
 (3,3,7,5,0x04,'sequence_mismatch'),
 (0,0,7,6,0x08,'version_mismatch'),
 (3,4,7,7,0x10,'micon_mismatch'),
 (3,5,7,8,0x20,'offset_mismatch'),
 (3,6,7,9,0x40,'response_mismatch'),
 (3,7,7,2,0x00,'short_count'),
 (3,8,7,10,0x49,'multiple_mismatch'),
 (0,1,7,10,0x09,'multiple_mismatch'),
 (3,9,6,0,0x00,'not_evaluated'),
]
rows=[]
for version,variant,exp_rc,exp_reason,exp_mask,exp_name in expected_cases:
 p=subprocess.run([str(out),str(version),str(variant)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 assert not p.stderr,p.stderr
 v=json.loads(p.stdout);expected_ok=(exp_rc==0)
 assert v['writes']==1 and v['rc']==exp_rc,v
 assert v['header_reason']==exp_reason and v['header_mask']==exp_mask,v
 assert v['op5_point1_reason']==exp_reason and v['op5_point1_mask']==exp_mask,v
 assert F.READ0_HEADER_REASONS[v['header_reason']]==exp_name
 assert v['body_total']==(88 if expected_ok else 0)and v['bytes']==(88 if expected_ok else 0)
 assert v['STOP_calls']==(1 if expected_ok else 0)
 if expected_ok:
  assert v['body_calls']==4 and v['STOP_rc']==0 and v['reply_valid']==1
  expected=hmac.new(bytes([0x5a])*32,bytes((x*3+1)&255 for x in range(88)),sha256).hexdigest()
  assert v['opaque_hmac']==expected
 else:
  assert v['body_calls']==0 and v['reply_valid']==0 and v['opaque_hmac']=='0'*64
 rows.append(dict(version=version,variant=variant,reason_name=exp_name,result=v,all_device_and_auth_state_artificial=True))

p=H/'bounded_hasp_read.py';spec=importlib.util.spec_from_file_location('bounded278',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
request=struct.pack('<IHHBBBB',5,0x10,1,0,0,0,0)+bytes.fromhex('00001f0000')
assert m.fixed_request(1)==request
body=bytes((x*3+1)&255 for x in range(88));reply=struct.pack('<IHHBBBB',88,0x10,1,3,0,0,1)+body
obs=m.decode_fixed_reply(reply,1,bytes([0x5a])*32)
assert (obs.payload_bytes,obs.header_reason,obs.header_mask)==(88,1,0)
assert m.classify_reply_header(reply[:11],1)==dict(reason=2,name='short_count',mask=0,fields=())
for offset,val,exp_reason,exp_mask,exp_fields in [
 (0,89,3,0x01,('size',)),
 (4,0x11,4,0x02,('pFunc',)),
 (6,2,5,0x04,('sequence',)),
 (8,0,6,0x08,('version',)),
 (9,1,7,0x10,('miconType',)),
 (10,1,8,0x20,('offsetType',)),
 (11,0,9,0x40,('response',)),
]:
 bad=bytearray(reply);bad[offset]=val
 c=m.classify_reply_header(bytes(bad[:12]),1)
 assert c==dict(reason=exp_reason,name=m.HEADER_REASONS[exp_reason],mask=exp_mask,fields=exp_fields),c
 try:m.decode_fixed_reply(bytes(bad),1,bytes([0x5a])*32)
 except m.Rejected as e:assert m.HEADER_REASONS[exp_reason] in str(e)
 else:raise AssertionError('mismatched header accepted')
multi=bytearray(reply[:12]);multi[0]=0;multi[8]=0;multi[11]=0
assert m.classify_reply_header(bytes(multi),1)==dict(reason=10,name='multiple_mismatch',mask=0x49,fields=('size','version','response'))

receipt=dict(status='BOUNDED_TYPED_HEADER_LOCALIZATION_COMPONENT_PASS',
 created_utc=datetime.now(timezone.utc).isoformat(),builds=builds,rows=rows,Python_codec_check_pass=True,
 actual_request_bytes_unchanged=True,response_body_limit_still_88=True,expected_response_version_still_3=True,
 raw_header_or_HASP_or_auth_bytes_exported=False,native_production_helper_built_or_executed=False,
 new_live_package_ready=False,actual_root_journal_modified=False,new_admin_or_USB_operations=0,
 real_camera_header_or_read0_success_proven=False,error_exit_STOP_policy_unchanged=True)
with(H/'component-check.json').open('x')as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],own_backend_cases=len(rows),new_admin_or_USB_operations=0)))
