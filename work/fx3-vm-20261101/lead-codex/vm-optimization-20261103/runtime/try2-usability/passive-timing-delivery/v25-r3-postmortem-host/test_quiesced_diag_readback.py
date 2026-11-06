import json
import struct
import tempfile
from pathlib import Path

from parse_v25_diag_r3 import HEADER, MAGIC, CAPACITY, STRIDE
from quiesced_diag_readback import SIZE, capture


def ring_bytes():
    data = bytearray(SIZE)
    struct.pack_into('<6Q', data, HEADER, MAGIC, 2, 1, CAPACITY, STRIDE, 0)
    struct.pack_into('<12Q', data, 0x2040, 1, 100, 900, 5, 5738, 5532, 0x2886049,
                     5000, 0, 1, 0x402, 0)
    return data


def main():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp)
        commands = []
        def qmp(cmd, arguments=None):
            commands.append((cmd, arguments))
            if cmd == 'query-status':
                return {'return': {'running': False, 'status': 'paused'}}
            if cmd == 'query-cpus-fast':
                return {'return': [{'cpu-index': 0, 'thread-id': 123}]}
            if cmd == 'human-monitor-command' and arguments['command-line'] == 'info registers -a':
                return {'return': 'CPU#0 PC=0x400000'}
            if cmd == 'human-monitor-command' and arguments['command-line'].startswith('pmemsave '):
                (run / 'osd-ring-final.bin').write_bytes(ring_bytes())
            return {'return': {}}
        receipt = capture(qmp, run, capture_cpus=True)
        assert receipt['consistent'] and receipt['bytes'] == SIZE
        assert [x[0] for x in commands] == ['stop', 'query-status', 'query-cpus-fast',
                                           'human-monitor-command', 'human-monitor-command']
        assert commands[3][1]['command-line'] == 'info registers -a'
        assert receipt['fault_vcpu_snapshot'].endswith('fault-vcpu-paused.json')
        assert receipt['fault_vcpu_snapshot_complete'] is True
        assert json.loads((run / 'fault-vcpu-paused.json').read_text())['guest_tid_mapping'] == 'unknown'
        assert json.loads((run / 'osd-ring-final-diag.json').read_text())['readback_quiesced']
        try:
            capture(qmp, run)
        except FileExistsError:
            pass
        else:
            raise AssertionError('existing final readback overwritten')
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
    print('quiesced readback: stop/status/size/parse/no-overwrite/live-reject PASS')


if __name__ == '__main__':
    main()
