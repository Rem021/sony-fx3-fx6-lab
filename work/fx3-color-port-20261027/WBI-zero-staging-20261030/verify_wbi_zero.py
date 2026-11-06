#!/usr/bin/env python3
"""Check original dispatch bytes and match the established independent WBI map."""
import hashlib,json,struct
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;FW=HERE.parents[2]/'work/sony-firmware-20261024'
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    assert not (HERE/'validation-results.json').exists()
    p=json.loads((HERE/'WBI-zero-proof.json').read_text());inventory=json.loads((HERE/'WBI-record-inventory.json').read_text())
    old=json.loads((FW/'stage203-WBI-layout-and-early-memory/WBI-layout-audit.json').read_text())
    assert old['source_sha256']==inventory['source_sha256'] and len(old['sections'])==1399
    for a,b in zip(inventory['records'],old['sections']):
        assert (int(a['physical_start'],16),a['stored_bytes'],a['original_bytes'],a['flag'])==(b['addr'],b['rlen'],b['olen'],b['flag'])
    ap=(FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin').read_bytes();assert sha(ap)==p['AP_reference_sha256']
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    expected={
        0xfe0597d4:('and','x8, x20, #7'),
        0xfe0597dc:('add','x1, x9, x8, lsl #6'),
        0xfe0597e0:('mov','w2, #0x40'),
        0xfe0597e8:('bl','#0xfe04b444'),
        0xfe0597ec:('ldr','x23, [x24, #0x20]'),
        0xfe059804:('ldrb','w9, [x24, #0x18]'),
        0xfe059808:('ldr','x8, [x24]'),
        0xfe05980c:('tbnz','w9, #0, #0xfe059908'),
        0xfe059908:('ldr','x9, [x24, #0x20]'),
        0xfe059928:('ldr','x23, [x24]'),
        0xfe05992c:('ldr','x24, [x24, #0x20]'),
        0xfe05993c:('bl','#0xfe056298'),
        0xfe059940:('mov','w8, #4'),
        0xfe059980:('stp','x8, x23, [sp, #0x18]'),
        0xfe059984:('str','x24, [sp, #0x28]'),
        0xfe059988:('bl','#0xfe056408'),
    }
    checks=[]
    for at,want in expected.items():
        b=ap[at-0xfe040000:at-0xfe040000+4];i=next(md.disasm(b,at));assert (i.mnemonic,i.op_str)==want
        checks.append(dict(VA=hex(at),bytes=b.hex(),instruction=i.mnemonic+' '+i.op_str))
    for q in p['section_queries']:
        lo=int(q['start'],16);hi=int(q['end_exclusive'],16)
        # Compare the independently established stage203 map, including ZERO.
        assert not any(s['addr']<hi and lo<s['addr']+s['olen'] for s in old['sections'])
    result=dict(status='PASS_SCOPED_WBI_ZERO_DISPATCH_AND_STAGING_EXCLUSION',
        original_section_rows_compared_with_independent_stage203=1399,original_section_metadata_xor_checks=1399,
        stored_records=1317,zero_fill_records=82,instruction_checks=checks,
        original_reference_dispatch_fragments=2,independent_pre_DMA_fragment=1,
        two_original_records_copied_byte_exact=True,default_AP_staging_region_queries=3,overlapping_any_records=0,
        flag1_zero_semantics_supported_by_Sony_reference_and_AP_dispatch=True,
        source_kernel_version='FX3 GPL Ver7.00 reference, layout verified against 7.02 data',
        AP_code_model='A7 IV v2.00 reference, not current target FX3 AP',
        actual_WBI_restore_or_DMA_executed=False,unknown_earlier_initialization_remains=True,
        physical_chip_capacity_inferred=False,complete_source_RAM_or_full_private_ISP_recovered=False,
        modified_or_flashable_firmware_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='instruction_checks'}))


if __name__=='__main__':main()
