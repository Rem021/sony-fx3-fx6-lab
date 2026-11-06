from pathlib import Path
import importlib.util,sys,hashlib,json,ast
O=Path(__file__).resolve().parents[1];D=O.parent;source=D/'v25-r21-recovery-integration/cpio_audit.py';candidate=D/'r36-fixed-slot-package/guest.cpio';baseline=Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio')
# Owning source inspected: only newc read_bytes/sha/stat arithmetic, no subprocess,
# imports of runners, write/open mode, or dynamic guest interfaces.
t=ast.parse(source.read_text());assert {n.names[0].name for n in t.body if isinstance(n,ast.Import)}=={'hashlib','stat'}
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('write_text','write_bytes','Popen','run','system','mkdir','unlink') for n in ast.walk(t))
pins=[]
for p in [source,candidate,baseline]:
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 pins.append({'path':str(p),'bytes':p.stat().st_size,'sha256':h})
(O/'CPIO-AUDIT-INPUTS-BEFORE.json').write_text(json.dumps(pins,indent=2)+'\n')
def audit_event(event,args):
 if event in ('subprocess.Popen','socket.__new__','os.system','os.fork','os.posix_spawn','os.mkdir'):raise RuntimeError('forbidden CPIO audit side effect:'+event)
 if event=='open' and isinstance(args[0],(str,bytes)) and ((args[1] and any(c in args[1] for c in 'wax+')) or args[2]&0x603) and not Path(args[0]).resolve().is_relative_to(O):raise RuntimeError('outside write')
sys.addaudithook(audit_event)
spec=importlib.util.spec_from_file_location('r37_exact_original_cpio_audit',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);r=m.audit(candidate,baseline)
assert r['safe_to_unpack'] is True and not r['baseline_ELF_changed_or_missing'] and not r['unpack_parent_order_errors'];assert r['candidate_cpio_sha256']=='49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff'
(O/'ORIGINAL-CPIO-ADMISSION.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['member_count','original_baseline_ELF_members','baseline_ELF_changed_or_missing','unpack_parent_order_errors','candidate_cpio_sha256','safe_to_unpack']}))
