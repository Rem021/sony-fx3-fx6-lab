"""Final native-only rebuild after removing an analyzer-reported dead store.

The9-check sanitized unit's linked sources are unchanged, so it is not rerun.
"""
from pathlib import Path
from hashlib import sha256
import json,subprocess,plistlib
H=Path(__file__).resolve().parent
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
old=json.loads((H/'build-receipt-v5.json').read_text())
for name in ['stream.c','stream.h','unit.c','public_material.h','digest_vectors.h']:
    member=next(x for x in old['sources']if x['path']==name)
    assert sha256((H/name).read_bytes()).hexdigest()==member['sha256']
assert json.loads((H/'unit-receipt-v5.json').read_text())['returncode']==0
out=H/'artifacts-final';out.mkdir(mode=0o700,exist_ok=False)
command=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-dynamiclib',str(H/'stream.c'),str(H/'iokit_adapter.c'),'-framework','IOKit','-framework','CoreFoundation','-o',str(out/'fx3-generation-stream.dylib')]
p=subprocess.run(command,capture_output=True,text=True)
assert p.returncode==0,p.stderr
analyze=['/usr/bin/xcrun','clang','--analyze','-std=c11','-Wno-deprecated-declarations',str(H/'iokit_adapter.c'),'-o',str(H/'iokit_adapter-analysis-final.plist')]
a=subprocess.run(analyze,capture_output=True,text=True)
assert a.returncode==0 and not a.stderr,a.stderr
for name in ['stream-analysis.plist','iokit_adapter-analysis-final.plist']:
    assert plistlib.loads((H/name).read_bytes())['diagnostics']==[]
report=dict(native_argv=command,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,
    analyzer_argv=analyze,analyzer_returncode=a.returncode,analyzer_diagnostics=0,
    native_path=str(out/'fx3-generation-stream.dylib'),native_sha256=sha256((out/'fx3-generation-stream.dylib').read_bytes()).hexdigest(),
    native_library_executed=False,unit_receipt='unit-receipt-v5.json',unit_linked_sources_unchanged=True,
    source_hashes={x.name:sha256(x.read_bytes()).hexdigest()for x in sorted(H.iterdir())if x.suffix in ['.c','.h']},
    new_device_cache_root_or_USB_operations=0)
with(H/'final-build-receipt.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(status='NATIVE_BUILD_AND_ANALYZER_PASS_UNIT9_REUSED_WITH_IDENTICAL_LINKED_SOURCES',native_sha256=report['native_sha256'],native_executed=False)))
