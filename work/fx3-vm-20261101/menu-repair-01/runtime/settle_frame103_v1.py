"""Wait for completed one-key capture, request an additional read-only frame.
Does not choose or send keys. Worker must view the result before next decision.
"""
from pathlib import Path
import sys,time,json
R=Path(__file__).resolve().parent;run=Path(sys.argv[1]).resolve();step=int(sys.argv[2]);assert run.parent==R/'runs' and 1<=step<=30
end=time.monotonic()+30
while time.monotonic()<end:
 if (run/'receipt.json').exists():raise SystemExit('Run ended')
 p=run/'ap102-step-readbacks.json'
 if p.exists() and any(x['step']==step and not x.get('error')for x in json.loads(p.read_text())):break
 time.sleep(.25)
else:raise SystemExit('No completed per-step readback')
time.sleep(4)
assert not(run/'receipt.json').exists();label='step-%02d-settled'%step;request=run/'ap102-capture-current.json';temp=run/'ap103-settle.tmp';temp.write_text(json.dumps({'step':step,'label':label}));temp.replace(request);p=run/('ap102-'+label+'.png');end=time.monotonic()+20
while time.monotonic()<end:
 if p.exists():print(p);break
 if(run/'receipt.json').exists():raise SystemExit('Run ended before extra frame')
 time.sleep(.25)
else:raise SystemExit('No additional frame yet')
