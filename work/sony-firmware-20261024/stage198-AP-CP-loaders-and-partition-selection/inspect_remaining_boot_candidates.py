"""Bounded remaining package candidates, saved data only."""
from pathlib import Path
from hashlib import sha256
import json, re
H=Path(__file__).resolve().parent;B=H.parent
audit=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/current-updater-asset-audit.json'
j=json.loads(audit.read_text())
source=B/'fx3-7.02-decrypted.fdat'
expected='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
h=sha256()
with source.open('rb') as f:
    while chunk:=f.read(1024*1024):h.update(chunk)
assert h.hexdigest()==expected
name='0640_darwin/darwin_core.bin'
rows=[r for r in j['tar']['members'] if r['name']==name];assert len(rows)==1
r=rows[0];assert r['size']==243000 and r['sha256']=='ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
with source.open('rb') as f:
    f.seek(r['fdat_data_offset']);data=f.read(r['size'])
assert len(data)==r['size'] and sha256(data).hexdigest()==r['sha256']
with (H/'originals/darwin_core.bin').open('xb') as f:f.write(data)
strings=[{'offset':hex(m.start()),'value':m.group().decode('ascii')}
         for m in re.finditer(rb'[\x20-\x7e]{5,}',data)]
with (H/'darwin_core.bin.strings.json').open('x') as f:json.dump(strings,f,indent=2);f.write('\n')
p5=B/'stage2/extraction/nflasha5.img'
expected5='ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1'
h=sha256()
with p5.open('rb') as f:
    first=f.read(96);h.update(first)
    while chunk:=f.read(1024*1024):h.update(chunk)
assert h.hexdigest()==expected5
result={
 'saved_FDAT_path':str(source),'saved_FDAT_sha256_verified':expected,
 'darwin':{'member':name,'FDAT_offset':r['fdat_data_offset'],'bytes':len(data),
    'sha256':r['sha256'],'first64':data[:64].hex(),'string_count':len(strings),
    'SPI_sender_identity_or_boot_mode_generation_proven':False},
 'p5':{'path':str(p5),'sha256_verified':expected5,'bytes':p5.stat().st_size,
       'first96':first.hex(),'signature_ascii':first[:4].decode('ascii'),
       'signature_only_not_complete_WBI_parse':True},
 'top_level_partition_payloads':[r['member'] for r in j['partition_payloads']],
 'FDAT_filesystem_slots':j['fdat']['filesystem_slots'][:j['fdat']['filesystem_count']],
 'known_boot0_payload_or_FX3_current_p1_obtained':False,
 'original_or_guest_execution':False,'root_or_device_operations':0}
with (H/'remaining-candidates.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'darwin_bytes':len(data),'darwin_first16':data[:16].hex(),
    'strings':len(strings),'p5_signature':first[:4].decode('ascii'),'no_device_operations':True}))
