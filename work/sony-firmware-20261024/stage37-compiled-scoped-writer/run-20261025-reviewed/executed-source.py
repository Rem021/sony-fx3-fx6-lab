#!/usr/bin/env python3
"""Compile/load a standalone A64 data-writer prototype into Unicorn only.

This relocates OUR freestanding ET_REL object, never a camera firmware image or
Sony module. Actual camera hooks/ABI/lock domain/epochs/completion are unbound.
"""
from pathlib import Path
import argparse
import datetime
import io
import json
import struct
import subprocess
import sys
import traceback

from elftools.elf.elffile import ELFFile

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage36-private-preset-data-candidate'))
import private_preset as w
r,V=w.r,w.V
CODE,RODATA=0x13000000,0x13010000
CONTROL=r.ARENA+0x3a0000
MAGIC,SESSION,EPOCH=0x4658334733373031,0x1122334455667788,7
FIELDS=('magic','session','epoch','observed_epoch','owner','gate','phase','fault',
        'next_id','out_id','live','lock','data_restored')
FLAGS=['--target=aarch64-none-elf','-std=c11','-O2','-ffreestanding','-fno-builtin',
 '-fno-stack-protector','-fno-asynchronous-unwind-tables','-fno-unwind-tables',
 '-fno-vectorize','-fno-slp-vectorize','-mno-outline-atomics','-Wall','-Wextra','-Werror']


def object_image(raw):
    e=ELFFile(io.BytesIO(raw));assert e['e_type']=='ET_REL' and e['e_machine']=='EM_AARCH64'
    assert e.elfclass==64 and e.little_endian and e.num_segments()==0
    text=e.get_section_by_name('.text');ro=e.get_section_by_name('.rodata')
    assert text['sh_flags']==6 and ro['sh_flags']==2
    assert not any(s['sh_flags']&3==3 for s in e.iter_sections())
    code=bytearray(text.data());data=ro.data();assert 0<len(code)<=0x10000 and len(data)==256
    symtab=e.get_section_by_name('.symtab')
    assert not any(s.name and s['st_shndx']=='SHN_UNDEF' for s in symtab.iter_symbols())
    funcs=[s for s in symtab.iter_symbols() if s['st_info']['type']=='STT_FUNC']
    assert len(funcs)==1 and funcs[0].name=='fx3_candidate' and funcs[0]['st_value']==0
    assert funcs[0]['st_size']==len(code)
    indices={i:s.name for i,s in enumerate(e.iter_sections())}
    bases={i:CODE if name=='.text' else RODATA for i,name in indices.items() if name in ('.text','.rodata')}
    relocations=[]
    for section in e.iter_sections():
        if section['sh_type']!='SHT_RELA':continue
        assert indices[section['sh_info']]=='.text'
        symbols=e.get_section(section['sh_link'])
        for rel in section.iter_relocations():
            sym=symbols.get_symbol(rel['r_info_sym']);assert sym['st_shndx'] in bases
            S=bases[sym['st_shndx']]+sym['st_value']+rel['r_addend']
            off=rel['r_offset'];P=CODE+off;kind=rel['r_info_type']
            old=struct.unpack_from('<I',code,off)[0]
            if kind==275: # R_AARCH64_ADR_PREL_PG_HI21
                delta=((S&~4095)-(P&~4095))>>12
                assert -(1<<20)<=delta<(1<<20)
                bits=delta&0x1fffff
                new=(old&~((3<<29)|(0x7ffff<<5)))|((bits&3)<<29)|((bits>>2)<<5)
            elif kind==277: # R_AARCH64_ADD_ABS_LO12_NC
                new=(old&~(4095<<10))|((S&4095)<<10)
            else:raise AssertionError(('unsupported object relocation',kind))
            struct.pack_into('<I',code,off,new)
            relocations.append({'offset':hex(off),'type':kind,'target':hex(S),
              'old_word':hex(old),'relocated_word':hex(new)})
    assert len(relocations)==2
    return bytes(code),data,relocations


