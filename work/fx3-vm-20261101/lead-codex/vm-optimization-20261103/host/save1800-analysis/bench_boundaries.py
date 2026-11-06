"""Measure host predicate CPU on immutable prefixes at the two GPE bounds."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bench_save1800 import SERIAL,SHA,actual_regex
from guarded_reject import ASSERT,RM,guarded_rejects


def timed(fn):
    t=time.process_time_ns();v=fn();return v,round((time.process_time_ns()-t)/1e6,3)


def main():
    data=SERIAL.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
    rows=[]
    for seq in (6329,7545):
        marker=f'seq={seq} completion_source='.encode()
        pos=data.find(marker)
        assert pos>=0
        end=data.find(b'\n',pos)
        text=data[:end+1].decode(errors='replace')
        full,full_ms=timed(lambda:actual_regex(text))
        old_pair,old_pair_ms=timed(lambda:(bool(ASSERT.search(text)),bool(RM.search(text))))
        guard_pair,guard_ms=timed(lambda:guarded_rejects(text))
        assert old_pair==guard_pair
        rows.append({'seq':seq,'prefix_bytes':end+1,'decoded_chars':len(text),
                     'full_actual_predicate_cpu_ms':full_ms,'old_two_reject_cpu_ms':old_pair_ms,
                     'guarded_two_reject_cpu_ms':guard_ms,'decisions_equal':True,
                     'diagnostic_seen':full['diagnostic']})
    samples=50;start=time.process_time_ns();wall=time.perf_counter_ns()
    for _ in range(samples):
        subprocess.run(['ps','-o','rss=,vsz=','-p',str(os.getpid())],capture_output=True,text=True,check=True)
    ps_cpu=(time.process_time_ns()-start)/1e6;ps_wall=(time.perf_counter_ns()-wall)/1e6
    result={'serial_sha256':SHA,'prefixes':rows,'ps_samples':samples,
            'ps_parent_cpu_ms':round(ps_cpu,3),'ps_wall_ms':round(ps_wall,3),
            'note':'ps targets this benchmark PID; process lifecycle and QEMU load differ'}
    (HERE/'boundary-bench.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
