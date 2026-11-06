# Derived from the existing project read-only reader; hardened bounds, no execution.
"""Bounded read-only SquashFS 4.0/gzip reader for original updater images.

Implements metadata streams, basic/extended directories and regular files,
fragments and symlink records. Does not mount or create links/devices, execute
extracted code, or support other compressors. Layout reference: Linux v4.9
fs/squashfs/squashfs_fs.h. The caller separately checks an independent oracle.
"""
from functools import lru_cache
import math, stat, struct, zlib

def inflate_bounded(data, limit):
    dec=zlib.decompressobj()
    out=dec.decompress(data,limit+1)
    if len(out)>limit or dec.unconsumed_tail or not dec.eof or dec.unused_data:
        raise ValueError('invalid or over-limit compressed block')
    return out

class SquashFS:

    def __init__(self, data):
        self.data = data
        fields = struct.unpack('<5I6H8Q', self.read(0, 96))
        names = ('magic', 'inodes', 'mtime', 'block_size', 'fragments', 'compression', 'block_log', 'flags', 'ids', 'major', 'minor', 'root_inode', 'bytes_used', 'id_table_start', 'xattr_table_start', 'inode_table_start', 'directory_table_start', 'fragment_table_start', 'export_table_start')
        self.header = dict(zip(names, fields))
        h = self.header
        if not (h['magic'] == 1936814952 and (h['major'], h['minor']) == (4, 0) and (h['compression'] == 1)):
            raise ValueError('invalid SquashFS structure')
        if not (h['block_size'] == 1 << h['block_log'] and 4096 <= h['block_size'] <= 1048576):
            raise ValueError('invalid SquashFS structure')
        if not (96 < h['bytes_used'] <= len(data) and 0 < h['inodes'] < 100000):
            raise ValueError('invalid SquashFS structure')
        self.end = h['bytes_used']

    def read(self, offset, size):
        limit = getattr(self, 'end', len(self.data))
        if not (0 <= offset <= limit and 0 <= size <= limit - offset):
            raise ValueError('invalid SquashFS structure')
        return self.data[offset:offset + size]

    @lru_cache(maxsize=128)
    def metadata(self, offset):
        value = struct.unpack('<H', self.read(offset, 2))[0]
        size = value & 32767
        if not 0 < size <= 8192:
            raise ValueError('invalid SquashFS structure')
        data = self.read(offset + 2, size)
        if not value & 32768:
            data = inflate_bounded(data, 8192)
        if not 0 < len(data) <= 8192:
            raise ValueError('invalid SquashFS structure')
        return (data, offset + 2 + size)

    def stream(self, block, offset, size):
        result = []
        hops=0
        while size:
            hops+=1
            if hops>65536:raise ValueError('metadata hop bound')
            data, nextblock = self.metadata(block)
            if not offset >= 0:
                raise ValueError('invalid SquashFS structure')
            if offset > len(data):
                offset -= len(data)
                block = nextblock
                continue
            count = min(size, len(data) - offset)
            if count:
                result.append(data[offset:offset + count])
                size -= count
            block = nextblock
            offset = 0
        return b''.join(result)

    def inode(self, reference):
        block = self.header['inode_table_start'] + (reference >> 16)
        offset = reference & 65535
        header = self.stream(block, offset, 16)
        kind, mode, uid, gid, mtime, number = struct.unpack('<4H2I', header)
        if not (1 <= kind <= 14 and 1 <= number <= self.header['inodes']):
            raise ValueError('invalid SquashFS structure')
        extra_size = {1: 16, 8: 24, 2: 16, 9: 40, 3: 8, 10: 8}.get(kind, 0)
        extra = self.stream(block, offset + 16, extra_size)
        row = dict(inode_reference=hex(reference), inode=number, kind=kind, permissions=mode, uid_index=uid, gid_index=gid, mtime=mtime)
        if kind == 1:
            start, nlink, size, diroff, parent = struct.unpack_from('<2I2HI', extra)
            row.update(type='directory', size=size, dir_start=start, dir_offset=diroff, parent=parent)
        elif kind == 8:
            nlink, size, start, parent, index_count, diroff, xattr = struct.unpack_from('<4I2HI', extra)
            row.update(type='directory', size=size, dir_start=start, dir_offset=diroff, parent=parent)
        elif kind == 2:
            start, fragment, fragment_offset, size = struct.unpack_from('<4I', extra)
            row.update(type='file', size=size, data_start=start, fragment=fragment, fragment_offset=fragment_offset, block_list_offset=16 + 16)
        elif kind == 9:
            start, size, sparse, nlink, fragment, fragment_offset, xattr = struct.unpack_from('<3Q4I', extra)
            row.update(type='file', size=size, data_start=start, fragment=fragment, fragment_offset=fragment_offset, block_list_offset=16 + 40)
        elif kind in (3, 10):
            nlink, size = struct.unpack_from('<2I', extra)
            if not size <= 4096:
                raise ValueError('invalid SquashFS structure')
            target = self.stream(block, offset + 24, size).decode('utf-8')
            row.update(type='symlink', size=size, target=target)
        else:
            row.update(type='special_record_only', size=0)
        types = {1: stat.S_IFDIR, 8: stat.S_IFDIR, 2: stat.S_IFREG, 9: stat.S_IFREG, 3: stat.S_IFLNK, 10: stat.S_IFLNK, 4: stat.S_IFBLK, 11: stat.S_IFBLK, 5: stat.S_IFCHR, 12: stat.S_IFCHR, 6: stat.S_IFIFO, 13: stat.S_IFIFO, 7: stat.S_IFSOCK, 14: stat.S_IFSOCK}
        row['mode'] = stat.filemode(types[kind] | mode)
        return row

    def directory(self, inode):
        if not (inode['type'] == 'directory' and inode['size'] >= 3):
            raise ValueError('invalid SquashFS structure')
        data = self.stream(self.header['directory_table_start'] + inode['dir_start'], inode['dir_offset'], inode['size'] - 3)
        pos = 0
        while pos < len(data):
            if not len(data) - pos >= 12:
                raise ValueError('invalid SquashFS structure')
            count, start, number = struct.unpack_from('<3I', data, pos)
            pos += 12
            if not count < 256:
                raise ValueError('invalid SquashFS structure')
            for _ in range(count + 1):
                if not len(data) - pos >= 8:
                    raise ValueError('invalid SquashFS structure')
                offset, delta, kind, length = struct.unpack_from('<HhHH', data, pos)
                pos += 8
                length += 1
                if not (1 <= length <= 256 and length <= len(data) - pos):
                    raise ValueError('invalid SquashFS structure')
                name = data[pos:pos + length].decode('utf-8')
                pos += length
                if not (name not in ('', '.', '..') and '/' not in name and ('\x00' not in name)):
                    raise ValueError('invalid SquashFS structure')
                reference = start << 16 | offset
                child = self.inode(reference)
                if not child['inode'] == number + delta:
                    raise ValueError('invalid SquashFS structure')
                yield (name, child)
        if not pos == len(data):
            raise ValueError('invalid SquashFS structure')

    @lru_cache(maxsize=64)
    def block(self, start, encoded_size):
        size = encoded_size & 16777215
        if not 0 < size <= self.header['block_size']:
            raise ValueError('invalid SquashFS structure')
        data = self.read(start, size)
        if not encoded_size & 1 << 24:
            data = inflate_bounded(data, 1048576)
        if not 0 < len(data) <= self.header['block_size']:
            raise ValueError('invalid SquashFS structure')
        return data

    def fragment(self, index):
        if not 0 <= index < self.header['fragments']:
            raise ValueError('invalid SquashFS structure')
        block_index = index * 16 // 8192
        offset = index * 16 % 8192
        pointer = struct.unpack('<Q', self.read(self.header['fragment_table_start'] + block_index * 8, 8))[0]
        start, size, unused = struct.unpack('<QII', self.stream(pointer, offset, 16))
        return self.block(start, size)

    def contents(self, inode):
        if not (inode['type'] == 'file' and 0 <= inode['size'] <= 128 * 1024 * 1024):
            raise ValueError('invalid SquashFS structure')
        size = inode['size']
        bs = self.header['block_size']
        fragment = inode['fragment']
        count = (size + bs - 1) // bs if fragment == 4294967295 else size // bs
        reference = int(inode['inode_reference'], 16)
        block = self.header['inode_table_start'] + (reference >> 16)
        offset = (reference & 65535) + inode['block_list_offset']
        encoded = self.stream(block, offset, count * 4)
        start = inode['data_start']
        parts = []
        done = 0
        for value, in struct.iter_unpack('<I', encoded):
            wanted = min(bs, size - done)
            data = self.block(start, value) if value else bytes(wanted)
            if not len(data) == wanted:
                raise ValueError('invalid SquashFS structure')
            parts.append(data)
            done += len(data)
            start += value & 16777215
        if done < size:
            if not fragment != 4294967295:
                raise ValueError('invalid SquashFS structure')
            raw = self.fragment(fragment)
            off = inode['fragment_offset']
            remaining = size - done
            if not off + remaining <= len(raw):
                raise ValueError('invalid SquashFS structure')
            parts.append(raw[off:off + remaining])
            done += remaining
        if not done == size:
            raise ValueError('invalid SquashFS structure')
        return b''.join(parts)

    def walk(self):
        count = 0

        def recurse(path, inode, ancestors):
            nonlocal count
            count += 1
            if not count <= 100000:
                raise ValueError('invalid SquashFS structure')
            yield dict(path=path, **inode)
            if len(ancestors)>32:raise ValueError('directory depth bound')
            if inode['type'] == 'directory':
                if not inode['inode'] not in ancestors:
                    raise ValueError('invalid SquashFS structure')
                names = set()
                for name, child in self.directory(inode):
                    if not name not in names:
                        raise ValueError('invalid SquashFS structure')
                    names.add(name)
                    yield from recurse(path.rstrip('/') + '/' + name, child, ancestors + (inode['inode'],))
        yield from recurse('/', self.inode(self.header['root_inode']), ())
