#!/usr/bin/env python3
"""Offline host binding, budget-contract, preserved-boundary and input-hash tests.

No VM, browser, server, QMP, guest, deployment or firmware write. The only
subprocesses are the candidate's own prepare/import checks (side effects blocked
by an audit hook) and the read-only package hash check.
"""
import ast
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
DEL = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery'
R42 = DEL / 'r42-command-timing-runner'
CAND = DEL / 'r44-review-budget-candidate'
PACKAGE = DEL / 'r42-command-timing-package'
DTB = DEL / 'v25-menu-osd-diagnostic-r3/vmopt-20261104-v25-menu-osd-diagnostic-r3/guest.dtb'
BUDGET_FILES = [
    'operator-helpers/deadline.js',
    'operator-helpers/recovery_cancel.js',
    'operator-helpers/snapshot_read.js',
    'operator-helpers/recovery_readonly.js',
    'operator-helpers/planned_navigation_click.js',
    'operator-helpers/postkey_read.js',
    'operator-helpers/snapshot_confirm.js',
    'operator-helpers/recovery_observation.py',
    'runtime-wrapper/cleanup.py',
    'runtime-wrapper/operate.py',
]
EXPECTED_60000 = {
    'operator-helpers/deadline.js': 0,  # uses 60_000 (underscore) exactly once
    'operator-helpers/recovery_cancel.js': 3,
    'operator-helpers/snapshot_read.js': 1,
    'operator-helpers/recovery_readonly.js': 5,
    'operator-helpers/planned_navigation_click.js': 1,
    'operator-helpers/postkey_read.js': 3,
    'operator-helpers/snapshot_confirm.js': 1,
    'operator-helpers/recovery_observation.py': 1,
    'runtime-wrapper/cleanup.py': 3,
    'runtime-wrapper/operate.py': 1,
}
INPUT_SHA = {
    'r42 SOURCE-FREEZE.json': '6f8d7e926ae6a1387c42cb43f8e4c95ca74e3c51572a8dac1bee783868a89652',
    'r42 CORE-SOURCE-FREEZE.json': '0760035499c8362eef3ee24c819d3b8f6cbed3bf156bf4ee8b09adc187b1ba68',
    'r42 package candidate.json': '857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806',
    'r42 package guest.cpio': '59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63',
    'fixed guest.dtb': '5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b',
}
PRESERVED_SHA = {
    'r42 run_trial_r24_review_snapshot.py': ('run_trial_r24_review_snapshot.py', '1f8cf2b78f3a56e2f38ab561ff1a7a3c072d984878a02be9b6afedf68a4fcd28'),
    'r42 trial_web_r24_review_snapshot.py': ('trial_web_r24_review_snapshot.py', '450d1e33413117ca4d6c29cb8fc4befbfc5eaa268b42c96c2e0c6e465fad5df2'),
    'r42 review_page_r24.js': ('review_page_r24.js', '26aaf20a42124dabd7b339662870e72c5351b99843afdff54f5652aca8d8e4a1'),
    'r42 confirm_page_r24.js': ('confirm_page_r24.js', '0bd31e9c2f61da3f645ce7191958ac00487208c0e770669f2c96c962f1b37c72'),
    'r42 PAGE-IDENTITY.json': ('PAGE-IDENTITY.json', '7f4b2f3a3f9c86fdb3193a2177135955f3aa000a135e819eba08493c0cf41a0a'),
    'r42 NAVIGATION-PLAN.json': ('NAVIGATION-PLAN.json', '4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f'),
    'r42 start_and_wait.py': ('runtime-wrapper/start_and_wait.py', 'e62309eb24b808d2e831607c767a7102a65e242a62de0a8df94d75e2f1a336d4'),
}
RESULTS = []


def check(name, fn):
    try:
        detail = fn()
        RESULTS.append({'case': name, 'passed': True, 'detail': detail})
    except Exception as exc:  # noqa: BLE001
        RESULTS.append({'case': name, 'passed': False, 'error': repr(exc)})
        raise


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jsonload(p):
    return json.loads(Path(p).read_text())


def hashes(label_paths):
    return {label: {'path': str(p), 'sha256': sha(p)} for label, p in label_paths.items()}


