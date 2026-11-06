#!/usr/bin/env python3
"""Cross-check original CP parsing against prior host decoder and pin boundaries."""
import ast,hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
sys.path.insert(0,str(HERE))
from extent_config_guest import Guest,image,BASE,PIN

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    target=HERE/'configuration-review.json';assert not target.exists()
    previous=TASK/'dmm-service-20261029/final-receipt.json'
    assert sha(previous.read_bytes())=='73fe9a2d770beb5481e6a2d48daeefb970c65cc11641b9ffd3b454dac53c6022'
    prev=json.loads(previous.read_text())['files']
    for r in prev:
        b=(previous.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    sibling=TASK.parent/'sony-firmware-20261024'
    old=sibling/'stage128-DMM-provider-and-config';ap=sibling/'stage129-AP-DMM-config-and-device-trial-plan'
    raw=(HERE/'original-files/DmmCfg.bin').read_bytes();assert raw==(old/'inputs/DmmCfg.bin').read_bytes()
    # Extract only the previously reviewed pure decoder AST. Do not import the
    # module's kernel/guest helpers or execute its main entry point.
    code=(old/'provider_audit.py').read_text();tree=ast.parse(code)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='decode_cfg')
    body=ast.get_source_segment(code,node);namespace={'struct':struct}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(old/'provider_audit.py'), 'exec'),namespace)
    decoded=namespace['decode_cfg'](raw)
    assert decoded==json.loads((old/'DmmCfg-decoded.json').read_text())
    (HERE/'host-decoder-source.txt').write_text(body+'\n')
    assert len(decoded['roots'])==1 and len(decoded['rules'])==164 and len(decoded['units'])==348
    g=Guest(image(),raw);assert g.call(0xab8b70)['raw_r0']=='0x0'
    assert g.call(0xaba7b6)['raw_r0']=='0x0' and g.offset==len(raw)
    expected=[(hex(u['unit_type']),[hex(v) for v in u['extent_types']]) for u in decoded['units']]
    assert [(r['key'],r['extent_IDs']) for r in g.unit_table()]==expected
    headers=records=0
    for kind,base in [('roots',0x1da78c8),('rules',0x1da7968)]:
        for index,group in enumerate(decoded[kind]):
            at=base+index*0x50;native=bytes(g.u.mem_read(at,0x50));source=bytes.fromhex(group['header_bytes'])
            assert native[4:]==source[4:],(kind,index)
            pointer=struct.unpack_from('<I',native)[0]
            for j,row in enumerate(group['rows']):
                a=int(row['offset'],16);assert bytes(g.u.mem_read(pointer+j*20,20))==raw[a:a+20],(kind,index,j)
                records+=1
            assert struct.unpack_from('<I',g.u.mem_read(pointer+len(group['rows'])*20,20),8)[0]==0xffffffff
            headers+=1
    selected=next(u for u in decoded['units'] if u['unit_type']==0x4af)
    assert selected['extent_types']==[0x62a]
    matches=[]
    for i,group in enumerate(decoded['rules']):
        for row in group['rows']:
            if row['words'][2]==0x62a:matches.append(dict(rule_index=i,header_offset=group['header_offset'],record_offset=row['offset'],raw_words=row['words']))
    assert len(matches)==2 and {r['rule_index'] for r in matches}=={1}
    apraw=(ap/'inputs/AP-DmmCfg.bin').read_bytes();assert sha(apraw)=='48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1'
    apdecoded=json.loads((ap/'AP-DmmCfg-decoded.json').read_text());assert len(apdecoded['units'])==603
    boot=(ap/'inputs/insmod_drv2').read_text();assert 'DMMCFG_FILE=/setting/DmmCfg.bin' in boot
    assert 'insmod /usr/kmod/dmm.ko DmmConfig=$DMMCFG_FILE' in boot
    rawcp=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);md.skipdata=True
    windows=[(0xab8b70,0xab8e9a),(0xaba7b6,0xaba842),(0xab9830,0xab988e),(0xab8e9a,0xab8f0a),
        (0xab75f6,0xab7874),(0x4982cc,0x498338),(0x4985c4,0x49863c),(0xa85174,0xa8527c),(0x4d7a84,0x4d7b40)]
    folder=HERE/'source-fragments';folder.mkdir(exist_ok=True);fragments=[]
    for a,z in windows:
        b=rawcp[a-BASE:z-BASE];file=folder/f'{a:08x}-{z:08x}.txt'
        file.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:12} {i.op_str}' for i in md.disasm(b,a))+'\n')
        fragments.append(dict(va=hex(a),bytes=len(b),sha256=sha(b),listing=str(file.relative_to(HERE))))
    address_table=rawcp[0xb54930-BASE:0xb54930-BASE+128]
    ranges=[list(struct.unpack_from('<4Q',address_table,i*32)) for i in range(4)]
    wbi=TASK.parent/'sony-firmware-20261024/stage2/extraction/nflasha5.img'
    wraw=wbi.read_bytes();assert sha(wraw)=='ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1'
    h=struct.unpack_from('<11Q',wraw);assert h[0]==int.from_bytes(b'WBI2','little') and h[1]==1399
    table=h[5]+h[6];sections=[struct.unpack_from('<8Q',wraw,table+i*64) for i in range(h[1])]
    candidate=0x804000000;assert not any(r[0]<=candidate<r[0]+r[4] for r in sections)
    domain=dict(WBI_sha256=sha(wraw),sections=len(sections),physical_min=hex(min(r[0] for r in sections)),
        physical_max_exclusive=hex(max(r[0]+r[4] for r in sections)),
        original_CP_static_range_table=[list(map(hex,r)) for r in ranges],CP_range_table_va='0xb54930',CP_range_table_sha256=sha(address_table),
        backup_initializer_argument='0x04000000',CP_backup_candidate_physical_from_static_range_table=hex(candidate),
        WBI_sections_covering_candidate=0,
        scope='Constant-table inference and stored-section bounds only. No live MMU mapping or normal CP backup producer is proved; AP WBI virtual/physical domains cannot be substituted for CP RAM.')
    source_pins=[]
    for p in [old/'README.md',old/'provider_audit.py',old/'DmmCfg-decoded.json',ap/'README.md',ap/'input-receipt.json',
              ap/'inputs/AP-DmmCfg.bin',ap/'inputs/insmod_drv2',ap/'AP-DmmCfg-decoded.json']:
        b=p.read_bytes();source_pins.append(dict(path=str(p),bytes=len(b),sha256=sha(b)))
    out=dict(previous_sealed_files_verified=len(prev),CP_sha256=PIN,CP_configuration_sha256=sha(raw),
        independent_oracle=dict(source='Previously completed stage128 pure host decoder; no old main rerun.',
            decoder_source_sha256=sha((body+'\n').encode()),original_group_headers_matched=headers,
            original_records_matched=records,all_original_units_matched=len(expected),consumed_bytes=g.offset,
            CP_version=decoded['version_ascii']),
        selected_unit=dict(unit=selected,matching_rule_records=matches),source_fragments=fragments,source_pins=source_pins,
        domain_separation=domain,
        reuse_and_novelty=dict(previously_completed='Stage128 extracted and host-decoded CP file; stage129 separated AP file and established its startup argument.',
            new='Execute original CP common/unit parsers and config lookup helpers; match every group/record/unit to prior independent host parse; bind this CP NRV unit0x4af to extent0x62a and its two source records.',
            AP_and_CP_configurations_interchangeable=False),
        normal_CP_boot_filename_parameter_binding_proven=False,unit_slot_or_image_allocation_executed=False,
        actual_frame_buffer_or_MAIN_pixels_obtained=False,full_modified_firmware_emitted=False,flashable_package_produced=False,
        firmware_source_originals_changed=False,native_Sony_programs_executed=0,device_actions=0,goal_complete=False)
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(original_headers_matched=headers,original_records_matched=records,original_units_matched=len(expected),
        consumed_bytes=g.offset,unit4af_extent62a_records=len(matches),CP_backup_WBI_coverage=0,previous_files_verified=len(prev))))

if __name__=='__main__':main()
