#!/usr/bin/env python3
"""Reproducible permitted binding-only deltas from frozen r30, no runner execution."""
from pathlib import Path
import hashlib,json,difflib
O=Path(__file__).resolve().parent;S=O.parent/'r30-startup-observation-candidate'
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def put(name,s):
 old=(S/name).read_text();(O/name).write_text(s);return ''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='r30/'+name,tofile='r37/'+name))
diffs=[]
n='run_trial_r24_review_snapshot.py';s=(S/n).read_text();s=replace(s,'import argparse','from r35_package_selection import PACKAGE as R35_PACKAGE, CANDIDATE_SHA as R35_MANIFEST_SHA, LABEL as R35_LABEL, options as r35_options, verify_package as verify_r35_package\nimport argparse')
s=replace(s,'    ns = ap.parse_args()','    ap.add_argument("--r35-diagnostic-package", action="store_true", help="仅另行授权时选择固定r36包；须snapshot-tail/N64")\n    ns = ap.parse_args()\n    try:r35_options(ns)\n    except ValueError as e:ap.error(str(e))')
s=replace(s,"    selected_root = (fixed_slot_guests/f'guest-N{ns.gate_publish_interval}'", "    selected_root = (R35_PACKAGE if ns.r35_diagnostic_package else\n                     fixed_slot_guests/f'guest-N{ns.gate_publish_interval}'")
s=replace(s,"    ns.label = (f'v25gate-n{ns.gate_publish_interval}-r17'", "    ns.label = (R35_LABEL if ns.r35_diagnostic_package else\n                f'v25gate-n{ns.gate_publish_interval}-r17'")
s=replace(s,'    vol = plistlib.loads', '    if ns.r35_diagnostic_package:r35_selection_receipt=verify_r35_package(DATA_ROOT)\n    vol = plistlib.loads')
s=replace(s,'    if digest(candidate_path) != pinned_manifest_sha:', '    if ns.r35_diagnostic_package:pinned_manifest_sha = R35_MANIFEST_SHA\n    if digest(candidate_path) != pinned_manifest_sha:')
s=replace(s,"'web_rejection_receipt.py']:", "'web_rejection_receipt.py'] + (['r35_package_selection.py'] if ns.r35_diagnostic_package else []):")
s=replace(s,"    (run / 'command.json').write_text", "    if ns.r35_diagnostic_package:command['r35_diagnostic_selection']=r35_selection_receipt\n    (run / 'command.json').write_text");diffs.append(put(n,s))
n='prepare_run.py';s=(S/n).read_text();s=replace(s,'import argparse,hashlib', 'from r35_package_selection import output_root,PROFILE\nimport argparse,hashlib');s=replace(s,"out=Path(a.run_dir).resolve();assert", "raw=Path(a.run_dir);out=output_root(raw);assert");s=replace(s,"cfg={'session'", "cfg={'candidate_source_root':str(ROOT),'runner_profile':PROFILE,'session'");s=replace(s,"files=[ROOT/'startup_observation.py'", "files=[ROOT/'r35_package_selection.py',ROOT/'startup_observation.py'")
s=replace(s,"put('LOCAL-SOURCE-FREEZE.json',{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()})", "put('LOCAL-SOURCE-FREEZE.json',{str(ROOT/f):h for f,h in json.loads((ROOT/'SOURCE-FREEZE.json').read_text()).items()})");diffs.append(put(n,s))
n='runtime-wrapper/common.py';s=(S/n).read_text();s=replace(s,'SOURCE=Path(__file__).resolve().parent','SOURCE=Path(__file__).resolve().parent\nimport sys\nsys.path.insert(0,str(SOURCE.parent))\nfrom r35_package_selection import output_root,PROFILE\n')
s=replace(s,"HERE=Path(os.environ['FX3_NAV_RUN_DIR']).resolve()", "HERE=output_root(Path(os.environ['FX3_NAV_RUN_DIR']))")
s=replace(s,"assert FROZEN.resolve()", "assert CFG['candidate_source_root']==str(SOURCE.parent) and CFG['runner_profile']==PROFILE\n_expected_freeze={str(SOURCE.parent/f):h for f,h in json.loads((SOURCE.parent/'SOURCE-FREEZE.json').read_text()).items()}\nassert json.loads((HERE/'LOCAL-SOURCE-FREEZE.json').read_text())==_expected_freeze\nassert FROZEN.resolve()");diffs.append(put(n,s))
n='runtime-wrapper/launch_prepare.py';s=(S/n).read_text();s=replace(s,"'--pre-input-snapshot-step','2']", "'--pre-input-snapshot-step','2','--r35-diagnostic-package']");diffs.append(put(n,s))
n='runtime-wrapper/preflight.py';s=(S/n).read_text();s=replace(s,"group('r30_local_core'", "group('r37_local_core'")
s=replace(s," write(name,{'groups':groups", " from r35_package_selection import verify_package\n selection=verify_package(HERE)\n write('R35-PACKAGE-SELECTION.json',selection)\n write(name,{'groups':groups")
s=s.replace("run_name='r30_import_only'", "run_name='r37_import_only'").replace("'r30-import-only'", "'r37-import-only'")
s=replace(s,"g=runpy.run_path", "def audit(event,args):\n if event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','socket.__new__'):raise RuntimeError('forbidden import side effect: '+event)\nsys.addaudithook(audit)\ng=runpy.run_path")
s=replace(s,"mods={name", "mods={name")
s=replace(s,"assert g['ACTIVE_GUARD'] is None", "assert Path(sys.modules['r35_package_selection'].__file__).resolve()==r/'r35_package_selection.py'\nassert g['ACTIVE_GUARD'] is None")
diffs.append(put(n,s))
(O/'r30-to-r37.diff').write_text(''.join(diffs))
# Core has all original core paths plus selector; adapter's source-freeze pin is
# derived only AFTER core hash, avoiding a self-referential hash.
core={n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in json.loads((S/'CORE-SOURCE-FREEZE.json').read_text())};core['r35_package_selection.py']=hashlib.sha256((O/'r35_package_selection.py').read_bytes()).hexdigest();(O/'CORE-SOURCE-FREEZE.json').write_text(json.dumps(core,indent=2)+'\n')
n='return-tools/return_adapter.py';s=(S/n).read_text();old="CORE_FREEZE_SHA='3591a3fcbb79c2b1617ba47f4fa4de5b79f2057f717198393e433156f69dc5e9'";s=replace(s,old,"CORE_FREEZE_SHA='"+hashlib.sha256((O/'CORE-SOURCE-FREEZE.json').read_bytes()).hexdigest()+"'")
s=replace(s,"OPERATE=FROZEN/", "sys.path.insert(0,str(FROZEN))\nfrom r35_package_selection import output_root,PROFILE\nOPERATE=FROZEN/")
s=replace(s,"run=Path(a.run_dir).resolve();out=Path(a.output_dir)", "run=output_root(Path(a.run_dir));out=Path(a.output_dir)\n cfg=json.loads((run/'config.json').read_text())\n assert cfg['candidate_source_root']==str(FROZEN) and cfg['runner_profile']==PROFILE\n expected={str(FROZEN/f):h for f,h in json.loads((FROZEN/'SOURCE-FREEZE.json').read_text()).items()}\n assert json.loads((run/'LOCAL-SOURCE-FREEZE.json').read_text())==expected")
s=replace(s,"if out.exists() or not out.parent.is_dir()", "if not out.is_absolute() or out.exists() or not out.parent.is_dir()")
diffs.append(put(n,s));(O/'r30-to-r37.diff').write_text(''.join(diffs))
source={n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in json.loads((S/'SOURCE-FREEZE.json').read_text())};source['r35_package_selection.py']=hashlib.sha256((O/'r35_package_selection.py').read_bytes()).hexdigest();(O/'SOURCE-FREEZE.json').write_text(json.dumps(source,indent=2)+'\n');print('binding-only derived sources frozen',len(source))

# Include the sole new runtime module in the complete source delta.
with (O/'r30-to-r37.diff').open('a') as out:out.write(''.join(difflib.unified_diff([], (O/'r35_package_selection.py').read_text().splitlines(True),fromfile='/dev/null',tofile='r37/r35_package_selection.py')))
