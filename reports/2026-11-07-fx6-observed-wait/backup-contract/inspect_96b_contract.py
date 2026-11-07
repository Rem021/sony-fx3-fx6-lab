#!/usr/bin/env python3
"""Read-only static binding for the observer's 0x92a208fc notification."""
from io import BytesIO
from pathlib import Path
import hashlib
import json
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

REPO=Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab')
DONOR=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor')
ARCHIVE=REPO/'work/fx6-observer-integration-20261107/guest-observer-only295.cpio'
RUN=REPO/'work/fx6-observer-integration-20261107/runs/observer-004ab971f4'
def sha(b): return hashlib.sha256(b).hexdigest()
def member(name):
    with ARCHIVE.open('rb') as stream:
        while True:
            header=stream.read(110)
            if header[:6] not in (b'070701',b'070702'):raise ValueError('newc magic')
            values=[int(header[6+i*8:14+i*8],16) for i in range(13)]
            size,namesize=values[6],values[11]
            item=stream.read(namesize).rstrip(b'\0').decode()
            stream.seek((-110-namesize)%4,1)
            if item=='TRAILER!!!':raise KeyError(name)
            if item==name:return stream.read(size)
            stream.seek(size+(-size)%4,1)
def text_model(blob):
    elf=ELFFile(BytesIO(blob));section=elf.get_section_by_name('.text')
    syms=list(elf.get_section_by_name('.symtab').iter_symbols())
    reloc=elf.get_section_by_name('.rela.text')
    calls={r['r_offset']:syms[r['r_info_sym']].name for r in reloc.iter_relocations()}
    return elf,section.data(),calls
def one(text,address):
    item=next(Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(text[address:address+4],address))
    return f'{item.mnemonic} {item.op_str}'.rstrip()
def require(text,expected):
    result={}
    for address,value in expected.items():
        actual=one(text,address);assert actual==value,(hex(address),actual,value)
        result[hex(address)]=actual
    return result

