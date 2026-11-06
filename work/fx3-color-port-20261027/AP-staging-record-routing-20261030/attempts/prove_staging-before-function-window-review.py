#!/usr/bin/env python3
"""Pinned public AP instructions with original FX3 defaults, in bounded RAM only."""
import datetime, hashlib, importlib.util, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from capstone.arm64_const import ARM64_OP_MEM
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_PROT_ALL, UC_PROT_READ, UC_PROT_EXEC, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID
from unicorn import arm64_const as R

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
PROJECT = HERE.parents[2]
FW = PROJECT / 'work/sony-firmware-20261024'
AP_BASE = 0xfe040000
BACKUP = 0x404000000
CTX = 0x100100000
STACK = 0x100200000
OUT = 0x100300000
RETURN = 0x100400000
STATE = 0xfe26c300
GLOBALS = [0xfe06a038, 0xfe06a040, 0xfe06a048]
PINS = {
    'AP': '2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74',
    'bank0': '33789a7a4d648c9a0bd74bd332de395500bdf0f363839f1d770393a3a3191da5',
    'bank1': '5dc5883fb86d87d14c1c3d530d4d65d903361c189a64edabcd1f636df289f5b7',
    'previous': 'e68dd2e1596ab1b10f508ce658e2a796dcc9cebbe51ed8fe6e270b15c87e42e2',
}
MD = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
MD.detail = True


def sha(b): return hashlib.sha256(b).hexdigest()
def hx(v): return hex(v)
def packed(v): return struct.pack('<Q', v)


