"""Regression: fixed3s is insufficient; ack alone/bytes alone never pass."""
from pathlib import Path
import tempfile,struct,re
from restore_api103_v1 import restore_native_api,PHYS,API,ORIGINAL,CONTROL
PATCH=bytes.fromhex('5000005800021fd6bcfc4d0080ffffff')

def case(timeout,ack_at,bytes_at,status=0):
    with tempfile.TemporaryDirectory(prefix='fx3-restore103-')as td:
        now=[0.];running=[False];requested=[False];writes=[]
        def clock():return now[0]
        def sleep(n):assert running[0];now[0]+=n
        class Gate:
            def shutdown_control(self):assert not requested[0];requested[0]=True;writes.append((PHYS+48,8))
        def qmp(cmd,args=None):
            if cmd=='cont':assert not running[0];running[0]=True;return
            if cmd=='stop':running[0]=False;return
            assert cmd=='human-monitor-command' and not running[0]
            m=re.fullmatch(r'(p?memsave) (0x[0-9a-f]+) (0x[0-9a-f]+) "([^"]+)"',args['command-line']);assert m
            a,n=int(m[2],16),int(m[3],16);p=Path(m[4])
            if (a,n)==(PHYS,4096):
                b=bytearray(4096);struct.pack_into('<8s8Q',b,0,b'F100FILE',4,2,2229740,123,0,CONTROL if requested[0]else 0,status if now[0]>=ack_at else 0,int(now[0]>=ack_at));p.write_bytes(b)
            elif(a,n)==(API,16):p.write_bytes(ORIGINAL if now[0]>=bytes_at else PATCH)
            else:raise AssertionError('unexpected address')
        r=restore_native_api(qmp,Gate(),td,timeout=timeout,poll=.25,clock=clock,sleep=sleep)
        assert not running[0] and writes==[(PHYS+48,8)]
        return r

a=case(3,4.5,4.5);assert not a['passed'] and a['reason']=='completion_timeout'
b=case(20,4.5,4.5);assert b['passed'] and b['elapsed_seconds']>=4.5
c=case(5,999,0);assert not c['passed'] # Actual bytes alone are not script completion.
d=case(5,1,999);assert not d['passed'] and d['reason']=='guest_acknowledged_but_API_mismatch'
e=case(5,1,1,status=256);assert not e['passed'] and e['reason']=='guest_shutdown_failed'
print('AP103_ACK_AND_ORIGINAL_API16_BOUNDED_POLL_FIXED3S_REGRESSION_NEGATIVE_CASES_PASS')