def main():
    archive_sha=hashlib.file_digest(ARCHIVE.open('rb'),'sha256').hexdigest()
    assert archive_sha=='d02c7909458dcf8dff73fdf426953d07034cb386f8c8bd0bbd40a9440d32569e'
    runtime=member('usr/kmod/upm.ko');kernel_osal=member('usr/kmod/osal_uipc.ko')
    original=(DONOR/'nflasha15-files/kmod/upm.ko').read_bytes()
    assert sha(runtime)=='5be2aa0b6d6c0a31bb7802400fcd688a980583a08e945245adad7700b9882994'
    assert sha(original)=='34d5bca76b6750f2af36f34404c305aaef71aeabab1d3ae52a9e00b65c6b7970'
    assert sha(kernel_osal)=='6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38'
    _,runtime_text,runtime_calls=text_model(runtime)
    _,original_text,original_calls=text_model(original)
    _,osal_text,_=text_model(kernel_osal)
    runtime_insns=require(runtime_text,{
        0x63e0:'mov w2, #0x60',0x63e4:'movk w0, #0x92a2, lsl #16',
        0x6400:'stp wzr, w23, [x1]',0x640c:'str x2, [x1, #8]',0x6414:'str w2, [x1, #0x10]',
        0x65a8:'mov w2, #0x60',0x65ac:'movk w0, #0x92a2, lsl #16',
        0x207b8:'mov w2, #0x60',0x207d0:'mov w2, #4',0x207dc:'stp wzr, w2, [x1]',
        0x207e8:'str x2, [x1, #8]',0x207f0:'str w2, [x1, #0x10]',
        0x23288:'mov w2, #0x60',0x231f4:'mov w24, #4',
    })
    original_insns=require(original_text,{
        0x63b8:'mov w2, #0x28',0x63bc:'movk w0, #0x92a2, lsl #16',
        0x63d8:'stp wzr, w23, [x1]',0x63e4:'str x2, [x1, #8]',0x63ec:'str w2, [x1, #0x10]',
        0x6580:'mov w2, #0x28',0x6584:'movk w0, #0x92a2, lsl #16',
        0x1e194:'mov w2, #0x28',0x1e1a8:'mov w2, #4',
    })
    # Verify a named real FX6 userspace consumer of the same companion protocol.
    usb_path=DONOR/'nflasha15-files/lib/libUsbControl.so';usb_blob=usb_path.read_bytes()
    assert sha(usb_blob)=='951d1da8a4366dc8cf7bf475181344ea487e661869701218a2343e9c9ecf1483'
    usb=ELFFile(BytesIO(usb_blob));usb_section=usb.get_section_by_name('.text')
    usb_symbols=usb.get_section_by_name('.dynsym')
    for name,address in {'_ZN3UFW10DfsWrapper2okEv':0x12fac,'_ZN3UFW10DfsWrapper2ngEv':0x130a4}.items():
        assert usb_symbols.get_symbol_by_name(name)[0]['st_value']==address
    def usb_one(address):
        off=address-usb_section['sh_addr']
        return one(usb_section.data(),off)
    assert usb_one(0x12e48)=='mov w2, #0x28'
    # Relative disassembly address changes branch text; verify encoded BL target.
    for address,target in {0x13044:0x12e40,0x13160:0x12e40}.items():
        off=address-usb_section['sh_addr'];word=struct.unpack_from('<I',usb_section.data(),off)[0]
        imm=word&0x3ffffff
        if imm&0x2000000:imm-=0x4000000
        assert word>>26==0b100101 and address+imm*4==target
    osal_insns=require(osal_text,{
        0x3370:'mov w4, #0xa5a5',0x3374:'add x3, x0, #0x18',
        0x3378:'movk w4, #0xa5a5, lsl #16',0x338c:'str w4, [x0, #0xc]',
        0x3394:'str x3, [x19]',0x5e54:'ldur w0, [x0, #-8]',0x5e70:'ldur w0, [x0, #-0xc]',
    })
    call_checks={}
    for address,name in {0x63ec:'osal_valloc_msg_wait',0x641c:'osal_snd_msg',
        0x65b4:'osal_valloc_msg_wait',0x65e4:'osal_snd_msg',
        0x20778:'osal_snd_sync_msg',0x207c4:'osal_valloc_msg_wait',0x207f8:'osal_snd_msg',
        0x2321c:'osal_snd_sync_msg',0x23294:'osal_valloc_msg_wait',0x232c4:'osal_snd_msg'}.items():
        assert runtime_calls[address]==name
        call_checks[hex(address)]=name
    for address,name in {0x63c4:'osal_valloc_msg_wait',0x63f4:'osal_snd_msg',
        0x658c:'osal_valloc_msg_wait',0x65bc:'osal_snd_msg'}.items():assert original_calls[address]==name
    serial=RUN/'serial.log';data=serial.read_bytes();lines=data.decode(errors='replace').splitlines()
    logs=[{'line':index+1,'text':line} for index,line in enumerate(lines) if 'destination=0x92a208fc' in line]
    decoded=[]
    for item in logs:
        if ' raw=' not in item['text']:continue
        raw=bytes.fromhex(item['text'].split(' raw=')[1].split()[0])
        decoded.append({'line':item['line'],'captured_bytes':len(raw),
            'u32_words':[hex(x) for x in struct.unpack('<'+'I'*(len(raw)//4),raw)],
            'body_0_19_contract':'u32 discriminator=0; u32 notification kind; 12-byte copied parameter block',
            'bytes_20_and_later':'not initialized by identified producer stores; no pointer-array type proof'})
    result={'status':'PASS','scope':'read-only source and original ELF plus frozen observer artifacts',
        'archive':{'path':str(ARCHIVE),'sha256':archive_sha},
        'runtime_upm':{'member':'usr/kmod/upm.ko','bytes':len(runtime),'sha256':sha(runtime),
            'text_instruction_checks':runtime_insns,'relocation_call_checks':call_checks},
        'actual_fx6_upm':{'path':str(DONOR/'nflasha15-files/kmod/upm.ko'),'bytes':len(original),
            'sha256':sha(original),'text_instruction_checks':original_insns},
        'runtime_osal':{'member':'usr/kmod/osal_uipc.ko','bytes':len(kernel_osal),'sha256':sha(kernel_osal),
            'text_instruction_checks':osal_insns,'source_initialization':'0xa5a5a5a5 at allocation header+12 = payload-12'},
        'actual_fx6_userspace':{'path':str(usb_path),'sha256':sha(usb_blob),
            'named_callers':{'UFW::DfsWrapper::ok()':'0x12fac -> 0x13044 -> 0x12e40',
                'UFW::DfsWrapper::ng()':'0x130a4 -> 0x13160 -> 0x12e40'},
            'allocation_bytes':40,'asynchronous_destination':'0x92a208fc'},
        'observer_serial':{'path':str(serial),'bytes':len(data),'sha256':sha(data),'logs':logs,'decoded':decoded},
        'findings':[
            'Runtime upm allocates 96B for this destination; actual FX6 donor upm allocates 40B.',
            'Both producers write exactly 20B before asynchronous osal_snd_msg.',
            '96B length is compatible with runtime kernel UPM, not evidence of 40B widening corruption.',
            '0xa5a5a5a5 is explicit allocator source initialization, not a valid reply queue.',
            'Exact notification caller/TID is not in frozen log; multiple UPM producers match.',
            'No synchronous reply edge for this destination is proved; earlier local sync is 0x80920901.',
            'No VM, shim, donor, Git mutation performed.'
        ]}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
