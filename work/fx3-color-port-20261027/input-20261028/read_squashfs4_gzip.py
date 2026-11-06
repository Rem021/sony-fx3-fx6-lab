#!/usr/bin/env python3
"""Bounded read-only SquashFS 4.0/gzip reader for original updater images.

Implements metadata streams, basic/extended directories and regular files,
fragments and symlink records. Does not mount or create links/devices, execute
extracted code, or support other compressors. Layout reference: Linux v4.9
fs/squashfs/squashfs_fs.h. The caller separately checks an independent oracle.
"""
from functools import lru_cache
import math,stat,struct,zlib


class SquashFS:
    def __init__(self,data):
        self.data=data
        fields=struct.unpack('<5I6H8Q',self.read(0,96))
        names=('magic','inodes','mtime','block_size','fragments','compression','block_log','flags','ids','major','minor',
               'root_inode','bytes_used','id_table_start','xattr_table_start','inode_table_start','directory_table_start',
               'fragment_table_start','export_table_start')
        self.header=dict(zip(names,fields));h=self.header
        assert h['magic']==0x73717368 and (h['major'],h['minor'])==(4,0) and h['compression']==1
        assert h['block_size']==1<<h['block_log'] and 4096<=h['block_size']<=1048576
        assert 96<h['bytes_used']<=len(data) and 0<h['inodes']<100000
        self.end=h['bytes_used']

    def read(self,offset,size):
        limit=getattr(self,'end',len(self.data))
        assert 0<=offset<=limit and 0<=size<=limit-offset,(offset,size,limit)
        return self.data[offset:offset+size]

    @lru_cache(maxsize=128)
    def metadata(self,offset):
        value=struct.unpack('<H',self.read(offset,2))[0];size=value&0x7fff
        assert 0<size<=8192
        data=self.read(offset+2,size)
        if not value&0x8000:data=zlib.decompress(data)
        assert 0<len(data)<=8192
        return data,offset+2+size

    def stream(self,block,offset,size):
        result=[]
        while size:
            data,nextblock=self.metadata(block)
            assert offset>=0
            if offset>len(data):offset-=len(data);block=nextblock;continue
            count=min(size,len(data)-offset)
            if count:result.append(data[offset:offset+count]);size-=count
            block=nextblock;offset=0
        return b''.join(result)

    def inode(self,reference):
        block=self.header['inode_table_start']+(reference>>16);offset=reference&65535
        header=self.stream(block,offset,16);kind,mode,uid,gid,mtime,number=struct.unpack('<4H2I',header)
        assert 1<=kind<=14 and 1<=number<=self.header['inodes']
        extra_size={1:16,8:24,2:16,9:40,3:8,10:8}.get(kind,0)
        extra=self.stream(block,offset+16,extra_size)
        row=dict(inode_reference=hex(reference),inode=number,kind=kind,permissions=mode,uid_index=uid,gid_index=gid,mtime=mtime)
        if kind==1:
            start,nlink,size,diroff,parent=struct.unpack_from('<2I2HI',extra)
            row.update(type='directory',size=size,dir_start=start,dir_offset=diroff,parent=parent)
        elif kind==8:
            nlink,size,start,parent,index_count,diroff,xattr=struct.unpack_from('<4I2HI',extra)
            row.update(type='directory',size=size,dir_start=start,dir_offset=diroff,parent=parent)
        elif kind==2:
            start,fragment,fragment_offset,size=struct.unpack_from('<4I',extra)
            row.update(type='file',size=size,data_start=start,fragment=fragment,fragment_offset=fragment_offset,block_list_offset=16+16)
        elif kind==9:
            start,size,sparse,nlink,fragment,fragment_offset,xattr=struct.unpack_from('<3Q4I',extra)
            row.update(type='file',size=size,data_start=start,fragment=fragment,fragment_offset=fragment_offset,block_list_offset=16+40)
        elif kind in (3,10):
            nlink,size=struct.unpack_from('<2I',extra);assert size<=4096
            target=self.stream(block,offset+24,size).decode('utf-8')
            row.update(type='symlink',size=size,target=target)
        else:row.update(type='special_record_only',size=0)
        types={1:stat.S_IFDIR,8:stat.S_IFDIR,2:stat.S_IFREG,9:stat.S_IFREG,3:stat.S_IFLNK,10:stat.S_IFLNK,
               4:stat.S_IFBLK,11:stat.S_IFBLK,5:stat.S_IFCHR,12:stat.S_IFCHR,6:stat.S_IFIFO,13:stat.S_IFIFO,7:stat.S_IFSOCK,14:stat.S_IFSOCK}
        row['mode']=stat.filemode(types[kind]|mode)
        return row

    def directory(self,inode):
        assert inode['type']=='directory' and inode['size']>=3
        data=self.stream(self.header['directory_table_start']+inode['dir_start'],inode['dir_offset'],inode['size']-3)
        pos=0
        while pos<len(data):
            assert len(data)-pos>=12
            count,start,number=struct.unpack_from('<3I',data,pos);pos+=12;assert count<256
            for _ in range(count+1):
                assert len(data)-pos>=8
                offset,delta,kind,length=struct.unpack_from('<HhHH',data,pos);pos+=8;length+=1
                assert 1<=length<=256 and length<=len(data)-pos
                name=data[pos:pos+length].decode('utf-8');pos+=length
                assert name not in ('','.','..') and '/' not in name and '\0' not in name
                reference=(start<<16)|offset
                child=self.inode(reference);assert child['inode']==number+delta
                yield name,child
        assert pos==len(data)

    @lru_cache(maxsize=64)
    def block(self,start,encoded_size):
        size=encoded_size&0xffffff;assert 0<size<=self.header['block_size']
        data=self.read(start,size)
        if not encoded_size&(1<<24):data=zlib.decompress(data)
        assert 0<len(data)<=self.header['block_size']
        return data

    def fragment(self,index):
        assert 0<=index<self.header['fragments']
        block_index=(index*16)//8192;offset=(index*16)%8192
        pointer=struct.unpack('<Q',self.read(self.header['fragment_table_start']+block_index*8,8))[0]
        start,size,unused=struct.unpack('<QII',self.stream(pointer,offset,16))
        return self.block(start,size)

    def contents(self,inode):
        assert inode['type']=='file' and 0<=inode['size']<=128*1024*1024
        size=inode['size'];bs=self.header['block_size'];fragment=inode['fragment']
        count=(size+bs-1)//bs if fragment==0xffffffff else size//bs
        reference=int(inode['inode_reference'],16);block=self.header['inode_table_start']+(reference>>16)
        offset=(reference&65535)+inode['block_list_offset']
        encoded=self.stream(block,offset,count*4);start=inode['data_start'];parts=[];done=0
        for value, in struct.iter_unpack('<I',encoded):
            wanted=min(bs,size-done)
            data=self.block(start,value) if value else bytes(wanted)
            assert len(data)==wanted,(inode['inode'],len(data),wanted)
            parts.append(data);done+=len(data);start+=value&0xffffff
        if done<size:
            assert fragment!=0xffffffff
            raw=self.fragment(fragment);off=inode['fragment_offset'];remaining=size-done
            assert off+remaining<=len(raw);parts.append(raw[off:off+remaining]);done+=remaining
        assert done==size
        return b''.join(parts)

    def walk(self):
        count=0
        def recurse(path,inode,ancestors):
            nonlocal count
            count+=1;assert count<=100000
            yield dict(path=path,**inode)
            if inode['type']=='directory':
                assert inode['inode'] not in ancestors
                names=set()
                for name,child in self.directory(inode):
                    assert name not in names;names.add(name)
                    yield from recurse(path.rstrip('/')+'/'+name,child,ancestors+(inode['inode'],))
        yield from recurse('/',self.inode(self.header['root_inode']),())
