#!/usr/bin/env python3
"""Capture original ARM64 reader functions as data; no vendor code execution."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

HERE = Path(__file__).resolve().parent
TASK = HERE.parent


def main():
    assert not (HERE / 'reader-contract.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    helper = TASK / 'donor-20261028/macho_static.py'
    seal = json.loads((helper.parent / 'final-receipt.json').read_text())
    pin = next(r['sha256'] for r in seal['files'] if r['path'] == helper.name)
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == pin
    spec = importlib.util.spec_from_file_location('own_readonly_macho', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inventory = json.loads((HERE / 'payload-inventory.json').read_text())
    libraries = [r for p in inventory['packages'] for r in p['entries'] if r['type']=='file' and Path(r['path']).name=='libAxsMemContorlLib.dylib']
    assert len(libraries) == 2
    for library in libraries:
        assert hashlib.sha256((HERE / library['saved_path']).read_bytes()).hexdigest() == library['sha256']
    selected_library = next(r for r in libraries if r['saved_path'].startswith('payload-files/AXSMDriveUtility.pkg/'))
    path = HERE / selected_library['saved_path']
    image = module.MachO(path)
    selectors = ['checkFileMode','CheckNewMemFirmware','ReadDriveFirmwareFile','R5FirmwareUpdate','MemFirmwareUpdateEx']
    selected = [s for s in image.symbols if not s['kind'] & 0xe0 and s['kind'] & 0x0e == 0x0e and s['va'] and s['section'] and any(t in s['name'] for t in selectors)]
    assert len(selected) == 5
    labels = {s['va']:s['name'] for s in image.symbols if not s['kind'] & 0xe0 and s['va'] and s['section']}
    labels.update(image.stubs)
    output = HERE / 'reader-spans'
    output.mkdir(exist_ok=False)
    rows = []
    decoder = Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    for symbol in sorted(selected,key=lambda s:s['va']):
        address = symbol['va']
        code = image.function(address)
        assert len(code)%4 == 0
        binary = output / (hex(address)+'.bin')
        text = output / (hex(address)+'.txt')
        binary.write_bytes(code)
        lines, calls = [], []
        for ins in decoder.disasm(code,address):
            line = f'{ins.address:08x} {ins.mnemonic:9} {ins.op_str}'
            if ins.mnemonic == 'bl':
                target = int(ins.op_str.removeprefix('#'),16)
                label = labels.get(target)
                if label:
                    line += ' ; '+label
                calls.append({'VA':hex(ins.address),'target_VA':hex(target),'symbol':label})
            lines.append(line)
        assert len(lines)*4 == len(code)
        text.write_text(symbol['name']+'\n'+'\n'.join(lines)+'\n')
        rows.append({'name':symbol['name'],'VA':hex(address),'bytes':len(code),'sha256':hashlib.sha256(code).hexdigest(),
                     'raw':str(binary.relative_to(HERE)),'listing':str(text.relative_to(HERE)),'direct_calls':calls})
    cstrings = []
    for section in image.sections:
        if section['name'] != '__cstring':
            continue
        raw = image.read(section['va'],section['bytes'])
        position = 0
        for item in raw.split(b'\0'):
            if any(term in item.lower() for term in [b'firmware',b'update',b'.ascr',b'axs-r',b'axs-a',b'decrypt',b'binarypackproperty',b'data23213']):
                cstrings.append({'VA':hex(section['va']+position),'text':item[:240].decode('utf8','replace')})
            position += len(item)+1
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_copies':libraries,'same_named_library_whole_files_equal':libraries[0]['sha256']==libraries[1]['sha256'],
              'selected_source':selected_library['saved_path'],'source_sha256':selected_library['sha256'],'ARM64_slice_offset':image.slice_offset,
              'ARM64_slice_bytes':len(image.b),'ARM64_slice_sha256':hashlib.sha256(image.b).hexdigest(),
              'own_MachO_helper':str(helper.relative_to(TASK)),'own_helper_sha256':pin,
              'function_boundaries':'Original LC_FUNCTION_STARTS, not arbitrary fixed instruction windows',
              'functions':rows,'selected_original_cstrings':cstrings,
              'vendor_code_executed':False,'device_actions':0,'modified_firmware_created':False}
    (HERE / 'reader-contract.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'functions':[{'VA':r['VA'],'bytes':r['bytes'],'name':r['name']} for r in rows],'selected_cstrings':cstrings[:14]},ensure_ascii=False))


if __name__ == '__main__':
    main()
