#!/usr/bin/env python3
"""Infer a bounded header mask from observations, without guessing a body cipher."""
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import plistlib
import subprocess
import zlib

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entropy(data):
    counts = collections.Counter(data)
    return -sum(n / len(data) * math.log2(n / len(data)) for n in counts.values())


def linear_complexity(bits):
    # Binary Berlekamp-Massey recurrence fit; this infers a model from data.
    current = previous = 1
    degree = 0
    gap = 1
    for n, bit in enumerate(bits):
        discrepancy = bit
        for i in range(1, degree + 1):
            discrepancy ^= ((current >> i) & 1) * bits[n-i]
        if discrepancy:
            old = current
            current ^= previous << gap
            if 2 * degree <= n:
                degree, previous, gap = n + 1 - degree, old, 1
            else:
                gap += 1
        else:
            gap += 1
    return degree, [i for i in range(1, degree + 1) if current >> i & 1]


def sliding_runs(data, start, end):
    runs = []
    first = start
    for i in range(start, end-1):
        if (data[i+1] & 127) != data[i] >> 1:
            runs.append((first, i+1))
            first = i+1
    runs.append((first, end))
    return sorted(runs, key=lambda pair: pair[1]-pair[0], reverse=True)


def bit_sequence(data, lo, hi):
    return [(data[lo] >> k) & 1 for k in range(8)] + [data[i] >> 7 for i in range(lo+1, hi)]


def analyze(name, path, expected_sha):
    data = path.read_bytes()
    assert sha(data) == expected_sha
    assert data[4:10] == b'AXS-R7'
    header_start = 0x4c
    header_length = int.from_bytes(data[0x34:0x38], 'big')
    body_length = int.from_bytes(data[0x44:0x48], 'big')
    assert header_length == 1024
    header_end = header_start + header_length
    assert header_end + body_length + 16 == len(data)
    assert data[:4] == data[0x40:0x44]
    runs = sliding_runs(data, header_start, header_end)
    fitted = []
    for lo, hi in runs[:6]:
        bits = bit_sequence(data, lo, hi)
        assert len(bits) >= 64
        degree, taps = linear_complexity(bits[:64])
        mismatches = [n for n in range(64, len(bits)) if bits[n] != sum(bits[n-i] for i in taps) % 2]
        assert degree == 16 and taps == [11, 13, 14, 16] and not mismatches
        fitted.append({'start': lo, 'end_exclusive': hi, 'train_bits': 64, 'fit_degree': degree,
                       'taps': taps, 'held_out_bits': len(bits)-64, 'held_out_mismatches': len(mismatches)})
    # Use just the first 64 training bits from the longest run. The rest remain independent observations.
    lo, hi = runs[0]
    bits = bit_sequence(data, lo, hi)[:64]
    stream = {lo+i: bit for i, bit in enumerate(bits)}
    for i in range(lo-1, header_start-1, -1):
        stream[i] = stream[i+16] ^ stream[i+5] ^ stream[i+3] ^ stream[i+2]
    for i in range(max(stream)+1, header_end+7):
        stream[i] = stream[i-11] ^ stream[i-13] ^ stream[i-14] ^ stream[i-16]
    mask = bytes(sum(stream[i+j] << j for j in range(8)) for i in range(header_start, header_end))
    candidate = bytes(a ^ b for a,b in zip(data[header_start:header_end], mask))
    nonzero = [header_start+i for i, b in enumerate(candidate) if b]
    output = HERE / (name + '-bounded-header-candidate.bin')
    with output.open('xb') as out:
        out.write(candidate)
    markers = {}
    for label, magic in [('ELF', b'\x7fELF'), ('gzip', b'\x1f\x8b\x08'), ('XZ', b'\xfd7zXZ\0'),
                         ('SquashFS_LE', b'hsqs'), ('UBI', b'UBI#'), ('CPIO_newc', b'070701'),
                         ('BinaryPackProperty', b'BinaryPackProperty'), ('DATA23213', b'DATA23213')]:
        found = []
        at = 0
        while True:
            at = data.find(magic, at)
            if at < 0:
                break
            found.append(at)
            at += 1
        markers[label] = found
    gzip_results = []
    for offset in markers['gzip']:
        decoder = zlib.decompressobj(31)
        result = {'source_offset': offset, 'output_cap': 4*1024*1024, 'input_cap': 4*1024*1024}
        try:
            output_bytes = decoder.decompress(data[offset:offset+4*1024*1024], 4*1024*1024+1)
            result.update(output_bytes=len(output_bytes), eof=decoder.eof, within_output_cap=len(output_bytes)<=4*1024*1024)
            result['complete_valid_stream'] = decoder.eof and len(output_bytes)<=4*1024*1024
        except zlib.error as error:
            result.update(complete_valid_stream=False, error=str(error))
        gzip_results.append(result)
    return {'name': name, 'source': str(path.relative_to(HERE)), 'bytes': len(data), 'sha256': expected_sha,
            'version_bytes_ascii': data[0x48:0x4c].decode('ascii'), 'clear_header_bytes': header_start,
            'raw_field_0x00_equals_0x40': True, 'bounded_header_candidate_start': header_start,
            'bounded_header_candidate_bytes': header_length, 'declared_body_bytes_field_0x44': body_length,
            'body_candidate_offset': header_end, 'trailer_candidate_bytes': 16, 'total_length_relation_matches': True,
            'independent_run_fits': fitted, 'candidate_path': output.name, 'candidate_sha256': sha(candidate),
            'candidate_nonzero_byte_count': len(nonzero), 'candidate_nonzero_source_offsets': nonzero,
            'candidate_scope': 'Only this 1024-byte prefix was transformed; isolated residual bytes have not been assigned a field/key/IV meaning. No body decryption or signing.',
            'raw_prefix_sliding_relation_matches': sum((data[i+1]&127)==data[i]>>1 for i in range(header_start,header_end-1)),
            'raw_prefix_sliding_relation_pairs': header_length-1,
            'raw_body_first_1MiB_entropy': entropy(data[header_end:header_end+1048576]),
            'raw_selected_magic_offsets': markers, 'bounded_gzip_checks': gzip_results,
            'body_or_private_loader_readable': False}


