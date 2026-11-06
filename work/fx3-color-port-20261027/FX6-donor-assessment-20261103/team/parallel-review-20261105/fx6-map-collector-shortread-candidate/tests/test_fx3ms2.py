#!/usr/bin/env python3
import json, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parent
sys.path.insert(0, str(CAND / 'host'))
sys.path.insert(0, str(CAND / 'tools'))
import fx3ms2 as F
import make_fixtures as MF

FIX = CAND / 'fixtures/native-target-frame-v2.serial'
NOAPP = CAND / 'fixtures/no-appfw-v2.serial'
VALID = FIX.read_text()
checks = []

def check(name, fn):
    fn()
    checks.append(name)
    print('PASS', name, flush=True)

class Deadline:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds
    def remaining_observation(self):
        return max(0.0, self.end - time.monotonic())
    def remaining_total(self):
        return max(0.0, self.end - time.monotonic())

def raises(exc, fn, contains=None):
    try:
        fn()
    except exc as e:
        if contains is not None and contains not in str(e):
            raise AssertionError('wrong error %r, want %r' % (str(e), contains))
        return e
    except Exception as e:
        raise AssertionError('wrong exception type %r: %r' % (type(e).__name__, str(e)))
    raise AssertionError('no exception')

def test_accept():
    d = F.decode(VALID)
    assert d['pid'] == 239 and d['starttime'] == 777
    assert d['read_count'] == 3 and d['eintr_count'] == 2 and d['read_attempts'] == 6
    assert d['snapshot_atomic'] is False and d['bytes'] == 10563
    m = F.FramedProviderV2().select(VALID)
    assert m['ap']['bias'] == 0x7efab5b000 and m['snapshot_atomic'] is False
    assert m['read_count'] == 3 and m['eintr_count'] == 2
check('accept_valid_fixture', test_accept)

def test_legacy_reject():
    src = (CAND / 'fixtures/source-native-target-frame-fx3ms1.serial').read_text()
    raises(F.Reject, lambda: F.FramedProviderV2().select(src), 'legacy FX3MS1')
check('legacy_fx3ms1_rejected_no_fallback', test_legacy_reject)

def test_wait_partial_then_complete():
    raw = VALID.encode()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'serial.log'
        p.write_bytes(b'')
        def w():
            for i in range(0, len(raw), 97):
                with p.open('ab') as f:
                    f.write(raw[i:i + 97])
                    f.flush()
                time.sleep(0.002)
        t = threading.Thread(target=w)
        t.start()
        m = F.wait_mapping(F.FramedProviderV2(), p, Deadline(10))
        t.join()
        assert m['ap']['bias'] == 0x7efab5b000
check('wait_partial_chunks_then_complete', test_wait_partial_then_complete)

def test_partial_tail_not_accepted():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'serial.log'
        p.write_bytes(VALID.encode()[:40])
        raises(TimeoutError, lambda: F.wait_mapping(F.FramedProviderV2(), p, Deadline(0.15)), 'no complete framed map')
check('partial_tail_held_not_accepted', test_partial_tail_not_accepted)

def test_complete_corrupt_immediate():
    bad = b'FX3MS2 BAD complete line\n'
    raises(F.Reject, lambda: F.FramedProviderV2().select(bad.decode()), 'unknown frame')
check('complete_malformed_rejected_immediately', test_complete_corrupt_immediate)

def test_collector_error_no_retry():
    err = ('FX3MS2 ERROR pid=239 starttime=777 seq=1 reason=short_read_more_data '
           'read_count=1 bytes=95 eintr_count=0 read_attempts=2 elapsed_ms=1\n')
    e = raises(F.CollectorError, lambda: F.FramedProviderV2().select(err), 'short_read_more_data')
    assert e.fields['reason'] == 'short_read_more_data'
check('collector_error_rejected_no_retry', test_collector_error_no_retry)

def test_no_appfw_retryable():
    raises(F.NoAppFwFrame, lambda: F.FramedProviderV2().select(NOAPP.read_text()), 'no appFw')
check('no_appfw_frame_retryable', test_no_appfw_retryable)

def _valid_seq(seq):
    payload = (CAND / 'fixtures/native-target-frame-v2.maps').read_bytes()
    return MF.make(payload, 239, 777, seq=seq, read_count=3, eintr=2).decode()

def test_later_valid_after_no_appfw():
    noapp = NOAPP.read_text()
    # No-appFw frame seq=1; a valid frame seq=2 with the same PID/starttime.
    text = noapp + _valid_seq(2)
    m = F.FramedProviderV2().select(text)
    assert m['frame_seq'] == 2 and m['frame_count'] == 2
