#!/usr/bin/env python3
"""Read current public references and documentation; never run project code."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import subprocess
import sys
import urllib.request

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def fetch(item):
    name,url=item
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'FX3-offline-source-review/1'})
        with urllib.request.urlopen(request,timeout=25) as response:
            raw=response.read(262145)
            assert len(raw)<=262144
            return {'name':name,'url':url,'status':response.status,'final_url':response.url,
                    'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                    'http_date':response.headers.get('Date'),'raw':raw}
    except Exception as e:return {'name':name,'url':url,'error':str(e)}


def gitref(item):
    name,url,ref=item
    try:
        p=subprocess.run(['git','ls-remote',url,ref],capture_output=True,text=True,timeout=25)
        return {'name':name,'url':url,'ref':ref,'exit_code':p.returncode,
                'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
    except Exception as e:return {'name':name,'url':url,'ref':ref,'error':str(e)}


def main():
    h.im.volume();out=STAGE/'public-source-refresh-20261027';assert not out.exists()
    docs=[('rea-firmware-guide.md','https://raw.githubusercontent.com/morluto/rea/main/docs/firmware-analysis.md'),
          ('a6700-readme.md','https://raw.githubusercontent.com/xyzhangxin/sony-a6700-powerful/main/README.md'),
          ('a7c2-readme.md','https://raw.githubusercontent.com/QAQLeonard/a7c2-fl23-research/main/README.md')]
    refs=[('REA','https://github.com/morluto/rea.git','refs/heads/main'),
          ('A6700','https://github.com/xyzhangxin/sony-a6700-powerful.git','refs/heads/main'),
          ('A7CII','https://github.com/QAQLeonard/a7c2-fl23-research.git','refs/heads/main'),
          ('fwtool-PR52','https://github.com/ma1co/fwtool.py.git','refs/pull/52/head')]
    with ThreadPoolExecutor(max_workers=7) as pool:
        fs=[pool.submit(fetch,x) for x in docs];gs=[pool.submit(gitref,x) for x in refs]
        dr=[x.result() for x in fs];gr=[x.result() for x in gs]
    out.mkdir()
    for row in dr:
        raw=row.pop('raw',None)
        if raw is not None:(out/row['name']).write_bytes(raw)
    receipt={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'read_only_public_HTTP_and_git_references':True,'docs':dr,'git_refs':gr,
             'web_observations':[
               {'url':'https://github.com/QAQLeonard/a7c2-fl23-research/releases','observation':'Page currently labels v3.0.3 latest, 23 Oct, tag commit7827856.'},
               {'url':'https://github.com/ma1co/fwtool.py/pull/52','observation':'Page currently shows Open.'}],
             'binaries_payloads_camera_attachments_downloaded_or_third_party_code_run':False}
    h.im.write_json(out/'receipt.json',receipt)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
