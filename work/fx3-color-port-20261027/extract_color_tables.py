#!/usr/bin/env python3
"""Read pinned FX3 7.02 flat image. Extract data; never connects to a device."""
from pathlib import Path
import csv
import hashlib
import json
import plistlib
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
IMAGE = HERE.parent / 'sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin'
BASE = 0xffffffc001000000
PIN = '0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'


def digest(b):
    return hashlib.sha256(b).hexdigest()


def read_image():
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    b = IMAGE.read_bytes()
    assert digest(b) == PIN
    assert struct.unpack_from('<Q', b, 0)[0] == BASE + 0x58
    return b


def descriptors(b):
    records = {}
    for m in re.finditer(rb'MLUT_[A-Z0-9_]+\0', b):
        off = m.start() - 20
        if off < 0 or off % 8:
            continue
        pointer, register, words = struct.unpack_from('<QQI', b, off)
        data_offset = pointer - BASE
        # Exclude the separate enable-table format, which has two pointers.
        if not (0 <= data_offset < len(b) and register < 0x10000 and 0 < words < 10000):
            continue
        assert data_offset + words * 4 <= len(b)
        assert b[m.end():off + 148] == bytes(off + 148 - m.end())
        name = m.group()[:-1].decode()
        raw = b[data_offset:data_offset + words * 4]
        records[name] = dict(name=name, descriptor_offset=off, data_pointer=hex(pointer),
                             data_offset=data_offset, register_offset=register, word_count=words,
                             byte_count=len(raw), sha256=digest(raw),
                             words=list(struct.unpack('<' + str(words) + 'I', raw)))
    return records


def halfwords(record):
    return [v for word in record['words'] for v in (word & 65535, word >> 16)]


def banks(records, flavor):
    if flavor == 'THRU':
        return {ch: [halfwords(records[f'MLUT_L3D_SRAM_{k}_{ch}_THRU']) for k in range(8)] for ch in 'RGB'}
    return {ch: [halfwords(records[f'MLUT_L3D_SRAM_{ch}_{k}_{flavor}']) for k in range(8)] for ch in 'RGB'}


def sample(bank_set, r, g, b):
    bank = ((r & 1) << 2) | ((g & 1) << 1) | (b & 1)
    address = (r // 2) * 100 + (g // 2) * 10 + b // 2
    return tuple(bank_set[ch][bank][address] for ch in 'RGB')


def csv_write(path, header, rows):
    with path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    b = read_image()
    records = descriptors(b)
    out = HERE / 'tables'
    out.mkdir(exist_ok=True)
    selected = {k: v for k, v in records.items() if 'VENICE' in k}
    assert len(selected) == 30
    # Same-image THRU/test controls independently constrain the interpretation.
    matrix_name = 'MLUT_MTX_A_REG_VENICE_LMX0_SLOG3_SGAMUT3_ACES'
    raw_matrix = selected[matrix_name]['words']
    identity = records['MLUT_MTX_A_REG_THRU']['words']
    test = records['MLUT_MTX_A_REG_TEST']['words']
    assert identity == [1, 0, 0, 0, 65536, 0, 0, 0, 65536, 0, 0, 0, 65536]
    assert test[4:] == [0x7ffff] * 9
    signed = [x - 0x80000 if x & 0x40000 else x for x in raw_matrix[4:]]
    assert all(x < 0x80000 for x in raw_matrix[4:])
    assert [sum(signed[k:k + 3]) for k in (0, 3, 6)] == [65536] * 3
    matrix = [signed[k:k + 3] for k in (0, 3, 6)]
    csv_write(out / 'venice_matrix_signed_q16.csv', ['row', 'column', 'raw_u19', 'signed', 'coefficient'],
              ([r, c, raw_matrix[4 + 3*r + c], matrix[r][c], matrix[r][c]/65536] for r in range(3) for c in range(3)))
    curves = {ch: halfwords(selected[f'MLUT_L1D_B_SRAM_{ch}_VENICE_L1D0_SLOG3_SGAMUT3_ACES']) for ch in 'RGB'}
    assert curves['R'] == curves['G'] == curves['B']
    assert len(curves['R']) == 512 and curves['R'][-1] == 0
    assert all(a <= z for a, z in zip(curves['R'][:-2], curves['R'][1:-1]))
    csv_write(out / 'venice_1d_packed_halfwords.csv', ['index', 'R', 'G', 'B'],
              ([i] + [curves[ch][i] for ch in 'RGB'] for i in range(512)))
    thru = banks(records, 'THRU')
    venice = banks(records, 'VENICE_3DLUT_SLOG3_SGAMUT3_ACES')
    thru_axes = records['MLUT_L3D_REG_THRU']['words'][11:]
    venice_axes = selected['MLUT_L3D_REG_VENICE_3DLUT_SLOG3_SGAMUT3_ACES']['words'][11:]
    assert len(thru_axes) == len(venice_axes) == 20
    checks = 0
    rows = []
    for r in range(20):
        for g in range(20):
            for bl in range(20):
                assert sample(thru, r, g, bl) == (thru_axes[r], thru_axes[g], thru_axes[bl])
                checks += 3
                rows.append([r, g, bl, venice_axes[r], venice_axes[g], venice_axes[bl], *sample(venice, r, g, bl)])
    csv_write(out / 'venice_3d_20x20x20_raw.csv', ['r_index', 'g_index', 'b_index', 'r_axis_raw', 'g_axis_raw', 'b_axis_raw', 'R_raw', 'G_raw', 'B_raw'], rows)
    for rec in selected.values():
        raw = b[rec['data_offset']:rec['data_offset'] + rec['byte_count']]
        (out / (rec['name'] + '.bin')).write_bytes(raw)
    all_descriptors = [{k: v for k, v in rec.items() if k != 'words'} for rec in records.values()]
    (HERE / 'descriptor-index.json').write_text(json.dumps(all_descriptors, indent=2) + '\n')
    result = dict(image=str(IMAGE), sha256=PIN, image_base=hex(BASE),
                  descriptor_candidate_format='<Q data_pointer, I register_offset, I reserved_zero, I word_count, char name[128], pad[4]>',
                  descriptor_count=len(records), venice_descriptor_count=len(selected),
                  matrix=dict(raw_words=raw_matrix, signed_q16=matrix,
                              coefficients=[[x/65536 for x in row] for row in matrix],
                              interpretation='signed 19-bit/Q16 inferred from same-image THRU and all-ones TEST; actual hardware consumer still to trace'),
                  one_d=dict(halfwords=512, channels_equal=True, tail_zero=True,
                             monotonic_excluding_final_padding=True, maximum=max(curves['R']),
                             input_sample_positions='not recovered; do not assume uniform or drop final element in hardware payload'),
                  three_d=dict(grid=[20, 20, 20], samples=8000, channel_checks_against_thru=checks,
                               bank='((r&1)<<2)|((g&1)<<1)|(b&1)',
                               local_index='(r//2)*100+(g//2)*10+b//2',
                               input_axes_raw=venice_axes,
                               output_ranges={ch: [min(v for bank in venice[ch] for v in bank), max(v for bank in venice[ch] for v in bank)] for ch in 'RGB'},
                               normalization_and_interpolator='not recovered; raw integer grid only'),
                  selected=selected,
                  limits=['No proof of active MAIN route or recovered camera input calibration.',
                          'No bootloader/service/camera/USB action.',
                          'VENICE name is a label for these stages, not a claim of full VENICE ISP.'])
    (HERE / 'extraction-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'selected'}, indent=2))


if __name__ == '__main__':
    main()
