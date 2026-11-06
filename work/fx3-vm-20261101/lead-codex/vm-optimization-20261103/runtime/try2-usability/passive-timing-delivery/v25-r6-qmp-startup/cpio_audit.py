"""Read-only newc structure audit, including Linux unpack parent ordering."""
from pathlib import Path
import hashlib
import stat


def parse(path):
    b = path.read_bytes()
    off = 0
    rows = []
    data = {}
    directories = {'.'}
    errors = []
    trailer = False
    while off < len(b):
        header = b[off:off + 110]
        if header[:6] not in (b'070701', b'070702'):
            raise ValueError('Not uncompressed newc header at ' + hex(off))
        f = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        if f[11] < 1:
            raise ValueError('Invalid cpio namesize')
        raw_name = b[off + 110:off + 110 + f[11]]
        if len(raw_name) != f[11] or raw_name[-1:] != b'\0':
            raise ValueError('Invalid cpio name')
        name = raw_name[:-1].decode()
        off = (off + 110 + f[11] + 3) & ~3
        content = b[off:off + f[6]]
        if len(content) != f[6]:
            raise ValueError('Truncated cpio member')
        off = (off + f[6] + 3) & ~3
        if name == 'TRAILER!!!':
            trailer = True
            break
        if name.startswith('/') or '..' in Path(name).parts or name in data:
            raise ValueError('Unsafe or duplicate cpio member ' + name)
        parent = str(Path(name).parent)
        if parent not in directories:
            errors.append({'member': name, 'missing_preceding_directory': parent})
        if stat.S_ISDIR(f[1]):
            directories.add(name)
        data[name] = content
        rows.append({'path': name, 'mode': oct(f[1]), 'bytes': len(content),
                     'sha256': hashlib.sha256(content).hexdigest(),
                     'rdev_major': f[9], 'rdev_minor': f[10]})
    if not trailer:
        raise ValueError('No cpio trailer')
    return {'members': rows, 'member_count': len(rows),
            'unpack_parent_order_errors': errors,
            'init_text': data.get('init', b'').decode(errors='replace')}, data


def audit(initrd, baseline):
    report, files = parse(initrd)
    _, original = parse(baseline)
    elf = {n: d for n, d in original.items() if d.startswith(b'\x7fELF')}
    changed = [n for n, d in elf.items() if files.get(n) != d]
    report['original_baseline_ELF_members'] = len(elf)
    report['baseline_ELF_changed_or_missing'] = changed
    report['baseline_cpio_sha256'] = hashlib.sha256(baseline.read_bytes()).hexdigest()
    report['candidate_cpio_sha256'] = hashlib.sha256(initrd.read_bytes()).hexdigest()
    report['safe_to_unpack'] = not report['unpack_parent_order_errors'] and not changed
    return report
