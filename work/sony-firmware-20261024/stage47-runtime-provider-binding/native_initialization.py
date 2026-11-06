#!/usr/bin/env python3
"""Original kernel memcpy/memset plus original LIRO copy and two constructors.

Only memcpy/memset imports are resolved from original kernel exports. Other
runtime imports stay zero. Module section bases/CPU are explicit guest fixtures;
no actual kernel/module boot or camera instance. No PC/return/service adapter.
"""
from pathlib import Path
import argparse
import datetime
import io
import json
import struct
import sys
import traceback
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import provider_binding as q
r,im,V,BASE,ROOT=q.r,q.im,q.V,q.BASE,q.ROOT
K=0xffffff8008080000
MCODE=K+0x1000000
MSTR=MCODE+0x10000
MDATA=MCODE+0x20000
CONTEXT=q.CONTEXT
LOWER=r.ARENA+0x240000
UPPER=r.ARENA+0x260000
DEST=r.ARENA+0x35000c


def kernel_exports(kernel):
    # The first candidate has nine adjacent valid export-name starts and
    # sorted names. The second low-page candidate found during discovery did
    # not pass neighboring string-boundary validation and is not admitted.
    around=[]
    for at in range(0x57df98,0x57e028,16):
        value,name=struct.unpack_from('<QQ',kernel,at);off=name-K
        assert kernel[off-1]==0;label=im.cstring(kernel,off)
        assert 0<=value-K<len(kernel)
        around.append({'entry_offset':hex(at),'name':label,'name_offset':hex(off),'value':hex(value)})
    assert [e['name'] for e in around]==sorted(e['name'] for e in around)
    result={}
    for name,entry in (('memcpy',0x57de98),('memset',0x57dfd8)):
        value,pointer=struct.unpack_from('<QQ',kernel,entry)
        assert im.cstring(kernel,pointer-K)==name and kernel[pointer-K-1]==0
        result[name]={'entry_offset':hex(entry),'value':value,'file_offset':value-K,'name_offset':hex(pointer-K)}
    assert result['memcpy']['file_offset']==0x1efe80 and result['memset']['file_offset']==0x1f0180
    return result,around


