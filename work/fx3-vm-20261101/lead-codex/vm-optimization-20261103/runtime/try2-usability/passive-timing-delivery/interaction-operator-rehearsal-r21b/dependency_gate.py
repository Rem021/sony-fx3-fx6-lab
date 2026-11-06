import importlib.util,plistlib,re,subprocess,sys
from common import *
def verify(name):
 disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
 assert disk['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 groups={}
 def group(label,pairs):
  rows=[]
  for path,expected in pairs:
   path=Path(path);actual=sha(path);assert actual==expected,(label,str(path),actual,expected)
   rows.append({'path':str(path.resolve()),'sha256':actual})
  groups[label]=rows
 group('coordinator_pins',[(FROZEN/f,h) for f,h in CFG['fixed_pins'].items()])
 group('source_40',[(FROZEN/f,h) for f,h in read_external(FROZEN/'SOURCE-FREEZE.json').items()])
 group('delivery_145',[(FROZEN/f,h) for f,h in read_external(FROZEN/'DELIVERY-MANIFEST.json')['files'].items()])
 group('dependency_11',[(x['path'],x['sha256']) for x in read_external(FROZEN/'INPUT-HASHES.json').values()])
 group('fixed_input_14',[(Path('/Volumes/KAFU2T/AI/Projects/Mac')/x['path'],x['expected_sha256']) for x in read_external(FROZEN/'FIXED-INPUT-14.json')['files']])
 sums=[]
 for line in (FROZEN/'SHA256SUMS').read_text().splitlines():
  h,f=line.split(maxsplit=1);sums.append((FROZEN/f.lstrip('*'),h))
 group('sha256sums',sums)
 old=HERE.parent/'interaction-operator-rehearsal-r21'
 oldpairs=[]
 for line in (old/'SHA256SUMS').read_text().splitlines():
  h,f=line.split(maxsplit=1);oldpairs.append((old/f.lstrip('*'),h))
 group('previous_failed_delivery_88',oldpairs)
 group('previous_failed_fixed_pins',[(old/'REPORT.md','e74eb7ae0b2fc8a50b5892e16f20eb8a20a60a61317929d06db4e9c9dfed4bb2'),(old/'SHA256SUMS','7327a058d4e62fe7a67a16bab6d51d4d2df00b83defafd98b02b30bd914d7d8f')])
 historical=Path(CFG['historical_root']);group('historical_png',[(historical/f,sha(historical/f)) for f in ('trial-standby-ready.png','trial-step-01-key-1ab.png','trial-final.png')])
 assert sha(historical/'trial-final.png')=='60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292'
 # Source can import without writing into frozen directory.
 spec=importlib.util.spec_from_file_location('original_r21',FROZEN/'trial_web_v22_navigation_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 canonical=re.search(r'<script>(.*?)</script>',m.PAGE,re.S).group(1)
 page_sha=hashlib.sha256(canonical.encode()).hexdigest()
 assert page_sha=='f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab',page_sha
 value={'passed':True,'groups':groups,'counts':{k:len(v) for k,v in groups.items()},'canonical_PAGE_sha256':page_sha,'volume_uuid':disk['VolumeUUID'],**stamp()};write(name,value);return value
def read_external(p):return json.loads(p.read_text())
if __name__=='__main__':print(json.dumps(verify(sys.argv[1] if len(sys.argv)>1 else 'DEPENDENCY-BEFORE.json')['counts']))