def test_source_manifests():
    old_s = jsonload(R42 / 'SOURCE-FREEZE.json')
    old_c = jsonload(R42 / 'CORE-SOURCE-FREEZE.json')
    new_s = jsonload(CAND / 'SOURCE-FREEZE.json')
    new_c = jsonload(CAND / 'CORE-SOURCE-FREEZE.json')
    assert len(old_s) == 43 and len(old_c) == 38
    assert len(new_s) == 43 and len(new_c) == 38
    assert set(new_c) == set(old_c)
    core_changed = sorted(rel for rel in new_c if new_c[rel] != old_c[rel])
    core_unchanged = sorted(rel for rel in new_c if new_c[rel] == old_c[rel])
    expected_core_changed = sorted([
        'operator-helpers/deadline.js', 'operator-helpers/planned_navigation_click.js',
        'operator-helpers/postkey_read.js', 'operator-helpers/recovery_cancel.js',
        'operator-helpers/recovery_observation.py', 'operator-helpers/recovery_readonly.js',
        'operator-helpers/snapshot_confirm.js', 'operator-helpers/snapshot_read.js',
        'prepare_run.py', 'r35_package_selection.py', 'runtime-wrapper/cleanup.py',
        'runtime-wrapper/operate.py',
    ])
    assert core_changed == expected_core_changed, core_changed
    assert len(core_changed) == 12 and len(core_unchanged) == 26
    for rel, expected in new_c.items():
        assert sha(CAND / rel) == expected, rel
        assert new_s[rel] == expected, rel
    all_changed = sorted(rel for rel in old_s if new_s[rel] != old_s[rel])
    unchanged = sorted(rel for rel in old_s if new_s[rel] == old_s[rel])
    code_changed = [rel for rel in all_changed if rel != 'CORE-SOURCE-FREEZE.json']
    expected_code_changed = sorted([
        'operator-helpers/deadline.js', 'operator-helpers/planned_navigation_click.js',
        'operator-helpers/postkey_read.js', 'operator-helpers/recovery_cancel.js',
        'operator-helpers/recovery_observation.py', 'operator-helpers/recovery_readonly.js',
        'operator-helpers/snapshot_confirm.js', 'operator-helpers/snapshot_read.js',
        'prepare_run.py', 'r35_package_selection.py', 'return-tools/return_adapter.py',
        'runtime-wrapper/cleanup.py', 'runtime-wrapper/operate.py',
    ])
    assert code_changed == expected_code_changed, code_changed
    assert all_changed == sorted(expected_code_changed + ['CORE-SOURCE-FREEZE.json'])
    assert len(all_changed) == 14 and len(unchanged) == 29
    for rel, expected in new_s.items():
        assert sha(CAND / rel) == expected, rel
    assert new_s['CORE-SOURCE-FREEZE.json'] == sha(CAND / 'CORE-SOURCE-FREEZE.json')
    delta = jsonload(CAND / 'CANDIDATE-DELTA.json')
    assert delta['candidate_source43_sha256'] == sha(CAND / 'SOURCE-FREEZE.json')
    assert delta['candidate_core38_sha256'] == sha(CAND / 'CORE-SOURCE-FREEZE.json')
    assert sorted(x['path'] for x in delta['changed']) == all_changed
    assert delta['unchanged_count'] == 29
    for row in delta['changed']:
        assert row['old'] == old_s[row['path']] and row['new'] == new_s[row['path']]
    for row in delta['unchanged']:
        assert row['sha256'] == new_s[row['path']] == old_s[row['path']]
    adapter = (CAND / 'return-tools/return_adapter.py').read_text()
    operate_sha = sha(CAND / 'runtime-wrapper/operate.py')
    core_sha = sha(CAND / 'CORE-SOURCE-FREEZE.json')
    assert f"OPERATE_SHA='{operate_sha}'" in adapter
    assert f"CORE_FREEZE_SHA='{core_sha}'" in adapter
    return {'source_entries': 43, 'core_entries': 38, 'all_changed': all_changed,
            'code_changed_count': len(code_changed), 'core_manifest_changed': True,
            'core_changed': core_changed, 'core_changed_count': len(core_changed),
            'core_unchanged_count': len(core_unchanged),
            'unchanged_count': len(unchanged), 'candidate_source_sha256': sha(CAND / 'SOURCE-FREEZE.json'),
            'candidate_core_sha256': core_sha,
            'return_adapter_operate_sha': operate_sha, 'return_adapter_core_sha': core_sha}