class Guest(r.RawGuest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,[(0x253b38,0x253dac),(0x155bd0,0x155f7c),(0x2f67c,0x2f690)],{})
        self.exports,self.export_neighbors=kernel_exports(kernel);self.loading=False;self.cpu_events=[]
        self.ranges.extend([(K+0x1efe80,K+0x1effe0),(K+0x1f0180,K+0x1f0308),(MCODE+0x4b0,MCODE+0x4c8)])
        self.boundaries[MCODE+0x4c8]='after_original_kernel_memcpy_before_next_diagnostic'
        self.uc.mem_map(K,(len(kernel)+4095)&~4095,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_write(K,kernel)
        elf=ELFFile(io.BytesIO(module));text=bytearray(elf.get_section_by_name('.init.text').data())
        data=bytearray(elf.get_section_by_name('.init.data').data());syms=elf.get_section_by_name('.symtab')
        rels={e['r_offset']:e for e in elf.get_section_by_name('.rela.init.text').iter_relocations()}
        rel=rels[0x598];symbol=syms.get_symbol(rel['r_info_sym'])
        assert rel['r_info_type']==257 and symbol['st_shndx']==25 and rel['r_addend']==0
        struct.pack_into('<Q',text,0x598,MDATA)
        rel=rels[0x4c4];symbol=syms.get_symbol(rel['r_info_sym'])
        assert rel['r_info_type']==283 and symbol.name=='memcpy'
        delta=self.exports['memcpy']['value']-(MCODE+0x4c4)
        assert delta%4==0 and -(1<<27)<=delta<(1<<27)
        old=struct.unpack_from('<I',text,0x4c4)[0];assert old&0xfc000000==0x94000000
        struct.pack_into('<I',text,0x4c4,(old&0xfc000000)|((delta//4)&0x3ffffff))
        rels={e['r_offset']:e for e in elf.get_section_by_name('.rela.init.data').iter_relocations()}
        rel=rels[0x670];assert rel['r_info_type']==257 and syms.get_symbol(rel['r_info_sym']).name=='memset'
        assert syms.get_symbol(rel['r_info_sym'])['st_shndx']=='SHN_UNDEF' and rel['r_addend']==0
        struct.pack_into('<Q',data,0x670,self.exports['memset']['value'])
        assert sum(int.from_bytes(data[i:i+8],'little')!=0 for i in range(0,len(data),8))==1
        for address,content in ((MCODE,bytes(text)),(MDATA,bytes(data))):
            self.uc.mem_map(address,(len(content)+4095)&~4095,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
            self.uc.mem_write(address,content)
        # Only the shared first page containing the import vector is writable
        # for original loader memcpy; no execution from that page is admitted.
        self.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)

    def code(self,u,pc,size,user):
        if pc in (K+0x1f0280,K+0x1f02ec):
            # Execute the actual Unicorn implementation of these two original
            # instructions. Never replace register values or zero bytes here.
            instruction=next(self.md.disasm(bytes(u.mem_read(pc,size)),pc))
            expected=('mrs','x3, dczid_el0') if pc==K+0x1f0280 else ('dc','zva, x8')
            assert (instruction.mnemonic,instruction.op_str)==expected
            self.pcs.append(pc);self.cpu_events.append({'pc':hex(pc),'instruction':instruction.mnemonic+' '+instruction.op_str,
              'x8':hex(u.reg_read(r.reg.UC_ARM64_REG_X8))})
            return
        if pc==K+0x1f0284:
            self.cpu_events.append({'pc':hex(pc),'emulated_DCZID_EL0':hex(u.reg_read(r.reg.UC_ARM64_REG_X3)),
              'actual_FX3_CPU_register_not_observed':True})
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        if V+0x1ec<=address and address+size<=V+0x884:
            assert self.loading and K+0x1efe80<=u.reg_read(r.reg.UC_ARM64_REG_PC)<K+0x1effe0
            self.writes.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),'address':hex(address),'size':size,'scope':'original_loader_import_data'})
            return
        return super().store(u,access,address,size,value,user)


def phase(m,label,address,**regs):
    m.reason=None;m.pcs=[];m.writes=[];m.cpu_events=[];m.regs(sp=r.SP,x30=r.STOP);m.regs(**regs)
    m.uc.emu_start(address,0,count=20000,timeout=1000000)
    assert m.reason is not None
    return {'label':label,'reason':m.reason,'start_pc':hex(address),'stop_pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
      'SP_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
      'x0_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_X0)),
      'pcs':[hex(pc) for pc in m.pcs],'writes':m.writes,'emulated_CPU_instructions':list(m.cpu_events),
      'native_output_or_return_adapter':False}


def link(m):
    m.uc.mem_write(CONTEXT+0x50,r.p64(V));m.loading=True
    event=phase(m,'original LIRO copy through original exported kernel memcpy',MCODE+0x4b0,x19=CONTEXT)
    m.loading=False
    assert event['reason']=='boundary: after_original_kernel_memcpy_before_next_diagnostic'
    assert m.read(V+0x1ec,0x698)==m.read(MDATA,0x698)
    assert int.from_bytes(m.read(V+0x85c,8),'little')==m.exports['memset']['value']
    assert m.read(V,0x1ec)==m.blob[:0x1ec] and m.read(V+0x884,len(m.blob)-0x884)==m.blob[0x884:]
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ)
    return event