class RAM:
    """No helper substitutions, devices, system registers or permissive zero pages."""
    def __init__(self, ap, banks, mode=3):
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.ap = ap
        self.sources = [(AP_BASE, AP_BASE + len(ap))]
        self.mutable = [(STACK, STACK + 0x10000), (CTX, CTX + 0x1000),
                        (OUT, OUT + 0x10000), (0xfe204000, 0xfe207000)]
        self.mutable += [(a, a + 8) for a in GLOBALS]
        self.known = set()
        self.calls = []
        self.writes = []
        self.boundary = None
        self.trace = []
        self.map(AP_BASE, ap, UC_PROT_ALL)
        self.offset1 = (len(banks[0]) + 0xfff) & ~0xfff
        for base, b in [(BACKUP, banks[0]), (BACKUP + self.offset1, banks[1])]:
            self.map(base, b, UC_PROT_READ)
            self.sources.append((base, base + len(b)))
        for base, size in [(STACK, 0x10000), (CTX, 0x1000), (OUT, 0x10000),
                           (0xfe204000, 0x3000), (STATE & ~0xfff, 0x1000), (RETURN, 0x1000)]:
            self.u.mem_map(base, size, UC_PROT_ALL)
        self.seed(STATE, struct.pack('<I', mode))
        # Caller register values are an explicit harness fixture, not body state.
        for n in range(31): self.u.reg_write(getattr(R, f'UC_ARM64_REG_X{n}'), 0xd00d0000 + n)
        self.u.reg_write(R.UC_ARM64_REG_SP, STACK + 0x8000)
        self.u.hook_add(UC_HOOK_CODE, self.code)
        self.u.hook_add(UC_HOOK_MEM_READ, self.read)
        self.u.hook_add(UC_HOOK_MEM_WRITE, self.write)
        self.u.hook_add(UC_HOOK_MEM_INVALID, self.invalid)

    def map(self, at, b, perm):
        assert at % 4096 == 0
        self.u.mem_map(at, (len(b) + 4095) & ~4095, perm)
        self.u.mem_write(at, b)

    def seed(self, at, b):
        self.u.mem_write(at, b)
        self.known.update(range(at, at + len(b)))

    def stop(self, reason, **fields):
        if self.boundary is None:
            self.boundary = dict(reason=reason, PC=hx(self.u.reg_read(R.UC_ARM64_REG_PC)), **fields)
        self.u.emu_stop()

    def code(self, u, pc, size, unused):
        if pc == RETURN: self.stop('original_function_return'); return
        if pc in self.ends: self.stop(self.ends[pc]); return
        if pc == 0xfe055530: self.stop('before_original_diagnostic'); return
        if pc == 0xfe05d884: self.stop('before_original_bulk_transfer'); return
        windows = [(0xfe04b444, 0xfe04b470), (0xfe04c0fc, 0xfe04c244),
                   (0xfe04c8d0, 0xfe04c958), (0xfe04cd10, 0xfe04cd30),
                   (0xfe04ce08, 0xfe04cecc), (0xfe04cf84, 0xfe04d134),
                   (0xfe04ebc0, 0xfe04ed70), (0xfe04edf0, 0xfe04ee00),
                   (0xfe04eee0, 0xfe04eee8), (0xfe050158, 0xfe050260),
                   (0xfe052af8, 0xfe052b28), (0xfe05b2b8, 0xfe05b3d0)]
        if not any(a <= pc < z for a, z in windows):
            self.stop('before_outside_scoped_original_code'); return
        ins = next(MD.disasm(self.ap[pc-AP_BASE:pc-AP_BASE+4], pc), None)
        if ins is None or ins.mnemonic in ['mrs', 'msr', 'sys', 'dc', 'ic', 'tlbi', 'eret', 'svc', 'hvc', 'smc']:
            self.stop('before_privileged_or_undecoded_instruction'); return
        self.trace.append(pc)

    def read(self, u, access, at, size, value, unused):
        if all(a in self.known for a in range(at, at + size)): return
        # The AP image supplies static bytes, not the live BK4 selection globals.
        if AP_BASE <= at and at + size <= AP_BASE + len(self.ap):
            if at + size <= 0xfe06a000 or at >= 0xfe06b000: return
        if any(a <= at and at + size <= z for a, z in self.sources[1:]): return
        self.stop('before_unknown_RAM_read', address=hx(at), bytes=size)

    def write(self, u, access, at, size, value, unused):
        if not any(a <= at and at + size <= z for a, z in self.mutable):
            self.stop('before_outside_scoped_RAM_write', address=hx(at), bytes=size); return
        self.known.update(range(at, at + size))
        self.writes.append(dict(PC=hx(u.reg_read(R.UC_ARM64_REG_PC)), address=hx(at), bytes=size))

    def invalid(self, u, access, at, size, value, unused):
        self.stop('before_invalid_memory_access', access=access, address=hx(at), bytes=size)
        return False

    def run(self, entry, args=None, registers=None, ends=None):
        self.boundary = None
        self.trace = []
        self.writes = []
        self.ends = ends or {}
        self.u.reg_write(R.UC_ARM64_REG_X30, RETURN)
        for n, value in enumerate(args or []): self.u.reg_write(getattr(R, f'UC_ARM64_REG_X{n}'), value)
        for name, value in (registers or {}).items(): self.u.reg_write(getattr(R, 'UC_ARM64_REG_' + name), value)
        try: self.u.emu_start(entry, RETURN + 4, timeout=3000000, count=150000)
        except UcError:
            if self.boundary is None: raise
        assert self.boundary is not None, 'instruction/time budget exhausted'
        result = dict(entry=hx(entry), boundary=self.boundary, instructions=len(self.trace),
                      trace_sha256=sha(b''.join(packed(x) for x in self.trace)),
                      reached_entries=[hx(x) for x in dict.fromkeys(self.trace) if x in
                          [0xfe04cf84, 0xfe04cfe4, 0xfe04d064, 0xfe04d0d4, 0xfe04ce64,
                           0xfe04c904, 0xfe05b2b8, 0xfe04b444, 0xfe04c170, 0xfe052af8]],
                      X0=hx(self.u.reg_read(R.UC_ARM64_REG_X0)), X1=hx(self.u.reg_read(R.UC_ARM64_REG_X1)),
                      X2=hx(self.u.reg_read(R.UC_ARM64_REG_X2)), X3=hx(self.u.reg_read(R.UC_ARM64_REG_X3)),
                      RAM_write_operations=len(self.writes),
                      BK4_global_writes=[w for w in self.writes if any(a <= int(w['address'], 16) < a+8 for a in GLOBALS)])
        self.calls.append(result)
        return result

    def init(self, address):
        r = self.run(0xfe04c900, [address])
        assert r['boundary']['reason'] == 'original_function_return' and int(r['X0'], 16) == 0
        assert self.qword(0xfe06a040) == address
        return r

    def qword(self, at):
        assert all(a in self.known for a in range(at, at + 8))
        return struct.unpack('<Q', self.u.mem_read(at, 8))[0]

    def get(self, key, expected):
        r = self.run(0xfe05b2b8, [key, OUT])
        assert r['boundary']['reason'] == 'original_function_return'
        assert int(r['X0'], 16) == len(expected)
        assert bytes(self.u.mem_read(OUT, len(expected))) == expected
        r.update(property=hx(key), returned_bytes=len(expected), output_sha256=sha(expected))
        return r


