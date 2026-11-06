#!/usr/bin/env python3
"""Freeze this offline candidate only; no VM or firmware packaging operations."""
import hashlib,json,pathlib
p=pathlib.Path(__file__).resolve().parent
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
sources={q.name:sha(q) for q in sorted(p.iterdir()) if q.is_file() and q.suffix in ('.py','.c','.S')}
(p/'SOURCE-FREEZE.json').write_text(json.dumps({'scope':'r15 offline sources only','files':sources},indent=2)+'\n')
delivery={q.name:sha(q) for q in sorted(p.iterdir()) if q.is_file() and q.name!='SHA256SUMS'}
(p/'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name,digest in delivery.items()))
print(f'{len(sources)} source files; {len(delivery)} delivery files')
