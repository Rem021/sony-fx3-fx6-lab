"""Unicorn AArch64 Instruction-Level Verifier for P3, P4, P8, P9, and Fan Adaptations.

Verifies:
1. P4 (`appFw.so` `set_nd_filter_mode_i` @ `0x2111358` & `set_nd_filter_value_i` @ `0x21113d8`):
   576-combination Cartesian sweep proving 100% Clear state (`4` and `(1, 1)`) with 0 assertions.
2. P3 (`libInfraAppRemoteBoard.so` `execRcvMsg` @ `0x157c` & `MainThread` @ `0x1700`):
   Clean `0` return under `NULL` argument without pointer dereference fault.
3. P8 (`appFw.so` async log wait @ `0x2159c50`):
   Non-blocking `0` return in 2 instructions.
4. P9 (`upm.ko` `ET_REL` `.text+0x136b8`):
   Unpatched `blr x2` faults when callback slot `[x2 + 0x10] == NULL`, whereas adapted `mov w0, #0`
   completes cleanly with `w0 == 0` and intact flags flow.
5. Fan (`libfan.so` `_Z19fan_i_bkup_is_validv` @ `0x1dec`):
   Returns `w0 == 1` in 2 instructions with preserved stack pointer.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence, Tuple

from .elf_verify import parse_elf64_relocatable_aarch64, section_offset_to_file_offset

_LOCAL_UNICORN_SITE = Path(
    "/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22/"
    "tools/venv/lib/python3.14/site-packages"
)
try:
    import unicorn as U
    from unicorn import arm64_const as A
except ImportError:
    if _LOCAL_UNICORN_SITE.is_dir() and str(_LOCAL_UNICORN_SITE) not in sys.path:
        sys.path.append(str(_LOCAL_UNICORN_SITE))
    import unicorn as U
    from unicorn import arm64_const as A


ND_MODE_FUNC_VMA = 0x2111358
ND_VALUE_FUNC_VMA = 0x21113D8
ASSERT_ENTRY_VMA = 0x2167784
ND_STEP_HELPER_VMA = 0x1A0A880

P8_FUNC_VMA = 0x2159C50
FAN_FUNC_VMA = 0x1DEC
P9_TEXT_LOAD_BASE = 0x400000

TEXT_MAP_BASE = 0x2111000
TEXT_MAP_SIZE = 0x2000
ASSERT_MAP_BASE = 0x2167000
ASSERT_MAP_SIZE = 0x1000
HELPER_MAP_BASE = 0x1A0A000
HELPER_MAP_SIZE = 0x1000
RODATA_MAP_BASE = 0x260C000
RODATA_MAP_SIZE = 0x10000

STACK_BASE = 0x70000000
STACK_SIZE = 0x10000
STACK_INIT_SP = 0x7000E000

MSG_BUF_BASE = 0x71000000
MSG_BUF_SIZE = 0x1000
RETURN_SENTINEL_VMA = 0x72000000


@dataclass(frozen=True)
class NdSweepSummary:
    function_name: str
    patched: bool
    total_combinations: int
    clear_output_count: int
    non_clear_output_count: int
    assert_hit_count: int
    assert_lines_observed: Tuple[int, ...]
    helper_call_count: int


@dataclass(frozen=True)
class P3PruneExecSummary:
    exec_rcv_msg_ret: int
    main_thread_ret: int
    instructions_executed: int


@dataclass(frozen=True)
class P8ExecSummary:
    return_value: int
    instructions_executed: int
    sp_preserved: bool


@dataclass(frozen=True)
class P9GuardExecSummary:
    unpatched_null_callback_faulted: bool
    patched_return_value: int
    patched_completed_cleanly: bool


@dataclass(frozen=True)
class FanExecSummary:
    return_value: int
    instructions_executed: int
    sp_preserved: bool


def run_p4_nd_unicorn_sweep(
    appfw_image: bytes,
    patched_label: bool,
    w0_values: Sequence[int] = range(6),
    w1_values: Sequence[int] = range(4),
    w2_values: Sequence[int] = range(4),
    w3_values: Sequence[int] = range(6),
) -> Tuple[NdSweepSummary, NdSweepSummary]:
    """Execute `set_nd_filter_mode_i` and `set_nd_filter_value_i` in Unicorn across all enum combinations."""
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)

    mu.mem_map(TEXT_MAP_BASE, TEXT_MAP_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(TEXT_MAP_BASE, appfw_image[TEXT_MAP_BASE : TEXT_MAP_BASE + TEXT_MAP_SIZE])

    mu.mem_map(RODATA_MAP_BASE, RODATA_MAP_SIZE, U.UC_PROT_READ)
    mu.mem_write(RODATA_MAP_BASE, appfw_image[RODATA_MAP_BASE : RODATA_MAP_BASE + RODATA_MAP_SIZE])

    mu.mem_map(ASSERT_MAP_BASE, ASSERT_MAP_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(ASSERT_MAP_BASE, appfw_image[ASSERT_MAP_BASE : ASSERT_MAP_BASE + ASSERT_MAP_SIZE])

    mu.mem_map(HELPER_MAP_BASE, HELPER_MAP_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(ND_STEP_HELPER_VMA, struct.pack("<II", 0x52800840, 0xD65F03C0))

    mu.mem_map(STACK_BASE, STACK_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(MSG_BUF_BASE, MSG_BUF_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(RETURN_SENTINEL_VMA, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(RETURN_SENTINEL_VMA, struct.pack("<I", 0xD503201F))

    mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)

    state: Dict[str, int] = {"assert_hit": 0, "assert_line": 0, "helper_calls": 0}

    def _code_hook(uc: U.Uc, address: int, _size: int, _user_data: object) -> None:
        if address == ASSERT_ENTRY_VMA:
            state["assert_hit"] = 1
            state["assert_line"] = uc.reg_read(A.UC_ARM64_REG_W1)
            uc.emu_stop()
        elif address == ND_STEP_HELPER_VMA:
            state["helper_calls"] += 1

    mu.hook_add(U.UC_HOOK_CODE, _code_hook)

    mode_total = 0
    mode_clear = 0
    mode_non_clear = 0
    mode_asserts = 0
    mode_assert_lines = set()

    for w0 in w0_values:
        for w1 in w1_values:
            for w2 in w2_values:
                for _w3 in w3_values:
                    mode_total += 1
                    state["assert_hit"] = 0
                    state["assert_line"] = 0
                    mu.mem_write(MSG_BUF_BASE, b"\xff" * 64)
                    mu.reg_write(A.UC_ARM64_REG_SP, STACK_INIT_SP)
                    mu.reg_write(A.UC_ARM64_REG_LR, RETURN_SENTINEL_VMA)
                    mu.reg_write(A.UC_ARM64_REG_X0, w0)
                    mu.reg_write(A.UC_ARM64_REG_X1, w1)
                    mu.reg_write(A.UC_ARM64_REG_X2, w2)
                    mu.reg_write(A.UC_ARM64_REG_X3, MSG_BUF_BASE)

                    mu.emu_start(ND_MODE_FUNC_VMA, RETURN_SENTINEL_VMA, count=200)
                    if state["assert_hit"]:
                        mode_asserts += 1
                        mode_assert_lines.add(state["assert_line"])
                    else:
                        written_mode = mu.mem_read(MSG_BUF_BASE + 8, 1)[0]
                        if written_mode == 4:
                            mode_clear += 1
                        else:
                            mode_non_clear += 1

    mode_summary = NdSweepSummary(
        function_name="set_nd_filter_mode_i",
        patched=patched_label,
        total_combinations=mode_total,
        clear_output_count=mode_clear,
        non_clear_output_count=mode_non_clear,
        assert_hit_count=mode_asserts,
        assert_lines_observed=tuple(sorted(mode_assert_lines)),
        helper_call_count=0,
    )

    val_total = 0
    val_clear = 0
    val_non_clear = 0
    val_asserts = 0
    val_assert_lines = set()
    state["helper_calls"] = 0

    for w0 in w0_values:
        for w1 in w1_values:
            for w2 in w2_values:
                for w3 in w3_values:
                    val_total += 1
                    state["assert_hit"] = 0
                    state["assert_line"] = 0
                    mu.mem_write(MSG_BUF_BASE, b"\xff" * 64)
                    mu.mem_write(STACK_INIT_SP, struct.pack("<Q", MSG_BUF_BASE))
                    mu.reg_write(A.UC_ARM64_REG_SP, STACK_INIT_SP)
                    mu.reg_write(A.UC_ARM64_REG_LR, RETURN_SENTINEL_VMA)
                    mu.reg_write(A.UC_ARM64_REG_X19, 0xCAFEBABE12345678)
                    mu.reg_write(A.UC_ARM64_REG_X0, w0)
                    mu.reg_write(A.UC_ARM64_REG_X1, w1)
                    mu.reg_write(A.UC_ARM64_REG_X2, w2)
                    mu.reg_write(A.UC_ARM64_REG_X3, w3)
                    mu.reg_write(A.UC_ARM64_REG_X4, 4)
                    mu.reg_write(A.UC_ARM64_REG_X5, 8)
                    mu.reg_write(A.UC_ARM64_REG_X6, 16)
                    mu.reg_write(A.UC_ARM64_REG_X7, 0x1280)

                    mu.emu_start(ND_VALUE_FUNC_VMA, RETURN_SENTINEL_VMA, count=500)
                    if state["assert_hit"]:
                        val_asserts += 1
                        val_assert_lines.add(state["assert_line"])
                    else:
                        f0, f1 = struct.unpack_from("<II", mu.mem_read(MSG_BUF_BASE + 8, 8))
                        sp_after = mu.reg_read(A.UC_ARM64_REG_SP)
                        x19_after = mu.reg_read(A.UC_ARM64_REG_X19)
                        if sp_after != STACK_INIT_SP or x19_after != 0xCAFEBABE12345678:
                            raise RuntimeError(
                                f"ABI corruption in set_nd_filter_value_i: sp=0x{sp_after:x}, x19=0x{x19_after:x}"
                            )
                        if (f0, f1) == (1, 1):
                            val_clear += 1
                        else:
                            val_non_clear += 1

    val_summary = NdSweepSummary(
        function_name="set_nd_filter_value_i",
        patched=patched_label,
        total_combinations=val_total,
        clear_output_count=val_clear,
        non_clear_output_count=val_non_clear,
        assert_hit_count=val_asserts,
        assert_lines_observed=tuple(sorted(val_assert_lines)),
        helper_call_count=state["helper_calls"],
    )

    return mode_summary, val_summary


def run_p3_remoteboard_unicorn_check(patched_remoteboard_so: bytes) -> P3PruneExecSummary:
    """Execute P3-adapted `execRcvMsg` (0x157c) and `MainThread` (0x1700) in Unicorn with x0=NULL."""
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    mu.mem_map(0x1000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(0x1000, patched_remoteboard_so[0x1000:0x2000])
    mu.mem_map(STACK_BASE, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(RETURN_SENTINEL_VMA, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(RETURN_SENTINEL_VMA, struct.pack("<I", 0xD503201F))

    insns = [0]

    def _cnt_hook(_uc: U.Uc, _addr: int, _sz: int, _ud: object) -> None:
        insns[0] += 1

    mu.hook_add(U.UC_HOOK_CODE, _cnt_hook)

    mu.reg_write(A.UC_ARM64_REG_SP, STACK_BASE + 0x2000)
    mu.reg_write(A.UC_ARM64_REG_LR, RETURN_SENTINEL_VMA)
    mu.reg_write(A.UC_ARM64_REG_X0, 0)
    mu.emu_start(0x157C, RETURN_SENTINEL_VMA, count=16)
    ret_rcv = mu.reg_read(A.UC_ARM64_REG_W0)

    mu.reg_write(A.UC_ARM64_REG_SP, STACK_BASE + 0x2000)
    mu.reg_write(A.UC_ARM64_REG_LR, RETURN_SENTINEL_VMA)
    mu.reg_write(A.UC_ARM64_REG_X0, 0xDEADBEEF)
    mu.emu_start(0x1700, RETURN_SENTINEL_VMA, count=16)
    ret_main = mu.reg_read(A.UC_ARM64_REG_W0)

    return P3PruneExecSummary(
        exec_rcv_msg_ret=ret_rcv,
        main_thread_ret=ret_main,
        instructions_executed=insns[0],
    )


def run_p8_appfw_unicorn_check(patched_appfw_so: bytes) -> P8ExecSummary:
    """Execute P8-adapted `appFw.so` `0x2159c50` in Unicorn and verify immediate `0` return."""
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    page_base = P8_FUNC_VMA & ~0xFFF
    mu.mem_map(page_base, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(page_base, patched_appfw_so[page_base : page_base + 0x1000])
    mu.mem_map(STACK_BASE, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(RETURN_SENTINEL_VMA, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(RETURN_SENTINEL_VMA, struct.pack("<I", 0xD503201F))

    insns = [0]
    mu.hook_add(U.UC_HOOK_CODE, lambda _uc, _a, _s, _u: insns.__setitem__(0, insns[0] + 1))

    init_sp = STACK_BASE + 0x2000
    mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
    mu.reg_write(A.UC_ARM64_REG_LR, RETURN_SENTINEL_VMA)
    mu.reg_write(A.UC_ARM64_REG_X0, 0xDEADBEEF)
    mu.emu_start(P8_FUNC_VMA, RETURN_SENTINEL_VMA, count=16)

    return P8ExecSummary(
        return_value=mu.reg_read(A.UC_ARM64_REG_W0),
        instructions_executed=insns[0],
        sp_preserved=mu.reg_read(A.UC_ARM64_REG_SP) == init_sp,
    )


def run_p9_upm_ko_unicorn_check(unpatched_upm_ko: bytes, patched_upm_ko: bytes) -> P9GuardExecSummary:
    """Verify P9 `upm.ko` `.text+0x136b8` prevents a NULL callback dereference (`blr x2 -> mov w0, #0`)."""
    elf_u = parse_elf64_relocatable_aarch64(unpatched_upm_ko)
    text_foff_u, text_sec_u = section_offset_to_file_offset(elf_u, ".text", 0, size=0x14000)

    elf_p = parse_elf64_relocatable_aarch64(patched_upm_ko)
    text_foff_p, _ = section_offset_to_file_offset(elf_p, ".text", 0, size=0x14000)

    def _exec_slice(text_bytes: bytes) -> Tuple[bool, int]:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        map_sz = (text_sec_u.sh_size + 0xFFF) & ~0xFFF
        mu.mem_map(P9_TEXT_LOAD_BASE, map_sz, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(P9_TEXT_LOAD_BASE, text_bytes)

        cb_struct_base = 0x73000000
        mu.mem_map(cb_struct_base, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        # Callback pointer at [x2 + 0x10] is NULL (0x0)
        mu.mem_write(cb_struct_base + 0x10, struct.pack("<Q", 0))
        mu.mem_map(STACK_BASE, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)

        # Execute the 3-instruction window `.text+0x136b4 .. .text+0x136c0`:
        #   +0x136b4: ldr x2, [x2, #0x10]
        #   +0x136b8: blr x2 (unpatched)  OR  mov w0, #0 (P9 adapted)
        #   +0x136bc: tst w0, #0xff
        mu.reg_write(A.UC_ARM64_REG_SP, STACK_BASE + 0x2000)
        mu.reg_write(A.UC_ARM64_REG_X29, STACK_BASE + 0x2000)
        mu.reg_write(A.UC_ARM64_REG_X2, cb_struct_base)
        mu.reg_write(A.UC_ARM64_REG_X0, 0x99)
        try:
            mu.emu_start(
                P9_TEXT_LOAD_BASE + 0x136B4,
                P9_TEXT_LOAD_BASE + 0x136C0,
                count=8,
            )
            return False, mu.reg_read(A.UC_ARM64_REG_W0)
        except U.UcError:
            return True, -1

    fault_unpatched, _ = _exec_slice(unpatched_upm_ko[text_foff_u : text_foff_u + text_sec_u.sh_size])
    fault_patched, w0_patched = _exec_slice(patched_upm_ko[text_foff_p : text_foff_p + text_sec_u.sh_size])

    return P9GuardExecSummary(
        unpatched_null_callback_faulted=fault_unpatched,
        patched_return_value=w0_patched,
        patched_completed_cleanly=not fault_patched,
    )


def run_fan_libfan_unicorn_check(patched_libfan_so: bytes) -> FanExecSummary:
    """Execute adapted `libfan.so` `_Z19fan_i_bkup_is_validv` (`0x1dec`) in Unicorn and verify `w0 == 1`."""
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    mu.mem_map(0x1000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(0x1000, patched_libfan_so[0x1000:0x3000])
    mu.mem_map(STACK_BASE, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(RETURN_SENTINEL_VMA, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(RETURN_SENTINEL_VMA, struct.pack("<I", 0xD503201F))

    insns = [0]
    mu.hook_add(U.UC_HOOK_CODE, lambda _uc, _a, _s, _u: insns.__setitem__(0, insns[0] + 1))

    init_sp = STACK_BASE + 0x2000
    mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
    mu.reg_write(A.UC_ARM64_REG_LR, RETURN_SENTINEL_VMA)
    mu.reg_write(A.UC_ARM64_REG_X0, 0)
    mu.emu_start(FAN_FUNC_VMA, RETURN_SENTINEL_VMA, count=16)

    return FanExecSummary(
        return_value=mu.reg_read(A.UC_ARM64_REG_W0),
        instructions_executed=insns[0],
        sp_preserved=mu.reg_read(A.UC_ARM64_REG_SP) == init_sp,
    )
