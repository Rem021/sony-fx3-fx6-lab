#!/usr/bin/env python3
"""Original flat-image initializer and memcpy in a bounded CPU-only guest."""
import hashlib
import json
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from extract_color_tables import read_image, descriptors, BASE, HERE


def main():
    image = read_image()
    records = descriptors(image)
    by_offset = {r['descriptor_offset']: r for r in records.values()}
    stack, sentinel = 0x50000000, 0x60000000
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(BASE, (len(image) + 4095) & ~4095)
    uc.mem_write(BASE, image)
    uc.mem_map(stack, 0x10000)
    uc.mem_map(sentinel, 0x1000)
    uc.mem_write(stack, b'\xa7' * 0x10000)
    uc.reg_write(R.UC_ARM64_REG_SP, stack + 0xf000)
    uc.reg_write(R.UC_ARM64_REG_LR, sentinel)
    saved = {getattr(R, f'UC_ARM64_REG_X{i}'): 0x7777000000000000 + i for i in range(19, 30)}
    for reg, val in saved.items():
        uc.reg_write(reg, val)
    copies, violations, configuration_writes = [], [], []
    count = [0]

    def on_code(u, address, size, user):
        count[0] += 1
        if address == sentinel:
            u.emu_stop()
            return
        off = address - BASE
        if not (0x2baf00 <= off < 0x2c278c or 0xd80 <= off < 0x1060):
            violations.append({'unexpected_code': hex(address)})
            u.emu_stop()
            return
        if off == 0xd80:
            dst, src, n = [u.reg_read(reg) for reg in [R.UC_ARM64_REG_X0, R.UC_ARM64_REG_X1, R.UC_ARM64_REG_X2]]
            assert n == 152
            copies.append(dict(caller=hex(u.reg_read(R.UC_ARM64_REG_LR) - BASE - 4),
                               dst=hex(dst - BASE), src=hex(src - BASE), size=n,
                               name=by_offset.get(src - BASE, {}).get('name')))

    def on_write(u, access, address, size, value, user):
        if BASE + 0xbb5044 <= address and address + size <= BASE + 0xbb51b0:
            configuration_writes.append(dict(offset=hex(address-BASE), size=size, value=value,
                                             pc=hex(u.reg_read(R.UC_ARM64_REG_PC)-BASE)))
        elif not (BASE + 0xae0000 <= address and address + size <= BASE + 0xb40000
                or stack <= address and address + size <= stack + 0x10000):
            violations.append({'unexpected_write': hex(address), 'size': size, 'pc': hex(u.reg_read(R.UC_ARM64_REG_PC)-BASE), 'value': value})
            u.emu_stop()

    uc.hook_add(UC_HOOK_CODE, on_code)
    uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
    for entry in [0x2baf00, 0x2bc100, 0x2bc330]:
        uc.reg_write(R.UC_ARM64_REG_LR, sentinel)
        uc.emu_start(BASE + entry, sentinel + 4, count=500000)
        assert not violations, violations
        assert uc.reg_read(R.UC_ARM64_REG_PC) == sentinel
        assert uc.reg_read(R.UC_ARM64_REG_SP) == stack + 0xf000
        assert all(uc.reg_read(reg) == val for reg, val in saved.items())
    for c in {c['dst']: c for c in copies}.values():
        src, dst = int(c['src'], 16), int(c['dst'], 16)
        assert bytes(uc.mem_read(BASE + dst, 152)) == image[src:src + 152]
    venice = [c for c in copies if 'VENICE' in str(c['name'])]
    # Measured initializer does NOT consume the named VENICE matrix record.
    # Retain this counterexample rather than interpreting all 30 labels as one pipeline.
    unused_matrix = 'MLUT_MTX_A_REG_VENICE_LMX0_SLOG3_SGAMUT3_ACES'
    expected = {name for name in records if 'VENICE' in name} - {unused_matrix}
    assert {c['name'] for c in venice} == expected
    assert len(venice) == 29
    initialized = bytes(uc.mem_read(BASE + 0xae0000, 0x60000))
    (HERE / 'initialized-profile-region.bin').write_bytes(initialized)
    matrix_record = records[unused_matrix]
    actual_matrix = records['MLUT_MTX_A_REG_SG3TOAP1_0']
    assert matrix_record['words'] == actual_matrix['words']
    assert any(c['name'] == actual_matrix['name'] and c['dst'] == '0xb07ba0' for c in copies)
    result = dict(status='PASS_ORIGINAL_INITIALIZER_AND_ORIGINAL_MEMCPY',
                  instructions=count[0], initializer_offsets=['0x2baf00', '0x2bc100', '0x2bc330'], initializer_end='0x2c278c',
                  original_memcpy_offset='0xd80',
                  initializer_sha256=hashlib.sha256(image[0x2baf00:0x2c278c]).hexdigest(),
                  copies=copies, copied_venice_descriptors=venice,
                  named_matrix_not_copied_by_these_initializers=unused_matrix,
                  equivalent_matrix_descriptor_used='MLUT_MTX_A_REG_SG3TOAP1_0',
                  equivalent_matrix_bytes_match=True,
                  initialized_region_sha256=hashlib.sha256(initialized).hexdigest(),
                  configuration_writes=configuration_writes,
                  stack_and_callee_saved_preserved=True, unexpected_writes=violations,
                  scope='CPU-only guest. Original descriptor initialization, not camera DSP writes or current record route.')
    (HERE / 'initializer-guest-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['copies', 'copied_venice_descriptors', 'configuration_writes']}, indent=2))
    print('copies', len(copies), 'VENICE descriptors', len(venice))


if __name__ == '__main__':
    main()