def main():
    assert not (HERE / 'structure-analysis.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    old = json.loads((HERE / 'acquisition-current-etag-receipt.json').read_text())
    new = json.loads((HERE / 'AXS601-local-verification.json').read_text())
    assert old['result'] == 'COMPLETE_AXS_MEMBER_CRC_AND_ADJACENT_MD5_VERIFIED'
    assert new['result'] == 'COMPLETE_OFFICIAL_ZIP_CRC_AND_FIRMWARE_MD5_VERIFIED'
    rows = [analyze('AXS600', HERE / old['extracted'][0]['path'], old['extracted'][0]['sha256']),
            analyze('AXS601', HERE / new['firmware_path'], new['firmware_sha256'])]
    # A direct, bounded format comparison with an existing original VENICE inner; no mask/cipher is applied to it.
    venice = HERE.parent / 'donor-loader-20261029/outer-members/VENICE/DATA23213'
    with venice.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest() == '498d047ca2f6f11d54c502a399e2c5a9f4740e6fae4913eba1aaaf486349c785'
    with venice.open('rb') as stream:
        prefix = stream.read(1100)
    comparison = {'source': str(venice.relative_to(HERE.parent)), 'type': 'VENICE V2.01 type3 inner',
                  'source_sha256': '498d047ca2f6f11d54c502a399e2c5a9f4740e6fae4913eba1aaaf486349c785',
                  'compared_span_start': 0x4c, 'compared_span_bytes': 1024,
                  'sliding_relation_matches': sum((prefix[i+1]&127)==prefix[i]>>1 for i in range(0x4c,1099)),
                  'sliding_relation_pairs': 1023, 'AXS_clear_product_prefix_matches': prefix[4:10] == b'AXS-R7',
                  'AXS_mask_or_cipher_attempted': False,
                  'scope': 'The observed AXS padded-prefix pattern is not assumed to be a VENICE type3 format or a successful VENICE decoding.'}
    result = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'firmware_samples': rows,
              'inferred_recurrence': 's[n]=s[n-11]^s[n-13]^s[n-14]^s[n-16], byte mask is an eight-bit sliding window',
              'hypothesis': 'Long sliding-window runs in a bounded prefix expose a linear mask under a zero-padding hypothesis. Independent held-out predictions fit. This is a data model, not an original loader contract or identification of the body cipher.',
              'VENICE_direct_comparison': comparison, 'VENICE_or_FX5_private_ISP_recovered': False,
              'private_signing_key_operations': False, 'body_cipher_guesses_or_trials': False,
              'modified_firmware_created': False, 'vendor_program_execution': False, 'device_actions': 0}
    (HERE / 'structure-analysis.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'samples':len(rows), 'held_out_predictions':sum(r['held_out_bits'] for x in rows for r in x['independent_run_fits']),
                      'candidate_nonzero_counts':[x['candidate_nonzero_byte_count'] for x in rows],
                      'VENICE_relation_matches':comparison['sliding_relation_matches'], 'body_readable':False}))


if __name__ == '__main__':
    main()
