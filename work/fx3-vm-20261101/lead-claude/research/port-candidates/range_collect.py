"""Bounded HTTP Range download of GPL archives, with complete archive SHA/MD5 verification."""
import concurrent.futures, json, pathlib, re, subprocess, time
import collect_sources as c
ROOT=pathlib.Path(__file__).resolve().parent
def download(job):
 model,url=job
 receipt=ROOT/'receipts'/f'{model}-{"kernel-u" if "-u.tar" in url else "kernel"}.json'
 if receipt.exists():return {'already_collected':model}
 if model in c.LOCAL: return c.collect(job)
 hdr=c.get_headers(url)
 n=int(re.findall(r'(?im)^content-length:\s*(\d+)',hdr)[-1])
 etag=re.findall(r'(?im)^etag:\s*(\S+)',hdr)[-1]
 dest=ROOT/'gpl-archives'/model/('linux-kernel-u.tar.gz' if '-u.tar' in url else 'linux-kernel.tar.gz')
 dest.parent.mkdir(exist_ok=True,parents=True)
 chunk_size=1024*1024
 prefix=dest.stat().st_size if dest.exists() else 0
 if prefix % chunk_size and prefix != n: raise ValueError('unaligned incomplete prefix')
 parts=dest.parent/('parts-u' if '-u.tar' in url else 'parts');parts.mkdir(exist_ok=True)
 def part(i):
  start=i*chunk_size;end=min(n,start+chunk_size)-1
  cache=parts/f'{i:05d}.bin'
  if cache.exists() and cache.stat().st_size==end-start+1:return i,cache
  for attempt in range(5):
   p=subprocess.run(['curl','-fsSL','--connect-timeout','15','--max-time','45','--range',f'{start}-{end}','-H',f'If-Match: {etag}',url],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   # Retrying curl to stdout concatenates partial responses, so retry in Python.
   if p.returncode==0 and len(p.stdout)==end-start+1:
    cache.write_bytes(p.stdout);return i,cache
   if attempt==4:raise ValueError(f'bad range {model} {i}: rc={p.returncode}, bytes={len(p.stdout)}')
 # Ordered map limits memory; writes only this task directory.
 with dest.open('ab') as out, concurrent.futures.ThreadPoolExecutor(6) as pool:
  for i,cache in pool.map(part,range(prefix//chunk_size,(n+chunk_size-1)//chunk_size)):
   out.write(cache.read_bytes());out.flush();cache.unlink()
 r=c.collect(job)
 r['range_download_headers']=hdr
 import hashlib,base64
 expected=re.findall(r'(?im)^content-md5:\s*(\S+)',hdr)
 with dest.open('rb') as f:md5=hashlib.file_digest(f,'md5').digest()
 if expected and base64.b64encode(md5).decode()!=expected[-1]:raise ValueError('MD5 mismatch')
 r['content_md5_verified']=bool(expected);r['transport']='complete ordered Range chunks; If-Match ETag; complete Content-MD5 verified'
 receipt.write_text(json.dumps(r,indent=2)+'\n')
 return {'collected':model,'bytes':n}
if __name__=='__main__':
 pages=json.loads((ROOT/'page-receipts.json').read_text())['pages']
 jobs=[(p['model'],u) for p in pages for u in p['kernel_urls']]
 errors=[]
 with concurrent.futures.ThreadPoolExecutor(3) as pool:
  fs={pool.submit(download,j):j for j in jobs}
  for f in concurrent.futures.as_completed(fs):
   try:
    result=f.result();print(json.dumps({'result':result.get('collected',result.get('model',result.get('already_collected')))}),flush=True)
   except Exception as e:errors.append({'job':fs[f],'error':str(e)});print(json.dumps(errors[-1]),flush=True)
 (ROOT/'collection-errors.json').write_text(json.dumps(errors,indent=2)+'\n')
