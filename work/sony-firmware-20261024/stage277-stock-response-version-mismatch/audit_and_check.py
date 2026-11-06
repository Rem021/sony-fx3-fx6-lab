"""Static original bytes + own CPU backends only. No camera or privileged API."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import io,json,struct,subprocess,os,sys,re,hmac,importlib.util
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent
assert os.getuid()==os.geteuid()==501
raw=(B/'stage2/extraction/files/nflasha15/lib/libsencore.so').read_bytes()
assert sha256(raw).hexdigest()=='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
elf=ELFFile(io.BytesIO(raw));symbols={s.name:s for s in elf.get_section_by_name('.dynsym').iter_symbols()}
cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def code(va,size):
 for seg in elf.iter_segments():
  if seg['p_type']=='PT_LOAD'and seg['p_vaddr']<=va and va+size<=seg['p_vaddr']+seg['p_filesz']:
   at=seg['p_offset']+va-seg['p_vaddr'];return raw[at:at+size]
 raise ValueError('unmapped original function')
functions=[]
for name in ['_Z12SendResponseP12SenserPacketP10PacketData','_Z9SerializePFiPhmEPvm','_Z12SenserIfSendPhm']:
 s=symbols[name];data=code(s['st_value'],s['st_size'])
 functions.append(dict(name=name,VA=hex(s['st_value']),bytes=len(data),sha256=sha256(data).hexdigest(),
  instructions=[dict(pc=hex(i.address),bytes=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str)for i in cs.disasm(data,s['st_value'])]))
i={int(i['pc'],16):i for i in functions[0]['instructions']}
assert i[0xb4d0]['asm']=='mov w0, #3'and i[0xb4e0]['asm']=='strb w0, [x19, #8]'
assert i[0xb4cc]['asm']=='mov x19, x0'
assert i[0xb56c]['asm']=='bl #0xa580'and i[0xb5f8]['asm']=='bl #0xa580'
# The single-header and header+body branches both pass the same x19 buffer.
assert i[0xb568]['asm']=='mov x1, x19'and i[0xb5ec]['asm']=='mov x1, x19'
old=(H/'history/stream.before.c').read_text();new=(H/'stream.c').read_text()
assert old.replace('expected[12]={88,0,0,0,0x10,0,1,0,0,0,0,1}',
                   'expected[12]={88,0,0,0,0x10,0,1,0,3,0,0,1}')==new
original=dict(status='PINNED_STOCK_RESPONSE_PRODUCER_VERSION3_VS_HOST_EXPECTED0',
 image_sha256=sha256(raw).hexdigest(),functions=functions,
 header_field_layout=dict(size='0..3',pFunc='4..5',sequence='6..7',version='8',miconType='9',offsetType='10',response='11'),
 stock_SendResponse_overwrites_version_to=3,old_host_response_version=0,new_offline_candidate_version=3,
 original_Sony_instructions_executed=False,actual_275_header_bytes_not_available=True,
 exact_real_camera_header_mismatch_unproven=True,source_not_a_same_body_backup=True)
with(H/'original-response-producer.json').open('x')as f:json.dump(original,f,ensure_ascii=False,indent=2);f.write('\n')
rows=[];builds={}
for label,source in [('before',H/'history/stream.before.c'),('candidate',H/'stream.c')]:
 out=H/'artifacts'/('read0-'+label)
 argv=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
 '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(H),str(source),str(H/'transition_identity.c'),str(H/'unit.c'),'-o',str(out)]
 p=subprocess.run(argv,capture_output=True,text=True);assert p.returncode==0,p.stderr
 deps=subprocess.check_output(['/usr/bin/otool','-L',str(out)],text=True);assert 'IOKit'not in deps
 builds[label]=dict(argv=argv,returncode=p.returncode,stderr=p.stderr,sha256=sha256(out.read_bytes()).hexdigest(),dependencies=deps)
 cases=[(0,0),(3,0)]if label=='before'else[(3,k)for k in range(8)]+[(0,0)]
 for version,variant in cases:
  p=subprocess.run([str(out),str(version),str(variant)],capture_output=True,text=True);assert p.returncode==0,p.stderr
  assert not p.stderr,p.stderr
  v=json.loads(p.stdout);expected_ok=variant==0 and version==(0 if label=='before'else 3)
  assert v['writes']==1 and v['rc']==(0 if expected_ok else 7)
  assert v['body_total']==(88 if expected_ok else 0)and v['bytes']==(88 if expected_ok else 0)
  assert v['STOP_calls']==(1 if expected_ok else 0)
  if expected_ok:
   assert v['body_calls']==4 and v['STOP_rc']==0
   expected=hmac.new(bytes([0x5a])*32,bytes((x*3+1)&255 for x in range(88)),sha256).hexdigest()
   assert v['opaque_hmac']==expected
  rows.append(dict(source=label,version=version,variant=variant,result=v,all_device_and_auth_state_artificial=True))
# Independently verify the public Python codec; the request must remain version0.
p=H/'bounded_hasp_read.py';spec=importlib.util.spec_from_file_location('bounded277',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
request=struct.pack('<IHHBBBB',5,0x10,1,0,0,0,0)+bytes.fromhex('00001f0000')
assert m.fixed_request(1)==request
body=bytes((x*3+1)&255 for x in range(88));reply=struct.pack('<IHHBBBB',88,0x10,1,3,0,0,1)+body
assert m.decode_fixed_reply(reply,1,bytes([0x5a])*32).payload_bytes==88
bad=bytearray(reply);bad[8]=0
try:m.decode_fixed_reply(bytes(bad),1,bytes([0x5a])*32)
except m.Rejected:pass
else:raise AssertionError('old response version accepted')
receipt=dict(status='STOCK_VERSION3_REJECTED_BY_OLD_COMPONENT_ACCEPTED_BY_CORRECTED_COMPONENT',
 created_utc=datetime.now(timezone.utc).isoformat(),builds=builds,rows=rows,Python_codec_check_pass=True,
 actual_request_bytes_unchanged=True,response_body_limit_still_88=True,only_response_version_field_changed=True,
 native_production_helper_built_or_executed=False,full_live_controller_integrated=False,new_live_package_ready=False,
 actual_root_journal_modified=False,new_admin_or_USB_operations=0,real_camera_header_or_read0_success_proven=False,
 error_exit_STOP_policy_unchanged=True)
with(H/'component-check.json').open('x')as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],own_backend_cases=len(rows),original_functions=len(functions),new_admin_or_USB_operations=0)))