def test_budget_literals():
    per_file = {}
    for rel in BUDGET_FILES:
        text = (CAND / rel).read_text()
        assert '20000' not in text, ('old budget remains', rel)
        assert '20_000' not in text, ('old budget remains', rel)
        count = text.count('60000')
        per_file[rel] = {'count_60000': count, 'count_20000': 0}
        assert count == EXPECTED_60000[rel], (rel, count, EXPECTED_60000[rel])
    deadline = (CAND / 'operator-helpers/deadline.js').read_text()
    assert 'const DEADLINE_MS = 60_000;' in deadline
    assert (CAND / 'operator-helpers/recovery_observation.py').read_text().count('alarm_60s_browser_identity') == 1
    assert 'alarm_20s_browser_identity' not in (CAND / 'operator-helpers/recovery_observation.py').read_text()
    return per_file


def test_preserved_boundaries():
    out = {}
    for label, (rel, expected) in PRESERVED_SHA.items():
        got = sha(CAND / rel)
        assert got == expected, (label, got, expected)
        assert sha(R42 / rel) == expected
        out[label] = got
    run = (CAND / 'run_trial_r24_review_snapshot.py').read_text()
    r42run = (R42 / 'run_trial_r24_review_snapshot.py').read_text()
    tree = ast.parse(run)
    tree42 = ast.parse(r42run)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'native_input_deadline_error')
    fn42 = next(n for n in tree42.body if isinstance(n, ast.FunctionDef) and n.name == 'native_input_deadline_error')
    a = ast.get_source_segment(run, fn)
    b = ast.get_source_segment(r42run, fn42)
    assert a == b and '<= 12' in a
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'native_input_deadline_error']
    assert len(calls) == 1
    assert 'restore_native_api(qmp, input_gate, run, timeout=20)' in run
    web = (CAND / 'trial_web_r24_review_snapshot.py').read_text()
    assert 'SNAPSHOT_TTL=20.0' in web and 'PAGE_SCRIPT_SHA' in web
    plan = jsonload(CAND / 'NAVIGATION-PLAN.json')
    assert plan['runtime_budget'] == {'minutes': 8, 'accepted_keys': 8, 'explicit_attempts': 10, 'attributed_unqueued_recoveries': 2, 'recoveries_per_step': 1}
    start = (CAND / 'runtime-wrapper/start_and_wait.py').read_text()
    assert 'deadline=start_monotonic+180' in start
    postkey = (CAND / 'operator-helpers/postkey_read.js').read_text()
    assert 'wait.not_before_ms=wait.arm_ms+5000' in postkey
    assert 'Math.min(performance.now()+6000,before.h.current.due_ms)' in postkey
    out.update({'native_input_deadline_error_12s': 'byte-identical to r42', 'restore_native_api_timeout_20': 'byte-identical to r42',
                'SNAPSHOT_TTL': 20.0, 'PAGE_SCRIPT_SHA': '852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b',
                'startup_limit_seconds': 180, 'total_run_minutes': 8, 'first_observation_arm_plus_ms': 5000,
                'native_12_call_sites': 1})
    return out


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def observation_state(mode, budget, armed=1000, performance=2000, cancelled=None):
    due = armed + budget
    binding = {
        'attempt_id': '44444444-4444-4444-8444-444444444444',
        'nonce': '22222222-2222-4222-8222-222222222222',
        'launch_request_id': '11111111-1111-4111-8111-111111111111',
        'document_time_origin': 500,
        'base_step': 0,
        'expected_step': 1,
        'key': 427,
        'PNG_sha256': 'a' * 64,
        'content_generation': 2,
        'sequence': 10,
    }
    state = {
        'qualified': True, 'mode': mode, 'attempt_binding': binding, 'attempt_id': binding['attempt_id'],
        'nonce': binding['nonce'], 'launch_id': binding['launch_request_id'], 'document_time_origin': 500,
        'document_id': '66666666-6666-4666-8666-666666666666', 'step': 0, 'alarm_state': mode,
        'alarm_budget_ms': budget, 'alarm_due_exact_in_browser': True, 'alarm_armed_ms': armed,
        'alarm_due_ms': due, 'alarm_cancelled_ms': cancelled, 'phase': 'ready', 'ready': True,
        'busy': False, 'review_required': False, 'error': None, 'delivery_unknown': False,
        'review_unknown': False, 'protocol_unknown': False, 'ending': False, 'finished': False,
        'attempt_outcome': 'not_posted', 'mutation_called': False, 'performance_ms': performance,
        'sequence': 10,
        'fresh_server_lifecycle': {'phase': 'ready', 'ready': True, 'steps': 0,
                                   'launch_id': binding['launch_request_id'], 'busy': False,
                                   'review_required': False, 'error': None, 'protocol_unknown': False,
                                   'render_valid': True},
    }
    return binding, state


