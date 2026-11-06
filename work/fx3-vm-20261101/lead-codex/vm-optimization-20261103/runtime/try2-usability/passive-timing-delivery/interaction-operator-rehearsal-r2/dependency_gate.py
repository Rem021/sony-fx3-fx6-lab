#!/usr/bin/env python3
"""Explicit coordinator release must exist, then verify frozen dependencies."""
import datetime,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;D=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    release=json.loads((H/'COORDINATOR-RELEASE.json').read_text())
    assert release['allowed_single_timed_rehearsal'] is True
    assert release['coordinator_message_id'].startswith('msg_')
    base=D/'interaction-bounded-capture-helper-r2'
    for name in ['SOURCE-FREEZE.json','SHA256SUMS','REPORT.md']:
        assert sha(base/name)==release['pins'][name],name
    details={}
    for folder,pins in [(base.name,release['pins']),('interaction-explicit-confirm-helper',{
        'SOURCE-FREEZE.json':'8c751f05ab82a94ee06c7c0154ba48967bc7909a6100fd1a77cc9f022c23285a',
        'SHA256SUMS':'b0f7d8e107ec5758227792bfb76d91ac33f8acfc640f83c044f8772fe6d4a49f'})]:
        b=D/folder
        for n,x in pins.items():assert sha(b/n)==x,n
        files=json.loads((b/'SOURCE-FREEZE.json').read_text())['files']
        for n,x in files.items():assert sha(b/n)==x,n
        deps=json.loads((b/'DEPENDENCIES.json').read_text())
        for e in deps.values():assert sha(Path(e['path']))==e['sha256'],e['path']
        count=0
        for line in (b/'SHA256SUMS').read_text().splitlines():
            x,n=line.split('  ',1);assert sha(b/n)==x,n;count+=1
        details[folder]={'sources':len(files),'dependencies':len(deps),'delivery':count,'unchanged':True}
    return {'coordinator_message_id':release['coordinator_message_id'],'verified_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packages':details}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
