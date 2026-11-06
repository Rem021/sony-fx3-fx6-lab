#!/usr/bin/env python3
"""Pin original BK4/query/MMU boundaries and distinguish defaults from boot."""
import datetime,hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_ARM
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
sys.path.insert(0,str(HERE))
from backup_query_guest import image,BASE,PIN
def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    target=HERE/'backup-source-review.json';assert not target.exists()
    previous=TASK/'dmm-config-20261029/final-receipt.json'
    assert sha(previous.read_bytes())=='de2a4e5c86324321bd2fe766e51231cf84193746daa8352610280a4f34f6a168'
    old=json.loads(previous.read_text())['files']
    for r in old:
        b=(previous.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    raw=image();folder=HERE/'source-fragments';folder.mkdir(exist_ok=True);fragments=[]
    windows=[(0x4982cc,0x498338,CS_MODE_THUMB),(0x4985c4,0x498636,CS_MODE_THUMB),
        (0xa85174,0xa8527c,CS_MODE_THUMB),(0xa84be8,0xa84c3c,CS_MODE_THUMB),
        (0x4d7a84,0x4d7b40,CS_MODE_THUMB),(0xa85482,0xa85576,CS_MODE_THUMB),
        (0x53894c,0x53898c,CS_MODE_ARM),(0x54bbd0,0x54bbf4,CS_MODE_ARM),
        (0x554ebc,0x555014,CS_MODE_ARM),(0x52ee34,0x52ee68,CS_MODE_ARM),
        (0x52f17c,0x52f1ac,CS_MODE_ARM)]
    for a,z,mode in windows:
        b=raw[a-BASE:z-BASE];file=folder/f'{a:08x}-{z:08x}.txt'
        file.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:12} {i.op_str}' for i in Cs(CS_ARCH_ARM,mode).disasm(b,a))+'\n')
        fragments.append(dict(va=hex(a),bytes=len(b),mode='ARM' if mode==CS_MODE_ARM else 'Thumb',sha256=sha(b),listing=str(file.relative_to(HERE))))
    table=raw[0xb54930-BASE:0xb54930-BASE+128]
    ranges=[struct.unpack_from('<4Q',table,i*32) for i in range(4)]
    evidence=json.loads((HERE/'public-template-parameters.json').read_text())
    sample=next(t for t in evidence['templates'] if t['member']==evidence['canonical_template'])
    transforms=[]
    for record in sample['records']:
        v=int(record['parameters'][0]['u64'],16);matches=[]
        for index,(physical,logical,alias,n) in enumerate(ranges):
            if physical<=v<physical+n:matches.append(dict(range_index=index,logical_address=hex(v-physical+logical),high_word_zero=(v-physical+logical)>>32==0))
        transforms.append(dict(bank_index=record['index'],original_value=hex(v),matching_ranges=matches))
    assert transforms[0]['matching_ranges']==[] and transforms[1]['matching_ranges'][0]['logical_address']=='0x9a08e00'
    tomco=(HERE/'tomco.txt').read_text();values={}
    for line in tomco.splitlines():
        if '=' in line:
            k,v=line.split('=',1)
            if k in ['snapshotdbg_addr','snapshotdbg_size']:values[k]=int(v,0)
    candidate=0x9a08e00;adjacent=int(sample['records'][1]['parameters'][1]['u64'],16)
    assert candidate+adjacent==values['snapshotdbg_addr']==0x9a21e00
    assert 'memcfg=0x7000000@0x09000000:uc' in tomco and 0x09000000<=candidate<candidate+adjacent<=0x10000000
    source_cp_config=TASK/'dmm-config-20261029/original-files/DmmCfg.bin'
    cp_config=source_cp_config.read_bytes();assert sha(cp_config)=='820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166'
    wbi=TASK.parent/'sony-firmware-20261024/stage2/extraction/nflasha5.img';b=wbi.read_bytes()
    assert sha(b)=='ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1'
    h=struct.unpack_from('<11Q',b);table_at=h[5]+h[6];sections=[struct.unpack_from('<8Q',b,table_at+i*64) for i in range(h[1])]
    covers=[]
    for record in sample['records']:
        value=int(record['parameters'][0]['u64'],16)
        found=[i for i,s in enumerate(sections) if s[0]<=value<s[0]+s[4]]
        assert found==[];covers.append(dict(bank_index=record['index'],parameter_address=hex(value),covering_sections=found))
    out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),CP_sha256=PIN,
        previous_sealed_files_verified=len(old),source_fragments=fragments,
        physical_range_table=dict(va='0xb54930',sha256=sha(table),entries=[list(map(hex,r)) for r in ranges]),
        original_parameter_transforms=transforms,
        candidate_layout=dict(bank_index=1,candidate_CP_logical_address=hex(candidate),adjacent_parameter_0xfa0183=hex(adjacent),
            adjacent_parameter_capacity_meaning='Layout inference; no dedicated0xfa0183 consumer recovered here.',
            computed_end=hex(candidate+adjacent),original_tomco_snapshotdbg_addr=hex(values['snapshotdbg_addr']),
            within_tomco_uncached_region=True,CP_file_bytes=len(cp_config),CP_file_fits=True,
            fit_does_not_prove_file_loading_or_identity=True),
        WBI_evidence=dict(sha256=sha(b),sections=len(sections),parameter_address_coverage=covers),
        normal_selection_and_load=dict(selected_bank_proven=False,canonical_template_is_body_selection=False,
            upstream_loader_copy_to_CP_backup_or_config_RAM_proven=False,source_file_loaded_at_candidate_proven=False,
            observation='Static default-template second record and CP address table agree; normal bank selection and memory state remain missing.'),
        original_memory_attribute_boundary=dict(entry='0x53894c',query='0x54bbd0',page_table_query='0x554ebc',root_global='0x14007c8',
            scope='Pinned original code would inspect software MMU tables and mapping attributes before returning a usable pointer; no current tables or mapping success supplied.'),
        public_format_reference=dict(url='https://raw.githubusercontent.com/ma1co/Sony-PMCA-RE/master/pmca/backup/__init__.py',
            use='Maintainer parser independently supports BK4 six-byte property entries, data-offset bounds and checksum excluding0x20..0x23. Original CP source and official bytes are primary for this checkpoint.',
            compatibility='No inference that PMCA updater/service execution is available on FX3; no upstream program run.'),
        sequential_file_read_adapter_used=False,real_configuration_copy_completed=False,real_buffer_or_MAIN_pixels_obtained=False,
        full_modified_firmware_emitted=False,flashable_package_produced=False,goal_complete=False,device_actions=0)
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(old),source_windows=len(fragments),candidate_CP_address=hex(candidate),
        matches_tomco_boundary=True,normal_boot_selection_proven=False,WBI_coverage=0,file_adapter_calls=0)))

if __name__=='__main__':main()
