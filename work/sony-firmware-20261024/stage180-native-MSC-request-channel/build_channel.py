"""Compile native dispatcher object only and an IOKit-free process fixture."""
from pathlib import Path
from hashlib import sha256
import json
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'stage179-bounded-IOKit-wire'


def main():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    manifest=PRIOR/'final-receipt.json'
    assert sha256(manifest.read_bytes()).hexdigest()=='cfc2b5495d0e4cca11e6dc9d700104f3d25b23ea99ff57a990220fe1e8e3e3d8'
    for name in ('iokit_wire.h','iokit_wire.c','fake_iokit.c'):
        path=PRIOR/name
        rec=next(x for x in json.loads(manifest.read_text())['files'] if x['path'].endswith('/stage179-bounded-IOKit-wire/'+name))
        assert sha256(path.read_bytes()).hexdigest()==rec['sha256']
    out=HERE/'artifacts-v6';out.mkdir(exist_ok=False)
    flags=['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
    commands={'native_object':flags+['-c',str(HERE/'native_session.c'),'-o',str(out/'native-session.o')],
              'process_fixture':flags+['-DFX3_IOKIT_WIRE_FIXTURE',str(HERE/'native_session.c'),str(HERE/'process_fixture.c'),
                                       str(PRIOR/'iokit_wire.c'),str(PRIOR/'fake_iokit.c'),'-o',str(out/'session-process-fixture')]}
    report={}
    for key,argv in commands.items():
        r=subprocess.run(argv,capture_output=True,text=True)
        if r.returncode:
            with (HERE/(key+'-compile-failure.json')).open('x') as f:json.dump({'argv':argv,'returncode':r.returncode,'stderr':r.stderr},f,indent=2)
            r.check_returncode()
        path=Path(argv[-1]);rec={'argv':argv,'sha256':sha256(path.read_bytes()).hexdigest(),'stderr':r.stderr}
        if key=='process_fixture':
            rec['dependencies']=subprocess.check_output(['otool','-L',str(path)],text=True)
            assert 'IOKit' not in rec['dependencies'] and 'libusb' not in rec['dependencies'] and 'CoreFoundation' not in rec['dependencies']
        report[key]=rec
    report.update(native_object_linked_or_executed=False,new_root_or_device_operations=0,
                  sources={n:sha256((HERE/n).read_bytes()).hexdigest() for n in ('native_session.h','native_session.c','process_fixture.c')})
    with (HERE/'build-receipt-v6.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'compiled':list(report)[:2],'real_USB_or_root':0}))


if __name__=='__main__':main()
