#!/usr/bin/env python3
"""Original body-image assembly from the official plaintext source.

This isolates the consumer of the already decrypted stream. It does not model
legacy/CBC decryption, input admission, native file I/O, mounting or dlopen.
"""
from pathlib import Path
import hashlib,json,struct,sys
HERE=Path(__file__).resolve().parent
AP=HERE.parent/'ap-input-20261029'
sys.path.insert(0,str(AP))
from current_static import View,sources
from header_guest import HeaderGuest,DATA,STACK,STOP,R

FIRM=HERE.parents[2]/'work/sony-firmware-20261024/fx3-7.02-decrypted.fdat'
FIRM_PIN='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
PEEK=STOP+0x100
ADVANCE=STOP+0x104

class Guest(HeaderGuest):
    def __init__(self,view,stream,chunk=32768):
        self.stream=stream;self.position=512;self.chunk=chunk;self.events=[];self.sink=bytearray();self.strings={}
        super().__init__(view)
        self.u.mem_map(DATA+0x4000,0x200000)
        self.defined={s.name:s['st_value'] for s in view.symbols if s['st_shndx']!='SHN_UNDEF' and s['st_info']['type']=='STT_FUNC' and s['st_size']}
        self.allowed=[(0x8854,0x885c),(0x8930,0x8954),(0x8954,0x8a6c),(0x8a6c,0x8b24),(0x8e38,0x8ed0),(0x8f28,0x8f34),(0x8f84,0x8ff8),(0x95a0,0x9ae8),(0xa1f8,0xa204),(0xa514,0xa564)]

    def write(self,u,access,a,size,value,unused):
        assert DATA<=a and a+size<=DATA+0x204000 or STACK<=a and a+size<=STACK+0x10000,('outside declared synthetic RAM',hex(a),size)

    def string(self,a):
        b=bytes(self.u.mem_read(a,256)).split(b'\0',1)[0];return b.decode()

    def code(self,u,pc,size,user):
        self.instructions+=1;assert self.instructions<100000
        if pc==STOP:u.emu_stop();return
        if pc in [PEEK,ADVANCE]:
            x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(3)]
            if pc==PEEK:
                count=min(x[2],self.chunk);assert 0<count<=32768
                self.stream.seek(self.position);data=self.stream.read(count);assert len(data)==count
                u.mem_write(DATA+0x10000,data);u.mem_write(x[1],struct.pack('<Q',DATA+0x10000));self.ret(count)
            else:
                self.position+=x[1];assert self.position<=808704512;self.ret(x[1])
            return
        if pc in self.plt:
            raw=self.plt[pc];name=self.view.names.get(raw,raw);x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
            if raw in self.defined:u.reg_write(R.UC_ARM64_REG_PC,self.defined[raw]);return
            if raw=='_Znam':assert x[0]==512;self.ret(DATA+0x1000);return
            if raw.startswith('pthread_mutex_'):self.ret(0);return
            if raw=='memset':u.mem_write(x[0],bytes([x[1]&255])*x[2]);self.ret(x[0]);return
            if raw=='memcpy':assert x[2]<=512;u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0]);return
            if raw=='memcmp':
                a=bytes(u.mem_read(x[0],x[2]));b=bytes(u.mem_read(x[1],x[2]));self.ret(0 if a==b else 0xffffffffffffffff if a<b else 1);return
            if name.startswith('Updater::StringHandler::StringHandler'):self.strings[x[0]]='';self.ret(0);return
            if name.startswith('Updater::StringHandler::SetString'):self.strings[x[0]]=self.string(x[1]);self.ret(0);return
            if name.startswith('Updater::StringHandler::~StringHandler'):self.ret(0);return
            if name.startswith('Updater::DirectoryHandler::Create'):self.events.append(dict(operation='directory_request_only',path=self.strings[x[0]]));self.ret(1);return
            if name.startswith('Updater::FileHandler::FileHandler') or name.startswith('Updater::FileHandler::~FileHandler'):self.ret(0);return
            if name.startswith('Updater::FileHandler::Open'):
                path=self.string(x[1]);assert path=='/tmp_updater/updater/bodyimg';self.events.append(dict(operation='memory_sink_open',path=path,flags=x[2]));self.ret(1);return
            if name.startswith('Updater::FileHandler::WriteAll'):
                assert 0<x[2]<=32768;self.sink+=bytes(u.mem_read(x[1],x[2]));u.mem_write(x[3],struct.pack('<Q',x[2]));self.ret(1);return
            if name.startswith('Updater::FileHandler::Close'):self.events.append(dict(operation='memory_sink_close'));self.ret(1);return
            if raw=='printf':self.ret(0);return
            if raw=='__cxa_allocate_exception':assert x[0]==16;self.ret(DATA+0x3000);return
            if raw=='__cxa_throw':raise AssertionError(('original exception',hex(struct.unpack('<I',u.mem_read(x[0]+8,4))[0]),hex(pc)))
            raise AssertionError(('unmodelled boundary',name,hex(pc)))
        assert any(a<=pc<b for a,b in self.allowed),('outside selected original spans',hex(pc))

    def prepare(self,header):
        self.u.mem_write(DATA+0x800,header)
        self.run(0x8f84,[DATA,6,1]) # Original BaseBodyLoader ctor; mode/bool match crypt manager initialization.
        self.run(0x89b0,[DATA+0xc0,DATA+0x800,512])
        check,_=self.run(0x8a74,[DATA+0xc0]);assert check==1
        self.u.mem_write(DATA+0x48,struct.pack('<Q',DATA+0x2000))
        self.u.mem_write(DATA+0x2000,struct.pack('<Q',DATA+0x2200))
        self.u.mem_write(DATA+0x2248,struct.pack('<QQ',PEEK,ADVANCE))

def main():
    source=next(s for s in sources() if Path(s['path']).name=='libupdatercorecommon.so');view=View(source['path'],source['sha256'])
    inventory=json.loads((HERE.parent/'package-20261028/updater-inventory.json').read_text())
    with FIRM.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==FIRM_PIN;stream.seek(0);header=stream.read(512)
        g=Guest(view,stream);g.prepare(header);_,instructions=g.run(0x95a0,[DATA]);image=bytes(g.sink)
    assert len(image)==inventory['filesystem_bytes'] and hashlib.sha256(image).hexdigest()==inventory['filesystem_sha256']
    result=dict(source_library_sha256=source['sha256'],original_fdat_sha256=FIRM_PIN,header_sha256=hashlib.sha256(header).hexdigest(),
                image_bytes=len(image),image_sha256=hashlib.sha256(image).hexdigest(),previous_independent_image_matches=True,plaintext_cursor_after=g.position,assembly_instructions=instructions,total_instructions=g.instructions,events=g.events,
                scope='Original BaseBodyLoader constructor, header constructor/set/check/getters and createBodyImage execute in synthetic RAM. Plaintext ring input and file/directory outputs are explicit adapters; output image is held in host memory and hashed only. No original decryptor or complete manager/thread flow, original native file I/O, mount, dlopen, USB, camera, changed library or complete firmware package is executed or emitted.')
    (HERE/'body-assembly-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(image_bytes=len(image),image_sha256=result['image_sha256'],matches_prior_image=True,camera_actions=0)))

if __name__=='__main__':main()
