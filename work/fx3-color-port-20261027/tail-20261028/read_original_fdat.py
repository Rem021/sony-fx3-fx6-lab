#!/usr/bin/env python3
"""Read-only random access into pinned original Sony CBC FDAT packages.

No firmware execution, repacking, writes to source, camera or device access.
Validates outer CRC and every decrypted block actually read, rather than
claiming that sparse indexing has checked every plaintext block.
"""
from pathlib import Path
from hashlib import sha256, file_digest
import ast, importlib.util, io, json, struct, tarfile, urllib.request, warnings, zlib

HERE = Path(__file__).resolve().parent
FW = HERE.parents[2] / 'work/sony-firmware-20261024'
spec = importlib.util.spec_from_file_location('bounded_cbc', HERE.parent/'package-20261028/cbc_vectors.py')
cbc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cbc)


def public_keys():
    errors=[]
    urls=[cbc.SOURCE,cbc.SOURCE.replace('raw.githubusercontent.com/','raw.githubusercontent.com:443/'),
          'https://cdn.jsdelivr.net/gh/DavidBuchanan314/fwtool.py@3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/constants.py']
    for url in urls:
        try:
            source = urllib.request.urlopen(url, timeout=20).read()
            break
        except (OSError, urllib.error.URLError) as error:
            errors.append(type(error).__name__)
    else: raise RuntimeError('Pinned public format source unavailable: '+','.join(errors))
    assert sha256(source).hexdigest() == cbc.PIN
    log=HERE/'public-format-source-fetches.json'
    rows=json.loads(log.read_bytes()) if log.exists() else []
    rows.append(dict(url=url,sha256=cbc.PIN,bytes=len(source),preceding_errors=errors,
                     scope='Public pinned format source used only in memory; no constant values copied into artifacts.'))
    log.write_text(json.dumps(rows,indent=2)+'\n')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning); tree = ast.parse(source)
    keys = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('key_aes','key_cxd90057_k0','key_cxd90057_k8'):
                    keys[target.id] = ast.literal_eval(node.value)
    assert len(keys) == 3
    return keys


class FDAT:
    def __init__(self, path, keys, expected_sha256=None):
        self.path=Path(path); self.f=self.path.open('rb'); self.checked=set()
        size=self.path.stat().st_size
        self.sha256=file_digest(self.f,'sha256').hexdigest()
        if expected_sha256: assert self.sha256==expected_sha256
        self.f.seek(0); assert self.f.read(8)==b'\x89UFU\r\n\x1a\n'
        self.chunks=[]; pos=8
        while pos<size:
            self.f.seek(pos); length,kind=struct.unpack('>I4s',self.f.read(8))
            assert pos+8+length<=size
            self.chunks.append(dict(type=kind.decode('ascii'),offset=pos+8,bytes=length))
            pos+=8+length
        assert pos==size and self.chunks[-1]['type']=='DEND' and self.chunks[-1]['bytes']==4
        self.f.seek(0); crc=0; remaining=size-12
        while remaining:
            data=self.f.read(min(4*1024*1024,remaining)); assert data
            crc=zlib.crc32(data,crc); remaining-=len(data)
        self.f.seek(size-4); assert struct.unpack('>I',self.f.read(4))[0]==crc
        self.outer_crc32=hex(crc)
        chunks=[c for c in self.chunks if c['type']=='FDAT']; assert len(chunks)==1
        self.base=chunks[0]['offset']; self.encrypted_size=chunks[0]['bytes']-0x110
        assert self.encrypted_size>0 and self.encrypted_size%1024==0
        self.count=self.encrypted_size//1024
        self.f.seek(self.base+self.encrypted_size); self.tail=self.f.read(0x110); assert len(self.tail)==0x110
        self.f.seek(self.base); cipher=self.f.read(1024)
        first=cbc.crypt(cipher[:512],keys['key_aes'],decrypt=True,ecb=True)
        good=[]
        for name in ('key_cxd90057_k0','key_cxd90057_k8'):
            block=first+cbc.crypt(cipher[512:],keys[name],self.tail[:16],decrypt=True)
            checksum,flags=struct.unpack_from('<HH',block)
            if sum(struct.unpack('<511H',block[2:]))&0xffff==checksum and block[4:12]==b'UDTRFIRM':
                good.append((name,block))
        assert len(good)==1,'No unique published key matched the original first block'
        self.key_name,block=good[0]; self.key=keys[self.key_name]; self.ecb_key=keys['key_aes']
        data=self._validate(0,block)
        last=self._blocks(self.count-1,1)
        self.size=(self.count-1)*1020+len(last)
        header=data[:512]; assert zlib.crc32(header[12:])==struct.unpack_from('<I',header,8)[0]
        n=struct.unpack_from('<I',header,56)[0]; assert 0<=n<=28
        self.header=dict(magic=header[:8].decode(),firmware_version=f'{header[33]:x}.{header[32]:02x}',
            model_id=hex(struct.unpack_from('<I',header,36)[0]),region_id=hex(struct.unpack_from('<I',header,40)[0]),
            firmware_offset=struct.unpack_from('<I',header,48)[0],firmware_size=struct.unpack_from('<I',header,52)[0],
            filesystem_count=n,header_crc32_matches=True,filesystems=[])
        for i in range(n):
            off=64+16*i; start,length=struct.unpack_from('<II',header,off+4)
            assert start+length<=self.size
            self.header['filesystems'].append(dict(mode=chr(header[off]),offset=start,size=length))
        assert self.header['firmware_offset']+self.header['firmware_size']==self.size

    def _validate(self,index,block):
        assert len(block)==1024
        checksum,flags=struct.unpack_from('<HH',block)
        length=flags&0x7fff
        assert 0<length<=1020 and sum(struct.unpack('<511H',block[2:]))&0xffff==checksum,(index,'block checksum/length')
        assert bool(flags&0x8000)==(index==self.count-1),(index,'end flag')
        if index!=self.count-1: assert length==1020
        assert block[4+length:]==b'\xff'*(1020-length),(index,'padding')
        self.checked.add(index)
        return block[4:4+length]

    def _blocks(self,index,count):
        assert 0<=index<self.count and 0<count<=self.count-index
        if index:
            self.f.seek(self.base+index*1024-16); iv=self.f.read(16)
        else: iv=self.tail[:16]
        self.f.seek(self.base+index*1024); cipher=self.f.read(count*1024)
        assert len(cipher)==count*1024
        if index==0:
            raw=cbc.crypt(cipher[:512],self.ecb_key,decrypt=True,ecb=True)+cbc.crypt(cipher[512:],self.key,iv,decrypt=True)
        else: raw=cbc.crypt(cipher,self.key,iv,decrypt=True)
        return b''.join(self._validate(index+j,raw[j*1024:(j+1)*1024]) for j in range(count))

    def read(self,offset,length):
        assert 0<=offset<=self.size and 0<=length<=self.size-offset
        if length==0:return b''
        index=offset//1020; skip=offset%1020; count=(skip+length+1019)//1020
        data=self._blocks(index,count)[skip:skip+length]; assert len(data)==length
        return data

    def summary(self):
        return dict(source=str(self.path.relative_to(HERE)) if self.path.is_relative_to(HERE) else str(self.path),
            source_sha256=self.sha256,outer_crc32=self.outer_crc32,outer_crc32_matches=True,chunks=self.chunks,
            key_name=self.key_name,blocks=self.count,plaintext_bytes=self.size,header=self.header,
            unique_blocks_checked=len(self.checked),all_plaintext_blocks_checked=len(self.checked)==self.count,
            tail_bytes=len(self.tail),tail_sha256=sha256(self.tail).hexdigest(),
            scope='Read-only decryption and structural checks, not complete camera admission, signature, execution or boot verification.')

    def close(self):self.f.close()


