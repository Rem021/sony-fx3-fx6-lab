"""Exercise actual old/new lock-acquisition AST against disposable host locks."""
import ast
import fcntl
import hashlib
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
NEW = HERE.parent / 'run_trial_v18_preinput_stop.py'
OLD = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/run_trial_v3.py')


def extract(path):
    tree = ast.parse(path.read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    index = next(i for i, n in enumerate(main.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'locks' for t in n.targets))
    body = main.body[index:index + 2]
    assert isinstance(body[1], ast.For)
    assert '.run.lock' in ast.unparse(body[1])
    return compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec')


def free(path):
    with path.open('rb') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(f, fcntl.LOCK_UN)
        return True


rows = []
for source in (OLD, NEW):
    code = extract(source)
    for busy_index in (0, 1):
        with tempfile.TemporaryDirectory(prefix='locks-', dir=HERE) as tmp:
            root = Path(tmp)
            dirs = [root / 'frozen', root / 'runtime']
            for d in dirs:
                d.mkdir()
                (d / '.run.lock').touch()
            paths = [d / '.run.lock' for d in dirs]
            holder = paths[busy_index].open('rb')
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ns = dict(FROZEN=dirs[0], ROOT=dirs[1], fcntl=fcntl)
            error = None
            try:
                exec(code, ns)
            except Exception as exc:
                error = exc
            assert error is not None
            assert not free(paths[busy_index]), 'must not steal active owner lock'
            partial_released = free(paths[0]) if busy_index == 1 else None
            if source == OLD:
                assert isinstance(error, BlockingIOError)
                if busy_index == 1:
                    assert partial_released is False
            else:
                assert isinstance(error, RuntimeError)
                assert '已有 FX3' in str(error)
                if busy_index == 1:
                    assert partial_released is True
            rows.append(dict(source=str(source), busy_index=busy_index,
                             error_type=type(error).__name__, error=str(error),
                             active_owner_preserved=True,
                             first_lock_released_before_outer_exit=partial_released))
            for handle in ns.get('locks', []) + [ns.get('lock'), holder]:
                if handle is not None and not handle.closed:
                    handle.close()
            assert all(free(p) for p in paths)

result = dict(scope='Actual production lock-acquisition blocks; disposable host files only; no QEMU',
              source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (OLD, NEW)},
              cases=rows, old_screenshot_root_cause_proven=False,
              screenshot_error_reproduced_by_lock_contention=True,
              current_default_entry_changed=False)
(HERE / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
