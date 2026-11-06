import json
import struct
import tempfile
from pathlib import Path

from procdiag_readback import ADDRESS, MAGIC, SIZE, SLOT_BYTES, SLOTS, capture, fnv, parse


def sample():
    raw = bytearray(SIZE)
    body = b'PCDIAG_BEGIN guest_monotonic_ns=100\nTARGET role=key96 pid=343 tid=344\nFILE_END role=key96 kind=stack status=ok\n'
    struct.pack_into('<QQII', raw, 0x9000, MAGIC, 2, 1, 0)
    offset = SLOTS[0]
    struct.pack_into('<QIII4xQQ', raw, offset, 4, len(body), 16, 15, 100, fnv(body))
    raw[offset + 40:offset + 40 + len(body)] = body
    struct.pack_into('<Q', raw, offset + SLOT_BYTES - 8, 4)
    return raw


def main():
    assert parse(bytes(SIZE))['reason'] == 'diagnostic_not_loaded_or_no_capture'
    raw = sample()
    result = parse(raw)
    assert result['available'] and result['latest_sequence'] == 2
    assert result['slots'][0]['step'] == 16 and 'pid=343' in result['slots'][0]['text']
    raw[SLOTS[0] + SLOT_BYTES - 8] ^= 1
    assert parse(raw)['reason'] == 'missing_or_torn_latest_slot'
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp)
        calls = []
        def qmp(cmd, args=None, *, timeout=None):
            calls.append(cmd)
            if cmd == 'query-status':
                return {'return': {'running': False, 'status': 'paused'}}
            if cmd == 'human-monitor-command':
                assert args['command-line'].startswith(f'pmemsave {ADDRESS:#x} {SIZE:#x}')
                (run / 'procdiag-final-key93.bin').write_bytes(sample())
                return {'return': ''}
            raise AssertionError(cmd)
        receipt = capture(qmp, run)
        assert receipt['available'] and receipt['consistent_memory']
        assert calls == ['query-status', 'human-monitor-command']
        assert json.loads((run / 'procdiag-final-readback.json').read_text())['available']
        assert capture(qmp, run)['reason'] == 'existing_artifact_not_overwritten'
    for mode in ('error', 'exception', 'running'):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            def qmp(cmd, args=None, *, timeout=None):
                if mode == 'exception': raise TimeoutError('optional QMP timeout')
                if mode == 'running': return {'return': {'running': True, 'status': 'running'}}
                return {'return': {'running': False, 'status': 'paused'}} if cmd == 'query-status' else {'error': {'desc': 'failed'}}
            record = capture(qmp, run)
            assert not record['available']
            assert (run / 'procdiag-final-readback.json').exists()
    print('procdiag paused parser/readback/optional failures PASS')


if __name__ == '__main__':
    main()
