from pathlib import Path
import sys,time
p=Path(sys.argv[1]);end=time.monotonic()+20
while time.monotonic()<end:
 if p.is_file() and p.stat().st_size>0:print(p);sys.exit(0)
 if (p.parent/'receipt.json').exists():raise SystemExit('Run ended before requested frame')
 time.sleep(.25)
raise SystemExit('Frame not yet available')
