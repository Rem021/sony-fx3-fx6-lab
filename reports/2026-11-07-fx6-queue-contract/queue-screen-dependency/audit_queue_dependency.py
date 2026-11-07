#!/usr/bin/env python3
"""Read-only FX6 queue/initialization dependencies, SHA pinned; standard library."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

SHA = 'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'


def audit(path, shim=None):
    b = Path(path).read_bytes()
    digest = hashlib.sha256(b).hexdigest()
    if digest != SHA:
        raise ValueError('FX6 SHA mismatch')
    h = struct.unpack_from('<HHIQQQIHHHHHH', b, 16)
    loads = [struct.unpack_from('<IIQQQQQQ', b, h[4]+i*h[8]) for i in range(h[9])]
    sections = [struct.unpack_from('<IIQQQQIIQQ', b, h[5]+i*h[10]) for i in range(h[11])]
    shstr = sections[h[12]]

    def cstr(off):
        return b[off:b.index(b'\0', off)].decode('ascii')

    named = {cstr(shstr[4]+s[0]): s for s in sections}

    def off(addr):
        for p in loads:
            if p[0] == 1 and p[3] <= addr < p[3]+p[5]:
                return p[2]+addr-p[3]
        raise ValueError(f'Unbacked VMA {addr:#x}')

    def u32(a):
        return struct.unpack_from('<I', b, off(a))[0]

    def target(pc):
        w = u32(pc)
        if w & 0x7c000000 != 0x14000000:
            raise ValueError(f'{pc:#x} is not B/BL')
        imm = w & 0x3ffffff
        if imm & 0x2000000:
            imm -= 0x4000000
        return pc+imm*4

    def call(pc, expected):
        actual = target(pc)
        if actual != expected:
            raise ValueError(f'Unexpected call at {pc:#x}')
        return {'pc': hex(pc), 'target': hex(actual), 'import': imports.get(actual)}

    sy = named['.dynsym']; strings = sections[sy[6]]
    symbols = [cstr(strings[4]+struct.unpack_from('<I', b, a)[0])
               for a in range(sy[4], sy[4]+sy[5], sy[9])]
    rp = named['.rela.plt']; plt = named['.plt']
    imports = {}
    for i,a in enumerate(range(rp[4], rp[4]+rp[5], rp[9])):
        _, info, _ = struct.unpack_from('<QQq', b, a)
        imports[plt[3]+32+i*16] = symbols[info >> 32]
    needed = {0xb17970:'osal_reg_sync_msg_queue_cb', 0xb18c00:'osal_snd_sync_direct',
              0xb17b30:'osal_reg_msg_queue_cb', 0xb19ec0:'osal_rcv_msg_tmo',
              0xb1a120:'osal_snd_msg'}
    for a,n in needed.items():
        if imports.get(a) != n:
            raise ValueError(f'Import binding mismatch {a:#x}')
    diagnostics = {}
    for a, prefix in [
        (0x22456f8,'void App::start_utimer()'),
        (0x2245680,'void App::exec_utimer()'),
        (0x24bf408,'void model::model_api::detail::model_start()'),
        (0x2269f00,'void adjust::senser::biz_senser_cb('),
        (0x25ffb28,'void infra_wrapper_bb::detail::initialize()'),
    ]:
        value=cstr(off(a))
        if not value.startswith(prefix):
            raise ValueError(f'Diagnostic identity mismatch {a:#x}')
        diagnostics[hex(a)]=value

    def mov32_pair(pc, expected, gap=4, reg=0):
        lo,hi = u32(pc),u32(pc+gap)
        if lo != (0x52800000 | ((expected & 0xffff) << 5) | reg):
            raise ValueError(f'MOVZ mismatch at {pc:#x}')
        if hi != (0x72a00000 | ((expected >> 16) << 5) | reg):
            raise ValueError(f'MOVK mismatch at {pc+gap:#x}')

    mov32_pair(0xc09c60,0x910040)
    mov32_pair(0xc09bbc-8,0x5503e0)
    mov32_pair(0xc0a200,0x5503e0)
    mov32_pair(0xc09b78,0x02010094,gap=8,reg=1)
    mov32_pair(0xc09fcc,0x02010094,gap=8,reg=1)
    mov32_pair(0xc1506c,0x01050244,gap=20)
    mov32_pair(0xc150a4,0x02170625,gap=16)
    edges = [call(a,t) for a,t in [
        (0xc09de4,0x12d9fc8),(0x12da020,0x12d8174),
        (0x12d8254,0x20ed13c),(0xc09df0,0xc14dfc),(0xc14dfc,0xc15060),
        (0xc15084,0xb17970),(0xc150b8,0xb17970),
        (0xc09e50,0xc09c14),(0xc09c68,0xb18c00),(0xc09c98,0xb17b30),
        (0xc09ce4,0xb18c00),(0xc09d04,0xc0924c),
        (0xc09c10,0xc09ac8),(0xc09bbc,0xb1a120),(0xc0a208,0xb19ec0),
        (0xc0a860,0x1397450),(0x1397494,0x1395c3c),(0xc0a870,0xdf91e8),
        (0xdf9230,0xdf8d6c),
    ]]
    lifecycle = []
    for pc in range(0x20ed13c,0x20ed260,4):
        if u32(pc) & 0xfc000000 == 0x94000000:
            lifecycle.append({'pc':hex(pc),'target':hex(target(pc))})
    lifecycle.append({'pc':'0x20ed25c','target':hex(target(0x20ed25c))})
    if len(lifecycle) != 70:
        raise ValueError('Expected 70 infrastructure initialization wrappers')
    bb_threads = [call(pc,0x222dd58) for pc in [0x20efa1c,0x20efa6c,0x20efabc,0x20efad8,0x20efaf4]]
    if u32(0xdf9204) != 0x52804aa0 or u32(0xdf9214) != 0xb81f8e60 or u32(0xdf921c) != 0x29067fa0:
        raise ValueError('Initial screen request/sentinel instruction mismatch')
    if u32(0xf2dedc) != 0x7109541f:
        raise ValueError('HOME controller invalid-screen comparison mismatch')
    result = {'input':{'path':str(path),'bytes':len(b),'sha256':digest},
        'invalid_screen_sentinel': {'hex':'0x255','decimal':597,
            'home_cmp_vma':'0xf2dedc','home_cmp_instruction_word':'0x7109541f'},
        'manager_initial_screen_request': {'hex':['0x255','0x0','0x255'],
            'decimal':[597,0,597], 'mov_vma':'0xdf9204','mov_instruction_word':'0x52804aa0'},
        'queue_roles': {'0x910040':'timer-service destination passed to osal_snd_sync_direct',
                        '0x5503e0':'App message queue, send and receive',
                        '0x02010094':'exec_utimer message word; App converter maps to type 5'},
        'call_edges':edges, 'infrastructure_initialization_wrappers':lifecycle,
        'diagnostic_strings':diagnostics,
        'bb_initialize_thread_creation_calls':bb_threads,
        'boundary':'Static producer/consumer dependency; no live queue contents or runtime root cause proved.'}
    if shim:
        sb=Path(shim).read_bytes();st=sb.decode()
        m=re.search(r'offs\[5\]\s*=\s*\{([^}]+)\}',st)
        result['shim']={'path':str(shim),'bytes':len(sb),'sha256':hashlib.sha256(sb).hexdigest(),
            'nop_offsets':[hex(int(x,16)) for x in re.findall(r'0x[0-9a-fA-F]+',m.group(1))] if m else []}
    return result


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('appfw',type=Path)
    ap.add_argument('--shim',type=Path)
    args=ap.parse_args()
    print(json.dumps(audit(args.appfw,args.shim),indent=2,ensure_ascii=False))
