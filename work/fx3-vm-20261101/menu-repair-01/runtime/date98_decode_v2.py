from pathlib import Path
import json,struct,hashlib,sys
MAGIC=0x3130383945544144;SIZE=0x6000;CAP=64;REC=320

def decode(path):
 p=Path(path);b=p.read_bytes();assert len(b)==SIZE;head=struct.unpack_from('<8Q',b);out={'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'header':list(head),'records':[]}
 if head[0]==0:out['status']='not_yet_bound';return out
 assert head[:4]==(MAGIC,1,CAP,REC),head
 out['status']='bound';out['event_count']=head[4];out['dropped']=head[5]
 for i in range(min(head[4],CAP)):
  r=b[64+i*REC:64+(i+1)*REC];seq,event=struct.unpack_from('<2Q',r);pid,tid,dst,n=struct.unpack_from('<4I',r,16);pointer,caller=struct.unpack_from('<2Q',r,32);state,rc,err,before,after,bm,am,kind=struct.unpack_from('<Iii5I',r,48);start,end=struct.unpack_from('<2Q',r,80);assert event==i+1
  def model(off):
   f,fn,fv,d,dn,dm=struct.unpack_from('<6I',r,off);return {'force_current':f,'force_next':fn,'force_valid':bool(fv),'date_current':d,'date_next':dn,'date_read_mask':dm}
  out['records'].append({'slot':i,'sequence':seq,'published_stable':seq in [2,4],'event':event,'kind':'original_user_sync' if kind==1 else 'kernel_CP_dispatch' if kind==2 else str(kind),'pid':pid,'tid':tid,'destination':hex(dst),'bytes':n,'pointer':hex(pointer),'caller':hex(caller),'state':'native_call_returned' if state==2 and kind==1 else 'copy_complete_before_unchanged_fallback_return0_not_CP_completion' if state==2 and kind==2 else 'entered_no_return_observed','native_return':rc if state==2 and kind==1 else None,'unchanged_fallback_branch_value':rc if kind==2 else None,'native_return_observed':state==2 and kind==1,'native_errno':err if state==2 and kind==1 else None,'before_captured':bool(before),'after_captured':bool(after),'before_method':bm,'after_method':am,'before_raw':r[192:192+n].hex() if before and n<=64 else None,'after_raw':r[256:256+n].hex() if after and n<=64 else None,'start_ns':start,'end_ns':end,'live_before':model(96) if kind==1 else None,'live_after':model(120) if kind==1 and state==2 else None,'original_state_writes':False,'CP_reply_added':False})
 return out
if __name__=='__main__':
 q=decode(sys.argv[1]);out=Path(sys.argv[2]) if len(sys.argv)>2 else None
 if out:out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(q,ensure_ascii=False,indent=2))
