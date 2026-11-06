#!/usr/bin/env python3
"""Compile native and fixture executables plus device-free IPC; never elevate."""
from pathlib import Path
from hashlib import sha256
import json
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent


def main():
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and v['WritableVolume']
    out=HERE/'artifacts';out.mkdir(exist_ok=False)
    (HERE/'runs').mkdir(mode=0o700,exist_ok=False)
    common=['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
    prefix='-DFX3_APPROVED_JOB_ROOT='+json.dumps(str(HERE/'runs')+'/')
    base=[str(HERE/n) for n in ['owner_core.c','owner_ipc.c','entry_support.c','owner_entry_main.c']]
    commands={
        'fixture':common+[prefix,'-DFX3_ENTRY_FIXTURE',*base,str(HERE/'owner_fixture.c'),'-o',str(out/'owner-fixture-helper')],
        'native':common+[prefix,*base,str(HERE/'owner_iokit.c'),'-framework','IOKit','-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'owner-native-helper')],
        'ipc':common+['-dynamiclib',str(HERE/'owner_ipc.c'),str(HERE/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')]}
    items={}
    for label,argv in commands.items():
        result=subprocess.run(argv,check=True,capture_output=True,text=True)
        path=Path(argv[-1]);deps=subprocess.check_output(['otool','-L',str(path)],text=True)
        if label!='native':assert 'IOKit' not in deps and 'libusb' not in deps
        items[label]={'path':path.relative_to(HERE).as_posix(),'sha256':sha256(path.read_bytes()).hexdigest(),
            'compile_argv':argv,'compiler_stderr':result.stderr,'dependencies':deps}
    script_argv=['osacompile','-o',str(out/'admin_launch.scpt'),str(HERE/'admin_launch.applescript')]
    subprocess.run(script_argv,check=True,capture_output=True,text=True)
    names=['owner_trial.h','owner_core.c','owner_iokit.c','owner_fixture.c','owner_ipc.c','owner_binding.py',
        'entry_shared.h','entry_support.c','owner_entry_main.c','admin_launch.applescript']
    receipt={'ABI':3,**items,'sources':[{'path':n,'sha256':sha256((HERE/n).read_bytes()).hexdigest()} for n in names],
        'applescript_compile_argv':script_argv,'applescript_compiled_not_executed':True,
        'native_helper_executed_or_IOKit_loaded':False,'administrator_prompt_requested':False,'new_device_operations':0}
    with (HERE/'helper-build-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    (HERE/'build-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'ABI':3,'artifacts_compiled':list(items),'native_helper_executed':False,'administrator_prompt_requested':False}))


if __name__=='__main__':main()
