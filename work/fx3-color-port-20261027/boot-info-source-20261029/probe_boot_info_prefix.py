#!/usr/bin/env python3
"""Strict original NOR prefixes only; never enter DGU or supply boot metadata."""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from unicorn import (Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC,
                     UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID)
from unicorn import arm64_const as R

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
BASE = 0xfe049000
MIS_BASE = 0xfe080000
STACK = 0x200000000
STOP = 0x400000000


class Guest:
    def __init__(self, nor, mis=None):
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.nor = nor
        self.mis = mis
        self.u.mem_map(BASE, (len(nor) + 4095) & ~4095, UC_PROT_READ | UC_PROT_EXEC)
        self.u.mem_write(BASE, nor)
        if mis is not None:
            self.u.mem_map(MIS_BASE, (len(mis) + 4095) & ~4095, UC_PROT_READ)
            self.u.mem_write(MIS_BASE, mis)
        self.u.mem_map(STACK, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
        self.stack_known = bytearray(0x10000)
        self.u.mem_map(STOP, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        self.boundary = None
        self.instructions = 0
        self.samples = []
        self.calls = []
        self.u.hook_add(UC_HOOK_CODE, self.code)
        self.u.hook_add(UC_HOOK_MEM_READ, self.read)
        self.u.hook_add(UC_HOOK_MEM_WRITE, self.write)
        self.u.hook_add(UC_HOOK_MEM_INVALID, self.invalid)

    def stop(self, reason, **extra):
        if self.boundary is None:
            self.boundary = dict(reason=reason, PC=hex(self.u.reg_read(R.UC_ARM64_REG_PC)), **extra)
        self.u.emu_stop()

    def code(self, u, pc, size, user):
        if pc == STOP:
            self.stop('returned')
            return
        if pc == 0xfe0561b4:
            self.stop('before_original_diagnostic_call', caller_return=hex(u.reg_read(R.UC_ARM64_REG_LR)))
            return
        if not BASE <= pc < BASE + len(self.nor):
            self.stop('before_non_NOR_code')
            return
        i = next(self.md.disasm(bytes(u.mem_read(pc, 4)), pc, count=1), None)
        if i is None:
            self.stop('undecoded_instruction')
            return
        if i.mnemonic in {'mrs', 'msr', 'sys', 'sysl', 'dc', 'ic', 'tlbi', 'dsb', 'dmb', 'isb',
                          'sev', 'wfe', 'wfi', 'svc', 'hvc', 'smc', 'eret'}:
            self.stop('before_CPU_or_hardware_operation', instruction=i.mnemonic + ' ' + i.op_str)
            return
        if pc == 0xfe055d44:
            self.samples.append(dict(PC=hex(pc), original_comparison_return=hex(u.reg_read(R.UC_ARM64_REG_X0))))
        if i.mnemonic in {'bl', 'blr'}:
            self.calls.append(dict(PC=hex(pc), instruction=i.mnemonic + ' ' + i.op_str))
        self.instructions += 1
        if self.instructions >= 100000:
            self.stop('instruction_budget')

    def read(self, u, access, at, size, value, user):
        if BASE <= at and at + size <= BASE + len(self.nor):
            return
        if self.mis is not None and MIS_BASE <= at and at + size <= MIS_BASE + len(self.mis):
            return
        if STACK <= at and at + size <= STACK + len(self.stack_known):
            if all(self.stack_known[at - STACK:at - STACK + size]):
                return
        self.stop('before_unknown_read', address=hex(at), bytes=size)

    def write(self, u, access, at, size, value, user):
        if STACK <= at and at + size <= STACK + len(self.stack_known):
            self.stack_known[at - STACK:at - STACK + size] = b'\1' * size
            return
        self.stop('before_nonstack_write', address=hex(at), bytes=size)

    def invalid(self, u, access, at, size, value, user):
        self.stop('unmapped_external_state', address=hex(at), bytes=size)
        return False

    def call(self, entry, args=()):
        self.u.reg_write(R.UC_ARM64_REG_SP, STACK + 0xf000)
        self.u.reg_write(R.UC_ARM64_REG_LR, STOP)
        for n, value in enumerate(args):
            self.u.reg_write(getattr(R, f'UC_ARM64_REG_X{n}'), value)
        try:
            self.u.emu_start(entry, STOP + 4, timeout=3000000, count=100000)
        except UcError:
            if self.boundary is None:
                raise
        assert self.boundary is not None
        return dict(entry=hex(entry), arguments=list(map(hex, args)), original_instructions=self.instructions,
                    boundary=self.boundary, registers=[hex(self.u.reg_read(getattr(R, f'UC_ARM64_REG_X{n}'))) for n in range(4)],
                    original_return_samples=self.samples, original_calls=self.calls,
                    nonstack_writes=0, boot_information_supplied=False, DGU_entry_executed=False,
                    diagnostic_or_other_function_return_replaced=False)


def main():
    out = HERE / 'boot-info-prefix-results.json'
    assert not out.exists()
    review = json.loads((HERE / 'boot-info-source-review.json').read_text())
    src = {Path(x['path']).name: x for x in review['sources']}
    nor = Path(src['loader_nor.bin']['path']).read_bytes()
    mis = Path(src['MIS.bin']['path']).read_bytes()
    for name, b in [('loader_nor.bin', nor), ('MIS.bin', mis)]:
        assert hashlib.sha256(b).hexdigest() == src[name]['sha256']
    strict = Guest(nor).call(0xfe056024)
    assert strict['boundary'] == dict(reason='unmapped_external_state', PC='0xfe0587b0', address='0xfe040090', bytes=4)
    explicit = Guest(nor, mis).call(0xfe055d14, [0x10, 0xfe040800, MIS_BASE])
    assert explicit['boundary'] == dict(reason='before_original_diagnostic_call', PC='0xfe0561b4', caller_return='0xfe055dd8')
    assert explicit['original_return_samples'] == [dict(PC='0xfe055d44', original_comparison_return='0x0')]
    assert explicit['registers'][:3] == ['0x6', '0xfe05f501', '0xfe080123']
    result = dict(NOR_sha256=src['loader_nor.bin']['sha256'], MIS_sha256=src['MIS.bin']['sha256'],
                  strict_original_boot_caller=strict, explicit_original_MIS_reader_prefix=explicit,
                  explicit_case_scope='Independent direct function call using original MIS bytes at its declared base and pformat DGU load address as explicit arguments. It does not supply actual boot-table values or prove that the real caller reaches this state.',
                  physical_state_or_block_data_supplied=False, hardware_CPU_operations_executed=0,
                  native_Sony_programs_executed=0, device_actions=0, full_boot_completed=False,
                  memory_initialization_or_ISP_or_RAW_completed=False, flashable_package_produced=False)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(strict=strict['boundary'], explicit=explicit['boundary'],
                          MIS_compare=explicit['original_return_samples'], original_instructions=[strict['original_instructions'], explicit['original_instructions']])))


if __name__ == '__main__':
    main()
