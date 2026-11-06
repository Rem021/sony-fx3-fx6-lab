#!/usr/bin/env python3
"""Task-scoped offline r15 relink and provenance, no CPIO/VM actions here."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).absolute().parent
DEL=HERE.parent
TOOL=DEL/'r15-fixed-layout-packaging/fixed_layout.py'
TOOL_SHA='b5b9bf75763b193575a007074e6701d1a1541ba9d3658ae32a164fc350eca8bc'
assert hashlib.sha256(TOOL.read_bytes()).hexdigest()==TOOL_SHA
spec=importlib.util.spec_from_file_location('fixed_layout_frozen',TOOL)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
R15=DEL/'v25-r15-snapshot-tail'


def main():
    m.volume_check()
    preflight=json.loads(m.read_file(HERE/'PREFLIGHT.json'))
    source_json=R15/'SOURCE-FREEZE.json'
    source_text=DEL/'r16-r15-guest-SOURCE-SHA256SUMS'
    build_path=R15/'BUILD.json'
    m.require(m.sha_file(source_json)==preflight['r15_pins']['SOURCE-FREEZE.json'], 'r15 freeze changed')
    m.require(m.sha_file(source_text)==preflight['adapted_source_manifest_sha256'], 'adapted sources changed')
    m.require(m.sha_file(build_path)==preflight['r15_build_sha256'], 'r15 build receipt changed')
    sources=m.source_manifest_rows(source_text)
    build=json.loads(m.read_file(build_path))
    summaries=[]
    for variant in ('N1','N64'):
        b=build['variants'][variant]
        original=list(b['command'])
        raw=Path(original[original.index('-o')+1])
        m.require(b['exit']==0 and m.sha_file(raw)==b['sha256'], 'original debug ELF changed')
        output=m.output_path(HERE/'samples'/f'fx3-ui-gate-v15-{variant.lower()}-linker-strip.so')
        inputs=m.command_inputs(original)
        command=list(original)
        command[command.index('-o')+1]=str(output)
        command.insert(2,'-Wl,--strip-debug')
        with output.open('xb'):
            pass
        m.exclusive_json(Path(str(output)+'.INCOMPLETE.json'),dict(state='incomplete',command=command))
        result=subprocess.run(command,text=True,capture_output=True,timeout=120)
        receipt=dict(schema='fx3-linker-strip-build/v1',command=command,original_command=original,
                     exit=result.returncode,stdout=result.stdout,stderr=result.stderr,
                     raw_sha256=m.sha_file(raw),stripped_sha256=m.sha_file(output),
                     raw_build_manifest_sha256=m.sha_file(build_path),source_manifest_sha256=m.sha_file(source_text),
                     original_source_freeze_sha256=m.sha_file(source_json),
                     command_input_hashes=inputs,source_rows=sources,
                     raw_bytes=raw.stat().st_size,stripped_bytes=output.stat().st_size,
                     no_VM=True,no_CPIO=True,method_authority='task_d3ac03eee1f0/ctx_f1626e885554')
        receipt_path=HERE/'samples'/f'{variant}-build.json'
        m.exclusive_json(receipt_path,receipt)
        m.require(result.returncode==0, 'linker failed; incomplete output retained')
        audit=m.audit_elf(m.read_file(raw),m.read_file(output))
        m.require(audit['stripped_size']<=m.PINS['slot_size'], 'r15 ELF exceeds fixed slot')
        m.exclusive_json(HERE/'samples'/f'{variant}-ELF-AUDIT.json',audit)
        release=dict(schema='fx3-fixed-layout-release/v1',helper_version='r15',variant=variant,
                     soname=f'fx3-ui-gate-v15-{variant.lower()}.so',raw_sha256=m.sha_file(raw),
                     stripped_sha256=m.sha_file(output),
                     provenance={
                         'raw_build_manifest':dict(path=str(build_path),sha256=m.sha_file(build_path)),
                         'source_manifest':dict(path=str(source_text),sha256=m.sha_file(source_text)),
                         'strip_build_receipt':dict(path=str(receipt_path),sha256=m.sha_file(receipt_path))},
                     diagnostic_contract=dict(
                         guest_report=dict(path=str(R15/'REPORT.md'),sha256=m.sha_file(R15/'REPORT.md')),
                         source_freeze=dict(path=str(source_json),sha256=m.sha_file(source_json)),
                         source_adaptation=dict(path=str(HERE/'SOURCE-ADAPTATION.json'),sha256=m.sha_file(HERE/'SOURCE-ADAPTATION.json')),
                         protocol='r15 requested immutable snapshot v5',protocol_version=5,
                         physical_base='0x41dc00000',reserved_bytes=65536,
                         request=dict(offset='0x3000',bytes=64),
                         ready_ack=dict(offset='0x3040',bytes=192),
                         payload=dict(offset='0x3100',bytes=784,qwords=98,end_exclusive='0x3410'),
                         ordinary_ram_statistics_authoritative=True,uc_region_plain_aligned_32bit_access_and_dmb_only=True,
                         atomic_fields_snapshot_is_transactionally_consistent=False,
                         snapshot_is_end_state=False,
                         extra_tail_cont_not_part_of_first_frame_or_performance_window=True,
                         protocol_runtime_validated=False,VM_started=False,
                         scope='guest packaging only; no host runner source/pin integration; r16 host managed separately'))
        m.contract_check(release,audit)
        m.provenance_check(release,raw,output)
        m.exclusive_json(HERE/'samples'/f'{variant}-release.json',release)
        m.exclusive_json(HERE/'samples'/f'{variant}-COMPLETE.json',dict(state='complete',audit_passed=True,
            raw_debug_elf_retained=True,historical_incomplete_marker_superseded=True,
            raw_sha256=release['raw_sha256'],stripped_sha256=release['stripped_sha256']))
        summaries.append(dict(variant=variant,raw_bytes=receipt['raw_bytes'],stripped_bytes=receipt['stripped_bytes'],
            stripped_sha256=receipt['stripped_sha256'],alloc_section_count=len(audit['alloc_sections']),
            program_headers_equal=audit['program_headers_equal'],
            elf_header_changes=audit['elf_header_changes'],pt_load_differing_offsets=[x['differing_file_offsets'] for x in audit['pt_load_comparison']],
            removed_static_sections=audit['removed_static_symbol_sections']))
    m.exclusive_json(HERE/'STRIP-RECEIPT.json',dict(variants=summaries,tool_sha256=TOOL_SHA,
        original_debug_ELFs_retained=True,no_VM=True,no_CPIO=True))
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    main()
