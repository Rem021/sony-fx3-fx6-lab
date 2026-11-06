from pathlib import Path
import tempfile,struct,re,json
from key_readback103_v1 import capture_frame,BASE,HEADER,STRIDE
from trial_ring_v1 import validate_slot
R=Path(__file__).resolve().parent;data=(R/'runs/ap103v3ldec600-4ad191d2/osd-ring-final.bin').read_bytes();g=struct.unpack_from('<16Q',data);index=(g[4]-1)%8;off=HEADER+index*STRIDE;sample=data[off:off+STRIDE];value,reason=validate_slot(g,sample);assert not reason;v,raw=value
with tempfile.TemporaryDirectory(prefix='fx3-readback103-')as td:
    seen=[]
    def qmp(cmd,args):
        assert cmd=='human-monitor-command';m=re.fullmatch(r'pmemsave (0x[0-9a-f]+) (0x[0-9a-f]+) "([^"]+)"',args['command-line']);assert m
        a,n=int(m[1],16),int(m[2],16);assert (a,n)in[(BASE,256),(BASE+off,STRIDE)];seen.append((a,n));Path(m[3]).write_bytes(data[a-BASE:a-BASE+n]);return ''
    r=capture_frame(qmp,td,'fixture',12,0x1ac,0);assert not r.get('error') and Path(r['raw']).read_bytes()==raw and len(seen)==2;assert r['slot_FNV_verified'];assert r['registered_target']['valid_during_native_read_lease_and_raster_lifecycle_guards']
bad=bytearray(sample);bad[512]^=1;assert validate_slot(g,bad)[0]is None
bad=bytearray(sample);struct.pack_into('<Q',bad,33*8,v[33]+1);assert validate_slot(g,bad)[0]is None
print('AP103_COMMITTED_RING_EXACT_FIXTURE_NO_SOURCE_PA_READ_IDENTITY_FNV_REJECT_PASS')
