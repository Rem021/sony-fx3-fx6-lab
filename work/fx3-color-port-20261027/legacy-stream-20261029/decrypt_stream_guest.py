#!/usr/bin/env python3
"""Whole RAM-only legacy stream through original decryptor control and wrappers.

AES mathematical primitives are explicit Apple CommonCrypto adapters; no native
Sony executable, process, mount, camera, USB or output firmware file is used.
"""
from pathlib import Path
import ctypes,hashlib,io,json,struct,sys,zlib
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'ap-input-20261029'))
from current_static import View,sources as ap_sources
sys.path.insert(0,str(TASK/'marker-20261029'))
from keytag_factory_guest import Guest as LoaderGuest,DATA,STACK,STOP,R
sys.path.insert(0,str(TASK/'package-20261028'))
from cbc_vectors import pack,crypt
sys.path.insert(0,str(TASK/'controller-20261029'))
from controller_guest import tar_stream

DEC=DATA+0x1000
INPUT=DATA+0x2000
OUTPUT=DATA+0x2100
INVT=DATA+0x2200
OUTVT=DATA+0x2300
READ=STOP+0x100
AT_END=STOP+0x104
WRITE=STOP+0x108

class AesPrimitive:
    def __init__(self):
        lib=ctypes.CDLL('/usr/lib/system/libcommonCrypto.dylib');self.lib=lib;self.fn=lib.CCCrypt
        self.fn.argtypes=[ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
        self.fn.restype=ctypes.c_int32;self.key=None;self.kb=None
        self.src=ctypes.create_string_buffer(16);self.out=ctypes.create_string_buffer(32);self.moved=ctypes.c_size_t()

    def set_key(self,key):assert len(key)==16;self.key=key;self.kb=ctypes.create_string_buffer(key,16)
    def decrypt(self,data):
        assert len(data)==16 and self.key is not None
        self.src.raw=data
        result=self.fn(1,0,2,self.kb,16,None,self.src,16,self.out,32,ctypes.byref(self.moved))
        assert result==0 and self.moved.value==16
        return self.out.raw[:16]

def sources():
    order=['libupdatercorecommon.so','libupdatertalk.so','libcryptfileinputupdaterapi.so']
    rows=[]
    for index,name in enumerate(order):
        source=next(r for r in ap_sources() if Path(r['path']).name==name)
        rows.append((0x10000000*(index+1),View(source['path'],source['sha256'])))
    ap=TASK/'ap-input-20261029'
    source=next(r for r in json.loads((ap/'additional-source-members.json').read_text()) if r['original_path']=='/lib/libupdatercommon.so')
    rows.append((0x40000000,View(ap/source['output'],source['sha256'])))
    return rows

class Guest(LoaderGuest):
    def __init__(self,views,cipher):
        super().__init__(views);self.pretty={name:label for base,v in views for name,label in v.names.items()}
        self.cipher=cipher;self.position=0;self.sink=bytearray();self.exception=None
        self.reads=0;self.end_checks=0;self.writes=0;self.aes_calls=0;self.events=[];self.sink_end_flags=[]
        self.aes=AesPrimitive();self.budget=12000000;self.allowed=[];self.allowed_pcs=set();self.entries={}
        self.entry_names={base+s['st_value']:v.names.get(s.name,s.name) for base,v in views for s in v.symbols if s['st_value'] and s['st_size'] and s['st_info']['type']=='STT_FUNC'}
        for base,v in views:
            for address,size in v.sizes.items():
                if any(t in v.labels.get(address,'') for t in ['DecryptorModule::','BaseModule::BaseModule','BaseModule::ThreadStatus::']):self.allowed.append((base+address,base+address+size))
        self.allowed += [(0x1000a0bc,0x1000a0c4),(0x200008c0,0x2000090c),(0x400095e4,0x40009630),(0x4000956c,0x40009574)]
        self.u.mem_write(INPUT,struct.pack('<Q',INVT));self.u.mem_write(INVT+0x30,struct.pack('<Q',0x400095e4));self.u.mem_write(INVT+0x40,struct.pack('<Q',READ))
        self.u.mem_write(INPUT+0x28,struct.pack('<Q',len(cipher)));self.u.mem_write(INPUT+0x30,b'\x01')
        self.u.mem_write(OUTPUT,struct.pack('<Q',OUTVT));self.u.mem_write(OUTVT+0x30,struct.pack('<Q',WRITE))
        talk=views[1][1]
        sym=next(s for s in talk.symbols if s.name=='decx');assert sym['st_size']==244
        self.key_context=0x20000000+sym['st_value']
        key=next(s for s in talk.symbols if s.name=='KeyArray');self.expected_key=0x20000000+key['st_value']

    def named(self,label):return next(a for name,a in self.definitions.items() if self.pretty.get(name)==label)

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<=self.budget
        if pc==STOP:u.emu_stop();return
        if pc==0x400095e4:self.end_checks+=1
        if pc in [READ,WRITE]:
            x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
            if pc==READ:
                assert x[0]==INPUT and x[1]==DEC+0xb0 and x[2]==1024
                n=min(x[2],len(self.cipher)-self.position);assert n>=0
                u.mem_write(x[1],self.cipher[self.position:self.position+n]);self.position+=n;self.reads+=1;self.ret(n)
                u.mem_write(INPUT+0x28,struct.pack('<Q',len(self.cipher)-self.position))
            else:
                assert x[0]==OUTPUT and x[1]==DEC+0xb4 and 0<x[2]<=1020 and x[3] in [0,1]
                self.sink.extend(u.mem_read(x[1],x[2]));self.writes+=1;self.sink_end_flags.append(x[3]);self.ret(x[2])
            return
        if pc in self.plt:
            raw=self.plt[pc]
            if raw in self.definitions:u.reg_write(R.UC_ARM64_REG_PC,self.definitions[raw]);return
            x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
            if raw.startswith('pthread_mutex_'):
                assert raw in ['pthread_mutex_init','pthread_mutex_lock','pthread_mutex_unlock']
                assert any(lo<=x[0]<hi for lo,hi in [(DATA,DATA+0x10000),(STACK,STACK+0x10000)])
                self.ret(0);return
            if raw=='memset':assert x[0]==DEC+0xb0 and x[1]==255 and x[2]==1024;u.mem_write(x[0],b'\xff'*1024);self.ret(x[0]);return
            if raw=='AES_set_decrypt_key':
                assert x[0]==self.expected_key and x[1]==128 and x[2]==self.key_context
                self.aes.set_key(bytes(u.mem_read(x[0],16)));self.events.append(dict(adapter='host AES-128 key setup',key_sha256=hashlib.sha256(self.aes.key).hexdigest(),source_wrapper='Dec_ScrambleInit',original_schedule_memory_emulated=False));self.ret(0);return
            if raw=='AES_decrypt':
                assert x[2]==self.key_context and STACK<=x[0]<STACK+0x10000 and STACK<=x[1]<STACK+0x10000
                u.mem_write(x[1],self.aes.decrypt(bytes(u.mem_read(x[0],16))));self.aes_calls+=1;self.ret(0);return
            if raw=='printf':self.ret(0);return
            if raw=='__cxa_allocate_exception':assert x[0]==16;self.ret(DATA+0x3000);return
            if raw=='__cxa_throw':
                self.exception=dict(code=hex(struct.unpack('<I',u.mem_read(x[0]+8,4))[0]),pc=hex(pc),native_unwind=False);u.emu_stop();return
            raise AssertionError(('unmodelled decryptor import',raw,hex(pc)))
        if pc not in self.allowed_pcs:
            assert any(lo<=pc<hi for lo,hi in self.allowed),('outside original decoder selection',hex(pc));self.allowed_pcs.add(pc)
        if pc in self.entry_names:
            name=self.entry_names[pc];self.entries[name]=self.entries.get(name,0)+1

    def run(self,entry,args):
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        for i,value in enumerate(args):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),value)
        before=self.steps;u.emu_start(entry,STOP+4,count=self.budget)
        if self.exception:assert u.reg_read(R.UC_ARM64_REG_PC)==int(self.exception['pc'],16)
        else:
            assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
            assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        return u.reg_read(R.UC_ARM64_REG_X0),self.steps-before

    def execute(self):
        self.run(self.named('Updater::MsDecryptorModule::MsDecryptorModule()'),[DEC])
        self.u.mem_write(DEC+0x48,struct.pack('<QQ',INPUT,OUTPUT))
        self.run(self.named('Updater::BaseModule::ThreadStatus::Run()'),[DEC+0x10])
        self.run(self.named('Updater::DecryptorModule::execute()'),[DEC])
        return dict(returned=self.exception is None,exception=self.exception,cipher_bytes=len(self.cipher),cipher_sha256=hashlib.sha256(self.cipher).hexdigest(),
                    consumed_cipher_bytes=self.position,trailing_cipher_bytes=len(self.cipher)-self.position,decoded_bytes=len(self.sink),decoded_sha256=hashlib.sha256(self.sink).hexdigest(),
                    input_read_calls=self.reads,input_end_checks=self.end_checks,output_write_calls=self.writes,output_end_flag_count=sum(self.sink_end_flags),last_output_end_flag=self.sink_end_flags[-1] if self.sink_end_flags else None,
                    host_aes_block_calls=self.aes_calls,host_adapters=self.events,original_function_entries=self.entries,total_instructions=self.steps)

