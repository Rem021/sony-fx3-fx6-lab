#!/usr/bin/env python3
"""Original kernel prefix and module callback dependencies, static only."""
import datetime
import struct
import link_modules as f


def main():
    f.im.volume();out=f.STAGE/'kernel-boundary-audit.json';assert not out.exists()
    modules,providers,kernel=f.build();module=modules['osal_uipc.ko']
    boundaries=[]
    for name in ('_raw_spin_lock_irqsave','udif_driver_register'):
        address=providers[name]['address'];offset=address-f.n.K
        boundaries.append({'symbol':name,'static_kernel_address':hex(address),
          'instructions_not_executed':f.im.dump(kernel,offset,offset+0x60,f.n.K)})
    irq=boundaries[0]['instructions_not_executed']
    assert [x['asm'] for x in irq[:3]]==['mrs x3, daif','msr daifset, #2','mrs x2, sp_el0']
    driver=module.address('udif_uipc');data=module.section('.data');off=driver-data['base']
    ops=struct.unpack_from('<Q',data['data'],off+0x38)[0]
    assert data['base']<=ops<data['base']+data['size']
    callback=struct.unpack_from('<Q',data['data'],ops-data['base'])[0]
    init=module.section('.init.text');assert callback==init['base']
    inner=module.address('k_uipc_init')
    wrapper_call=[x for x in module.relocations if x['section']=='.init.text'
      and x['offset']=='0x90' and x['type']==283]
    assert len(wrapper_call)==1 and int(wrapper_call[0]['S_plus_A'],16)==inner
    symbol=[s for s in module.syms.iter_symbols() if s.name=='k_uipc_init'][0]
    start=symbol['st_value'];end=start+symbol['st_size']
    relocs=[x for x in module.relocations if x['section']=='.text' and start<=int(x['offset'],16)<end]
    assert {'__mutex_init','__get_free_pages','fblock_init','udif_cdev_register',
      'proc_create_data','osal_create_waitable_thread'}<={x['symbol'] for x in relocs}
    f.im.write_json(out,{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'STATIC_KERNEL_IRQ_CURRENT_TASK_AND_MODULE_INIT_REQUIREMENTS',
      'kernel_sha256':f.im.sha(kernel),'boundaries':boundaries,
      'module_driver_data_pointer':hex(driver),'driver_plus38_ops_pointer':hex(ops),
      'ops_first_callback_pointer':hex(callback),'ops_callback_name_not_retained':True,
      'first_callback_instructions_not_executed':f.im.dump(module.elf.get_section(init['index']).data(),0,0xe0,0),
      'first_callback_direct_call_to_inner':wrapper_call[0],
      'inner_callback_pointer':hex(inner),'inner_callback_symbol':'k_uipc_init',
      'callback_original_section_range':[hex(start),hex(end)],'callback_relocations':relocs,
      'callback_instructions_not_executed':f.im.dump(module.elf.get_section(symbol['st_shndx']).data(),start,end,0),
      'IRQ_flags_current_task_pointer_preempt_count_memory_pools_threads_or_callbacks_observed_on_camera':False,
      'zero_ELF_BSS_is_not_evidence_of_actual_camera_fault_or_valid_runtime_initialization':True,
      'native_kernel_or_callback_execution_here':False,
      'next_scope':'Audit original startup/context and callback arguments, kernel BSS/allocator ownership and thread/IRQ requirements before increasing native scope. Do not insert fabricated task structures, IRQ values, allocated pages or replies.'})
    print({'status':'STATIC_KERNEL_IRQ_CURRENT_TASK_AND_MODULE_INIT_REQUIREMENTS','callback':'k_uipc_init'})


if __name__=='__main__':main()
