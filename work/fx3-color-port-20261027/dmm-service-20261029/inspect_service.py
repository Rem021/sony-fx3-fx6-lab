#!/usr/bin/env python3
"""Pin original receiver/configuration sources and audit complete-goal gates."""
import datetime,hashlib,json,re,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
sys.path.insert(0,str(HERE))
from service_guest import image,BASE,PIN

WINDOWS=[(0x4d77e4,0x4d782a),(0x49ef00,0x49f00a),(0x49f368,0x49f5a0),
 (0xa874e2,0xa8750e),(0xab95e0,0xab9636),(0xa87b3c,0xa87b4e),
 (0xab71cc,0xab72ac),(0xab6190,0xab6284),(0xab9830,0xab988e),
 (0xab9e28,0xab9ef4),(0xaba7b6,0xaba842),(0xab60ae,0xab60c0),
 (0x4d7a84,0x4d7b40),(0xa84be8,0xa84c3c),(0xa85174,0xa85254)]

def pin(path):
    raw=path.read_bytes();return dict(path=str(path.relative_to(TASK)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main():
    assert not (HERE/'source-and-goal-review.json').exists()
    previous=TASK/'dmm-request-20261029/final-receipt.json'
    assert hashlib.sha256(previous.read_bytes()).hexdigest()=='8a51be060874e07da4133944125a6beb6b83c377bc699570d2b15dbe625c73d2'
    old=json.loads(previous.read_text())['files']
    for row in old:
        b=(previous.parent/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    raw=image();folder=HERE/'source-fragments';folder.mkdir(exist_ok=True)
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);md.skipdata=True;fragments=[]
    for a,z in WINDOWS:
        b=raw[a-BASE:z-BASE];file=folder/f'{a:08x}-{z:08x}.txt'
        file.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:12} {i.op_str}' for i in md.disasm(b,a))+'\n')
        fragments.append(dict(va=hex(a),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),listing=str(file.relative_to(HERE))))
    table_va=0xd11f94;table_bytes=raw[table_va-BASE:table_va-BASE+46*4]
    table=list(struct.unpack('<46I',table_bytes));assert table[0x20]==0xab6191
    table_file=folder/'00d11f94-dispatch-table.json'
    table_file.write_text(json.dumps(dict(va=hex(table_va),bytes=len(table_bytes),sha256=hashlib.sha256(table_bytes).hexdigest(),
        entries=[dict(message_type=hex(i),original_thumb_pointer=hex(v)) for i,v in enumerate(table)]),indent=2)+'\n')
    public=json.loads((HERE/'public-source-readback.json').read_text())
    pages={r['name']:r for r in public['records']}
    no_update='現在、本ページで提供されているアップデート情報はありません。'
    for name in ['fx5-jp-support','fx5-jp-downloads']:
        r=pages[name];assert r['status']==200 and no_update in (HERE/r['text_file']).read_text()
    # Keep the first capture and its incorrectly UTF-8-decoded text unchanged.
    # The official VENICE page declares Shift_JIS; decode its saved bytes anew.
    vraw=(HERE/pages['venice2-jp-update']['file']).read_bytes()
    assert re.search(rb'charset\s*=\s*["\']?shift[_-]jis',vraw,re.I)
    from capture_public import Page
    parser=Page();parser.feed(vraw.decode('cp932'))
    corrected=HERE/'public-pages/venice2-jp-update.corrected-text.txt'
    corrected.write_text('\n'.join(parser.text)+'\n')
    vtext=corrected.read_text();assert 'Ver. 5.00' in vtext and '2026年7月' in vtext and '862,640,780' in vtext
    oss=pages['fx5-oss'];assert oss['status']==200
    archive_links=[u for u in oss['download_or_package_links'] if re.search(r'\.(?:tar\.(?:xz|gz|bz2)|tgz)$',u,re.I)]
    artifacts=[pin(TASK/p) for p in ['input-20261028/validation-results.json','input-20261028/final-receipt.json',
        'transport-20261029/verification-contract-review.json','transport-20261029/final-receipt.json',
        'donor-20261028/donor-inner-source-inventory.json','donor-20261028/final-receipt.json']]
    originals=json.loads((TASK/'donor-20261028/donor-inner-source-inventory.json').read_text())['files']
    donor_pins=[]
    for row in originals:
        p=Path(row['path']);b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
        donor_pins.append({k:row[k] for k in ('version','path','bytes','sha256')})
    out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cp_sha256=PIN,
        previous_sealed_files_verified=len(old),source_fragments=fragments,
        queue_binding=dict(queue_ID='0x61003c',registration_entry='0x4d77e4',registration_API='0x49ef00',
            stored_handle='0x13f8fd8',original_queue_dispatch_wrapper='0xa874e3',original_callback='0xab95e1',
            dispatcher_entry='0xab71cc',evidence='Original registration and separate original callback prefix executed in bounded RAM; full normal send stopped before kernel thread identity.',
            normal_boot_and_real_send_proven=False),
        static_message_dispatch=dict(executed=False,table_va=hex(table_va),entry_count=46,table_sha256=hashlib.sha256(table_bytes).hexdigest(),
            request_type='0x20',original_handler='0xab6191',table_file=str(table_file.relative_to(HERE)),
            dispatcher_copies_request_bytes=40,dispatcher_request_frame_offset='0xc',
            handler_observations=['Reply type request_type|0x8000; client0x20 corresponds to0x8020.',
                'Request u16+0x14 copied through frame+0x20 to reply u16+6.',
                'Request u32+4 through frame+0x10 supplies unit/type key0x4af to0xab9830.',
                'Request u16+0x16 through frame+0x22 is masked by0x10f; values0,1,4 can reach0xab9830.',
                'With appropriate returned handle/mode,0xab9e28 formats count and64-bit base+offset plus size into16-byte records. These have not been returned by a real provider.'],
            distinction='Static handler and extent layout, not executed allocation, valid handle, recovered live physical address or sensor pixel data.'),
        static_configuration_dependency=dict(executed=False,unit_list_initializer='0xaba7b6',unit_key_table_RAM='0x1fba6d0',
            extent_ID_list_RAM='0x1fbc6d0',unit_list_pointer_global='0x13f8ff4',
            read_thunk='0xab60ae -> 0x4d7a84',parameter_key='0xfa0182',parameter_query='0xa84be8',
            read_offset_global='0x13f8ffc',physical_range_translation_table='0xb54930',
            evidence='Original initializer reads key/list records through GetConfigData; its raw source is a64-bit parameter value, range-translated and converted by0x53894c before stream copies.',
            scope='These RAM addresses are beyond this flat CP file; no populated unit0x4af configuration or physical pool is inferred from addresses alone.'),
        public_readback=dict(official_FX5_support_and_downloads_200_no_update=True,
            wording=no_update,scope='Only the inspected Japanese pages currently state no update information. Not global/repair-channel absence.',
            FX5_OSS_archive_links=len(archive_links),FX5_complete_proprietary_image_obtained=False,
            VENICE2_official_version='5.00',VENICE2_release='2026-07',VENICE2_listed_bytes=862640780,
            venice_text_correction=dict(saved_raw_unchanged=True,initial_UTF8_text_preserved=True,correct_encoding='cp932/Shift_JIS',file=str(corrected.relative_to(HERE)),sha256=hashlib.sha256(corrected.read_bytes()).hexdigest()),
            FX5B_failed_request='SSL EOF; no absence inference'),
        existing_evidence_pins=artifacts,original_donor_payloads_rehashed=donor_pins,
        complete_goal_gates=[
            dict(gate='FX5 full private menus/applications and dependencies',passed=False,evidence='Public OSS and inspected no-update pages do not supply full proprietary image.'),
            dict(gate='VENICE full RAW/sensor calibration/WB/demosaic/NR/ISP chain',passed=False,evidence='Original three DATA23213 payloads remain opaque; existing ART/monitor coefficient matches are partial.'),
            dict(gate='FX3 MAIN pixel binding and physical buffer provider',passed=False,evidence='Normal receiver is now linked; actual unit0x4af config, scheduler/kernel state, allocation and MAIN pixel path remain unproven.'),
            dict(gate='Whole professional menu and function transplant',passed=False,evidence='No full donor system or integrated implementation.'),
            dict(gate='Modified package admission and normal boot/recovery',passed=False,evidence='Earlier official package signatures verified and mutations rejected; USB/UUD verification is historical2.04/2.05 evidence. No current7.02 modified-package admission, boot or independent recovery receipt.')],
        next_research='Trace parameter0xfa0182 normal producer and unit-list stream source, rather than fabricating provider replies; retain full donor/signature/boot gates.',
        full_modified_firmware_emitted=False,flashable_package_produced=False,goal_complete=False,
        device_actions=0,sony_native_programs_executed=0,private_signing_material_read_or_derived=False)
    (HERE/'source-and-goal-review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(source_windows=len(fragments),dispatch_entries=len(table),previous_files_verified=len(old),donor_originals_rehashed=len(donor_pins),FX5_OSS_archives=len(archive_links),full_goal_gates_passed=0)))

if __name__=='__main__':main()
