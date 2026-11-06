#!/usr/bin/env python3
"""Build both ABI2 candidates; inspect real dylib without loading it."""
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
    common=['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-fvisibility=hidden','-dynamiclib',
        str(HERE/'owner_core.c'),str(HERE/'owner_ipc.c')]
    fixture_argv=common+[str(HERE/'owner_fixture.c'),'-o',str(out/'owner-fixture.dylib')]
    native_argv=common+['-Wno-deprecated-declarations',str(HERE/'owner_iokit.c'),'-framework','IOKit',
        '-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'owner-iokit.dylib')]
    builds={}
    for label,argv in [('fixture',fixture_argv),('native',native_argv)]:
        result=subprocess.run(argv,capture_output=True,text=True,check=True)
        path=out/('owner-'+('fixture' if label=='fixture' else 'iokit')+'.dylib')
        dependencies=subprocess.check_output(['otool','-L',str(path)],text=True)
        if label=='fixture':assert 'IOKit' not in dependencies and 'libusb' not in dependencies
        builds[label]={'path':path.relative_to(HERE).as_posix(),'bytes':path.stat().st_size,'sha256':sha256(path.read_bytes()).hexdigest(),
            'compile_argv':argv,'compiler_stderr':result.stderr,'dependencies':dependencies,
            'symbols':subprocess.check_output(['nm','-gU',str(path)],text=True)}
    names=['owner_trial.h','owner_core.c','owner_ipc.c','owner_iokit.c','owner_fixture.c','owner_binding.py',
        'shared_job.py','owner_worker.py','owner_supervisor.py']
    record={'ABI':2,**builds,'sources':[{'path':n,'sha256':sha256((HERE/n).read_bytes()).hexdigest()} for n in names],
        'native_candidate_loaded':False,'new_device_operations':0,
        'sdk':subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip()}
    with (HERE/'build-receipt.json').open('x') as handle:json.dump(record,handle,indent=2);handle.write('\n')
    (HERE/'build-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'fixture_sha256':builds['fixture']['sha256'],'native_sha256':builds['native']['sha256'],'real_native_loaded':False}))


if __name__=='__main__':main()
