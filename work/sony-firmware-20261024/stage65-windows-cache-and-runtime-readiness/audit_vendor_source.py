#!/usr/bin/env python3
"""Cross-check selected official 7.00 vendor-source ABI with original 7.02 bytes."""
import datetime
import json
import re
import struct
import tarfile
import prepare_handoff as h

ARCHIVE_SHA = 'bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
KERNEL_SHA = 'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
NAMES = ['Makefile', 'arch/arm64/include/asm/current.h', 'arch/arm64/include/asm/thread_info.h',
    'arch/arm64/include/asm/memory.h', 'arch/arm64/kernel/head.S', 'include/linux/sched.h',
    'include/linux/sched/prio.h', 'include/linux/udif/driver.h', 'drivers/udif/driver.c',
    'arch/arm64/configs/cxd90057_set_defconfig',
    'arch/arm64/boot/dts/cxd/cxd90057_set.dts', 'arch/arm64/boot/dts/cxd/cxd90057-memmap.dtsi']


def main():
    h.im.volume()
    out = h.STAGE / 'vendor-source-runtime-crosscheck.json'
    assert not out.exists()
    receipt = json.loads((h.STAGE / 'runtime-source-downloads.json').read_text())
    source = receipt['files'][0]
    archive_path = h.ROOT / source['path']
    assert source['sha256'] == ARCHIVE_SHA == h.im.sha(archive_path.read_bytes())
    assert source['official_content_md5_verified']
    texts = {}
    rows = {}
    with tarfile.open(archive_path, 'r:gz') as archive:
        for name in NAMES:
            member = archive.getmember('linux-kernel/' + name)
            assert member.isfile() and member.size < 200000
            data = archive.extractfile(member).read()
            assert len(data) == member.size
            texts[name] = data.decode()
            rows[name] = {'archive_member': member.name, 'bytes': member.size, 'sha256': h.im.sha(data)}
    def excerpt(name, lo, hi):
        lines = texts[name].splitlines()
        return {'member': name, 'lines': [[i+1, lines[i]] for i in range(lo-1, min(hi, len(lines)))]}
    assert texts['Makefile'].splitlines()[:3] == ['VERSION = 4', 'PATCHLEVEL = 9', 'SUBLEVEL = 337']
    assert 'return (struct task_struct *)read_sysreg(sp_el0);' in texts[NAMES[1]]
    thread = re.search(r'struct thread_info \{(.*?)\n\};', texts[NAMES[2]], re.S).group(1)
    assert 'unsigned long\t\tflags;' in thread and 'mm_segment_t\t\taddr_limit;' in thread
    assert 'int\t\t\tpreempt_count;' in thread and '*task' not in thread
    config_name = 'arch/arm64/configs/cxd90057_set_defconfig'
    config = dict(line.split('=', 1) for line in texts[config_name].splitlines()
                  if line.startswith('CONFIG_') and '=' in line)
    assert all(config[k] == 'y' for k in ('CONFIG_THREAD_INFO_IN_TASK', 'CONFIG_EJ',
        'CONFIG_OSAL_UDIF_THREAD', 'CONFIG_ARM64_4K_PAGES', 'CONFIG_PREEMPT', 'CONFIG_SMP'))
    assert config['CONFIG_HZ'] == '100' and config['CONFIG_MAX_USER_RT_PRIO'] == '160'
    assert 'void *____private;' in texts['include/linux/sched.h']
    head = texts['arch/arm64/kernel/head.S']
    assert 'adr_l\tx5, init_task' in head and 'msr\tsp_el0, x5' in head
    drv_header = texts['include/linux/udif/driver.h']
    assert 'UDIF_MODULE_INIT_CB init;' in drv_header
    assert 'int  udif_driver_register(UDIF_DRIVER **, UDIF_U32);' in drv_header
    drv_source = texts['drivers/udif/driver.c']
    assert 'ret = drv->ops->init(drv->data);' in drv_source
    assert 'kthread_create(udif_thread, drv[i],' in drv_source
    assert 'wake_up_process(tsk);' in drv_source
    assert 'wait_for_completion_timeout(&th.com, 5*60*HZ)' in drv_source
    modules, providers, kernel = h.prev.build()
    assert h.im.sha(kernel) == KERNEL_SHA
    K = h.prev.n.K
    uipc = modules['osal_uipc.ko']
    symbol = [x for x in uipc.syms.iter_symbols() if x.name == 'udif_uipc']
    assert len(symbol) == 1 and symbol[0]['st_size'] == 0x80
    data = uipc.section('.data')
    offset = uipc.address('udif_uipc') - data['base']
    ops = struct.unpack_from('<Q', data['data'], offset + 0x38)[0]
    cb_data = struct.unpack_from('<Q', data['data'], offset + 0x40)[0]
    callback = struct.unpack_from('<Q', data['data'], ops-data['base'])[0]
    assert callback == uipc.section('.init.text')['base'] and cb_data == 0
    callback_prefix = h.im.dump(kernel, 0x31a22c, 0x31a240, K)
    assert [x['asm'] for x in callback_prefix] == [
        'ldr x0, [x19, #0x38]', 'ldr x1, [x0]',
        'cbz x1, #0xffffff800839a24c', 'ldr x0, [x19, #0x40]', 'blr x1']
    calls = []
    for site, target, name in ((0x31a608, 0x3cf00, 'kthread_create_on_node'),
                              (0x31a5d8, 0x457a8, 'wake_up_process'),
                              (0x31a63c, 0x421250, 'wait_for_completion_timeout')):
        word = struct.unpack_from('<I', kernel, site)[0]
        assert word & 0xfc000000 == 0x94000000
        disp = word & 0x3ffffff
        if disp & (1 << 25):
            disp -= 1 << 26
        assert site + disp * 4 == target
        candidates = h.prev.audit.export_candidates(kernel, name)
        assert len(candidates) == 1 and int(candidates[0]['value'], 16) == K + target
        calls.append({'symbol': name, 'original_BL': hex(K+site),
            'decoded_target': hex(K+target), 'original_export_candidate': candidates[0]})
    boot = json.loads((h.STAGE / 'boot-context-audit.json').read_text())
    current = int(boot['original_startup_current_context'], 16)
    off = current - K
    # AArch64 source: 24-byte thread_info, vendor CONFIG_EJ private pointer,
    # then long state and stack pointer. This is a selected-layout crosscheck,
    # not proof that the 7.00 defconfig is the actual 7.02 build configuration.
    assert struct.unpack_from('<Q', kernel, off+0x28)[0] == K + 0x600000
    assert int(boot['initial_stack'], 16) == K + 0x600000 + 0x4000
    assert struct.unpack_from('<I', kernel, off+0x10)[0] == 1
    assert h.im.dump(kernel, 0x31a564, 0x31a568, K)[0]['asm'] == 'mov w1, #0x5a'
    assert h.im.dump(kernel, 0x31a638, 0x31a63c, K)[0]['asm'] == 'mov x1, #0x7530'
    result = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'SELECTED_VENDOR_SOURCE_AND_ORIGINAL_BINARY_RUNTIME_ABI_CROSSCHECK',
        'source_script_sha256': h.im.sha(h.STAGE.joinpath('audit_vendor_source.py').read_bytes()),
        'official_model_page': receipt['official_model_page'], 'source_label': 'FX3 7.00',
        'source_kernel_version': '4.9.337', 'original_binary': 'FX3 7.02 pinned kernel Image',
        'whole_source_build_or_7_02_exact_source_match_verified': False,
        'archive_sha256': ARCHIVE_SHA, 'kernel_sha256': KERNEL_SHA, 'source_members': rows,
        'selected_excerpts': [excerpt(NAMES[1], 10, 17), excerpt(NAMES[2], 34, 50),
            excerpt('include/linux/sched.h', 1495, 1511), excerpt('arch/arm64/kernel/head.S', 441, 475),
            excerpt('include/linux/udif/driver.h', 35, 70),
            excerpt('drivers/udif/driver.c', 192, 216), excerpt('drivers/udif/driver.c', 337, 386)],
        'reference_config': {k: config[k] for k in ('CONFIG_THREAD_INFO_IN_TASK', 'CONFIG_EJ',
            'CONFIG_OSAL_UDIF_THREAD', 'CONFIG_ARM64_4K_PAGES', 'CONFIG_PREEMPT', 'CONFIG_SMP',
            'CONFIG_HZ', 'CONFIG_MAX_USER_RT_PRIO')},
        'current_context_correlation': {'original_init_context_pointer': hex(current),
            'plus10_original_preempt_word': 1, 'vendor_private_slot_explains_stack_offset': '0x28',
            'original_stack_base': hex(K+0x600000), 'original_SP': boot['initial_stack'],
            'stack_bytes': 0x4000, 'native_prefix_cases': 2, 'actual_scheduled_client_context_observed': False},
        'driver_init_ABI': {'original_driver_symbol_bytes': 0x80, 'ops_field_offset': '0x38',
            'callback_data_field_offset': '0x40', 'original_callback_data_value': hex(cb_data),
            'first_ops_callback': hex(callback), 'actual_kernel_callback_prefix_not_executed': callback_prefix,
            'register_argument_is_driver_pointer_array': True,
            'init_callback_argument_is_driver_data_not_driver_object': True},
        'original_registration_services_not_executed': calls,
        'threaded_registration_correlation': {'original_priority_immediate': 90,
            'reference_config_160_minus70': 90, 'original_completion_timeout_jiffies': 30000,
            'reference_5min_times_HZ100': 30000, 'real_thread_completion_scheduler_or_timeout_execution': False},
        'reference_DTS_present': True, 'complete_BIONZ_ISP_sensor_HEVC_hardware_emulator_verified': False,
        'next_gate': 'Driver registration creates/wakes actual kernel threads and waits for completion. Initial task bytes or a lock return cannot replace Linux scheduling, allocator, driver callbacks or real device state.',
        'camera_operations_or_downloaded_source_execution': False, 'goal_complete': False,
    }
    h.im.write_json(out, result)
    print(json.dumps({'status': result['status'], 'source_kernel': '4.9.337',
        'selected_source_members': len(rows), 'original_kernel_service_calls_named': len(calls),
        'driver_bytes': 128, 'callback_data': 0, 'whole_7_02_source_match': False,
        'real_scheduler_or_camera_execution': False}))


if __name__ == '__main__':
    main()