check('wait_for_later_seq_not_prior_frame', test_later_valid_after_no_appfw)

def test_latest_frame_selected():
    valid2 = _valid_seq(2)
    m = F.FramedProviderV2().select(VALID + valid2)
    assert m['frame_seq'] == 2 and m['frame_count'] == 2
check('latest_valid_frame_selected', test_latest_frame_selected)

def test_duplicate_seq_rejected():
    raises(F.Reject, lambda: F.FramedProviderV2().select(VALID + VALID), 'duplicate/out-of-order')
check('duplicate_sequence_rejected', test_duplicate_seq_rejected)

def test_valid_then_corrupt_no_fallback():
    text = VALID + 'FX3MS2 BAD after valid\n'
    raises(F.Reject, lambda: F.FramedProviderV2().select(text), 'unknown frame')
check('valid_then_corrupt_no_fallback', test_valid_then_corrupt_no_fallback)

def test_valid_then_partial_tail_not_accepted():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'serial.log'
        p.write_bytes(VALID.encode() + b'FX3MS2 BEGIN pid=239 starttime=777 seq=2 cap=262144')
        raises(TimeoutError, lambda: F.wait_mapping(F.FramedProviderV2(), p, Deadline(0.15)), 'incomplete tail')
check('valid_frame_with_partial_tail_not_accepted', test_valid_then_partial_tail_not_accepted)

def test_unterminated_payload():
    text = VALID[:-1]
    d = text.encode()
    # Rebuild END bytes claim is still complete; the host parser cannot see the
    # final byte because the serial frontier is a partial tail.  Use decode on
    # a rebuilt frame with a payload that does not end in newline instead.
    payload = (CAND / 'fixtures/native-target-frame-v2.maps').read_bytes().rstrip(b'\n')
    bad = MF.make(payload, 239, 777, seq=3, read_count=3, eintr=0)
    raises(F.Reject, lambda: F.decode(bad.decode()), 'payload final byte not newline')
check('unterminated_maps_payload_rejected', test_unterminated_payload)

def test_flags_rejected():
    for old, new, why in (
        ('eof_observed=1', 'eof_observed=0', 'EOF not observed'),
        ('snapshot_atomic=0', 'snapshot_atomic=1', 'atomic snapshot'),
        ('cap_hit=0', 'cap_hit=1', 'cap_hit'),
        ('read_limit_hit=0', 'read_limit_hit=1', 'read_limit_hit'),
        ('time_limit_hit=0', 'time_limit_hit=1', 'time_limit_hit'),
        ('read_attempts=6', 'read_attempts=5', 'read attempt accounting'),
        ('identity_after=239:777', 'identity_after=239:778', 'identity_before/after'),
    ):
        bad = VALID.replace(old, new)
        raises(F.Reject, lambda b=bad: F.decode(b), why)
check('end_flags_and_identity_rejected', test_flags_rejected)

def test_digest_and_bytes_rejected():
    lines = VALID.splitlines()
    changed = False
    out = []
    for ln in lines:
        if not changed and ln.startswith('FX3MS2 DATA '):
            parts = ln.split()
            enc = parts[6]
            parts[6] = ('A' if enc[0] != 'A' else 'B') + enc[1:]
            out.append(' '.join(parts))
            changed = True
        else:
            out.append(ln)
    bad = '\n'.join(out) + '\n'
    raises(F.Reject, lambda: F.decode(bad), 'digest mismatch')
    bad2 = VALID.replace('bytes=10563', 'bytes=10562')
    raises(F.Reject, lambda: F.decode(bad2), 'length mismatch')
check('digest_and_length_rejected', test_digest_and_bytes_rejected)

def test_mapping_range_change_rejected():
    payload = (CAND / 'fixtures/native-target-frame-v2.maps').read_bytes()
    lines = payload.splitlines()
    out = []
    removed = False
    for ln in lines:
        if not removed and b'/usr/lib/appFw.so' in ln and b'r-xp' in ln:
            removed = True
            continue
        out.append(ln)
    bad_payload = b'\n'.join(out) + b'\n'
    bad = MF.make(bad_payload, 239, 777, seq=4, read_count=3, eintr=0)
    e = raises(F.Reject, lambda: F.FramedProviderV2().select(bad.decode()), 'map_bias')
    assert 'map_bias' in str(e)
check('mapping_range_change_rejected', test_mapping_range_change_rejected)

out = {'schema': 'fx6-map-collector-shortread-host-tests-v1',
       'status': 'PASS', 'tests': len(checks), 'cases': checks}
(CAND / 'receipts/host-tests.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
