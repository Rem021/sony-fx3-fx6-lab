#!/usr/bin/env python3
"""Original TAR header parser and key factory with a read-only 512-byte adapter."""
from pathlib import Path
import hashlib,json,struct,tarfile
from keytag_factory_guest import Guest as FactoryGuest,DATA,HERE,View,PATH,PIN,R

OBJ=DATA+0x3000
BLOCK=DATA+0x5000

class Guest(FactoryGuest):
    def __init__(self,views,raw):
        assert len(raw)==512;super().__init__(views)
        self.pretty={name:label for base,view in views for name,label in view.names.items()}
        self.extra_permitted_names=['PackedFileHeader::','CreateValueFromOctalString']
        self.u.mem_write(BLOCK,raw);self.block_requests=0

    def code(self,u,pc,size,user):
        if pc in self.plt:
            raw=self.plt[pc];name=self.pretty.get(raw,raw)
            if name=='Updater::PackedFirmwareBuffer::GetCurrentBlock()':self.block_requests+=1;assert self.block_requests<=2;self.ret(BLOCK);return
            if raw=='isspace':self.ret(int(u.reg_read(R.UC_ARM64_REG_X0) in [9,10,11,12,13,32]));return
        return super().code(u,pc,size,user)

    def parse(self):
        self.run(0x10011c00,[OBJ]);ret,steps=self.run(0x10011eb8,[OBJ,DATA+0x6000])
        row=dict(parse_result=ret,parser_instructions=steps,block_requests=self.block_requests)
        if ret==0:
            getter=next(address for name,address in self.definitions.items() if self.pretty.get(name)=='Updater::StringHandler::GetCharString() const')
            pointer,_=self.run(getter,[OBJ+8]);normalized=self.string(pointer).decode()
            index=struct.unpack('<I',self.u.mem_read(OBJ+0x48,4))[0]
            tag,tag_steps=self.run(0x1001335c,[index,OBJ+8]);vptr=struct.unpack('<Q',self.u.mem_read(tag,8))[0]
            row.update(normalized_name=normalized,index=index,result_type=self.vtables[vptr],factory_instructions=tag_steps)
        return row

def main():
    ap=HERE.parent/'ap-input-20261029';common_source=next(r for r in json.loads((ap/'additional-source-members.json').read_text()) if r['original_path']=='/lib/libupdatercommon.so')
    views=[(0x10000000,View(PATH,PIN)),(0x20000000,View(ap/common_source['output'],common_source['sha256']))]
    project=HERE.parents[2];firm=project/'work/sony-firmware-20261024/fx3-7.02-decrypted.fdat';manifest=json.loads((project/'work/sony-firmware-20261024/fx3-7.02-offline-manifest.json').read_text())
    fixtures=[]
    with firm.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==manifest['decrypted_fdat_sha256']
        for name in ['0100_config','0100_config/mount.conf']:
            item=next(r for r in manifest['tar_members'] if r['name']==name);offset=manifest['firmware_tar_offset']+item['data_offset_in_tar']-512
            stream.seek(offset);raw=stream.read(512);assert raw[:len(name)]==name.encode();fixtures.append((name,raw,'official_original_header'))
    toy=tarfile.TarInfo('0001_program/probe.txt');toy.mode=0o644;toy.size=0;raw=toy.tobuf(format=tarfile.USTAR_FORMAT)
    fixtures.append(('0001_program/probe.txt',raw,'isolated_empty_nonexecutable_file_header'))
    bad=bytearray(raw);bad[0]^=1;fixtures.append(('corrupted_checksum',bytes(bad),'isolated_bad_header'))
    rows=[]
    for label,raw,kind in fixtures:
        row=Guest(views,raw).parse();row.update(case=label,fixture_kind=kind,header_sha256=hashlib.sha256(raw).hexdigest());rows.append(row)
    assert all(r['parse_result']==0 for r in rows[:3]) and rows[3]['parse_result']==2
    assert rows[0]['normalized_name']=='config' and rows[1]['normalized_name']=='config/mount.conf'
    assert rows[2]['normalized_name']=='program/probe.txt' and rows[2]['result_type']=='vtable for Updater::CommonKeyTag'
    result=dict(body_library_sha256=PIN,common_library_sha256=common_source['sha256'],official_plain_fdat_sha256=manifest['decrypted_fdat_sha256'],cases=rows,
                scope='Original PackedFileHeader constructor/Parse/filename normalization, octal conversion, StringHandler and KeyTagFactory execute in synthetic RAM. The only source adapter returns one declared 512-byte block; host shims are allocation, bounded libc bytes/strings and ASCII isspace. The program fixture describes an empty nonexecutable text file and has no payload or full update container. No file extraction, XML dispatch, unsigned code execution, native process, external admission, changed complete package, USB or camera action.')
    (HERE/'tar-header-guest-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),normalized_program_name=rows[2]['normalized_name'],program_tag=rows[2]['result_type'],bad_checksum_rejected=True,camera_actions=0)))

if __name__=='__main__':main()
