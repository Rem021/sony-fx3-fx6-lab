#!/usr/bin/env python3
"""Rebuild an offline evidence audit; only writes adjacent menu-layers-proof.json.

No QEMU, QMP, device, guest, lock, or other audit rebuild is invoked. Unicorn
replays only original descriptor builders with every external call intercepted.
Missing source pixels and hardware arithmetic remain explicitly unproven.
"""
from pathlib import Path
from io import BytesIO
import collections
import hashlib
import json
import plistlib
import re
import runpy
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
from unicorn import arm64_const as ar

HERE = Path(__file__).resolve().parent
TASK = next(p for p in HERE.parents if (p / 'menu-repair-01').is_dir())
PROJECT = TASK.parents[1]
RUNTIME = TASK / 'menu-repair-01/runtime'
AP = TASK / 'menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib'
CP = PROJECT / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
RUNS = {
    'ap97r2alpha600-cd3c48f7': '3349b5c2a8d6da0485045328ec01fe30589c11a38e254bdb3701d15ec0f21c10',
    'ap100v1sync600-8d0d69c0': 'ffe11f4561da66a5bba2707f953e258a6e6e205e8066320642f713bca67a5294',
    'ap101r4tile600-be9996d0': '11fcdf7d7962f5b92fd71099e8d682d9f16ccd5cb5cf55112a5ec8315332c8f8',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def source(path, pin=None):
    b = path.read_bytes()
    h = sha(b)
    if pin:
        assert h == pin, ('source changed', str(path), h)
    return {'file': str(path.relative_to(PROJECT)), 'bytes': len(b), 'sha256': h}


def u(q, o, n=4):
    return int.from_bytes(q[o:o+n], 'little')


def signed(q, o):
    return struct.unpack_from('<i', q, o)[0]


def decode(q):
    d = {'dst': hex(u(q, 0, 8)), 'dst_xywh': [signed(q, 8), signed(q, 12), u(q, 16), u(q, 20)]}
    if len(q) == 56:
        return {**d, 'stride': u(q, 24), 'format': u(q, 28), 'color': list(q[32:36]),
                'selector': q[36], 'K': q[37], 'async': q[38]}
    assert len(q) == 144
    dx = signed(q, 8)+signed(q, 40)-signed(q, 80)
    dy = signed(q, 12)+signed(q, 44)-signed(q, 84)
    cx, cy, cw, ch = signed(q, 24), signed(q, 28), u(q, 32), u(q, 36)
    inter = [max(dx, cx), max(dy, cy), min(dx+u(q, 16), cx+cw), min(dy+u(q, 20), cy+ch)]
    return {**d, 'clip': [cx, cy, cw, ch], 'adjusted_xy': [dx, dy],
            'intersection_ltrb': inter, 'empty_intersection': inter[2] <= inter[0] or inter[3] <= inter[1],
            'dst_stride': u(q, 48), 'dst_format': u(q, 52), 'src': hex(u(q, 56, 8)),
            'src_xywh': [u(q, n) for n in (64, 68, 72, 76)],
            'src_stride': u(q, 88), 'src_format': u(q, 92),
            'scale_f32': list(struct.unpack_from('<ff', q, 96)), 'rotation': u(q, 104),
            'color': list(q[108:112]), 'selector': q[112], 'conversion': q[113],
            'K': q[114], 'flags_P73_to_P78': list(q[115:121]), 'async': q[121]}


def histogram(c):
    return [{'key': list(k) if isinstance(k, tuple) else k, 'count': v} for k, v in sorted(c.items(), key=lambda x: str(x[0]))]


def audit_run(name, pin):
    p = RUNTIME / 'runs' / name / 'serial.log'
    provenance = source(p, pin)
    lines = p.read_bytes().split(b'\n')
    commands, raw, malformed, noops, vdf, records = [], [], [], [], [], collections.defaultdict(list)
    tags = ('FX3_OSD_HEADLESS_VALIDATE', 'FX3_OSD_FRAME_TARGET_VALID', 'FX3_OSD_HEADLESS_ACK',
            'FX3_OSD_OWNER_GUI', 'FX3_OSD_OWNER_CURRENT', 'FX3_OSD_LIFE_SEND',
            'FX3_GPE_RESOURCE_REGISTER', 'FX3_GPE_EMPTY_CLIP_NOOP', 'FX3_GPE_TILE_APPLIED')
    for ln, b in enumerate(lines, 1):
        s = b.decode(errors='replace').rstrip('\r')
        for tag in tags:
            if tag+' ' in s:
                text = s[s.index(tag+' '):]
                fields = dict(re.findall(r'(\w+)=(\S+)', text))
                if tag == 'FX3_OSD_LIFE_SEND' and fields.get('op') not in ('1002', '1003', '1005'):
                    continue
                records[tag].append({'LF_line': ln, 'fields': fields, 'text': text})
                if tag == 'FX3_GPE_EMPTY_CLIP_NOOP':
                    noops.append(int(fields['seq']))
        m = re.search(r'FX3_GPE_CMD op=(\w+) seq=(\d+) (.*)', s)
        if m:
            kv = dict(re.findall(r'(\w+)=(\S+)', m[3]))
            commands.append({'LF_line': ln, 'op': m[1], 'seq': int(m[2]), **kv})
        m = re.search(r'FX3_GPE_RAW_PARAMS op=(\w+) seq=(\d+) read=1 len=(\d+) raw_hex=([0-9a-f]+)', s)
        if m:
            op, seq, n, h = m.groups()
            if len(h) != 2*int(n) or int(n) not in (56, 144, 24):
                malformed.append({'LF_line': ln, 'op': op, 'seq': int(seq), 'expected_bytes': int(n), 'hex_chars': len(h)})
                continue
            q = bytes.fromhex(h)
            raw.append({'LF_line': ln, 'op': op, 'seq': int(seq), 'raw_hex': h,
                        'decoded': decode(q) if len(q) != 24 else {'flush_bytes': len(q)}})
        if 'FX3_PROVIDER_REQUEST ' in s:
            m = re.search(r'raw=(0d20(?:4701|4c01)[0-9a-f]+)', s)
            if m:
                q = bytes.fromhex(m[1])
                vdf.append({'LF_line': ln, 'command': hex(u(q, 2, 2)), 'raw_hex': m[1],
                            'bytes': len(q), 'sha256': sha(q)})
    fills = [r for r in raw if r['op'] == 'FillRect']
    blits = [r for r in raw if r['op'] == 'BitBlit']
    raw_by_seq = {r['seq']: r for r in raw}
    noop_details = []
    for seq in noops:
        assert seq in raw_by_seq, ('no-op raw absent', name, seq)
        row = raw_by_seq[seq]
        assert row['decoded']['empty_intersection'], ('visible command incorrectly no-opped', row)
        noop_details.append(row)
    # Existing review counts refer to intact CMD markers, not every FIFO command.
    review = RUNTIME / (name+'-review-v4.json')
    rv = json.loads(review.read_text())
    results = collections.Counter((c['op'], c.get('result', 'unparsed')) for c in commands)
    targets = collections.Counter((r['fields'].get('original_FB'), r['fields'].get('bitmap'),
                                   r['fields'].get('physical')) for r in records['FX3_OSD_FRAME_TARGET_VALID'])
    # Thousands of unchanged 1005 transactions add no new fields. Preserve
    # exact aggregate counts and bounded first/last examples per wire opcode;
    # all identities, validated frames, raw GPE commands and no-ops stay intact.
    record_counts = {tag: histogram(collections.Counter(r['fields'].get('op', tag) for r in items))
                     for tag, items in records.items()}
    for tag in ('FX3_OSD_LIFE_SEND', 'FX3_OSD_OWNER_CURRENT'):
        groups = collections.defaultdict(list)
        for r in records[tag]:
            groups[r['fields'].get('op')].append(r)
        records[tag] = sorted({r['LF_line']: r for items in groups.values()
                              for r in items[:8]+items[-8:]}.values(), key=lambda r: r['LF_line'])
    return {'serial': provenance, 'line_numbering': 'LF, one based; CR is not a new line',
            'review': source(review), 'review_summary': {k: rv.get(k) for k in
                ('health_pass', 'GPE_complete_records', 'GPE_nonzero_records', 'GPE_incomplete_records')},
            'CMD_marker_result_counts': histogram(results), 'complete_raw_count': len(raw),
            'incomplete_raw_records': malformed, 'raw_records': raw,
            'raw_fill_counts': histogram(collections.Counter((tuple(r['decoded']['color']), r['decoded']['selector'], r['decoded']['K']) for r in fills)),
            'raw_blit_counts': histogram(collections.Counter((r['decoded']['dst_format'], r['decoded']['src_format'],
                r['decoded']['selector'], r['decoded']['K'], tuple(r['decoded']['flags_P73_to_P78'])) for r in blits)),
            'raw_blit_destinations': histogram(collections.Counter(r['decoded']['dst'] for r in blits)),
            'FB_bitmap_physical_tuples': histogram(targets), 'empty_clip_commands': noop_details,
            'VDF_layout_requests': vdf, 'publication_record_counts': record_counts,
            'publication_record_sampling': 'LIFE_SEND and OWNER_CURRENT: first/last eight per opcode; other records complete',
            'publication_and_identity_records': dict(records)}


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume.get('VolumeUUID') == UUID and volume.get('MountPoint') == '/Volumes/KAFU2T'
    provider = HERE.parent / 'gpe-blend-p3/audit_gpe_blend.py'
    provider_source = source(provider, '88effc3d0cf05c7027d30e1b7a505e88cad96ba001e55815c9300a422dff0bc1')
    lib = runpy.run_path(str(provider), run_name='menu_layers_readonly_provider')
    obj, gpe = lib['Image']('libObj.so'), lib['Image']('libgpe.so')
    app_data = (AP/'appFw.so').read_bytes()
    app_elf = ELFFile(BytesIO(app_data))
    cp_data = CP.read_bytes()

    def block(image, start, end):
        return image.block(start, end)

    def app_block(start, end):
        seg = next(s for s in app_elf.iter_segments() if s['p_type'] == 'PT_LOAD' and
                   s['p_vaddr'] <= start and end <= s['p_vaddr']+s['p_filesz'])
        off = seg['p_offset']+start-seg['p_vaddr']
        rows = [{'va': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic+' '+i.op_str}
                for i in Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN).disasm(app_data[off:off+end-start], start)]
        assert sum(len(bytes.fromhex(r['bytes'])) for r in rows) == end-start
        return rows

    def cp_block(start, end):
        rows = [{'va': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic+' '+i.op_str}
                for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(cp_data[start-0x108000:end-0x108000], start)]
        assert sum(len(bytes.fromhex(r['bytes'])) for r in rows) == end-start
        return rows

    original = {
        'libObj.so': {'source': source(obj.path, obj.sha), 'blocks': {hex(a): block(obj, a, z) for a, z in
            [(0x1528b8, 0x152960), (0x1535e4, 0x153714), (0x153860, 0x153940),
             (0x15394c, 0x1539f4), (0x169480, 0x169554), (0x169850, 0x16997c),
             (0x168b70, 0x168c48),
             (0x1017ac, 0x101d20), (0x100f98, 0x1011a0), (0xf2638, 0xf27d8),
             (0xf2fa0, 0xf305c), (0xf335c, 0xf3418), (0xf393c, 0xf394c)]}},
        'libgpe.so': {'source': source(gpe.path, gpe.sha), 'blocks': {hex(a): block(gpe, a, z) for a, z in
            [(0xcf2c, 0xd148), (0xbbcc, 0xc154), (0xc878, 0xcf2c), (0xc384, 0xc5e4)]}},
        'appFw.so': {'source': source(AP/'appFw.so'), 'blocks': {hex(a): app_block(a, z) for a, z in
            [(0x16ee6f8, 0x16ee790), (0x2deb060, 0x2deb3fc)]}},
        'CP': {'source': source(CP), 'blocks': {hex(a): cp_block(a, z) for a, z in
            [(0x4b36fc, 0x4b3882), (0x5f5f7c, 0x5f60b8), (0x5f56ee, 0x5f576a)]}},
    }
    # Fixed, independently readable instruction anchors. No reliance on names alone.
    def has(rows, va, asm):
        r = next(r for r in rows if int(r['va'], 16) == va)
        assert r['asm'] == asm, (hex(va), r['asm'], asm)
    has(original['libObj.so']['blocks']['0x153860'], 0x153938, 'bl #0x55710')
    has(original['libObj.so']['blocks']['0x1528b8'], 0x152940, 'bl #0x56090')
    has(original['libObj.so']['blocks']['0xf2638'], 0xf26f0, 'mov w1, #1')
    has(original['libObj.so']['blocks']['0xf2638'], 0xf26f4, 'str w1, [x0, #0xc]')
    has(original['libObj.so']['blocks']['0xf335c'], 0xf33ec, 'ldp x0, x1, [x19, #0x60]')
    has(original['libObj.so']['blocks']['0xf335c'], 0xf33f0, 'stp x1, x0, [x19, #0x60]')
    has(original['libObj.so']['blocks']['0xf393c'], 0xf393c, 'mov w0, #0')

    runs = {name: audit_run(name, pin) for name, pin in RUNS.items()}
    latest = runs['ap101r4tile600-be9996d0']
    rows = {r['seq']: r for r in latest['raw_records']}
    # Geometric roles are B-level fits, not captured Widget/UX resource IDs.
    selected = {name: rows[seq] for name, seq in
        [('main_tile_candidate', 226), ('panel_bitmap_candidate', 1363),
         ('highlight_top_candidate', 1215), ('highlight_center_candidate', 1218),
         ('highlight_bottom_candidate', 1221), ('repeat_separator', 757)]}
    candidate_seqs = {r['seq'] for r in selected.values()} | {r['seq'] for r in latest['empty_clip_commands']}
    candidate_observers = []
    serial_lines = (RUNTIME/'runs/ap101r4tile600-be9996d0/serial.log').read_bytes().split(b'\n')
    for ln, b in enumerate(serial_lines, 1):
        s = b.decode(errors='replace').rstrip('\r')
        m = re.search(r'(FX3_GPE_(?:SCOPE|DRAW_INTERVAL|CMD|TILE_APPLIED|EMPTY_CLIP_NOOP)) .*?seq=(\d+)\b', s)
        if m and int(m[2]) in candidate_seqs:
            candidate_observers.append({'LF_line': ln, 'text': s[s.index(m[1]):]})

    class Replay(lib['Replay']):
        def hook(self, uc, address, size, arg):
            name = self.image.plt.get(address, '')
            if 'StretchRotateBlit' in name:
                uc.reg_write(ar.UC_ARM64_REG_PC, 0xc878)
                return
            if name in ('cslMakeZoomSprite', 'cslMakeZoomRotateSprite'):
                self.other.append({'kind': name, 'caller_va': hex(self.reg(30)-4),
                    'dst_xy': [self.reg(1)&0xffffffff, self.reg(2)&0xffffffff],
                    'src_struct40': bytes(uc.mem_read(self.reg(0), 40)).hex(),
                    'scale_f32': [struct.unpack('<f', struct.pack('<I', uc.reg_read(r)&0xffffffff))[0]
                                  for r in (ar.UC_ARM64_REG_S0, ar.UC_ARM64_REG_S1)]})
                self.ret()
                return
            super().hook(uc, address, size, arg)
    replay = Replay(gpe)
    replay_results = {}
    for name, row in {**selected, **{'empty_clip_'+str(r['seq']): r for r in latest['empty_clip_commands']}}.items():
        q = bytes.fromhex(row['raw_hex'])
        result = replay.run(0xcf2c, q)
        assert result['status'] == 'submission_intercepted', (name, result)
        regs = {int(w['reg'], 16): w['value'] for w in result['register_writes']}
        assert regs[0x760] == 1 and regs[0x770] == 0x05040501
        replay_results[name] = {'captured_command': row, 'original_descriptor_execution': result,
                               'hardware_pixels_executed': False}

    # Exact raw readback pixels, not a visual approximation of a screenshot.
    capture = RUNTIME/'runs/ap101r4tile600-be9996d0/ap101-step-10-key-1ac.json'
    meta = json.loads(capture.read_text())
    raw_path = Path(meta['raw'])
    raw = raw_path.read_bytes()
    assert len(raw) == 640*480*2 and sha(raw) == meta['raw_sha256'] == meta['native_committed_sha256']
    assert meta['matches_committed_ring'] is True
    pixels = collections.Counter(struct.unpack('<307200H', raw))
    alpha = collections.Counter()
    for v, n in pixels.items():
        alpha[v&15] += n
    assert alpha == {15: 307200}

    # Decode every persisted ring header's native 1003/1005, including +0xc.
    descriptors = []
    for p in sorted(capture.parent.glob('osd-frame-*-slot-header.bin')):
        q = p.read_bytes()
        if len(q) < 0x1a4:
            continue
        wire = q[0x180:0x1a4]
        op = u(wire, 0, 2)
        if op in (0x1003, 0x1005):
            d = {'file': p.name, 'seq': u(q, 16, 8), 'op': hex(op),
                 'raw36_hex': wire.hex(), 'token': hex(u(wire, 8)), 'constant_plus_0c': u(wire, 12),
                 'format_boolean': u(wire, 16, 2), 'canvas_wh': [u(wire, 20, 2), u(wire, 22, 2)],
                 'update_xywh': [u(wire, o, 2) for o in (24, 26, 28, 30)], 'diagnostic_word': u(wire, 32)}
            descriptors.append(d)
    assert any(d['op'] == '0x1003' for d in descriptors)
    assert all(d['constant_plus_0c'] == 1 for d in descriptors if d['op'] == '0x1003')

    model = RUNTIME/'helpers/fx3-gpe-backend-v8.c'
    model_lines = model.read_text().splitlines()
    terms = ('empty_clip_noop', 'p->approx_blend=', 'straight_over_v1(', 'a8_color_over_candidate(',
             'p->approx_tile', 'q[117]', 'q[118]', 'if(p->approx_fmt2)', 'else if(p->approx_blend)')
    context_paths = [TASK/'lead-claude/COMMON-CONTEXT.md', TASK/'lead-claude/PLAN.md']
    context_paths += [HERE.parent/n/'README.md' for n in ('gpe-menu-draw', 'gpe-blend-p3',
        'vdf0147-plane-scanout', 'osd-completion-6003', 'offscreen-subblock')]
    context_paths += [RUNTIME/n for n in ('ap100-runtime-evidence-v1.json', 'ap101-r4-runtime-evidence-v1.json',
        'ap97r2alpha600-cd3c48f7-acceptance.json', 'ap97r2alpha600-cd3c48f7-ui-readback.json',
        'fx3-vdf-config-proof.json')]
    proof = {'scope': 'read-only saved-run/static audit; only adjacent JSON written; no QEMU/QMP/device/Git/locks',
        'evidence_levels': {'A1': 'pinned original bytes and intercepted descriptor replay',
            'A2': 'saved run records/raw readbacks, with observer gaps retained',
            'B': 'geometry/call-chain inference, not resource-ID or pixel-oracle proof', 'U': 'unproven'},
        'provider': provider_source, 'context_inputs': [source(p) for p in context_paths],
        'original': original, 'runs': runs, 'candidate_observers': candidate_observers,
        'selected_candidates_and_original_replay': replay_results,
        'native_publication_descriptors': descriptors,
        'final_readback': {'metadata_source': source(capture), 'raw_source': source(raw_path),
            'identity': meta['native_identity'], 'registered_target': meta['registered_target'],
            'matches_committed_ring': True, 'alpha_nibble_counts': histogram(alpha),
            'pixel_value_counts': histogram(pixels)},
        'model': {'source': source(model, 'b2fcf092426c4919f5c74a130447348d7e08edcb34302faaa470802f625fd220'),
                  'line_evidence': [{'line': n, 'text': s} for n, s in enumerate(model_lines, 1) if any(t in s for t in terms)]},
        'findings': {
            'missing_second_simultaneous_FB_plane': 'B: unsupported; observed two bitmap banks belong to one FB and alternate',
            'native_1003_layer_number': 'A1/A2: +0xc is hardcoded 1; no recovered z/alpha/layer descriptor',
            'empty_clip_hides_visible_highlight': 'A2: false for five saved no-ops; all intersections empty',
            'fmt3_fmt4_CLUT_explains_observed_commands': 'A2 bounded negative: decoded raw uses dst0/src0 or src2 only; no CLUT fields identified',
            'best_next_localization': 'B: CPU-produced fmt0 texture/source-alpha/near-approx-raster chain; exact faulty stage remains U',
            'texture_role_binding': 'B: nine-patch/highlight, large panel bitmap, repeated tile icons fit geometry; no captured Widget/resource-ID binding',
            'export_alpha_drop': 'A2: final raw alpha all 15 and hash matches committed ring; cannot explain absent RGB at this capture',
        },
        'unproven': ['source texture byte content at command execution', 'UX resource-ID to each candidate binding',
            'native hardware blend factors/rounding/filter/texture alpha convention',
            'all FIFO opcode2/3 coverage (only three worker entries intercepted)',
            '1000/1001 config consumption and full CP scanout/retirement/composition',
            'no invisible plane anywhere in firmware (bounded evidence cannot prove universal absence)',
            'one corrective pixel implementation that restores all three observed symptoms'],
    }
    out = HERE/'menu-layers-proof.json'
    out.write_text(json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'result': 'PASS', 'scope': 'offline evidence reconstruction, not a rendering fix',
        'proof': str(out), 'sha256': sha(out.read_bytes()), 'replayed_commands': len(replay_results),
        'complete_raw_records': {n: r['complete_raw_count'] for n, r in runs.items()},
        'native_publication_headers': len(descriptors)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
