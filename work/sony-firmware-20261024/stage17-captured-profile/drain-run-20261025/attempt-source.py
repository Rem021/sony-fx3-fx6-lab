#!/usr/bin/env python3
"""Guest-only evidence for draining marked packets before consumer removal."""
from pathlib import Path
import argparse
import json
import captured_profile as cp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cp.qp.verify_volume()
    out = Path(args.output).resolve()
    assert cp.STAGE in out.parents and not out.exists()
    out.mkdir()
    inputs = [Path(cp.__file__), Path(cp.pp.__file__), Path(cp.qp.__file__), cp.APP.path, cp.MPR.path]
    before = {str(p.relative_to(cp.ROOT)): cp.qp.sha(p) for p in inputs}
    im = cp.pp.Image(); rows = cp.model_copy_rows(im); marker = cp.capture_patch(im)
    query_patch, _ = cp.qp.new_patch(); setter_patch = cp.pp.trampolines(im)[1]
    active, marked = cp.copy_packet(im, rows, marker, {'frame': 0}, flag=1)
    inactive, regenerated = cp.copy_packet(im, rows, marker, {'frame': 0}, flag=0)
    live = cp.captured_query(marked, query_patch, future_flag=0)
    removed = cp.captured_query(marked, None)
    stock = cp.captured_query(regenerated, None)
    assert live['reason'] == stock['reason'] == 'conversion block complete'
    assert removed['reason'].startswith('firmware assertion entry reached')
    assert active['global_model_cells_unchanged'] and inactive['global_model_cells_unchanged']
    retained_setter = cp.tuple_setter(im, setter_patch, cp.a.TARGET, future_flag=0)
    removed_setter = cp.pp.setter(im, [], cp.a.TARGET)
    assert retained_setter['output_vpc_quality_frame'] == [6, 6, 3]
    assert removed_setter['reason'] == 'conversion block complete'
    assert removed_setter['output_vpc_quality_frame'] == [5, 6, 3]
    codecs = []
    for result in (retained_setter, removed_setter):
        vpc = result['output_vpc_quality_frame'][0]
        codec, _ = cp.pp.mpr_call(0xcd40c, 0xcd4f8, [vpc, 0], logging_adapter=True)
        assert codec['reason'] == 'returned'
        codecs.append({'VPC': vpc, 'main_stream': 0, 'actual_original_codec_helper': codec})
    assert codecs[0]['actual_original_codec_helper']['return_u32'] != codecs[1]['actual_original_codec_helper']['return_u32']
    assert before == {str(p.relative_to(cp.ROOT)): cp.qp.sha(p) for p in inputs}
    proof = {'status': 'PASS_GUEST_CONSUMER_REMOVAL_NEGATIVES_AND_REGENERATED_STOCK_CONTROL',
        'scope': 'Independent guest invocations representing consumer availability; no camera rollback, live uninstall or real queue draining',
        'inputs_unchanged': before, 'active_captured_packet': active, 'inactive_regenerated_packet': inactive,
        'marked_packet_with_consumer': live, 'marked_packet_without_consumer': removed,
        'regenerated_stock_packet_without_consumer': stock,
        'target_tuple_with_setter_consumer': retained_setter, 'target_tuple_without_setter_consumer': removed_setter,
        'main_codec_identity_controls': codecs,
        'findings': ['A marked local packet reaches the original query assertion if its interpreting consumer is removed, despite legal unchanged global model values.',
                     'A queued target builder tuple changes from VPC6toVPC5 when interpreted by the original setter; the original main codec helper also returns a different codec.',
                     'Regenerating an unmarked stock packet restores the bounded original query path; actual quiescence and restoration remain unverified.'],
        'required_but_unimplemented_restore_preconditions': [
            'Bind same-body healthy originals and actual code/data/WBI state.',
            'Stop new profile admission through the real configuration owner and recording-idle gate.',
            'Observe and drain/discard all in-flight marked packets, active target tuples and callers before removing dependent consumers.',
            'Regenerate legitimate stock snapshots and confirm current hardware/recording state can return to stock.',
            'Restore and read back original bytes through a proven scoped loader/restorer, then verify corresponding boot/WBI and recording behavior.'],
        'real_drain_observer_loader_restorer_or_recovery_entry_implemented': False,
        'camera_USB_native_execution_settings_WBI_or_firmware_write': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'marked_packet_without_consumer': removed['reason'],
        'regenerated_packet_stock_query': stock['reason'],
        'target_tuple_VPC_with_without_consumer': [6, 5],
        'main_codec_values_with_without_consumer': [r['actual_original_codec_helper']['return_u32'] for r in codecs],
        'real_restore_or_brick_recovery_verified': False, 'goal_complete': False}
    cp.qp.write_json(out / 'drain-results.json', proof)
    cp.qp.write_json(out / 'summary.json', summary)
    cp.qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(cp.ROOT)),
        'script_sha256': cp.qp.sha(Path(__file__)), 'results_sha256': cp.qp.sha(out / 'drain-results.json'),
        'summary_sha256': cp.qp.sha(out / 'summary.json'), 'inputs': before, 'volume_uuid': cp.qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