def test_recovery_observation_python():
    mod = load_module(CAND / 'operator-helpers/recovery_observation.py', 'r44_recovery_observation')
    binding, before = observation_state('armed', 60000, performance=2000)
    _, after = observation_state('armed', 60000, performance=3000)
    mod.valid_states(before, after, binding, 'armed')
    old_binding, old_before = observation_state('armed', 20000, performance=2000)
    _, old_after = observation_state('armed', 20000, performance=3000)
    try:
        mod.valid_states(old_before, old_after, old_binding, 'armed')
        raise AssertionError('old 20000 budget was accepted')
    except ValueError as exc:
        assert 'alarm_60s_browser_identity' in str(exc), exc
    bad_budget = dict(before, alarm_budget_ms=20000)
    try:
        mod.valid_states(bad_budget, dict(after, alarm_budget_ms=20000), binding, 'armed')
        raise AssertionError('mixed old budget was accepted')
    except ValueError as exc:
        assert 'alarm_60s_browser_identity' in str(exc)
    bad_flag = dict(before, alarm_due_exact_in_browser=False)
    try:
        mod.valid_states(bad_flag, after, binding, 'armed')
        raise AssertionError('non-exact due was accepted')
    except ValueError as exc:
        assert 'alarm_60s_browser_identity' in str(exc)
    cbinding, cbefore = observation_state('cancelled', 60000, performance=2000, cancelled=1500)
    _, cafter = observation_state('cancelled', 60000, performance=3000, cancelled=1500)
    mod.valid_states(cbefore, cafter, cbinding, 'cancelled')
    return {'armed_60000': 'accepted', 'old_20000': 'rejected', 'mixed_20000': 'rejected',
            'non_exact_due': 'rejected', 'cancelled_60000': 'accepted'}


def load_cleanup_alarm_disposition():
    text = (CAND / 'runtime-wrapper/cleanup.py').read_text()
    tree = ast.parse(text)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'alarm_disposition')
    ns = {'math': __import__('math'), 're': __import__('re')}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<alarm_disposition>', 'exec'), ns)
    return ns['alarm_disposition']


def test_cleanup_python():
    fn = load_cleanup_alarm_disposition()
    c = {'url': 'http://127.0.0.1:60752/', 'launch_id': '11111111-1111-4111-8111-111111111111'}
    base = {
        'version': 1, 'deadline_ms': 60000, 'expectedURL': c['url'], 'expectedLaunchId': c['launch_id'],
        'sealed': False, 'documentTimeOrigin': 500.0, 'events': [], 'current': None,
    }
    armed = {**base, 'current': {'nonce': '22222222-2222-4222-8222-222222222222', 'state': 'armed',
                                  'armed_ms': 1000, 'due_ms': 61000, 'deadline_ms': 60000},
             'events': [{'event': 'armed'}]}
    assert fn(armed, c) == 'valid_armed_do_not_cancel_or_dispose'
    cancelled = {**armed, 'current': {**armed['current'], 'state': 'cancelled', 'cancelled_ms': 30000},
                 'events': [{'event': 'armed'}, {'event': 'cancelled'}]}
    assert fn(cancelled, c) == 'valid_nonarmed'
    assert fn(base, c) == 'valid_null_never_armed'
    assert fn({**armed, 'deadline_ms': 20000}, c) == 'unknown_malformed'
    assert fn({**armed, 'current': {**armed['current'], 'due_ms': 21000}}, c) == 'unknown_malformed'
    assert fn({**armed, 'current': {**armed['current'], 'deadline_ms': 20000}}, c) == 'unknown_malformed'
    return {'armed_60000': 'valid_armed_do_not_cancel_or_dispose', 'cancelled_60000': 'valid_nonarmed',
            'null_never_armed': 'valid_null_never_armed', 'deadline_20000': 'unknown_malformed',
            'due_arm_20000': 'unknown_malformed', 'current_deadline_20000': 'unknown_malformed'}


