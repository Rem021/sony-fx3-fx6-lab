#!/usr/bin/env python3
"""All writes confined to this permitted work directory; no donor/VM operations."""
import json
import subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(argv):
    result=subprocess.run(argv,cwd=HERE,text=True,capture_output=True,timeout=90)
    if result.returncode:
        raise RuntimeError(f'{argv}: {result.stdout}\n{result.stderr}')
    return result.stdout

def main():
    uuid=run(['diskutil','info','-plist','/Volumes/KAFU2T'])
    import plistlib
    assert plistlib.loads(uuid.encode())['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    evidence=json.loads(run(['python3','-B','inspect_contract.py']))
    (HERE/'contract-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    flags=['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic']
    run(flags+['-DFX6_READER_TEST_ALLOC','-fsanitize=address,undefined','-g',
        'typed_backup_reader.c','test_typed_backup_reader.c','-o','test_typed_backup_reader'])
    native=json.loads(run(['./test_typed_backup_reader']))
    run(flags+['-shared','-fPIC','typed_backup_reader.c','-o','libtyped_backup_reader.dylib'])
    byof=json.loads(run(['python3','-B','test_byof_reader.py']))
    report={'status':'PASS','volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B',
        'host_sanitizers':['address','undefined'],'native_checks':native,
        'byof_checks':byof,'binding_status':evidence['status'],
        'excluded':['VM','QMP','GDB','physical camera','native Sony API execution',
            'shared source mutations','donor mutations','Git mutations'],
        'limitation':'Helper statuses deliberately do not claim Sony remote return semantics.'}
    (HERE/'test-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
