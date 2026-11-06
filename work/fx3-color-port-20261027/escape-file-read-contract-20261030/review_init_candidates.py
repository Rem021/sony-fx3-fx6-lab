#!/usr/bin/env python3
"""Keep nearby clear/zero names scoped to their actual original inputs."""
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;FW=HERE.parents[2]/'work/sony-firmware-20261024'
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    assert not (HERE/'initialization-candidate-review.json').exists()
    ap=(FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin').read_bytes()
    assert sha(ap)=='2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74'
    bk=TASK/'dmm-backup-20261029';j=json.loads((bk/'final-receipt.json').read_text());p=bk/'extract_backup_parameters.py'
    assert sha(p.read_bytes())==next(x for x in j['files'] if x['path']==p.name)['sha256']
    s=importlib.util.spec_from_file_location('pinned_owned_BK4',p);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
    record=(bk/'original-records/canonical-bank0.bin').read_bytes()
    assert sha(record)=='33789a7a4d648c9a0bd74bd332de395500bdf0f363839f1d770393a3a3191da5'
    prop=h.property_at(record,0xfa0080);table=bytes.fromhex(prop['value_hex']);assert len(table)==9216
    rows=[]
    for at in range(0,len(table),0x90):
        row=table[at:at+0x90];start,end,partition,mode=struct.unpack_from('<QQII',row)
        if start==end==partition==mode==0:break
        path=row[24:].split(b'\0')[0].decode()
        overlap=start<0x414a00000 and end+1>0x412000000
        rows.append(dict(index=len(rows),start=hex(start),end_inclusive=hex(end),partition=partition,mode=hex(mode),path=path,
                         overlaps_default_AP_staging=overlap))
    assert len(rows)==9 and not any(x['overlaps_default_AP_staging'] for x in rows)
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    checks={0xfe04f618:('bl','#0xfe05231c'),0xfe04f640:('bl','#0xfe05231c'),
            0xfe052354:('mov','w0, #0x80'),0xfe052360:('movk','w0, #0xfa, lsl #16'),
            0xfe05236c:('bl','#0xfe05b2b8'),0xfe059928:('ldr','x23, [x24]'),
            0xfe05992c:('ldr','x24, [x24, #0x20]')}
    results=[]
    for address,want in checks.items():
        i=next(md.disasm(ap[address-0xfe040000:address-0xfe040000+4],address))
        assert (i.mnemonic,i.op_str)==want
        results.append(dict(VA=hex(address),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str))
    windows=[]
    for label,lo,hi in [('reference-clear-reboot-dispatch',0xfe04f5f0,0xfe04f6cc),
                         ('reference-AP-descriptor-query',0xfe05231c,0xfe0523a0),
                         ('reference-MMC-zero-fill-candidate',0xfe059908,0xfe0599d0)]:
        raw=ap[lo-0xfe040000:hi-0xfe040000];path=HERE/'listings'/(label+'.txt')
        path.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,lo))+'\n')
        windows.append(dict(begin=hex(lo),end_exclusive=hex(hi),original_bytes_sha256=sha(raw),listing=str(path.relative_to(HERE))))
    result=dict(AP_default_FA0080_sha256=sha(table),AP_default_descriptors=rows,instruction_checks=results,source_windows=windows,
        clear_reboot_label_not_a_whole_staging_zeroing_proof=True,
        clear_reboot_calls_config_loader_that_queries_AP_FA0080=True,
        AP_default_descriptors_overlap_staging=False,
        MMC_zero_fill_diagnostic_at='0xfe065921',MMC_zero_fill_code_at='0xfe059908',
        MMC_zero_fill_target='descriptor X24+0; length X24+0x20',MMC_zero_fill_bound_to_FA019A=False,
        candidate_hardware_helper_calls_executed=False,any_prior_whole_boot_staging_initialization_proved=False,
        actual_target_FX3_AP_loader_obtained=False,goal_complete=False)
    (HERE/'initialization-candidate-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(AP_default_descriptors=len(rows),overlap_with_default_staging=False,instruction_checks=len(results),whole_boot_zeroing_proved=False)))


if __name__=='__main__':main()
