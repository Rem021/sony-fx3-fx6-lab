#!/usr/bin/env python3
"""Expose configuration-snapshot boundaries; no thread or camera simulation."""
from pathlib import Path
import argparse
import itertools
import json
import private_activation as a


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    a.qp.verify_volume()
    output = Path(args.output).resolve()
    assert a.STAGE in output.parents and not output.exists()
    output.mkdir()
    inputs = [Path(a.__file__), Path(a.pp.__file__), Path(a.qp.__file__), a.APP.path, a.MPR.path]
    before = {str(p.relative_to(a.ROOT)): a.qp.sha(p) for p in inputs}
    im = a.pp.Image(); ps = a.patches(im)
    flag_cases = [a.chain(im, ps, {'frame': 0}, flags) for flags in itertools.product((0, 1), repeat=3)]
    for row in flag_cases:
        flags = row['flag_snapshots_builder_setter_query']
        assert row['builder']['reason'] == row['query']['reason'] == 'returned'
        assert row['setter']['reason'] == 'conversion block complete'
        # This is a measured consistency table, not a guard that repairs it.
        row['interpretation'] = ('same_tuple_for_this_fixture' if row['setter_query_equal']
                                 else 'different_tuple_for_this_fixture')
        if len(set(flags)) == 1: assert row['setter_query_equal']
    first_builder = a.builder(im, ps, frame=0, exposure=5, flag=1)
    first_setter = a.setter(im, ps, first_builder['builder_tuple'], flag=1)
    contexts = []
    for mode in range(17):
        later = a.query(ps, frame=0, mode=mode, flag=1)
        if later['reason'] != 'returned':
            category = 'later_query_fixture_dependencies_unclosed'
        elif later['output_vpc_quality_frame'] == first_setter['output_vpc_quality_frame']:
            category = 'same_tuple_for_independent_input_snapshots'
        else:
            category = 'constant_flag_but_mode_snapshot_mismatch'
        contexts.append({'earlier_builder_mode': 5, 'later_query_mode': mode,
                         'constant_private_flag': 1, 'category': category, 'query': later})
    assert [r['later_query_mode'] for r in contexts if r['category'] ==
            'constant_flag_but_mode_snapshot_mismatch'] == list(range(5))
    assert before == {str(p.relative_to(a.ROOT)): a.qp.sha(p) for p in inputs}
    proof = {'status': 'PASS_NEGATIVE_SNAPSHOT_BOUNDARY_AUDIT',
             'scope': 'Independent function invocations with deliberately differing synthetic input snapshots; no actual scheduling or transition executed',
             'inputs_unchanged': before, 'all_binary_flag_snapshots': flag_cases,
             'earlier_builder': first_builder, 'earlier_setter': first_setter,
             'later_independent_query_contexts': contexts,
             'derived_requirement': 'A future activation owner must bind profile flag AND eligible mode/format/system inputs over parameter generation, conversion and querying. Atomic access to the flag alone is insufficient.',
             'remaining_requirements': [
                 'Locate actual caller ownership, threads, change notifications, configuration epochs and record-idle transition boundaries.',
                 'Determine NTSC/PAL model semantics and enforce the 30000/1001 target only in a verified eligible context; this harness has not done so.',
                 'Define complete UI/metadata/display behavior and stock disable behavior, then implement and verify them.',
                 'Determine private-state allocation/lifetime, WBI and save/load behavior; emulator reinitialization proves none of those.',
                 'Verify full hardware capture and corresponding same-body restoration, without inducing a brick.'],
             'activation_owner_or_synchronization_implemented': False,
             'firmware_payload_camera_operation_or_recovery_claim': False,
             'goal_complete': False}
    summary = {'status': proof['status'], 'binary_flag_snapshots': len(flag_cases),
               'flag_snapshot_mismatches': sum(not x['setter_query_equal'] for x in flag_cases),
               'constant_flag_but_mode_snapshot_mismatches': list(range(5)),
               'actual_concurrency_or_mode_transitions_executed': False, 'goal_complete': False}
    a.qp.write_json(output / 'snapshot-results.json', proof)
    a.qp.write_json(output / 'summary.json', summary)
    a.qp.write_json(output / 'source-receipt.json', {'script': str(Path(__file__).relative_to(a.ROOT)),
        'script_sha256': a.qp.sha(Path(__file__)), 'results_sha256': a.qp.sha(output / 'snapshot-results.json'),
        'summary_sha256': a.qp.sha(output / 'summary.json'), 'inputs': before,
        'volume_uuid': a.qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
