from pathlib import Path
import sys,json,hashlib,datetime
run=Path(sys.argv[1]);step=int(sys.argv[2]);key=sys.argv[3];png=run/sys.argv[4];description=sys.argv[5];reason=sys.argv[6]
assert png.is_file() and key in {'0x3','0x30','0x15','0x1af','0x1ac','0x1ab','0x1f8'}
assert len(list((run/'vmopt-visual-decisions.jsonl').open()))==step-1 if (run/'vmopt-visual-decisions.jsonl').exists() else step==1
row={'step':step,'key':key,'hold_ms':100,'observed_page':description,'reason':reason,'authorization':'msg_7eb2cdbf663a','observed_png':str(png.resolve()),'observed_png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'viewed_by_worker':True,'decision_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(run/'vmopt-visual-decisions.jsonl').open('a').write(json.dumps(row,ensure_ascii=False)+'\n');(run/'ap102-next-key.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
print('queued one key',step,key,png)
