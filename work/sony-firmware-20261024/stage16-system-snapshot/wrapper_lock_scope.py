#!/usr/bin/env python3
"""Static scope of the identified wrapper bookkeeping mutex, no execution."""
from pathlib import Path
import json
import system_snapshot as ss


def main():
    ss.qp.verify_volume()
    im = ss.StaticImage()
    regions = [('status_wrapper', 0x2dda7d4, 0x2dda814),
               ('remain_wrapper', 0x2dda854, 0x2dda894),
               ('enter_bookkeeping', 0x2f6ea24, 0x2f6eae8),
               ('exit_bookkeeping', 0x2f6eae8, 0x2f6eba8),
               ('lock_helper', 0x16ed554, 0x16ed580),
               ('unlock_helper', 0x273879c, 0x27387b4)]
    assert ss.APP.plt[0x15941f0] == 'pthread_mutex_lock'
    assert ss.APP.plt[0x1594030] == 'pthread_mutex_unlock'
    expected = {0x2dda7f0: 'bl #0x2f6ea24', 0x2dda7fc: 'bl #0x2e69ef0',
                0x2dda810: 'b #0x2f6eae8', 0x2dda870: 'bl #0x2f6ea24',
                0x2dda87c: 'bl #0x2e6a59c', 0x2dda890: 'b #0x2f6eae8',
                0x2f6eab0: 'bl #0x16ed554', 0x2f6ead4: 'bl #0x273879c',
                0x2f6eb6c: 'bl #0x16ed554', 0x2f6eb94: 'bl #0x273879c'}
    for pc, text in expected.items(): assert im.dump(pc, pc + 4)[0]['asm'] == text
    proof = {'status': 'PASS_STATIC_IDENTIFIED_MUTEX_SCOPE',
             'source_app_sha256': ss.qp.sha(ss.APP.path),
             'scope': 'Static normal-path ordering of the specific identified bookkeeping mutex; no whole-program locking or runtime claim',
             'regions': [{'name': name, 'start': hex(a), 'end': hex(z), 'instructions': im.dump(a, z)}
                         for name, a, z in regions],
             'PLT_bindings': {'0x15941f0': 'pthread_mutex_lock', '0x1594030': 'pthread_mutex_unlock'},
             'ordering': ['Enter bookkeeping may lock/update/unlock its record before returning.',
                          'Status/remain implementation is invoked after enter bookkeeping returns.',
                          'Exit bookkeeping may take and release the mutex again.'],
             'conclusion': 'This mutex is not held across the status/remain call by these wrapper paths. It cannot serve as the unproven configuration-snapshot owner.',
             'other_locks_owners_threads_or_error_paths_fully_audited': False,
             'guest_or_native_mutex_execution': False, 'camera_operations': False, 'goal_complete': False}
    path = ss.STAGE / 'wrapper-lock-scope.json'
    ss.qp.write_json(path, proof)
    ss.qp.write_json(ss.STAGE / 'wrapper-lock-source-receipt.json',
                    {'script': str(Path(__file__).relative_to(ss.ROOT)),
                     'script_sha256': ss.qp.sha(Path(__file__)), 'result_sha256': ss.qp.sha(path),
                     'inputs': {str(ss.APP.path.relative_to(ss.ROOT)): ss.qp.sha(ss.APP.path),
                                str(Path(ss.__file__).relative_to(ss.ROOT)): ss.qp.sha(Path(ss.__file__))},
                     'volume_uuid': ss.qp.EXPECTED_VOLUME})
    print(json.dumps({'status': proof['status'], 'mutex_held_across_status_or_remain': False}))


if __name__ == '__main__': main()
