#!/usr/bin/env python3
"""Pin public maintainer status and fwtool format entry points as text only."""
import datetime,hashlib,json,subprocess,urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parent


def get(url):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'FX3-static-readiness-review','Accept':'application/vnd.github+json' if 'api.github.com/' in url else '*/*'})
        with urllib.request.urlopen(req,timeout=15) as response:
            body=response.read(2*1024*1024+1)
            assert len(body)<=2*1024*1024
            return body,dict(method='urllib',HTTP_status=response.status)
    except Exception as e:
        failure=dict(error_type=type(e).__name__,message=str(e))
        p=subprocess.run(['/usr/bin/curl','--fail','--location','--silent','--show-error','--max-time','20',url],capture_output=True)
        if p.returncode!=0:
            raise RuntimeError(json.dumps(dict(url=url,urllib=failure,curl_exit=p.returncode,curl_error=p.stderr.decode(errors='replace')[:800])))
        assert len(p.stdout)<=2*1024*1024
        return p.stdout,dict(method='curl_default_TLS_verification',urllib_attempt=failure,curl_exit=0)


def save(path,data):
    with path.open('xb') as f:f.write(data)
    return dict(path=str(path.relative_to(HERE)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def main():
    out=HERE/'public-maintainer-status.json';assert not out.exists()
    refs=HERE/'references';refs.mkdir(exist_ok=False)
    rows=[]
    for label,repo in [('a7iv','leogenot/sony-a7iv-feature-research'),('a6000','nicolvus/a6000-fw-decomp'),('fwtool','ma1co/fwtool.py')]:
        row=dict(label=label,repository='https://github.com/'+repo,downloaded_source_executed=False)
        try:
            raw,transport=get('https://api.github.com/repos/'+repo+'/commits?per_page=1')
            commit=json.loads(raw)[0]
            pin=commit['sha'];row.update(commit=pin,commit_time=commit['commit']['committer']['date'],commit_url=commit['html_url'],transport=transport)
            row['commit_metadata']=save(refs/(label+'-commit-list.json'),raw)
            url='https://raw.githubusercontent.com/'+repo+'/'+pin+'/README.md'
            data,transport=get(url)
            row['readme']=dict(url=url,transport=transport,**save(refs/(label+'-README.md.source.txt'),data))
            if label=='fwtool':
                url='https://api.github.com/repos/'+repo+'/git/trees/'+pin+'?recursive=1'
                tree_raw,transport=get(url);tree=json.loads(tree_raw)
                assert not tree.get('truncated')
                row['tree']=dict(url=url,transport=transport,**save(refs/'fwtool-tree.json',tree_raw))
                available={x['path'] for x in tree['tree'] if x['type']=='blob'}
                row['format_entry_sources']=[]
                for path in ['fwtool.py','fwtool/__init__.py','fwtool/sony/__init__.py','fwtool/sony.py']:
                    if path not in available:continue
                    url='https://raw.githubusercontent.com/'+repo+'/'+pin+'/'+path
                    data,transport=get(url)
                    row['format_entry_sources'].append(dict(repository_path=path,url=url,transport=transport,
                        **save(refs/('fwtool-'+path.replace('/','_')+'.source.txt'),data)))
        except Exception as e:
            row['incomplete_retrieval']=dict(error_type=type(e).__name__,message=str(e)[:1600])
        rows.append(row)
    result=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=rows,
        scope='Primary public maintainer status and fwtool format selectors only. No device scripts, private signing keys, firmware, binaries, or camera backups requested. Text sources are not imported or executed. A status claim for another model is not FX3 admission or complete ISP evidence.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(label=r['label'],commit=r.get('commit'),source_files=1+len(r.get('format_entry_sources',[])) if 'readme' in r else 0,error=r.get('incomplete_retrieval')) for r in rows]))


if __name__=='__main__':main()
