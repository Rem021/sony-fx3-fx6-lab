#!/usr/bin/env python3
"""Build a private library and header-only layout probe; never load/init libusb."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json
import os
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'work/libusb-1.0.30'
BUILD=HERE/'work/native-build'
PREFIX=HERE/'artifacts/private-libusb'


def main():
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and v['WritableVolume']
    patch=json.loads((HERE/'private-source-patch.json').read_text())
    assert sha256((SOURCE/'libusb/os/darwin_usb.c').read_bytes()).hexdigest()==patch['patched_sha256']
    BUILD.mkdir(exist_ok=False)
    env=dict(os.environ);env['TMPDIR']=str(HERE/'work-tmp')
    commands=[
      [str(SOURCE/'configure'),'--prefix='+str(PREFIX),'--disable-static','--enable-shared',
       '--disable-examples-build','--disable-tests-build','--disable-log','CC=/usr/bin/clang'],
      ['/usr/bin/make','-j2'],['/usr/bin/make','install']]
    runs=[]
    for n,command in enumerate(commands):
        log=HERE/('build-step'+str(n)+'.log')
        with log.open('xb') as handle:
            result=subprocess.run(command,cwd=BUILD,env=env,stdout=handle,stderr=subprocess.STDOUT,timeout=240)
        runs.append({'argv':command,'returncode':result.returncode,'log':log.relative_to(ROOT).as_posix()})
        if result.returncode:
            print(log.read_text(errors='replace')[-6000:]);raise SystemExit(result.returncode)
    probe=HERE/'artifacts/abi-probe'
    command=['/usr/bin/clang','-std=c11','-Wall','-Wextra','-Werror','-I'+str(SOURCE/'libusb'),str(HERE/'abi_probe.c'),'-o',str(probe)]
    subprocess.run(command,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    layout=json.loads(subprocess.check_output([str(probe)],env=env,timeout=5))
    deps=subprocess.check_output(['/usr/bin/otool','-L',str(probe)],text=True)
    assert 'libusb' not in '\n'.join(deps.splitlines()[1:])
    library=PREFIX/'lib/libusb-1.0.0.dylib'
    assert library.is_file() and library.resolve().is_relative_to(HERE)
    symbols=subprocess.check_output(['/usr/bin/nm','-gU',str(library)],text=True)
    assert '_libusb_fx3_set_target' in symbols and '_libusb_init' in symbols
    receipt={'status':'BUILT_PRIVATE_DARWIN_LIBRARY_NOT_LOADED_OR_INITIALIZED',
        'created_utc':datetime.now(timezone.utc).isoformat(),'runs':runs,'probe_compile_argv':command,
        'probe_header_layout':layout,'probe_dependencies':deps,
        'library':{'path':library.relative_to(ROOT).as_posix(),'bytes':library.stat().st_size,
                   'sha256':sha256(library.read_bytes()).hexdigest()},
        'private_source_sha256':patch['patched_sha256'],'library_init_or_device_operations':0,
        'only_own_header_probe_executed_no_libusb_link':True,'no_global_driver_library_or_PATH_install':True}
    with (HERE/'native-build-receipt.json').open('x') as h:json.dump(receipt,h,ensure_ascii=False,indent=2);h.write('\n')
    print(json.dumps({'status':receipt['status'],'layout':layout,'library_bytes':library.stat().st_size,'device_operations':0}))


if __name__=='__main__':main()
