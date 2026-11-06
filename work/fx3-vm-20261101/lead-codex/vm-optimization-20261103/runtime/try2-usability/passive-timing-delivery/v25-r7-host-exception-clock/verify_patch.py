#!/usr/bin/env python3
"""Apply to a small source copy under this directory; never import/run main."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'v25-r6-qmp-startup/run_trial_v25_diag_r3.py'
SOURCE_SHA = '2101edb5eb9c7789faa5c753e206fe315df87307df0695d290a95e718fb4846c'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    volume = plistlib.loads(subprocess.check_output(
        ['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    raw = SOURCE.read_bytes()
    assert sha(raw) == SOURCE_SHA
    target = json.loads((HERE / 'PATCH-TARGET.json').read_text())
    patch = HERE / 'r6-to-r7-host-exception-clock.patch'
    assert sha(patch.read_bytes()) == target['patch_sha256']
    # Only this 64 KB Python file is copied, never a guest or image.
    checks = HERE / 'apply-checks'
    checks.mkdir(exist_ok=True)
    copied = Path(tempfile.mkdtemp(prefix='check-', dir=checks))
    candidate = copied / SOURCE.name
    candidate.write_bytes(raw)
    commands = []
    for dry_run in (True, False):
        argv = ['/usr/bin/patch', '--batch', '--fuzz=0', '-p1', '-d', str(copied),
                '-i', str(patch)]
        if dry_run:
            argv.append('--dry-run')
        result = subprocess.run(argv, capture_output=True, text=True)
        commands.append({'argv': argv, 'exit_code': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
        assert result.returncode == 0, commands[-1]
        assert 'offset' not in result.stdout.lower()
        assert 'fuzz' not in result.stdout.lower()
    actual = candidate.read_bytes()
    assert sha(actual) == target['patched_sha256']
    assert sha(SOURCE.read_bytes()) == SOURCE_SHA
    # Compile only: executing the runner or importing its VM dependencies is forbidden here.
    compile(actual, str(candidate), 'exec')
    compile((HERE / 'host_exception_clock.py').read_bytes(), 'host_exception_clock.py', 'exec')
    before, after = ast.parse(raw), ast.parse(actual)
    old_main = next(n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    new_main = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    dump = lambda n: ast.dump(n, include_attributes=False)
    # All original main finally blocks (QMP/API restoration, waits, signals, close) are identical.
    finals = lambda main: [dump(ast.Module(body=n.finalbody, type_ignores=[]))
                           for n in ast.walk(main) if isinstance(n, ast.Try) and n.finalbody]
    assert finals(old_main) == finals(new_main)
    qmp_calls = lambda main: [dump(n) for n in ast.walk(main) if isinstance(n, ast.Call)
                             and isinstance(n.func, ast.Name)
                             and n.func.id in {'qmp', 'startup_handshake', 'restore_native_api'}]
    assert qmp_calls(old_main) == qmp_calls(new_main)
    # The outer finalizer loop is identical after removing only the added evidence observer.
    old_execute = next(n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == 'execute_runner')
    new_execute = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == 'execute_runner')

    class RemoveEvidence(ast.NodeTransformer):
        def visit_If(self, node):
            if (len(node.body) == 1 and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Call)
                    and isinstance(node.body[0].value.func, ast.Name)
                    and node.body[0].value.func.id == 'write_host_first_exception'):
                return None
            return self.generic_visit(node)

    assert dump(old_execute) == dump(RemoveEvidence().visit(new_execute))
    receipt = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source': str(SOURCE), 'source_sha256_before': sha(raw),
               'source_sha256_after': sha(SOURCE.read_bytes()),
               'patch_sha256': sha(patch.read_bytes()),
               'applied_source': str(candidate), 'applied_source_sha256': sha(actual),
               'helper_sha256': sha((HERE / 'host_exception_clock.py').read_bytes()),
               'volume_uuid': volume['VolumeUUID'], 'commands': commands,
               'compile_only': 'PASS', 'main_finally_ast_unchanged': True,
               'qmp_and_startup_budget_calls_ast_unchanged': True,
               'execute_runner_control_flow_ast_unchanged_except_evidence_calls': True,
               'runner_imported': False, 'runner_executed': False, 'vm_started': False,
               'integration_status': 'not_integrated'}
    (HERE / 'PATCH-APPLY-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return candidate, receipt


if __name__ == '__main__':
    _, receipt = verify()
    print(json.dumps(receipt, indent=2))
