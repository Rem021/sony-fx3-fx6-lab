"""Public source/header audit only; never executes downloaded code or accesses devices."""
import base64, concurrent.futures, datetime, hashlib, io, json, pathlib, re, struct, tarfile, urllib.request
OUT=pathlib.Path(__file__).resolve().parent

def fetch(url,headers=None,limit=120_000_000):
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers or {}),timeout=45) as r:
        b=r.read(limit+1)
        if len(b)>limit: raise ValueError('size cap')
        return b,dict(r.headers),r.status,r.url

def kernel(name):
    url='https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/'+name
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30) as r:
        h=dict(r.headers); final=r.url
    total=int(h['Content-Length']); step=4*1024*1024
    def part(start):
        end=min(start+step,total)-1
        data,headers,status,_=fetch(url,{'Range':f'bytes={start}-{end}','If-Match':h['ETag']},step)
        assert status==206 and len(data)==end-start+1
        assert headers.get('Content-Range')==f'bytes {start}-{end}/{total}'
        return data
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as chunks:
        b=b''.join(chunks.map(part,range(0,total,step)))
    md5=base64.b64encode(hashlib.md5(b).digest()).decode()
    assert len(b)==int(h['Content-Length']) and md5==h['Content-MD5']
    rows=[]
    with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as t:
        for m in t:
            p=m.name
            if not m.isfile():continue
            root_make=p.count('/')<=1 and p.endswith('Makefile')
            device='/boot/dts/' in p and ('cxd' in p.lower() or 'sony' in p.lower()) and p.endswith(('.dts','.dtsi'))
            config='/configs/' in p and ('cxd' in p.lower() or 'sony' in p.lower())
            if not (root_make or device or config):continue
            data=t.extractfile(m).read();s=data.decode(errors='replace')
            terms=r'^(VERSION|PATCHLEVEL|SUBLEVEL)\s*=' if root_make else (r'compatible\s*=|#include|/include/' if device else r'CONFIG_(ARM64|ARM=|TEE|OPTEE|SMP|NR_CPUS)')
            hits=[{'line':i,'text':l.strip()} for i,l in enumerate(s.splitlines(),1) if re.search(terms,l)]
            if hits: rows.append({'member':p,'sha256':hashlib.sha256(data).hexdigest(),'matches':hits})
    result={'url':url,'final_url':final,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'server_md5_matches':True,'files':rows,'scope':'Published kernel source, not proof of shipping DTB or RAW/ISP binary compatibility. Archive held in memory only.'}
    (OUT/(name+'.evidence.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return {'name':name,'files':len(rows),'bytes':len(b)}

def firmware():
    url='https://support.d-imaging.sony.co.jp/download/NEX/Dobb4b83c7/BODYDATA.DAT?fm=cn'
    b,h,status,final=fetch(url,{'Range':'bytes=0-65535'},65536)
    assert status==206 and len(b)==65536 and h.get('Content-Range','').startswith('bytes 0-65535/')
    chunks=[]
    if b[:8]==b'\x89UFU\r\n\x1a\n':
        pos=8
        while pos+8<=len(b):
            size,kind=struct.unpack_from('>I4s',b,pos)
            chunks.append({'offset':pos,'type':kind.decode('ascii',errors='replace'),'length':size})
            pos+=8+size
    (OUT/'fx6-6.01-prefix.bin').write_bytes(b)
    result={'url':url,'final_url':final,'status':status,'content_range':h.get('Content-Range'),'sha256':hashlib.sha256(b).hexdigest(),'first16_hex':b[:16].hex(),'chunks':chunks,'full_download':False,'decrypted':False,'camera_access':False}
    (OUT/'firmware-prefix.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(kernel,n) for n in ['linux-kernel.tar.gz','linux-kernel-u.tar.gz']]+[pool.submit(firmware)]
        for f in concurrent.futures.as_completed(fs):
            try: result=f.result()
            except Exception as e:result={'error':str(e)}
            results.append(result);print(json.dumps(result),flush=True)
    (OUT/'collection.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},indent=2)+'\n')
