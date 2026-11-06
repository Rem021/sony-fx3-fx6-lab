from PIL import Image
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parents[1];T=D.parents[1]
old=T/'runs/v25gate-n64-r17-65cecb63/trial-frame.png'
new=T/'coordinator-pixel-difference-review/e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4.png'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(old).startswith('2914275cae') and h(new).startswith('e0140ea1b7')
a=Image.open(old).convert('RGBA');b=Image.open(new).convert('RGBA');assert a.size==b.size==(640,480)
pa=a.load();pb=b.load();coords=[]
for y in range(a.height):
 for x in range(a.width):
  if pa[x,y]!=pb[x,y]:coords.append((x,y))
result={'old_run_path':str(old),'old_sha256':h(old),'new_historical_path':str(new),'new_sha256':h(new),'new_not_persisted_in_65cecb63_run':True,'size':list(a.size),'different_pixels':len(coords),'percent':len(coords)/(640*480)*100,'bbox_xyxy_exclusive':[min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords)+1,max(y for x,y in coords)+1],'quarter_counts':[sum(1 for x,y in coords if y//120==k) for k in range(4)]}
(D/'evidence/pixel-difference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result)
