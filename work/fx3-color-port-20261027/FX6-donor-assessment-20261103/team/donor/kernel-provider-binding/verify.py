#!/usr/bin/env python3
"""Dependency-free final receipt audit for pinned FX6 symbol and provider chain."""
from hashlib import sha256
import json

from kernel_symbols import HERE, KernelSymbols


def digest(path):return sha256(path.read_bytes()).hexdigest()


def main():
    recovery=json.loads((HERE/'symbol-recovery.json').read_text())
    symbols=json.loads((HERE/'symbol-verification.json').read_text())
    binding=json.loads((HERE/'binding-evidence.json').read_text())
    replay=json.loads((HERE/'wrapper-replay.json').read_text())
    x=KernelSymbols()
    assert recovery['kernel_sha256']==symbols['kernel_sha256']==binding['pins']['fx6_kernel']==sha256(x.raw).hexdigest()
    assert recovery['symbol_count']==symbols['symbols']==len(x.rows)==41294
    assert recovery['catalog_sha256']==digest(HERE/'fx6-kernel-symbol-catalog.json')
    assert symbols['export_entries']==6089 and symbols['guest_original_calls']==1007
    assert symbols['export_sha256']==digest(HERE/'export-crosscheck.json')
    assert len(json.loads((HERE/'export-crosscheck.json').read_text()))==6089
    assert x.tables['names']['file_offset']==0x4aad00
    assert x.tables['token_index']['file_offset']==0x522900
    assert x.tables['relative_base']['file_offset']==0x4aab00
    donor=HERE.parent;mac=HERE.parents[5]
    paths={'fx6_kernel':donor/'fat-files/nflasha3/vmlinux.bin',
           'fx6_av':donor/'fat-files/nflasha3/av-cam.bin',
           'fx6_im':donor/'nflasha15-files/bin/im.elf',
           'liro':donor/'nflasha15-files/kmod/liro.ko',
           'osal_uipc':donor/'nflasha15-files/kmod/osal_uipc.ko',
           'backup':donor/'nflasha15-files/kmod/backup.ko',
           'fx3_liro':mac/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/liro.ko',
           'fx3_osal_uipc':mac/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/osal_uipc.ko',
           'fx3_backup':mac/'work/sony-firmware-20261024/stage208-Backup-record-routing/originals/kmod/backup.ko'}
    assert set(paths)==set(binding['pins'])
    for key,pin in binding['pins'].items():
        assert digest(paths[key])==pin
    assert binding['liro']['provider_table_copy']['length']==0x698
    assert binding['liro']['provider_table_copy']['destination']=='*(loaded_AV_base+0x20)+0x48'
    slots=binding['liro']['slots']
    assert slots['0x3c0']['relocation']['symbol']=='.text'
    assert slots['0x3c0']['relocation']['addend']=='0xc28'
    assert slots['0x3e8']['relocation']['symbol']=='osal_free_msg'
    assert slots['0x4c0']['relocation']['symbol']=='Backup_nread'
    assert all(s['relocation']['type_number']==257 for s in slots.values())
    assert binding['fx3_liro_field_comparison']['same_three_relocation_target_symbols']
    assert binding['fx3_provider_function_comparison']['osal_receive_and_free_original_function_bytes_identical']
    assert not binding['fx3_provider_function_comparison']['backup_nread_original_function_bytes_identical']
    assert len(replay['cases'])==2 and not replay['natural_event_observed']
    for case in replay['cases']:
        assert not case['violations'] and case['return_pc']=='0x60000000'
        assert case['sp_and_callee_saved_preserved'] and case['output_fixture_untouched']
        assert len(case['original_pcs'])<replay['budget_per_case']
        assert [c['symbol'] for c in case['stub_calls']]==[
            'liro_disable_hook','osal_rcv_msg_tmo','liro_enable_hook']
        assert case['stub_calls'][1]['x0']=='0x2ae085a'
        assert case['return_w0']==hex(case['external_status_fixture']&0xffffffff)
    output={'status':'PASS','fixed_original_files_checked':len(binding['pins']),
            'fx6_symbols':41294,'independent_original_export_pairs':6089,
            'original_kernel_leaf_CPU_cases':1007,'original_LIRO_wrapper_CPU_cases':2,
            'bound_slots':{k:v['relocation']['symbol'] for k,v in slots.items()},
            'source_sha256':{name:digest(HERE/name) for name in
                ('kernel_symbols.py','recover_symbols.py','verify_symbols.py',
                 'analyze_binding.py','replay_wrapper.py','verify.py','prepare.sh')},
            'output_sha256':{name:digest(HERE/name) for name in
                ('fx6-kernel-symbol-catalog.json','symbol-recovery.json','export-crosscheck.json',
                 'symbol-verification.json','binding-evidence.json','wrapper-replay.json')},
            'scope':'original static symbols/ELF relocation and bounded isolated CPU only; no kernel module runtime addresses, actual Backup word/event, VM or device proof'}
    (HERE/'run-receipt.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':'PASS','original_files':len(binding['pins']),
                      'symbols':41294,'exports':6089,'CPU_cases':1009}))


if __name__=='__main__':main()
