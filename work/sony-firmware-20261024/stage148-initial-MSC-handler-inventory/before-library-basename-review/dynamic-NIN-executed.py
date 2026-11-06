#!/usr/bin/env python3
"""Trace original libObj callback to dynamic NIN loader using unwind boundaries."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
from elftools.dwarf.callframe import FDE

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def main():
    prior=BASE/'stage134-backup-reader-scope-and-service-extension'
    raw=(prior/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    path=prior/'audit_readers.py';pin=next(x for x in json.loads(raw)['files'] if x['path']==path.relative_to(ROOT).as_posix())
    assert sha256(path.read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_dynamic_image',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.LIB=HERE/'work/originals'
    obj=module.Image('libObj.so','c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae')
    frames={x['initial_location']:x['address_range'] for x in obj.elf.get_dwarf_info().EH_CFI_entries() if isinstance(x,FDE)}
    labels={0xeaa04:'exported_senser_init',0xea54c:'normal_senif_setup',0xea4f4:'register_senif_callbacks',
            0xea128:'shared_senif_event_callback',0xeb900:'dynamic_NinThread_start',
            0xeb794:'open_core_library',0xec5bc:'dynamic_symbol_lookup',0xec3f4:'thread_start_wrapper',
            0xea1dc:'normal_dispatcher_thread',0xeb7f4:'dynamic_normal_mode_start',0xea0a4:'normal_mode_callback'}
    functions=[]
    for va,label in labels.items():
        assert va in frames and 0<frames[va]<2048,(hex(va),frames.get(va))
        size=frames[va]
        functions.append({'label':label,'VA':hex(va),'bytes':size,'boundary_source':'original .eh_frame FDE',
            'sha256':sha256(obj.read(va,size)).hexdigest(),'instructions':obj.instructions(va,size)})
    ins={int(i['pc'],16):i for f in functions for i in f['instructions']}
    expected={0xeaa94:'bl #0xea54c',0xea574:'bl #0xea4f4',0xea500:'mov w0, #1',
              0xea508:'ldr x2, [x2, #0x8d0]',0xea50c:'add x1, x1, #0x168',
              0xea128:'cmp w0, #1',0xea13c:'cmp w2, #1',0xea140:'b.hi #0xea1d8',
              0xea164:'str x1, [x0, #0x100]',0xea194:'mov x1, x20',0xea1a0:'bl #0xeb900',
              0xeb91c:'bl #0xeb794',0xeb924:'b.eq #0xeb94c',0xeb930:'add x1, x1, #0x262',
              0xeb934:'bl #0xec5bc',0xeb938:'mov x1, x0',0xeb93c:'mov x2, x19',0xeb948:'bl #0xec3f4',
              0xea254:'bl #0xeb7f4',0xeb824:'add x1, x1, #0x22f',0xeb828:'bl #0xec5bc',0xeb844:'br x2'}
    for pc,asm in expected.items():assert ins[pc]['asm']==asm,(hex(pc),ins[pc])
    assert ins[0xea510]['PLT_symbol']=='senif_init'
    assert any(i['PLT_symbol']=='dlsym' for i in ins.values())
    assert any(i['PLT_symbol']=='pthread_create' for i in ins.values())
    strings={hex(va):obj.string(va) for va in (0x1dc22f,0x1dc262)}
    assert strings=={'0x1dc22f':'senser_normal_mode_start','0x1dc262':'NinThread'}
    dyn=obj.elf.get_section_by_name('.dynsym');relocs={}
    for r in obj.elf.get_section_by_name('.rela.dyn').iter_relocations():
        if r['r_offset'] in (0x2628d0,0x2646c8,0x2646d0):
            assert r['r_info_type']==1027 and r['r_info_sym']==0
            relocs[hex(r['r_offset'])]={'type':'R_AARCH64_RELATIVE','addend':hex(r['r_addend'])}
    assert relocs=={'0x2628d0':{'type':'R_AARCH64_RELATIVE','addend':'0x2646c8'},
        '0x2646c8':{'type':'R_AARCH64_RELATIVE','addend':'0xea128'},
        '0x2646d0':{'type':'R_AARCH64_RELATIVE','addend':'0xea128'}}
    report={'status':'ORIGINAL_NORMAL_APPLICATION_CALLBACK_REACHES_DYNAMIC_NIN_START_STATIC_ONLY',
        'input_SHA256':sha256(obj.raw).hexdigest(),'functions':functions,'asserted_local_instruction_facts':len(expected),
        'callback_table_relocations':relocs,'dynamic_symbol_strings':strings,
        'route':'senser_init non-mode1 branch -> senif_init(1, callbacks) -> event1 callback with state<=1 -> dynamically resolve NinThread -> thread_create wrapper',
        'normal_mode_dispatcher':'mode0 dispatcher thread separately resolves senser_normal_mode_start',
        'full_dynamic_library_path_and_runtime_symbol_resolution_proven':False,
        'current_MSC_driver_USB_transport_or_cooperator_vtable_binding_proven':False,
        'initial_MSC_hash_input_algorithm_proven':False,
        'no_auto_change_to_stage145_MSC_digest_selection':True,
        'new_host_USB_camera_driver_or_Windows_operations':0,'original_code_executed':False}
    with (HERE/'dynamic-NIN-route-review.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'dynamic-NIN-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':report['status'],'original_FDE_bounded_functions':len(functions),
        'instruction_facts':len(expected),'callback_relocations':len(relocs),'initial_MSC_verifier_proven':False}))


if __name__=='__main__':main()