def test_operate_assert():
    text = (CAND / 'runtime-wrapper/operate.py').read_text()
    tree = ast.parse(text)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        seg = ast.get_source_segment(text, node)
        if "arm['deadline_ms']" in seg:
            found.append(seg)
    assert len(found) == 1, found
    seg = found[0]
    assert "arm['deadline_ms']==60000" in seg and '20000' not in seg
    return {'assert': seg}


def test_selector_and_package():
    mod = load_module(CAND / 'r35_package_selection.py', 'r44_selector')
    assert mod.HOST == CAND
    assert mod.APPROVED_HOST == CAND
    assert mod.PROFILE == 'r44-review-budget-60s'
    assert mod.LABEL == 'v44review-n64-r44'
    assert mod.PACKAGE == PACKAGE
    assert mod.PINS['r42-command-timing-runner/SOURCE-FREEZE.json'] == INPUT_SHA['r42 SOURCE-FREEZE.json']
    assert mod.PINS['r42-command-timing-runner/CORE-SOURCE-FREEZE.json'] == INPUT_SHA['r42 CORE-SOURCE-FREEZE.json']
    run_dir = CAND / 'run-inputs' / 'preflight-task_00000000-r44binding'
    selection = mod.verify_package(run_dir)
    assert selection['profile'] == 'r44-review-budget-60s'
    assert selection['candidate_sha256'] == INPUT_SHA['r42 package candidate.json']
    assert selection['initrd_sha256'] == INPUT_SHA['r42 package guest.cpio']
    assert selection['label'] == 'v44review-n64-r44'
    return {'profile': selection['profile'], 'label': selection['label'],
            'candidate': selection['candidate_sha256'], 'initrd': selection['initrd_sha256'],
            'initrd_bytes': selection['initrd_bytes'], 'load_address': selection['load_address'],
            'dtb': selection['dtb_sha256'], 'pins': len(selection['provenance_manifest_pins'])}


