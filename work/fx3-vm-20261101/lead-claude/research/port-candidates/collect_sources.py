"""Read-only public GPL evidence collection; never execute downloaded code."""
import base64, concurrent.futures, datetime, hashlib, json, pathlib, re, subprocess, tarfile
from urllib.parse import urljoin

ROOT = pathlib.Path(__file__).resolve().parent
STAGE = pathlib.Path('/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage133-FX5-source-availability-and-portability')
PAGES = {
 'FX3':'B2B/ILME-FX3_Ver700.html', 'FX3A':'B2B/ILME-FX3A_Ver200.html',
 'A7SIII':'DI/ILCE-7SM3_Ver500.html', 'FX30':'B2B/ILME-FX30_Ver600.html',
 'FX2':'B2B/ILME-FX2BFX2_V100.html', 'A7IV':'DI/ILCE-7M4_Ver600.html',
 'A1':'DI/ILCE-1_Ver400.html', 'FX6':'B2B/ILME-FX6V_Ver600.html',
 'FX5':'B2B/ILME-FX5.html'}
LOCAL = {'FX3': STAGE.parent/'stage65-windows-cache-and-runtime-readiness/work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz',
         'FX5': STAGE/'gpl-archives/linux-kernel.tar.gz'}

def get(url):
 return subprocess.check_output(['curl','-fsSL','--connect-timeout','15','--max-time','70','--retry','2',url])

def page(model, path):
 url='https://oss.sony.net/Products/Linux/'+path
 data=get(url)
 dest=ROOT/'pages'/f'{model}.html'; dest.parent.mkdir(exist_ok=True); dest.write_bytes(data)
 links=[urljoin(url,x) for x in re.findall(r'href=["\']([^"\']+)["\']',data.decode())]
 return {'model':model,'url':url,'sha256':hashlib.sha256(data).hexdigest(),'path':str(dest.relative_to(ROOT)),
         'kernel_urls':[x for x in links if re.search(r'/linux-kernel(?:-u)?\.tar\.gz$',x)]}

class DigestReader:
 def __init__(self, file): self.file=file; self.sha=hashlib.sha256(); self.md5=hashlib.md5(); self.n=0
 def read(self,n=-1):
  b=self.file.read(n); self.sha.update(b); self.md5.update(b); self.n+=len(b); return b

def collect(item):
 model,url=item
 local=LOCAL.get(model) if url.endswith('/linux-kernel.tar.gz') else None
 if not local:
  archive=ROOT/'gpl-archives'/model/('linux-kernel-u.tar.gz' if '-u.tar' in url else 'linux-kernel.tar.gz')
  if archive.exists(): local=archive
 proc=None
 if local:
  file=local.open('rb'); headers=''
 else:
  headers=get_headers(url)
  proc=subprocess.Popen(['curl','-fsSL','--connect-timeout','20','--max-time','900',url],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  file=proc.stdout
 reader=DigestReader(file); selected=[]; count=0
 try:
  with tarfile.open(fileobj=reader,mode='r|gz') as tf:
   for m in tf:
    count+=1
    # Keep only metadata, Sony platform DT/config files, and their Makefiles.
    p=pathlib.PurePosixPath(m.name)
    wanted=(len(p.parts)<=2 and p.name=='Makefile') or ('/arch/' in '/'+m.name and ('/cxd/' in m.name or ('/configs/' in m.name and 'cxd' in p.name)))
    if not (m.isfile() and wanted and m.size<2_000_000): continue
    if '..' in p.parts or p.is_absolute(): raise ValueError('unsafe archive path')
    b=tf.extractfile(m).read()
    dest=ROOT/'source-excerpts'/model/('linux-kernel-u' if '-u.tar' in url else 'linux-kernel')/pathlib.Path(*p.parts)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
    selected.append({'member':m.name,'path':str(dest.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
  while reader.read(1024*1024): pass
 finally: file.close()
 if proc:
  err=proc.stderr.read().decode(); rc=proc.wait()
  if rc: raise RuntimeError(f'curl {rc}: {err}')
 expected=re.findall(r'(?im)^content-length:\s*(\d+)',headers)
 md5=re.findall(r'(?im)^content-md5:\s*(\S+)',headers)
 if expected and reader.n!=int(expected[-1]): raise ValueError('length mismatch')
 if md5 and base64.b64encode(reader.md5.digest()).decode()!=md5[-1]: raise ValueError('Content-MD5 mismatch')
 result={'model':model,'url':url,'reused_local_archive':str(local) if local else None,'bytes':reader.n,'sha256':reader.sha.hexdigest(),
         'content_md5_verified':bool(md5),'headers':headers,'archive_members_seen':count,'selected_files':selected,'downloaded_code_executed':False}
 (ROOT/'receipts').mkdir(exist_ok=True)
 (ROOT/'receipts'/f'{model}-{ "kernel-u" if "-u.tar" in url else "kernel"}.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'done':model,'url':url,'sha256':result['sha256'],'selected':len(selected)}),flush=True)
 return result

def get_headers(url):
 return subprocess.check_output(['curl','-fsSI','--connect-timeout','15','--max-time','60',url]).decode()

if __name__=='__main__':
 pages=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(4) as pool:
  fs={pool.submit(page,m,p):m for m,p in PAGES.items()}
  for f in concurrent.futures.as_completed(fs):
   try: pages.append(f.result())
   except Exception as e: errors.append({'model':fs[f],'error':str(e)})
 (ROOT/'page-receipts.json').write_text(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pages':pages,'errors':errors},indent=2)+'\n')
 jobs=[(p['model'],u) for p in pages for u in p['kernel_urls']]
 with concurrent.futures.ThreadPoolExecutor(4) as pool:
  fs={pool.submit(collect,j):j for j in jobs}
  for f in concurrent.futures.as_completed(fs):
   try:f.result()
   except Exception as e: errors.append({'job':fs[f],'error':str(e)}); print(json.dumps(errors[-1]),flush=True)
 (ROOT/'collection-errors.json').write_text(json.dumps(errors,indent=2)+'\n')
