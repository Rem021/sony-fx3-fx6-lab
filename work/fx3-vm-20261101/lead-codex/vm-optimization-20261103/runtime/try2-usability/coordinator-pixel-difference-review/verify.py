"""Compare pinned original PNG pixels; no image transformations or guest access."""
from pathlib import Path
import hashlib
import json
from PIL import Image

HERE = Path(__file__).resolve().parent
RUN = HERE.parent/'runs/try2mssallinternal-c017e6ed'
INPUTS = [
    ('view-step-01-seq-240-2914275caea5.png', '2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e'),
    ('internal-stale-01-f37ae114-current.png', 'e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4'),
]
images=[]
for name,expected in INPUTS:
    p=RUN/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
    im=Image.open(p)
    assert im.mode=='RGBA' and im.size==(640,480)
    assert im.getchannel('A').getextrema()==(255,255)
    images.append(im)
a,b=images
changed=[(x,y) for y in range(480) for x in range(640) if a.getpixel((x,y))!=b.getpixel((x,y))]
box=[min(x for x,y in changed),min(y for x,y in changed),max(x for x,y in changed)+1,max(y for x,y in changed)+1]
outside=sum(not (358<=x<454 and 4<=y<30) for x,y in changed)
assert len(changed)==885 and box==[364,7,448,27] and outside==0
receipt=json.loads((HERE/'receipt.json').read_text())
assert receipt['changed_pixels_rgba']==len(changed)
assert receipt['changed_bbox_half_open']==box and receipt['changed_pixels_outside_region']==outside
for im,item in zip(images,receipt['inputs']):
    assert hashlib.sha256(im.tobytes()).hexdigest()==item['decoded_rgba_sha256']
print('Verified 885 changed RGBA pixels, confined to NO CARD region; 306315 unchanged pixels')
