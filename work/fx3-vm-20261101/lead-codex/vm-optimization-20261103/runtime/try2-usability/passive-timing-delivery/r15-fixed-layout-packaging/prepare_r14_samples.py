#!/usr/bin/env python3
"""One offline build of each r14 sample; never runs guest or writes CPIO.

Uses the coordinator-approved linker alternative after Zig objcopy's actual
ELF output failed as unimplemented. Frozen r14 sources and debug ELFs are read
only. Output paths are exclusive; no retries or deletion of prior artifacts.
"""
import json
from pathlib import Path
import subprocess
import fixed_layout as m

R14=m.DEL/'v25-r14-low-overhead-gate'
BUILD_SHA='af9cfbae2f0e8bbc076f74f699b2fe2227a422433bce1234f9d25e1c950af387'
SOURCE_SHA='d71ae629cb023774def26481f631ed12e6e77e55ca08e4acb17545ce568227b3'


def main():
    m.volume_check()
    build_path=R14/'BUILD.json'; source_path=R14/'SOURCE-SHA256SUMS'
    m.require(m.sha_file(build_path)==BUILD_SHA and m.sha_file(source_path)==SOURCE_SHA, 'frozen r14 build/source identity mismatch')
    sources=m.source_manifest_rows(source_path)
    build=json.loads(m.read_file(build_path))
    summaries=[]
    for variant in ('N1','N64'):
        b=build['variants'][variant]
        command=list(b['command'])
        raw=Path(command[command.index('-o')+1])
        m.require(b['exit']==0 and m.sha_file(raw)==b['sha256'], 'original r14 ELF identity mismatch')
        output=m.output_path(m.HERE/'samples'/f'fx3-ui-gate-v14-{variant.lower()}-linker-strip.so')
        original=list(command)
        inputs=m.command_inputs(original)
        command[command.index('-o')+1]=str(output)
        command.insert(2,'-Wl,--strip-debug')
        # Reserve target exclusively before allowing the approved linker to fill it.
        with output.open('xb'):
            pass
        incomplete=Path(str(output)+'.INCOMPLETE.json')
        m.exclusive_json(incomplete,dict(state='incomplete',command=command))
        result=subprocess.run(command,text=True,capture_output=True,timeout=120)
        receipt=dict(schema='fx3-linker-strip-build/v1',command=command,original_command=original,
                     exit=result.returncode,stdout=result.stdout,stderr=result.stderr,
                     raw_sha256=m.sha_file(raw),stripped_sha256=m.sha_file(output),
                     raw_build_manifest_sha256=BUILD_SHA,source_manifest_sha256=SOURCE_SHA,
                     command_input_hashes=inputs,source_rows=sources,
                     raw_bytes=raw.stat().st_size,stripped_bytes=output.stat().st_size,
                     no_VM=True,no_CPIO=True,method_authority='Orca msg_b4a35376625d')
        receipt_path=m.HERE/'samples'/f'{variant}-build.json'
        m.exclusive_json(receipt_path,receipt)
        m.require(result.returncode==0, 'linker strip failed; incomplete output retained')
        audit=m.audit_elf(m.read_file(raw),m.read_file(output))
        m.exclusive_json(m.HERE/'samples'/f'{variant}-ELF-AUDIT.json',audit)
        release=dict(schema='fx3-fixed-layout-release/v1',helper_version='r14',variant=variant,
                     soname=f'fx3-ui-gate-v14-{variant.lower()}.so',raw_sha256=m.sha_file(raw),
                     stripped_sha256=m.sha_file(output),
                     provenance={
                         'raw_build_manifest':dict(path=str(build_path),sha256=BUILD_SHA),
                         'source_manifest':dict(path=str(source_path),sha256=SOURCE_SHA),
                         'strip_build_receipt':dict(path=str(receipt_path),sha256=m.sha_file(receipt_path))},
                     diagnostic_contract=dict(scope='r14 packaging sample only; NOT final r15 nonce contract',
                                              runtime_validated=False))
        m.provenance_check(release,raw,output)
        release_path=m.HERE/'samples'/f'{variant}-release.json'
        m.exclusive_json(release_path,release)
        m.exclusive_json(m.HERE/'samples'/f'{variant}-COMPLETE.json',dict(state='complete',audit_passed=True,
            incomplete_marker_is_historical=True,raw_sha256=release['raw_sha256'],stripped_sha256=release['stripped_sha256']))
        summaries.append(dict(variant=variant,raw_bytes=receipt['raw_bytes'],stripped_bytes=receipt['stripped_bytes'],
                              stripped_sha256=receipt['stripped_sha256'],audit_passed=True,
                              static_sections_removed=audit['removed_static_symbol_sections']))
    m.exclusive_json(m.HERE/'STRIP-RECEIPT.json',dict(variants=summaries,originals_unchanged=True,
        original_debug_ELFs_retained=True,method_authority='Orca msg_b4a35376625d',no_VM=True,no_CPIO=True))
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    main()
