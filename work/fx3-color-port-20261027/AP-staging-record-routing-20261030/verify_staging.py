#!/usr/bin/env python3
"""Independent byte-level instruction checks and default span round trips."""
import hashlib, importlib.util, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
HERE = Path(__file__).resolve().parent
TASK = HERE.parent
FW = HERE.parents[2]/'work/sony-firmware-20261024'
def sha(b): return hashlib.sha256(b).hexdigest()


def main():
    assert not (HERE/'validation-results.json').exists()
    proof = json.loads((HERE/'staging-proof.json').read_text())
    ap = Path(proof['AP_reference']['path']).read_bytes()
    assert sha(ap) == proof['AP_reference']['sha256']
    md = Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    checks = {
        0xfe04ec0c: ('bl','#0xfe04c900'),
        0xfe04edf4: ('bl','#0xfe04c900'),
        0xfe04c900: ('b','#0xfe04d0d4'),
        0xfe04d0d8: ('str','x0, [x9, #0x40]'),
        0xfe05b2dc: ('cmp','w8, #4'),
        0xfe05b2e0: ('b.ne','#0xfe05b334'),
        0xfe05b33c: ('bl','#0xfe04c904'),
        0xfe050164: ('mov','w0, #0x19a'),
        0xfe050170: ('movk','w0, #0xfa, lsl #16'),
        0xfe05018c: ('mov','w9, #-1'),
        0xfe050190: ('cmp','x2, x9'),
        0xfe050198: ('add','w0, w20, #1'),
        0xfe0501a0: ('str','x2, [x19, #0x38]'),
        0xfe0501c0: ('add','w0, w20, #0x2d'),
        0xfe0501c8: ('str','x2, [x19, #0x40]'),
        0xfe0501ec: ('str','x2, [x19, #0x48]'),
        0xfe0501f0: ('bl','#0xfe052af8'),
        0xfe052b0c: ('ldr','x1, [x0, #0x218]'),
        0xfe052b10: ('ldr','x2, [x0, #0x38]'),
        0xfe052b14: ('ldr','x3, [x0, #0x220]'),
        0xfe052b24: ('bl','#0xfe05d884'),
        0xfe052168: ('mov','w0, #0x19a'),
        0xfe05216c: ('movk','w0, #0xfa, lsl #16'),
        0xfe052290: ('add','x29, x8, x10'),
        0xfe05b6e8: ('mov','w8, #3'),
        0xfe05b6f0: ('str','w8, [x22]'),
    }
    instruction_checks=[]
    for address, expected in checks.items():
        raw=ap[address-0xfe040000:address-0xfe040000+4]
        i=next(md.disasm(raw,address))
        assert (i.mnemonic,i.op_str)==expected
        instruction_checks.append(dict(VA=hex(address),bytes=raw.hex(),mnemonic=i.mnemonic,operands=i.op_str))
    previous=json.loads((TASK/'CP-escape-config-20261030/escape-source-proof.json').read_text())
    original_rows=previous['class5_rows']
    f=proof['independent_original_fragments'];call=f['AP_source_wrapper_prefix']
    source=int(call['X2'],16);dest=int(call['X1'],16);length=int(call['X3'],16)
    capacity=int(f['AP_context_fields']['0x40'],16)
    reader=FW/'stage2/extraction/read_filesystems.py'
    assert sha(reader.read_bytes())=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    spec=importlib.util.spec_from_file_location('pinned_fs_reader',reader)
    fsmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(fsmod)
    image=FW/'stage2/extraction/nflasha8.img'
    assert sha(image.read_bytes())=='3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
    fs=fsmod.FAT16(image);entries={x['path']:x for x in fs.walk()}
    rows=[]
    for row in original_rows:
        lo=int(row['start'],16);end=int(row['end'],16)+1
        at=source+lo-dest;last=source+end-dest
        assert dest <= lo < end <= dest+length
        assert source <= at < last <= source+capacity
        assert dest+(at-source)==lo and dest+(last-source)==end
        path=row['path'].replace('\\','/')
        entry=entries.get(path)
        member=None
        if entry:
            data=fs.data(entry['cluster'],entry['size'])
            assert len(data)==entry['size'] and len(data)<=end-lo
            member=dict(actual_bytes=len(data),sha256=sha(data),declared_slot_tail_bytes=(end-lo)-len(data),
                        tail_initialization_proved=False)
        rows.append(dict(path=row['path'],original_row_sha256=row['original_record_sha256'],
            CP_start=hex(lo),CP_end_exclusive=hex(end),declared_slot_bytes=end-lo,
            projected_AP_start=hex(at),projected_AP_end_exclusive=hex(last),
            CP_address_roundtrip_exact=True,member_in_original_update_p8=member))
    assert len(rows)==9 and sum(x['member_in_original_update_p8'] is not None for x in rows)==4
    dmm=next(x for x in rows if x['path']=='\\DmmCfg.bin')
    assert dmm['projected_AP_start']=='0x4132d8e00'
    assert dmm['member_in_original_update_p8']['actual_bytes']==43320
    assert dmm['member_in_original_update_p8']['sha256']=='820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166'
    (HERE/'default-span-roundtrip.json').write_text(json.dumps(dict(
        source=hex(source),destination=hex(dest),length=hex(length),AP_declared_capacity=hex(capacity),
        scope='Default address arithmetic only. File slot sizes and firmware file sizes are different; neither tails nor holes are presumed initialized.',
        rows=rows),indent=2)+'\n')
    result=dict(status='PASS_SCOPED_STAGING_AND_RECORD_ROUTING',instruction_checks=instruction_checks,
        complete_original_leaf_API_calls=len(proof['complete_original_leaf_API_calls']),
        original_leaf_instructions=sum(x['instructions'] for x in proof['complete_original_leaf_API_calls']),
        CP_context_fragment_instructions=f['CP_context']['instructions'],AP_wrapper_prefix_instructions=call['instructions'],
        independent_original_fragments_not_whole_boot=True,mode3_explicit_fixture_not_current_body=True,
        original_record1_offset_verified='0xd2000',source_pointer_0x38_bound_to_FA019A_in_reference=True,
        AP_CP_property_selection_proved_in_reference=True,source_pointer_admission_check_complete=False,
        class5_default_address_roundtrips=9,original_p8_members=4,DmmCfg_slot_bytes=dmm['declared_slot_bytes'],
        DmmCfg_actual_bytes=43320,DmmCfg_tail_initialization_proved=False,
        wrong_CP_record_allones_reaches_transfer_boundary=True,wrong_record_is_analytical_control_not_observed_boot=True,
        actual_transfer_file_load_hardware_or_privileged_execution=False,FX3_AP_boot_or_current_backup_obtained=False,
        CMOS_RAW_full_ISP_or_flashable_modified_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='instruction_checks'}))


if __name__=='__main__': main()
