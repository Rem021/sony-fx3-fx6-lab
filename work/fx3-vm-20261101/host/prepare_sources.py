from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,tarfile,datetime,subprocess,plistlib,io
root=Path(__file__).resolve().parent
vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert vol['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
records=[]
def get(url,headers=None):
 args=['curl','--silent','--show-error','--fail','--location','--max-time','90',url]
 for k,v in (headers or {}).items():args.extend(['--header',k+': '+v])
 return io.BytesIO(subprocess.check_output(args))
def download(url,dest,expected,headers=None):
 if dest.exists():
  assert hashlib.sha256(dest.read_bytes()).hexdigest()==expected,dest
  return
 part=dest.with_suffix(dest.suffix+'.partial')
 assert not part.exists()
 args=['curl','--fail','--location','--max-time','300','--output',str(part),url]
 for k,v in (headers or {}).items():args.extend(['--header',k+': '+v])
 subprocess.run(args,check=True)
 assert hashlib.sha256(part.read_bytes()).hexdigest()==expected,(dest,'hash mismatch')
 part.rename(dest)
for name in ['pcre2','gettext','glib','pkgconf']:
 url='https://formulae.brew.sh/api/formula/'+name+'.json'
 d=json.load(get(url)); (root/'metadata'/f'{name}.json').write_text(json.dumps(d,indent=2)+'\n')
 tag='arm64_golden_gate'
 bottle=d['bottle']['stable']['files'][tag]
 token=json.load(get('https://ghcr.io/token?'+urllib.parse.urlencode({'service':'ghcr.io','scope':f'repository:homebrew/core/{name}:pull'})))['token']
 out=root/'downloads'/f'{name}-{bottle["sha256"]}.tar.gz'
 download(bottle['url'],out,bottle['sha256'],{'Authorization':'Bearer '+token})
 with tarfile.open(out) as t:t.extractall(root/'deps',filter='data')
 records.append({'formula':name,'version':d['versions']['stable'],'tag':tag,'url':bottle['url'],'sha256':bottle['sha256'],'bytes':out.stat().st_size,'source_metadata':url})
 print('BOTTLE_READY',name,d['versions']['stable'],out.stat().st_size,flush=True)
url='https://download.qemu.org/qemu-11.1.2.tar.xz'
expected='731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016'
out=root/'downloads/qemu-11.1.2.tar.xz'
download(url,out,expected)
def filt(m,d):
 if m.issym() and m.linkname=='/opt/X11/include':return None
 return tarfile.data_filter(m,d)
if not (root/'sources/qemu-11.1.2').exists():
 with tarfile.open(out) as t:t.extractall(root/'sources',filter=filt)
records.append({'source':'QEMU','version':'11.1.2','url':url,'sha256':expected,'bytes':out.stat().st_size,'identity_reference':'upstream SOURCE-ORIGINS.json pinned b3d7c1f; no Sony patch applied'})
(root/'source-receipt.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':records},indent=2)+'\n')
print('SOURCES_READY',flush=True)
