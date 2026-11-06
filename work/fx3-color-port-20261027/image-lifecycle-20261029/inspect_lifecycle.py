#!/usr/bin/env python3
"""Verify predecessor seal and pin the source behind image-lifecycle experiments."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from registry_guest import image,BASE,PIN,SPANS,POOL,GROUP_STRIDE,GROUP3
PREVIOUS_PIN='7bde51a229f4915d542756ff348a07b1eb6cc8a07a61b34a7a433967b5166ea9'

def main():
    prev=HERE.parent/'stp-buffer-20261029';receipt=prev/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==PREVIOUS_PIN
    entries=json.loads(receipt.read_text())['files']
    for row in entries:
        b=(prev/row['path']).read_bytes()
        assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
    raw=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);dest=HERE/'source-fragments';dest.mkdir(exist_ok=True)
    windows=[(*span,'guest-'+hex(span[0])[2:]) for span in SPANS]+[
        (0x428438,0x428598,'caller-image-descriptor-bridge'),
        (0x44de7c,0x44de9c,'owned-release-handle-prefix'),
        (0x4a0398,0x4a046a,'common-handle-bitmap-selection')]
    fragments=[]
    for a,z,label in windows:
        b=raw[a-BASE:z-BASE];path=dest/(label+'.txt')
        instructions=list(md.disasm(b,a))
        assert sum(i.size for i in instructions)==len(b),(hex(a),hex(z))
        path.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in instructions)+'\n')
        fragments.append(dict(va=hex(a),file_offset=hex(a-BASE),bytes=z-a,sha256=hashlib.sha256(b).hexdigest(),listing=str(path.relative_to(HERE))))
    tables=[]
    for va,expected,label in [(0xf1b620,[0,1,1,1],'file-backed-group-enable-counts'),(0xf1b630,[2,2,60,1],'file-backed-active-entry-counts')]:
        b=raw[va-BASE:va-BASE+16];words=list(struct.unpack('<4I',b));assert words==expected
        tables.append(dict(va=hex(va),bytes=16,words=words,sha256=hashlib.sha256(b).hexdigest(),label=label,
                           scope='Initial file bytes only; mutable at runtime, not a current camera readback'))
    out=dict(cp_sha256=PIN,previous_receipt_sha256=PREVIOUS_PIN,previous_files_verified=len(entries),source_fragments=fragments,config_tables=tables,
             registry=dict(va=hex(POOL),record_bytes=0x88,records=240,group_count=4,reserved_records_per_group=60,
                           group_stride=hex(GROUP_STRIDE),group3_va=hex(GROUP3),bytes=4*GROUP_STRIDE),
             corrected_interpretations=[
                 dict(va='0x9cecb8',previous='before_original_frame_query',current='Frame/subframe-threshold cleanup; no output image pointer or query-success contract.'),
                 dict(va='0x403a78',previous='before_original_image_query',current='Reuse-or-acquire path: held descriptor/status/key checks, allocation wrapper if needed, 0x50-byte descriptor copy with output ownership byte forced to zero.'),
                 dict(va='0x4a032c',current='Shared handle-table operation boundary. Flags 0x2a, argument5, in/out stack pointer. No claim of native service send/receive or meaning of every handle flag.')],
             public_reference=dict(url='https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000876510.html',retrieved_local_date='2026-10-29',
                                   relevance='PPLUT recording support is documented; it does not identify these private CP registry groups or validate a VENICE transplant.'),
             scope='Pinned static windows and initial configuration, separate from guest and physical acceptance. No MAIN routing, physical pixel buffers, entire donor ISP, signed modified output or flashability.')
    (HERE/'lifecycle-source-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(entries),source_windows=len(fragments),registry_records=240,config_tables=len(tables))))

if __name__=='__main__':main()
