#!/usr/bin/env python3
"""r47 full-chain binding inventory: local base PAGE, helper routing, hashes, budgets.

Pure import/static checks only; no browser, server, network, VM, QMP, guest or spawn.
"""
import ast
import hashlib
import importlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'run-inputs/r47-offline-closed-loop'
OUT = HERE / 'receipts/binding-inventory.json'
NEW = 'f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf'
OLD = '852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b'
CHECKS = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(name, fn):
    detail = fn()
    CHECKS.append({'case': name, 'passed': True, 'detail': detail})
    print('PASS', name)


def main():
    source = json.loads((HERE / 'SOURCE-FREEZE.json').read_text())
    core = json.loads((HERE / 'CORE-SOURCE-FREEZE.json').read_text())
    expected = {str(HERE / rel): h for rel, h in source.items()}
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / 'LOCAL-SOURCE-FREEZE.json').write_text(json.dumps(expected, ensure_ascii=False, indent=2) + '\n')
    local = json.loads((RUN / 'LOCAL-SOURCE-FREEZE.json').read_text())
    assert len(source) == 44 and len(core) == 39, (len(source), len(core))
    assert local == expected
    for rel, h in source.items():
        assert sha(HERE / rel) == h, rel
    for rel, h in core.items():
        assert sha(HERE / rel) == h, rel
    assert 'trial_web_v22_navigation_review.py' in source and 'trial_web_v22_navigation_review.py' in core

    os.environ['FX3_NAV_RUN_DIR'] = str(RUN)
    sys.path.insert(0, str(HERE / 'runtime-wrapper'))
    sys.path.insert(0, str(HERE / 'operator-helpers'))
    common = importlib.import_module('common')
    r35 = importlib.import_module('r35_package_selection')
    review_cli = importlib.import_module('review_snapshot_cli')
    postkey = importlib.import_module('postkey_observation')
    # common routing tuple is the only dynamic helper selector.
    src = (HERE / 'runtime-wrapper/common.py').read_text()
    tree = ast.parse(src)
    route = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'helper':
            route = ast.get_source_segment(src, node)
    assert route and "'planned_navigation_click.py','review_snapshot_cli.py','deadline_cli.py','recovery_tools.py','postkey_observation.py'" in route
    assert common.CANDIDATE_OPS == HERE / 'operator-helpers'
    assert common.FROZEN == HERE.parent / 'v25-r21-recovery-integration'
    assert common.OPS == common.FROZEN / 'operator-helpers'
    assert common.PROFILE == 'r47-runtime-integration-60s'
    assert r35.APPROVED_HOST == HERE
    assert r35.PROFILE == 'r47-runtime-integration-60s' and r35.LABEL == 'v47runtime-n64-r47'
    assert r35.PACKAGE == HERE.parent / 'r42-command-timing-package'
    assert r35.CANDIDATE_SHA == '857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806'
    assert r35.CPIO_SHA == '59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63'
    assert review_cli.PAGE_SHA == NEW
    assert postkey.PAGE_SHA == NEW

    # Every executed old-PAGE-hash site is locally bound to the new candidate.
    hash_sites = {
        'operator-helpers/deadline.js': "const SCRIPT_SHA = '" + NEW + "'",
        'operator-helpers/recovery_cancel.js': "const PAGE_SHA='" + NEW + "'",
        'operator-helpers/recovery_readonly.js': "hash!=='" + NEW + "'",
        'operator-helpers/planned_navigation_click.py': "PAGE_SHA='" + NEW + "'",
        'runtime-wrapper/untimed_image.py': NEW,
        'runtime-wrapper/later_capture.py': NEW,
        'runtime-wrapper/launch_prepare.py': NEW,
        'PAGE-IDENTITY.json': NEW,
    }
    site_results = {}
    for rel, needle in hash_sites.items():
        text = (HERE / rel).read_text()
        assert needle in text, rel
        assert OLD not in text, rel
        site_results[rel] = {'new_present': True, 'old_absent': True, 'sha256': sha(HERE / rel)}
    # No old hash anywhere in actual runtime source (tests/docs/receipts excluded).
    runtime_files = list((HERE / 'runtime-wrapper').glob('*.py')) + list((HERE / 'operator-helpers').glob('*.py')) + \
        list((HERE / 'operator-helpers').glob('*.js')) + list((HERE / 'return-tools').glob('*.*')) + \
        [HERE / n for n in ('trial_web_v22_navigation_review.py', 'trial_web_r24_review_snapshot.py',
                            'run_trial_r24_review_snapshot.py', 'r35_package_selection.py', 'prepare_run.py',
                            'PAGE-IDENTITY.json', 'NAVIGATION-PLAN.json', 'review_page_r24.js', 'confirm_page_r24.js')]
    old_hits = [str(p.relative_to(HERE)) for p in runtime_files if OLD in p.read_text()]
    assert not old_hits, old_hits
    # 20000/20_000 semantics: no old operator budget literal in executed runtime.
    old_budget = []
    allowed_20_semantics = []
    for p in runtime_files:
        for lineno, line in enumerate(p.read_text().splitlines(), 1):
            if '20000' in line or '20_000' in line:
                if 'raw=02000007000000' in line:
                    allowed_20_semantics.append({'path': str(p.relative_to(HERE)), 'line': lineno,
                                                 'reason': 'serial raw literal, not a budget'})
                else:
                    old_budget.append({'path': str(p.relative_to(HERE)), 'line': lineno, 'text': line.strip()[:160]})
    assert not old_budget, old_budget
    # Preserved other 20s semantics and fixed budgets.
    web = (HERE / 'trial_web_r24_review_snapshot.py').read_text()
    runner = (HERE / 'run_trial_r24_review_snapshot.py').read_text()
    startup = (HERE / 'runtime-wrapper/start_and_wait.py').read_text()
    plan = json.loads((HERE / 'NAVIGATION-PLAN.json').read_text())
    assert 'SNAPSHOT_TTL=20.0' in web
    assert 'restore_native_api(qmp, input_gate, run, timeout=20)' in runner
    assert '<= 12' in runner or '<=12' in runner
    assert 'deadline=start_monotonic+180' in startup
    assert plan['runtime_budget'] == {'minutes': 8, 'accepted_keys': 8, 'explicit_attempts': 10,
                                      'attributed_unqueued_recoveries': 2, 'recoveries_per_step': 1}
    assert (HERE / 'operator-helpers/deadline.js').read_text().count('const DEADLINE_MS = 60_000;') == 1
    assert (HERE / 'trial_web_v22_navigation_review.py').read_text().count('h.deadline_ms!==60000') == 1
    assert (HERE / 'trial_web_v22_navigation_review.py').read_text().count('h.current.due_ms!==h.current.armed_ms+60000') == 1
    # Return adapter self-binding.
    adapter = (HERE / 'return-tools/return_adapter.py').read_text()
    core_sha = sha(HERE / 'CORE-SOURCE-FREEZE.json')
    operate_sha = sha(HERE / 'runtime-wrapper/operate.py')
    assert f"CORE_FREEZE_SHA='{core_sha}'" in adapter
    assert f"OPERATE_SHA='{operate_sha}'" in adapter
    assert f"FROZEN=Path(__file__).resolve().parents[1]" in adapter
    # prepare config is self-bound to this candidate.
    cfg = json.loads((RUN / 'config.json').read_text())
    assert cfg['candidate_source_root'] == str(HERE)
    assert cfg['runner_profile'] == r35.PROFILE
    assert cfg['frozen_root'] == str(common.FROZEN)
    assert cfg['plan_sha'] == sha(HERE / 'NAVIGATION-PLAN.json')
    # trial web imports the local base explicitly.
    tw = (HERE / 'trial_web_r24_review_snapshot.py').read_text()
    assert "BASE=HERE" in tw and "BASE=HERE.parent/'v25-r21-recovery-integration'" not in tw

    value = {
        'schema': 'fx3-r47-binding-inventory-v1', 'offline': True, 'browser': False,
        'server': False, 'network': False, 'VM': False, 'QMP': False, 'guest': False,
        'source_members': len(source), 'core_members': len(core),
        'source_sha256': sha(HERE / 'SOURCE-FREEZE.json'),
        'core_sha256': sha(HERE / 'CORE-SOURCE-FREEZE.json'),
        'local_source_freeze_equal': True,
        'profile': r35.PROFILE, 'label': r35.LABEL, 'approved_host': str(r35.APPROVED_HOST),
        'common': {'SOURCE': str(common.SOURCE), 'FROZEN': str(common.FROZEN),
                   'OPS': str(common.OPS), 'CANDIDATE_OPS': str(common.CANDIDATE_OPS),
                   'helper_routing_candidate_helpers': ['planned_navigation_click.py',
                                                        'review_snapshot_cli.py', 'deadline_cli.py',
                                                        'recovery_tools.py', 'postkey_observation.py']},
        'page_sha_binding_sites': site_results,
        'runtime_old_page_hash_hits': old_hits,
        'runtime_old_20000_hits': old_budget,
        'allowed_20_semantics': allowed_20_semantics,
        'review_snapshot_cli_PAGE_SHA': review_cli.PAGE_SHA,
        'postkey_observation_PAGE_SHA': postkey.PAGE_SHA,
        'page_identity': json.loads((HERE / 'PAGE-IDENTITY.json').read_text()),
        'preserved_budgets': {'snapshot_ttl': 20.0, 'api16_restore_timeout': 20,
                              'native_input_deadline': 12, 'startup_seconds': 180,
                              'total_minutes': 8, 'accepted_keys': 8, 'attempts': 10,
                              'recoveries': 2, 'recoveries_per_step': 1},
        'return_adapter': {'CORE_FREEZE_SHA': core_sha, 'OPERATE_SHA': operate_sha,
                           'candidate_root': str(HERE)},
        'prepare_config': cfg,
        'checks': CHECKS,
    }
    OUT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'source': len(source), 'core': len(core),
                      'old_page_hits': old_hits, 'old_20000_hits': old_budget,
                      'receipt': str(OUT)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
