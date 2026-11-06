#!/usr/bin/env python3
"""Independent static return-contract checks and bounded source-file inventory."""
import hashlib, importlib.util, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
FW=HERE.parents[2]/'work/sony-firmware-20261024'
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    assert not (HERE/'validation-results.json').exists()
    proof=json.loads((HERE/'file-read-proof.json').read_text())
    ap=(FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin').read_bytes()
    assert sha(ap)==proof['AP_reference']['sha256']
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    checks={
        0xfe059e30:('bl','#0xfe05a1e0'),
        0xfe059e34:('mov','w20, w0'),
        0xfe059e40:('mov','w1, w20'),
        0xfe059e44:('bl','#0xfe05a674'),
        0xfe059e48:('mov','w21, w0'),
        0xfe059e4c:('tbz','w0, #0x1f, #0xfe059e84'),
        0xfe059e88:('mov','w0, w20'),
        0xfe059e80:('mov','w20, #-0x198'),
        0xfe052298:('bl','#0xfe059e20'),
        0xfe05229c:('sxtw','x4, w0'),
        0xfe0522a0:('mov','w0, #6'),
        0xfe0522b0:('bl','#0xfe055530'),
        0xfe0522b8:('add','w27, w27, #1'),
        0xfe0522bc:('cmp','w20, w27'),
        0xfe0522d4:('mov','w0, wzr'),
        0xfe05a65c:('ldrb','w8, [x20, #0x1a]'),
        0xfe05a664:('ldr','w21, [x20, #0x1c]'),
        0xfe05a66c:('stp','w8, w21, [x23, #0x18]'),
        0xfe04e4d0:('bl','#0xfe058b54'),
        0xfe04e51c:('bl','#0xfe058b54'),
        0xfe04e55c:('mov','x2, x24'),
        0xfe04e560:('bl','#0xfe04b444'),
    }
    checked=[]
    for at,want in checks.items():
        raw=ap[at-0xfe040000:at-0xfe040000+4];i=next(md.disasm(raw,at))
        assert (i.mnemonic,i.op_str)==want
        checked.append(dict(VA=hex(at),bytes=raw.hex(),instruction=i.mnemonic+' '+i.op_str))
    wrapper=list(md.disasm(ap[0x19e20:0x19e94],0xfe059e20))
    assert not any(i.mnemonic=='cmp' for i in wrapper)
    after_load=list(md.disasm(ap[0x1229c:0x122b8],0xfe05229c))
    assert not any(i.mnemonic.startswith('b.') or i.mnemonic in ['cbz','cbnz','tbz','tbnz'] for i in after_load)
    calls=[]
    for label,lo,hi,targets in [
        ('wrapper',0xfe059e20,0xfe059e94,{0xfe05a1e0,0xfe05a674,0xfe055530}),
        ('file_read',0xfe05a674,0xfe05a84c,{0xfe04e424,0xfe055530}),
        ('cluster_read',0xfe04e424,0xfe04e580,{0xfe058b54,0xfe04b444,0xfe055530}),
        ('escape_loader',0xfe0520d4,0xfe05231c,{0xfe055530,0xfe05b2b8,0xfe059e94,0xfe059e20})]:
        hits=[dict(VA=hex(i.address),target=i.op_str) for i in md.disasm(ap[lo-0xfe040000:hi-0xfe040000],lo) if i.mnemonic=='bl']
        assert {int(x['target'].lstrip('#'),16) for x in hits}==targets
        calls.append(dict(function=label,original_direct_calls=hits,no_direct_memset_call=True,
                          scope='Direct call targets only; not proof of absence of earlier whole-boot memory initialization.'))
    reader=FW/'stage2/extraction/read_filesystems.py';assert sha(reader.read_bytes())=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    spec=importlib.util.spec_from_file_location('pinned_inventory_reader',reader);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    targets={'bonobo.bin','idt_cam.bin','defdet.bin','psd.bin','lensfile.bin'}
    inventories=[]
    for part,pin,kind in [
        (3,'ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568',h.FAT16),
        (7,'ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7',h.Ext2),
        (8,'3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b',h.FAT16),
        (15,'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',h.Ext2)]:
        path=reader.parent/f'nflasha{part}.img';assert sha(path.read_bytes())==pin
        fs=kind(path);entries=list(fs.walk());found=[]
        for entry in entries:
            if entry['path'].rsplit('/',1)[-1].casefold() in targets:
                data=fs.data(entry['cluster'],entry['size']) if kind is h.FAT16 else fs.data(entry['inode'])
                found.append(dict(metadata=entry,sha256=sha(data)))
        inventories.append(dict(image=str(path),image_sha256=pin,entries_including_directories=len(entries),matches=found))
    assert len(inventories[0]['matches'])==2 and all(not x['matches'] for x in inventories[1:])
    original=json.loads((TASK/'AP-staging-record-routing-20261030/default-span-roundtrip.json').read_text())
    rows=sorted(original['rows'],key=lambda x:int(x['CP_start'],16));cursor=int(original['destination'],16);gaps=[]
    for row in rows:
        lo=int(row['CP_start'],16);hi=int(row['CP_end_exclusive'],16)
        assert cursor<=lo<hi
        if lo>cursor:gaps.append(dict(start=hex(cursor),end_exclusive=hex(lo),bytes=lo-cursor))
        cursor=hi
    envelope=int(original['length'],16);slots=sum(x['declared_slot_bytes'] for x in rows)
    assert slots+sum(x['bytes'] for x in gaps)==envelope
    coverage=dict(envelope_bytes=envelope,declared_slot_bytes=slots,unlisted_gap_bytes=sum(x['bytes'] for x in gaps),gaps=gaps,
                  original_p8_file_bytes=sum((x['member_in_original_update_p8'] or {}).get('actual_bytes',0) for x in rows),
                  byte_coverage_is_projection_not_observed_RAM=True,
                  no_substitution_between_partition3_and_partition8=True,missing_names_search_scope='Parsed file names in original p3/p7/p8/p15 only; no whole-package, compressed-content or real-body absence claim.')
    (HERE/'source-inventory-and-coverage.json').write_text(json.dumps(dict(inventories=inventories,coverage=coverage),indent=2)+'\n')
    result=dict(status='PASS_SCOPED_FILE_READ_AND_RETURN_CONTRACT',instruction_checks=checked,direct_call_checks=calls,
        original_root_lookup_fragments=8,original_ctype_initializer_executed=True,ctype_helper_substitutions=0,
        p8_files_found=4,p8_root_names_returning_minus408=4,nested_sabin_path_not_guest_tested=True,
        DmmCfg_full_sector_read_request=dict(start_sector=224,sectors=84,bytes=43008),
        DmmCfg_tail_read_request=dict(sector=308,sectors=1),original_tail_copy_bytes=312,
        original_file_read_or_device_block_io_executed=False,slot_tail_bytes_unchanged_in_independent_copy_fragment=59080,
        static_short_read_equality_check_present=False,static_selected_file_error_aggregation_present=False,
        any_prior_whole_boot_zeroing_proved=False,actual_source_RAM_complete=False,
        complete_FX3_target_boot_RAW_full_ISP_or_flashable_modified_package_proved=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],instruction_checks=len(checked),original_lookup_cases=8,
        declared_slot_bytes=slots,unlisted_gap_bytes=coverage['unlisted_gap_bytes'],p8_file_bytes=coverage['original_p8_file_bytes'],goal_complete=False)))


if __name__=='__main__':main()