def main():
    assert not (HERE/'staging-proof.json').exists()
    previous = TASK/'CP-escape-config-20261030'
    seal = (previous/'final-receipt.json').read_bytes()
    assert sha(seal) == PINS['previous']
    manifest = json.loads(seal)
    for f in manifest['files']:
        b = (previous/f['path']).read_bytes()
        assert len(b) == f['bytes'] and sha(b) == f['sha256']
    ref = FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin'
    ap = ref.read_bytes(); assert sha(ap) == PINS['AP']
    bk = TASK/'dmm-backup-20261029'
    pins = json.loads((bk/'final-receipt.json').read_text())
    reader = bk/'extract_backup_parameters.py'
    assert sha(reader.read_bytes()) == next(x for x in pins['files'] if x['path']==reader.name)['sha256']
    spec = importlib.util.spec_from_file_location('owned_BK4_reader', reader)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    banks = [(bk/f'original-records/canonical-bank{n}.bin').read_bytes() for n in [0, 1]]
    for n, b in enumerate(banks):
        assert sha(b) == PINS[f'bank{n}']
        assert (sum(b[:32])+sum(b[36:])) & 0xffffffff == struct.unpack_from('<I', b, 32)[0]
    prop = lambda n, key: bytes.fromhex(helper.property_at(banks[n], key)['value_hex'])
    val = lambda n, key: int.from_bytes(prop(n, key), 'little')
    assert val(0, 0xfa0006) == BACKUP
    # Complete original leaf APIs. State 3 is the declared RAM-backed fixture,
    # not a claim about the user's current boot state.
    ram = RAM(ap, banks)
    ram.init(BACKUP)
    ram.get(0xfa019a, prop(0, 0xfa019a))
    second = ram.run(0xfe04c8d0, [BACKUP, 1])
    assert second['boundary']['reason']=='original_function_return'
    cp_mirror = int(second['X0'], 16)
    assert cp_mirror == BACKUP + 0xd2000
    ram.init(cp_mirror)
    for key in [0xfa0006, 0xfa01d0, 0xfa01d3, 0xfa0077, 0xfa01af, 0xfa0080]: ram.get(key, prop(1, key))
    ram.init(BACKUP)
    for key in [0xfa019a, 0xfa019b, 0xfa01c7]: ram.get(key, prop(0, key))
    leaf_calls = list(ram.calls)
    # Independent after-diagnostic original fragment: switch to CP mirror and
    # populate CP fields/table, stopping before the next diagnostic. No stub.
    frag = RAM(ap, banks); frag.init(BACKUP)
    load = frag.run(0xfe04ebc0, registers={'X19':CTX, 'X20':BACKUP, 'W23':0xfa0006},
                    ends={0xfe04ed6c:'before_CP_bounds_diagnostic'})
    assert load['boundary']['reason']=='before_CP_bounds_diagnostic'
    cp_fields = {hx(x):hx(frag.qword(CTX+x)) for x in [0x18, 0x20, 0x28, 0x30, 0x200, 0x208, 0x210, 0x218, 0x220, 0x228, 0x230]}
    assert frag.qword(0xfe06a040) == cp_mirror
    assert frag.qword(CTX+0x218) == val(1, 0xfa01d0)
    assert frag.qword(CTX+0x220) == val(1, 0xfa01d3)-val(1, 0xfa01d0)
    table = prop(1, 0xfa0080)
    assert bytes(frag.u.mem_read(0xfe204000, len(table))) == table
    # A distinct late fragment restores AP selection; the intervening original
    # logger/allocator/cache-registration loop is deliberately not executed.
    restore = frag.run(0xfe04edf0, registers={'X20':BACKUP}, ends={0xfe04eee0:'before_original_context_status_store'})
    assert restore['boundary']['reason']=='before_original_context_status_store'
    assert frag.qword(0xfe06a040) == BACKUP
    # Complete wrapper prefix with original generic getter and memcpy code.
    send = frag.run(0xfe050158, [CTX])
    assert send['boundary']['reason']=='before_original_bulk_transfer'
    assert [int(send[k],16) for k in ['X0','X1','X2','X3']] == [CTX+0xa0,val(1,0xfa01d0),val(0,0xfa019a),val(1,0xfa01d3)-val(1,0xfa01d0)]
    ap_fields = {hx(x):hx(frag.qword(CTX+x)) for x in [0x38,0x40,0x48]}
    assert frag.qword(CTX+0x38)==val(0,0xfa019a) and frag.qword(CTX+0x40)==val(0,0xfa019b)
    wrong = RAM(ap,banks); wrong.init(cp_mirror)
    negative = wrong.run(0xfe050158,[CTX])
    assert negative['boundary']['reason']=='before_original_diagnostic'
    assert 0xfe052af8 not in wrong.trace
    # Complete aligned scan, retained as candidates; source contexts below are
    # the validated subset, not every syntactically decoded store.
    candidates=[]
    for at in range(0x9000,0x23000,4):
        for i in MD.disasm(ap[at:at+4],AP_BASE+at):
            if i.mnemonic.startswith('st') and any(o.type==ARM64_OP_MEM and o.mem.disp in [0x30,0x38,0x40,0x48] for o in i.operands):
                candidates.append(dict(VA=hx(i.address),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str))
    listings=HERE/'listings';listings.mkdir(exist_ok=False)
    cuts=[]
    windows=[('reference-record-select-and-CP-read',0xfe04ebc0,0xfe04ed70),
             ('reference-restore-AP-record',0xfe04ed88,0xfe04eee8),
             ('reference-record-address-size-and-init',0xfe04cf84,0xfe04d134),
             ('reference-property-getter-mode',0xfe05b2b8,0xfe05b3d0),
             ('reference-AP-source-to-transfer-wrapper',0xfe050158,0xfe050260),
             ('reference-transfer-arguments',0xfe052af8,0xfe052bdc),
             ('reference-RAM-backed-mode-setting',0xfe05b4d8,0xfe05b738)]
    for label,lo,hi in windows:
        raw=ap[lo-AP_BASE:hi-AP_BASE]
        p=listings/(label+'.txt')
        p.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in MD.disasm(raw,lo))+'\n')
        cuts.append(dict(label=label,begin=hx(lo),end_exclusive=hx(hi),original_bytes_sha256=sha(raw),listing=str(p.relative_to(HERE))))
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        AP_reference=dict(path=str(ref),sha256=sha(ap),model='A7 IV v2.00, not the target FX3 AP bootloader'),
        original_FX3_defaults=[dict(bank=n,bytes=len(b),sha256=sha(b)) for n,b in enumerate(banks)],
        explicit_fixture=dict(backup_address=hx(BACKUP),record1_offset=hx(ram.offset1),CP_mirror_address=hx(cp_mirror),property_mode=3,
                              mode3_role='Static original branch FE05B544->FE05B6E8 sets 3 after Data_init success. Runtime selection is not asserted.'),
        complete_original_leaf_API_calls=leaf_calls,
        independent_original_fragments=dict(CP_context=load,CP_context_fields=cp_fields,CP_FA0080_sha256=sha(table),restore_AP=restore,
            AP_source_wrapper_prefix=send,AP_context_fields=ap_fields,CP_selected_negative=negative,
            omitted_middle='FE04ED6C..FE04EDEC diagnostic/allocator/cache registration not executed; no successful boot path is inferred.'),
        binding=dict(source_property='0xfa019a',load_destination_property='0xfa019a',context_source_store='0xfe0501a0',
            capacity_property='0xfa019b',capacity_store='0xfe0501c8',secondary_source_property='0xfa01c7',secondary_source_store='0xfe0501ec',
            bulk_destination=send['X1'],bulk_source=send['X2'],bulk_bytes=send['X3'],bulk_call='0xfe052b24 ->0xfe05d884',
            AP_declared_capacity_check_proved=False,actual_file_read_or_transfer_executed=False),
        scan=dict(range_begin='0xfe049000',range_end_exclusive='0xfe063000',aligned_store_candidates=candidates,all_candidates_are_context_stores=False),
        source_windows=cuts,previous_receipt_sha256=sha(seal),previous_files_reverified=len(manifest['files']),
        boundaries=dict(physical_actions=0,helper_substitutions=0,privileged_instructions=0,originals_modified=False,
            other_owner_files_written=False,FX3_target_AP_obtained=False,current_body_backup_selection_proved=False,
            actual_buffers_RAW_full_ISP_proved=False,modified_or_flashable_firmware_produced=False,goal_complete=False))
    (HERE/'staging-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(leaf_calls=len(leaf_calls),CP_mirror=hx(cp_mirror),CP_fragment=load['boundary'],AP_source=send['X2'],
        bulk_destination=send['X1'],bulk_bytes=send['X3'],wrong_record=negative['boundary'],whole_target_goal_proved=False)))


if __name__=='__main__': main()
