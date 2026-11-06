"""Bounded read-only optional captures after a complete paused ring readback."""
import hashlib
import time


def capture(qmp, transport, run, snapshots, *, budget=10.0, clock=time.monotonic):
    if not 0 < budget <= 15:
        raise ValueError('optional snapshot budget must be 0..15 seconds')
    deadline = clock() + budget
    result = {'attempted': False, 'paused_reproved': False, 'budget_seconds': budget,
              'items': [], 'errors': []}
    if transport is None or transport.send_unknown:
        result['errors'].append('transport_send_unknown')
        return result

    def ask(command, arguments=None):
        if transport.send_unknown:
            raise RuntimeError('transport_send_unknown')
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError('optional_absolute_budget_expired')
        return qmp(command, arguments, timeout=remaining)

    def file_hash(path, expected):
        digest = hashlib.sha256()
        size = 0
        with path.open('rb') as stream:
            while True:
                if deadline - clock() <= 0:
                    raise TimeoutError('optional_hash_budget_expired')
                chunk = stream.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > expected:
                    raise RuntimeError('optional pmemsave grew beyond declared length')
                digest.update(chunk)
        if size != expected:
            raise RuntimeError('optional pmemsave changed length during hash')
        return digest.hexdigest()

    try:
        status = ask('query-status')
        state = status.get('return') if isinstance(status, dict) else None
        result['query_status'] = status
        if not isinstance(state, dict) or state.get('running') is not False or state.get('status') != 'paused':
            result['errors'].append('not_provably_paused')
            return result
        result['paused_reproved'] = True
    except Exception as exc:
        result['errors'].append('pause_recheck:' + repr(exc))
        return result

    # Small UI gate first; never reread the 16 MiB OSD ring.
    ordered = sorted((s for s in snapshots if s['name'] != 'osd-ring-final.bin'),
                     key=lambda s: (s['name'] != 'ui-gate-counters.bin', s['name']))
    for item in ordered:
        name = item['name']
        entry = {'name': name, 'address': item['address'], 'expected_bytes': item['size']}
        result['items'].append(entry)
        if transport.send_unknown:
            entry['status'] = 'not_attempted_transport_unknown'
            break
        if deadline - clock() <= 0:
            entry['status'] = 'not_attempted_budget_exhausted'
            break
        path = run / name
        if path.exists():
            entry['status'] = 'not_attempted_existing_path'
            continue
        result['attempted'] = True
        try:
            response = ask('human-monitor-command', {'command-line':
                           f'pmemsave {item["address"]:#x} {item["size"]:#x} "{path}"'})
            if not isinstance(response, dict) or 'error' in response or 'return' not in response:
                raise RuntimeError('QMP pmemsave error: ' + repr(response))
            if not path.is_file() or path.stat().st_size != item['size']:
                raise RuntimeError('optional pmemsave missing or wrong length')
            entry['sha256'] = file_hash(path, item['size'])
            entry['bytes'] = item['size']
            entry['status'] = 'complete'
        except Exception as exc:
            entry['status'] = 'failed'
            entry['error'] = repr(exc)
            if transport.send_unknown:
                result['errors'].append('transport_send_unknown_after_optional_failure')
                break
    return result
