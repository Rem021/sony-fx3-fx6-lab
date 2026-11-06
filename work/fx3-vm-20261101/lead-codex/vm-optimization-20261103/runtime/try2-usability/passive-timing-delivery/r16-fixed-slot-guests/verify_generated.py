#!/usr/bin/env python3
"""Sequential final artifact/hash and manifest verification; no writes to inputs."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).absolute().parent
DEL=HERE.parent
TOOL=DEL/'r15-fixed-layout-packaging/fixed_layout.py'
TOOL_SHA='b5b9bf75763b193575a007074e6701d1a1541ba9d3658ae32a164fc350eca8bc'
assert hashlib.sha256(TOOL.read_bytes()).hexdigest()==TOOL_SHA
spec=importlib.util.spec_from_file_location('fixed_layout_frozen',TOOL)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def main():
    m.volume_check()
    pre=json.loads(m.read_file(HERE/'PREFLIGHT.json'))
    base=json.loads(m.read_file(m.BASE/'candidate.json'))
    assert m.sha_file(m.BASE/'candidate.json')==m.PINS['candidate_sha256']
    dtb_sha=m.sha_file(m.BASE/'guest.dtb')
    assert dtb_sha==m.PINS['dtb_sha256']
    # One final independent full source hash after both writes; no concurrent IO.
    source_sha=m.sha_file(m.BASE/'guest.cpio')
    assert source_sha==m.PINS['archive_sha256']
    with m.open_read(m.BASE/'guest.cpio') as src:
        source_index=m.index_archive(src)
    outputs={}
    for variant in ('N1','N64'):
        folder=HERE/f'guest-{variant}'
        complete=json.loads(m.read_file(folder/'COMPLETE.json'))
        plan=json.loads(m.read_file(HERE/f'plans-{variant}/plan.json'))
        assert complete['state']=='complete' and complete['outside_slot_every_byte_equal'] and complete['archive_index_equal']
        assert complete['complete_source_sha256']==source_sha
        assert not (folder/'FAILED.json').exists()
        target=folder/'guest.cpio'
        # Independent full output digest, strictly N1 then N64.
        output_sha=m.sha_file(target)
        assert output_sha==complete['archive_sha256']
        assert target.stat().st_size==m.PINS['archive_size']==complete['archive_bytes']
        helper=m.read_file(plan['inputs']['stripped_helper'])
        with m.open_read(target) as out:
            out_index=m.index_archive(out)
            assert out_index==source_index
            out.seek(m.PINS['payload_offset'])
            slot=out.read(m.PINS['slot_size'])
        assert slot==helper+bytes(m.PINS['slot_size']-len(helper))
        assert m.digest(slot)==complete['padded_slot_sha256']
        candidate=json.loads(m.read_file(folder/'candidate.json'))
        assert candidate['initrd']==dict(path=str(target),sha256=output_sha)
        changed=sorted(k for k in set(base)|set(candidate) if base.get(k)!=candidate.get(k))
        assert changed==['fixed_layout_diagnostic_contract','initrd']
        assert candidate['dtb']==base['dtb']
        assert {k:v for k,v in candidate.items() if k not in ('initrd','fixed_layout_diagnostic_contract')}=={k:v for k,v in base.items() if k!='initrd'}
        assert candidate['fixed_layout_diagnostic_contract']['runtime_validated'] is False
        assert candidate['fixed_layout_diagnostic_contract']['release']['helper_version']=='r15'
        assert candidate['fixed_layout_diagnostic_contract']['release']['diagnostic_contract']['snapshot_is_end_state'] is False
        outputs[variant]=dict(candidate_path=str(folder/'candidate.json'),candidate_sha256=m.sha_file(folder/'candidate.json'),
            cpio_path=str(target),cpio_sha256=output_sha,cpio_bytes=target.stat().st_size,
            helper_path=plan['inputs']['stripped_helper'],helper_sha256=m.digest(helper),helper_bytes=len(helper),
            original_debug_helper_sha256=plan['raw_helper_sha256'],padded_slot_sha256=m.digest(slot),
            zero_padding_bytes=plan['zero_padding_bytes'],allowed_change=plan['allowed_change'],
            static_generation_complete=True,outside_slot_every_byte_equal_proven_by_write=True,
            independent_output_hash_matched=True,independent_full_index_matched=True,independent_slot_bytes_matched=True,
            candidate_changed_top_level_fields=changed,other_candidate_fields_equal=True,original_dtb_reference_equal=True,
            complete_receipt_sha256=m.sha_file(folder/'COMPLETE.json'),
            historical_incomplete_marker_superseded_by_COMPLETE=True,runtime_validated=False)
    # Recheck small frozen artifacts and all original r15 sources/deliveries.
    final_inputs=[]
    for row in pre['source_rows']+pre['delivery_rows']:
        assert m.sha_file(row['path'])==row['sha256'],row['path']
    for name,row in pre['prior_inputs'].items():
        assert m.sha_file(row['path'])==row['sha256'],name
        final_inputs.append(dict(name=name,**row))
    for name,h in pre['r15_pins'].items():
        assert m.sha_file(DEL/'v25-r15-snapshot-tail'/name)==h
    assert m.sha_file(TOOL)==TOOL_SHA
    assert m.sha_file(TOOL.parent/'SHA256SUMS')==pre['tool_delivery_manifest_sha256']
    text_path=DEL/'r16-r15-guest-SOURCE-SHA256SUMS'
    assert m.sha_file(text_path)==pre['adapted_source_manifest_sha256']
    binding=json.loads(m.read_file(HERE/'SOURCE-ADAPTATION.json'))
    freeze=json.loads(m.read_file(binding['original_json']['path']))
    expected=''.join(h+'  v25-r15-snapshot-tail/'+n+'\n' for n,h in freeze['files'].items())
    assert m.read_file(text_path).decode()==expected
    report=dict(schema='fx3-fixed-slot-guests-final-verification/v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        volume_uuid=m.UUID,tool_sha256=TOOL_SHA,original_source_cpio_sha256=source_sha,
        original_candidate_sha256=m.sha_file(m.BASE/'candidate.json'),original_dtb_path=base['dtb']['path'],original_dtb_sha256=dtb_sha,
        source_manifest_adaptation_sha256=m.sha_file(text_path),source_manifest_exact_JSON_mapping=True,
        frozen_r15_sources_checked=31,frozen_r15_delivery_files_checked=54,prior_inputs_checked=final_inputs,
        original_debug_ELFs_and_frozen_inputs_unchanged=True,
        source_member_count=len(source_index)-1,trailer_end=source_index[-1]['next_offset'],
        outputs=outputs,write_order=['N1','N64'],verification_large_file_order=['source','N1','N64'],
        no_parallel_large_file_operations=True,VM_started=False,host_source_or_pins_changed=False,deployed=False,
        packaging_static_validation_passed=True,runtime_validated=False)
    m.exclusive_json(HERE/'VERIFICATION.json',report)
    print(json.dumps(outputs,indent=2))


if __name__=='__main__':
    main()
