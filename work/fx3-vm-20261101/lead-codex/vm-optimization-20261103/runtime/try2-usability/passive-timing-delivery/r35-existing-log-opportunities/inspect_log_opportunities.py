from pathlib import Path
import json,re,hashlib
HERE=Path(__file__).resolve().parent
KEYS="id n tid pc object a18 a12 a13 r0 decision_a18 elapsed old_time new_time message type source observed_only".split()
rows=[]
for tag in ["r31","r28","r26","r26b"]:
 metadata=HERE.parent/"r32-zero-ring-causal-review"/(tag+"-ANALYSIS.json")
 j=json.loads(metadata.read_text());run=Path(j["run"]);source=run/"serial.log";data=source.read_bytes();cut=j["windows"]["comparison"]["cut"];prefix=data[:cut];complete=prefix.rfind(b"\n")+1;byid={};accepted=[];rejected=[]
 for m in re.finditer(rb"^FX3_UI_GATE_SAMPLE ([^\n]*)\n",prefix[:complete],re.M):
  parts=m.group(1).split();pairs=[v.split(b"=",1) for v in parts]
  good=(len(pairs)==len(KEYS) and all(len(x)==2 and x[0].decode(errors="replace")==key and re.fullmatch(rb"(?:-?[0-9]+|0x[0-9a-f]+)",x[1]) for x,key in zip(pairs,KEYS)))
  if not good:rejected.append(m.start());continue
  f={key:int(x[1],16) if x[1].startswith(b"0x") else int(x[1]) for x,key in zip(pairs,KEYS)}
  if f["observed_only"]!=1:rejected.append(m.start());continue
  v=byid.setdefault(str(f["id"]),{"records":0,"max_n":0,"last_offset":0});v["records"]+=1;v["max_n"]=max(v["max_n"],f["n"]);v["last_offset"]=m.start();accepted.append({"id":f["id"],"n":f["n"],"byte_offset":m.start()})
 rows.append({"tag":tag,"source":str(source),"source_sha256":hashlib.sha256(data).hexdigest(),"window_metadata":str(metadata),"window_metadata_sha256":hashlib.sha256(metadata.read_bytes()).hexdigest(),"cut":cut,"complete_line_prefix_end":complete,"accepted":len(accepted),"by_id":byid,"rejected_offsets":rejected,"last3":accepted[-3:]})
result={"scope":"Historical strictly complete original UI sample lines only; source order and numeric fields checked. No imports of runners or guest execution.","limitations":["Presence in these windows is not future scheduling or event-export assurance.","No wall-clock latency inferred from byte offsets.","Truncated/interleaved/extra-field lines rejected, not silently repaired.","No late output does not prove an event never occurred; no exact End claim."],"runs":rows}
(HERE/"opportunities.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
for r in rows:print(r["tag"],r["accepted"],"strict samples; rejected",len(r["rejected_offsets"]))
