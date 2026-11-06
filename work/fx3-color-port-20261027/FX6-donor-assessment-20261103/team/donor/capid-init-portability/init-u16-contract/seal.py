"""Seal this directory only; validate original delivery manifests and ELF hashes."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((H/'instruction-evidence.json').read_text())
for k,v in j['inputs'].items():assert sha(Path(v['path']))==v['sha256'],k
old=[]
for p,key in [(B/'delivery-manifest.json','files'),(B/'callback-contracts/receipt.json','artifacts'),(B/'poweron-contract/receipt.json','artifacts')]:
 rows=json.loads(p.read_text())[key]
 for name,value in rows.items():
  expected=value['sha256'] if isinstance(value,dict) else value
  assert sha(p.parent/name)==expected,str(p.parent/name)
 old.append({'manifest':str(p),'sha256':sha(p),'files_checked':len(rows),'all_match':True})
for target in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
 if target!='receipt.json' and not target.startswith(('http:','https:','#')):assert (H/target).exists(),target
artifacts={p.name:{'sha256':sha(p),'size':p.stat().st_size} for p in sorted(H.iterdir()) if p.is_file() and p.name!='receipt.json'}
receipt={'status':'STATIC_U16_ROLE_AND_CONDITIONAL_XAVCS_CONVERSION_PROVEN_RUNTIME_ADAPTER_NOT_APPROVED','inputs':j['inputs'],'old_deliveries':old,'originals_unchanged':True,'instructions_verified':len(j['instructions']),'disassembly_excerpts':len(j['excerpt_hashes']),'offline_result':'PASS: 5 initializer inputs, 7 threshold cases, conditional Mxf interlace counterexample, 7 converter rejections','stubs':[],'elf_function_execution':False,'vm_or_device_run':False,'platform_or_firmware_mutation':False,'decision':{'fx6_xavcs_native_effective_u16':780,'fx6_mxf_native_effective_u16':1440,'global_init_conversion_permitted':False,'direct_1440_preserves_xavcs_threshold':False,'conditional_two_byte_conversion':'a005 -> 0c03 only with known source Xavcs constructor 0x1b3284 and target 0x11b9dc','mxf_conversion':'explicitly rejected'},'remaining_edges':['actual Init call, GOT and return','concrete MovieRecInfo+0x27c from GetMovieRecParam+0x1dc at EnterRec and constructor/initializer identity','cross-writer frame-rate/counter domain and event side effects if Mxf requested','global alias exclusion beyond the two identified queued-record x2 producer edges is not claimed'],'artifacts':artifacts}
(H/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'fixed_inputs':len(j['inputs']),'old_files_verified':sum(x['files_checked'] for x in old),'instructions_verified':len(j['instructions']),'artifacts':len(artifacts),'receipt_sha256':sha(H/'receipt.json')}))
