"""Build new native candidate; execute ONLY local fake-object tests elsewhere."""
from pathlib import Path
from hashlib import sha256
import json, plistlib, subprocess
HERE=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert '#define FX3_NATIVE_RELEASED 0' in (HERE/'entry_target.h').read_text()
out=HERE/'artifacts-v2';out.mkdir(mode=0o700,exist_ok=False);(HERE/'runs').mkdir(mode=0o700,exist_ok=True)
common=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
base=[str(HERE/n) for n in ['owner_core.c','owner_ipc.c','entry_support.c','owner_entry_main.c','owner_channel.c','iokit_wire.c','native_session.c','global_guard.c','frame_io.c']]
commands={
 'fixture':common+['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DFX3_ENTRY_FIXTURE','-DFX3_OWNER_CHANNEL_FIXTURE','-DFX3_IOKIT_WIRE_FIXTURE',*base,str(HERE/'owner_fixture.c'),str(HERE/'fake_iokit.c'),'-o',str(out/'owner-fixture-helper')],
 'native':common+[*base,str(HERE/'owner_iokit.c'),str(HERE/'host_login.c'),'-framework','Security','-lbsm','-framework','IOKit','-framework','CoreFoundation','-framework','DiskArbitration','-o',str(out/'owner-native-helper')],
 'ipc':common+['-dynamiclib','-DFX3_ENTRY_FIXTURE',str(HERE/'owner_ipc.c'),str(HERE/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')],
}
results={}
for name,argv in commands.items():
 r=subprocess.run(argv,capture_output=True,text=True)
 results[name]={'argv':argv,'returncode':r.returncode,'stderr':r.stderr}
 if r.returncode:
  with (HERE/'build-v2-failure.json').open('x') as f:json.dump(results,f,indent=2)
  print(r.stderr);raise SystemExit(r.returncode)
 path=Path(argv[-1]);deps=subprocess.check_output(['/usr/bin/otool','-L',str(path)],text=True)
 if name!='native':assert 'IOKit.framework' not in deps and 'libusb' not in deps
 results[name].update(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),dependencies=deps)
sources=[p for p in sorted(HERE.iterdir()) if p.suffix in ('.c','.h')]
report={'schema':1,'owner_ABI':4,'entry_schema':3,'native_build_released':False,'native_helper_executed':False,'administrator_or_camera_operations':0,
        'SDK':subprocess.check_output(['/usr/bin/xcrun','--show-sdk-path'],text=True).strip(),'builds':results,
        'sources':[{'path':p.name,'sha256':sha256(p.read_bytes()).hexdigest()} for p in sources]}
with (HERE/'build-receipt-v2.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'builds':list(results),'fixture_sanitizers':['address','undefined'],'native_released':False,'native_executed':False}))
