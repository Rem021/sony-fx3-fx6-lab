#!/usr/bin/env python3
"""Inventory an offline glibc link_map candidate associated with SKD's page tables."""
import json,struct
from wbi_page_table_candidates import Snapshot,HERE,MASK


def main():
    identity=json.loads((HERE/'skd-snapshot-code-results.json').read_bytes())
    root=int(identity['root_physical_address'],16);base=int(identity['library_base_candidate'],16)
    s=Snapshot();inverse={};tables=0;unreadable_tables=0;block_descriptors=0
    def visit(pa,shift,va):
        nonlocal tables,unreadable_tables,block_descriptors
        try:raw=s.physical(pa,4096)
        except ValueError:unreadable_tables+=1;return
        tables+=1
        for index,(value,) in enumerate(struct.iter_unpack('<Q',raw)):
            if value&3!=3:
                if value&3==1:block_descriptors+=1
                continue
            address=va+(index<<shift)
            if shift==12:inverse.setdefault(value&MASK,[]).append(address)
            else:visit(value&MASK,shift-9,address)
    visit(root,30,0)
    def string(va):
        out=bytearray()
        for _ in range(512):
            ch=s.virtual(root,va,1);va+=1
            if ch==b'\0':return out.decode('utf-8')
            out.extend(ch)
        raise ValueError('unterminated module name')
    candidates=[];off=s.meta['data_start'];end=off+s.meta['data_bytes'];needle=struct.pack('<Q',base)
    while (off:=s.data.find(needle,off,end))!=-1:
        pos=off;off+=1
        if (pos-s.meta['data_start'])%8:continue
        pa=s.location(pos,40)
        if pa is None:continue
        values=struct.unpack_from('<5Q',s.data,pos)
        if values[2]!=base+0x2c7588:continue
        try:name=string(values[1])
        except (ValueError,UnicodeDecodeError):continue
        if 'libInfraSKD.so' not in name:continue
        for pageva in inverse.get(pa&~4095,[]):
            va=pageva+(pa&4095)
            if s.virtual(root,va,40)!=s.data[pos:pos+40]:continue
            candidates.append(dict(link_map_va=hex(va),physical_address=hex(pa),name=name))
    assert len(candidates)==1,('No unique SKD link_map candidate',candidates)
    skd=int(candidates[0]['link_map_va'],16)
    # Walk backwards, validating each reverse edge, then walk forwards from head.
    seen=set();cursor=skd
    while True:
        assert cursor not in seen;seen.add(cursor)
        values=struct.unpack('<5Q',s.virtual(root,cursor,40));previous=values[4]
        if not previous:head=cursor;break
        other=struct.unpack('<5Q',s.virtual(root,previous,40));assert other[3]==cursor
        cursor=previous;assert len(seen)<1024
    modules=[];seen=set();cursor=head;previous=0
    while cursor:
        assert cursor not in seen;seen.add(cursor)
        address,nameptr,dynamic,nextmap,prevmap=struct.unpack('<5Q',s.virtual(root,cursor,40))
        assert prevmap==previous
        error=None
        try:name=string(nameptr)
        except (ValueError,UnicodeDecodeError) as exc:name=None;error=str(exc)
        modules.append(dict(link_map_va=hex(cursor),base=hex(address),dynamic_va=hex(dynamic),name=name,name_pointer=hex(nameptr),name_read_error=error))
        previous,cursor=cursor,nextmap;assert len(seen)<1024
    assert any(int(m['link_map_va'],16)==skd for m in modules)
    result=dict(status='PASS_OFFLINE_RECIPROCAL_LINK_MAP_INVENTORY',source_sha256=s.meta['source_sha256'],
        root_physical_address=hex(root),skd=candidates[0],table_pages_read=tables,unreadable_table_pages=unreadable_tables,
        block_descriptors_not_expanded=block_descriptors,mapped_4k_pages=sum(map(len,inverse.values())),modules=modules,
        scope='Original WBI only. Structural 39-bit page-table walk and reciprocal glibc five-field link_map links agree with SKD metadata. Module names and bases are snapshot facts, not live processes, current camera mappings, original-file byte identity, executable recovery or update admission.')
    (HERE/'snapshot-link-map-inventory.json').write_text(json.dumps(result,indent=2)+'\n');s.close()
    print('link_map',len(modules),'modules','table_pages',tables,flush=True)
    for module in modules:
        if any(t in (module['name'] or '').lower() for t in ('updat','sdfile','crypt','skd')):print(module,flush=True)


if __name__=='__main__':main()