def test_prepare_and_import_binding():
    run_dir = CAND / 'run-inputs' / 'preflight-task_00000000-r44binding'
    parent = CAND / 'run-inputs'
    parent.mkdir(parents=True, exist_ok=True)
    if run_dir.exists():
        assert run_dir.parent == parent and CAND in run_dir.parents
        shutil.rmtree(run_dir)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    prepare = subprocess.run(
        [sys.executable, '-B', str(CAND / 'prepare_run.py'), '--run-dir', str(run_dir),
         '--task-id', 'task_00000000', '--dispatch-id', 'ctx_00000000',
         '--session', 'fx3-deadline-r44-offline-binding'],
        text=True, capture_output=True, env=env, timeout=60)
    assert prepare.returncode == 0, prepare.stdout + prepare.stderr
    prepared = json.loads(prepare.stdout)
    assert prepared['status'] == 'prepared_only_no_process_started'
    assert prepared['config']['runner_profile'] == 'r44-review-budget-60s'
    assert prepared['config']['candidate_source_root'] == str(CAND)
    assert prepared['config']['scope'].endswith('candidate whole-step operator deadline 60s')
    assert jsonload(run_dir / 'LOCAL-SOURCE-FREEZE.json') == {str(CAND / rel): h for rel, h in jsonload(CAND / 'SOURCE-FREEZE.json').items()}
    files = sorted(p.name for p in run_dir.iterdir() if p.is_file())
    assert files == ['CLI-TEMPLATES.json', 'LOCAL-SOURCE-FREEZE.json', 'config.json', 'ledger.json']

    common_code = r'''
import json, os, sys
sys.path.insert(0, os.path.join(os.environ["FX3_NAV_RUN_DIR"], "..", "..", "runtime-wrapper"))
import common
print(json.dumps({"profile": common.PROFILE, "candidate_source_root": common.CFG["candidate_source_root"],
 "runner_profile": common.CFG["runner_profile"], "frozen_root": common.CFG["frozen_root"],
 "plan_sha": common.CFG["plan_sha"], "source_entries": len(common._expected_freeze),
 "here": str(common.HERE)}))
'''
    common = subprocess.run([sys.executable, '-B', '-c', common_code], text=True, capture_output=True,
                            env={**env, 'FX3_NAV_RUN_DIR': str(run_dir)}, timeout=60)
    assert common.returncode == 0, common.stdout + common.stderr
    common_value = json.loads(common.stdout)
    assert common_value['profile'] == 'r44-review-budget-60s'
    assert common_value['candidate_source_root'] == str(CAND)
    assert common_value['runner_profile'] == 'r44-review-budget-60s'
    assert common_value['source_entries'] == 43

    import_code = r'''
import json, os, runpy, sys
from pathlib import Path
r=Path(sys.argv[1]).resolve()
def audit(event,args):
 if event in ("subprocess.Popen","os.system","os.fork","os.posix_spawn","socket.__new__"):raise RuntimeError("forbidden import side effect: "+event)
sys.addaudithook(audit)
g=runpy.run_path(str(r/"run_trial_r24_review_snapshot.py"),run_name="r44_import_only")
mods={name:str(Path(sys.modules[name].__file__).resolve()) for name in ("startup_observation","trial_ring_cached","trial_log_v4_mss","qmp_line_transport","gate_input_usability","runtime_resource_guard","trial_web_r24_review_snapshot")}
for name in ("startup_observation","trial_ring_cached","trial_log_v4_mss","trial_web_r24_review_snapshot"):assert Path(mods[name]).parent==r
for name in ("qmp_line_transport","gate_input_usability","runtime_resource_guard"):assert Path(mods[name]).parent==r.parent/"v25-r21-recovery-integration"
assert Path(sys.modules["r35_package_selection"].__file__).resolve()==r/"r35_package_selection.py"
assert g["ACTIVE_GUARD"] is None and g["ACTIVE_STARTUP_OBSERVATION"] is None
print(json.dumps({"mode":"import_only_main_not_called","modules":mods,"run_dir":os.environ["FX3_NAV_RUN_DIR"]}))
'''
    imported = subprocess.run([sys.executable, '-B', '-c', import_code, str(CAND)], text=True, capture_output=True,
                              env={**env, 'FX3_NAV_RUN_DIR': str(run_dir)}, timeout=120)
    assert imported.returncode == 0, imported.stdout + imported.stderr
    imported_value = json.loads(imported.stdout)
    assert imported_value['mode'] == 'import_only_main_not_called'
    assert imported_value['modules']['trial_web_r24_review_snapshot'].startswith(str(CAND))
    assert imported_value['modules']['r35_package_selection'].startswith(str(CAND)) if 'r35_package_selection' in imported_value['modules'] else True
    logdir = CAND / 'receipts' / 'process'
    logdir.mkdir(parents=True, exist_ok=True)
    logs = {}
    for name, proc in (('prepare', prepare), ('common-import', common), ('run-trial-import-only', imported)):
        (logdir / (name + '.stdout.txt')).write_text(proc.stdout)
        (logdir / (name + '.stderr.txt')).write_text(proc.stderr)
        logs[name] = {'argv': proc.args, 'returncode': proc.returncode,
                      'stdout_path': str(logdir / (name + '.stdout.txt')),
                      'stdout_sha256': hashlib.sha256(proc.stdout.encode()).hexdigest(),
                      'stderr_path': str(logdir / (name + '.stderr.txt')),
                      'stderr_sha256': hashlib.sha256(proc.stderr.encode()).hexdigest()}
    return {'run_dir': str(run_dir), 'prepared_files': files, 'process_logs': logs,
            'prepare_stdout_sha256': hashlib.sha256(prepare.stdout.encode()).hexdigest(),
            'common': common_value, 'import_only': imported_value,
            'processes': {'prepare': 'one offline python child, no server', 'common_import': 'one offline python child',
                          'run_trial_import_only': 'one offline python child with audit hook blocking subprocess/socket'},
            'VM': False, 'browser': False, 'server': False, 'QMP': False, 'guest': False}


