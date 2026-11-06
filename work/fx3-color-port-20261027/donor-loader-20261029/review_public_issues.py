#!/usr/bin/env python3
"""Read public maintainer issue metadata; no issue writes, cloned tools or execution."""
import datetime,hashlib,json,re,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
URL='https://api.github.com/repos/ma1co/fwtool.py/issues?state=all&per_page=100'
def main():
    out=HERE/'maintainer-issue-review.json';assert not out.exists()
    rec=dict(requested_url=URL,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(urllib.request.Request(URL,headers={'Accept':'application/vnd.github+json','User-Agent':'offline-camera-research'}),timeout=20) as r:
            b=r.read(8*1024*1024+1);assert len(b)<=8*1024*1024
            rec.update(status=r.status,final_url=r.url,headers=dict(r.headers),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        (HERE/'fwtool-public-issues.raw.json').write_bytes(b)
        rows=json.loads(b);assert isinstance(rows,list)
        pattern=re.compile(r'VENICE|CineAlta|DATA23213|BinaryPack|type3|FX6\b|FX9\b|PMW.F[5]+\b',re.I)
        hits=[]
        for row in rows:
            texts=[('title',row['title']),('body',row.get('body') or '')]
            matched=[]
            for k,s in texts:
                for m in pattern.finditer(s):matched.append(dict(field=k,keyword=m.group(),context=s[max(0,m.start()-180):m.end()+350]))
            if matched:hits.append(dict(number=row['number'],title=row['title'],url=row['html_url'],comments_url=row['comments_url'],comments=row['comments'],matches=matched))
        rec.update(issue_or_PR_records=len(rows),pagination_link=rec['headers'].get('Link'),matched_records=hits,
            limits='Only this one issue-list page titles and bodies; comments, full histories and other repositories are not included. No-match does not prove global absence of a reader.')
    except Exception as e:rec['error']=type(e).__name__+': '+str(e)
    out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:rec[k] for k in ['status','issue_or_PR_records','pagination_link','matched_records','error'] if k in rec},ensure_ascii=False))
if __name__=='__main__':main()
