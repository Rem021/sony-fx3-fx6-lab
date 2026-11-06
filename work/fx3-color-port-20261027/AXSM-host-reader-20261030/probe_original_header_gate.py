#!/usr/bin/env python3
"""Run seven original instructions on original file prefixes in isolated RAM."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE, UC_HOOK_MEM_INVALID
from unicorn.arm64_const import UC_ARM64_REG_SP, UC_ARM64_REG_X8, UC_ARM64_REG_X9

HERE = Path(__file__).resolve().parent


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    assert not (HERE / 'original-header-gate-results.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    source = json.loads((HERE / 'reader-contract.json').read_text())
    function = next(r for r in source['functions'] if 'ReadDriveFirmwareFile' in r['name'])
    raw = (HERE / function['raw']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == function['sha256']
    start, stop_match, stop_reject = 0x9e68, 0x9e84, 0x9f20
    code = raw[start-int(function['VA'],16):stop_match-int(function['VA'],16)]
    assert len(code) == 28
    (HERE / 'UPDATE-header-gate-original.bin').write_bytes(code)
    inventory = json.loads((HERE / 'payload-inventory.json').read_text())
    inputs = []
    firmware = next(p for p in inventory['packages'] if p['component']=='Firmware.pkg')
    for item in firmware['entries']:
        if item['type']=='file':
            inputs.append({'name':Path(item['path']).name,'path':HERE/item['saved_path'], 'sha256':item['sha256'],
                           'kind':'Embedded drive/card firmware from the same official utility', 'expected_stop':stop_match})
    previous = HERE.parent / 'AXS-R7-donor-loader-20261030'
    old = json.loads((previous / 'acquisition-current-etag-receipt.json').read_text())
    new = json.loads((previous / 'AXS601-local-verification.json').read_text())
    inputs.extend([
        {'name':'AXS-R7 V6.00','path':previous/old['extracted'][0]['path'],'sha256':old['extracted'][0]['sha256'],'kind':'AXS-R7 recorder original','expected_stop':stop_reject},
        {'name':'AXS-R7 V6.01','path':previous/new['firmware_path'],'sha256':new['firmware_sha256'],'kind':'AXS-R7 recorder original','expected_stop':stop_reject},
        {'name':'VENICE V2.01 type3 inner','path':HERE.parent/'donor-loader-20261029/outer-members/VENICE/DATA23213',
         'sha256':'498d047ca2f6f11d54c502a399e2c5a9f4740e6fae4913eba1aaaf486349c785','kind':'Actual VENICE private inner original','expected_stop':stop_reject},
    ])
    assert len(inputs)==10
    prefix_dir = HERE/'gate-input-prefixes'
    prefix_dir.mkdir(exist_ok=False)
    results = []
    for index,item in enumerate(inputs):
        path = item['path']
        assert file_hash(path) == item['sha256']
        with path.open('rb') as stream:
            prefix=stream.read(512)
        assert len(prefix)==512
        saved=prefix_dir/(str(index).zfill(2)+'.bin')
        saved.write_bytes(prefix)
        guest=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        guest.mem_map(0x9000,4096,UC_PROT_READ|UC_PROT_WRITE|UC_PROT_EXEC)
        guest.mem_write(start,code)
        guest.mem_protect(0x9000,4096,UC_PROT_READ|UC_PROT_EXEC)
        stack=0x200000
        guest.mem_map(stack,4096,UC_PROT_READ|UC_PROT_WRITE)
        guest.mem_write(stack+0x48,prefix)
        guest.mem_protect(stack,4096,UC_PROT_READ)
        guest.reg_write(UC_ARM64_REG_SP,stack)
        executed=[]
        state={}
        def on_code(uc,address,size,userdata):
            if address in [stop_match,stop_reject]:
                state['stop']=address
                uc.emu_stop()
                return
            assert start<=address<stop_match and address%4==0 and size==4
            executed.append(address)
        def on_invalid(uc,access,address,size,value,userdata):
            raise AssertionError(('Undeclared guest memory access',access,hex(address),size))
        guest.hook_add(UC_HOOK_CODE,on_code)
        guest.hook_add(UC_HOOK_MEM_INVALID,on_invalid)
        guest.emu_start(start,0x10000,count=16)
        assert state.get('stop')==item['expected_stop'] and len(executed)==7
        assert guest.reg_read(UC_ARM64_REG_SP)==stack
        assert bytes(guest.mem_read(start,len(code)))==code
        assert bytes(guest.mem_read(stack+0x48,len(prefix)))==prefix
        results.append({'name':item['name'],'source':str(path.relative_to(HERE.parent)),'source_sha256':item['sha256'],'kind':item['kind'],
                        'prefix':str(saved.relative_to(HERE)),'prefix_sha256':hashlib.sha256(prefix).hexdigest(),
                        'original_gate_stop':hex(state['stop']),'matched_UPDATE_header_predicate':state['stop']==stop_match,
                        'instructions_executed':len(executed),'input_and_code_unchanged':True,
                        'comparison_input_word':hex(guest.reg_read(UC_ARM64_REG_X8)),
                        'literal_word_from_original_instructions':hex(guest.reg_read(UC_ARM64_REG_X9))})
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_library_sha256':source['source_sha256'],
            'original_gate_VA':hex(start),'original_gate_bytes':len(code),'original_gate_sha256':hashlib.sha256(code).hexdigest(),
            'cases':results,'original_instructions_executed':sum(r['instructions_executed'] for r in results),
            'scope':'Only the original literal header comparison after a declared 512-byte input precondition. No fopen/fread/malloc/crypto/driver calls, stubs, actual I/O, exception handling, full reader success or device admission.',
            'full_ReadDriveFirmwareFile_executed':False,'native_vendor_program_execution':False,'hardware_or_device_actions':0,
            'other_parser_paths_excluded':False,'VENICE_decoder_recovered':False,'modified_firmware_created':False}
    (HERE/'original-header-gate-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'original_instructions':result['original_instructions_executed'],
                      'UPDATE_header_matches':sum(r['matched_UPDATE_header_predicate'] for r in results),
                      'AXS_R7_and_VENICE_rejected_before_later_processing':3,'whole_reader_executed':False}))


if __name__=='__main__':
    main()
