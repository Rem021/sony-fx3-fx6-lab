#!/usr/bin/env python3
"""Offline audit of actual frozen newc members, not a partial file projection."""
import hashlib
import json
import posixpath
import re
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parent
MAC = HERE.parents[5]
VM = MAC / 'work/fx3-vm-20261101'
BASE = VM / 'lead-codex/vm-optimization-20261103/runtime/try2-usability'
CPIO = BASE / 'vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
HELP = VM / 'menu-repair-01/runtime/helpers'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def pinned(path, digest):
    data = path.read_bytes()
    assert sha(data) == digest, str(path)
    return data

def newc(data):
    members, offset = {}, 0
    while True:
        assert data[offset:offset+6] == b'070701', offset
        fields = [int(data[offset+6+i*8:offset+14+i*8], 16) for i in range(13)]
        mode, size, namesz = fields[1], fields[6], fields[11]
        start = offset+110
        assert namesz > 0 and data[start+namesz-1] == 0
        name = data[start:start+namesz-1].decode()
        body = (start+namesz+3) & ~3
        assert body+size <= len(data)
        if name == 'TRAILER!!!':
            break
        name = posixpath.normpath(name).lstrip('/')
        assert name not in members and not name.startswith('../'), name
        members[name] = (mode, data[body:body+size])
        offset = (body+size+3) & ~3
    return members

def resolve(members, path):
    path = posixpath.normpath(path).lstrip('/')
    chain = []
    for _ in range(32):
        if path not in members:
            return None, chain
        mode, data = members[path]
        chain.append(path)
        if mode & 0o170000 != 0o120000:
            return path, chain
        target = data.decode()
        path = posixpath.normpath(target if target.startswith('/') else posixpath.join(posixpath.dirname(path), target)).lstrip('/')
    raise ValueError('symlink loop: '+str(chain))

class ELF:
    def __init__(self, data):
        self.data = data
        assert data[:6] == b'\x7fELF\x02\x01'
        assert struct.unpack_from('<H', data, 18)[0] == 183
        phoff = struct.unpack_from('<Q', data, 32)[0]
        entsz, count = struct.unpack_from('<HH', data, 54)
        self.ph = [struct.unpack_from('<IIQQQQQQ', data, phoff+i*entsz) for i in range(count)]
        tags = {}
        for typ, flags, off, va, pa, size, memsz, align in self.ph:
            if typ != 2:
                continue
            for cursor in range(off, off+size, 16):
                tag, value = struct.unpack_from('<qQ', data, cursor)
                if tag == 0:
                    break
                tags.setdefault(tag, []).append(value)
        self.needed = []
        self.tags = tags
        if 5 in tags:
            off = self.offset(tags[5][0])
            strings = data[off:off+tags[10][0]]
            for index in tags.get(1, []):
                end = strings.index(b'\0', index)
                self.needed.append(strings[index:end].decode())

    def offset(self, va, size=1):
        for typ, flags, off, start, pa, filesz, memsz, align in self.ph:
            if typ == 1 and start <= va and va+size <= start+filesz:
                return off+va-start
        raise ValueError('VA is not file-backed: '+hex(va))

    def word(self, va):
        off = self.offset(va, 4)
        return off, struct.unpack_from('<I', self.data, off)[0]

