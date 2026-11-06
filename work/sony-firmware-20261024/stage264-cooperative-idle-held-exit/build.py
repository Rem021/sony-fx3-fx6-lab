"""Build the unreleased native candidate; execute only unprivileged fixtures."""
from pathlib import Path
from hashlib import sha256
import json,plistlib,subprocess
H=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert '#define FX3_NATIVE_SERVICE_RELEASED 0' in (H/'service_profile.h').read_text()
assert '#define FX3_CONTROLLED_PORT_ASSOCIATION_RELEASED 0' in (H/'service_profile.h').read_text()
out=H/'artifacts'
base=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
shared=[str(H/n) for n in ['owner_core.c','owner_ipc.c','entry_support.c','owner_entry_main.c',
    'owner_channel.c','host_transport.c','iokit_wire.c','native_session.c','global_guard.c','frame_io.c',
    'owner_receipt.c','helper_hello.c','status_permit.c','stream.c','transition_identity.c',
    'descriptor_policy.c','flow_journal.c','service_flow.c','idle_held.c']]
commands={
    'fixture':base+['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DFX3_ENTRY_FIXTURE',
        '-DFX3_OWNER_CHANNEL_FIXTURE','-DFX3_IOKIT_WIRE_FIXTURE',*shared,str(H/'owner_fixture.c'),
        str(H/'fake_iokit.c'),str(H/'flow_fixture.c'),'-o',str(out/'service-fixture-helper')],
    'native':base+[*shared,str(H/'owner_iokit.c'),str(H/'iokit_adapter.c'),str(H/'port_anchor.c'),
        str(H/'host_login.c'),'-framework','Security','-lbsm','-framework','IOKit',
        '-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'service-native-closed')],
    'ipc':base+['-dynamiclib','-DFX3_ENTRY_FIXTURE',str(H/'owner_ipc.c'),str(H/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')]
}
builds={}
for name,cmd in commands.items():
    p=subprocess.run(cmd,capture_output=True,text=True)
    builds[name]=dict(argv=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    if p.returncode:
        (H/'build-failure.json').write_text(json.dumps(builds,indent=2)+'\n')
        print(p.stderr);raise SystemExit(p.returncode)
    binary=Path(cmd[-1]);deps=subprocess.check_output(['/usr/bin/otool','-L',str(binary)],text=True)
    if name!='native':assert 'IOKit.framework' not in deps
    builds[name].update(path=str(binary),sha256=sha256(binary.read_bytes()).hexdigest(),dependencies=deps)
sources=[dict(path=p.name,sha256=sha256(p.read_bytes()).hexdigest()) for p in sorted(H.iterdir())
         if p.suffix in ('.c','.h','.inc')]
with (H/'build-receipt.json').open('w') as f:
    json.dump(dict(builds=builds,sources=sources,native_build_released=False,
        native_helper_executed=False,new_root_or_USB_operations=0),f,indent=2);f.write('\n')
print(json.dumps(dict(status='CANDIDATE_BUILT_NATIVE_CLOSED',new_root_or_USB_operations=0)))
