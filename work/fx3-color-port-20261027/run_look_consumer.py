#!/usr/bin/env python3
"""Original lookup and DMA-list production. No hardware submission is executed."""
import hashlib
import json
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from extract_color_tables import read_image, BASE, HERE

STACK, DATA, STOP, STUB = 0x50000000, 0x51000000, 0x60000000, 0x61000000
VIRT_START, PHYS_START = 0xffffffc000000000, 0x400000000


def machine():
    image = read_image()
    init = (HERE / 'initialized-profile-region.bin').read_bytes()
    receipt = json.loads((HERE / 'initializer-guest-results.json').read_text())
    assert hashlib.sha256(init).hexdigest() == receipt['initialized_region_sha256']
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(BASE, (len(image) + 4095) & ~4095)
    u.mem_write(BASE, image)
    u.mem_write(BASE + 0xae0000, init)
    for address, size in [(STACK, 0x10000), (DATA, 0x10000), (STOP, 0x1000), (STUB, 0x1000)]:
        u.mem_map(address, size)
    u.mem_write(STACK, b'\xa7' * 0x10000)
    u.reg_write(R.UC_ARM64_REG_SP, STACK + 0xf000)
    u.reg_write(R.UC_ARM64_REG_LR, STOP)
    return u, image


def lookup_case(value):
    u, image = machine()
    u.mem_write(DATA, b'\x5a' * 64)
    u.reg_write(R.UC_ARM64_REG_X0, value & 0xffffffff)
    u.reg_write(R.UC_ARM64_REG_X1, DATA + 16)
    pcs = []
    def code(u, pc, size, user):
        if pc == STOP:
            u.emu_stop()
        else:
            assert BASE + 0x2c3334 <= pc < BASE + 0x2c33c4, hex(pc)
            pcs.append(pc - BASE)
    u.hook_add(UC_HOOK_CODE, code)
    u.emu_start(BASE + 0x2c3334, STOP + 4, count=2000)
    assert u.reg_read(R.UC_ARM64_REG_PC) == STOP
    raw = bytes(u.mem_read(DATA, 64))
    assert raw[:16] == raw[48:] == b'\x5a' * 16
    ret = u.reg_read(R.UC_ARM64_REG_X0)
    result = dict(input=value, returned=ret, instruction_count=len(pcs))
    if 1 <= value <= 29:
        assert ret == 1
        expected = image[0x38ada8 + (value - 1)*32:0x38ada8 + value*32]
        assert raw[16:48] == expected
        idx, ptr, count, name = struct.unpack('<4Q', expected)
        name_off = name - BASE
        result.update(index=idx, descriptors=hex(ptr - BASE), descriptor_count=count,
                      name=image[name_off:image.index(0, name_off)].decode())
    else:
        assert ret == 0 and raw[16:48] == b'\x5a' * 32
    assert u.reg_read(R.UC_ARM64_REG_SP) == STACK + 0xf000
    return result


