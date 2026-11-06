#!/usr/bin/env python3
"""Pinned original MIPS VCD codec-config validation, not a VCD/hardware boot.

CPU uses normal Unicorn MIPS kseg address translation. Image is mapped at
physical0 and executes at kseg0+offset. Original config predicates execute and
return with no output, service, PC, delay-slot or return-value adapters.
The full enc-start checker is only routed to, not run past its entry.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback
import unicorn as u
from unicorn import mips_const as reg
import capstone as cs

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage48-codec-initialization'))
import codec_initialization as c
im=c.im
IMAGE_VA=0x80000000
INPUT_PA,INPUT=0x01000000,0x81000000
STACK_PA,STACK,SP=0x02000000,0x82000000,0x82008000
STOP_PA,STOP=0x03000000,0x83000000
CODEC_CHECK=0x1a8594
COMMON_CHECK=0x1a8648
ROUTER=0x19118c
PRIOR_SHA='3a76d3582755478d21485cdf4e32bd4da6a6d0858c168e9aaf412b224a32f980'
VCD_PATH=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin'


def mips_dump(blob,lo,hi):
    md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
    out=[{'offset':hex(i.address-IMAGE_VA),'va':hex(i.address),'bytes':i.bytes.hex(),
      'asm':i.mnemonic+' '+i.op_str} for i in md.disasm(blob[lo:hi],IMAGE_VA+lo)]
    assert sum(len(bytes.fromhex(i['bytes'])) for i in out)==hi-lo
    return out


class Guest:
    def __init__(self,blob,payload):
        self.blob=blob;self.payload=payload;self.pcs=[];self.reads=[];self.writes=[];self.reason=None
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.uc.mem_map(0,(len(blob)+4095)&~4095,u.UC_PROT_READ|u.UC_PROT_EXEC)
        self.uc.mem_write(0,blob)
        self.uc.mem_map(INPUT_PA,0x10000,u.UC_PROT_READ)
        self.uc.mem_write(INPUT_PA,payload)
        self.uc.mem_map(STACK_PA,0x10000,u.UC_PROT_READ|u.UC_PROT_WRITE)
        self.uc.mem_write(STACK_PA,bytes([0xd7])*0x10000)
        self.uc.mem_map(STOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_EXEC)
        self.uc.reg_write(reg.UC_MIPS_REG_SP,SP)
        self.uc.reg_write(reg.UC_MIPS_REG_RA,STOP)
        self.uc.reg_write(reg.UC_MIPS_REG_S0,0x12121212)
        self.uc.reg_write(reg.UC_MIPS_REG_A0,INPUT)
        self.uc.reg_write(reg.UC_MIPS_REG_A1,INPUT)
        self.uc.hook_add(u.UC_HOOK_CODE,self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_READ,self.load)
        self.uc.hook_add(u.UC_HOOK_MEM_WRITE,self.store)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID,self.invalid)

    def stop(self,reason):self.reason=reason;self.uc.emu_stop()

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==STOP:return self.stop('returned')
        off=pc-IMAGE_VA
        boundaries={0x1a3f00:'enc_start_checker_entry_before_runtime_globals',
          0x1a4968:'next_command_checker_entry',0x192554:'default_noop_checker_entry',
          0xae50:'before_original_assertion'}
        if off in boundaries:return self.stop('boundary: '+boundaries[off])
        if not any(a<=off and off+size<=b for a,b in ((0x1a8594,0x1a8c10),(0x19118c,0x191200))):
            return self.stop('unapproved original execution '+hex(pc))
        raw=bytes(uc.mem_read(off,size));assert raw==self.blob[off:off+size]
        ins=next(self.md.disasm(raw,pc),None)
        if ins is None or ins.mnemonic in {'syscall','break','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'}:
            return self.stop('unapproved original instruction '+hex(pc))

    def load(self,uc,access,address,size,value,user):
        self.reads.append({'pc':hex(uc.reg_read(reg.UC_MIPS_REG_PC)),'address':hex(address),'size':size})
        assert any(a<=address and address+size<=a+n for a,n in (
          (IMAGE_VA,len(self.blob)),(INPUT,len(self.payload)),(STACK,0x10000)))

    def store(self,uc,access,address,size,value,user):
        assert STACK<=address and address+size<=STACK+0x10000
        self.writes.append({'pc':hex(uc.reg_read(reg.UC_MIPS_REG_PC)),'address':hex(address),'size':size})

    def invalid(self,uc,access,address,size,value,user):
        self.stop('invalid guest memory '+hex(address));return False

    def run(self,label,start=CODEC_CHECK):
        self.uc.emu_start(IMAGE_VA+start,0,count=20000,timeout=1000000)
        assert self.reason is not None,'bounded CPU limit without expected boundary'
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(INPUT_PA,len(self.payload)))==self.payload
        if self.reason=='returned':
            assert self.uc.reg_read(reg.UC_MIPS_REG_SP)==SP
            assert self.uc.reg_read(reg.UC_MIPS_REG_S0)==0x12121212
        read_bytes=set()
        for e in self.reads:
            at=int(e['address'],16)
            read_bytes.update(range(max(at,INPUT)-INPUT,min(at+e['size'],INPUT+len(self.payload))-INPUT))
        return {'label':label,'start_offset':hex(start),'reason':self.reason,
          'stop_pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
          'native_v0':hex(self.uc.reg_read(reg.UC_MIPS_REG_V0)),
          'SP_after':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
          'input_hex':self.payload.hex(),'input_sha256':im.sha(self.payload),
          'pcs':[hex(pc) for pc in self.pcs],'reads':self.reads,'writes':self.writes,
          'input_byte_offsets_read':[hex(i) for i in sorted(read_bytes)],
          'read_stage48_unwritten_offsets':[hex(i) for i in sorted(read_bytes&set(c.EXPECTED_UNWRITTEN))],
          'original_code_and_input_unchanged':True,'native_output_PC_or_return_adapter':False}


def static_evidence(avcam,vcd,kernel,module):
    assert im.cstring(avcam,0x44fcc7)=='/usr/codec/vcd_firmware_imola2.bin'
    pathrefs=im.adrp_refs(avcam,{0x44fcc7:'imola2 VCD firmware pathname'})
    assert len(pathrefs)==1 and pathrefs[0]['adrp_offset']=='0x2186cc'
    assert struct.unpack_from('<I',vcd,0x24654c+0x1e*4)[0]==IMAGE_VA+0x1a3f00
    assert im.cstring(vcd,0x23a8e8).endswith('imola_api_parameter_check.c')
    assert 'EncConfigAddr' in im.cstring(vcd,0x23a9c0)
    assert struct.unpack_from('<I',vcd,0x1a42b8)[0]==0x0c000000|((IMAGE_VA+CODEC_CHECK)>>2&0x3ffffff)
    regions=[('original command checker router',ROUTER,0x191200),
      ('enc-start checker header',0x1a3f00,0x1a3fd0),
      ('448-byte range/cache and codec-config checker call',0x1a414c,0x1a42cc),
      ('config checker and codec dispatcher',CODEC_CHECK,0x1a8648),
      ('common config checker',COMMON_CHECK,0x1a875c),
      ('HEVC config checker',0x1a875c,0x1a8a08),
      ('VUI prefix checker',0x1a8bd8,0x1a8c10),
      ('assertion string reference',0x1a46a4,0x1a46c4)]
    exports=[]
    for name,entry,off in (('arch_phys_to_noncache',0x577de8,0x31b6b0),('arch_va_to_phys',0x577e48,0x31b938)):
        value,ptr=struct.unpack_from('<QQ',kernel,entry)
        assert value==c.n.K+off and im.cstring(kernel,ptr-c.n.K)==name
        exports.append({'name':name,'export_entry':hex(entry),'file_offset':hex(off),'value':hex(value),
          'instructions':im.dump(kernel,off,off+0x60,c.n.K),
          'scope':'Static binding only; real DAIF/AT/PAR page translation unexecuted and no substitute return.'})
    elf=c.n.ELFFile(c.n.io.BytesIO(module));syms=elf.get_section_by_name('.symtab')
    imports=[]
    for rel in elf.get_section_by_name('.rela.init.data').iter_relocations():
        if rel['r_offset'] in (0x5d8,0x5e8):
            imports.append({'LIRO_init_data_offset':hex(rel['r_offset']),
              'avcam_CAPI_offset':hex(rel['r_offset']+0x48),'name':syms.get_symbol(rel['r_info_sym']).name})
    return {'VCD_version':im.cstring(vcd,0x10),'VCD_bytes':len(vcd),'VCD_sha256':im.sha(vcd),
      'static_address_model':'MIPS32 little endian at kseg0 0x80000000 plus file offset, corroborated by original string references, JAL targets and dispatch pointers; no live boot address observation.',
      'avcam_path_references':pathrefs,
      'avcam_path_getter':im.dump(avcam,0x2186c8,0x2186dc,c.V),
      'command_0x1e_dispatch_pointer':{'table_offset':'0x24654c','entry_offset':'0x2465c4','value':hex(IMAGE_VA+0x1a3f00)},
      'checker_source_string':{'offset':'0x23a8e8','text':im.cstring(vcd,0x23a8e8)},
      'EncConfigAddr_assertion':{'offset':'0x23a9c0','text':im.cstring(vcd,0x23a9c0)},
      'original_MIPS_regions':[{'name':name,'instructions':mips_dump(vcd,a,z)} for name,a,z in regions],
      'avcam_pointer_command_builder':im.dump(avcam,0x26c9b8,0x26ca00,c.V),
      'avcam_notification_register_write':im.dump(avcam,0x27470c,0x2747b0,c.V),
      'pointer_imports':imports,'kernel_pointer_export_anchors':exports,
      'actual_VCD_boot_shared_RAM_cache_notification_response_or_hardware_verified':False}


def run(out):
    prior=c.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    vcd=VCD_PATH.read_bytes();assert im.sha(vcd)==im.PINS[str(VCD_PATH.relative_to(BASE))]
    avcam=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(avcam)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    kernel=(c.n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    module=(c.n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    static=static_evidence(avcam,vcd,kernel,module)
    old=json.loads((c.STAGE/'run-20261025/codec-initialization-results.json').read_text())
    positives=[]
    for z in old['cases']:
        payload=bytes.fromhex(z['payload_hex'])
        positives.append(Guest(vcd,payload).run(z['label']))
    payload=bytes.fromhex(old['cases'][1]['payload_hex'])
    mutations=[]
    for at in c.EXPECTED_UNWRITTEN:
        data=bytearray(payload);data[at]=0xff
        event=Guest(vcd,bytes(data)).run('single unwritten byte '+hex(at)+' set to FF')
        event['mutation_offset']=hex(at);mutations.append(event)
    all_ff=bytearray(payload)
    for at in c.EXPECTED_UNWRITTEN:all_ff[at]=0xff
    all_ff_case=Guest(vcd,bytes(all_ff)).run('all52 unwritten bytes set to FF')
    negatives=[]
    for label,at,val,expected in (('invalid codec',0,3,0x3001),('invalid common flag',1,2,0x3002),
      ('invalid HEVC field+1e',0x1e,3,0x3044),('invalid VUI flag',0x64,2,0x30c1)):
        data=bytearray(payload);data[at]=val
        event=Guest(vcd,bytes(data)).run(label);event['expected_native_v0']=hex(expected)
        assert event['reason']=='returned' and int(event['native_v0'],16)==expected
        negatives.append(event)
    common_controls=[]
    for value in (0,0xa5):
        data=bytearray(payload);data[0]=1;data[0xe]=value;data[0xf]=0
        event=Guest(vcd,bytes(data)).run('common-only codec1 field+e='+hex(value),COMMON_CHECK)
        assert int(event['native_v0'],16)==(0 if value==0 else 0x3007)
        common_controls.append(event)
    routes=[]
    for cmd,expected in ((0x1e,'enc_start_checker_entry_before_runtime_globals'),
      (0x1f,'next_command_checker_entry'),(0x4b,'before_original_assertion')):
        packet=bytearray(0x38);packet[1]=cmd
        event=Guest(vcd,bytes(packet)).run('original command router '+hex(cmd),ROUTER)
        assert event['reason']=='boundary: '+expected;routes.append(event)
    all_events=[*positives,*mutations,all_ff_case,*negatives,*common_controls,*routes]
    pure=[*positives,*mutations,all_ff_case]
    for event in pure:assert event['reason']=='returned'
    reads=set(int(x,16) for e in positives for x in e['input_byte_offsets_read'])
    proof={'status':'TRACED_ORIGINAL_VCD_CODEC_CONFIG_CHECKER_AND_COMMAND_ROUTE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'static_evidence':static,
      'original_functions_or_router_fragments':len(all_events),'positive_cases':positives,
      'single_byte_mutations':mutations,'all52_FF_case':all_ff_case,'negative_controls':negatives,
      'different_codec_common_controls':common_controls,'command_routes':routes,
      'allfour_original_codec_configs_return_zero':all(int(e['native_v0'],16)==0 for e in positives),
      'all52_single_and_combined_FF_return_zero':all(int(e['native_v0'],16)==0 for e in [*mutations,all_ff_case]),
      'positive_HEVC_input_byte_offsets_read':[hex(i) for i in sorted(reads)],
      'positive_HEVC_read_stage48_unwritten_offsets':[hex(i) for i in sorted(reads&set(c.EXPECTED_UNWRITTEN))],
      '52bytes_globally_unused_or_safe_to_overwrite':False,
      'scope':'Full original pure codec-config predicate and original command routing on explicit fixtures. No full enc-start checker, VCD startup, actual shared RAM/address mapping/cache/doorbell/response, DSP encoding or real camera validation.',
      'Unicorn_version':u.__version__,'virtual_CPU_model':'MIPS32 24Kc, declared fixture; actual VCD CPU model not observed',
      'normal_CPU_kseg_mapping_not_host_address_or_return_adapter':True,
      'full_builder_Open_Start_Hal_or_file_audio_longrun_backup_recovery':False,
      'UU_Windows_or_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'vcd-consumer-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(avcam),'vcd_sha256':im.sha(vcd),'kernel_sha256':im.sha(kernel),
      'liro_sha256':im.sha(module),'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_functions_or_router_fragments',
      'allfour_original_codec_configs_return_zero','all52_single_and_combined_FF_return_zero',
      'positive_HEVC_read_stage48_unwritten_offsets','goal_complete')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