def test_source_syntax():
    py = sorted((CAND / 'operator-helpers').glob('*.py')) + sorted((CAND / 'runtime-wrapper').glob('*.py')) + [
        CAND / 'prepare_run.py', CAND / 'r35_package_selection.py', CAND / 'run_trial_r24_review_snapshot.py',
        CAND / 'startup_observation.py', CAND / 'trial_log_v4_mss.py', CAND / 'trial_ring_cached.py',
        CAND / 'trial_web_r24_review_snapshot.py', CAND / 'return-tools' / 'return_adapter.py',
    ]
    parsed = []
    for p in py:
        ast.parse(p.read_text())
        parsed.append(p.name)
    js = sorted((CAND / 'operator-helpers').glob('*.js')) + sorted((CAND / 'return-tools').glob('*.mjs')) + [
        CAND / 'review_page_r24.js', CAND / 'confirm_page_r24.js', CAND / 'return-tools' / 'short_tool.mjs',
    ]
    checked = []
    for p in sorted(set(js)):
        proc = subprocess.run(['node', '--check', str(p)], text=True, capture_output=True, timeout=30)
        assert proc.returncode == 0, (p, proc.stderr)
        checked.append(p.name)
    return {'python_parsed': len(parsed), 'node_check': checked}


INPUT_CAPTURE = {}


def capture_inputs(phase):
    """Capture the actual r42 inputs/package/DTB at a named suite boundary."""
    captured_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    captured_monotonic_ns = time.monotonic_ns()
    entries = {}
    for rel in sorted(jsonload(R42 / 'SOURCE-FREEZE.json')):
        p = R42 / rel
        entries['r42/' + rel] = {'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size,
                                 'mtime_ns': p.stat().st_mtime_ns}
    manifest = R42 / 'SOURCE-FREEZE.json'
    entries['r42/SOURCE-FREEZE.json'] = {'path': str(manifest), 'sha256': sha(manifest),
                                         'bytes': manifest.stat().st_size,
                                         'mtime_ns': manifest.stat().st_mtime_ns}
    for label, p in (('r42 package candidate.json', PACKAGE / 'candidate.json'),
                     ('r42 package guest.cpio', PACKAGE / 'guest.cpio'),
                     ('fixed guest.dtb', DTB)):
        entries[label] = {'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size,
                          'mtime_ns': p.stat().st_mtime_ns}
    return {'phase': phase, 'captured_utc': captured_utc,
            'captured_monotonic_ns': captured_monotonic_ns, 'entry_count': len(entries),
            'coverage': 'all 43 r42 SOURCE members + r42 SOURCE-FREEZE.json manifest + r42 package candidate.json/guest.cpio + fixed guest.dtb',
            'entries': entries}