def produce_case(ip, delta=0):
    u, image = machine()
    argument, output = DATA + 0x1000, BASE + 0xbb5d40
    n, first = 70, BASE + 0xb05638
    u.mem_write(argument, struct.pack('<IIQ', ip, n, first))
    u.mem_write(output - 16, b'\x5a' * (16 + n*16 + 16))
    # Declared providers in an isolated guest, dispatched through original stubs.
    provider_table = DATA + 0x8000
    u.mem_write(BASE + 0x20, struct.pack('<Q', provider_table))
    u.mem_write(provider_table + 0x610, struct.pack('<Q', STUB))
    u.mem_write(provider_table + 0x630, struct.pack('<Q', STUB + 0x100))
    u.reg_write(R.UC_ARM64_REG_X0, argument)
    u.reg_write(R.UC_ARM64_REG_X1, output)
    callbacks, flushes, pcs, writes = [], [], [], []
    def code(u, pc, size, user):
        if pc == STOP:
            u.emu_stop()
            return
        if pc == STUB + 0x100:
            v = u.reg_read(R.UC_ARM64_REG_X0)
            assert VIRT_START <= v < VIRT_START + 0x100000000
            declared = PHYS_START + v - VIRT_START + delta
            callbacks.append(dict(virtual=hex(v), declared_physical=hex(declared)))
            u.reg_write(R.UC_ARM64_REG_X0, declared)
            u.reg_write(R.UC_ARM64_REG_PC, u.reg_read(R.UC_ARM64_REG_LR))
            return
        if pc == STUB:
            flushes.append([hex(u.reg_read(R.UC_ARM64_REG_X0)), u.reg_read(R.UC_ARM64_REG_X1)])
            u.reg_write(R.UC_ARM64_REG_PC, u.reg_read(R.UC_ARM64_REG_LR))
            return
        off = pc - BASE
        assert 0x2c4794 <= off < 0x2c49c0 or 0x2b4268 <= off < 0x2b427c or 0x2f4d8 <= off < 0x2f53c, hex(pc)
        pcs.append(off)
    def write(u, access, address, size, value, user):
        assert (output <= address and address+size <= output+n*16
                or argument <= address and address+size <= argument+16
                or STACK <= address and address+size <= STACK+0x10000), (hex(address), size)
        writes.append([hex(address), size])
    u.hook_add(UC_HOOK_CODE, code)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(BASE + 0x2c4794, STOP + 4, count=50000)
    assert u.reg_read(R.UC_ARM64_REG_PC) == STOP
    raw = bytes(u.mem_read(output - 16, 16+n*16+16))
    assert raw[:16] == raw[-16:] == b'\x5a'*16
    lli = [list(struct.unpack_from('<4I', raw, 16+i*16)) for i in range(n)]
    assert len(flushes) == n and len(callbacks) == 3*n-1
    assert struct.unpack('<IIQ', bytes(u.mem_read(argument, 16))) == (ip, n, first+n*152)
    destinations = []
    for i, row in enumerate(lli):
        pointer, reg, count = struct.unpack('<QQI', bytes(u.mem_read(first+i*152, 20)))
        expected_source = (pointer - VIRT_START + delta) & 0xffffffff
        expected_next = 0 if i == n-1 else ((output+(i+1)*16 - VIRT_START+delta) & 0xfffffffe)
        expected_control = 0x0e489000 | (count & 4095) | (0x80000000 if i == n-1 else 0)
        assert row[0] == expected_source and row[2:] == [expected_next, expected_control], (i, row)
        destinations.append((row[1]-reg) & 0xffffffff)
    assert len(set(destinations)) == 1
    return dict(ip_fixture=ip, mapping_delta_fixture=delta,
                status='PASS_ORIGINAL_70_ENTRY_DMA_LIST' if ip == 0 else 'COUNTEREXAMPLE_NONZERO_IP_PRODUCES_ZERO_REGISTER_BASE',
                instruction_count=len(pcs), register_base_low32=hex(destinations[0]),
                descriptors=lli, normalization_provider_calls=len(callbacks),
                cache_provider_calls=len(flushes), guards_preserved=True,
                hardware_submission_executed=False,
                scope='Original CPU code produces linked list against declared virtual-to-physical/cache providers. No actual OSAL mapping or DMA transaction is proved.')


def main():
    lookup = [lookup_case(x) for x in [0, -1, *range(1, 30), 30]]
    cases = [produce_case(0, 0), produce_case(0, 64), produce_case(1, 0)]
    # Positive delta must alter addresses but cannot alter register destinations or transfer counts.
    for original, altered in zip(cases[0]['descriptors'], cases[1]['descriptors']):
        assert altered[0] == (original[0]+64) & 0xffffffff
        assert altered[1] == original[1] and altered[3] == original[3]
    result = dict(lookup=lookup, dma_list_cases=cases,
                  scope='No camera. No DMA submission, sensor access or active MAIN/monitor routing proof.')
    (HERE / 'look-consumer-guest-results.json').write_text(json.dumps(result, indent=2)+'\n')
    print('lookups', len(lookup), 'valid', sum(x['returned'] == 1 for x in lookup))
    print(json.dumps([{k:v for k,v in c.items() if k!='descriptors'} for c in cases], indent=2))


if __name__ == '__main__':
    main()
