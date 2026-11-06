#!/usr/bin/env python3
"""Offline source check for the r46 page candidate.

Imports the frozen base PAGE module and the candidate copy, extracts the inline
script, and proves the candidate changes exactly the two recovery-budget literals.
No browser/server/VM is involved; imports have no side effects.
"""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
DEL = HERE.parent
ORIG = DEL / 'v25-r21-recovery-integration/trial_web_v22_navigation_review.py'
CAND = HERE / 'page/trial_web_v22_navigation_review_r46.py'
FIXTURE = HERE / 'tests/fixtures/PAGE-script.txt'
FIXTURE_R46 = HERE / 'page/PAGE-script-r46.txt'
IDENT = json.loads((HERE / 'page/PAGE-IDENTITY-r46.json').read_text())
OLD1 = 'h.deadline_ms!==20000'
NEW1 = 'h.deadline_ms!==60000'
OLD2 = 'h.current.due_ms!==h.current.armed_ms+20000'
NEW2 = 'h.current.due_ms!==h.current.armed_ms+60000'


def script_of(path):
    spec = importlib.util.spec_from_file_location('r46_page_' + hashlib.sha256(str(path).encode()).hexdigest()[:8], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    m = re.search(r'<script>(.*)</script>', mod.PAGE, re.S)
    assert m, 'inline script missing'
    return m.group(1)


def sha_text(s):
    return hashlib.sha256(s.encode()).hexdigest()


def main():
    orig = script_of(ORIG)
    cand = script_of(CAND)
    result = {
        'schema': 'fx3-r46-page-source-check-v1', 'offline': True, 'browser': False,
        'server': False, 'network': False, 'VM': False, 'QMP': False, 'guest': False,
        'base_page_sha256': hashlib.sha256(ORIG.read_bytes()).hexdigest(),
        'candidate_page_sha256': hashlib.sha256(CAND.read_bytes()).hexdigest(),
        'original_inline_script_sha256': sha_text(orig),
        'candidate_inline_script_sha256': sha_text(cand),
        'original_inline_bytes': len(orig), 'candidate_inline_bytes': len(cand),
        'fixture_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'fixture_r46_sha256': hashlib.sha256(FIXTURE_R46.read_bytes()).hexdigest(),
    }
    assert orig.count(OLD1) == 1 and orig.count(OLD2) == 1, (orig.count(OLD1), orig.count(OLD2))
    assert cand.count(OLD1) == 0 and cand.count(OLD2) == 0
    assert cand.count(NEW1) == 1 and cand.count(NEW2) == 1
    # Exactly two changed lines in the extracted base script, both budget literals.
    a = orig.split('\n'); b = cand.split('\n')
    assert len(a) == len(b)
    changed = [{'line': i + 1, 'old': a[i].strip(), 'new': b[i].strip()}
               for i in range(len(a)) if a[i] != b[i]]
    assert len(changed) == 2, json.dumps(changed)
    assert all((OLD1 in x['old'] and NEW1 in x['new']) or (OLD2 in x['old'] and NEW2 in x['new'])
               for x in changed)
    # The final r24 assembled script changes the same two lines only.
    f1 = FIXTURE.read_text(); f2 = FIXTURE_R46.read_text()
    fa = f1.split('\n'); fb = f2.split('\n')
    assert len(fa) == len(fb)
    fchanged = [{'line': i + 1, 'old': fa[i].strip(), 'new': fb[i].strip()}
                for i in range(len(fa)) if fa[i] != fb[i]]
    assert len(fchanged) == 2, json.dumps(fchanged)
    assert all((OLD1 in x['old'] and NEW1 in x['new']) or (OLD2 in x['old'] and NEW2 in x['new'])
               for x in fchanged)
    assert IDENT['original_canonical_script_sha256'] == hashlib.sha256(f1.encode()).hexdigest()
    assert IDENT['patched_canonical_script_sha256'] == hashlib.sha256(f2.encode()).hexdigest()
    result['base_changed_lines'] = changed
    result['final_changed_lines'] = fchanged
    result['identity'] = IDENT
    out = HERE / 'receipts/page-source-check.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'base_changed_lines': changed, 'final_changed_lines': fchanged,
                      'original_inline_sha256': result['original_inline_script_sha256'],
                      'candidate_inline_sha256': result['candidate_inline_script_sha256'],
                      'receipt': str(out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
