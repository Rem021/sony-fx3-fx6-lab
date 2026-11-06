#!/usr/bin/env python3
"""Fresh cached-only Windows handoff; original source bytes stay pinned."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage64-osal-offline-link'))
import link_modules as prev
im=prev.im
WINDOWS_PROJECT=r'C:\Users\owo\Documents\Codex\2026-10-16\rea-2'
WINDOWS_OUTPUT=r'outputs\fx3-cache-associations-20261026T144834Z'
PINS={'Fx3CachedAssociations.cs':'f14e6907e0e1077b3d92b38764c9aa66014563a781b4b732d8339bd4bcf0be2d',
      'Review-Fx3Msc.ps1':'7e9df2455522aede99c7dc32d987ae1421d1ea2739701089e474f3b2680e19c0'}


def main():
    im.volume();out=STAGE/'windows-cache-handoff';assert not out.exists();out.mkdir()
    old=BASE/'stage12-prototype/msc-probe/windows-cache-handoff'
    for name,digest in PINS.items():
        raw=(old/name).read_bytes();assert im.sha(raw)==digest
        with (out/name).open('xb') as stream:stream.write(raw)
    text=(old/'TASK.txt').read_text()
    text=text.replace('fx3-cache-associations-handoff-20261025T170645Z','fx3-cache-associations-20261026T144834Z')
    text=text.replace('- This is a later handoff package. It has NOT been dispatched or executed.',
      '- This is a fresh stage65 package. At preparation time it has NOT been transferred or executed.')
    text=text.replace('- Current UU server/device is unavailable; the Mac coordinator must not dispatch\n  or run this package until that external condition changes.',
      '- User has restored UU and permits the main display while the Windows computer is unused.\n  Verify the intended host/project again; this does not expand camera authorization.')
    text+='\nStage65 clarification\n- This package manifest uses ordinary single Windows path separators in its parsed string values.\n- The two source files are byte-identical to the reviewed stage12 metadata-only sources.\n- Current user authorization permits the main display for this task; no camera interface or active query is authorized.\n'
    with (out/'TASK.txt').open('xb') as stream:stream.write(text.replace('\n','\r\n').encode())
    rows=[]
    for name in ('Review-Fx3Msc.ps1','Fx3CachedAssociations.cs','TASK.txt'):
        raw=(out/name).read_bytes()
        rows.append({'package_relative_path':name,'windows_project_relative_path':WINDOWS_OUTPUT+'\\'+name,
          'bytes':len(raw),'sha256':im.sha(raw)})
    manifest={'schema':'fx3-windows-cached-only-handoff/2','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'state_at_creation':'PREPARED_NOT_TRANSFERRED_NOT_EXECUTED','windows_project_root':WINDOWS_PROJECT,
      'windows_new_output_project_relative_path':WINDOWS_OUTPUT,'package_file_count':4,
      'allowed_files':['Review-Fx3Msc.ps1','Fx3CachedAssociations.cs','TASK.txt','sha256-manifest.json'],
      'files':rows,'active_source_included':False,'current_scope':'cached PnP only',
      'Windows_compile_runtime_device_access_or_hardware_acceptance':False}
    im.write_json(out/'sha256-manifest.json',manifest)
    assert set(x.name for x in out.iterdir())==set(manifest['allowed_files'])
    assert '\\\\' not in WINDOWS_PROJECT and '\\\\' not in WINDOWS_OUTPUT
    im.write_json(STAGE/'handoff-preparation.json',{'created_utc':manifest['created_utc'],
      'package':str(out.relative_to(ROOT)),'windows_output':WINDOWS_PROJECT+'\\'+WINDOWS_OUTPUT,
      'manifest_sha256':im.sha((out/'sha256-manifest.json').read_bytes()),
      'four_file_hashes':{x.name:im.sha(x.read_bytes()) for x in out.iterdir()},
      'two_original_source_hashes_unchanged':True,
      'old_manifest_literal_double_separators_replaced_in_fresh_manifest_not_overwritten':True,
      'camera_interface_auth_modes_drivers_files_modules_WBI_flash':False})
    print(json.dumps({'package':str(out),'manifest_sha256':im.sha((out/'sha256-manifest.json').read_bytes()),
      'windows_output':WINDOWS_PROJECT+'\\'+WINDOWS_OUTPUT}))


if __name__=='__main__':main()
