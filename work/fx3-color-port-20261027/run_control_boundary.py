#!/usr/bin/env python3
"""Trace original look selector to its queue entry; never submit to hardware."""
import json
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from run_look_consumer import machine, STACK, DATA, STUB, STOP, BASE, HERE


def run(ip, look):
    u, image = machine()
    callback = STUB + 0x200
    table = DATA + 0x8000
    u.mem_write(BASE + 0x20, struct.pack('<Q', table))
    u.mem_write(table + 0x6b8, struct.pack('<Q', STUB))
    # This declared diagnostic-logging mode suppresses logging callbacks only.
    u.mem_write(BASE + 0xc148b8, struct.pack('<I', 3))
    u.reg_write(R.UC_ARM64_REG_X0, ip)
    u.reg_write(R.UC_ARM64_REG_X1, look)
    u.reg_write(R.UC_ARM64_REG_X2, callback)
    reached, pcs, external = [], [], []

    def code(u, pc, size, unused):
        if pc == STOP:
            u.emu_stop()
            return
        if pc == STUB:
            dst, byte, length = [u.reg_read(r) for r in [R.UC_ARM64_REG_X0, R.UC_ARM64_REG_X1, R.UC_ARM64_REG_X2]]
            assert STACK <= dst and dst + length <= STACK + 0x10000
            external.append(dict(provider='declared memset', size=length, byte=byte))
            u.mem_write(dst, bytes([byte & 255]) * length)
            u.reg_write(R.UC_ARM64_REG_PC, u.reg_read(R.UC_ARM64_REG_LR))
            return
        if pc == BASE + 0x2c4cc8:
            arg = u.reg_read(R.UC_ARM64_REG_X0)
            raw = bytes(u.mem_read(arg, 0x48))
            reached.append(dict(queue_entry_offset='0x2c4cc8', input_hex=raw.hex(),
                                command=struct.unpack_from('<I', raw, 0)[0],
                                look=struct.unpack_from('<I', raw, 4)[0],
                                ip=struct.unpack_from('<I', raw, 8)[0],
                                callback=hex(struct.unpack_from('<Q', raw, 16)[0]),
                                event_field=hex(struct.unpack_from('<I', raw, 24)[0])))
            u.emu_stop()
            return
        off = pc - BASE
        assert (0x2b5ffc <= off < 0x2b6110 or 0x2b8150 <= off < 0x2b815c
                or 0x2f67c <= off < 0x2f690 or 0xd80 <= off < 0x1060), hex(pc)
        pcs.append(off)

    def write(u, access, address, size, value, unused):
        assert STACK <= address and address+size <= STACK+0x10000, hex(address)

    u.hook_add(UC_HOOK_CODE, code)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(BASE + 0x2b5ffc, STOP+4, count=5000)
    if ip == 0 and look == 22:
        assert len(reached) == 1 and reached[0]['command'] == 0
        assert reached[0]['look'] == 22 and reached[0]['ip'] == 0
        assert reached[0]['callback'] == hex(callback)
        assert reached[0]['event_field'] == '0x2ae085a'
        status = 'REACHED_QUEUE_ENTRY_NOT_EXECUTED'
    else:
        assert not reached and u.reg_read(R.UC_ARM64_REG_PC) == STOP
        assert u.reg_read(R.UC_ARM64_REG_X0) & 0xffffffff == 0xfffffff3
        assert u.reg_read(R.UC_ARM64_REG_SP) == STACK+0xf000
        status = 'REJECTED_MINUS_13'
    return dict(ip_fixture=ip, look=look, status=status, instruction_count=len(pcs),
                declared_provider_calls=external, queue_checkpoint=reached,
                actual_enqueue_or_callback_completion=False)


def main():
    cases = [run(0, 22), run(0, 0), run(0, 30), run(1, 22)]
    result = dict(cases=cases, scope='Original look-setting front end to a queue-entry checkpoint, logging mode=3 and memset provider declared. No actual queue, OSAL resource, DMA, MAIN routing or output evidence.')
    (HERE/'control-boundary-guest-results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(cases, indent=2))


if __name__ == '__main__':
    main()
