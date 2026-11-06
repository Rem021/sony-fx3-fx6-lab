#!/usr/bin/env python3
"""Compile candidates and parse one admin source; never run native or elevate."""
from pathlib import Path
from hashlib import sha256
import json
import plistlib
import subprocess
import launch_policy as P

HERE=Path(__file__).resolve().parent


def main():
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and v['WritableVolume']
    out=HERE/'artifacts';out.mkdir(exist_ok=False);(HERE/'runs').mkdir(mode=0o700,exist_ok=False)
    constants={'FX3_GRANT_ID':P.GRANT_ID,'FX3_FIXED_JOB_DIR':str(P.JOB_DIR),'FX3_FIXED_FRAME':str(P.JOB_DIR/'shared.bin'),
        'FX3_ROOT_GRANT_DIR':str(P.ROOT_DIR),'FX3_INSTALLED_HELPER':str(P.ROOT_DIR/'helper'),
        'FX3_ROOT_ENTRY_LEASE':str(P.ROOT_DIR/'entry.once'),'FX3_FIXTURE_JOB_ROOT':str(HERE/'runs')+'/'}
    with (HERE/'entry_target.h').open('x') as f:
        for k,v in constants.items():f.write('#define '+k+' '+json.dumps(v)+'\n')
    common=['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
    base=[str(HERE/n) for n in ['owner_core.c','owner_ipc.c','entry_support.c','owner_entry_main.c']]
    commands={'fixture':common+['-DFX3_ENTRY_FIXTURE',*base,str(HERE/'owner_fixture.c'),'-o',str(out/'owner-fixture-helper')],
        'native':common+[*base,str(HERE/'owner_iokit.c'),'-framework','IOKit','-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'owner-native-helper')],
        'ipc':common+['-dynamiclib',str(HERE/'owner_ipc.c'),str(HERE/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')]}
    items={}
    for label,argv in commands.items():
        result=subprocess.run(argv,check=True,capture_output=True,text=True)
        path=Path(argv[-1]);deps=subprocess.check_output(['otool','-L',str(path)],text=True)
        if label!='native':assert 'IOKit' not in deps and 'libusb' not in deps
        items[label]={'path':path.relative_to(HERE).as_posix(),'sha256':sha256(path.read_bytes()).hexdigest(),
            'compile_argv':argv,'compiler_stderr':result.stderr,'dependencies':deps}
    names=['owner_trial.h','owner_core.c','owner_iokit.c','owner_fixture.c','owner_ipc.c','owner_binding.py','entry_shared.h',
        'entry_support.c','entry_target.h','owner_entry_main.c','entry_binding.py','launch_policy.py','cache_observer.py']
    receipt={'ABI':3,'entry_schema':2,'grant_id':P.GRANT_ID,**items,
        'sources':[{'path':n,'sha256':sha256((HERE/n).read_bytes()).hexdigest()} for n in names],
        'native_helper_executed_or_IOKit_loaded':False,'administrator_prompt_requested':False,'active_device_operations':0}
    with (HERE/'helper-build-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    script,body=P.native_applescript('00'*16)
    (HERE/'admin-source-example.applescript').write_text(script+'\n');(HERE/'root-bootstrap-example.sh').write_text(body)
    script_argv=['osacompile','-o',str(out/'admin-source-example.scpt'),str(HERE/'admin-source-example.applescript')]
    subprocess.run(script_argv,check=True,capture_output=True,text=True)
    (HERE/'build-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'ABI':3,'entry_schema':2,'artifacts':list(items),'native_or_admin_executed':False,'admin_source_parsed_only':True}))


if __name__=='__main__':main()
