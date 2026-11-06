"""Build host-only root candidate and unprivileged executable fixtures.

No artifact is executed here. No owner, IOKit/USB backend or firmware linked.
"""
from pathlib import Path
from hashlib import sha256
import json,plistlib,subprocess
HERE=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
out=HERE/'artifacts';out.mkdir(mode=0o700,exist_ok=False);(HERE/'runs').mkdir(mode=0o700,exist_ok=True)
base=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-fvisibility=hidden']
sources=['host_trial.c','host_transport.c','helper_hello.c','entry_support.c','owner_ipc.c','frame_io.c','global_guard.c','host_login.c']
deps=['-framework','Security','-lbsm']
commands={
 'root_host':base+[str(HERE/n) for n in sources]+deps+['-o',str(out/'root-host-helper')],
 'fixture':base+['-DHOST_FIXTURE','-DFX3_ENTRY_FIXTURE','-fsanitize=address,undefined','-fno-sanitize-recover=all']+[str(HERE/n) for n in sources]+deps+['-o',str(out/'host-fixture-helper')],
 'ipc':base+['-dynamiclib','-DFX3_ENTRY_FIXTURE',str(HERE/'owner_ipc.c'),str(HERE/'entry_support.c'),'-o',str(out/'entry-ipc.dylib')],
}
builds={}
for name,argv in commands.items():
 r=subprocess.run(argv,capture_output=True,text=True);builds[name]={'argv':argv,'returncode':r.returncode,'stderr':r.stderr}
 if r.returncode:
  with (HERE/'build-failure.json').open('x') as f:json.dump(builds,f,indent=2)
  print(r.stderr);raise SystemExit(r.returncode)
 p=Path(argv[-1]);linked=subprocess.check_output(['/usr/bin/otool','-L',str(p)],text=True);symbols=subprocess.check_output(['/usr/bin/nm','-u',str(p)],text=True)
 assert 'IOKit.framework' not in linked and 'libusb' not in linked and 'usbmux' not in linked
 assert not any(x in symbols for x in ('_IOService','_IORegistry','_IOCreatePlugIn','_IOUSB','_libusb_','_IOConnect'))
 builds[name].update(path=str(p),sha256=sha256(p.read_bytes()).hexdigest(),dependencies=linked,undefined_symbols=symbols)
files=[p for p in sorted(HERE.iterdir()) if p.suffix in ('.c','.h')]
report={'schema':1,'root_candidate_executed':False,'specific_admin_approval':False,'camera_or_root_operations':0,
        'native_build_released':False,'native_helper_executed':False,'host_only':True,'root_uid_required_by_root_candidate':True,
        'owner_USB_firmware_backends_linked':False,'builds':builds,
        'sources':[{'path':p.name,'sha256':sha256(p.read_bytes()).hexdigest()} for p in files]}
with (HERE/'build-receipt.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'builds':list(builds),'root_executed':False,'IOKit_or_firmware_linked':False}))
