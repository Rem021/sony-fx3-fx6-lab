#!/usr/bin/env python3
"""Real-runner import-only proof of the locally served PAGE.

No runner main, browser, server, socket, QMP or guest. The audit hook blocks
subprocess/socket side effects; only the module import graph is executed.
"""
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'run-inputs/r47-offline-closed-loop'
OUT = HERE / 'receipts'
OUT.mkdir(exist_ok=True)
EXPECT_CANONICAL = 'f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf'
EXPECT_FULL = '551cbd919f61858ba8542a3a46d7eab3894162c915038d92d5a16317bc3c719b'


def sha_text(s):
    return hashlib.sha256(s.encode()).hexdigest()


def main():
    os.environ['FX3_NAV_RUN_DIR'] = str(RUN)
    blocked = []

    def audit(event, args):
        if event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.posix_spawn', 'socket.__new__'):
            blocked.append(event)
            raise RuntimeError('forbidden import side effect: ' + event)

    sys.addaudithook(audit)
    g = runpy.run_path(str(HERE / 'run_trial_r24_review_snapshot.py'), run_name='r47_import_only')
    tw = sys.modules['trial_web_r24_review_snapshot']
    base = tw.base
    canonical = tw.PAGE.split('<script>')[1].split('</script>')[0]
    served = canonical.replace('const token=__TOKEN__;', 'const token="r47-test-token";')
    full_sha = sha_text(tw.PAGE)
    (OUT / 'final-canonical-script.txt').write_text(canonical)
    (OUT / 'final-served-script.txt').write_text(served)
    from r35_package_selection import PROFILE, LABEL, APPROVED_HOST
    modules = {name: str(Path(sys.modules[name].__file__).resolve())
               for name in ('trial_web_r24_review_snapshot', 'r35_package_selection',
                            'startup_observation', 'trial_ring_cached', 'trial_log_v4_mss',
                            'qmp_line_transport', 'gate_input_usability', 'runtime_resource_guard')}
    value = {
        'schema': 'fx3-r47-import-only-page-v1', 'offline': True, 'browser': False,
        'server': False, 'network': False, 'VM': False, 'QMP': False, 'guest': False,
        'runner': str(HERE / 'run_trial_r24_review_snapshot.py'),
        'runner_main_called': False, 'blocked_import_side_effects': blocked,
        'modules': modules,
        'base_page_module': str(Path(base.__file__).resolve()),
        'base_page_under_candidate': Path(base.__file__).resolve().parent == HERE,
        'trial_web_under_candidate': Path(tw.__file__).resolve().parent == HERE,
        'profile': PROFILE, 'label': LABEL, 'approved_host': str(APPROVED_HOST),
        'canonical_script_sha256': tw.PAGE_SCRIPT_SHA,
        'expected_canonical_script_sha256': EXPECT_CANONICAL,
        'full_PAGE_sha256': full_sha,
        'expected_full_PAGE_sha256': EXPECT_FULL,
        'canonical_script_bytes': len(canonical.encode()),
        'full_PAGE_bytes': len(tw.PAGE.encode()),
        'base_PAGE_new_budget': 'h.deadline_ms!==60000' in base.PAGE and 'h.current.due_ms!==h.current.armed_ms+60000' in base.PAGE,
        'base_PAGE_old_budget_absent': 'h.deadline_ms!==20000' not in base.PAGE and 'h.current.due_ms!==h.current.armed_ms+20000' not in base.PAGE,
        'served_PAGE_new_budget': 'h.deadline_ms!==60000' in tw.PAGE and 'h.current.due_ms!==h.current.armed_ms+60000' in tw.PAGE,
        'served_PAGE_old_budget_absent': 'h.deadline_ms!==20000' not in tw.PAGE and 'h.current.due_ms!==h.current.armed_ms+20000' not in tw.PAGE,
        'canonical_sha256': sha_text(canonical),
        'served_sha256': sha_text(served),
        'source_freezes': {
            'SOURCE-FREEZE.json': hashlib.sha256((HERE / 'SOURCE-FREEZE.json').read_bytes()).hexdigest(),
            'CORE-SOURCE-FREEZE.json': hashlib.sha256((HERE / 'CORE-SOURCE-FREEZE.json').read_bytes()).hexdigest(),
            'PAGE-IDENTITY.json': hashlib.sha256((HERE / 'PAGE-IDENTITY.json').read_bytes()).hexdigest(),
        },
        'ACTIVE_GUARD': g.get('ACTIVE_GUARD'),
        'ACTIVE_STARTUP_OBSERVATION': g.get('ACTIVE_STARTUP_OBSERVATION'),
    }
    assert not blocked, blocked
    assert value['base_page_under_candidate'] and value['trial_web_under_candidate']
    assert value['canonical_script_sha256'] == EXPECT_CANONICAL
    assert full_sha == EXPECT_FULL
    assert value['base_PAGE_new_budget'] and value['base_PAGE_old_budget_absent']
    assert value['served_PAGE_new_budget'] and value['served_PAGE_old_budget_absent']
    assert value['canonical_sha256'] == EXPECT_CANONICAL
    assert value['ACTIVE_GUARD'] is None and value['ACTIVE_STARTUP_OBSERVATION'] is None
    (OUT / 'page-import-only.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'canonical': value['canonical_script_sha256'],
                      'full': full_sha, 'base': value['base_page_module'],
                      'receipt': str(OUT / 'page-import-only.json')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
