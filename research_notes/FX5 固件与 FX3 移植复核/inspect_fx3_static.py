from pathlib import Path
import hashlib, json, plistlib, re, struct, subprocess

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024')
OUT = Path(__file__).parent
volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert volume['MountPoint'] == '/Volumes/KAFU2T'

FILES = {
    'av-cam': ('stage2/extraction/files/nflasha3/av-cam.bin', '0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'),
    'libmpr': ('stage2/extraction/files/nflasha15/lib/libmpr.so', '9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'),
    'appFw': ('stage2/extraction/files/nflasha15/lib/appFw.so', '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'),
    'dmm': ('stage128-DMM-provider-and-config/inputs/dmm.ko', '1e28a4921b36cd8866330a6670d72627d347c556dbea8568cd5b3ab60853e65a'),
    'AP_DmmCfg': ('stage129-AP-DMM-config-and-device-trial-plan/inputs/AP-DmmCfg.bin', '48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1'),
}

def elf_symbols(b):
    if b[:6] != b'\x7fELF\x02\x01': return []
    e = struct.unpack_from('<16sHHIQQQIHHHHHH', b)
    sections = [struct.unpack_from('<IIQQQQIIQQ', b, e[6]+i*e[11]) for i in range(e[12])]
    result = []
    for sec in sections:
        if sec[1] not in (2,11): continue
        strtab = sections[sec[6]]
        st = b[strtab[4]:strtab[4]+strtab[5]]
        for p in range(sec[4], sec[4]+sec[5], sec[9]):
            name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', b, p)
            end = st.find(b'\0', name)
            text = st[name:end].decode('ascii', 'replace')
            if re.search(r'GetDmm|SetMemTbl|UnitTypeTableSelect|FreeDmmMemory|raw.*output|raw.*capture|sensor|cache.*flush|dma.*map', text, re.I):
                result.append({'name': text, 'value': hex(value), 'size': size, 'defined': shndx != 0, 'table_type': sec[1]})
    return result

buckets = {
    'DMM': r'GetDmm|SetMemTbl|STILLMP_BUF_RAW_UNPACKED',
    'still_RAW': r'StillMP_Sequence_.*RAW|ConfluenceRaw',
    'HDMI_RAW': r'HDMI.*RAW|RAW.*HDMI|RAW_OUTPUT|RawOutput',
    'cinema_menu': r'CINE_EI|CINEEI|MOVIE_MAIN_MENU|MAIN_MENU.*MOVIE|BIG6',
    'sensor': r'CMOS|SENSOR.*READ|READ.*SENSOR|DEBAYER|DEMOSAIC',
}

receipt = {'scope': 'Offline fixed-file hashes, ELF symbol tables and bounded printable-string inventory only. No call-graph completeness, live hardware, sensor data or runtime support claim.', 'files': {}}
receipt['source_containers'] = []
for name, expected in [('fx3-7.02-BODYDATA.DAT', 'f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854'), ('fx3-7.02-decrypted.fdat', '694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768')]:
    with (ROOT/name).open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    assert digest == expected
    receipt['source_containers'].append({'path': str(ROOT/name), 'sha256': digest, 'bytes': (ROOT/name).stat().st_size})
for label, (rel, expected) in FILES.items():
    b = (ROOT/rel).read_bytes()
    digest = hashlib.sha256(b).hexdigest()
    assert digest == expected, (label, digest)
    strings = [(m.start(), m.group().decode()) for m in re.finditer(rb'[\x20-\x7e]{7,300}',b)]
    item = {'path': str(ROOT/rel), 'bytes': len(b), 'sha256': digest, 'symbols': elf_symbols(b), 'string_buckets': {}}
    for category, pattern in buckets.items():
        matches = [{'file_offset':hex(offset),'text':text} for offset,text in strings if re.search(pattern,text,re.I)]
        item['string_buckets'][category] = {'pattern':pattern,'total':len(matches),'first_matches':matches[:30]}
    receipt['files'][label] = item

ap = json.loads((ROOT/'stage148-initial-MSC-handler-inventory/AP-handler-inventory.json').read_text())
receipt['existing_AP_image_inventory'] = {k: ap[k] for k in ['source_image','source_image_sha256','regular_entries','unique_ELF_inodes']}
receipt['existing_AP_image_inventory']['selected_records'] = [x for x in ap['ELF_records'] if any(re.search(r'EXTERNAL_RAW|libmpr|dmm.ko', p, re.I) for p in x['image_paths'])]
(OUT/'fx3-static-chain-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
for label,item in receipt['files'].items():
    print(label, item['sha256'], {k:v['total'] for k,v in item['string_buckets'].items()})
    print(json.dumps(item['symbols'][:15],ensure_ascii=False))
print('WROTE',OUT/'fx3-static-chain-receipt.json')
