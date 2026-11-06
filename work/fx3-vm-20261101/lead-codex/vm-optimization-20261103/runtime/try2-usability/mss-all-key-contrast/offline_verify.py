#!/usr/bin/env python3
"""Offline host gates for the isolated MSS key contrast runner; forbids real Popen."""
import ast
import contextlib
import fcntl
import importlib.util
import io
import json
import signal
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'run_trial_v17_mss_key_contrast.py'


def load():
    spec = importlib.util.spec_from_file_location('mss_key_contrast_runner', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def startup_body(module):
    tree = ast.parse(SOURCE.read_text())
    main = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'main')
    start = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'journal' for t in node.targets))
    main.body = main.body[start:]
    main.name = 'exercise_startup'
    main.args = ast.parse('def f(run, ns, args, env, checks, observer_sources, candidate_path, candidate, locks, snapshots): pass').body[0].args
    namespace = dict(vars(module))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[main], type_ignores=[])),
                 str(SOURCE), 'exec'), namespace)
    return namespace


def main():
    module = load()
    assert module.valid_command(1, 0x1ab, 100, 0, 0, 32)
    assert module.valid_command(12, 0x30, 100, 11, 0, 32)
    assert not module.valid_command(1, 0x1ab, 100, 0, 0, 12)
    assert module.native_input_deadline_error({'sent_monotonic': 100}, 1, {1: (101, 0)}, False, 113)
    assert module.native_input_deadline_error({'sent_monotonic': 100}, 1, {1: (101, 0)}, True, 113) is None
    runner_ast = ast.parse(SOURCE.read_text())
    main_ast = next(x for x in runner_ast.body if isinstance(x, ast.FunctionDef) and x.name == 'main')
    text = SOURCE.read_text()
    assert text.index('phaseA_capture = None\n    phase_exit_hit = False') < text.index('subprocess.Popen(args')
    assert "'serial_log_not_created'" in text and "deadline = start + ns.seconds" in text
    assert "host_step >= 12" in text and "deadline-240" in text
    candidate_path = module.OUT / 'vmopt-20261103-try2-mss-all-v3/candidate.json'
    assert module.digest(candidate_path) == '2382063eacb5f185e8553c2596be2c644654efe7234adc1e4578f7464ab99a05'
    candidate = json.loads(candidate_path.read_text())
    seed = Path(candidate['native_Backup_seed']['path'])
    assert module.digest(seed) == '92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f'
    namespace = startup_body(module)
    with tempfile.TemporaryDirectory(prefix='offline-host-', dir=HERE) as directory:
        temp = Path(directory)
        run = temp / 'run'; run.mkdir()
        frozen = temp / 'frozen'; frozen.mkdir()
        runtime = temp / 'runtime'; runtime.mkdir()
        held = []
        for root in (frozen, runtime):
            path = root / '.run.lock'; path.touch()
            stream = path.open('rb'); fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB); held.append(stream)
        manifest = temp / 'candidate.json'; manifest.write_text('{}')
        def denied(*args, **kwargs):
            raise OSError('offline fixture forbids QEMU spawn')
        namespace['subprocess'] = types.SimpleNamespace(Popen=denied, TimeoutExpired=module.subprocess.TimeoutExpired)
        namespace['FROZEN'] = frozen
        namespace['ROOT'] = runtime
        namespace['checkpoint'] = lambda value: None
        ns = types.SimpleNamespace(internal_hoststep=True, seconds=60, max_steps=32, port=0,
                                   exit_at_phase=None)
        saved = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                result = namespace['exercise_startup'](run, ns, [], {}, [], [], manifest, {}, held, [])
        finally:
            for sig, handler in saved.items(): signal.signal(sig, handler)
            for stream in held:
                if not stream.closed: fcntl.flock(stream, fcntl.LOCK_UN); stream.close()
        receipt = json.loads((run / 'receipt.json').read_text())
        assert result == 2 and receipt['stop_cause'] == 'host_error'
        assert 'offline fixture forbids QEMU spawn' in receipt['host_observer_error']
        assert receipt['date99_raw_serial_evidence']['reason'] == 'serial_log_not_created'
        assert receipt['qemu_pid'] is None and receipt['key_steps'] == 0
        assert all(item['free_at_close'] for item in receipt['locks'])
    out = {'capacity_32_step_1_and_12': True, 'capacity_12_rejected': True,
           'actual_host_budget_12': True, 'host_900s_cleanup_reserve_240s': True,
           'startup_spawn_error_receipt_without_QEMU': True, 'serial_absent_explicit_unknown': True,
           'native_receive_missing_deadline': True, 'candidate_and_English_seed_sha_fixed': True}
    (HERE / 'offline-receipt.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
