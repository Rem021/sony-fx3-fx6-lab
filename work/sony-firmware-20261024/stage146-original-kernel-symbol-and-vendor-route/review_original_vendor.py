#!/usr/bin/env python3
"""Consolidate bounded original-code evidence; do not infer physical USB state."""
from pathlib import Path
from hashlib import sha256
import json
import struct
from kernel_symbols import KernelSymbols,K,KERNEL_SHA256

HERE=Path(__file__).resolve().parent


def main():
    image=KernelSymbols()
    source=json.loads((HERE/'kernel-symbol-recovery.json').read_text())
    names=json.loads((HERE/'run-symbol-verification/results.json').read_text())
    vendor=json.loads((HERE/'run-vendor-dispatch/results.json').read_text())
    assert source['symbol_count']==names['recovered_symbols']==41269
    assert names['original_export_entries']==6089 and names['original_leaf_guest_calls']==1007
    assert vendor['case_count']==11 and vendor['original_kernel_vendor_arm_entries']==11 and vendor['original_module_callback_entries']==8
    assert (HERE/'kernel_symbols.py').read_bytes()==(HERE/'run-symbol-verification/parser-executed.py').read_bytes()
    assert (HERE/'run_vendor_dispatch_guest.py').read_bytes()==(HERE/'run-vendor-dispatch/test-executed.py').read_bytes()
    assert sha256((HERE/'run_vendor_dispatch_guest.py').read_bytes()).hexdigest()==vendor['test_sha256']
    indexed={x['name']:x for x in vendor['cases']}
    one=indexed['start_all_THRU'];assert one['queue_attempts']==one['halt_bridge_calls']==1
    assert one['kernel_status_register_w19']==0 and one['internal_ep0_flag_after']==1
    failure=indexed['event_enqueue_failure_still_THRU']
    assert failure['queue_attempts']==failure['halt_bridge_calls']==1
    assert next(x for x in failure['events'] if x.get('bridge')=='usb_event_add_queue')['return']==-12
    later=indexed['later_handler_zero_after_failed_queue']
    assert later['queue_attempts']==1 and later['halt_bridge_calls']==0 and later['internal_ep0_flag_after']==0
    assert later['kernel_status_register_w19']==0
    assert next(x for x in later['events'] if x.get('bridge')=='usb_event_add_queue')['return']==-12
    # Recheck exact inlined command dispatch and both callback-result branches.
    expected={0x2e7524:0x7100179f,0x2e75a4:0xd63f0060,0x2e75b8:0x7100077f,
              0x2e75d4:0x94000000}
    assert image.u32(0x2e7524)==expected[0x2e7524]
    assert image.u32(0x2e75a4)==expected[0x2e75a4]
    assert image.u32(0x2e75b8)==expected[0x2e75b8]
    assert image.u32(0x2e75d4)&0xfc000000==expected[0x2e75d4]
    table=0x46f728;arms=struct.unpack_from('<6h',image.raw,table)
    assert 0x2e7544+arms[4]*4==0x2e7548
    references=[]
    for member,want in [('kernel/kallsyms.c','6319b85d5eedbd3b491d4224eeaa164e9e5f06ca7b87c64bafbea154d0cee952'),
                        ('scripts/kallsyms.c','a292041fcad2f1ea4e74eafbdf2b6c05beb6c0726910c816e9dffb083dd26fe4')]:
        path=HERE/'work/official-reference/linux-kernel'/member
        assert sha256(path.read_bytes()).hexdigest()==want
        references.append({'path':path.relative_to(HERE).as_posix(),'bytes':path.stat().st_size,'sha256':want})
    result={'status':'PASS_ORIGINAL_702_SYMBOL_AND_VENDOR_CONDITIONAL_BOUNDARIES_NOT_RUNTIME_READY',
        'original_kernel_sha256':KERNEL_SHA256,'symbol_count':41269,'original_export_pair_crosschecks':6089,
        'sampled_original_name_expansion_guest_calls':1007,'original_vendor_arm_cases':11,'original_module_callback_entries':8,
        'command4_vendor_arm':{'jump_table_offset':hex(table),'arm_file_offset':'0x2e7548','guest_entry_before_switch':'0x2e7524'},
        'queue_attempt_can_precede_original_kernel_halt_request':True,
        'queue_failure_can_coexist_with_no_halt_and_internal_zero_after_later_callback':True,
        'w19_is_internal_helper_or_handled_result_not_host_USB_success':True,
        'actual_702_instructions_replace_700_reference_only_for_these_bounded_branches':True,
        'not_proven':['kernel thread startup/locks/IRQ/scheduler','actual driver registration order or ownership',
                      'real event queue admission/delivery/completion','USB controller halt or host wire return',
                      'initial MSC authentication verifier','service entry/exit, healthy backup or unbrick'],
        'explicit_guest_bridges':['memcmp','stop_other_driver return fixture','event_add_queue return fixture',
                                  'printk','IRQ lock/unlock helpers','usb_ep_set_halt','other-driver callback returns'],
        'source_reference_page':'https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html',
        'reference_archive_sha256':'bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f',
        'reference_source_files':references,'new_host_USB_camera_or_driver_operations':0,
        'goal_complete':False,'persistent_write_release':False}
    with (HERE/'completed-local-review.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'symbols':41269,'export_pairs':6089,'name_guests':1007,'vendor_guests':11,
                      'new_camera_operations':0}))


if __name__=='__main__':main()
