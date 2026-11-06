"""Build own fixed-permit candidate; execute only separate unprivileged tests."""
from pathlib import Path
from hashlib import sha256
import json,subprocess,plistlib
H=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
out=H/'artifacts';out.mkdir(mode=0o700);(H/'runs').mkdir(mode=0o700)
base=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
shared=[str(H/n) for n in ['owner_core.c','owner_ipc.c','entry_support.c','owner_entry_main.c','owner_channel.c','host_transport.c',
 'iokit_wire.c','native_session.c','global_guard.c','frame_io.c','owner_receipt.c','helper_hello.c','status_permit.c']]
commands={
 'fixture':base+['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DFX3_ENTRY_FIXTURE','-DFX3_OWNER_CHANNEL_FIXTURE','-DFX3_IOKIT_WIRE_FIXTURE',
 *shared,str(H/'owner_fixture.c'),str(H/'fake_iokit.c'),'-o',str(out/'owner-fixture-helper')],
 'native':base+[*shared,str(H/'owner_iokit.c'),str(H/'host_login.c'),'-framework','Security','-lbsm','-framework','IOKit','-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'owner-native-helper')],
 'ipc':base+['-dynamiclib','-DFX3_ENTRY_FIXTURE',str(H/'owner_ipc.c'),str(H/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')],
 'permit_test':base+['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DFX3_PERMIT_TEST',str(H/'status_permit.c'),str(H/'permit_unit.c'),'-o',str(out/'permit-unit')]}
builds={}
for name,args in commands.items():
 p=subprocess.run(args,capture_output=True,text=True);builds[name]=dict(argv=args,returncode=p.returncode,stderr=p.stderr)
 if p.returncode:
  with (H/'build-failure.json').open('x') as f:json.dump(builds,f,indent=2)
  print(p.stderr);raise SystemExit(p.returncode)
 path=Path(args[-1]);deps=subprocess.check_output(['/usr/bin/otool','-L',str(path)],text=True)
 if name!='native':assert 'IOKit.framework' not in deps
 builds[name].update(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),dependencies=deps)
report=dict(schema=1,native_build_released=False,native_helper_executed=False,
 native_requires_new_authority_and_root_private_fixed_permit=True,new_root_or_camera_operations=0,builds=builds,
 sources=[dict(path=p.name,sha256=sha256(p.read_bytes()).hexdigest()) for p in sorted(H.iterdir()) if p.suffix in ('.c','.h')])
with (H/'build-receipt.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(built=list(builds),native_executed=False,root_or_USB_operations=0)))
