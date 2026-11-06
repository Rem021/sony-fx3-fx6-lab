#!/usr/bin/env python3
"""Resume bounded official FX6 download; reject changed ETag or invalid ranges."""
import concurrent.futures, hashlib, json, os, pathlib, re, subprocess, threading

ROOT = pathlib.Path(__file__).resolve().parent
URL = 'https://di.update.sony.net/NEX/Dobb4b83c7/BODYDATA.DAT'
SIZE = 847081840
ETAG = '"bb5889444b135bf412958a2cabec1a37:1788139615.370836"'
CHUNK = 8 * 1024 * 1024
OUT = ROOT / 'BODYDATA.DAT'
STATE = ROOT / 'download-state.json'
lock = threading.Lock()

def run_one(i):
    lo, hi = i * CHUNK, min(SIZE, (i + 1) * CHUNK) - 1
    headers = ROOT / f'.chunk-{i:03d}.headers'
    part = ROOT / f'.chunk-{i:03d}.part'
    cmd = ['curl', '-fLsS', '--retry', '3', '--retry-delay', '2', '--max-time', '180',
           '-H', f'If-Range: {ETAG}', '-r', f'{lo}-{hi}', '-D', str(headers), '-o', str(part), URL]
    try:
        subprocess.run(cmd, check=True)
        h = headers.read_text(errors='replace')
        if not re.search(r'(?im)^HTTP/\S+ 206\b', h): raise ValueError('not HTTP 206')
        if f'Content-Range: bytes {lo}-{hi}/{SIZE}'.lower() not in h.lower(): raise ValueError('wrong Content-Range')
        if f'ETag: {ETAG}'.lower() not in h.lower(): raise ValueError('ETag changed')
        data = part.read_bytes()
        if len(data) != hi-lo+1: raise ValueError('short chunk')
        digest = hashlib.sha256(data).hexdigest()
        fd = os.open(OUT, os.O_WRONLY)
        try: os.pwrite(fd, data, lo)
        finally: os.close(fd)
        with lock:
            s = json.loads(STATE.read_text())
            s['chunks'][str(i)] = digest
            STATE.write_text(json.dumps(s, indent=2) + '\n')
            print(f'{i+1}/{(SIZE+CHUNK-1)//CHUNK} {lo}-{hi} sha256={digest[:12]}', flush=True)
    finally:
        part.unlink(missing_ok=True)
        headers.unlink(missing_ok=True)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    n = (SIZE+CHUNK-1)//CHUNK
    if STATE.exists():
        s=json.loads(STATE.read_text())
        assert s['url']==URL and s['etag']==ETAG and s['bytes']==SIZE and s['chunk_bytes']==CHUNK
    else:
        s={'url':URL,'etag':ETAG,'bytes':SIZE,'chunk_bytes':CHUNK,'chunks':{}}
        STATE.write_text(json.dumps(s, indent=2)+'\n')
    fd=os.open(OUT, os.O_CREAT|os.O_RDWR, 0o644)
    try: os.ftruncate(fd,SIZE)
    finally: os.close(fd)
    # Rehash completed ranges before trusting a resume state.
    with OUT.open('rb') as f:
        for k,v in list(s['chunks'].items()):
            i=int(k); f.seek(i*CHUNK)
            if hashlib.sha256(f.read(min(CHUNK,SIZE-i*CHUNK))).hexdigest()!=v: del s['chunks'][k]
    STATE.write_text(json.dumps(s,indent=2)+'\n')
    todo=[i for i in range(n) if str(i) not in s['chunks']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for _ in ex.map(run_one,todo): pass
    s=json.loads(STATE.read_text())
    assert len(s['chunks'])==n
    sha=hashlib.sha256()
    with OUT.open('rb') as f:
        while b:=f.read(CHUNK): sha.update(b)
    receipt={'url':URL,'etag':ETAG,'bytes':SIZE,'sha256':sha.hexdigest(),'chunk_count':n,'range_checks':'all HTTP 206, exact Content-Range, ETag and length'}
    (ROOT/'download-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)

if __name__=='__main__': main()
