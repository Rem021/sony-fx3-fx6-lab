#!/usr/bin/env python3
"""Original LIRO-bound OSAL entry to unexecuted kernel lock service.

Declared relocated module pages/ELF-zero BSS are not running Linux module
state. No kernel IRQ/thread/allocator, OSAL buffer or synchronous reply adapter.
"""
from pathlib import Path
import argparse
import datetime
import io
import json
import struct
import traceback
from elftools.elf.elffile import ELFFile
import link_modules as link

STAGE,BASE,ROOT=link.STAGE,link.BASE,link.ROOT
f=link.prev
r,im,V,n,p=f.r,f.im,f.V,f.n,f.p
SLOTS={'osal_valloc_msg_wait':0x398,'osal_snd_sync_msg':0x368,
       'osal_free_msg':0x3a0,'osal_set_msg_src':0x3c8}


class Guest(f.Guest):
    def __init__(self,assets,modules,providers):
        super().__init__(*assets)
        self.modules=modules;self.providers=providers;self.module_writes=[]
        self.kernel_service_entries=[];self.module_alloc_entries=[];self.empty_client_reads=[]
        self.lock_entries=[];self.import_bindings=[]
        self.boundaries.pop(V+0x2f038)
        self.kernel_names={}
        for name,resolution in providers.items():
            if resolution['kind']!='original_kernel_export_candidate' or name in ('memcpy','memset'):continue
            self.kernel_names.setdefault(resolution['address'],[]).append(name)
            self.boundaries[resolution['address']]='before_original_unexecuted_kernel_service'
        for module in modules.values():
            for section in module.sections.values():
                if not section['mapped_size']:continue
                perm=r.unicorn.UC_PROT_READ
                if section['flags']&1:perm|=r.unicorn.UC_PROT_WRITE
                if section['flags']&4:perm|=r.unicorn.UC_PROT_EXEC
                assert perm!=7
                self.uc.mem_map(section['base'],section['mapped_size'],perm)
                self.uc.mem_write(section['base'],bytes(section['data']))
                assert self.read(section['base'],section['size'])==bytes(section['data'])
        uipc=modules['osal_uipc.ko'];text=uipc.section('.text')['base'];self.utext=text
        self.ranges.extend((text+a,text+z) for a,z in [
          (0x44c0,0x4628),(0x3248,0x3518),(0x2ee8,0x3158),(0x1b8,0x1dc),(0x5e68,0x5e70)])
        for module in (uipc,modules['osal_utm.ko']):
            sym=[s for s in module.syms.iter_symbols() if s.name=='init_module']
            assert len(sym)==1
            self.ranges.append((module.address('init_module'),module.address('init_module')+sym[0]['st_size']))
        elf=ELFFile(io.BytesIO(assets[1]));sy=elf.get_section_by_name('.symtab')
        rels={x['r_offset']:x for x in elf.get_section_by_name('.rela.init.data').iter_relocations()}
        # Apply only the original four ABS64 provider relocations to LIRO's
        # source vector, then let its original kernel memcpy copy the vector.
        for name,slot in SLOTS.items():
            rel=rels[slot];assert rel['r_info_type']==257 and rel['r_addend']==0
            assert sy.get_symbol(rel['r_info_sym']).name==name
            target=uipc.exports[name]['address']
            assert self.read(n.MDATA+slot,8)==bytes(8)
            self.uc.mem_write(n.MDATA+slot,r.p64(target))
            self.import_bindings.append({'name':name,'LIRO_init_data_offset':hex(slot),
              'actual_avcam_slot':hex(V+0x1ec+slot),'original_module_target':hex(target)})

    def code(self,u,pc,size,user):
        reg=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
        if pc in self.kernel_names:
            self.kernel_service_entries.append({'pc':hex(pc),'names':sorted(self.kernel_names[pc]),
              'LR':hex(reg(30)),'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'x0_x5':[hex(reg(i)) for i in range(6)],'kernel_body_executed':False,
              'kernel_return_IRQ_lock_thread_or_allocation_adapter':False})
        if pc==self.utext+0x44c0:
            self.module_alloc_entries.append({'pc':hex(pc),'LR':hex(reg(30)),
              'x0_x3':[hex(reg(i)) for i in range(4)],'native_module_function_entered':True})
        if pc==self.utext+0x3290:
            self.empty_client_reads.append({'pc':hex(pc),'client_id':reg(4)&0x7fff,
              'slot_address':hex(reg(0)+0x10),'loaded_X21':hex(reg(21)),
              'slot_bytes':self.read(reg(0)+0x10,8).hex(),
              'ELF_zero_BSS_not_real_driver_initialization':True})
        if pc==self.utext+0x1b8:
            self.lock_entries.append({'pc':hex(pc),'object':hex(reg(0)),
              'initial_object16_hex':self.read(reg(0),16).hex()})
        if pc==V+0x2f038:
            self.allocation_entries.append({'pc':hex(pc),'branch_X4':hex(reg(4)),
              'x0_x3':[hex(reg(i)) for i in range(4)],'LR':hex(reg(30)),
              'indirect_branch_executed':True,'buffer_or_OSAL_return_adapter':False})
            # stage63's observation stopped before this branch. Here the
            # actual target is bound and executed; do not inherit false data.
            return f.last.Guest.code(self,u,pc,size,user)
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        for module in self.modules.values():
            for section in module.sections.values():
                if section['flags']&1 and section['base']<=address and address+size<=section['base']+section['size']:
                    pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
                    assert any(a<=pc<z for a,z in self.ranges)
                    self.module_writes.append({'pc':hex(pc),'address':hex(address),'size':size})
                    return
        return super().store(u,access,address,size,value,user)


