"""One-shot, absolute-budget QMP greeting/capabilities startup handshake.

This is host startup only. It does not change guest 5000 ms, runtime key,
or cleanup ACK budgets, and it never resends a command after uncertainty.
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

from qmp_line_transport import QmpDeadline, QmpProtocolError


def is_proven_prelaunch(status_response) -> bool:
    status = status_response.get('return', {}) if isinstance(status_response, dict) else {}
    return status.get('status') == 'prelaunch' and status.get('running') is False


def startup_handshake(transport, qmp, guard, run: Path, journal: list, *,
                      budget_seconds: float = 15.0, clock=time.monotonic,
                      connect_elapsed_seconds: float | None = None):
    if not 0 < budget_seconds <= 15:
        raise ValueError('startup QMP budget must be at most 15 seconds')
    run = Path(run)
    begin = clock()
    deadline = begin + budget_seconds
    result = {'budget_seconds': budget_seconds,
              'connect_elapsed_seconds': connect_elapsed_seconds,
              'greeting_elapsed_seconds': None,
              'capabilities_elapsed_seconds': None,
              'capabilities_request_id': None,
              'capabilities_response_id': None,
              'matched_success': False}
    def remaining():
        left = deadline - clock()
        if left <= 0:
            raise QmpDeadline('startup QMP absolute 15-second deadline expired')
        return left
    try:
        stage = clock()
        greeting = transport.read_json(timeout=remaining())
        result['greeting_elapsed_seconds'] = clock() - stage
        if 'QMP' not in greeting:
            raise QmpProtocolError('QMP greeting missing QMP identity')
        journal.append({'greeting': greeting, 'elapsed_seconds': clock() - transport.started})
        guard.set_qmp(qmp)
        stage = clock()
        try:
            response = qmp('qmp_capabilities', timeout=remaining())
        finally:
            result['capabilities_elapsed_seconds'] = clock() - stage
            result['capabilities_request_id'] = transport.sequence
        result['capabilities_response_id'] = response.get('id')
        if 'error' in response or 'return' not in response:
            raise QmpProtocolError('qmp_capabilities returned error or no return: ' + repr(response))
        result['matched_success'] = True
        return greeting, response
    except Exception as exc:
        result['exception_type'] = type(exc).__name__
        result['exception'] = repr(exc)
        result['traceback'] = traceback.format_exc()
        raise
    finally:
        result['total_elapsed_seconds'] = clock() - begin
        result['buffered_bytes'] = len(transport.buffer)
        result['send_unknown'] = transport.send_unknown
        journal.append({'startup_qmp_handshake': dict(result)})
        try:
            (run / 'startup-qmp-timing.json').write_text(json.dumps(result, indent=2) + '\n')
        except Exception as exc:
            journal.append({'startup_qmp_timing_write_error': repr(exc)})
