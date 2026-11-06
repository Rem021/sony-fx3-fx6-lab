#!/usr/bin/env python3
"""Exact eight real ring slots through cached reader into v22 web identity gate."""
import hashlib
import json
import shlex
import struct
import tempfile
from pathlib import Path

import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT/'runs/try2passivetiming-internal-v21-2383af57'
sys.path.insert(0, str(RUN/'observer-source'))
from osd_ring93_v4 import BASE, HEADER, STRIDE
from trial_ring_cached import TrialRingReader
from trial_web_v22_navigation_review import TrialState

blob = (RUN/'osd-ring-final.bin').read_bytes()
head = blob[:256]
slots = sorted((blob[HEADER+i*STRIDE:HEADER+(i+1)*STRIDE] for i in range(8)),
               key=lambda s:struct.unpack_from('<Q',s)[0])

class FakeQMP:
    def __init__(self, folder):
        self.folder=folder
        self.frame=None
    def __call__(self, cmd, args):
        assert cmd=='human-monitor-command'
        op,addr,n,path=shlex.split(args['command-line'])
        addr=int(addr,0);n=int(n,0)
        seq=struct.unpack_from('<16Q',self.frame[0])[4]
        assert op=='pmemsave' and Path(path).parent==self.folder
        assert addr==(BASE if n==256 else BASE+HEADER+((seq-1)%8)*STRIDE)
        data=self.frame[0] if n==256 else self.frame[1]
        assert len(data)==n
        Path(path).write_bytes(data)
        return {'return':''}

folder=Path(tempfile.mkdtemp(prefix='cache-nav-',dir=HERE))
state=TrialState('HOST_CACHE_COMBINATION',60,4096)
q=FakeQMP(folder)
reader=TrialRingReader(folder,q,state)
for slot in slots:
    words=list(struct.unpack_from('<16Q',head))
    v=struct.unpack_from('<36Q',slot)
    words[3]=v[1]; words[4]=v[0]
    q.frame=(struct.pack('<16Q',*words)+head[128:],slot)
    reader.poll()

assert reader.cache_hits==7 and reader.cache_misses==1
assert [*state.frames]==list(range(4267,4275))
assert {f['content_generation'] for f in state.frames.values()}=={1}
assert state.frame['PNG_sha256']==hashlib.sha256((RUN/'trial-final.png').read_bytes()).hexdigest()
state.update(phase='ready',ready=True,steps=1)
state.require_visual_review(1,'no_change_observed',False)
first=state.frames[4267]
code, ack=state.confirm_visual({'step':1,'observed_sequence':4267,
    'content_generation':first['content_generation'], 'PNG_sha256':first['PNG_sha256'],
    'request_id':'a'*32})
assert code==200 and ack['guest_input_written'] is False and state.snapshot()['ready']
receipt={'status':'PASS','guest_started':False,'source':'exact v21 final eight ring slots',
         'sequences':[4267,4274],'cache_hits':reader.cache_hits,'cache_misses':reader.cache_misses,
         'content_generation':state.content_generation,'review_ack':ack,
         'cached_source_sha256':hashlib.sha256((HERE/'trial_ring_cached.py').read_bytes()).hexdigest(),
         'web_source_sha256':hashlib.sha256((HERE/'trial_web_v22_navigation_review.py').read_bytes()).hexdigest()}
(folder/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'receipt':str(folder/'receipt.json'),**receipt},ensure_ascii=False,indent=2))