def phase(m,label,absolute,**regs):
    global LAST_PHASE
    e=p.c.phase(m,label,absolute,**regs);LAST_PHASE=e
    return e


def linked(assets,modules,providers):
    m=Guest(assets,modules,providers);events=[n.link(m)]
    for binding in m.import_bindings:
        assert m.read(int(binding['actual_avcam_slot'],16),8)==r.p64(int(binding['original_module_target'],16))
    assert sum(int.from_bytes(m.read(V+0x1ec+i*8,8),'little')!=0 for i in range(211))==5
    m.uc.mem_write(f.f58.SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for at,value in m.expected_data.items():
        assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=phase(m,'original mute setter on declared initialized logger',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    low=f.G&~4095;high=(f.G+f.GSIZE+4095)&~4095
    m.uc.mem_protect(low,high-low,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    return m,events


def assert_images(m,global_initialized):
    raw=bytearray(m.read(V,len(m.blob)))
    assert raw[0x1ec:0x884]==m.read(n.MDATA,0x698);raw[0x1ec:0x884]=m.blob[0x1ec:0x884]
    at=f.f58.SITE-V;assert raw[at:at+4]==m.patch;raw[at:at+4]=m.blob[at:at+4]
    for at,value in m.expected_data.items():assert raw[at-V]==value;raw[at-V]=m.blob[at-V]
    assert raw[f.FLAG-V:f.FLAG-V+8]==r.p64(int(global_initialized))
    if global_initialized:raw[f.G-V:f.G-V+f.GSIZE]=m.blob[f.G-V:f.G-V+f.GSIZE]
    assert raw==m.blob
    assert m.read(f.f58.BRIDGE,len(m.code_bytes))==m.code_bytes
    assert m.read(f.f58.CONST,len(m.ro_bytes))==m.ro_bytes
    for module in m.modules.values():
        for section in module.sections.values():
            assert m.read(section['base'],section['size'])==bytes(section['data'])
    assert not m.module_writes


def request(assets,modules,providers,label,descriptor,seed,expected):
    m,events=linked(assets,modules,providers);f.prefix(m,events,descriptor,seed)
    assert m.real_returns[0]['W0']==expected
    source=int(m.bridge_entries[0]['source'],16);raw=m.read(source,152)
    assert raw[:136]==descriptor and m.read(f.last.COMMON+0xe110,136)==descriptor
    m.boundaries.pop(V+0x21dd54)
    e=phase(m,'same original queued request through original LIRO-bound OSAL to kernel service '+label,
      V+0x21dd54,independent=False)
    events.append(e)
    assert e['reason']=='boundary: before_original_unexecuted_kernel_service',e['reason']
    assert len(m.kernel_service_entries)==len(m.module_alloc_entries)==len(m.empty_client_reads)==len(m.lock_entries)==1
    dep=m.kernel_service_entries[0];assert dep['names']==['_raw_spin_lock_irqsave']
    assert dep['LR']==hex(m.utext+0x1cc)
    assert m.allocation_entries[0]['indirect_branch_executed']
    assert m.allocation_entries[0]['branch_X4']==hex(modules['osal_uipc.ko'].exports['osal_valloc_msg_wait']['address'])
    assert m.empty_client_reads[0]['loaded_X21']=='0x0' and m.empty_client_reads[0]['client_id']==0x3c
    assert m.lock_entries[0]['initial_object16_hex']==bytes(16).hex()
    assert dep['x0_x5'][0]==m.lock_entries[0]['object']
    assert m.read(source,152)==raw and m.read(f.last.COMMON+0xe110,136)==descriptor
    assert_images(m,True)
    return {'label':label,'seed':seed,'native_row':expected,'events':events,'import_bindings':m.import_bindings,
      'native_message':m.message_entries[0],'allocation_branch':m.allocation_entries[0],
      'native_OSAL_entry':m.module_alloc_entries[0],'empty_client_cache':m.empty_client_reads[0],
      'native_OSAL_lock_entry':m.lock_entries[0],'kernel_service_boundary':dep,
      'source_and_common_descriptor_unchanged':True,'module_sections_remain_relocated_initial_bytes':True,
      'module_driver_init_kernel_lock_allocator_reply_or_hardware_complete':False}


def source_setter(assets,modules,providers,value):
    m,events=linked(assets,modules,providers);buf=r.ARENA+0x3f0000;pointer=buf+32
    original=bytes([0x5a])*128;m.uc.mem_write(buf,original)
    target=modules['osal_uipc.ko'].exports['osal_set_msg_src']['address']
    e=phase(m,'independent original OSAL source setter on supplied prefixed storage',target,x0=pointer,x1=value)
    events.append(e);assert e['reason']=='returned' and e['SP_after']==hex(r.SP)
    expected=bytearray(original);struct.pack_into('<I',expected,20,value)
    assert m.read(buf,128)==bytes(expected)
    assert_images(m,False)
    return {'value':hex(value),'buffer':hex(buf),'payload_pointer':hex(pointer),'events':events,
      'only_payload_minus12_four_bytes_changed':True,'output128_hex':m.read(buf,128).hex(),
      'independent_storage_not_a_real_OSAL_allocation_or_full_message_send':True}


def init_entry(assets,modules,providers,module_name):
    m,events=linked(assets,modules,providers);module=modules[module_name]
    e=phase(m,'independent original module init entry to registration boundary '+module_name,module.address('init_module'))
    events.append(e);assert e['reason']=='boundary: before_original_unexecuted_kernel_service'
    assert len(m.kernel_service_entries)==1 and m.kernel_service_entries[0]['names']==['udif_driver_register']
    address=int(m.kernel_service_entries[0]['x0_x5'][0],16);data=module.section('.data')
    assert data['base']<=address<data['base']+data['size']
    assert_images(m,False)
    return {'module':module_name,'events':events,'registration_boundary':m.kernel_service_entries[0],
      'registration_callbacks_or_runtime_driver_initialization_executed':False}


def run(out):
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    modules,providers,kernel=link.build()
    linkedproof=STAGE/'link-run-20261026/module-relocation-results.json'
    assert [m.facts() for m in modules.values()]==json.loads(linkedproof.read_text())['modules']
    obj=f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=f.f58.object_image(obj.read_bytes())
    wobj=f.f61.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    wcode,wro,functions,_=f.f61.old.object_image(wobj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets=blob,liro,kernel,code,ro,wcode,wro,functions;inp=p.inputs()
    cases=[request(assets,modules,providers,'target FH priorA5',inp[0][1],0xa5,386),
      request(assets,modules,providers,'target FH priorC3',inp[0][1],0xc3,386),
      request(assets,modules,providers,'stock UHD control',inp[3][1],0xc3,431)]
    setters=[source_setter(assets,modules,providers,x) for x in (0x806800f3,0x12345678)]
    inits=[init_entry(assets,modules,providers,x) for x in ('osal_uipc.ko','osal_utm.ko')]
    proof={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'PASS_ORIGINAL_LIRO_OSAL_LINK_TO_UNEXECUTED_KERNEL_SERVICE',
      'requests':cases,'independent_source_setters':setters,'independent_init_entries':inits,
      'bounded_fragments':sum(len(x['events']) for x in cases+setters+inits),
      'module_page_readback_and_no_post_load_module_writes':True,
      'real_Linux_module_load_IRQ_task_driver_pool_init_OSAL_allocation_reply_or_Hal':False,
      'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'native-osal-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'linker_source_sha256':im.sha((STAGE/'link_modules.py').read_bytes()),
      'link_proof_sha256':im.sha(linkedproof.read_bytes()),'avcam_sha256':im.sha(blob),
      'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel),
      'wrapper_sha256':im.sha(obj.read_bytes()),'previous_manifest_sha256':link.PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['bounded_fragments'],
      'request_stop':'original kernel _raw_spin_lock_irqsave entry','goal_complete':False}))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        e=globals().get('LAST_PHASE',getattr(f,'LAST_PHASE',None))
        if e:im.write_json(out/'last-phase-at-failure.json',e)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
