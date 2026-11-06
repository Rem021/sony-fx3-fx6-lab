#!/usr/bin/env python3
"""Rebuild only r15 diagnostic ELF variants; never repack CPIO."""
import hashlib, json, pathlib, subprocess
HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parents[5] / 'menu-repair-01/runtime'
OLD = json.loads((BASE / 'helpers/fx3-ui-gate-v11-build.json').read_text())
def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
assert sha(BASE / 'helpers/fx3-ui-gate-v11.c') == OLD['source_sha256']
assert sha(HERE / 'fx3-ui-gate-probes-v1.S') == sha(BASE / 'helpers/fx3-ui-gate-probes-v1.S')
receipt = {'original_build_sha': sha(BASE / 'helpers/fx3-ui-gate-v11-build.json'), 'variants': {}}
for n in (1, 64):
    args = OLD['args'].copy()
    idx = args.index('-Wl,-soname,fx3-ui-gate-v11.so')
    args[idx] = f'-Wl,-soname,fx3-ui-gate-v15-n{n}.so'
    args.insert(idx, f'-DFX3_GATE_PUBLISH_INTERVAL={n}')
    args[next(i for i,x in enumerate(args) if x.endswith('/fx3-ui-gate-v11.c'))] = str(HERE / 'fx3-ui-gate-v15.c')
    args[next(i for i,x in enumerate(args) if x.endswith('/fx3-ui-gate-probes-v1.S'))] = str(HERE / 'fx3-ui-gate-probes-v1.S')
    args[-1] = str(HERE / f'fx3-ui-gate-v15-n{n}.so')
    p = subprocess.run(args, capture_output=True, text=True)
    rec = {'command': args, 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    if p.returncode == 0:
        rec['sha256'] = sha(args[-1])
        q = subprocess.run(['objdump','-p',args[-1]], capture_output=True, text=True)
        rec['dynamic_dependencies'] = [line.strip() for line in q.stdout.splitlines() if 'NEEDED ' in line or 'SONAME ' in line]
        q = subprocess.run(['objdump','-t',args[-1]], capture_output=True, text=True)
        rec['undefined_symbols'] = [line.strip().split()[-1] for line in q.stdout.splitlines() if '*UND*' in line]
        rec['statistics_symbol'] = [line.strip() for line in q.stdout.splitlines() if line.strip().endswith(' st')]
    receipt['variants'][f'N{n}'] = rec
(HERE / 'BUILD.json').write_text(json.dumps(receipt, indent=2) + '\n')
assert all(v['exit']==0 for v in receipt['variants'].values())
print('N1/N64 cross-build PASS')
