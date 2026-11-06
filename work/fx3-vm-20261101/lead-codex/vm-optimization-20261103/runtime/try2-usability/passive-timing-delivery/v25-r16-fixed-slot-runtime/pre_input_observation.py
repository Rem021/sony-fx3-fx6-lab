"""One selected host-only read in an already-stopped input window; no guest writes."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from osd_ring93_v4 import BASE as OSD_RING_BASE

# RingReader.poll() reads exactly 0x100 bytes at BASE before any full-ring read.
OSD_HEADER_BYTES = 0x100
UI_GATE_ADDRESS = 0x41dc00000
UI_GATE_BYTES = 0x10000
OSD_RESERVATION_BYTES = 0x1000000


class PreInputSnapshotError(RuntimeError):
    pass


class _Cancelled(Exception):
    pass


def capture(qmp, transport, run: Path, snapshots: list, stop_response: dict,
            step: int, stop_event, *, budget: float = 2.0, clock=time.monotonic) -> dict:
    """Fail closed before InputGate.command; preserve raw bytes and a receipt.

    QMP uses one shared transport and a common absolute clock deadline. The
    filesystem read/write calls are checked around each operation, not forcibly
    interrupted by this deadline.
    """
    if type(step) is not int or step < 1 or not 0 < budget <= 2.0:
        raise ValueError('invalid selected pre-input step or budget')
    started = clock()
    deadline = started + budget
    run = Path(run)
    prefix = f'pre-input-step-{step:04d}'
    receipt_path = run / f'{prefix}-receipt.json'
    ui_path = run / f'{prefix}-ui-gate.bin'
    osd_path = run / f'{prefix}-osd-header.bin'
    if any(p.exists() or p.is_symlink() for p in (receipt_path, ui_path, osd_path)):
        raise PreInputSnapshotError('selected pre-input evidence path already exists')
    receipt = {'step': step, 'status': 'started', 'read_only': True,
               'host_monotonic_start': started, 'budget_seconds': budget,
               'existing_input_stop_response': stop_response, 'items': [],
               'no_guest_key_written_by_capture': True}
    failure = None

    def check():
        if stop_event.is_set():
            raise _Cancelled('End or signal arrived during pre-input observation')
        if transport is None or transport.send_unknown:
            raise PreInputSnapshotError('QMP transport send_unknown')
        if deadline - clock() <= 0:
            raise PreInputSnapshotError('pre-input absolute budget expired')

    def ask(name, arguments=None):
        check()
        # The shared transport has a 3-second default; this explicit timeout
        # only shrinks it to the remaining two-second absolute budget.
        remaining = deadline - clock()
        return qmp(name, arguments, timeout=min(remaining, 3.0))

    try:
        if not isinstance(stop_response, dict) or 'error' in stop_response or 'return' not in stop_response:
            raise PreInputSnapshotError('existing input QMP stop was not acknowledged')
        ui = [s for s in snapshots if s.get('name') == 'ui-gate-counters.bin']
        osd = [s for s in snapshots if s.get('name') == 'osd-ring-final.bin']
        if (len(ui) != 1 or ui[0].get('address') != UI_GATE_ADDRESS or ui[0].get('size') != UI_GATE_BYTES
                or len(osd) != 1 or osd[0].get('address') != OSD_RING_BASE
                or osd[0].get('size') != OSD_RESERVATION_BYTES):
            raise PreInputSnapshotError('FDT-declared UI/OSD read-only reservation identity mismatch')
        status = ask('query-status')
        receipt['query_status_response'] = status
        check()
        state = status.get('return') if isinstance(status, dict) and 'error' not in status else None
        if not isinstance(state, dict) or state.get('running') is not False or state.get('status') != 'paused':
            raise PreInputSnapshotError('QMP paused state not proven')
        receipt['paused_proven'] = True
        for name, address, size, path in (
                ('ui-gate-counters', UI_GATE_ADDRESS, UI_GATE_BYTES, ui_path),
                ('osd-ring-header', OSD_RING_BASE, OSD_HEADER_BYTES, osd_path)):
            check()
            if path.exists() or path.is_symlink():
                raise PreInputSnapshotError('selected raw evidence path already exists: ' + str(path))
            item = {'name': name, 'address': hex(address), 'expected_bytes': size,
                    'path': str(path), 'host_monotonic_start': clock()}
            receipt['items'].append(item)
            response = ask('human-monitor-command', {'command-line':
                           f'pmemsave {address:#x} {size:#x} "{path}"'})
            item['qmp_response'] = response
            check()
            if not isinstance(response, dict) or 'error' in response or 'return' not in response:
                raise PreInputSnapshotError('QMP pmemsave failed: ' + repr(response))
            check()
            if not path.is_file() or path.is_symlink():
                raise PreInputSnapshotError('QMP pmemsave raw file missing or not regular: ' + str(path))
            raw = path.read_bytes()
            item['bytes'] = len(raw)
            item['sha256'] = hashlib.sha256(raw).hexdigest()
            item['host_monotonic_end'] = clock()
            if len(raw) != size:
                raise PreInputSnapshotError('QMP pmemsave raw length mismatch: ' + name)
            check()
        receipt['status'] = 'complete'
    except _Cancelled as exc:
        receipt['status'] = 'cancelled_no_guest_write'
        receipt['reason'] = str(exc)
    except BaseException as exc:
        receipt['status'] = 'failed_no_guest_write'
        receipt['error'] = repr(exc)
        failure = exc
    finally:
        receipt['host_monotonic_end'] = clock()
        receipt['elapsed_seconds'] = receipt['host_monotonic_end'] - started
        receipt['transport_send_unknown_at_end'] = bool(transport and transport.send_unknown)
        if receipt['elapsed_seconds'] > budget and receipt['status'] == 'complete':
            receipt['status'] = 'failed_no_guest_write'
            receipt['error'] = 'pre-input absolute budget exceeded during host filesystem work'
            failure = PreInputSnapshotError(receipt['error'])
        try:
            # A saved receipt cannot attest to its own persistence latency.
            # Keep that boundary visibly provisional; the runner's journal
            # gets the final status only after the post-write gate below.
            saved_receipt = dict(receipt)
            if saved_receipt['status'] == 'complete':
                saved_receipt['status'] = 'pending_postwrite_gate_no_guest_write'
            with receipt_path.open('x') as out:
                json.dump(saved_receipt, out, indent=2)
                out.write('\n')
        except Exception as exc:
            raise PreInputSnapshotError('pre-input receipt write failed: ' + repr(exc)) from exc
    if failure is not None:
        raise PreInputSnapshotError('pre-input observation failed: ' + repr(failure)) from failure
    # This is the last check before the caller may advance host_step/write a key.
    # No filesystem call can be hard-interrupted; a late receipt write fails
    # closed instead of returning a false "complete".
    if stop_event.is_set():
        receipt['status'] = 'cancelled_no_guest_write'
        receipt['reason'] = 'End or signal arrived during receipt persistence'
        return receipt
    if transport is None or transport.send_unknown:
        raise PreInputSnapshotError('QMP transport send_unknown after receipt persistence')
    receipt['postwrite_monotonic'] = clock()
    if receipt['postwrite_monotonic'] > deadline:
        raise PreInputSnapshotError('pre-input absolute budget exceeded during receipt persistence')
    receipt['postwrite_gate_passed'] = True
    return receipt