class View(io.RawIOBase):
    def __init__(self,fdat,start,size):
        assert 0<=start<=fdat.size and 0<=size<=fdat.size-start
        self.fdat=fdat; self.start=start; self.size=size; self.pos=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset if whence==2 else -1
        if not 0<=pos<=self.size:raise ValueError('seek outside bounded FDAT view')
        self.pos=pos;return pos
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        data=self.fdat.read(self.start+self.pos,n);self.pos+=len(data);return data


def inventory(fdat):
    h=fdat.header; rows=[]
    with View(fdat,h['firmware_offset'],h['firmware_size']) as view, tarfile.open(fileobj=view,mode='r:') as tar:
        for member in tar:
            rows.append(dict(name=member.name,size=member.size,type=member.type.decode('ascii'),data_offset_in_tar=member.offset_data))
    return rows


def main():
    keys=public_keys(); results=[]
    # Check seek/block boundaries against the existing fully validated original 7.02 plaintext.
    current=FDAT(FW/'fx3-7.02-BODYDATA.DAT',keys)
    offsets=[0,1,508,511,512,1019,1020,1021,65535,1253888,403000000,current.size-2048,current.size-1]
    with (FW/'fx3-7.02-decrypted.fdat').open('rb') as plain:
        for offset in offsets:
            length=min(2049,current.size-offset);plain.seek(offset)
            assert current.read(offset,length)==plain.read(length),(offset,length)
    (HERE/'random-reader-validation.json').write_text(json.dumps(dict(status='PASS_ORIGINAL_702_RANDOM_READER_MATCHES_KNOWN_PLAINTEXT',offsets=offsets,source=current.summary()),indent=2)+'\n')
    current.close()
    for path in sorted((HERE/'interim-members/mspack').glob('*.dat')):
        receipt=json.loads(path.with_suffix(path.suffix+'.receipt.json').read_bytes())
        fdat=FDAT(path,keys,receipt['sha256']); rows=inventory(fdat)
        row=fdat.summary();row['tar_members']=rows;results.append(row);fdat.close()
        print(path.name,row['header'],len(rows),'tar entries',flush=True)
    assert len(results)==2
    (HERE/'interim-fdat-inventory.json').write_text(json.dumps(dict(status='PASS_ORIGINAL_INTERIM_FDAT_SPARSE_INDEX',constants_source=cbc.SOURCE,constants_source_sha256=cbc.PIN,packages=results),indent=2)+'\n')


if __name__=='__main__':main()
