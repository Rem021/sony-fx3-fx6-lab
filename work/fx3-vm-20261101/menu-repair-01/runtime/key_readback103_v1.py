"""QMP read of the committed native OSD ring, never mutable source surfaces.
Caller quiesces QEMU first. Frozen TRY1 slot identity/FNV validation retained.
"""
from pathlib import Path
import json,struct,time,hashlib
from trial_ring_v1 import validate_slot
from osd_ring93_v4 import BASE,HEADER,STRIDE,MAGIC,rgba,png,sha

def capture_frame(qmp,run,label,step,key,first_observed_up):
    run=Path(run);stem='ap102-'+label
    def read(address,n,suffix):
        p=run/(stem+suffix);assert not p.exists()
        qmp('human-monitor-command',{'command-line':f'pmemsave {hex(address)} {hex(n)} "{p}"'})
        return p.read_bytes() if p.exists() else b''
    head=read(BASE,0x100,'-ring-header.bin')
    if len(head)!=256:return {'step':step,'key':hex(key),'error':'short native ring header'}
    g=struct.unpack_from('<16Q',head)
    if g[0]!=MAGIC or g[1]!=2 or g[9] or not g[4]:return {'step':step,'key':hex(key),'error':'unavailable/failed native ring'}
    slot=(g[4]-1)%8;sample=read(BASE+HEADER+slot*STRIDE,STRIDE,'-ring-slot.bin');value,reason=validate_slot(g,sample)
    if reason:return {'step':step,'key':hex(key),'error':reason}
    v,data=value;fmt,w,h,stride=v[7:11]
    if (fmt,w,h,stride)!=(0,640,480,640):return {'step':step,'key':hex(key),'error':'new native frame identity/format outside approved screen readback'}
    raw=run/(stem+'.bin');image=run/(stem+'.png');assert not raw.exists() and not image.exists();raw.write_bytes(data);pixels=rgba(data,w,h,stride,fmt);encoded=png(w,h,pixels);image.write_bytes(encoded)
    record={'step':step,'key':hex(key),'QMP_read_only':True,'physical':hex(v[6]),'format':'native GPE fmt0 LE16 RGBA4444 opaque RGB export','width':w,'height':h,'stride_pixels':stride,'after_up_first_observed_host_seconds':time.monotonic()-first_observed_up,'timing_scope':'Most recent committed frame sampled after successful up; semantic transition completion must be reviewed visually','raw':str(raw),'raw_sha256':sha(data),'PNG':str(image),'PNG_sha256':sha(encoded),'unique_pixels':len({pixels[i:i+4]for i in range(0,len(pixels),4)}),'latest_native_committed_sequence':v[0],'native_committed_sha256':sha(data),'matches_committed_ring':True,'committed_slot':slot,'slot_FNV_verified':True,'source':'native immutable software-ring copy, captured during original raster/native read lease; source PA not reread','synthetic_input':step>0,'original_cp_key_detection':False,'menu_verified':False,
      'registered_target':{'version':v[26],'kind':v[27],'object':hex(v[28]),'epoch':v[29],'identity':hex(v[30]),'parent_physical':hex(v[31]),'parent_bytes':v[32],'native_token':hex(v[33]),'vptr':hex(v[34]),'captured_physical':hex(v[35]),'valid_during_native_read_lease_and_raster_lifecycle_guards':True},
      'native_identity':{'FB':hex(v[13]),'bitmap':hex(v[14]),'entry':hex(v[15]),'allocation':hex(v[16]),'metadata_physical':hex(v[17]),'FB_format':v[18],'publish_sem':hex(v[19]),'config_hash':hex(v[20]),'bits_cpu_VA':hex(v[22]),'map_begin':hex(v[23]),'map_end':hex(v[24]),'map_offset':hex(v[25])}}
    (run/(stem+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');return record
