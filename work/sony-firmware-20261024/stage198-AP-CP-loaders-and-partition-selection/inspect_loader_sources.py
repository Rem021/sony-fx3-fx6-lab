"""Extract selected saved boot components as data only. No mount/execution."""
from pathlib import Path
from hashlib import sha256
import importlib.util, json, re, sys
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
READER = BASE/'stage2/extraction/read_filesystems.py'
EXPECTED_READER = 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
assert sha256(READER.read_bytes()).hexdigest() == EXPECTED_READER
spec = importlib.util.spec_from_file_location('saved_fs_reader', READER)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)  # Python filesystem reader, not Sony code; no main().

def put(n, v):
    with (HERE/n).open('x') as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
        f.write('\n')

out = HERE/'originals'
out.mkdir()
sources = []
components = []
image = BASE/'stage2/extraction/nflasha8.img'
assert sha256(image.read_bytes()).hexdigest() == '3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
fs = reader.FAT16(image)
rows = list(fs.walk())
sources.append({'label':'official7.02 p8 payload', 'path':str(image), 'sha256':sha256(image.read_bytes()).hexdigest(),
    'bytes':image.stat().st_size, 'metadata':fs.meta, 'complete_directory':rows})
for row in rows:
    if row['path'] not in ('/DGU.bin','/MIS.bin','/loader_spi.bin','/tomco.txt'):
        continue
    raw = fs.data(row['cluster'], row['size'])
    assert len(raw) == row['size']
    p = out/row['path'].lstrip('/')
    with p.open('xb') as f:
        f.write(raw)
    strings = [{'offset':hex(m.start()),'value':m.group().decode('ascii')}
               for m in re.finditer(rb'[\x20-\x7e]{5,}', raw)]
    put(p.name+'.strings.json', strings)
    components.append({'source':'official7.02 p8 payload','path_in_image':row['path'],
        'output':str(p),'sha256':sha256(raw).hexdigest(),'bytes':len(raw),'first64':raw[:64].hex(),
        'string_count':len(strings),'source_hash_verified':True})
fs.b.close();fs.f.close()

# Historical payload: do not confuse its provenance with the connected body.
sys.path.insert(0, str(ROOT/'outputs/fx3-recovery-adapter'))
from fx3_recovery.fat import FatP1
image = ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1'
raw = image.read_bytes()
assert sha256(raw).hexdigest() == 'ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591'
fs = FatP1(raw)
inventory = [{'path':name,'bytes':e['size'],'directory':e['directory'],
              'sha256':None if e['directory'] else sha256(fs.contents(name)).hexdigest()}
             for name,e in fs.files.items()]
sources.append({'label':'historical official2.05 p1 reference ONLY','path':str(image),'sha256':sha256(raw).hexdigest(),
    'bytes':len(raw),'current_body_identity_verified':False,'complete_directory':inventory})
for name in ('/boot/loadaddr.txt','/boot/kemco.txt'):
    value = fs.contents(name)
    p = out/('historical2.05-'+name.rsplit('/',1)[1])
    with p.open('xb') as f:
        f.write(value)
    components.append({'source':'historical2.05 p1 reference ONLY','path_in_image':name,'output':str(p),
        'bytes':len(value),'sha256':sha256(value).hexdigest(),'text':value.decode('ascii'),
        'current_body_identity_verified':False})
put('source-inventory.json', {'sources':sources,'components':components,
    'reader_path':str(READER),'reader_sha256':EXPECTED_READER,
    'Sony_or_guest_code_executed':False,'mount_or_device_or_administrator_operations':0})
print(json.dumps({'components':[(e['path_in_image'],e['bytes'],e['sha256']) for e in components],
                  'Sony_or_guest_code_executed':False}))
