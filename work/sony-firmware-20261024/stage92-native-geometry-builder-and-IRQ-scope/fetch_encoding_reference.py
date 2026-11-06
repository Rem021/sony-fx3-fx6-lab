#!/usr/bin/env python3
"""Hash one pinned public binutils test; save only three opcode matches."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import urllib.request

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import geometry_builder as a


def main():
    a.im.volume();out=STAGE/'public-encoding-reference.json';assert not out.exists()
    url='https://sources.debian.org/data/main/b/binutils/2.43.1-5/gas/testsuite/gas/mips/allegrex.d'
    request=urllib.request.Request(url,headers={'User-Agent':'FX3-offline-reference-audit/1'})
    with urllib.request.urlopen(request,timeout=20) as response:
        raw=response.read(16385);assert response.status==200 and len(raw)<=16384
        status=response.status;date=response.headers.get('Date');final=response.url
    body=raw.decode();assert all(x in body for x in ('70020026','70000026','70020024'))
    a.im.write_json(out,{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_url':url,'final_url':final,'HTTP_status':status,'HTTP_date':date,'bytes':len(raw),
        'sha256':hashlib.sha256(raw).hexdigest(),
        'matched_encodings':{'70020026':'mtic $2,$0','70000026':'mtic $0,$0','70020024':'mfic $2,$0'},
        'full_source_body_saved':False,'third_party_code_executed':False,
        'applicability':'Opcode decoding reference only; no FX3 processor identity, controller semantics or real IRQ-state proof.',
        'executed_fetch_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps({'HTTP_status':status,'bytes':len(raw),'matched_encodings':3,'output':str(out)}))


if __name__=='__main__':main()
