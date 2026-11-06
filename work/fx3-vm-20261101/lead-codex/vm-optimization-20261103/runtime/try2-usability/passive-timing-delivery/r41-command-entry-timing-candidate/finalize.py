"""Finalize only r41 source/receipts and actual input pins, never an execution gate."""
from pathlib import Path
import hashlib,json,os,plistlib,subprocess,sys,time
from elf_review import ELF
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
# Every input category keeps its observation timing; merge is only for the final recheck.
initial=json.loads((O/'INPUTS-BEFORE.json').read_text())['files'];extra=json.loads((O/'ADDITIONAL-INPUTS-BEFORE.json').read_text());dep=json.loads((O/'DEPENDENCY-BINDING.json').read_text())['additional_observed_technical_inputs'];slot=json.loads((O/'SLOT-ELF-REVIEW.json').read_text());r=slot['reference'];other={r['path']:{'sha256':r['sha256'],'bytes':r['bytes']}}
combined={};categories={}
for label,rows in [('initial_preparation_snapshot',initial),('first_observed_legacy_serial_after_read',extra),('later_observed_compiler_dependencies_and_tools',dep),('first_observed_linker_recipe_reference',other)]:
 categories[label]=len(rows)
 for name,value in rows.items():
  v={'sha256':value['sha256'],'bytes':value['bytes']}
  if name in combined:assert combined[name]==v,(name,'conflicting input pins')
  combined[name]=v
checks=[]
for name,v in sorted(combined.items()):
 p=Path(name);actual={'sha256':sha(p),'bytes':p.stat().st_size};checks.append({'path':name,'expected':v,'actual':actual,'match':actual==v})
assert all(v['match'] for v in checks)
(O/'INPUTS-AFTER.json').write_text(json.dumps({'categories_not_disjoint':categories,'merged_unique_inputs':len(checks),'matched':sum(v['match'] for v in checks),'scope':'33 original preparation pins plus later first-observed technical pins; NOT all fresh before/after snapshots','files':checks},indent=2)+'\n')
assert json.loads((O/'HOST-TESTS.json').read_text())['passed'] and len(json.loads((O/'HOST-TESTS.json').read_text())['cases'])==5
assert json.loads((O/'PARSER-TESTS.json').read_text())['passed'] and len(json.loads((O/'PARSER-TESTS.json').read_text())['cases'])==18
assert json.loads((O/'SOURCE-ELF-REVIEW.json').read_text())['passed'] and slot['passed']
a=ELF(O/'build/gpe-r41-candidate.so');b=ELF(O/'build/gpe-r41-fixed-slot.so')
info={}
for rr in a.raw:
 if rr[2]&2:
  n=next(n for n,s in a.sections.items() if s['offset']==rr[4] and s['size']==rr[5]);s=b.sections[n];tt=next(x for x in b.raw if x[4]==s['offset'] and x[5]==s['size']);assert rr[7]==tt[7],n;info[n]=True
(O/'FINAL-VERIFY.json').write_text(json.dumps({'passed':True,'ALLOC_sh_info_equal':info,'fixed_slot_body_sha256':sha(O/'build/gpe-r41-fixed-slot.so'),'fixed_slot_body_bytes':b.path.stat().st_size,'raw_excess_preserved':720,'known_legacy_durations':json.loads((O/'R38-COMPATIBILITY.json').read_text())['summary']['known_durations'],'VM_deploy_guest_execution':False},indent=2)+'\n')
source=[p for p in O.rglob('*') if p.is_file() and p.suffix in ('.py','.c','.h') and not p.is_relative_to(O/'build') and not p.is_relative_to(O/'receipts')]
(O/'SOURCE-FREEZE.json').write_text(json.dumps({str(p.relative_to(O)):sha(p) for p in sorted(source)},indent=2)+'\n')
(O/'RUNTIME-SOURCE-FREEZE.json').write_text(json.dumps({str(p.relative_to(O)):sha(p) for p in sorted((O/'src').iterdir())},indent=2)+'\n')
cache=[O/'build/zig-local',O/'build/zig-global',O/'build/tmp'];inventory={str(d.relative_to(O)):{'files':sum(p.is_file() for p in d.rglob('*')),'bytes':sum(p.stat().st_size for p in d.rglob('*') if p.is_file())} for d in cache}
(O/'CACHE-SCOPE.json').write_text(json.dumps({'excluded_rebuildable_roots':inventory,'reason':'compiler caches/temp only; not runtime source, ELF or test receipts','all_task_writes_within':str(O)},indent=2)+'\n')
(O/'EXECUTION-SCOPE.json').write_text(json.dumps({'host_commands':'clang/zig compilation, bounded Darwin host mocks/cost, pure-file Python/objdump analysis, diskutil read; all synchronously waited','VM_QEMU_browser_service_QMP_guest_camera_USB_SD_deployment':False,'target_ELF_loaded_or_executed':False,'CPIO_DTB_runtime_copied_or_modified':False,'task_output_root':str(O),'no_worker_delegation':True,'FX6_rejected_implementation_retried':False,'runtime_policy_20s_pin_confirm_changed':False,'timestamp_ns':time.time_ns()},indent=2)+'\n')
(O/'VERDICT.json').write_text(json.dumps({'offline_candidate_implementation':'passed','paired_full_source_host_cases':5,'parser_groups':18,'AArch64_raw_build':'passed','fixed_slot_link_strip_and_equivalence':'passed','fixed_slot_body_bytes':len(b.data),'CPIO_package':'not built','runtime_binding':'not implemented','VM':'not executed','performance_improvement':'not measured','FX6_boot':'not improved','technical_input_recheck':len(checks)},indent=2)+'\n')
files=[p for p in sorted(O.rglob('*')) if p.is_file() and p!=O/'SHA256SUMS' and not any(p.is_relative_to(d) for d in cache)]
(O/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(O))+'\n' for p in files))
print(json.dumps({'delivery_files':len(files),'delivery_bytes':sum(p.stat().st_size for p in files),'unique_inputs':len(checks),'SOURCE_items':len(source),'SHA256SUMS_SHA256':sha(O/'SHA256SUMS'),'REPORT_SHA256':sha(O/'REPORT.md'),'slot_elf_sha256':sha(b.path)}))
