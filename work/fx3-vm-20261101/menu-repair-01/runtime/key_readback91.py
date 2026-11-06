"""Read-only AP91 per-step QMP pixel receipt; no guest writes or UI rendering."""
from pathlib import Path
import json,hashlib,time
from PIL import Image

def capture_step(qmp,run,step,key,first_observed_up):
    run=Path(run);ring=json.loads((run/'osd-ring-readback.json').read_text());frames=ring.get('frames',[])
    if not frames:return {'step':step,'key':hex(key),'error':'no validated native ring frame'}
    latest=frames[-1];phys=int(latest['physical'],0);w,h,stride=latest['width'],latest['height'],latest['stride_pixels'];fmt=latest['native_format']
    if fmt!=0 or (w,h,stride)!=(640,480,640) or phys!=0x43feb5100:return {'step':step,'key':hex(key),'error':'new native frame identity/format outside approved screen readback','frame':latest}
    stem=f'ap91-step-{step:02d}-key-{key:03x}';raw=run/(stem+'.bin');png=run/(stem+'.png');assert not raw.exists() and not png.exists()
    response=qmp('human-monitor-command',{'command-line':f'pmemsave {hex(phys)} {hex(w*h*2)} "{raw}"'})
    if not raw.exists() or raw.stat().st_size!=w*h*2:return {'step':step,'key':hex(key),'error':'QMP frame read failed','response':response}
    data=raw.read_bytes();sha=hashlib.sha256(data).hexdigest();pixels=[]
    for i in range(0,len(data),2):
        v=int.from_bytes(data[i:i+2],'little');pixels.append(tuple(((v>>s)&15)*17 for s in (12,8,4,0)))
    im=Image.new('RGBA',(w,h));im.putdata(pixels);im.save(png)
    receipt={'step':step,'key':hex(key),'QMP_read_only':True,'physical':hex(phys),'format':'logical GPE fmt0 LE16 RGBA4444','width':w,'height':h,'stride_pixels':stride,'after_up_first_observed_host_seconds':time.monotonic()-first_observed_up,'timing_scope':'Host +2s from first observed successful up marker; polling/QMP add delay, not exact guest event age','raw':str(raw),'raw_sha256':sha,'PNG':str(png),'PNG_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'unique_pixels':len(set(pixels)),'latest_native_committed_sequence':latest['sequence'],'native_committed_sha256':latest['sha256'],'matches_committed_ring':sha==latest['sha256'],'synthetic_input':True,'original_cp_key_detection':False,'menu_verified':False}
    (run/(stem+'.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');return receipt