def main():
    cpio = pinned(CPIO, 'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d')
    members = newc(cpio)
    # Validate this independent member parser against the frozen audit.
    old = json.loads(CPIO.with_name('cpio-audit.json').read_text())
    for item in old['members']:
        mode, data = members[item['path']]
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
    assert len(members) == len(old['members'])
    init = members['init'][1].decode()
    helper_path = 'simulation/fx3-preset-context-v2-screen.so'
    helper = members[helper_path][1]
    assert sha(helper) == 'eb55680196806fb86958d632c6aed939eae91aa1ef928690a4a7d21d6a76c170'
    assert helper == (HELP/'fx3-preset-context-v6-save102.so').read_bytes()
    source = pinned(HELP/'fx3-preset-context-v6-save102.c', '32bb3b5ae43ddab667c655941784daf028f26ce4c9ce6cca7e91268c4bb72663').decode()
    build = json.loads((HELP/'fx3-preset-context-v6-save102-build.json').read_text())
    assert build['source_sha256'] == sha(source.encode()) and build['output_sha256'] == sha(helper)
    addresses = [int(x,16) for x in re.findall(r'app_base\+(0x[0-9a-f]+)', re.search(r'U addresses\[48\]=\{(.*?)\}', source)[1])]
    words = [int(x,16) for x in re.findall(r'0x[0-9a-f]+', re.search(r'W words\[48\]=\{(.*?)\}', source)[1])]
    assert len(addresses) == len(words) == 48
    fx3 = pinned(VM/'fx3-audit/original-members/nflasha15/lib/appFw.so', '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f')
    fx6 = pinned(DONOR/'nflasha15-files/lib/appFw.so', 'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067')
    elfs = {'fx3': ELF(fx3), 'fx6': ELF(fx6)}
    guards = []
    for index, (address, expected) in enumerate(zip(addresses, words)):
        row = {'index':index,'relative_va':hex(address),'expected':hex(expected)}
        for name, elf in elfs.items():
            try:
                off, word = elf.word(address)
                row[name] = {'file_offset':hex(off),'word':hex(word),'matches':word==expected}
            except ValueError as e:
                row[name] = {'matches':False,'unmapped':str(e)}
        assert row['fx3']['matches'], row
        guards.append(row)
    libraries = {}
    def lookup(name):
        for directory in ('simulation','usr/lib','lib'):
            path, chain = resolve(members, directory+'/'+name)
            if path:
                return {'resolved':path,'symlinks':chain,'sha256':sha(members[path][1])}
        return None
    for name in ('libopus.so.0','libSoundTouch.so.1','libObj.so'):
        libraries[name] = lookup(name)
    roots = {'bootin.elf':(DONOR/'nflasha15-files/bin/bootin.elf').read_bytes(),
             'im.elf':(DONOR/'nflasha15-files/bin/im.elf').read_bytes(), 'appFw.so':fx6}
    closures = {}
    for name, data in roots.items():
        queue, seen, missing, nodes = [(name,data)], set(), [], {}
        while queue:
            path, payload = queue.pop(0)
            if path in seen:
                continue
            seen.add(path)
            elf = ELF(payload)
            edges = []
            for needed in elf.needed:
                found = lookup(needed)
                edges.append({'needed':needed, 'binding':found})
                if found:
                    queue.append((found['resolved'], members[found['resolved']][1]))
                else:
                    missing.append({'from':path,'needed':needed})
            nodes[path] = {'sha256':sha(payload),'dependencies':edges}
        closures[name] = {'nodes':nodes,'missing':missing}
    out = {'scope':'STATIC_ONLY_NO_GUEST_EXECUTION','cpio':str(CPIO),'cpio_sha256':sha(cpio),
           'members_verified':len(members),'actual_guest_libraries':libraries,
           'fx6_roots_with_fixed_fx3_library_path':closures,
           'helper':{'guest_path':helper_path,'sha256':sha(helper),'actual_source':str(HELP/'fx3-preset-context-v6-save102.c'),
                     'source_sha256':sha(source.encode()),'build_receipt':str(HELP/'fx3-preset-context-v6-save102-build.json'),
                     'init_preload_present':helper_path in init,'passive_profile_present':'FX3_DISPLAY_OBSERVE=passive-v1' in init,
                     'guards':guards,'fx3_matches':sum(x['fx3']['matches'] for x in guards),'fx6_matches':sum(x['fx6']['matches'] for x in guards)},
           'limitations':['DT_NEEDED path presence only; symbol versions and runtime initialization are separate gates',
                         'Conditional helper refusal is inferred from pinned source/build and bytes; not a guest run',
                         'This helper is an observer: its rejection alone does not prove app process cannot start',
                         'Actual dlopen interposition and earlier preload effects remain unobserved for FX6',
                         'No kernel/platform/helper/Backup modification or guest payload built']}
    (HERE/'receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'members_verified':len(members),'libraries':libraries,
                      'missing_dependencies':{k:v['missing'] for k,v in closures.items()},
                      'guards':{k:out['helper'][k] for k in ('fx3_matches','fx6_matches','passive_profile_present')},
                      'first_guard':guards[0]},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
