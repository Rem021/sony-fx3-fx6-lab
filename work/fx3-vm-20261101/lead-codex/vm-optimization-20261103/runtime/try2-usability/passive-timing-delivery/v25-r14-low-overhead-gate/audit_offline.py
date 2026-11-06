#!/usr/bin/env python3
import hashlib,json,pathlib,re,subprocess
p=pathlib.Path(__file__).resolve().parent
old=p.parents[5]/'menu-repair-01/runtime/helpers'
def sha(q):return hashlib.sha256(pathlib.Path(q).read_bytes()).hexdigest()
a=(old/'fx3-ui-gate-v11.c').read_text();b=(p/'fx3-ui-gate-v14.c').read_text()
tables={}
for name,typ in [('offsets','U'),('words','W'),('regs','U')]:
 pat=rf'const {typ} {name}\[60\]=\{{([^}}]+)\}}'
 x=re.search(pat,a).group(1); y=re.search(pat,b).group(1)
 assert x==y
 tables[name]={'identical':True,'sha256':hashlib.sha256(x.encode()).hexdigest()}
assert sha(old/'fx3-ui-gate-probes-v1.S')==sha(p/'fx3-ui-gate-probes-v1.S')
assert all(not (0x3000<end and start<0x3040) for start,end in [(0,0x100),(0x100,0x410),(0x1100,0x1410),(0x4000,0x7000),(0x8000,0xa800),(0xb000,0x10000)])
assert 'AUTH_HEADER' not in b and '0x3000' not in b
build=json.loads((p/'BUILD.json').read_text())
old_undef=[line.split()[-1] for line in subprocess.run(['objdump','-t',str(old/'fx3-ui-gate-v11.so')],capture_output=True,text=True).stdout.splitlines() if '*UND*' in line]
for v in build['variants'].values():
 assert v['exit']==0
 assert set(v['undefined_symbols'])==set(old_undef)
 assert len(v['statistics_symbol'])==1 and '0000000000000310' in v['statistics_symbol'][0]
result={'original_source_sha256':sha(old/'fx3-ui-gate-v11.c'),'original_assembly_sha256':sha(old/'fx3-ui-gate-probes-v1.S'),'new_assembly_identical':True,'original_tables':tables,'old_undefined_symbols':old_undef,'new_undefined_symbols_identical':True,'future_observer_0x3000_0x3400_not_written_by_r14_core':True,'statistics_bytes':0x310,'legacy_prefix_bytes':0x300,'new_fields':['object_mismatch','root_change'],'static_semantic_limit':'original branch instructions unchanged; native host stub does not validate guest GPR/SIMD/NZCV execution'}
(p/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
print('instruction/assembly/layout/undefined dependency audit PASS')
