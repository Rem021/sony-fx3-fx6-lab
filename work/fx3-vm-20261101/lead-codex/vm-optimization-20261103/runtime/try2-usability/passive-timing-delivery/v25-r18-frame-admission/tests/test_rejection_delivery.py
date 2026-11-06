"""Offline actual TrialState and r18 delivery helper tests; no guest or QEMU."""
import ast
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'v25-r17-tail-receipt/trial_web_v22_navigation_review.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


old = load(BASE, 'r17_original')
new = load(ROOT / 'trial_web_v22_navigation_review.py', 'r18_candidate')
delivery = load(ROOT / 'web_rejection_receipt.py', 'r18_rejection_delivery')
results = {}


def state(mod):
    s = mod.TrialState('offline', 60, 4096)
    s.update(phase='ready', ready=True)
    s.publish(b'A', {'sequence': 1, 'PNG_sha256': 'a' * 64,
                     'all_zero_pixels': False, 'pixel_source_sequence': 1})
    return s


def publish(s, seq, letter):
    s.publish(letter.encode(), {'sequence': seq, 'PNG_sha256': letter.lower() * 64,
                                'all_zero_pixels': False, 'pixel_source_sequence': seq})


def parity(name, configure, body, expected_reason, failures=()):
    a, b = state(old), state(new)
    configure(a)
    configure(b)
    prior_pending = len(b.pending)
    old_reply, new_reply = a.submit(body), b.submit(body)
    assert old_reply == new_reply, (name, old_reply, new_reply)
    snap = b.key_rejection_snapshot()
    if old_reply[0] == 202:
        assert snap['total'] == snap['truncated'] == 0 and snap['records'] == []
        assert len(b.pending) == prior_pending + 1
    else:
        assert snap['total'] == 1 and snap['truncated'] == 0 and len(snap['records']) == 1
        row = snap['records'][0]
        assert row['reason'] == expected_reason and row['failed_predicates'] == list(failures)
        assert len(b.pending) == prior_pending
        assert set(row).isdisjoint({'token', 'body', 'key', 'request_body'})
        assert type(row['host_monotonic_ns']) is int and row['host_monotonic_ns'] > 0
    results[name] = {'response': new_reply, 'diagnostic': snap}


parity('same_content_seq_forward', lambda s: publish(s, 2, 'A'),
       {'key': 427, 'observed_sequence': 1}, None)
parity('A_to_B', lambda s: publish(s, 2, 'B'),
       {'key': 427, 'observed_sequence': 1}, 'frame_identity_or_render_invalid',
       ('sha_mismatch', 'generation_mismatch'))
parity('A_B_A', lambda s: (publish(s, 2, 'B'), publish(s, 3, 'A')),
       {'key': 427, 'observed_sequence': 1}, 'frame_identity_or_render_invalid',
       ('generation_mismatch',))
parity('bad_observed_sequence', lambda s: None,
       {'key': 427, 'observed_sequence': 999}, 'observed_sequence_missing')
parity('unsupported_key', lambda s: None,
       {'key': 999, 'observed_sequence': 1}, 'unsupported_key')
parity('render_invalid', lambda s: s.publish(b'zero',
       {'sequence': 2, 'PNG_sha256': 'z' * 64, 'all_zero_pixels': True,
        'pixel_source_sequence': 2}), {'key': 427, 'observed_sequence': 1},
       'frame_identity_or_render_invalid', ('render_invalid', 'sha_mismatch', 'generation_mismatch'))
parity('lifecycle_stop', lambda s: s.stop.set(),
       {'key': 427, 'observed_sequence': 1}, 'stopping_or_error')
parity('busy', lambda s: s.update(busy=True),
       {'key': 427, 'observed_sequence': 1}, 'not_ready_or_pending')
parity('key_limit', lambda s: s.update(steps=s.max_steps),
       {'key': 427, 'observed_sequence': 1}, 'configured_key_limit')

s = state(new)
for i in range(70):
    code, _ = s.submit({'key': 427, 'observed_sequence': 100 + i})
    assert code == 409
snap = s.key_rejection_snapshot()
assert snap['total'] == 70 and snap['truncated'] == 6 and len(snap['records']) == 64
assert snap['records'][0]['observed_sequence'] == 106
snap['records'][0]['observed_sequence'] = -1
snap['records'].clear()
assert s.key_rejection_snapshot()['records'][0]['observed_sequence'] == 106
results['bounded_wrap_and_deepcopy'] = {'total': 70, 'truncated': 6, 'stored': 64}

with tempfile.TemporaryDirectory(prefix='fx3-r18-rejections-') as temp:
    run = Path(temp)
    empty = state(new)
    receipt = delivery.deliver(empty, run)
    assert receipt['complete'] is True and receipt['total'] == 0 and receipt['stored'] == 0
    raw = (run / 'web-key-rejections.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt['sha256']
    assert json.loads(raw)['records'] == []
    # An existing output is never overwritten and cannot masquerade as success.
    second = delivery.deliver(empty, run)
    assert second['complete'] is False and second['error_type'] == 'FileExistsError'
    assert (run / 'web-key-rejections.json').read_bytes() == raw
    results['zero_rejections_export_and_file_error'] = {'first': receipt, 'second': second}

    other = run / 'other'
    other.mkdir()
    complete = delivery.deliver(s, other)
    assert complete['complete'] is True and complete['total'] == 70 and complete['truncated'] == 6
    assert json.loads((other / 'web-key-rejections.json').read_bytes())['records'][0]['observed_sequence'] == 106
    results['bounded_export'] = complete

# Assert the actual runner integrates the helper after its QEMU cleanup block,
# before ordinary receipt construction, and treats failed export as a failed gate.
runner = (ROOT / 'run_trial_v25_diag_r3.py').read_text()
tree = ast.parse(runner)
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
delivery_calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name) and n.func.id == 'deliver_web_rejections']
assert len(delivery_calls) == 1
deliver_line = delivery_calls[0].lineno
cleanup_line = runner.splitlines().index('        finally:') + 1
receipt_line = next(n.lineno for n in ast.walk(main) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'receipt' for t in n.targets))
assert cleanup_line < deliver_line < receipt_line
assert "diagnostic_readback_pass and web_rejections_export['complete']" in runner
assert "'web_key_rejections_export': web_rejections_export" in runner
assert "'web_rejection_receipt.py'" in runner
results['runner_cleanup_order'] = {'cleanup_finally_line': cleanup_line,
                                    'delivery_line': deliver_line, 'receipt_line': receipt_line}

print(json.dumps({'passed': True, 'cases': list(results)}, ensure_ascii=False))
(ROOT / 'evidence').mkdir(exist_ok=True)
(ROOT / 'evidence' / 'rejection-delivery-test.json').write_text(
    json.dumps({'passed': True, 'cases': results}, ensure_ascii=False, indent=2) + '\n')
