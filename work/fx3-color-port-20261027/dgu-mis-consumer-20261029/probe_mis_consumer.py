#!/usr/bin/env python3
"""Bounded DGU parser-body prefixes in RAM; stop at unknown/CPU/hardware state."""
import hashlib
import json
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID
from unicorn import arm64_const as R

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
FW = HERE.parents[2] / 'work/sony-firmware-20261024'
CODE = 0xfe040800
RAM = 0xfe040000
RAM_SIZE = 0x7000
MIS = 0xfe080000
STACK = 0x200000000
STOP = 0x400000000
CTX = 0xfe046978
PINS = dict(DGU='39eeb6d572a060149194463507800ed66b866a20dceb8ed49b01a04eb6fb2ba7',
            MIS='4cd3e9bc3a0a4aec4793bff77e7ca4dccdba8637212cd632cdc5ecbe550daf98')


class Guest:
    def __init__(self, dgu, mis):
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.dgu = dgu
        self.mis = mis
        self.u.mem_map(RAM, RAM_SIZE)
        self.u.mem_write(CODE, dgu)
        self.known = bytearray(RAM_SIZE)
        self.known[CODE-RAM:CODE-RAM+len(dgu)] = b'\1' * len(dgu)
        self.u.mem_map(MIS, (len(mis)+4095)&~4095)
        self.u.mem_write(MIS, mis)
        self.u.mem_map(STACK, 0x10000)
        self.stack_known = bytearray(0x10000)
        self.u.mem_map(STOP, 0x1000)
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        self.boundary = None
        self.instructions = 0
        self.writes = []
        self.write_count = 0
        self.dispatches = []
        self.cursor = None
        self.cache = {}
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
        if not CODE <= pc < CODE + len(self.dgu):
            self.stop('before_non_original_DGU_code', address=hex(pc))
            return
        if pc not in self.cache:
            i = next(self.md.disasm(bytes(u.mem_read(pc, 4)), pc, count=1), None)
            if i is None:
                self.stop('undecoded_instruction')
                return
            self.cache[pc] = (i.mnemonic, i.op_str)
        mn, op = self.cache[pc]
        if mn in {'mrs','msr','sys','sysl','dc','ic','tlbi','dsb','dmb','isb','sev','wfe','wfi','svc','hvc','smc','eret'}:
            self.stop('before_CPU_or_hardware_operation', instruction=mn+' '+op)
            return
        if pc in [0xfe04548c, 0xfe045504]:
            offset = 8 if pc == 0xfe04548c else 4
            self.cursor = struct.unpack('<I', bytes(u.mem_read(CTX+offset, 4)))[0]
        if pc == 0xfe045648:
            header = bytes(u.mem_read(CTX+0x30, 4))
            opcode, words, flags = struct.unpack('<BBH', header)
            raw = bytes(u.mem_read(CTX+0x34, max(0,words-1)*4))
            self.dispatches.append(dict(PC=hex(pc), cursor=hex(self.cursor) if self.cursor is not None else None,
                opcode=hex(opcode), word_count=words, raw_flags_u16=hex(flags),
                handler=hex(u.reg_read(R.UC_ARM64_REG_X8)), decoded_payload_hex=raw.hex()))
        self.instructions += 1
        if self.instructions >= 100000:
            self.stop('instruction_budget')

    def read(self, u, access, at, size, value, user):
        if RAM <= at and at+size <= RAM+RAM_SIZE and all(self.known[at-RAM:at-RAM+size]):
            return
        if MIS <= at and at+size <= MIS+len(self.mis):
            return
        if STACK <= at and at+size <= STACK+len(self.stack_known) and all(self.stack_known[at-STACK:at-STACK+size]):
            return
        self.stop('before_unknown_read', address=hex(at), bytes=size)

    def write(self, u, access, at, size, value, user):
        if STACK <= at and at+size <= STACK+len(self.stack_known):
            self.stack_known[at-STACK:at-STACK+size] = b'\1' * size
            return
        if CODE+len(self.dgu) <= at and at+size <= RAM+RAM_SIZE:
            self.known[at-RAM:at-RAM+size] = b'\1' * size
            kind = 'original_DGU_BSS_RAM'
        elif MIS <= at and at+size <= MIS+len(self.mis):
            kind = 'explicit_MIS_RAM_copy'
        else:
            self.stop('before_outside_model_write', address=hex(at), bytes=size, value=hex(value))
            return
        self.write_count += 1
        if len(self.writes) < 24:
            self.writes.append(dict(PC=hex(u.reg_read(R.UC_ARM64_REG_PC)), address=hex(at), bytes=size,
                                    value=hex(value), kind=kind))

    def invalid(self, u, access, at, size, value, user):
        self.stop('unmapped_external_state', access=access, address=hex(at), bytes=size, value=hex(value))
        return False

    def call(self, entry, args):
        self.u.reg_write(R.UC_ARM64_REG_SP, STACK+0xf000)
        self.u.reg_write(R.UC_ARM64_REG_LR, STOP)
        for n,x in enumerate(args):
            self.u.reg_write(getattr(R, f'UC_ARM64_REG_X{n}'), x)
        try:
            self.u.emu_start(entry, STOP+4, timeout=3000000, count=100000)
        except UcError:
            if self.boundary is None:
                raise
        assert self.boundary is not None
        return dict(entry=hex(entry), arguments=list(map(hex,args)), boundary=self.boundary,
                    original_instructions=self.instructions, original_dispatches=self.dispatches,
                    nonstack_RAM_write_operations=self.write_count, first_nonstack_RAM_writes=self.writes,
                    register_snapshot=[hex(self.u.reg_read(getattr(R,f'UC_ARM64_REG_X{n}'))) for n in range(4)],
                    hardware_state_or_reply_supplied=False, function_returns_replaced=False,
                    original_files_modified=False, whole_DGU_or_real_boot_proved=False)


def main():
    out = HERE/'DGU-MIS-prefix-results.json'
    assert not out.exists()
    originals = FW/'stage198-AP-CP-loaders-and-partition-selection/originals'
    dgu = (originals/'DGU.bin').read_bytes()
    mis = (originals/'MIS.bin').read_bytes()
    for key,data in [('DGU',dgu),('MIS',mis)]:
        assert hashlib.sha256(data).hexdigest() == PINS[key]
    cases = []
    for offset in [0xa00,0xc200,0x13200]:
        result = Guest(dgu,mis).call(0xfe04536c,[0x10,MIS+offset])
        cases.append(dict(script_offset=hex(offset), result=result))
    result = dict(source_pins=PINS, mode_argument='0x10', cases=cases,
        scope='Three independent original parser-body calls, bypassing no function return. Entry is the statically resolved body after the unexecuted DGU cache-maintenance wrapper. Original MIS file is an explicit writable RAM copy; BSS is unknown until original instructions write it. Not a normal boot or full DGU run. Stops before unknown state or any CPU/cache/system operation; no physical memory or device is mapped.',
        CPU_or_hardware_operations_executed=0, native_Sony_programs_executed=0, device_actions=0,
        modified_firmware_or_flashable_package_produced=False)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(script=x['script_offset'],boundary=x['result']['boundary'],
                          instructions=x['result']['original_instructions'],dispatches=len(x['result']['original_dispatches'])) for x in cases]))


if __name__ == '__main__':
    main()
