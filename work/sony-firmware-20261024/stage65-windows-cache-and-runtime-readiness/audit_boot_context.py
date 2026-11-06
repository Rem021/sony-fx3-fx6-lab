#!/usr/bin/env python3
"""Original Image startup operands and five independent instructions only."""
import datetime
import json
import struct
import unicorn
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_PROT_READ, UC_PROT_EXEC
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
import unicorn.arm64_const as a
import prepare_handoff as h

K = h.prev.n.K
KERNEL_SHA = 'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'


def u32(raw, off):
    return struct.unpack_from('<I', raw, off)[0]


def adrp(raw, off, rd):
    word = u32(raw, off)
    assert word & 0x9f000000 == 0x90000000 and word & 31 == rd
    imm = ((word >> 29) & 3) | (((word >> 5) & 0x7ffff) << 2)
    if imm & (1 << 20):
        imm -= 1 << 21
    return ((K + off) & ~4095) + (imm << 12)


def add(raw, off, rd, rn):
    word = u32(raw, off)
    assert word & 0xff800000 == 0x91000000
    assert word & 31 == rd and (word >> 5) & 31 == rn
    return ((word >> 10) & 0xfff) << (12 if word & (1 << 22) else 0)


def component(raw, seed, sp, current):
    # This starts inside the original post-MMU startup path. It is not a reset
    # boot, Linux scheduling context, or permission to resume an OSAL request.
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    page = K + 0x5b0000
    uc.mem_map(page, 4096, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_write(page, raw[0x5b0000:0x5b1000])
    for index in range(29):
        uc.reg_write(getattr(a, 'UC_ARM64_REG_X' + str(index)), int.from_bytes(bytes([seed]) * 8, 'little'))
    before = {name: uc.reg_read(reg) for name, reg in
        [('SP', a.UC_ARM64_REG_SP), ('SP_EL0', a.UC_ARM64_REG_SP_EL0), ('PSTATE', a.UC_ARM64_REG_PSTATE)]}
    # Require the observed emulator default EL1h; never set PSTATE/SP_EL0.
    assert before['PSTATE'] & 15 == 5
    trace = []
    def code(m, address, size, _):
        assert size == 4 and address == K + 0x5b0188 + len(trace) * 4
        assert len(trace) < 5
        trace.append(hex(address))
    def store(*_):
        raise AssertionError('Five-instruction prefix must not write RAM')
    uc.hook_add(UC_HOOK_CODE, code)
    uc.hook_add(UC_HOOK_MEM_WRITE, store)
    uc.emu_start(K + 0x5b0188, K + 0x5b019c, count=6)
    assert len(trace) == 5 and uc.reg_read(a.UC_ARM64_REG_PC) == K + 0x5b019c
    assert uc.reg_read(a.UC_ARM64_REG_SP) == sp
    assert uc.reg_read(a.UC_ARM64_REG_SP_EL0) == current
    assert uc.reg_read(a.UC_ARM64_REG_PSTATE) == before['PSTATE']
    assert bytes(uc.mem_read(page, 4096)) == raw[0x5b0000:0x5b1000]
    return {'seed': hex(seed), 'before': {k: hex(v) for k, v in before.items()},
        'executed_pcs': trace, 'native_SP': hex(sp), 'native_SP_EL0': hex(current),
        'stopped_before_PC': hex(K + 0x5b019c), 'RAM_writes': 0,
        'host_wrote_SP_SP_EL0_PSTATE_or_return_adapters': False,
        'real_boot_MMU_scheduler_task_or_OSAL_request_continuation': False}


def main():
    h.im.volume()
    out = h.STAGE / 'boot-context-audit.json'
    assert not out.exists()
    path = h.prev.n.STAGE / 'official-files/nflasha3/vmlinux.bin'
    raw = path.read_bytes()
    assert h.im.sha(raw) == KERNEL_SHA
    assert len(raw) == 6610952
    header = struct.unpack_from('<IIQQQQQQII', raw)
    code0, code1, text_offset, image_size, flags, res2, res3, res4, magic, res5 = header
    assert (text_offset, image_size, flags, magic) == (0x80000, 0x6af000, 10, 0x644d5241)
    assert code1 == res2 == res3 == res4 == res5 == 0
    assert code0 & 0xfc000000 == 0x14000000
    delta = code0 & 0x3ffffff
    if delta & (1 << 25):
        delta -= 1 << 26
    assert delta * 4 == 0x5b0000
    sp = adrp(raw, 0x5b0188, 4) + add(raw, 0x5b018c, 31, 4)
    current = adrp(raw, 0x5b0190, 5) + add(raw, 0x5b0194, 5, 5)
    assert u32(raw, 0x5b0198) == 0xd5184105  # Original MSR SP_EL0, X5.
    assert sp == K + 0x604000 and current == K + 0x60c500 and current != sp
    bss_start = adrp(raw, 0x5b01d0, 0) + add(raw, 0x5b01d4, 0, 0)
    bss_end = adrp(raw, 0x5b01dc, 2) + add(raw, 0x5b01e0, 2, 2)
    assert bss_start == K + len(raw) and bss_end == K + 0x6a8874
    assert bss_start < bss_end < K + image_size
    assert u32(raw, 0x5b01d8) == 0xaa1f03e1  # Original MOV X1, XZR.
    bl = u32(raw, 0x5b01e8)
    assert bl & 0xfc000000 == 0x94000000
    rel = bl & 0x3ffffff
    if rel & (1 << 25):
        rel -= 1 << 26
    assert K + 0x5b01e8 + rel * 4 == K + 0x1f0180
    current_off = current - K
    assert u32(raw, current_off + 0x10) == 1
    irq = h.prev.n.K + 0x423de8
    assert u32(raw, 0x423df4) == 0xb9401041
    runs = [component(raw, x, sp, current) for x in (0xa5, 0xc3)]
    h.im.write_json(out, {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'ORIGINAL_IMAGE_STARTUP_OPERANDS_AND_INDEPENDENT_FIVE_INSTRUCTION_PREFIX',
        'kernel_sha256': KERNEL_SHA, 'source_script_sha256': h.im.sha(h.STAGE.joinpath('audit_boot_context.py').read_bytes()),
        'kernel_model_base': hex(K), 'model_base_is_not_observed_camera_mapping': True,
        'header': {'text_offset': hex(text_offset), 'image_size': hex(image_size), 'file_bytes': len(raw),
            'flags': flags, 'endianness': 'little', 'page_size': 4096, 'entry_branch_file_offset': '0x5b0000'},
        'initial_stack': hex(sp), 'original_startup_current_context': hex(current),
        'current_context_original_128_bytes': raw[current_off:current_off+128].hex(),
        'lock_reads_and_updates_context_plus10': {'original_lock_entry': hex(irq),
            'original_LDR_address': hex(K + 0x423df4), 'file_initial_u32': 1,
            'structure_name_and_full_ABI_not_inferred_from_plain_4_9_headers': True},
        'original_BSS_clear_operands_not_executed': {'start': hex(bss_start), 'end_exclusive': hex(bss_end),
            'bytes': bss_end-bss_start, 'fill': 0, 'call_target': hex(K + 0x1f0180),
            'not_allocator_mutex_device_thread_or_service_initialization': True},
        'original_instructions': h.im.dump(raw, 0x5b0188, 0x5b0200, K),
        'independent_native_components': runs, 'unicorn_version': unicorn.__version__,
        'constraints': ['Five original instructions only in an observed emulator EL1h default, not Linux boot',
            'No synthetic current-context pointer, lock return, allocated page or reply injected into the prior request',
            'An initial file-backed context and its plus10 value do not describe a running client thread',
            'No camera interface, upload, WBI, persistent flash, actual encoding or recovery validation'],
        'goal_complete': False,
    })
    print(json.dumps({'status': 'PASS_BOUNDED_STARTUP_PREFIX_ONLY', 'cases': len(runs),
        'instructions_each': 5, 'native_SP': hex(sp), 'native_SP_EL0': hex(current),
        'BSS_clear_bytes_static_only': bss_end-bss_start, 'goal_complete': False}))


if __name__ == '__main__':
    main()