class Guest(w.CandidateGuest):
    def __init__(self,blob,code,ro):
        super().__init__(blob)
        self.uc.mem_map(CODE,0x10000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_map(RODATA,4096,r.unicorn.UC_PROT_READ)
        self.uc.mem_write(CODE,code);self.uc.mem_write(RODATA,ro)
        self.ranges.append((CODE,CODE+len(code)))

    def invoke(self,label,op,ticket=0,address=0,epoch=EPOCH,session=SESSION):
        w.f.reset_trace(self);self.regs(x0=CONTROL,x1=op,x2=ticket,x3=address,x4=epoch,x5=session)
        self.uc.emu_start(CODE,0,count=20000,timeout=1000000)
        assert self.reason=='returned',self.reason
        assert all(p==r.STOP or CODE<=p<CODE+0x10000 for p in self.pcs)
        permitted=((CONTROL,296),(w.COPY,256),(w.A+0xe000,8),(r.STACK,r.STACK_SIZE))
        assert all(any(lo<=int(z['address'],16) and int(z['address'],16)+z['size']<=lo+size
                       for lo,size in permitted) for z in self.writes)
        return {'label':label,'prototype_op':op,'ticket_input':ticket,'address_input':hex(address),
          'status':self.uc.reg_read(r.reg.UC_ARM64_REG_X0),
          'reason':self.reason,'pcs':[hex(p) for p in self.pcs],'writes':self.writes,
          'control_after':control(self),'native_output_or_diagnostic_adapters':False}


def control(m):
    raw=m.read(CONTROL,296);out=dict(zip(FIELDS,struct.unpack_from('<13Q',raw)))
    out['slots']=[dict(zip(('id','kind','address'),struct.unpack_from('<3Q',raw,104+i*24))) for i in range(8)]
    return out


def set_field(m,name,value):m.uc.mem_write(CONTROL+FIELDS.index(name)*8,r.p64(value))


def setup(blob,code,ro,descriptor,both=False):
    m=Guest(blob,code,ro);m.uc.mem_write(w.DESC,descriptor);original=[]
    for owner,label in ((w.A,'A'),(w.B,'B')) if both else ((w.A,'A'),):
        original.extend((w.prepare(m,owner,label+' original copy prefix'),w.selection(m,owner,label+' original selection')))
    values=[MAGIC,SESSION,EPOCH,EPOCH,w.A,1,0,0,1,0,0,0,0]
    m.uc.mem_write(CONTROL,struct.pack('<13Q',*values)+bytes(192))
    return m,original


def expect(m,events,label,op,status,**args):
    result=m.invoke(label,op,**args);assert result['status']==status,(label,result['status'],status)
    events.append(result);return result


def positive(blob,code,ro,descriptor):
    m,original=setup(blob,code,ro,descriptor,True);events=[]
    untouched_B=m.read(w.B,0xf000);untouched_A_descriptor=m.read(w.A+0xe110,0x88)
    a=expect(m,events,'native ENTER publishes private copy and producer lease',0,0)
    producer=a['control_after']['out_id'];assert producer==1
    assert int.from_bytes(m.read(w.A+0xe000,8),'little')==w.COPY
    source=blob[0x3c5798:0x3c5898];copy=m.read(w.COPY,256)
    assert [i for i,(u,v) in enumerate(zip(source,copy)) if u!=v]==[0xb0,0xb1,0xb2]
    # Native byte-copy touches +b0 once before the final 32-bit replacement.
    # Verify the entire 256-byte copy and ordered coefficient/publication stores.
    copies=[z for z in a['writes'] if w.COPY<=int(z['address'],16)<w.COPY+256 and z['size']==1]
    assert [int(z['address'],16) for z in copies]==list(range(w.COPY,w.COPY+256))
    assert all(CODE<=int(z['pc'],16)<CODE+len(code) for z in copies)
    relevant=[z for z in a['writes'] if int(z['address'],16) in (w.A+0xe000,w.COPY+0xb0)]
    assert [(int(z['address'],16),z['size']) for z in relevant]==[(w.COPY+0xb0,1),(w.COPY+0xb0,4),(w.A+0xe000,8)]
    assert all(CODE<=int(z['pc'],16)<CODE+len(code) for z in relevant)
    original.extend((w.default_query(m,w.A,'native-writer A decode',16000000),
      w.pack(m,w.A,w.PACKETS[3],'native-writer A original pack',16000000),
      w.default_query(m,w.B,'B after native-writer A',24498176),
      w.pack(m,w.B,w.PACKETS[1],'B original pack unchanged',24498176)))
    old=m.read(w.PACKETS[3],0x38)
    expect(m,events,'close new entry while producer remains',4,0)
    expect(m,events,'new ENTER rejected after close',0,3)
    expect(m,events,'restore blocked by producer',5,10)
    packet_event=expect(m,events,'prior producer registers packet after close',1,0,ticket=producer,address=w.PACKETS[3])
    packet=packet_event['control_after']['out_id'];assert packet==2
    expect(m,events,'finish producer leaves packet visible',2,0,ticket=producer)
    assert control(m)['live']==1
    expect(m,events,'restore blocked by retained packet',5,10)
    # This is an explicitly simulated trusted completion notification, not a
    # real consumer/HAL callback. Real provenance binding remains missing.
    expect(m,events,'simulated consumer completion releases packet',3,0,ticket=packet,address=w.PACKETS[3])
    expect(m,events,'data-only restore after declared dependencies finish',5,0)
    assert control(m)['data_restored']==1 and control(m)['gate']==0
    assert int.from_bytes(m.read(w.A+0xe000,8),'little')==w.PRESET
    original.extend((w.default_query(m,w.A,'A after prototype data restoration',24498176),
      w.pack(m,w.A,w.PACKETS[5],'A newly packed default',24498176)))
    assert m.read(w.PACKETS[3],0x38)==old and m.read(w.PRESET,256)==source
    assert m.read(w.COPY,256)==copy
    assert m.read(w.B,0xf000)==untouched_B
    assert m.read(w.A+0xe110,0x88)==untouched_A_descriptor
    return {'native_prototype_events':events,'original_firmware_fragments':original,
      'private_copy_created_by_compiled_code':True,'old_prepared_bytes_remain_after_declared_completion':True,
      'second_owner_entire_0xf000_bytes_and_A_descriptor_unchanged':True,
      'completion_notification':'Explicit simulated caller notification, no actual consumer/HAL provenance.',
      'data_restored_only_not_code_reclaim_or_physical_restore':True}


def negatives(blob,code,ro,descriptor):
    cases=[]
    for kind in ('profile','epoch','fingerprint','double_finish','capacity','wrong_packet','lock','foreign_pointer','session','sequence'):
        image=blob
        if kind=='fingerprint':
            image=bytearray(blob);image[0x3c5798+6]^=1;image=bytes(image)
        m,original=setup(image,code,ro,descriptor);events=[]
        if kind=='profile':
            w.put32(m,w.A+0xe148,4);expect(m,events,'FH descriptor ineligible',0,5)
        elif kind=='epoch':
            set_field(m,'observed_epoch',8);expect(m,events,'changed fixture epoch',0,4)
        elif kind=='fingerprint':expect(m,events,'wrong guest image record pin',0,6)
        elif kind=='double_finish':
            expect(m,events,'enter',0,0);expect(m,events,'finish producer once',2,0,ticket=1)
            expect(m,events,'duplicate finish faults closed',2,8,ticket=1)
            expect(m,events,'sticky fault denies data restore',5,11)
        elif kind=='capacity':
            for i in range(8):expect(m,events,'reserve producer'+str(i+1),0,0)
            expect(m,events,'ninth entry faults closed',0,7)
            for i in range(8):expect(m,events,'finish old producer'+str(i+1),2,0,ticket=i+1)
            expect(m,events,'capacity fault persists after empty',5,11)
            assert control(m)['live']==0 and control(m)['fault']==7
        elif kind=='wrong_packet':
            expect(m,events,'enter',0,0)
            expect(m,events,'register packet',1,0,ticket=1,address=w.PACKETS[0])
            expect(m,events,'wrong completion address faults closed',3,8,ticket=2,address=w.PACKETS[1])
            assert control(m)['live']==2
        elif kind=='lock':
            set_field(m,'lock',1);expect(m,events,'preheld native lock returns busy',0,2)
            assert control(m)['lock']==1
        elif kind=='foreign_pointer':
            m.uc.mem_write(w.A+0xe000,r.p64(V+0x3c8498))
            expect(m,events,'foreign selected record pointer',0,13)
        elif kind=='session':expect(m,events,'wrong prototype session',0,1,session=SESSION+1)
        elif kind=='sequence':
            set_field(m,'next_id',(1<<64)-1);expect(m,events,'id wrap forbidden',0,12)
        if kind in ('profile','epoch','fingerprint','lock','session','sequence'):
            assert int.from_bytes(m.read(w.A+0xe000,8),'little')==w.PRESET
            assert m.read(w.COPY,256)==bytes(256)
        cases.append({'control':kind,'native_prototype_events':events,
          'original_setup_fragments':original,'final_control':control(m),
          'scope':'Sequential guest API control; callbacks/epoch/owner/state are fixtures. Not a real camera race or recovery test.'})
    return cases


def run(out):
    prior=w.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='8a5c35564bab422d698d3d75baff647dc59b655a81cb907c991cbfeb66a3096a'
    manifest=json.loads(prior.read_text());assert all(r.im.sha((ROOT/e['path']).read_bytes())==e['sha256'] for e in manifest['files'])
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    # Recompile into this new output directory, preserving the initial object.
    cmd=['/usr/bin/clang',*FLAGS,'-c',str(STAGE/'scoped_writer.c'),'-o',str(out/'scoped_writer.a64.o')]
    result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode==0,result.stderr
    raw=(out/'scoped_writer.a64.o').read_bytes()
    assert raw==(STAGE/'scoped_writer.a64.o').read_bytes()
    code,ro,relocs=object_image(raw);assert ro==blob[0x3c5798:0x3c5898]
    md=r.capstone.Cs(r.capstone.CS_ARCH_ARM64,r.capstone.CS_MODE_ARM)
    ins=list(md.disasm(code,CODE));assert sum(i.size for i in ins)==len(code)
    atomic=[{'offset':hex(i.address-CODE),'asm':i.mnemonic+' '+i.op_str} for i in ins if i.mnemonic in ('ldaxr','stxr','stlr','ldar','clrex')]
    assert {i['asm'].split()[0] for i in atomic}>={'ldaxr','stxr','stlr','ldar'}
    old=json.loads((w.v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())
    descriptor=bytes.fromhex(old['artificial_quality24_descriptor']['descriptor_hex'])
    positive_case=positive(blob,code,ro,descriptor);negative_cases=negatives(blob,code,ro,descriptor)
    proto_calls=len(positive_case['native_prototype_events'])+sum(len(c['native_prototype_events']) for c in negative_cases)
    original_calls=len(positive_case['original_firmware_fragments'])+sum(len(c['original_setup_fragments']) for c in negative_cases)
    proof={'status':'PASS_COMPILED_A64_GUEST_WRITER_AND_SEQUENTIAL_LEASE_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'positive':positive_case,'negative_cases':negative_cases,
      'compiled_prototype':{'type':'Freestanding AArch64 ELF64 ET_REL, not Sony-loadable module',
       'compiler_version':subprocess.check_output(['/usr/bin/clang','--version'],text=True),
       'compile_command':cmd,'warnings':result.stderr,'object_sha256':r.im.sha(raw),
       'relocated_text_sha256':r.im.sha(code),'rodata_sha256':r.im.sha(ro),
       'relocations':relocs,'atomic_instructions':atomic,
       'relocated_instructions':[{'offset':hex(i.address-CODE),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in ins]},
      'scope':'Our compiled guest-only writer controls copy/publish and8 producer/packet leases under native atomics. Original packing sees16M. Sequential fixtures do not bind Sony hooks/ABI/current epoch/completion, all consumers, weak-memory or code reclamation.',
      'native_prototype_calls':proto_calls,'original_firmware_fragments':original_calls,
      'real_camera_hook_ABI_epoch_completion_or_all_consumer_binding':False,
      'camera_or_remote_access_attempted':False,'camera_loadable_module_or_firmware_exported':False,
      'native_output_or_diagnostic_adapters':False,'actual_hardware_or_restore_verified':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'native_prototype_calls':proto_calls,
      'original_firmware_fragments':original_calls,'negative_controls':len(negative_cases),
      'compiled_instructions':len(ins),'target_generated_by_native_prototype_and_original_packing':16000000,
      'producer_and_packet_leases_block_data_restore':True,
      'real_camera_hooks_or_multicore_or_code_reclamation_verified':False,
      'actual_hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'compiled-writer-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'C_sha256':r.im.sha((STAGE/'scoped_writer.c').read_bytes()),
      'expected_include_sha256':r.im.sha((STAGE/'expected_ff.inc').read_bytes()),
      'stage36_helper_sha256':r.im.sha(Path(w.__file__).read_bytes()),'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'image_sha256':r.im.sha(blob),'previous_manifest_sha256':r.im.sha(prior.read_bytes()),
      'object_sha256':r.im.sha(raw),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'compiled-writer-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as h:h.write(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
