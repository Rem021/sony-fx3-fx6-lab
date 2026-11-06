"""Read-only AP regular-file literal inventory and pinned public client review.

No target process, imported public client, USB interface, shell or camera action.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util, io, json, re, urllib.request
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
reader = BASE / 'stage2/extraction/read_filesystems.py'
assert sha256(reader.read_bytes()).hexdigest() == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec = importlib.util.spec_from_file_location('read_only_ap_fs', reader)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
fs = m.Ext2(BASE / 'stage2/extraction/nflasha15.img')
assert sha256(fs.b).hexdigest() == 'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
files = [r for r in fs.walk() if r['type'] == 0x8000]
assert len(files) == 797
needles = (b'sen_host_req', b'sen_host_res', b'/var/fifo', b'host_req', b'host_res')
hits = []
for rec in files:
    raw = fs.data(rec['inode'])
    matched = [s for s in needles if s in raw]
    if not matched:
        continue
    strings = [v.decode('ascii') for v in re.findall(rb'[\x20-\x7e]{4,}', raw)
               if any(n in v for n in needles)]
    hits.append({'path': rec['path'], 'inode': rec['inode'], 'bytes': len(raw),
                 'sha256': sha256(raw).hexdigest(), 'strings': strings})

core = next(r for r in files if r['path'] == '/lib/libsencore.so')
raw = fs.data(core['inode'])
assert sha256(raw).hexdigest() == 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
e = ELFFile(io.BytesIO(raw))
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
def read(va, n):
    s = next(s for s in e.iter_segments() if s['p_type'] == 'PT_LOAD'
             and s['p_vaddr'] <= va and va + n <= s['p_vaddr'] + s['p_filesz'])
    start = s['p_offset'] + va - s['p_vaddr']
    return raw[start:start + n]
functions = []
for va, size, name in [(0xec10, 140, 'TestMode'), (0xd724, 484, 'HostCommunicationCommand::DoExecute'),
                       (0x10344, 424, 'AdjustControlFunc')]:
    code = read(va, size)
    functions.append({'VA': hex(va), 'bytes': size, 'name': name,
                      'sha256': sha256(code).hexdigest(),
                      'disassembly': [f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in md.disasm(code, va)]})
assert read(0x1703f, len(b'/var/fifo/sen_host_req\x00')) == b'/var/fifo/sen_host_req\x00'
assert read(0x17056, len(b'/var/fifo/sen_host_res\x00')) == b'/var/fifo/sen_host_res\x00'

report = {'status': 'STATIC_FIFO_ROUTE_REVIEW_NOT_EXECUTION_CHANNEL_PROOF',
          'image_sha256': sha256(fs.b).hexdigest(), 'AP_regular_files_searched': len(files),
          'literal_hits': hits, 'core_functions': functions,
          'conclusion': 'The fixed host FIFO path belongs to TestMode, not the traced ADJUST TERM_MODE branch. A matching literal consumer has not been identified in these AP files. Constructed names, other partitions, runtime files or external peers are not excluded.',
          'original_code_executed': False, 'new_camera_operations': 0}
with (HERE / 'fifo-route-review.json').open('x') as f:
    json.dump(report, f, indent=2); f.write('\n')

def get(url, limit=1048576):
    req = urllib.request.Request(url, headers={'User-Agent': 'FX3-offline-source-audit', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(limit + 1)
    assert len(data) <= limit
    return data

commit = json.loads(get('https://api.github.com/repos/ma1co/Sony-PMCA-RE/commits/master'))
head = commit['sha']
url = f'https://raw.githubusercontent.com/ma1co/Sony-PMCA-RE/{head}/pmca/usb/sony.py'
client = get(url)
assert b'SONY_ADJUST_SENSER_TERM_MODE = (0x601, 0x1f)' in client
assert b'except:\n   pass' in client
# Store as text for review only; never import or run this camera-control module.
with (HERE / 'pmca-sony-source.txt').open('xb') as f:
    f.write(client)
lines = client.decode().splitlines()
start = next(i for i, l in enumerate(lines) if ' def setTerminalEnable(' in l)
client_report = {'repository': 'ma1co/Sony-PMCA-RE', 'commit': head,
                 'commit_date': commit['commit']['committer']['date'],
                 'source_url': f'https://github.com/ma1co/Sony-PMCA-RE/blob/{head}/pmca/usb/sony.py',
                 'raw_source_url': url, 'sha256': sha256(client).hexdigest(),
                 'setTerminalEnable_first_line': start + 1, 'setTerminalEnable_excerpt': lines[start:start + 9],
                 'interpretation': 'setTerminalEnable ignores ADJUST exceptions; return without exception is not evidence that TERM_MODE succeeded on FX3.',
                 'public_client_executed_or_imported': False, 'new_camera_operations': 0}
with (HERE / 'public-client-review.json').open('x') as f:
    json.dump(client_report, f, indent=2); f.write('\n')
print(json.dumps({'AP_regular_files': len(files), 'literal_hit_files': [r['path'] for r in hits],
                  'PMCA_commit': head, 'client_ignores_adjust_exception': True, 'new_camera_operations': 0}))