def run(out):
    prior=BASE/'stage46-upstream-restore-audit/final-receipt.json';assert im.sha(prior.read_bytes())=='ed3e73134be9b4da9b7a6c035c52c1043e11e69396340e2426405eb0d5f679b6'
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    for row in json.loads((STAGE/'official-extraction-receipt.json').read_text())['files']:assert im.sha(Path(row['output']).read_bytes())==row['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes();kernel=(STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    exports,neighbors=kernel_exports(kernel);events=[];clears=[];constructors=[]
    for length,fill in ((0x58,0),(0x151,0),(0x581,0),(0x151,0x13)):
        m=Guest(blob,module,kernel);m.uc.mem_write(DEST-32,bytes([0xa5])*(length+64))
        event=phase(m,'original kernel memset len'+hex(length)+' fill'+hex(fill),exports['memset']['value'],x0=DEST,x1=fill,x2=length)
        assert event['reason']=='returned' and event['x0_after']==hex(DEST)
        assert m.read(DEST,length)==bytes([fill])*length
        assert m.read(DEST-32,32)==m.read(DEST+length,32)==bytes([0xa5])*32
        events.append(event);clears.append({'length':length,'fill':fill,'exact_bytes_and_redzones_verified':True,'original_fragment':event})
    for name,obj,entry,size,state,clear_length,queue in (
      ('imola_encoder_state',LOWER,0x253b38,0x700,14,0x151,0x5a0),
      ('sfmc_output_state',UPPER,0x155bd0,0xe00,42,0x581,0xd18)):
        m=Guest(blob,module,kernel);m.uc.mem_write(obj,bytes([0xa5])*size)
        loaded=link(m);events.append(loaded)
        event=phase(m,'complete original constructor body '+name,V+entry,x0=obj);events.append(event)
        assert event['reason']=='returned' and event['SP_after']==hex(r.SP)
        assert hex(V+0x2f67c) in event['pcs'] and hex(exports['memset']['value']) in event['pcs']
        assert m.read(obj+0xc,clear_length)==bytes(clear_length) and m.read(obj+queue,0x58)==bytes(0x58)
        assert int.from_bytes(m.read(obj+8,4),'little')==state and m.read(obj,8)==bytes(8)
        constructors.append({'kind':name,'object_fixture':hex(obj),'initial_state':state,'active':m.read(obj+0xc,1)[0],
          'cleared_state_bytes':clear_length,'cleared_queue_bytes':0x58,
          'original_fragments':[loaded,event],
          'complete_bounded_constructor_body_returned_under_partial_import_fixture':True,
          'real_factory_owner_instance_synchronization_epoch_or_Hal_verified':False})
    proof={'status':'PASS_ORIGINAL_KERNEL_MEMORY_PROVIDERS_LOADER_COPY_AND_COMPLETE_BOUNDED_CONSTRUCTORS',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kernel_link_base':hex(K),
      'kernel_exports':exports,'validated_export_neighbors':neighbors,'clear_cases':clears,'constructor_cases':constructors,
      'original_fragments':len(events),'ordinary_store_hook_events':sum(len(e['writes']) for e in events),
      'unicorn_version':r.unicorn.__version__,
      'runtime_fixture':'Only original kernel memcpy/memset resolved. All other imports zero; module sections at declared guest addresses; actual FX3 ASLR/CPU/boot/loader instance unobserved.',
      'DCZID_and_DC_ZVA':'Original instructions executed by Unicorn; no register/output/zeroing adapter. Exact clear bytes and redzones verified; virtual CPU is not FX3 CPU evidence.',
      'host_official_files_and_guest_instruction_bytes_unchanged_except_two_ELF_relocations':True,
      'guest_avcam_API_data_initialized_by_original_loader_copy':True,
      'full_kernel_boot_logs_locks_Hal_or_52byte_codec_initialization_verified':False,
      'camera_or_remote_operation':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'native-initialization-results.json',proof);(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),'avcam_sha256':im.sha(blob),
      'kernel_sha256':im.sha(kernel),'liro_module_sha256':im.sha(module),'proof_sha256':im.sha((out/'native-initialization-results.json').read_bytes()),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_fragments','ordinary_store_hook_events',
      'full_kernel_boot_logs_locks_Hal_or_52byte_codec_initialization_verified','goal_complete','persistent_write_release')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args();im.volume()
    out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
