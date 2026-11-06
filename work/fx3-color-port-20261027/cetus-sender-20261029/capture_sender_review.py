#!/usr/bin/env python3
"""Preserve candidate contexts, original block-loader contracts and corpus scope."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from scan_handoff_sources import FSROOT
from read_filesystems import Ext2
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'sender-source-review.json';assert not out.exists()
    scan=json.loads((HERE/'handoff-marker-scan.json').read_text())
    image=next(x for x in scan['images'] if x['image'].endswith('nflasha15.img'))
    fs=Ext2(Path(image['image']));entries={x['path']:x for x in fs.walk()};filepins={x['path']:x for x in image['files']}
    context=[]
    for path,token in [('/kmod/mcmn_drv.ko',b'CETUS'),('/lib/libSysDef.so',b'CETUS'),('/lib/appFw.so',b'CETUS'),('/kmod/wlan.ko',b'CP_ESCAPE')]:
        b=fs.data(entries[path]['inode']);assert sha(b)==filepins[path]['sha256'];at=0;strings=[]
        while (at:=b.find(token,at))>=0:
            lo=b.rfind(b'\0',max(0,at-160),at)+1;hi=b.find(b'\0',at,min(len(b),at+180));assert hi>=0
            strings.append(dict(file_offset=hex(at),text=b[lo:hi].decode()));at+=len(token)
        context.append(dict(path=path,bytes=len(b),sha256=sha(b),strings=strings))
    raw=(TASK/'config-producer-20261029/original-files/loader_nor.bin').read_bytes()
    assert sha(raw)=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
    cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);folder=HERE/'source-fragments';folder.mkdir(exist_ok=True);fragments=[]
    for lo,hi in [(0xfe052ee8,0xfe052fc0),(0xfe05a1b4,0xfe05a370),(0xfe05a56c,0xfe05a648),
        (0xfe05881c,0xfe058894),(0xfe04fab0,0xfe04fd28),(0xfe05863c,0xfe058690)]:
        data=raw[lo-0xfe049000:hi-0xfe049000];decoded=list(cs.disasm(data,lo));assert sum(x.size for x in decoded)==len(data)
        f=folder/f'{lo:08x}-{hi:08x}.txt';assert not f.exists()
        f.write_text('\n'.join(f'{x.address:08x} {x.bytes.hex()} {x.mnemonic:8} {x.op_str}' for x in decoded)+'\n')
        fragments.append(dict(VA=hex(lo),end_exclusive=hex(hi),bytes=len(data),original_bytes_sha256=sha(data),listing=str(f.relative_to(HERE))))
    strings=[]
    for va in [0xfe05fda0,0xfe05fdc8,0xfe05fe54,0xfe05fe67]:
        at=va-0xfe049000;assert raw[at-1]==0
        end=raw.index(b'\0',at);strings.append(dict(VA=hex(va),text=raw[at:end].decode()))
    catalog=TASK.parent/'sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json'
    receipt=catalog.parents[1]/'final-receipt.json';old=json.loads(receipt.read_text())
    pin=next(x for x in old['files'] if x['path'].endswith('/work/kernel-symbol-catalog.json'))
    assert sha(catalog.read_bytes())==pin['sha256']=='b37c6b7d4315f65234cd6b64c3be4a3d7c6e0d2cca66204e27cb5c575000a51e'
    records=json.loads(catalog.read_text());assert records[0]['name']=='_head' and records[0]['file_offset']==0
    assert records[0]['address']==0xffffff8008080000
    result=dict(candidate_string_contexts=context,NOR_sha256=sha(raw),source_fragments=fragments,original_bulk_load_strings=strings,
        original_bulk_contract=dict(caller_first='0xfe052f24 ->0xfe05a1b4',caller_pre='0xfe052f90 ->0xfe05a2b4',
            slot_index=5,boot_info_base='0xfe040000',entry_stride='0x40',
            slot5_fields=['0xfe040140','0xfe040144','0xfe040150'],
            source_field_scale='The original code shifts the first two u32 values left9 before byte-offset/length arithmetic.',
            pre_length='0x500000',remaining_offset='0x500000',remaining_length='u32 count<<9 minus0x500000, with a separate original fallback branch',
            read_wrapper='0xfe05a56c',lower_reader='0xfe04fab0',
            lower_reader_source_bound='W1>>26 must be0',lower_reader_length_bound='W2 must be <=0x4000000',
            memory_mapped_branch_source_base='0xd0000000',
            metadata_values_supplied=False,block_read_success_obtained=False,
            scope='Original code/log labels and arithmetic. No actual slot values, packed flash contents or proof of DmmCfg coverage.'),
        reused_kernel_navigation=dict(catalog=str(catalog),catalog_bytes=catalog.stat().st_size,catalog_sha256=sha(catalog.read_bytes()),
            prior_manifest=str(receipt),prior_manifest_sha256=sha(receipt.read_bytes()),symbol_count=len(records),first_symbol=records[0],
            scope='Existing original recovery reused read only for navigation; old main/guest/device tools are not run and old validation is not counted as a new run.'),
        interpretation=dict(sender_located=False,source_names_alone_prove_sender=False,
            WLAN_CP_ESCAPE_is_COEX_token=True,appFw_CETUS_strings_are_beep_DMM_calls=True,
            full_AP_or_boot_source_absence_proved=False,normal_DMM_population_proved=False),
        scope='Read-only source context and strict prefix bounds. Bounded negative searches do not prove global sender absence or complete firmware understanding. No native/device action, keys, port or signed modified package.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(context_files=len(context),source_fragments=len(fragments),strings=strings,bulk=result['original_bulk_contract'])))
if __name__=='__main__':main()
