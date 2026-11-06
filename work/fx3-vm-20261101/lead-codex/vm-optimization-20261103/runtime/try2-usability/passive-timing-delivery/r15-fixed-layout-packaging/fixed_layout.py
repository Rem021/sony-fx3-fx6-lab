#!/usr/bin/env python3
"""Offline FX3 helper-only fixed-newc-slot packager; no VM/strip/DTB mutation.

CLI pins cannot be overridden. plan is seek-only for CPIO; write revalidates the
plan, hashes the complete source, streams to an exclusive target, then compares
every byte outside the permitted slot. Failure artifacts are never removed.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import struct
import subprocess
import sys

HERE = Path(__file__).absolute().parent
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
DEL = HERE.parent
BASE = DEL / 'v25-menu-osd-diagnostic-r3/vmopt-20261104-v25-menu-osd-diagnostic-r3'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
MEMBER = 'simulation/fx3-ui-gate-v1.so'
PINS = dict(candidate_sha256='a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518',
            archive_sha256='31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83',
            archive_size=453213884, header_offset=451339508,
            payload_offset=451339648, slot_size=58856, mode=0o100755,
            member_sha256='54eeed923a6412cd2c6743f6e8c968d1ede71b92aa79aca4575868ebccc4a9ec',
            dtb_sha256='5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b')
CHUNK = 1 << 20


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(path):
    """Reject symlinks in ALL existing components, including a dangling leaf."""
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts, 'absolute non-traversing path required')
    for item in [*reversed(p.parents), p]:
        try:
            st = item.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(st.st_mode), 'symlink forbidden: ' + str(item))
    return p


def read_file(path):
    with open_read(path) as f:
        return f.read()


def open_read(path):
    p = safe_path(path)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'input is not regular: ' + str(p))
        return os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise


def sha_file(path):
    with open_read(path) as f:
        return hash_stream(f)


def hash_stream(f):
    f.seek(0)
    h = hashlib.sha256()
    while data := f.read(CHUNK):
        h.update(data)
    return h.hexdigest()


def volume_check():
    info = plistlib.loads(subprocess.check_output(
        ['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T'], timeout=10))
    require(info.get('VolumeUUID') == UUID and info.get('MountPoint') == '/Volumes/KAFU2T',
            'target volume UUID/mount mismatch')


def output_path(path):
    p = safe_path(path)
    require(p.is_relative_to(ROOT), 'output must stay in the verified Mac project')
    require(not p.exists(), 'output already exists: ' + str(p))
    require(p.parent.is_dir(), 'output parent must already exist')
    # No writes inside frozen source/helper or original candidate directories.
    require(not p.is_relative_to(BASE), 'original candidate output forbidden')
    require(not any(x.startswith('v25-') for x in p.relative_to(DEL).parts[:-1])
            if p.is_relative_to(DEL) else True, 'frozen candidate output forbidden')
    return p


def exclusive_json(path, value):
    p = safe_path(path)
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def get_string(data, offset):
    require(0 <= offset < len(data), 'ELF string outside table')
    end = data.find(b'\0', offset)
    require(end >= 0, 'unterminated ELF string')
    return data[offset:end].decode('utf-8', errors='strict')


class ELF:
    def __init__(self, data):
        self.data = data
        require(len(data) >= 64 and data[:7] == b'\x7fELF\x02\x01\x01',
                'require ELF64 little-endian version 1')
        self.h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
        h = self.h
        require(h[1:4] == (3, 183, 1), 'require AArch64 ET_DYN ELF version 1')
        require(h[8] == 64 and h[9] == 56 and h[11] == 64 and h[10] > 0 and h[12] > 0,
                'unsupported ELF header/table sizes or extended indexing')
        require(h[13] < h[12], 'bad shstrndx')
        self.ph_bytes = self.span(h[5], h[9] * h[10])
        self.ph = [struct.unpack_from('<IIQQQQQQ', self.ph_bytes, i * 56) for i in range(h[10])]
        raw = [struct.unpack('<IIQQQQIIQQ', self.span(h[6] + i * 64, 64)) for i in range(h[12])]
        names = self.span(raw[h[13]][4], raw[h[13]][5])
        self.sections = []
        self.by_name = {}
        for i, s in enumerate(raw):
            name = get_string(names, s[0])
            require(name not in self.by_name, 'duplicate ELF section name')
            row = dict(index=i, name=name, type=s[1], flags=s[2], addr=s[3], offset=s[4],
                       size=s[5], link=s[6], info=s[7], align=s[8], entsize=s[9])
            row['data'] = b'' if s[1] == 8 else self.span(s[4], s[5])
            self.sections.append(row)
            self.by_name[name] = row
        for p in self.ph:
            self.span(p[2], p[5])
        self.dynamic = self.dynamic_info()
        self.symbols = self.dyn_symbols()

    def span(self, offset, size):
        require(0 <= offset <= len(self.data) and 0 <= size <= len(self.data)-offset, 'ELF span out of bounds')
        return self.data[offset:offset+size]

    def linked_strings(self, s):
        require(s['link'] < len(self.sections), 'bad ELF linked section')
        table = self.sections[s['link']]
        require(table['type'] == 3, 'ELF link is not string table')
        return table['data']

    def dynamic_info(self):
        ds = [s for s in self.sections if s['type'] == 6]
        require(len(ds) == 1, 'one dynamic section required')
        s = ds[0]
        require(s['entsize'] == 16 and s['size'] % 16 == 0, 'bad dynamic entry size')
        strings = self.linked_strings(s)
        result = {'needed': [], 'soname': [], 'rpath': [], 'runpath': []}
        for tag, value in struct.iter_unpack('<qQ', s['data']):
            if tag in (1, 14, 15, 29):
                result[{1:'needed', 14:'soname', 15:'rpath', 29:'runpath'}[tag]].append(get_string(strings, value))
        return result

    def dyn_symbols(self):
        ss = [s for s in self.sections if s['type'] == 11]
        require(len(ss) == 1, 'one dynsym required')
        s = ss[0]
        require(s['entsize'] == 24 and s['size'] % 24 == 0, 'bad dynsym size')
        strings = self.linked_strings(s)
        symbols = []
        for name, info, other, index, value, size in struct.iter_unpack('<IBBHQQ', s['data']):
            require(index < len(self.sections) or index >= 0xff00, 'bad symbol section index')
            symbols.append(dict(name=get_string(strings, name), bind=info>>4, type=info&15,
                                other=other, section=self.sections[index]['name'] if 0 < index < 0xff00 else index,
                                value=value, size=size))
        return symbols


def is_debug(name):
    return name.startswith(('.debug', '.zdebug', '.rela.debug', '.rel.debug')) or name == '.gdb_index'


def audit_elf(raw, stripped):
    """Recomputed at plan AND write; never trust an audit JSON as authorization."""
    a, b = ELF(raw), ELF(stripped)
    require(a.ph_bytes == b.ph_bytes, 'ELF program headers changed')
    header_changes = []
    header_names = ['ident','type','machine','version','entry','phoff','shoff','flags','ehsize',
                    'phentsize','phnum','shentsize','shnum','shstrndx']
    for i, (x, y) in enumerate(zip(a.h, b.h)):
        if x != y:
            require(i in (6, 12, 13), 'ELF header changed outside section-table fields')
            header_changes.append(dict(field=header_names[i], before=x, after=y))
    removed = sorted(set(a.by_name) - set(b.by_name))
    require(any(is_debug(n) for n in removed) and all(is_debug(n) or n in ('.symtab','.strtab') for n in removed),
            'only debug/static-symbol sections may be removed')
    require(not (set(b.by_name) - set(a.by_name)), 'new sections after strip-debug')
    require(not any(is_debug(n) for n in b.by_name), 'debug sections remain')
    nonalloc = []
    for n in set(a.by_name) & set(b.by_name):
        x,y = a.by_name[n], b.by_name[n]
        if not x['flags'] & 2 and n not in ('.symtab','.strtab','.shstrtab'):
            require(all(x[k] == y[k] for k in ('type','flags','addr','size','align','entsize')) and x['data'] == y['data'],
                    'non-debug non-ALLOC section changed: ' + n)
            nonalloc.append(n)
    aa = {n:s for n,s in a.by_name.items() if s['flags'] & 2}
    bb = {n:s for n,s in b.by_name.items() if s['flags'] & 2}
    require(set(aa) == set(bb), 'SHF_ALLOC section set changed')
    alloc = []
    for n, x in aa.items():
        y = bb[n]
        keys = ('type','flags','addr','offset','size','align','entsize')
        require(all(x[k] == y[k] for k in keys), 'SHF_ALLOC layout changed: ' + n)
        require(x['data'] == y['data'], 'SHF_ALLOC bytes changed: ' + n)
        alloc.append(dict(name=n, **{k:x[k] for k in keys},
                          sha256=None if x['type'] == 8 else digest(x['data']),
                          nobits=x['type'] == 8))
    require(a.dynamic == b.dynamic, 'ELF dependencies/SONAME changed')
    require(a.symbols == b.symbols, 'dynamic exports/undefined symbols changed')
    load_differences = []
    allowed = set(range(40,48)) | set(range(60,64))
    for i, p in enumerate(a.ph):
        if p[0] != 1:
            continue
        x, y = a.span(p[2], p[5]), b.span(p[2], p[5])
        diffs = [p[2]+j for j,(u,v) in enumerate(zip(x,y)) if u != v]
        require(set(diffs) <= allowed, 'PT_LOAD changed outside ELF section-table header fields')
        load_differences.append(dict(program_header_index=i, file_offset=p[2], filesz=p[5],
                                     differing_file_offsets=diffs, raw_sha256=digest(x), stripped_sha256=digest(y)))
    return dict(schema='fx3-strip-debug-audit/v1', passed=True,
                architecture='ELF64-LE-AArch64-ET_DYN', raw_sha256=digest(raw), stripped_sha256=digest(stripped),
                raw_size=len(raw), stripped_size=len(stripped),
                program_headers_equal=True, program_header_sha256=digest(a.ph_bytes),
                elf_header_changes=header_changes, removed_debug_sections=[n for n in removed if is_debug(n)],
                removed_static_symbol_sections=[n for n in removed if not is_debug(n)],
                retained_other_nonalloc_sections_equal=sorted(nonalloc),
                alloc_sections=alloc, dynamic=a.dynamic,
                exports=[s for s in a.symbols if s['bind'] in (1,2) and s['section'] != 0],
                undefined=[s for s in a.symbols if s['name'] and s['section'] == 0],
                pt_load_comparison=load_differences,
                pt_load_whole_bytes_equal=all(not x['differing_file_offsets'] for x in load_differences))


def aligned(n):
    return (n+3) & ~3


def index_archive(f):
    """Read headers/names only, seek payloads. Strict single unpadded 070701."""
    f.seek(0, 2)
    total = f.tell()
    f.seek(0)
    rows, names = [], set()
    while True:
        off = f.tell()
        h = f.read(110)
        require(len(h) == 110 and h[:6] == b'070701', 'require uncompressed newc 070701')
        require(re.fullmatch(b'[0-9a-fA-F]{104}', h[6:]) is not None, 'bad newc hex')
        v = [int(h[6+8*i:14+8*i], 16) for i in range(13)]
        require(v[12] == 0, 'newc check field must be zero')
        size, nlen = v[6], v[11]
        require(1 <= nlen <= 4096, 'invalid newc name length')
        name_bytes = f.read(nlen)
        require(len(name_bytes) == nlen and name_bytes[-1:] == b'\0' and b'\0' not in name_bytes[:-1], 'bad newc name')
        name = name_bytes[:-1].decode('utf-8', errors='strict')
        if name != 'TRAILER!!!':
            require(name and not name.startswith('/') and '\\' not in name and
                    all(x not in ('', '.', '..') for x in name.split('/')), 'unsafe member path: ' + name)
        require(name not in names, 'duplicate member: ' + name)
        names.add(name)
        payload = aligned(off+110+nlen)
        end = aligned(payload+size)
        require(payload <= total and end <= total, 'truncated member span')
        rows.append(dict(name=name, header_offset=off, payload_offset=payload,
                         size=size, mode=v[1], nlink=v[4], inode=v[0], devmajor=v[7], devminor=v[8],
                         next_offset=end, header_hex=h.hex()))
        f.seek(end)
        if name == 'TRAILER!!!':
            require(size == 0 and end == total, 'trailer must end exactly at EOF; no padding/concatenation')
            return rows


def contract_check(c, audit):
    require(c.get('schema') == 'fx3-fixed-layout-release/v1', 'wrong release contract version')
    version, variant = c.get('helper_version'), c.get('variant')
    require(version in ('r14','r15') and variant in ('N1','N64'), 'unsupported helper version/variant')
    expected_soname = 'fx3-ui-gate-v' + version[1:] + '-' + variant.lower() + '.so'
    require(c.get('soname') == expected_soname and audit['dynamic']['soname'] == [expected_soname], 'helper SONAME/version mismatch')
    require(c.get('raw_sha256') == audit['raw_sha256'] and c.get('stripped_sha256') == audit['stripped_sha256'], 'release ELF hash mismatch')
    require(audit['dynamic']['needed'] == ['libc.so.6', 'libdl.so.2'] and
            not audit['dynamic']['rpath'] and not audit['dynamic']['runpath'], 'unexpected helper dependencies/search paths')
    require(isinstance(c.get('diagnostic_contract'), dict) and c['diagnostic_contract'], 'explicit diagnostic contract required')


def source_manifest_rows(path):
    rows=[]
    for line in read_file(path).decode().splitlines():
        require(re.fullmatch(r'[0-9a-f]{64}  [^\x00]+',line) is not None, 'bad source hash manifest row')
        h,name=line.split('  ',1)
        require(not Path(name).is_absolute() and all(x not in ('','..','.') for x in name.split('/')), 'unsafe source manifest path')
        p=safe_path(Path(path).parent/name)
        require(sha_file(p)==h, 'source manifest input hash mismatch: '+name)
        rows.append(dict(path=str(p),sha256=h))
    require(rows and len({r['path'] for r in rows})==len(rows), 'empty/duplicate source manifest')
    return rows


def command_inputs(command):
    require(command.count('-o')==1, 'one build output required')
    output_index=command.index('-o')+1
    require(output_index < len(command), 'missing build output')
    paths=[p for i,p in enumerate(command) if i!=output_index and p.startswith('/')]
    require(paths and paths[0]==command[0], 'absolute compiler required')
    return [dict(path=str(safe_path(p)),sha256=sha_file(p)) for p in paths]


def provenance_check(release, raw_path, stripped_path):
    """Bind reviewed release to frozen sources/build and the sole linker flag.

    A receipt is provenance, not a signature or proof of execution; every declared
    input is rehashed and the loaded ELF is independently compared regardless.
    """
    refs=release.get('provenance',{})
    for key in ('raw_build_manifest','source_manifest','strip_build_receipt'):
        ref=refs.get(key,{})
        require(ref.get('path') and sha_file(ref['path'])==ref.get('sha256'), 'build provenance hash mismatch: '+key)
    sources=source_manifest_rows(Path(refs['source_manifest']['path']))
    build=json.loads(read_file(refs['raw_build_manifest']['path']))
    b=build['variants'][release['variant']]
    original=b['command']
    require(b['exit']==0 and b['sha256']==release['raw_sha256'], 'raw build receipt/hash mismatch')
    require(original[original.index('-o')+1]==str(raw_path), 'raw build output path mismatch')
    require('--strip-all' not in ' '.join(original) and '--strip-debug' not in ' '.join(original), 'raw debug build was already stripped')
    command=list(original)
    command[command.index('-o')+1]=str(stripped_path)
    command.insert(2,'-Wl,--strip-debug')
    receipt=json.loads(read_file(refs['strip_build_receipt']['path']))
    require(receipt.get('schema')=='fx3-linker-strip-build/v1' and receipt.get('exit')==0,
            'successful linker-strip build receipt required')
    require(receipt.get('command')==command and receipt.get('original_command')==original,
            'build differs beyond --strip-debug and output path')
    require(receipt.get('raw_sha256')==release['raw_sha256'] and receipt.get('stripped_sha256')==release['stripped_sha256'],
            'strip build artifact hash mismatch')
    require('--strip-all' not in ' '.join(command), 'strip-all forbidden')
    inputs=command_inputs(original)
    require(receipt.get('command_input_hashes')==inputs, 'build command input hash mismatch')
    source_set={r['path'] for r in sources}
    require(all(r['path'] in source_set for r in inputs if r['path'].endswith(('.c','.S'))),
            'compile source missing from frozen source manifest')
    return dict(method='relink_original_command_with_only_-Wl,--strip-debug_and_output_change',
                references=refs, command_input_hashes=inputs, source_rows=sources,
                raw_debug_elf_retained=True, static_symbol_removal_explicitly_accepted=True,
                no_strip_all=True)


def file_identity(f):
    s = os.fstat(f.fileno())
    return dict(device=s.st_dev, inode=s.st_ino, size=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)


def make_plan(base, raw_path, stripped_path, contract_path, pins=PINS):
    base = safe_path(base)
    paths = [safe_path(x) for x in (raw_path, stripped_path, contract_path)]
    candidate_bytes = read_file(base/'candidate.json')
    require(digest(candidate_bytes) == pins['candidate_sha256'], 'base manifest hash mismatch')
    candidate = json.loads(candidate_bytes)
    archive = safe_path(candidate['initrd']['path'])
    dtb = safe_path(candidate['dtb']['path'])
    require(archive == base/'guest.cpio' and candidate['initrd']['sha256'] == pins['archive_sha256'], 'base archive identity mismatch')
    require(dtb == base/'guest.dtb' and candidate['dtb']['sha256'] == pins['dtb_sha256'] and
            sha_file(dtb) == pins['dtb_sha256'], 'original DTB hash mismatch')
    raw, stripped, contract_bytes = (read_file(x) for x in paths)
    require(len(stripped) <= pins['slot_size'], 'helper exceeds fixed payload slot')
    audit = audit_elf(raw, stripped)
    release = json.loads(contract_bytes)
    contract_check(release, audit)
    provenance = provenance_check(release, paths[0], paths[1])
    with open_read(archive) as f:
        identity = file_identity(f)
        require(identity['size'] == pins['archive_size'], 'archive length mismatch')
        index = index_archive(f)
        matches = [r for r in index if r['name'] == MEMBER]
        require(len(matches) == 1, 'missing/duplicate fixed helper member')
        member = matches[0]
        for k, expected in [('header_offset',pins['header_offset']), ('payload_offset',pins['payload_offset']),
                            ('size',pins['slot_size']), ('mode',pins['mode'])]:
            require(member[k] == expected, 'member ' + k + ' mismatch')
        require(stat.S_ISREG(member['mode']) and member['nlink'] == 1, 'helper must be standalone regular member')
        require(sum((r['inode'],r['devmajor'],r['devminor']) == (member['inode'],member['devmajor'],member['devminor'])
                    and stat.S_ISREG(r['mode']) for r in index) == 1, 'helper hardlink alias forbidden')
        f.seek(member['payload_offset'])
        old = f.read(member['size'])
        require(digest(old) == pins['member_sha256'], 'original helper member hash mismatch')
        require(file_identity(f) == identity, 'archive changed during plan')
    padded = stripped + bytes(pins['slot_size']-len(stripped))
    plan = dict(schema='fx3-fixed-layout-plan/v1', base=str(base), pins=pins,
                inputs=dict(raw_helper=str(paths[0]), stripped_helper=str(paths[1]), release_contract=str(paths[2])),
                release_contract_sha256=digest(contract_bytes), source_identity=identity,
                source_full_hash_status='not_rehashed_in_seek_only_plan; required_before_write',
                archive_index_sha256=digest(json.dumps(index, sort_keys=True).encode()),
                member_count_excluding_trailer=len(index)-1, target_member=member,
                raw_helper_sha256=digest(raw), stripped_helper_sha256=digest(stripped),
                padded_slot_sha256=digest(padded), zero_padding_bytes=len(padded)-len(stripped),
                allowed_change=dict(offset=member['payload_offset'], bytes=member['size']),
                audit=audit, build_provenance=provenance, release_contract=release, dtb_unchanged=True,
                runtime_validated=False, real_archive_generated=False)
    return plan, index


def verify_outside(src, dst, offset, size):
    """Independent full pass: byte comparison outside slot, total length equality."""
    src.seek(0); dst.seek(0)
    h, pos = hashlib.sha256(), 0
    while True:
        a, b = src.read(CHUNK), dst.read(CHUNK)
        require(len(a) == len(b), 'output total length mismatch')
        if not a:
            return h.hexdigest()
        h.update(b)
        left, right = max(0, offset-pos), min(len(a), offset+size-pos)
        if right > 0 and left < len(a) and left < right:
            require(a[:left] == b[:left] and a[right:] == b[right:], 'changed bytes outside permitted slot')
        else:
            require(a == b, 'changed bytes outside permitted slot')
        pos += len(a)


def copy_amount(src, dst, amount, hasher):
    while amount:
        b = src.read(min(CHUNK, amount))
        require(b, 'source truncated while streaming')
        hasher.update(b)
        dst.write(b)
        amount -= len(b)


def derive_manifest(candidate, output, output_sha, plan):
    derived = copy.deepcopy(candidate)
    derived['initrd'] = dict(path=str(output), sha256=output_sha)
    derived['fixed_layout_diagnostic_contract'] = dict(
        base_candidate_sha256=plan['pins']['candidate_sha256'],
        base_initrd_sha256=plan['pins']['archive_sha256'], member=MEMBER,
        helper_raw_sha256=plan['raw_helper_sha256'], helper_stripped_sha256=plan['stripped_helper_sha256'],
        padded_slot_sha256=plan['padded_slot_sha256'], slot_bytes=plan['pins']['slot_size'],
        total_length_unchanged=True, dtb_bytes_unchanged=True,
        release=plan['release_contract'], runtime_validated=False)
    require({k:v for k,v in derived.items() if k not in ('initrd','fixed_layout_diagnostic_contract')} ==
            {k:v for k,v in candidate.items() if k != 'initrd'}, 'platform manifest fields changed')
    return derived


def write_archive(plan, output_dir, *, pins=PINS, require_r15=True, guard=volume_check, fault=None):
    guard()  # Before ANY output mutation; tests inject only a fixture guard.
    require(plan.get('schema') == 'fx3-fixed-layout-plan/v1' and plan.get('pins') == pins, 'wrong plan pins/version')
    fresh, index = make_plan(Path(plan['base']), plan['inputs']['raw_helper'],
                             plan['inputs']['stripped_helper'], plan['inputs']['release_contract'], pins=pins)
    require(fresh == plan, 'plan changed/stale; create a new reviewed plan')
    if require_r15:
        require(plan['release_contract']['helper_version'] == 'r15', 'write mode requires final r15 release; r14 is plan-only')
    out = output_path(output_dir)
    archive = Path(plan['base'])/'guest.cpio'
    with open_read(archive) as src:
        initial = file_identity(src)
        require(initial == plan['source_identity'], 'source identity changed')
        require(hash_stream(src) == pins['archive_sha256'], 'complete source archive hash mismatch')
        require(file_identity(src) == initial, 'source changed during full validation')
        guard()
        out.mkdir()  # exclusive; no parents or fallback
        exclusive_json(out/'INCOMPLETE.json', dict(state='incomplete', reason='write/validation not yet completed', plan=plan))
        target = out/'guest.cpio'
        try:
            stripped = read_file(plan['inputs']['stripped_helper'])
            require(digest(stripped) == plan['stripped_helper_sha256'], 'helper changed after plan')
            padded = stripped + bytes(pins['slot_size']-len(stripped))
            require(digest(padded) == plan['padded_slot_sha256'], 'padded slot hash mismatch')
            src.seek(0)
            h = hashlib.sha256()
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as dst:
                copy_amount(src, dst, pins['payload_offset'], h)
                old = src.read(pins['slot_size'])
                require(digest(old) == pins['member_sha256'], 'old member changed while copying')
                h.update(old)
                dst.write(padded)
                if fault:
                    fault(src, dst)
                copy_amount(src, dst, pins['archive_size']-src.tell(), h)
                require(not src.read(1), 'source grew while copying')
                dst.flush(); os.fsync(dst.fileno())
            require(h.hexdigest() == pins['archive_sha256'] and file_identity(src) == initial,
                    'source changed while copying')
            with open_read(target) as dst:
                output_sha = verify_outside(src, dst, pins['payload_offset'], pins['slot_size'])
                dst.seek(pins['payload_offset'])
                require(dst.read(pins['slot_size']) == padded, 'output slot content mismatch')
                require(index_archive(dst) == index, 'archive headers/order/offsets changed')
            require(sha_file(Path(plan['base'])/'guest.dtb') == pins['dtb_sha256'], 'DTB changed during output')
            require(file_identity(src) == initial, 'source changed during output verification')
            candidate = json.loads(read_file(Path(plan['base'])/'candidate.json'))
            require(sha_file(Path(plan['base'])/'candidate.json') == pins['candidate_sha256'], 'base manifest changed')
            exclusive_json(out/'candidate.json', derive_manifest(candidate, target, output_sha, plan))
            receipt = dict(state='complete', archive_sha256=output_sha, archive_bytes=target.stat().st_size,
                           complete_source_sha256=h.hexdigest(), source_open_mode='O_RDONLY|O_NOFOLLOW',
                           outside_slot_every_byte_equal=True, archive_index_equal=True,
                           original_dtb_sha256=pins['dtb_sha256'], original_dtb_referenced=True,
                           raw_helper_sha256=plan['raw_helper_sha256'], stripped_helper_sha256=plan['stripped_helper_sha256'],
                           padded_slot_sha256=plan['padded_slot_sha256'], runtime_validated=False)
            exclusive_json(out/'COMPLETE.json', receipt)
            # Retain the historical starting marker. COMPLETE, not deletion, supersedes it.
            return receipt
        except BaseException as e:
            exclusive_json(out/'FAILED.json', dict(state='incomplete', error=repr(e), target=str(target)))
            raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('audit', help='audit one already strip-debugged diagnostic helper pair')
    a.add_argument('--raw-helper', required=True, type=Path)
    a.add_argument('--helper', required=True, type=Path)
    a.add_argument('--report', required=True, type=Path)
    a = sub.add_parser('plan', help='seek-only original CPIO index and dry-run replacement plan; NO CPIO output')
    a.add_argument('--raw-helper', required=True, type=Path)
    a.add_argument('--helper', required=True, type=Path)
    a.add_argument('--release-contract', required=True, type=Path)
    a.add_argument('--report-dir', required=True, type=Path)
    a = sub.add_parser('write', help='EXPLICIT future use only: one new fixed-length CPIO, full source validation')
    a.add_argument('--plan', required=True, type=Path)
    a.add_argument('--output-dir', required=True, type=Path)
    a.add_argument('--acknowledge-real-cpio-output', required=True, choices=['REVIEWED_R15_FIXED_SLOT'])
    args = p.parse_args()
    volume_check()
    if args.mode == 'audit':
        report = audit_elf(read_file(args.raw_helper), read_file(args.helper))
        exclusive_json(output_path(args.report), report)
        print(json.dumps(dict(passed=True, raw_size=report['raw_size'], stripped_size=report['stripped_size'])))
    elif args.mode == 'plan':
        plan, index = make_plan(BASE, args.raw_helper, args.helper, args.release_contract)
        out = output_path(args.report_dir); out.mkdir()
        exclusive_json(out/'index.json', index)
        exclusive_json(out/'plan.json', plan)
        print(json.dumps(dict(plan=str(out/'plan.json'), real_archive_generated=False,
                              stripped_bytes=plan['audit']['stripped_size'], zero_padding_bytes=plan['zero_padding_bytes'])))
    else:
        plan = json.loads(read_file(args.plan))
        require(plan['base'] == str(BASE), 'write base is not fixed r3')
        print(json.dumps(write_archive(plan, args.output_dir)))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('REFUSED: ' + str(e), file=sys.stderr)
        sys.exit(1)
