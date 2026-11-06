"""Compile own fake-object executable and closed native candidate; run neither."""
from pathlib import Path
from hashlib import sha256
import subprocess,json,plistlib
H=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert '#define FX3_NATIVE_RELEASED 0' in (H/'entry_target.h').read_text()
out=H/'artifacts-current-port';out.mkdir(mode=0o700);(H/'runs').mkdir(mode=0o700,exist_ok=True)
base=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
shared=[str(H/n) for n in ['owner_core.c','owner_ipc.c','entry_support.c','owner_entry_main.c','owner_channel.c',
 'host_transport.c','iokit_wire.c','native_session.c','global_guard.c','frame_io.c','owner_receipt.c','helper_hello.c']]
commands={
 'fixture':base+['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DFX3_ENTRY_FIXTURE',
 '-DFX3_OWNER_CHANNEL_FIXTURE','-DFX3_IOKIT_WIRE_FIXTURE',*shared,str(H/'owner_fixture.c'),str(H/'fake_iokit.c'),'-o',str(out/'owner-fixture-helper')],
 'native':base+[*shared,str(H/'owner_iokit.c'),str(H/'host_login.c'),'-framework','Security','-lbsm',
 '-framework','IOKit','-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'owner-native-helper')],
 'ipc':base+['-dynamiclib','-DFX3_ENTRY_FIXTURE',str(H/'owner_ipc.c'),str(H/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')]}
results={}
for name,args in commands.items():
 result=subprocess.run(args,capture_output=True,text=True)
 results[name]=dict(argv=args,returncode=result.returncode,stderr=result.stderr)
 if result.returncode:
  with (H/'build-failure-current-port.json').open('x') as f:json.dump(results,f,indent=2)
  print(result.stderr);raise SystemExit(result.returncode)
 path=Path(args[-1]);deps=subprocess.check_output(['/usr/bin/otool','-L',str(path)],text=True)
 if name!='native':assert 'IOKit.framework' not in deps and 'libusb' not in deps
 results[name].update(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),dependencies=deps)
report=dict(schema=1,owner_ABI=4,entry_schema=3,native_build_released=False,native_helper_executed=False,
 administrator_or_camera_operations=0,builds=results,
 sources=[dict(path=p.name,sha256=sha256(p.read_bytes()).hexdigest()) for p in sorted(H.iterdir()) if p.suffix in ('.c','.h')])
with (H/'build-receipt-current-port.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(built=list(results),native_executed=False,device_operations=0)))
