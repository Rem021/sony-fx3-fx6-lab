"""One FX3 host first-exception record and its existing qmp.json journal.

No directory creation, fallback destination, retries, or resource operations.
The runner's single host control thread owns the journal.
"""
import datetime
import json
import sys
import time
import traceback


def _write_failed(status, exc):
    status.update(status='failed', error_type=type(exc).__name__, error=repr(exc))
    # Console delivery is best effort too; it must not replace the first error.
    try:
        print('Host exception persistence failed:', status['path'], repr(exc),
              file=sys.stderr, flush=True)
    except Exception:
        pass


def write_host_first_exception(run, journal, exc, transport=None):
    """Capture once per journal; return the same original record on later calls.

    The exception fields never acquire persistence errors. Status lives beside
    the record in memory, including when the first-exception file write succeeds.
    """
    for entry in journal:
        if 'host_first_exception' in entry:
            return entry['host_first_exception']
    host_monotonic = time.monotonic()
    host_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {'type': type(exc).__name__, 'error': repr(exc),
              'traceback': ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
              'host_utc': host_utc, 'host_monotonic': host_monotonic,
              'qmp_send_unknown': bool(transport.send_unknown) if transport is not None else None,
              'qmp_buffered_bytes': len(transport.buffer) if transport is not None else None}
    path = run / 'host-first-exception.json'
    status = {'path': str(path), 'status': 'pending', 'write_completed': False,
              'durability': 'not_verified'}
    journal.append({'host_first_exception': record,
                    'host_first_exception_persistence': status})
    try:
        path.write_text(json.dumps(record, indent=2) + '\n')
    except Exception as write_exc:
        _write_failed(status, write_exc)
    else:
        status.update(status='write_completed', write_completed=True)
    return record


def write_host_journal(run, journal):
    """Write only the runner's existing qmp.json; preserve its raising behavior.

    Its own write outcome is appended in memory AFTER the attempt, so the file
    does not purport to attest to completion of the write that produced it.
    """
    path = run / 'qmp.json'
    status = {'path': str(path), 'status': 'pending', 'write_completed': False,
              'durability': 'not_verified'}
    try:
        path.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
    except Exception as write_exc:
        # If this is the first host error, capture it from this exception object.
        # If an earlier error exists, this does not retry or rewrite its file.
        write_host_first_exception(run, journal, write_exc)
        _write_failed(status, write_exc)
        journal.append({'host_journal_persistence': status})
        raise
    else:
        status.update(status='write_completed', write_completed=True)
        journal.append({'host_journal_persistence': status})
    return status
