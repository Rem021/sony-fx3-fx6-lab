#!/usr/bin/env python3
"""Read-only original-ELF/saved-log audit; default writes only adjacent proof JSON.

Run with the existing capstone venv and -B. No guest process/device/VM access.
"""
import hashlib
import json
import plistlib
import re
import struct
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / 'work/sony-firmware-20261024').is_dir())
TASK = ROOT / 'work/fx3-vm-20261101'
RT = TASK / 'menu-repair-01/runtime'
PROJECTION = RT.parent / 'original-uipc/ap-projection/regular-files'
assert plistlib.loads(subprocess.check_output(
    ['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))['VolumeUUID'].upper() == \
    'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

FILES = {'appFw.so': 'usr/lib/appFw.so',
         'libpthread-2.25.so': 'lib/libpthread-2.25.so',
         'libstdc++.so.6.0.22': 'usr/lib/libstdc++.so.6.0.22'}
EXPECTED = {
    'appFw.so': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'libpthread-2.25.so': '7394f861930c45dd5076a700da5755faf0f6bed08544b0d60eadb85a14a7d592',
    'libstdc++.so.6.0.22': '28f2d082aea5206c42ba15664f39e2eaf7febed8f6264305e7e16aa44c878389'}


class Image:
    def __init__(self, name):
        self.path = PROJECTION / FILES[name]
        self.raw = self.path.read_bytes()
        self.f = self.path.open('rb')
        self.e = ELFFile(self.f)
        self.segs = [s for s in self.e.iter_segments() if s['p_type'] == 'PT_LOAD']
        self.cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        self.syms = {s.name: (s['st_value'], s['st_size'])
                     for s in self.e.get_section_by_name('.dynsym').iter_symbols()}
        self.plt = {}
        rel = self.e.get_section_by_name('.rela.plt')
        if rel:
            sy = self.e.get_section(rel['sh_link'])
            pv = self.e.get_section_by_name('.plt')['sh_addr']
            self.plt = {pv + 32 + 16*n: sy.get_symbol(r['r_info_sym']).name
                        for n, r in enumerate(rel.iter_relocations())}
        self.ptrs = defaultdict(list)
        for sec in self.e.iter_sections():
            if sec['sh_type'] != 'SHT_RELA':
                continue
            sy = self.e.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                idx = r['r_info_sym']
                sym = sy.get_symbol(idx) if idx else None
                val = (sym['st_value'] if sym else 0) + r['r_addend']
                self.ptrs[val].append({'slot': hex(r['r_offset']),
                                       'symbol': sym.name if sym else '',
                                       'type': r['r_info_type']})
        self.rev = None

    def read(self, va, size):
        s = next(s for s in self.segs
                 if s['p_vaddr'] <= va and va+size <= s['p_vaddr']+s['p_filesz'])
        off = s['p_offset'] + va - s['p_vaddr']
        return self.raw[off:off+size]

    def qword(self, va):
        return int.from_bytes(self.read(va, 8), 'little')

    def cstr(self, va):
        return self.read(va, 256).split(b'\0')[0].decode(errors='replace')

    def dis(self, va, size):
        rows = []
        for i in self.cs.disasm(self.read(va, size), va):
            d = {'va': hex(i.address), 'bytes': i.bytes.hex(),
                 'asm': i.mnemonic + ' ' + i.op_str}
            if i.mnemonic in ('b', 'bl') and i.op_str.startswith('#'):
                d['symbol'] = self.plt.get(int(i.op_str[1:], 16), '')
            rows.append(d)
        assert len(rows)*4 == size, (hex(va), size, len(rows))
        return rows

    def xref(self, va):
        if self.rev is None:
            self.rev = defaultdict(list)
            for sec in self.e.iter_sections():
                if not sec['sh_flags'] & 4:
                    continue
                b = sec.data()
                for k, (w,) in enumerate(struct.iter_unpack('<I', b[:len(b)//4*4])):
                    if w & 0x7c000000 != 0x14000000:
                        continue
                    imm = w & 0x3ffffff
                    if imm & (1 << 25):
                        imm -= 1 << 26
                    pc = sec['sh_addr'] + k*4
                    self.rev[pc+4*imm].append({'va': hex(pc),
                                              'kind': 'bl' if w >> 31 else 'b'})
        return {'branches': self.rev.get(va, []), 'relocations': self.ptrs.get(va, [])}

    def vtable(self, header, slot):
        ti = self.qword(header+8)
        return {'header': hex(header), 'typeinfo': hex(ti),
                'rtti_name_va': hex(self.qword(ti+8)),
                'rtti': self.cstr(self.qword(ti+8)), 'slot': hex(slot),
                'offset': hex(slot-header-16), 'function': hex(self.qword(slot))}


# Complete selected windows, including the whole large boot initialization body.
WINDOWS = {
    'appFw.so': [
        (0x16f1d08, 0x16c), (0x16f2098, 0x16c), (0x16f2220, 0x484),
        (0x27381b8, 8), (0x2eacc48, 0x120), (0x21916b0, 0x2d8),
        (0x219209c, 0x268), (0x2380778, 0x34), (0x237fe28, 0x950),
        (0x285f3b4, 0xa0), (0x285dc98, 0x171c),
        (0x2aa1648, 0x6c), (0x2aa222c, 0x2f0),
        (0x273b240, 0xb0), (0x271a368, 0x58),
        (0x27391b4, 0x4a8), (0x2718424, 0x2c),
        (0x2c214f0, 0x60), (0x2c20ce8, 0x40),
        (0x2b68330, 0x64), (0x2b638b8, 0x4a78),
        (0x2b66d80, 0xf4), (0x2b67a60, 0x48),
        (0x2b6353c, 0x148), (0x2dd0754, 0x40),
        (0x2debbb4, 0x1a4), (0x2e10c80, 0xc0),
        (0x1724c98, 0x34), (0x16ed554, 0x20)],
    'libpthread-2.25.so': [(0xd4d8, 0x2ec)],
    'libstdc++.so.6.0.22': [(0xb3600, 0x20)]}


def build():
    proof = {'scope': 'Offline original ELF and saved runs only; writes only adjacent proof',
             'line_rule': '1-based LF split of decoded bytes; preserve CR and NUL',
             'evidence_levels': {'A': 'original instructions/relocations or captured data',
                                 'B': 'constrained attribution from A, no live pointer read',
                                 'U': 'not established'},
             'sources': {}, 'blocks': {}, 'xrefs': {}, 'runs': {}}

    def source(path):
        raw = path.read_bytes()
        proof['sources'][str(path.relative_to(ROOT))] = {
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        return raw

    ims = {name: Image(name) for name in FILES}
    for name, im in ims.items():
        assert hashlib.sha256(source(im.path)).hexdigest() == EXPECTED[name]
        proof['blocks'][name] = {hex(v): im.dis(v, n) for v, n in WINDOWS[name]}
    a = ims['appFw.so']
    must = {
        0x16f22b8: 'bl #0x27381b8',
        0x16f2188: 'bl #0x16f1d08',
        0x2192274: 'bl #0x21916b0',
        0x219191c: 'blr x2',
        0x2380794: 'bl #0x237fe28',
        0x2380700: 'bl #0x285f3b4',
        0x285f41c: 'bl #0x285dc98',
        0x285e400: 'bl #0x15937a0',
        0x285e40c: 'bl #0x2aa1648',
        0x285e420: 'bl #0x273b240',
        0x285e424: 'bl #0x27391b4',
        0x285e42c: 'bl #0x2aa222c',
        0x2aa2294: 'bl #0x1592d30',
        0x273b298: 'bl #0x271a368',
        0x271a390: 'mov w1, #0x1f',
        0x271844c: 'b #0x2c214f0',
        0x2c21524: 'bl #0x2c20ce8',
        0x2c20d20: 'str x0, [x19, #0x1b8]',
        0x2b68370: 'bl #0x2b638b8',
        0x2b68388: 'ldr x0, [x19, #0x1b8]',
        0x2b6838c: 'bl #0x2aa1668',
        0x2aa168c: 'strb w0, [x20]',
        0x2aa16b0: 'b #0x1593f80',
        0x2b66f28: 'bl #0x2dd0754',
        0x2dd077c: 'bl #0x2debbb4',
        0x2b67674: 'bl #0x2b63224',
        0x2b67a6c: 'bl #0x2b6353c'}
    proof['checked_instructions'] = {}
    for va, asm in must.items():
        row = a.dis(va, 4)[0]
        assert row['asm'] == asm, row
        proof['checked_instructions'][hex(va)] = row
    for name, va, asm in [
        ('libpthread-2.25.so', 0xd4d8, 'stp x29, x30, [sp, #-0xd0]!'),
        ('libpthread-2.25.so', 0xd54c, 'add x19, x20, #0x28'),
        ('libpthread-2.25.so', 0xd5ec, 'svc #0'),
        ('libstdc++.so.6.0.22', 0xb3600, 'stp x29, x30, [sp, #-0x10]!')]:
        assert ims[name].dis(va, 4)[0]['asm'] == asm
    assert ims['libstdc++.so.6.0.22'].plt[0x8a780] == 'pthread_cond_wait'
    proof['stdlib_binding'] = {'libstdc++:0xb360c': {'target_plt': '0x8a780',
                                                       'symbol': 'pthread_cond_wait'}}
    proof['vtables'] = [a.vtable(0x455b220, 0x455b2b8),
                        a.vtable(0x46e4fd0, 0x46e4ff0)]
    assert proof['vtables'][0]['rtti'] == '23scr0039_boot_controller'
    assert proof['vtables'][1]['rtti'] == 'N5model13sequence_bootE'
    assert a.qword(0x47a8a70) == 0x46e4fd0
    assert a.qword(0x4029278+0x1f*8) == 0x2718424
    proof['data_bindings'] = {'0x47a8a70': hex(a.qword(0x47a8a70)),
                              '0x4029370': hex(a.qword(0x4029370)),
                              **{hex(v): hex(a.qword(v)) for v in
                                 [0x472c3c0, 0x472b2d0, 0x474f098, 0x47a6698]}}
    proof['strings'] = {hex(v): a.cstr(v) for v in [
        0x3135aa0, 0x391a6e8, 0x3801ea0, 0x3801f18]}
    for va in [0x2380778, 0x2aa1668, 0x2aa16b4, 0x2b68330, 0x2aa222c]:
        proof['xrefs'][hex(va)] = a.xref(va)

    names = ['ap70lcd-f61554d9', 'ap75final1-a67fe198', 'ap75final2-4d01e9f8',
             'ap76sync-fe30bc21', 'ap76corr-316e20b7',
             'ap77agate-f63dd39e', 'ap77bcount0-b9abfcab']
    for name in names:
        run = RT / 'runs' / name
        ls = source(run/'serial.log').decode(errors='replace').split('\n')
        result = {'snapshots': [], 'pthread_maps': [], 'events': [], 'profiles': []}
        for j, line in enumerate(ls):
            if re.match(r'[0-9a-f]+-[0-9a-f]+ r-xp 00000000 ', line) and 'libpthread-' in line:
                result['pthread_maps'].append({'line': j+1, 'text': line})
            if 'Name:\tAppFw' in line:
                begin = j-1
                tid = re.search(r'FX3_TASK_SNAPSHOT_(\d+)_BEGIN', ls[begin]).group(1)
                end = next(k for k in range(j+1, min(j+100, len(ls)))
                           if f'FX3_TASK_SNAPSHOT_{tid}_END' in ls[k])
                syscall = next((k for k in range(j, end) if re.match(r'98 0x', ls[k])), None)
                item = {'begin_line': begin+1, 'end_line': end+1,
                        'tid': int(tid), 'lines': ls[begin:end+1]}
                if syscall is not None:
                    vals = ls[syscall].split()
                    addr, sp, pc = [int(vals[k], 16) for k in [1, 7, 8]]
                    base = int(result['pthread_maps'][-1]['text'].split('-')[0], 16)
                    # pthread_cond_wait + libstdc++ wait + model_future::wait frames.
                    outer = sp + 0xd0 + 0x10 + 0x90
                    expected = outer + 0x108 + 8 + 0x28
                    item.update({'syscall_line': syscall+1, 'futex': hex(addr),
                                 'op': vals[2], 'sp': hex(sp), 'pc': hex(pc),
                                 'pthread_relative_pc': hex(pc-base),
                                 'candidate_285dc98_fp': hex(outer),
                                 'candidate_event': hex(outer+0x108),
                                 'candidate_condition_variable': hex(outer+0x110),
                                 'predicted_futex': hex(expected), 'fit': expected == addr,
                                 'attribution_level': 'B: stack fit plus original path; no saved user-memory unwind'})
                    assert pc-base == 0xd5f0, (name, item)
                    assert addr == expected, (name, item)
                result['snapshots'].append(item)
            if name != 'ap77agate-f63dd39e':
                continue
            if any(key in line for key in [
                'FX3_UI_GATE_SAMPLE id=11 ', 'FX3_UI_GATE_SAMPLE id=4 ',
                'FX3_UI_GATE_SAMPLE id=5 ', 'FX3_UI_GATE_SAMPLE id=6 ',
                'target=0x9059000e', 'Skip snd to 0xe\r',
                'FX3_BOOT_GATE_SAMPLE ', 'FX3_BOOT_QUEUE_SEND tid=289 ',
                'FX3_UI_GATE_BOUND', 'FX3_UI_GATE_SELFTEST']):
                result['events'].append({'line': j+1, 'text': line})
            if 'FX3_PROFILE_STACK_BEGIN' in line and 'tid=289 ' in line:
                # Other threads may interleave BEGIN/END for the same destination.
                # The wrapper's same-TID BOOT_QUEUE_SEND is the unambiguous end.
                if 'destination=0x5503e0 ' in line:
                    end = next(k for k in range(j+1, j+100)
                               if 'FX3_BOOT_QUEUE_SEND tid=289 ' in ls[k])
                else:
                    end = next(k for k in range(j+1, j+70) if 'FX3_PROFILE_STACK_END' in ls[k])
                result['profiles'].append({'begin_line': j+1, 'end_line': end+1,
                                           'interleaving_note': 'raw bounded context; do not assign another thread\'s interleaved frames to tid289',
                                           'lines': ls[j:end+1]})
        if name == 'ap77agate-f63dd39e':
            dq = [x for x in result['events'] if 'id=11 ' in x['text']]
            assert len(dq) == 2 and 'type=0x150000 ' in dq[0]['text'] and 'type=0x30072 ' in dq[1]['text']
            assert len(result['snapshots']) == 3
            sender = [x for x in result['events'] if 'raw=720003' in x['text']]
            assert len(sender) == 1
            raw = re.search(r'raw=(\w+)', sender[0]['text']).group(1)
            assert bytes.fromhex(raw) == struct.pack('<I', 0x30072)+bytes(24)
            result['message'] = {'bytes': 28, 'source': '0x830128',
                                 'target': '0x5503e0', 'payload_hex': raw,
                                 'sender_tid': 289, 'send_line': sender[0]['line']}
            result['sequence_snapshots'] = []
            for j, line in enumerate(ls):
                if 'FX3_TASK_SNAPSHOT_327_BEGIN' in line:
                    end = next(k for k in range(j+1, j+100) if 'FX3_TASK_SNAPSHOT_327_END' in ls[k])
                    result['sequence_snapshots'].append({'begin_line': j+1, 'end_line': end+1,
                                                         'lines': ls[j:end+1]})
            printk = run/'printk-decoded.txt'
            pl = source(printk).decode(errors='replace').split('\n')
            result['printk_matches'] = [{'line': j+1, 'text': line} for j, line in enumerate(pl)
                                        if 'Skip snd to 0xe' in line or '9059000e' in line]
        assert result['snapshots'], name
        proof['runs'][name] = result
    # Fixed saved counter decode adds raw RAM provenance; no rerun of VM/runner.
    for rel in ['ap77a-gate-readback.json', 'helpers/fx3-ui-gate-v1.c']:
        path = RT/rel
        if path.exists():
            raw = source(path)
            if path.suffix == '.json':
                proof['saved_gate_readback'] = json.loads(raw)
                counts = proof['saved_gate_readback']['counts']
                assert [counts[str(i)] for i in [9, 10, 11, 16, 22]] == [11381, 1, 2, 0, 0]
            else:
                lines = raw.decode().split('\n')
                proof['gate_observer_source'] = [
                    {'line': j+1, 'text': line} for j, line in enumerate(lines)
                    if 'if(id==11)' in line or 'const U offsets[31]' in line]
    source(RT/'runs/ap77agate-f63dd39e/ui-gate-counters.bin')
    proof['findings'] = [
        {'level': 'A', 'claim': '30072 is a self-enqueued startup message from AppFw16f22b8 through27381b8/2eacc48; 830128 is internal source class, not the boot worker TID'},
        {'level': 'A', 'claim': 'scr0039_boot_controller virtual+88=2380778 accepts30072 and calls237fe28/process_power_on; captured side-effect stacks connect2191920->2380798->2380704->285f420->285e3f8'},
        {'level': 'A', 'claim': '285e42c calls model_future::wait2aa222c; 2aa2294 imports std::condition_variable::wait, not std::future::get or OSAL synchronous receive'},
        {'level': 'A', 'claim': 'saved syscall PC minus mapped libpthread base isd5f0, directly after pthread_cond_wait futex SVCd5ec'},
        {'level': 'B', 'claim': 'futex object is boot initialization stack event: all selected runs fit SP+d0+10+90+108+8+28 exactly; no saved full user stack or event/sequence pointer memory read'},
        {'level': 'A', 'claim': 'command1f factory preserves event pointer in sequence_boot+1b8; sequence_boot::run2b68330 calls2b638b8 then2aa1668(event), which sets byte0 and notifies condition_variable at+8'},
        {'level': 'B', 'claim': 'AP77a SeqQueueCommon327 is the most likely notifier; its timecode no-reply wait prevents boot returning to notify, with get-func and four-task barrier still ahead'},
        {'level': 'U', 'claim': 'live event equality sequence_boot+1b8 ==285dc98-frame+108, run-return/notify and subsequent UI/render/menu behavior need runtime observation'},
        {'level': 'U', 'claim': 'model_future wait simple/cooperative branch: both2aa2294 and2aa23a4 wait on event cv;2aa2464 additionally waits on per-thread coordination cv; no saved LR distinguishes exact callsite'},
        {'level': 'A', 'claim': 'notify follows return of boot body, including error early-return paths; notify alone cannot certify successful four-task boot completion'}]
    proof['observation_points'] = {
        '0x285e42c': 'x20=model_future{event*,event+4,cv*}; record [x20], [x20+10], byte[event], w[event+4]',
        '0x2aa2294': 'x0=cv*, x1=unique_lock*; record pointers only; no wait/signal mutation',
        'libstdc++:0xb3600': 'x0=cv*, x1=unique_lock*, x30=caller LR:2aa2298/2aa23a8/2aa2468, TID; distinguish simple/cooperative wait and coordination object',
        '0x2c20d20': 'x19=sequence_boot*, x0=event* before store+1b8',
        '0x2b68370': 'x19=sequence_boot*; entry into boot body; matched run TID',
        '0x2b68374': 'boot body returned; x19 and [x19+1b8]',
        '0x2aa1668': 'x0=event*, caller/LR should2b68390 for this run; byte0 before/after',
        '0x2aa16b0': 'x0=event+8 (cv*) immediately before notify_one tail call',
        '0x2aa2298': 'condition_variable wait has returned; compare captured event identity',
        '0x285e430': 'model_future wait returned; destructor and further setup follow',
        '0x16f2698': 'second dequeue processing returned; outer loop may still apply backlog gate',
        '0x16f2640': 'actual timer/draw call; no guarantee solely from notify'}
    target = OUT/'appfw-30072-proof.json'
    target.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
    print('PASS: original hashes, selected complete decode, command/event/notify chain, AP77 two dequeues, seven-run futex fits; rebuilt '+target.name)
    for name, run in proof['runs'].items():
        print(name, 'snapshots='+str(len(run['snapshots'])),
              'PC='+run['snapshots'][0].get('pthread_relative_pc', 'not-futex'),
              'fit='+str(all(s.get('fit') for s in run['snapshots'])))


if __name__ == '__main__':
    if len(sys.argv) == 1:
        build()
    else:
        mode, name, *args = sys.argv[1:]
        im = Image(name)
        if mode == 'dis':
            for row in im.dis(int(args[0], 16), int(args[1], 16)):
                print(row['va'], row['asm'], row.get('symbol', ''))
        elif mode == 'xref':
            print(json.dumps({v: im.xref(int(v, 16)) for v in args}, indent=2))
        elif mode == 'sym':
            print(json.dumps({n: [hex(v), hex(size)] for n, (v, size) in im.syms.items()
                              if re.search(args[0], n)}, indent=2))
        else:
            raise SystemExit('Use dis, xref or sym, or no arguments to rebuild proof')
