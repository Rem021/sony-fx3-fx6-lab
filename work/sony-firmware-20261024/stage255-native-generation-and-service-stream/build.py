"""Compile actual IOKit adapter; execute only own unit binary without IOKit."""
from pathlib import Path
from hashlib import sha256
import json,subprocess,plistlib
H=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
out=H/'artifacts-v5';out.mkdir(mode=0o700,exist_ok=False)
base=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations']
commands={
    'native':base+['-dynamiclib',str(H/'stream.c'),str(H/'iokit_adapter.c'),'-framework','IOKit','-framework','CoreFoundation','-o',str(out/'fx3-generation-stream.dylib')],
    'unit':base+['-fsanitize=address,undefined','-fno-sanitize-recover=all',str(H/'stream.c'),str(H/'unit.c'),'-o',str(out/'stream-unit')],
}
builds={}
for name,command in commands.items():
    process=subprocess.run(command,capture_output=True,text=True)
    builds[name]=dict(argv=command,returncode=process.returncode,stdout=process.stdout,stderr=process.stderr)
    if process.returncode:
        failure=H/'build-failure-v5.json'
        with failure.open('x') as f:json.dump(builds,f,indent=2)
        print(process.stderr);raise SystemExit(process.returncode)
    path=Path(command[-1]);dependencies=subprocess.check_output(['/usr/bin/otool','-L',str(path)],text=True)
    if name=='unit':assert 'IOKit.framework' not in dependencies
    builds[name].update(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),dependencies=dependencies)
with(H/'build-receipt-v5.json').open('x')as f:json.dump(dict(builds=builds,sources=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())for p in sorted(H.iterdir())if p.suffix in ('.c','.h')],native_library_executed=False,USB_cache_or_admin_operations=0),f,indent=2);f.write('\n')
test=subprocess.run([str(out/'stream-unit')],capture_output=True,text=True)
with(H/'unit-receipt-v5.json').open('x')as f:json.dump(dict(argv=[str(out/'stream-unit')],returncode=test.returncode,stdout=test.stdout,stderr=test.stderr,sanitizers='address,undefined',IOKit_linked_or_executed=False,synthetic_callbacks_only=True),f,indent=2);f.write('\n')
print(json.dumps(dict(built=list(builds),unit_returncode=test.returncode,stdout=test.stdout,native_executed=False)))
raise SystemExit(test.returncode)
