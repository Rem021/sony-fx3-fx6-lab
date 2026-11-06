#!/usr/bin/env python3
"""Read-only static ABI/layout audit; never builds a CPIO or starts a guest."""
import hashlib,json,pathlib,re,subprocess
here=pathlib.Path(__file__).resolve().parent
runtime=here.parents[5]/'menu-repair-01/runtime'
old=runtime/'helpers'
r14=here.parent/'v25-r14-low-overhead-gate'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
original=(old/'fx3-ui-gate-v11.c').read_text()
prior=(r14/'fx3-ui-gate-v14.c').read_text()
current=(here/'fx3-ui-gate-v15.c').read_text()
tables={}
for name,typ in [('offsets','U'),('words','W'),('regs','U')]:
    pat=rf'const {typ} {name}\[60\]=\{{([^}}]+)\}}'
    a,b,c=[re.search(pat,x).group(1) for x in (original,prior,current)]
    assert a==b==c
    tables[name]=sha_value=hashlib.sha256(a.encode()).hexdigest()
assert sha(here/'fx3-ui-gate-probes-v1.S')==sha(old/'fx3-ui-gate-probes-v1.S')
assert sha(here/'fx3-ui-gate-probes-v1.S')=='b82a530c86ad3d37e06ba37828c72942c3c9188d904ed2b3a3bee89ebf9f62a1'
assert len(re.findall(r'static void snapshot_serve\(',current))==1
assert 'mirror();snapshot_serve(id,0);' in current
assert 'if(!tid)tid=(U)syscall(178)' in current
assert '#define SNAP_PAYLOAD_BYTES 0x310U' in current
assert 0x3000+0x40==0x3040 and 0x3040+0xc0==0x3100 and 0x3100+0x310==0x3410<0x4000
build=json.loads((here/'BUILD.json').read_text())
old_undef=[line.split()[-1] for line in subprocess.run(['objdump','-t',str(old/'fx3-ui-gate-v11.so')],capture_output=True,text=True).stdout.splitlines() if '*UND*' in line]
for item in build['variants'].values():
    assert item['exit']==0 and set(item['undefined_symbols'])==set(old_undef)
    assert len(item['statistics_symbol'])==1 and '0000000000000310' in item['statistics_symbol'][0]
result={'original_source_sha256':sha(old/'fx3-ui-gate-v11.c'),
 'original_assembly_sha256':sha(old/'fx3-ui-gate-probes-v1.S'),
 'assembly_byte_identical':True,'original_60_entry_tables_sha256':tables,
 'statistics_bytes':0x310,'snapshot_request':{'start':0x3000,'end':0x3040},
 'snapshot_ack':{'start':0x3040,'end':0x3100},
 'snapshot_payload':{'start':0x3100,'end':0x3410},
 'boot_region_start':0x4000,'undefined_symbols_identical_to_original_v11':True,
 'native_test_limit':'actual C under host ARM64 test stubs; guest assembly execution remains untested'}
(here/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
print('r15 static ABI/layout audit PASS')
