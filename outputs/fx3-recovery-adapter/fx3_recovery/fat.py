"""Bounded FAT12 P1 reader with cluster-to-image mapping. No mount or extraction."""
import struct
from .files import require

MAX_P1 = 25_100_288


class FatP1:
    def __init__(self, data):
        self.data = data
        require(512 <= len(data) <= MAX_P1 and data[510:512] == b'\x55\xaa', 'invalid P1 boot sector')
        u16 = lambda at: struct.unpack_from('<H', data, at)[0]
        self.sector, self.cluster_sectors = u16(11), data[13]
        reserved, copies, entries, fat_sectors = u16(14), data[16], u16(17), u16(22)
        total = u16(19) or struct.unpack_from('<I', data, 32)[0]
        require(self.sector == 512 and self.cluster_sectors == 32 and reserved == 1 and copies == 2 and entries == 512 and fat_sectors == 32,
                'unsupported FX3 P1 FAT geometry')
        self.fat_start = reserved*512
        fat_size = fat_sectors*512
        self.root = (reserved+copies*fat_sectors)*512
        self.root_size = entries*32
        self.start = self.root+self.root_size
        self.cluster_size = 512*self.cluster_sectors
        require(self.start <= total*512 <= len(data), 'FAT declared size exceeds input')
        self.clusters = (total*512-self.start)//self.cluster_size
        require(0 < self.clusters < 4085 and (self.clusters+2)*3//2+2 <= fat_size, 'unsupported FAT12 cluster count')
        self.fat = data[self.fat_start:self.fat_start+fat_size]
        require(self.fat == data[self.fat_start+fat_size:self.fat_start+2*fat_size], 'FAT copies differ')
        self.files, self.owners = {}, {}
        self._walk(None, '', 0)

    def chain(self, number):
        seen, chain = set(), []
        while number < 0xff8:
            require(2 <= number < self.clusters+2 and number not in seen, 'invalid or cyclic FAT chain')
            seen.add(number); chain.append(number)
            at = number+number//2
            value = struct.unpack_from('<H', self.fat, at)[0]
            number = value >> 4 if number & 1 else value & 0xfff
        require(chain and number <= 0xfff, 'empty or invalid chain')
        return chain

    def segment(self, number):
        start = self.start+(number-2)*self.cluster_size
        require(start+self.cluster_size <= len(self.data), 'cluster outside input')
        return start

    def _claim(self, chain, name):
        for cluster in chain:
            require(cluster not in self.owners, 'cross-linked FAT files/directories')
            self.owners[cluster] = name

    def _walk(self, chain, parent, depth):
        require(depth < 16 and len(self.files) < 1024, 'FAT directory bound')
        raw = self.data[self.root:self.root+self.root_size] if chain is None else b''.join(
            self.data[self.segment(n):self.segment(n)+self.cluster_size] for n in chain)
        long = []
        for at in range(0, len(raw), 32):
            require(len(self.files) < 4096, 'FAT entry bound')
            row = raw[at:at+32]
            if row[0] == 0:
                require(not long, 'orphan FAT long name')
                break
            if row[0] == 0xe5:
                long = []
                continue
            attr = row[11]
            if attr == 0x0f:
                sequence = row[0]&31
                require(1 <= sequence <= 20 and not row[0]&0xa0 and row[12] == 0 and row[26:28] == b'\0\0', 'invalid FAT long-name record')
                require((not long and row[0]&0x40) or (long and not row[0]&0x40 and sequence == long[-1][0]-1), 'FAT long-name order differs')
                long.append((sequence, row[13], row[1:11]+row[14:26]+row[28:32]))
                continue
            if attr & 8:
                require(not long, 'long name before volume label')
                continue
            name = row[:8].rstrip(b' ').decode('ascii')
            extension = row[8:11].rstrip(b' ').decode('ascii')
            if name in ('.', '..'):
                require(not long, 'long name on directory dot record')
                continue
            if extension:name += '.'+extension
            if long:
                check = 0
                for value in row[:11]:check = (((check&1)<<7)+(check>>1)+value)&255
                require(long[-1][0] == 1 and all(r[1] == check for r in long), 'FAT long-name checksum differs')
                text = b''.join(r[2] for r in sorted(long)).decode('utf-16-le')
                if '\0' in text:
                    text, padding = text.split('\0', 1)
                    require(all(c == '\uffff' for c in padding), 'invalid FAT name padding')
                require(0 < len(text) <= 255 and all(32 <= ord(c) < 127 for c in text), 'unsupported FAT long name')
                name = text
                long = []
            name = name.lower()
            require(name not in ('', '.', '..') and name == name.strip() and not any(c in name for c in '/\\:'), 'invalid FAT name')
            path = parent+'/'+name
            require(path not in self.files, 'duplicate FAT name')
            number, size = struct.unpack_from('<H', row, 26)[0], struct.unpack_from('<I', row, 28)[0]
            require(struct.unpack_from('<H', row, 20)[0] == 0, 'unsupported high cluster')
            require(not attr & 0xc0, 'unsupported FAT attribute')
            clusters = self.chain(number) if number else []
            require(not size or clusters and size <= len(clusters)*self.cluster_size, 'file chain too short')
            if attr & 16:require(clusters and not size, 'invalid directory record')
            self._claim(clusters, path)
            self.files[path] = {'clusters': clusters, 'size': size, 'directory': bool(attr & 16)}
            if attr & 16:self._walk(clusters, path, depth+1)
        require(not long, 'orphan FAT long name at directory end')

    def mapping(self, name, offset=0, size=None):
        entry = self.files.get(name)
        require(entry is not None and not entry['directory'], 'P1 member missing: '+name)
        if size is None:size = entry['size']-offset
        require(0 <= offset <= entry['size'] and 0 <= size <= entry['size']-offset, 'member range invalid')
        result = []
        while size:
            index, intra = divmod(offset, self.cluster_size)
            take = min(size, self.cluster_size-intra)
            absolute = self.segment(entry['clusters'][index])+intra
            if result and result[-1][0]+result[-1][1] == absolute:
                result[-1] = (result[-1][0], result[-1][1]+take)
            else:result.append((absolute, take))
            offset += take;size -= take
        return result

    def contents(self, name):
        return b''.join(self.data[at:at+n] for at, n in self.mapping(name))

    def replace(self, output, name, offset, raw):
        cursor = 0
        for at, n in self.mapping(name, offset, len(raw)):
            output[at:at+n] = raw[cursor:cursor+n]
            cursor += n
