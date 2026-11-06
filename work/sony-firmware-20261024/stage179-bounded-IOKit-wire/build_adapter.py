"""Compile native object only and a marked fake-vtable DSO. No USB execution."""
from pathlib import Path
from hashlib import sha256
import json
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent

def main():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    (HERE/'artifacts-v2').mkdir(exist_ok=False)
    common=['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
    commands={'native_object':common+['-c',str(HERE/'iokit_wire.c'),'-o',str(HERE/'artifacts-v2/iokit-wire-native.o')],
        'fixture':common+['-DFX3_IOKIT_WIRE_FIXTURE','-dynamiclib',str(HERE/'iokit_wire.c'),str(HERE/'fake_iokit.c'),'-o',str(HERE/'artifacts-v2/fake-iokit.dylib')]}
    receipt={}
    for label,argv in commands.items():
        result=subprocess.run(argv,check=True,capture_output=True,text=True);path=Path(argv[-1])
        receipt[label]={'argv':argv,'sha256':sha256(path.read_bytes()).hexdigest(),'compiler_stderr':result.stderr,
            'undefined_symbols':subprocess.check_output(['nm','-u',str(path)],text=True)}
        if label=='fixture':
            dependencies=subprocess.check_output(['otool','-L',str(path)],text=True)
            assert not any('IOKit' in l or 'libusb' in l or 'CoreFoundation' in l for l in dependencies.splitlines()[2:])
            receipt[label]['dependencies']=dependencies
    receipt['sources']=[{'path':n,'sha256':sha256((HERE/n).read_bytes()).hexdigest()} for n in ['iokit_wire.h','iokit_wire.c','fake_iokit.c']]
    receipt.update(native_object_linked_or_loaded=False,new_root_or_USB_operations=0)
    with (HERE/'build-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({'native_object_compiled_not_loaded':True,'fake_vtable_DSO_has_no_USB_library_dependency':True,'new_device_operations':0}))

if __name__=='__main__':main()
