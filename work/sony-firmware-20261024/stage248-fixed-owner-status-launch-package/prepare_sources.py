"""Derive own fixed status-only launch sources. No device/admin execution."""
from pathlib import Path
from hashlib import sha256
import json,secrets,struct,difflib
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];A=B/'stage247-shared-host-transport-owner-status'
manifest=(A/'final-receipt.json').read_bytes()
assert sha256(manifest).hexdigest()=='c2d5e059c3071aeae2b28354895a0b848c10424fb43d3dde0ac062e7172d75f1'
for row in json.loads(manifest)['files']:
 data=(R/row['path']).read_bytes();assert len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256']
names=[p.name for p in A.iterdir() if p.suffix in ('.c','.h')]
names+=['controller_ipc.py','receipt_receiver.py','supervisor.py','fixed_launch.py']
origins=[]
for name in sorted(names):
 before=(A/name).read_text();text=before.replace(A.name,H.name).replace('fx3-fixture-ipc247','fx3-fixture-ipc248')
 if name=='controller_ipc.py':text=text.replace('build-receipt-current-port.json','build-receipt.json')
 with (H/name).open('x') as f:f.write(text)
 origins.append(dict(path=name,source=str((A/name).relative_to(R)),source_sha256=sha256(before.encode()).hexdigest()))
cache=json.loads((A/'current-cache-target.json').read_text());assert cache['candidate_count']==1
target=cache['candidates'][0];nonce=secrets.token_bytes(16);key=secrets.token_bytes(32)
def array(name,data):return 'static const unsigned char '+name+'['+str(len(data))+']={'+','.join('0x%02x'%x for x in data)+'};\n'
header='#ifndef FX3_STATUS_TARGET_BINDING_H\n#define FX3_STATUS_TARGET_BINDING_H\n#include <stdint.h>\n'
header+=f'#define FX3_FIXED_LOCATION 0x{target["locationID"]:08x}u\n#define FX3_CACHED_REGISTRY_ID {target["registryID"]}ull\n'
header+=array('FX3_FIXED_NONCE',nonce)+array('FX3_FIXED_PRIVACY_KEY',key)
header+='static inline int fx3_target_registry_permitted(uint64_t id,unsigned capture_attempted){return capture_attempted || id==FX3_CACHED_REGISTRY_ID;}\n#endif\n'
(H/'target_binding.h').write_text(header)
permit=bytearray(96);permit[:16]=b'FX3STATUSPERM1'.ljust(16,b'\0')
struct.pack_into('<II',permit,16,1,0x53544154);permit[24:40]=nonce
struct.pack_into('<IIQ',permit,40,target['locationID'],1,target['registryID'])
permit[64:]=sha256(permit[:64]).digest()
with (H/'permit.bin').open('xb') as f:f.write(permit)
material=dict(schema=1,nonce=nonce.hex(),privacy_key=key.hex(),target=target,
 permit_sha256=sha256(permit).hexdigest(),original_cache_sha256=sha256((A/'current-cache-target.json').read_bytes()).hexdigest(),
 raw_serial_read_or_saved=False,same_unit_tag_source='root-private HMAC of cached serial at runtime, only after separate approval',
 existing_registry_pin_not_firmware_identity=True)
with (H/'fixed-material.json').open('x') as f:json.dump(material,f,indent=2);f.write('\n')
with (H/'source-origins.json').open('x') as f:json.dump(origins,f,indent=2);f.write('\n')
print(json.dumps(dict(derived_files=len(origins),permit_bytes=96,admin_or_USB_operations=0)))
