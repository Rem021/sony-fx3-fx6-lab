#!/usr/bin/env python3
"""Read-only original FX3 UIPC/GPE audit; writes only adjacent proof JSON."""
from pathlib import Path
from io import BytesIO
import argparse
import hashlib
import json
import plistlib
import struct
import subprocess
import capstone
import elftools
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

HERE = Path(__file__).resolve().parent
VM = next(p for p in HERE.parents if (p / 'menu-repair-01').is_dir())
ORIGINAL = VM / 'menu-repair-01/original-uipc'
FILES = {
    'kernel': ORIGINAL / 'original-modules/osal_uipc.ko',
    'uipc': ORIGINAL / 'ap-projection/regular-files/usr/lib/libosal_uipc.so',
    'gpe': ORIGINAL / 'ap-projection/regular-files/usr/lib/libgpe.so',
    'obj': ORIGINAL / 'ap-projection/regular-files/usr/lib/libObj.so',
}
CS = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

class Binary:
    def __init__(self, path):
        self.path = path
        self.raw = path.read_bytes()
        self.elf = ELFFile(BytesIO(self.raw))
        self.symtab = self.elf.get_section_by_name('.symtab') or self.elf.get_section_by_name('.dynsym')
        self.symbols = list(self.symtab.iter_symbols())
        self.relocs = {}
        self.plt = {}
        self.relative = {}
        for sec in self.elf.iter_sections():
            if sec['sh_type'] != 'SHT_RELA':
                continue
            symbols = self.elf.get_section(sec['sh_link'])
            target = self.elf.get_section(sec['sh_info'])
            for r in sec.iter_relocations():
                s = symbols.get_symbol(r['r_info_sym'])
                name = s.name or (self.elf.get_section(s['st_shndx']).name if isinstance(s['st_shndx'], int) else str(s['st_shndx']))
                self.relocs[(target.name, r['r_offset'])] = {'symbol': name, 'addend': r['r_addend'], 'type': r['r_info_type']}
                if r['r_info_type'] == 1027:
                    self.relative[r['r_offset']] = r['r_addend']
            if sec.name == '.rela.plt':
                plt = self.elf.get_section_by_name('.plt')
                for i, r in enumerate(sec.iter_relocations()):
                    self.plt[plt['sh_addr'] + 32 + 16*i] = symbols.get_symbol(r['r_info_sym']).name

    def data(self, va, size, section='.text'):
        if self.elf['e_type'] == 'ET_REL':
            s = self.elf.get_section_by_name(section)
            assert 0 <= va <= va+size <= s['sh_size']
            return s.data()[va:va+size]
        for s in self.elf.iter_segments():
            if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= va and va+size <= s['p_vaddr']+s['p_filesz']:
                off = s['p_offset'] + va-s['p_vaddr']
                return self.raw[off:off+size]
        raise AssertionError((self.path, hex(va), size))

    def disasm(self, va, size, section='.text'):
        rows = []
        for i in CS.disasm(self.data(va, size, section), va):
            row = {'va': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
            rel = self.relocs.get((section, i.address))
            if rel:
                row['relocation'] = rel
            if i.mnemonic in ('b', 'bl') and i.op_str.startswith('#'):
                dst = int(i.op_str[1:], 16)
                row['callee'] = self.plt.get(dst) or next((s.name for s in self.symbols if s['st_value'] == dst and s['st_info']['type'] == 'STT_FUNC' and s['st_shndx'] != 'SHN_UNDEF'), hex(dst))
            rows.append(row)
        assert len(rows)*4 == size
        return rows

PINNED = {
    'kernel': '6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38',
    'uipc': '09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3',
    'gpe': '363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464',
    'obj': 'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
}

BLOCKS = {
    'kernel': [
        (0x7c0, 0xd0, 'dynamic-id ioctl copy/dispatch/return'),
        (0xfd0, 0xfc, 'receive ioctl delegates to original receive'),
        (0x2938, 0x48, 'queue lookup, no creation'),
        (0x2ee8, 0x278, 'queue creation and dynamic-range flag bit3'),
        (0x3160, 0xe8, 'queue statistics, creates missing node'),
        (0x3248, 0x300, 'alloc_msg and unfetched error/literal relocations'),
        (0x4198, 0x328, 'osal_rcv_msg_tmo and literals'),
        (0x44c0, 0x190, 'osal_valloc_msg_wait and literals'),
        (0x4d08, 0x60, 'osal_stat_msgq'),
        (0x5780, 0x5c0, 'osal_dynamic_id allocate/release and literals'),
    ],
    'uipc': [
        (0x3c60, 0x78, 'u_osal_rcv_msg_tmo: ioctl and negative errno'),
        (0x3e98, 0x90, 'u_osal_valloc_msg_wait: ioctl and negative errno'),
        (0x3fb0, 0x90, 'u_osal_dynamic_id: ioctl and negative errno'),
        (0x6468, 0x344, 'osal_rcv_msg_tmo dispatch by bit15'),
        (0x67b0, 0x1c0, 'osal_valloc_msg_wait dispatch by bit15'),
        (0x6e08, 0x50, 'osal_stat_msgq dispatch'),
        (0x75b8, 0x730, 'osal_dynamic_id: bit1 selects kernel delegation'),
    ],
    'gpe': [
        (0x9ba4, 0x168, 'original Main and one failure status attempt'),
        (0x9f64, 0x5c, 'SetCallback FIFO registration and interrupt-wait request'),
        (0xa110, 0xcc, 'SyncCallback and callback-before-status'),
        (0xa398, 0x98, 'new dynamic queue and receive/free helper'),
        (0xa430, 0x43c, 'synchronous/asynchronous command wrappers and Finish'),
        (0xaf08, 0x90, 'callback metadata and hardware command buffer submit'),
        (0xc760, 0x118, 'original Flush and DoCallback'),
        (0xd6b0, 0x204, 'native send/receive and SendDrawComp wrappers'),
        (0xda64, 0x110, 'completion thread: wait indication then opcode5'),
        (0x13430, 0x70, 'cglWaitIntrMC'),
        (0x14d34, 0xa8, 'IntrWaitBitCore waits original interrupt queue'),
    ],
    'obj': [
        (0xf4278, 0x64, 'CmdWorker constructor names grm_gpe'),
        (0xf4348, 0xcc, 'CmdWorker virtual slot3 dequeues and runs command'),
        (0xfb7bc, 0x84, 'command dequeue wrapper'),
        (0xf3f18, 0xe4, 'command queue selection'),
        (0x100c48, 0xb4, 'fill command invokes GpermFillRect'),
        (0x100dac, 0x3c, 'finish command invokes GpermFinish'),
        (0x1010cc, 0xcc, 'blit command invokes GpermBitBlit'),
        (0x1017ac, 0x1c4, 'GRM fill async construction'),
        (0x101970, 0x3b0, 'GRM blit async construction'),
    ],
}

# Semantic anchors supplement full-file hashes; assertions bind the explanations
# to actual decoded original instructions instead of self-written models alone.
ANCHORS = {
    'kernel': {
        0x828: 'bl #0x828', 0x1030: 'bl #0x1030',
        0x3080: 'sub w19, w19, #6, lsl #12',
        0x3094: 'orr w1, w1, #8', 0x3098: 'strb w1, [x21]',
        0x3298: 'tbnz w24, #0x1f, #0x3470',
        0x32a0: 'tbnz w0, #3, #0x33f8',
        0x33f8: 'ldr x0, [x21, #0x30]', 0x33fc: 'cbz x0, #0x3488',
        0x3470: 'tst x24, #0x70000000', 0x3474: 'b.ne #0x34b8',
        0x347c: 'tbz w0, #3, #0x34b8',
        0x3480: 'ldr x0, [x21, #0x30]', 0x3484: 'cbnz x0, #0x34b8',
        0x34a4: 'mov w0, #-0x3fa',
        0x43a4: 'bl #0x2ee8',
        0x57cc: 'and w23, w19, #0x10',
        0x57d8: 'ldr x20, #0x5cf8', 0x57e0: 'tbz w19, #2, #0x59e8',
        0x59e8: 'add x20, x20, #0x40',
        0x5b30: 'orr w0, w28, w0', 0x5b4c: 'str x0, [x3, #0x30]',
        0x5b54: 'orr w0, w0, #0x80000000',
        0x59b0: 'str xzr, [x23, #0x30]', 0x5c80: 'str xzr, [x23, #0x30]',
    },
    'uipc': {
        0x7600: 'tbnz w28, #1, #0x7980',
        0x7980: 'bl #0x2650', 0x65a0: 'bl #0x27a0', 0x6860: 'bl #0x2670',
        0x3ff4: 'bl #0x2530', 0x4038: 'neg w0, w0',
        0x6e50: 'b #0x25f0',
    },
    'gpe': {
        0xa3a0: 'mov w0, #0x2a', 0xa39c: 'mov w1, #0x82',
        0xa3b0: 'bl #0x8fd0', 0xa418: 'mov w0, #0x4a',
        0xa41c: 'bl #0x8fd0', 0xa3f0: 'bl #0x93c0',
        0xa7b4: 'bl #0xa398', 0xa800: 'str w19, [x29, #0x50]',
        0xa824: 'bl #0x9500', 0xa834: 'bl #0xa3d4',
        0xa850: 'stp xzr, xzr, [x2]', 0xa858: 'bl #0x9160',
        0xd79c: 'b.ne #0xd7a4', 0xd7a0: 'mov w2, #-1',
        0xd6dc: 'bl #0x8c40', 0xd73c: 'bl #0x8b30',
        0xd898: 'b #0xd6b0', 0xd8ac: 'mov w3, #1',
        0xa124: 'str wzr, [x1, #-4]!', 0xa128: 'bl #0x9050',
        0x9cb4: 'bl #0x8980', 0x9cc4: 'b #0x9c3c',
        0x9c4c: 'bl #0x9050',
        0xdac4: 'bl #0x89e0', 0xdafc: 'bl #0x9500',
        0x14d7c: 'bl #0x8bc0', 0x14db4: 'tst w20, w0',
    },
    'obj': {
        0xf4280: 'add x1, x1, #0x231',
        0xf4394: 'ldr x1, [x1, #0x18]', 0xf4398: 'blr x1',
        0x100dc0: 'bl #0x56050',
        0x101924: 'stp xzr, xzr, [x29, #0x90]',
    },
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def file_record(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def literal_string(binary, literal):
    r = binary.relocs[('.text', literal)]
    section = binary.elf.get_section_by_name(r['symbol'])
    assert section is not None
    b = section.data()[r['addend']:]
    return {'literal_text_offset': hex(literal), 'target_section': section.name,
            'target_offset': hex(r['addend']), 'text': b[:b.index(0)].decode('ascii')}

def evidence_lines(path, needles):
    found = []
    for i, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
        if any(n in line for n in needles):
            found.append({'line': i, 'text': line})
    return {**file_record(path), 'numbering': 'UTF-8 replacement decode then splitlines(), 1-based', 'matches': found}

def gate_model(qid, flags, owner):
    """Small symbolic evaluation of the anchored gate, NOT original execution."""
    trace = [0x3294, 0x3298]
    if qid & 0x80000000:
        trace += [0x3470, 0x3474]
        if qid & 0x70000000:
            return {'outcome': 'continue_allocation', 'trace': [hex(x) for x in trace+[0x34b8]]}
        trace += [0x3478, 0x347c]
        if not flags & 8:
            return {'outcome': 'continue_allocation', 'trace': [hex(x) for x in trace+[0x34b8]]}
        trace += [0x3480, 0x3484]
        if owner:
            return {'outcome': 'continue_allocation', 'trace': [hex(x) for x in trace+[0x34b8]]}
    else:
        trace += [0x329c, 0x32a0]
        if not flags & 8:
            return {'outcome': 'continue_allocation', 'trace': [hex(x) for x in trace+[0x32a4]]}
        trace += [0x33f8, 0x33fc]
        if owner:
            return {'outcome': 'continue_allocation', 'trace': [hex(x) for x in trace+[0x3400]]}
    trace += list(range(0x3488, 0x34b4, 4))
    return {'outcome': 'unfetched', 'return_if_debug_trap_disabled': -1018, 'trace': [hex(x) for x in trace]}

def cpio_members(candidate, binaries):
    v = json.loads(candidate.read_text())
    cp = Path(v['initrd']['path'])
    assert sha(cp) == v['initrd']['sha256'], 'Candidate initrd hash mismatch'
    wanted = {'usr/kmod/osal_uipc.ko': 'kernel', 'usr/lib/libosal_uipc.so': 'uipc',
              'usr/lib/libgpe.so': 'gpe', 'usr/lib/libObj.so': 'obj',
              'simulation/fx3-gpe-observe-v7.so': 'adapter'}
    result = {}
    with cp.open('rb') as f:
        while True:
            header = f.read(110)
            assert len(header) == 110 and header[:6] in (b'070701', b'070702')
            fields = [int(header[6+8*i:14+8*i], 16) for i in range(13)]
            size, name_len = fields[6], fields[11]
            assert 1 <= name_len <= 4096
            name = f.read(name_len).rstrip(b'\0').decode()
            f.seek((-f.tell()) % 4, 1)
            if name in wanted:
                b = f.read(size)
                key = wanted[name]
                match = b == binaries[key].raw if key in binaries else None
                if key in binaries:
                    assert match, name+' differs from audited original'
                result[name] = {'bytes': size, 'sha256': hashlib.sha256(b).hexdigest(), 'original_match': match}
            else:
                f.seek(size, 1)
            f.seek((-f.tell()) % 4, 1)
            if name == 'TRAILER!!!':
                break
    assert set(result) == set(wanted)
    return {'candidate': file_record(candidate), 'initrd': file_record(cp), 'selected_members': result}

def build_proof(volume):
    binaries = {name: Binary(path) for name, path in FILES.items()}
    proof = {
        'schema_version': 1,
        'scope': 'Read-only original binary static audit plus already captured run evidence; no QEMU, no adapter change, no original execution or camera operation.',
        'address_convention': {'kernel': 'ET_REL module .text-relative offset; runtime address requires that exact module loaded .text base.',
                               'uipc_gpe_obj': 'ET_DYN linked VA; runtime address = DSO load base + VA.'},
        'tools': {'capstone': capstone.__version__, 'pyelftools': elftools.__version__},
        'volume_uuid': volume['VolumeUUID'],
        'images': {}, 'validation': {},
    }
    for name, binary in binaries.items():
        assert hashlib.sha256(binary.raw).hexdigest() == PINNED[name], name+' original hash mismatch'
        image = {**file_record(binary.path), 'elf_type': binary.elf['e_type'], 'blocks': {}, 'anchors': {}}
        for a, n, label in BLOCKS[name]:
            rows = binary.disasm(a, n)
            image['blocks'][hex(a)] = {'label': label, 'size': n, 'bytes': binary.data(a, n).hex(), 'instructions': rows}
        for a, want in ANCHORS[name].items():
            got = binary.disasm(a, 4)[0]
            assert got['asm'].strip() == want, (name, hex(a), got['asm'], want)
            image['anchors'][hex(a)] = got
        proof['images'][name] = image
    k, g, u, o = (binaries[n] for n in ('kernel', 'gpe', 'uipc', 'obj'))
    assert k.relocs[('.text', 0x828)]['symbol'] == 'osal_dynamic_id'
    assert k.relocs[('.text', 0x1030)]['symbol'] == 'osal_rcv_msg_tmo'
    assert k.relocs[('.text', 0x5cf8)] == {'symbol': '.data', 'addend': 0x640, 'type': 257}
    assert k.relocs[('.text', 0x5d28)] == {'symbol': '.bss', 'addend': 0x2640, 'type': 257}
    assert g.plt[0x8fd0] == 'osal_dynamic_id'
    assert g.plt[0x93c0].startswith('_ZN5mpgpe7message15ReceiveDrawComp')
    assert u.plt[0x2650] == 'u_osal_dynamic_id'
    assert o.relative[0x261530] == 0x252d40
    assert o.relative[0x252d68] == 0xf4348
    assert o.relative[0x261410] == 0x253748
    assert o.relative[0x253770] == 0x100dac
    assert o.data(0x1e0231, 8) == b'grm_gpe\0'
    proof['obj_virtual_binding'] = {
        'CmdWorker_name_va': '0x1e0231', 'constructor': '0xf4278',
        'GOT_vtable_261530_relative': hex(o.relative[0x261530]),
        'vptr': '0x252d50', 'slot18_relocation_at': '0x252d68', 'slot18_main': '0xf4348',
        'finish_command_vptr': '0x253758', 'finish_command_slot18': hex(o.relative[0x253770]),
    }
    d = k.elf.get_section_by_name('.data').data()
    assert struct.unpack_from('<II', d, 0x640+16) == (0x6000, 0x2000)
    assert struct.unpack_from('<II', d, 0x680+16) == (0x6000, 0x1000)
    proof['dynamic_queue'] = {
        'lookup_root': '.bss+0x2640', 'lookup_function': '.text+0x2938',
        'descriptor_array_base': '.data+0x640',
        'GPE_flags': '0x2a',
        'pool_selection': 'bit4 clear selects message ID; bit2 clear branches at .text+0x57e0 to .text+0x59e8 and adds0x40',
        'pool_descriptor': '.data+0x680', 'pool_start': '0x6000', 'pool_count': 0x1000,
        'dynamic_node_range': ['0x6000', '0x7fff'],
        'flag_dynamic': {'field': 'q+0x0:u8', 'mask': 8, 'set_va': '.text+0x3094..0x3098'},
        'fetched_owner': {'field': 'q+0x30:u64', 'meaning_for_dynamic': 'nonzero allocation owner token, not a receiver-has-waited flag',
                          'set_va': '.text+0x5b4c', 'value_for_observed_id': '0x008261c0',
                          'clear_va': ['.text+0x59b0', '.text+0x5c80'],
                          'cleared_by': 'dynamic ID release; warning path also clears after reporting pending counts'},
        'unfetched_gate_for_observed_id': '(q[0] & 8) != 0 && *(u64*)(q+0x30) == 0',
        'general_gate_after_valid_queue_lookup': '(q[0]&8) && owner==0 && (!(qid&0x80000000) || !(qid&0x70000000))',
        'not_checked_by_gate': ['receiver wait-list q+8', 'whether osal_rcv_msg_tmo has been called', 'first vs later receive'],
        'error_return': -1018, 'debug_guard': 'uipc_opt byte+0x17 nonzero traps at .text+0x34b4 instead of returning normally',
        'error_literals': [literal_string(k, a) for a in (0x3530, 0x5d18, 0x5d20, 0x5d30)],
    }
    assert 'unfetched dynamic queue' in proof['dynamic_queue']['error_literals'][0]['text']
    cases = [
        ('unclaimed_before_receive', 0x808261c0, 8, 0, 'unfetched'),
        ('claimed_before_first_receive', 0x808261c0, 8, 0x8261c0, 'continue_allocation'),
        ('claimed_after_receive', 0x808261c0, 8, 0x8261c0, 'continue_allocation'),
        ('released_despite_historical_receive', 0x808261c0, 8, 0, 'unfetched'),
        ('ordinary_non_dynamic', 0x80820884, 0, 0, 'continue_allocation'),
        ('remote_destination_bypasses_local_gate', 0x908261c0, 8, 0, 'continue_allocation'),
        ('non_topbit_dynamic_unclaimed', 0x008261c0, 8, 0, 'unfetched'),
    ]
    proof['symbolic_gate_cases'] = []
    for label, qid, flags, owner, want in cases:
        got = gate_model(qid, flags, owner)
        assert got['outcome'] == want
        proof['symbolic_gate_cases'].append({'label': label, 'qid': hex(qid), 'flags': flags, 'owner': hex(owner), **got})
    proof['symbolic_gate_case_scope'] = 'Python evaluation derived from checked original branch instructions; not emulation, runtime test, or proof of queue contents in the failed run.'
    proof['original_order'] = [
        {'stage': 'sync wrapper', 'va': 'libgpe+0xa7ac..0xa7b4', 'effect': 'async=0 calls a398 before constructing/sending command'},
        {'stage': 'allocate', 'va': 'libgpe+0xa39c..0xa3b0; libosal+0x7600/0x7980; kernel .text+0x828', 'effect': 'osal_dynamic_id(0x2a,0x82,&Q), kernel path, fresh logical acquisition'},
        {'stage': 'claim', 'va': 'kernel .text+0x5b28..0x5b88', 'effect': 'store owner at q+0x30, add bit31 to returned Q, mark allocator bitmap before unlock/return'},
        {'stage': 'send', 'va': 'libgpe+0xa800/0xa824', 'effect': 'completion Q at header+8, original SendDraw'},
        {'stage': 'receive', 'va': 'libgpe+0xa834 -> 0xa3d4 -> 0xd89c -> 0xd774; kernel .text+0x4198', 'effect': 'blocking receive timeout=-1; does not claim q+0x30'},
        {'stage': 'consume/free', 'va': 'libgpe+0xd7e0..0xd80c', 'effect': 'copy up to4B actual status and free actual message'},
        {'stage': 'release', 'va': 'libgpe+0xa410..0xa41c; kernel .text+0x59b0/0x5a00', 'effect': 'osal_dynamic_id(0x4a,0,(void*)Q), owner zero, allocator bitmap released; numeric Q may recur'},
    ]
    proof['hardware_completion_order'] = {
        'flush': 'c760 -> af08/9f64 CallbackFifo -> SendWaitIntr, af30 -> CMF::Set hardware command',
        'completion_thread': 'da64 ReceiveWaitIntr -> dac4 cglWaitIntrMC -> dafc sends opcode5',
        'wait_core': '13470 -> 14d34 original OSAL interrupt queue wait, indication bit check14db4',
        'main': '9cc8 -> c800 DoCallback -> a158 callback -> a110 SyncCallback -> d888 SendDrawComp',
        'proven': 'original completion is mediated by hardware indication and FIFO, while software adapter completes inline',
        'not_proven': 'real-camera latency, or an ordering requirement that the requester has entered receive before completion',
    }
    r = VM/'menu-repair-01/runtime'
    model_names = ['fx3-gpe-observe-v24-serial102.c', 'fx3-gpe-observe-v24-serial102.so',
                   'fx3-gpe-observe-v24-serial102-build.json', 'fx3-gpe-backend-v8.c',
                   'fx3-gpe-backend-v8.h', 'ioctl-trace-v12.c']
    proof['current_models'] = {n: file_record(r/'helpers'/n) for n in model_names}
    build = json.loads((r/'helpers/fx3-gpe-observe-v24-serial102-build.json').read_text())
    assert proof['current_models'][model_names[0]]['sha256'] == build['source_sha256']
    assert proof['current_models'][model_names[1]]['sha256'] == build['output_sha256']
    assert proof['current_models']['fx3-gpe-backend-v8.c']['sha256'] == build['pixel_math_backend_v8_unchanged']
    proof['model_completion_source'] = evidence_lines(r/'helpers'/model_names[0],
        ['execution[ao]=1', 'if(cb){struct gpe_callback_param', 'if(!raw[ao]&&src)',
         'if(result&&reason==GPE_DELIVERY)', 'Nonzero is returned to original Main'])
    proof['observer_dedup_source'] = evidence_lines(r/'helpers/ioctl-trace-v12.c',
        ['waits[i].tid==tid', 'if(i==wait_count', 'command==7&&outer_read'])
    candidate = r/'ap103-r2-soft-ldec/candidate.json'
    proof['cpio_original_binding'] = cpio_members(candidate, binaries)
    cp_adapter = proof['cpio_original_binding']['selected_members']['simulation/fx3-gpe-observe-v7.so']
    assert cp_adapter['sha256'] == build['output_sha256']
    ap103 = r/'runs/ap103v4ldec600-71ce5752'
    receipt = json.loads((ap103/'receipt.json').read_text())
    assert receipt['candidate_sha256'] == sha(candidate)
    proof['runtime_evidence'] = {
        'AP70': evidence_lines(r/'runs/ap70lcd-f61554d9/serial.log', ['FX3_UIPC_RECV_BEGIN tid=229 name=grm_gpe queue=0x808261c0']),
        'AP102_r2': evidence_lines(r/'runs/ap102r2save600-e15f61fb/serial.log', ['unfetched dynamic queue', 'print_task_info: MPGRM_GPE0', 'FX3_GPE_REJECT_DETAIL']),
        'AP103_r4': evidence_lines(ap103/'serial.log', ['unfetched dynamic queue', 'FX3_GPE_REJECT_DETAIL', 'FX3_GPE_CMD op=Flush', 'FX3_UIPC_RECV_BEGIN tid=274 name=grm_gpe']),
        'AP103_r4_printk': evidence_lines(ap103/'printk-decoded.txt', ['unfetched dynamic queue', 'print_task_info: MPGRM_GPE0', 'warning ret = -1018']),
        'review': file_record(r/'ap103-runtime-review-v1.json'), 'receipt': file_record(ap103/'receipt.json'),
    }
    pk = json.loads((ap103/'printk-decoded.json').read_text())
    proof['runtime_evidence']['AP103_r4_printk_structured'] = {
        **file_record(ap103/'printk-decoded.json'),
        'records': [x for x in pk['records'] if any(n in x['text'] for n in ['unfetched dynamic queue', 'print_task_info: MPGRM_GPE0', 'warning ret = -1018'])],
    }
    rows = proof['runtime_evidence']['AP103_r4']['matches']
    assert sum('unfetched dynamic queue' in x['text'] for x in rows) == 2
    assert any('seq=437 op=4' in x['text'] and 'errno=1018' in x['text'] for x in rows)
    assert any('queue=0x808261c0' in x['text'] and 'RECV_BEGIN' in x['text'] for x in rows)
    review = json.loads((r/'ap103-runtime-review-v1.json').read_text())
    assert review['overall_health_pass'] is False
    proof['runtime_evidence']['review_open_gate'] = review['reason']
    proof['verdict'] = {
        'first_receive_claims_dynamic_queue_hypothesis': 'refuted by original code',
        'early_software_completion_alone_causes_unfetched': 'refuted for a correctly acquired and unreleased original sync transaction',
        'actual_failure_condition': 'the looked-up dynamic queue owner field was zero at allocation; exact cause of zero in that transaction is not captured',
        'hardware_vs_software_schedule_difference': 'proven statically, insufficient to establish this runtime failure cause',
        'proposed_delay_until_rcv': 'not justified; receive does not set owner, historical receive is not a generation token',
        'implemented_fix': False,
    }
    proof['unconfirmed'] = [
        'Which dynamic-id generation owns Flush437 and why its owner became zero; no paired allocation/release trace or queue-state snapshot exists in the inspected evidence.',
        'Whether an early/duplicate release, unrelated thread, queue reuse, or memory corruption caused the zero owner; none is proven.',
        'Numeric QID reuse alone does not identify one transaction; current receive logs deduplicate by (tid,QID), without a per-acquisition epoch.',
        'Absolute real-camera interrupt latency and whether the camera requester has entered receive before completion.',
        'AP103 full600/date/save and fourth-run API16 restoration remain unaccepted according to supplied review; this audit does not close them.',
        'No adapter repair or runtime validation was performed; no QEMU was started.',
    ]
    proof['validation'] = {
        'result': 'passed', 'pinned_original_sha256': PINNED,
        'instruction_anchor_count': sum(len(x) for x in ANCHORS.values()),
        'symbolic_gate_cases': len(cases), 'selected_cpio_originals_equal': True,
        'all_original_inputs_unchanged_after_analysis': all(sha(FILES[n]) == PINNED[n] for n in FILES),
        'official_tool_reference': 'https://www.capstone-engine.org/lang_python.html',
        'reference_scope': 'Capstone API only, checked 2026-11-02 America/Los_Angeles; Sony semantics from local original code.',
    }
    assert proof['validation']['all_original_inputs_unchanged_after_analysis']
    (HERE/'unfetched-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
    print('PASS: regenerated', HERE/'unfetched-proof.json')
    print('Original-code verdict: dynamic-id acquisition claims queue before SendDraw; first rcv does not claim it. Runtime zero-owner cause remains unproven.')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', nargs=3, metavar=('BINARY', 'VA', 'SIZE'))
    ap.add_argument('--symbols', choices=FILES)
    args = ap.parse_args()
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume.get('VolumeUUID', '').upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    if args.dump:
        name, va, size = args.dump
        for r in Binary(FILES[name]).disasm(int(va, 0), int(size, 0)):
            print(r['va'], r['asm'], r.get('relocation', r.get('callee', '')))
        return
    if args.symbols:
        for s in Binary(FILES[args.symbols]).symbols:
            if s['st_info']['type'] == 'STT_FUNC' and s['st_shndx'] != 'SHN_UNDEF':
                print(hex(s['st_value']), hex(s['st_size']), s.name)
        return
    build_proof(volume)

if __name__ == '__main__':
    main()
