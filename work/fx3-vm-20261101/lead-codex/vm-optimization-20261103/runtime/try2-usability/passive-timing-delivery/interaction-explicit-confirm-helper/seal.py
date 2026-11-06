#!/usr/bin/env python3
"""Freeze this standalone offline helper and its pinned external source inputs."""
import hashlib,json,pathlib
p=pathlib.Path(__file__).resolve().parent
dep=p.parent
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
sources=['explicit_confirm.js','explicit_confirm_cli.py','offline_browser_test.py','seal.py']
(p/'SOURCE-FREEZE.json').write_text(json.dumps({'scope':'offline explicit-confirm source',
 'files':{name:sha(p/name) for name in sources}},indent=2)+'\n')
external={
 'r17_PAGE':dep/'v25-r17-tail-receipt/trial_web_v22_navigation_review.py',
 'original_deadline_JS':dep/'interaction-deadline-helper/deadline.js',
 'original_deadline_CLI':dep/'interaction-deadline-helper/deadline_cli.py',
}
(p/'DEPENDENCIES.json').write_text(json.dumps({k:{'path':str(v),'sha256':sha(v)}
 for k,v in external.items()},indent=2)+'\n')
all_files=sorted(q for q in p.rglob('*') if q.is_file() and '__pycache__' not in q.parts and q.name!='SHA256SUMS')
(p/'SHA256SUMS').write_text(''.join(f'{sha(q)}  {q.relative_to(p)}\n' for q in all_files))
print(len(sources),'source files;',len(all_files),'delivery files')