def whole_fixture():
    project=TASK.parents[1];firm=project/'work/sony-firmware-20261024/fx3-7.02-decrypted.fdat'
    pin='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
    with firm.open('rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest()==pin;f.seek(0);head=bytearray(f.read(512));image=f.read(1253376)
    assert struct.unpack_from('<I',head,0x30)[0]==1253888 and struct.unpack_from('<I',head,0x34)[0]==807450624
    assert hashlib.sha256(image).hexdigest()=='62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa'
    tar=tar_stream();struct.pack_into('<I',head,0x34,len(tar));struct.pack_into('<I',head,8,zlib.crc32(head[12:]))
    return bytes(head)+image+tar,dict(original_plain_fdat_sha256=pin,modified_header_sha256=hashlib.sha256(head).hexdigest(),firmware_offset=1253888,declared_firmware_bytes=len(tar),unchanged_image_bytes=len(image),unchanged_image_sha256=hashlib.sha256(image).hexdigest(),tar_bytes=len(tar),tar_sha256=hashlib.sha256(tar).hexdigest(),source_header_changes=['0x8 CRC32','0x34 firmware/TAR length'])

def main():
    views=sources();talk=views[1][1];key=next(s for s in talk.symbols if s.name=='KeyArray');secret=talk.read(key['st_value'],16)
    payload,fixture=whole_fixture();raw=b''.join(pack(payload[i:i+1020],i+1020>=len(payload)) for i in range(0,len(payload),1020))
    cipher=crypt(raw,secret,ecb=True);g=Guest(views,cipher);whole=g.execute();whole['case']='whole_inert_legacy_stream'
    assert whole['returned'] and bytes(g.sink)==payload and whole['trailing_cipher_bytes']==0 and whole['last_output_end_flag']==1
    rows=[whole]
    a=b'A'*1020;b=b'B'*37
    good=pack(a,False)+pack(b,True)
    early=pack(a,True)+pack(b,True)
    missing=pack(a,False)+pack(b,False)
    bad=bytearray(pack(a,True));bad[0]^=1
    zero=bytearray(pack(b'Z',True));struct.pack_into('<H',zero,2,0x8000);struct.pack_into('<H',zero,0,sum(struct.unpack('<511H',zero[2:]))&0xffff)
    fixtures=[('two_valid_blocks',crypt(good,secret,ecb=True),None,a+b),('early_end_with_trailing_block',crypt(early,secret,ecb=True),None,a),
              ('missing_end_at_eof',crypt(missing,secret,ecb=True),'0x30002',None),('short_cipher_block',crypt(pack(a,True),secret,ecb=True)[:-1],'0x30002',None),
              ('bad_checksum',crypt(bytes(bad),secret,ecb=True),'0x30002',None),('zero_payload_size',crypt(bytes(zero),secret,ecb=True),'0x30002',None)]
    for name,data,error,expected in fixtures:
        guest=Guest(views,data);row=guest.execute();row['case']=name
        if error:assert row['exception']['code']==error and not row['returned']
        else:assert row['returned'] and bytes(guest.sink)==expected
        if name=='early_end_with_trailing_block':assert row['trailing_cipher_bytes']==1024
        rows.append(row)
    # The complete decoded bytes are passed unchanged to two bounded original
    # consumers in separate guest instances; their startup and I/O fixtures remain explicit.
    sys.path.insert(0,str(TASK/'body-load-20261029'))
    from assemble_body_guest import Guest as AssemblyGuest
    assembly=AssemblyGuest(views[0][1],io.BytesIO(bytes(g.sink)));assembly.prepare(bytes(g.sink[:512]));assembly.run(0x95a0,[DATA])
    assert bytes(assembly.sink)==payload[512:1253888] and assembly.position==1253888
    from controller_guest import Guest as ControllerGuest,sources as controller_sources
    controller=ControllerGuest(controller_sources(),bytes(g.sink[assembly.position:]));controller_row=controller.execute()
    assert controller_row['boundary']['operation']=='system_request_boundary'
    result=dict(sources=[dict(path=str(v.path),sha256=hashlib.sha256(v.raw).hexdigest()) for base,v in views],fixture=fixture,cases=rows,
                downstream=dict(decoded_bytes_handed_off_unchanged=True,assembly_image_bytes=len(assembly.sink),assembly_image_sha256=hashlib.sha256(assembly.sink).hexdigest(),plaintext_cursor_after_assembly=assembly.position,assembly_instructions=assembly.instructions,controller=controller_row),
                scope='Seven original MsDecryptor/core decryptor stream executions in RAM, including complete 1.26 MB inert legacy ciphertext. Original constructor/thread-running state/decrypt-loop/talk wrappers/checksum/length/end checks/output/termination execute. Input ReadData is a strict RAM adapter updating the declared remaining-byte counter; original current AP RingBuffer::IsEnd executes over that counter and an explicit producer-EOF=true fixture. Full RingBuffer producer/ReadData concurrency is not executed. AES key setup and AES-128-ECB block math are explicit Apple CommonCrypto adapters, not native Sony crypto or OpenSSL schedule emulation. Source key values remain memory-only. Whole output is byte-exact, then handed unchanged to original header/body-image assembly and TAR controller in separate guests, whose ring/filesystem/mutex/stat/initial-script-zero-result fixtures persist. Early end accepting trailing ciphertext is a local decoder observation, not a complete-container acceptance rule. No real manager initialization, actual input API/USB, signature admission, real stat, native loader/scripts, complete VENICE implementation, camera or firmware file output.')
    (HERE/'decrypt-stream-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),whole_cipher_bytes=len(cipher),whole_plain_bytes=len(payload),whole_cipher_blocks=len(cipher)//1024,whole_roundtrip=True,original_image_recovered=True,controller_reaches_request=True,early_end_leaves_unread_cipher=True,camera_actions=0)))

if __name__=='__main__':main()
