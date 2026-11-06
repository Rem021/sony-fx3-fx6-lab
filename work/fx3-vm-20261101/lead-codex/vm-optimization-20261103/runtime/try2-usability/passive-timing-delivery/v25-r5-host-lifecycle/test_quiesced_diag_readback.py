import json
import struct
import tempfile
from pathlib import Path

from parse_v25_diag_r3 import HEADER, MAGIC, CAPACITY, STRIDE
from quiesced_diag_readback import SIZE, capture, capture_optional_vcpus


def ring_bytes():
    data = bytearray(SIZE)
    struct.pack_into('<6Q', data, HEADER, MAGIC, 2, 1, CAPACITY, STRIDE, 0)
    struct.pack_into('<12Q', data, 0x2040, 1, 100, 900, 5, 5738, 5532, 0x2886049,
                     5000, 0, 1, 0x402, 0)
    return data


def qmp_fixture(run, *, hmp='valid', cpu_error=False, cpu_exception=False):
    calls = []
    def qmp(cmd, arguments=None, *, timeout=None):
        calls.append((cmd, arguments))
        if cmd == 'query-status':
            return {'return': {'running': False, 'status': 'paused'}}
        if cmd == 'query-cpus-fast':
            if cpu_exception:
                raise OSError('optional QMP unavailable')
            if cpu_error:
                return {'error': {'class': 'CommandNotFound', 'desc': 'not available'}}
            return {'return': [{'cpu-index': i, 'thread-id': 100 + i} for i in range(4)]}
        if cmd == 'human-monitor-command' and arguments['command-line'].startswith('pmemsave '):
            (run / 'osd-ring-final.bin').write_bytes(ring_bytes())
            return {'return': ''}
        if cmd == 'human-monitor-command':
            if hmp == 'error_response':
                return {'error': {'class': 'GenericError', 'desc': 'bad option'}}
            if hmp == 'error_text':
                return {'return': 'unknown command: info registers -a'}
            return {'return': '\n'.join(f'CPU#{i} PC=ffffff800812345{i}' for i in range(4))}
        return {'return': {}}
    return qmp, calls


def main():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp)
        qmp, calls = qmp_fixture(run)
        receipt = capture(qmp, run)
        assert receipt['consistent'] and receipt['bytes'] == SIZE
        assert [x[0] for x in calls] == ['stop', 'query-status', 'human-monitor-command']
        assert json.loads((run / 'osd-ring-final-diag.json').read_text())['readback_quiesced']
        assert capture_optional_vcpus(qmp, run)['complete'] is True
        assert [x[0] for x in calls][-3:] == ['query-status', 'query-cpus-fast', 'human-monitor-command']
        assert (run / 'fault-vcpu-paused.json').exists()
        assert capture_optional_vcpus(qmp, run)['complete'] is False  # no overwrite
        try:
            capture(qmp, run)
        except FileExistsError:
            pass
        else:
            raise AssertionError('existing final readback overwritten')
    for kwargs in ({'hmp': 'error_response'}, {'hmp': 'error_text'},
                   {'cpu_error': True}, {'cpu_exception': True}):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            qmp, calls = qmp_fixture(run, **kwargs)
            assert capture(qmp, run)['consistent']
            before = (run / 'osd-ring-final.bin').read_bytes()
            optional = capture_optional_vcpus(qmp, run)
            assert optional['complete'] is False and optional['errors']
            assert (run / 'osd-ring-final.bin').read_bytes() == before
            assert (run / 'osd-ring-final-readback-receipt.json').exists()
            assert qmp('cont') == {'return': {}}
    with tempfile.TemporaryDirectory() as tmp:
        def bad(cmd, arguments=None):
            return {'return': {'running': True, 'status': 'running'}} if cmd == 'query-status' else {'return': {}}
        try:
            capture(bad, Path(tmp))
        except RuntimeError as exc:
            assert 'not provably paused' in str(exc)
        else:
            raise AssertionError('live memory accepted')
        assert not (Path(tmp) / 'osd-ring-final.bin').exists()
    print('quiesced readback: core first; QMP error/text/exception optional; cleanup continues PASS')


if __name__ == '__main__':
    main()
