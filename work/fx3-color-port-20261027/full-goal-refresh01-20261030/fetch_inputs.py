#!/usr/bin/env python3
"""Capture current primary public metadata only; never execute downloaded code."""
import concurrent.futures,datetime,hashlib,json,subprocess,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
REFS=HERE/'references'
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(label,url):
    path=REFS/(label+'.source.txt');assert not path.exists()
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Firmware-source-review/1.0','Accept':'application/vnd.github+json' if 'api.github.com' in url else '*/*'})
        with urllib.request.urlopen(req,timeout=18) as f:raw=f.read();status=f.status
        transport=dict(method='urllib_default_TLS',HTTP_status=status)
    except Exception as e:
        prior=dict(type=type(e).__name__,message=str(e))
        r=subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','22',url],capture_output=True)
        if r.returncode:return dict(label=label,url=url,error=dict(urllib=prior,curl_exit=r.returncode,curl_stderr=r.stderr.decode(errors='replace')[:500]))
        raw=r.stdout;transport=dict(method='curl_default_TLS',urllib_attempt=prior,curl_exit=0)
    path.write_bytes(raw)
    return dict(label=label,url=url,path=str(path.relative_to(HERE)),bytes=len(raw),sha256=sha(raw),transport=transport)


def main():
    assert not (HERE/'public-source-capture.json').exists();REFS.mkdir(exist_ok=False)
    repos={'a7iv':'leogenot/sony-a7iv-feature-research','a6000':'nicolvus/a6000-fw-decomp',
           'fwtool':'ma1co/fwtool.py','reloaded':'masterflai/pmca-re-reloaded'}
    jobs=[(name+'-commit','https://api.github.com/repos/'+repo+'/commits?per_page=1') for name,repo in repos.items()]
    jobs += [('FX5-JP','https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads'),
             ('FX5-US','https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads'),
             ('FX5-OSS','https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:items=list(pool.map(lambda x:fetch(*x),jobs))
    heads={};next_jobs=[]
    for name,repo in repos.items():
        item=next(x for x in items if x['label']==name+'-commit')
        if 'error' in item:continue
        j=json.loads((HERE/item['path']).read_text())[0];commit=j['sha']
        heads[name]=dict(repository=repo,commit=commit,time=j['commit']['committer']['date'],message=j['commit']['message'],url=j['html_url'])
        next_jobs.append((name+'-README','https://raw.githubusercontent.com/'+repo+'/'+commit+'/README.md'))
        if name=='reloaded':next_jobs.append(('reloaded-tree','https://api.github.com/repos/'+repo+'/git/trees/'+commit+'?recursive=1'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:items+=list(pool.map(lambda x:fetch(*x),next_jobs))
    result=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=items,heads=heads,
                source_executed=False,device_actions=0)
    (HERE/'public-source-capture.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(heads=heads,fetch_errors=[dict(label=x['label'],error=x['error']) for x in items if 'error' in x]),ensure_ascii=False))


if __name__=='__main__':main()
