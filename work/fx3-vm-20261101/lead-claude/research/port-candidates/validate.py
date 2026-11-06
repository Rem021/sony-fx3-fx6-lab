"""Validate the final static research receipts and local evidence links."""
import base64,datetime,hashlib,json,pathlib,re,subprocess,plistlib
ROOT=pathlib.Path(__file__).resolve().parent
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
errors=[];counts={'archives':0,'source_members':0,'pages':0,'line_matches':0}
def check(ok,msg):
 if not ok:errors.append(msg)
disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
check(disk.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','wrong external volume')
m=json.loads((ROOT/'platform-matrix.json').read_text())
check(len(m['models'])==9,'expected FX3 + 8 candidates')
check(len(m['archive_downloads'])==11,'expected 9 main kernels + 2 kernel-u')
check(len(m['ranking'])==8,'expected ranking of all 8 candidates')
check(not m['camera_or_runtime_touched'] and not m['camera_firmware_package_downloaded_or_modified'] and not m['downloaded_code_executed'],'scope flags')
for recfile in sorted((ROOT/'receipts').glob('*-kernel*.json')):
 r=json.loads(recfile.read_text());p=pathlib.Path(r['reused_local_archive'])
 check(p.is_file(),f'missing archive: {p}')
 if p.is_file():
  check(p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],f'archive size/SHA mismatch: {p}')
  headers=r.get('range_download_headers','')
  md5=re.findall(r'(?im)^content-md5:\s*(\S+)',headers)
  if md5:
   with p.open('rb') as f:actual=base64.b64encode(hashlib.file_digest(f,'md5').digest()).decode()
   check(actual==md5[-1] and r['content_md5_verified'],f'archive MD5 mismatch: {p}')
 counts['archives']+=1
 for file in r['selected_files']:
  p=ROOT/file['path'];check(p.is_file() and sha(p)==file['sha256'],f'source member mismatch {p}');counts['source_members']+=1
for page in m['all_oss_page_downloads']+m['all_spec_and_release_page_downloads']['pages']:
 p=ROOT/page['path'];check(p.is_file() and sha(p)==page['sha256'],f'page hash mismatch {p}');counts['pages']+=1
check(m['all_spec_and_release_page_downloads']['errors']==[],'unresolved specification capture error')
for r in m['models']:
 check(bool(r.get('published_main_platform')),f'missing main platform {r["id"]}')
 if r['id']!='FX5':
  check(r['published_main_platform']['compatible']==['cxd,cxd90057'],'unexpected main platform')
  check(r['published_main_platform']['cpu_nodes']==4,'unexpected CPU nodes')
 for a in r['platforms']:
  fs=[a['kernel_version_evidence']]+[p['evidence'] for p in a['published_platform_files']]+a['published_configs']
  for file in fs:
   p=ROOT/file['path'];ls=p.read_text().splitlines()
   check(sha(p)==file['sha256'],f'line evidence SHA mismatch {p}')
   for match in file['matches']:
    check(ls[match['line']-1].strip()==match['text'],f'wrong line evidence {p}:{match["line"]}');counts['line_matches']+=1
for file in m['FX5_cemmc_local_source_evidence']['files']:
 p=ROOT/file['path'];check(sha(p)==file['sha256'],f'FX5 local source mismatch {p}')
text=(ROOT/'README.md').read_text()
for dest in re.findall(r'\]\(([^)]+)\)',text):
 if dest.startswith(('https://','http://','#')):continue
 check((ROOT/dest).resolve().exists() or dest=='validation.json',f'broken report link {dest}')
check(not json.loads((ROOT/'collection-errors.json').read_text()),'unresolved collection errors')
result={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not errors else 'FAIL','counts':counts,'errors':errors,'scope':'Static source/page/archive/line/link validation only; no build, runtime or camera validation.','volume_uuid':disk.get('VolumeUUID'),'README_sha256':sha(ROOT/'README.md'),'matrix_sha256':sha(ROOT/'platform-matrix.json')}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(bool(errors))
