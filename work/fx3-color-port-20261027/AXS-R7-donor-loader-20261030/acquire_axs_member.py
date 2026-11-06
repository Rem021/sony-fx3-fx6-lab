#!/usr/bin/env python3
"""Read one whole stored public ZIP member plus its adjacent MD5, never flash it."""
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import zlib

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'Pro-catalog-sources-20261030'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert sys.argv[1:] in ([], ['--observed-full-range-etag'])
    follow_current = bool(sys.argv[1:])
    receipt_name = 'acquisition-current-etag-receipt.json' if follow_current else 'acquisition-receipt.json'
    assert not (HERE / receipt_name).exists(), 'Do not repeat completed acquisition'
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    metadata = json.loads((PREV / 'combo-zip-inspection.json').read_bytes())
    observations = json.loads((PREV / 'combo-member-prefixes-prefix-etag.json').read_bytes())
    prefix = next(r for r in observations['records'] if r['member_basename'] == 'AXS-R7_V600_firmware.f.bin')
    assert prefix['http_status'] == 206 and prefix['response_ETag_matches_requested']
    old_prefix = (PREV / prefix['path']).read_bytes()
    assert sha(old_prefix) == prefix['sha256']
    etag = prefix['response_ETag']
    if follow_current:
        first = json.loads((HERE / 'acquisition-receipt.json').read_text())
        assert first['http_status'] == 412 and first['requested_range'] == 'bytes=321079-29651863'
        etag = first['headers']['ETag']
        assert etag and etag != first['If_Match']
    members = [r for r in metadata['members'] if r['name'].endswith(('AXS-R7_V600_firmware.f.bin', 'AXS-R7_V600_firmware.f.md5'))]
    assert len(members) == 2 and all(r['compression_method'] == 0 and not r['flags'] & 1 for r in members)
    start = members[0]['local_header_offset']
    following = next(r['local_header_offset'] for r in metadata['members'] if r['local_header_offset'] > members[1]['local_header_offset'])
    end = following - 1
    length = end - start + 1
    assert 0 < length <= 32 * 1024 * 1024
    record = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_url': metadata['encoded_request_url'],
              'If_Match': etag, 'If_Match_source': 'Full-range 412 response just observed in this stage' if follow_current else 'Previously captured member prefix',
              'requested_range': f'bytes={start}-{end}', 'requested_bytes': length,
              'whole_archive_downloaded': False, 'whole_archive_identity_proven': False, 'vendor_execution': False, 'device_actions': 0}
    request = urllib.request.Request(metadata['encoded_request_url'], headers={
        'User-Agent': 'FirmwareCatalogResearch/1.0', 'Accept-Encoding': 'identity',
        'Range': record['requested_range'], 'If-Match': record['If_Match']})
    try:
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            record.update(http_status=response.code, final_url=response.url,
                          headers={k: v for k, v in response.headers.items() if k.lower() in ['content-range','content-length','etag','date','content-type']})
            if response.code != 206:
                body = response.read(4096)
                record.update(result='PRECONDITION_OR_RANGE_GAP', error_body_bytes=len(body), error_body_sha256=sha(body))
            else:
                assert response.headers.get('ETag') == record['If_Match']
                assert response.headers.get('Content-Range') == f'bytes {start}-{end}/{metadata["remote_archive_bytes"]}'
                raw = response.read(length + 1)
                assert len(raw) == length
                range_path = HERE / 'AXS-R7-member-and-md5.range.bin'
                with range_path.open('xb') as out:
                    out.write(raw)
                record.update(range_path=range_path.name, range_bytes=len(raw), range_sha256=sha(raw), previous_prefix_byte_identical=raw[:len(old_prefix)] == old_prefix)
                extracted = []
                for member in members:
                    relative = member['local_header_offset'] - start
                    fields = struct.unpack_from('<4s5H3I2H', raw, relative)
                    assert fields[0] == b'PK\x03\x04' and fields[2] == member['flags'] and fields[3] == 0
                    assert fields[6] == int(member['declared_CRC32'], 0)
                    assert fields[7] == fields[8] == member['uncompressed_bytes']
                    n, x = fields[9], fields[10]
                    name = raw[relative+30:relative+30+n]
                    assert name == member['name'].encode('cp437')
                    data_start = relative + 30 + n + x
                    payload = raw[data_start:data_start+fields[8]]
                    assert len(payload) == fields[8] and zlib.crc32(payload) == fields[6]
                    basename = member['name'].rsplit('/', 1)[-1]
                    path = HERE / basename
                    with path.open('xb') as out:
                        out.write(payload)
                    extracted.append({'path': basename, 'bytes': len(payload), 'sha256': sha(payload), 'CRC32': f'{fields[6]:08x}', 'CRC32_verified': True,
                                      'member_header_offset_within_range': relative, 'payload_offset_within_range': data_start,
                                      'local_header_and_prior_directory_fields_match': True})
                firmware = (HERE / extracted[0]['path']).read_bytes()
                md5_text = (HERE / extracted[1]['path']).read_text('ascii')
                declared_md5 = md5_text.split()[0].lower()
                assert len(declared_md5) == 32 and all(c in '0123456789abcdef' for c in declared_md5)
                actual_md5 = hashlib.md5(firmware, usedforsecurity=False).hexdigest()
                assert declared_md5 == actual_md5
                record.update(result='COMPLETE_AXS_MEMBER_CRC_AND_ADJACENT_MD5_VERIFIED', extracted=extracted,
                              firmware_md5=actual_md5, adjacent_md5_text=md5_text,
                              complete_firmware_member_acquired=True, private_loader_or_ISP_readability_proven=False)
    except Exception as error:
        record.update(result='ACQUISITION_OR_VALIDATION_GAP', error={'type': type(error).__name__, 'message': str(error)})
    (HERE / receipt_name).write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k in ['result','http_status','error','range_bytes','complete_firmware_member_acquired','firmware_md5']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
