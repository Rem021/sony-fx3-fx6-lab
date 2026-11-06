#!/usr/bin/env python3
"""Compare observers on unchanged original timing path; no engine fixes."""
from pathlib import Path
import datetime
import json
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pending_timing as p


def one(blob, prefix, kind):
    u, r = p.u, p.reg
    uc = u.Uc(u.UC_ARCH_MIPS, u.UC_MODE_MIPS32 | u.UC_MODE_LITTLE_ENDIAN)
    uc.ctl_set_cpu_model(r.UC_CPU_MIPS32_24KC)
    for at, length, prot in ((0, (len(blob)+4095)&-4096, u.UC_PROT_READ|u.UC_PROT_EXEC),
                             (p.INPUT_PA, 4096, u.UC_PROT_READ),
                             (p.CTX_PA, 4096, u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (p.HANDLE_PA, 4096, u.UC_PROT_READ),
                             (p.OUTPUT_PA, 4096, u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (p.STACK_PA, 0x10000, u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (p.a.STOP_PA, 4096, u.UC_PROT_READ|u.UC_PROT_EXEC)):
        uc.mem_map(at, length, prot)
    uc.mem_write(0, blob)
    uc.mem_write(p.INPUT_PA, prefix)
    context = bytearray([0xa5])*0x400
    context[1] = context[0x15] = 0
    struct.pack_into('<I', context, 0x10c, p.HANDLE)
    struct.pack_into('<I', context, 0x130, 0)
    uc.mem_write(p.CTX_PA, bytes(context))
    uc.mem_write(p.HANDLE_PA, struct.pack('<I', p.OUTPUT_PA))
    uc.mem_write(p.OUTPUT_PA, bytes([0xb6])*4096)
    uc.mem_write(p.STACK_PA, bytes([0xd7])*0x10000)
    for at, value in ((r.UC_MIPS_REG_SP, p.SP), (r.UC_MIPS_REG_RA, p.STOP),
                       (r.UC_MIPS_REG_A0, p.CTX), (r.UC_MIPS_REG_A1, p.a.INPUT),
                       (r.UC_MIPS_REG_A2, p.CTX+0x108)):
        uc.reg_write(at, value)
    pcs, stores = [], []
    def code(cpu, pc, size, user):
        pcs.append(pc)
        if len(pcs)>20000:
            cpu.emu_stop()
    def mem(cpu, access, at, size, value, user):
        if access == u.UC_MEM_WRITE:
            stores.append({'address':hex(at), 'bytes':size, 'value':hex(value&((1<<(8*size))-1))})
    if kind in ('code', 'both'):
        uc.hook_add(u.UC_HOOK_CODE, code)
    if kind in ('memory', 'both'):
        uc.hook_add(u.UC_HOOK_MEM_READ|u.UC_HOOK_MEM_WRITE, mem)
    err = None
    try:
        uc.emu_start(p.IMAGE+0x18fdb4, p.STOP, timeout=1000000, count=0)
    except u.UcError as exc:
        err = str(exc)
    result = {'kind':kind, 'error':err, 'PC':hex(uc.reg_read(r.UC_MIPS_REG_PC)),
              'SP':hex(uc.reg_read(r.UC_MIPS_REG_SP)), 'RA':hex(uc.reg_read(r.UC_MIPS_REG_RA)),
              'timing8_hex':bytes(uc.mem_read(p.OUTPUT_PA+0x7d0,8)).hex(),
              'target_entry_occurrences':pcs.count(p.IMAGE+0x1a085c),
              'pcs':[hex(x) for x in pcs], 'stores':stores}
    assert bytes(uc.mem_read(0,len(blob))) == blob
    assert bytes(uc.mem_read(p.INPUT_PA,64)) == prefix
    return result


def main():
    p.im.volume()
    out = Path(__file__).resolve().parent/'observer-matrix.json'
    assert not out.exists()
    blob = p.a.v.VCD_PATH.read_bytes()
    source = p.BASE/'stage78-native-start-flags-and-query-tail/run-20261026/start-flags-results.json'
    prefix = bytes.fromhex(json.loads(source.read_text())['cases'][0]['cases'][3]['extra_first64_hex'])
    cases = [one(blob,prefix,kind) for kind in ('none','code','memory','both')]
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope':'DIAGNOSTIC_OBSERVER_COMPARISON_NOT_DEVICE_OR_FIRMWARE_BUG_PROOF',
              'script_sha256':p.im.sha(Path(__file__).read_bytes()), 'unicorn_version':p.u.__version__,
              'cases':cases, 'original_image_or_execution_results_modified':False}
    p.im.write_json(out,result)
    print(json.dumps([{k:x[k] for k in ('kind','error','PC','SP','RA','target_entry_occurrences')} for x in cases]))


if __name__ == '__main__':
    main()
