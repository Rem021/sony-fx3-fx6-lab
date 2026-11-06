"""Ordinary Mac fixture process: reserve owner once, never remove the fence."""
from pathlib import Path
import json,os,sys
from live_arbiter import LiveArbiter,Denied
try:o=LiveArbiter.attach(Path(sys.argv[1]),fixture_only=True)
except (Denied,FileExistsError):
    print(json.dumps({'pid':os.getpid(),'claimed':False}),flush=True);raise SystemExit(0)
print(json.dumps({'pid':os.getpid(),'claimed':True}),flush=True)
assert sys.stdin.readline()=='EXIT\n'
o.close()
