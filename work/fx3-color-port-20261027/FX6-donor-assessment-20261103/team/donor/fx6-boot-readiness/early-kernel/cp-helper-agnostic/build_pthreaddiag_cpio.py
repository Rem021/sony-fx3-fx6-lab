#!/usr/bin/env python3
"""Add FX6 real libgrm.so and preload it in /init on top of the CAPID-preinit CPIO."""
import hashlib, json, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'guest-hybrid-fx6kernel-capid-grmreal21.cpio'
LIBS = [('usr/lib/libpthread-diag.so', Path(__file__).resolve().parent/'grm-fbinit'/'libpthread-diag.so')]
OUT = ROOT / 'guest-hybrid-fx6kernel-capid-grmreal22.cpio'
FIXED = 453184500
TARGET = 'usr/lib/libgrm.so'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def parse(data):
    members = []
    off = 0
    while off + 110 <= len(data):
        hdr = data[off:off+110]
        if hdr[:6] != b'070701':
            raise SystemExit('bad newc magic at %d' % off)
        vals = [int(hdr[6+i*8:14+i*8], 16) for i in range(13)]
        ino, mode, uid, gid, nlink, mtime, filesize, devmaj, devmin, rdevmaj, rdevmin, namesize, check = vals
        name = data[off+110:off+110+namesize-1].decode()
        name_end = off + 110 + namesize
        name_end += (-name_end) % 4
        payload = data[name_end:name_end+filesize]
        end = name_end + filesize
        end += (-end) % 4
        members.append({'name': name, 'hdr': hdr, 'mode': mode, 'uid': uid, 'gid': gid,
                        'nlink': nlink, 'mtime': mtime, 'filesize': filesize,
                        'devmaj': devmaj, 'devmin': devmin, 'rdevmaj': rdevmaj,
                        'rdevmin': rdevmin, 'check': check, 'data': payload,
                        'has_trailer': name == 'TRAILER!!!'})
        off = end
        if name == 'TRAILER!!!':
            break
    if not members or members[-1]['name'] != 'TRAILER!!!':
        raise SystemExit('no trailer')
    return members


def header(name, mode, uid, gid, nlink, mtime, filesize, devmaj=0, devmin=0, rdevmaj=0, rdevmin=0, ino=0):
    nb = name.encode() + b'\0'
    vals = [ino, mode, uid, gid, nlink, mtime, filesize, devmaj, devmin, rdevmaj, rdevmin, len(nb), 0]
    h = b'070701' + b''.join(b'%08x' % v for v in vals)
    assert len(h) == 110
    out = h + nb
    out += b'\0' * ((-len(out)) % 4)
    return out


def main():
    src = SRC.read_bytes()
    members = parse(src)
    # Preload real FX6 libgrm only on the bootin line(s), not on the ld --verify/list probes.
    init = next(m for m in members if m['name'] == 'init')
    text = init['data']
    lines = text.split(b'\n')
    changed = 0
    for i, line in enumerate(lines):
        if b'bootin.elf' in line and b'LD_PRELOAD=' in line:
            lines[i] = line.replace(b'LD_PRELOAD=', b'LD_PRELOAD=/usr/lib/libpthread-diag.so:', 1)
            changed += 1
    if changed != 1:
        raise SystemExit('expected exactly one bootin LD_PRELOAD line, got %d' % changed)
    init['data'] = b'\n'.join(lines)
    init['filesize'] = len(init['data'])
    # Update init header size while preserving all other header fields.
    hdr = bytearray(init['hdr'])
    hdr[6+6*8:14+6*8] = b'%08x' % len(init['data'])
    init['hdr'] = bytes(hdr)
    # Build output: all members in order, insert libgrm before trailer.
    libs = [(name, path.read_bytes()) for name, path in LIBS]
    if any(m['name'] in {n for n, _ in libs} for m in members):
        raise SystemExit('target already exists')
    out = bytearray()
    for m in members:
        if m['name'] == 'TRAILER!!!':
            for target, lib in libs:
                out += header(target, 0o100755, 0, 0, 1, 0, len(lib))
                out += lib
                out += b'\0' * ((-len(out)) % 4)
        out += m['hdr'] + m['name'].encode() + b'\0'
        out += b'\0' * ((-len(out)) % 4)
        out += m['data']
        out += b'\0' * ((-len(out)) % 4)
    if len(out) > FIXED:
        raise SystemExit('output too big: %d' % len(out))
    out += b'\0' * (FIXED - len(out))
    OUT.write_bytes(out)
    receipt = {
        'schema': 'fx6-hybrid-pthreaddiag-cpio-v1',
        'source': str(SRC), 'source_sha256': sha(SRC), 'source_bytes': SRC.stat().st_size,
        'output': str(OUT), 'output_sha256': sha(OUT), 'output_bytes': OUT.stat().st_size,
        'fixed_bytes': FIXED,
        'init': {'changed': changed, 'old_bytes': len(text), 'new_bytes': len(init['data']),
                 'preload_added': '/usr/lib/libgrm.so:'},
        'new_members': [{'name': target, 'bytes': len(lib), 'sha256': hashlib.sha256(lib).hexdigest()} for target, lib in libs],
        'source_member_count': len(members),
    }
    (ROOT / 'PTHREADDIAG-CPIO-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
