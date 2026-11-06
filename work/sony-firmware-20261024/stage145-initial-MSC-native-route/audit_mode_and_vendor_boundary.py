#!/usr/bin/env python3
"""Audit the original callback and GPL dispatcher separately; no native USB code."""
from pathlib import Path
from hashlib import sha256
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
import io
import json
import re

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def record(path):return {'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha256(path.read_bytes()).hexdigest()}


def main():
    reference=json.loads((HERE/'official-gcore-reference.json').read_text())
    for rec in reference['records']:
        path=HERE/rec['path'];assert path.stat().st_size==rec['bytes'] and sha256(path.read_bytes()).hexdigest()==rec['sha256']
    module=BASE/'stage138-USB-stop-dispatch-and-Mac-ownership/original-components/kmod/usbg_sen.ko'
    raw=module.read_bytes();assert sha256(raw).hexdigest()=='1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2'
    elf=ELFFile(io.BytesIO(raw));text=elf.get_section_by_name('.text').data();symbols=elf.get_section_by_name('.symtab')
    reloc={r['r_offset']:symbols.get_symbol(r['r_info_sym']).name for r in elf.get_section_by_name('.rela.text').iter_relocations()}
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    native=[{'offset':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'relocation_symbol':reloc.get(i.address)}
            for i in md.disasm(text[:0xc8],0)]
    bypc={int(x['offset'],16):x for x in native}
    assert bypc[0x58]['asm']=='mov w0, #2'
    assert bypc[0x70]['relocation_symbol']=='usb_gadgetcore_stop_other_driver'
    assert bypc[0x98]['relocation_symbol']=='usb_event_add_queue' and bypc[0x9c]['asm']=='b #0x54'
    directory=HERE/'work/official-kernel-reference/linux-kernel'
    paths=[directory/'include/linux/usb/gcore/usb_gadgetcore.h',
           directory/'drivers/usb/gcore/usb_gcore_setup.c',directory/'drivers/usb/gcore/usb_gcore_main.c']
    header,setup,main=(p.read_text(errors='replace') for p in paths)
    assert re.search(r'#define\s+USB_GADGETCORE_STALL\s+1',header)
    assert re.search(r'#define\s+USB_GADGETCORE_THRU\s+2',header)
    assert 'rc = tmp_func_drv->func_drv->vendor(tmp_func_drv->func_drv,' in setup
    assert 'tmp_func_drv->func_drv->stop(tmp_func_drv->func_drv);' in main
    snippets=[]
    for path,lo,hi in [(paths[0],58,65),(paths[1],516,551),(paths[1],2399,2413),
                       (paths[1],2549,2566),(paths[2],1004,1028)]:
        lines=path.read_text(errors='replace').splitlines()
        snippets.append({'path':path.relative_to(ROOT).as_posix(),'first_line':lo,'last_line':hi,
                         'text':'\n'.join(lines[lo-1:hi])})
    adopted=BASE/'stage143-mode-specific-authentication'
    candidates=json.loads((adopted/'MSC-original-candidates.json').read_text())
    pins=[record(adopted/'MSC-original-candidates.json'),record(adopted/'inspect_MSC_candidates.py')]
    for rec in candidates['records']:
        path=ROOT/rec['path'];assert record(path)=={k:rec[k] for k in ('path','bytes','sha256')}
        pins.append(record(path))
    pins.append(record(adopted/'README.md'))
    put={'status':'ORIGINAL_CALLBACK_RETURNS_THRU_AFTER_QUEUE_ATTEMPT_GPL_CORE_MAY_STALL_NOT_EXACT_702_CORE_RUNTIME_PROOF',
         'original_module':record(module),'original_callback_instructions':native,
         'original_queue_return_checked':False,'original_callback_returns_constant_2':True,
         'reference_THRU_value':2,'reference_STALL_value':1,'reference_source_snippets':snippets,
         'reference_other_recipient_visits_all_registered_vendor_callbacks':True,
         'if_all_callbacks_THRU_reference_returns_EINVAL_even_after_queue_attempt':True,
         'reference_vendor_request_uses_delayed_work_and_later_setup_response':True,
         'actual_702_gcore_runtime_registration_order_and_wire_STALL_proven':False,
         'transport_or_control_ACK_does_not_prove_queue_admission_consumption_or_worker_completion':True,
         'completed_STALL_must_not_be_conflated_with_no_effect_or_automatic_retry':True,
         'stage140_generic_START_error_goes_to_cleanup_not_authentication':True,
         'stage140_error_semantics_not_silently_changed_by_this_stage':True,
         'adopted_unsealed143_evidence_pins':pins,
         'initial_MSC_digest_verifier_not_located':True,
         'downloaded_native_USB_or_Sony_code_executed':False,'camera_or_Windows_operations':0}
    with (HERE/'mode-and-vendor-boundary-review.json').open('x') as f:json.dump(put,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':put['status'],'reference_files_verified':len(reference['records']),
                      'original_callback_bytes':0xc8,'adopted143_pins':len(pins),'new_USB_operations':0}))


if __name__=='__main__':main()