def test_input_hashes_before_after():
    before = INPUT_CAPTURE.get('before')
    after = INPUT_CAPTURE.get('after')
    assert before is not None and after is not None
    assert before['phase'] == 'before_all_tests'
    assert after['phase'] == 'after_all_tests'
    assert before['captured_monotonic_ns'] <= INPUT_CAPTURE['tests_started_monotonic_ns']
    assert INPUT_CAPTURE['tests_finished_monotonic_ns'] <= after['captured_monotonic_ns']
    assert after['captured_monotonic_ns'] > before['captured_monotonic_ns']

    def content(capture):
        return {key: {'sha256': value['sha256'], 'bytes': value['bytes']}
                for key, value in capture['entries'].items()}

    assert content(before) == content(after)
    assert before['entries']['r42/SOURCE-FREEZE.json']['sha256'] == INPUT_SHA['r42 SOURCE-FREEZE.json']
    assert before['entries']['r42/CORE-SOURCE-FREEZE.json']['sha256'] == INPUT_SHA['r42 CORE-SOURCE-FREEZE.json']
    assert before['entries']['r42 package candidate.json']['sha256'] == INPUT_SHA['r42 package candidate.json']
    assert before['entries']['r42 package guest.cpio']['sha256'] == INPUT_SHA['r42 package guest.cpio']
    assert before['entries']['fixed guest.dtb']['sha256'] == INPUT_SHA['fixed guest.dtb']
    elapsed_ns = after['captured_monotonic_ns'] - before['captured_monotonic_ns']
    receipt = {
        'schema': 'fx3-r44-input-hashes-before-after-v1',
        'scope': 'r42 SOURCE43 members + r42 package candidate.json/guest.cpio + fixed guest.dtb',
        'boundary': 'before captured at main start before any check; after captured after all checks',
        'limitation': 'INPUTS-BEFORE is a final-validation start snapshot, not a pre-edit snapshot; the dispatch sealed r42 pins are the authority for the original input identity.',
        'test_suite_window': {
            'before_captured_utc': before['captured_utc'],
            'tests_started_monotonic_ns': INPUT_CAPTURE['tests_started_monotonic_ns'],
            'tests_finished_monotonic_ns': INPUT_CAPTURE['tests_finished_monotonic_ns'],
            'after_captured_utc': after['captured_utc'],
            'elapsed_ns': elapsed_ns,
        },
        'entry_count': before['entry_count'],
        'content_unchanged': True,
        'before': before,
        'after': after,
    }
    (CAND / 'receipts' / 'input-hashes-before-after.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return {'before_captured_utc': before['captured_utc'],
            'after_captured_utc': after['captured_utc'], 'elapsed_ns': elapsed_ns,
            'entry_count': before['entry_count'], 'coverage': before['coverage'],
            'content_unchanged': True, 'limitation': receipt['limitation']}


def main():
    INPUT_CAPTURE['before'] = capture_inputs('before_all_tests')
    INPUT_CAPTURE['tests_started_monotonic_ns'] = time.monotonic_ns()
    checks = [
        ('source_manifests_43_38_and_13_code_changed_29_unchanged', test_source_manifests),
        ('budget_literals_all_60000_no_20000', test_budget_literals),
        ('preserved_native12_snapshot20_page_startup_8min_8accepted', test_preserved_boundaries),
        ('recovery_observation_valid_states_accepts_60000_rejects_20000', test_recovery_observation_python),
        ('cleanup_alarm_disposition_accepts_60000_rejects_20000', test_cleanup_python),
        ('operate_arm_assert_60000', test_operate_assert),
        ('selector_package_profile_label_and_cpio_binding', test_selector_and_package),
        ('prepare_then_common_and_run_trial_import_only_binding', test_prepare_and_import_binding),
        ('source_syntax_python_ast_node_check', test_source_syntax),
    ]
    try:
        for name, fn in checks:
            check(name, fn)
    finally:
        INPUT_CAPTURE['tests_finished_monotonic_ns'] = time.monotonic_ns()
        INPUT_CAPTURE['after'] = capture_inputs('after_all_tests')
    check('input_hashes_before_after_unchanged', test_input_hashes_before_after)
    passed = sum(1 for r in RESULTS if r['passed'])
    receipt = {
        'schema': 'fx3-r44-host-binding-test-v1',
        'offline': True, 'VM': False, 'browser': False, 'server': False, 'QMP': False,
        'guest_execution': False, 'deployment': False, 'firmware_write': False,
        'candidate': str(CAND), 'cases_total': len(RESULTS), 'cases_passed': passed,
        'cases_failed': len(RESULTS) - passed, 'results': RESULTS,
        'input_capture': {
            'before_utc': INPUT_CAPTURE['before']['captured_utc'],
            'after_utc': INPUT_CAPTURE['after']['captured_utc'],
            'coverage': INPUT_CAPTURE['before']['coverage'],
            'entry_count': INPUT_CAPTURE['before']['entry_count'],
            'receipt': 'receipts/input-hashes-before-after.json',
        },
    }
    (CAND / 'receipts' / 'host-binding.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases_total': len(RESULTS), 'cases_passed': passed, 'receipt': 'receipts/host-binding.json'}, indent=2))
    raise SystemExit(0 if passed == len(RESULTS) else 1)


if __name__ == '__main__':
    main()
