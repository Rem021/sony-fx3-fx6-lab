from pathlib import Path
import struct,json,hashlib,sys,datetime as dt
MAGIC=0x314b434f4c433939

def decode(path):
 p=Path(path);b=p.read_bytes();assert len(b)==4096;h=struct.unpack_from('<8Q',b);out={'path':str(p.resolve()),'sha256':hashlib.sha256(b).hexdigest(),'bytes':4096,'header':list(h),'transactions':[],'scope':'Software CP clock and owned copies of native messages; no physicalCP address or RTC proof.'}
 if h[0]==MAGIC:
  assert h[1]==1;utc=struct.unpack_from('<q',b,40)[0];reason,errors=struct.unpack_from('<2Q',b,88);out['clock']={'generation':h[2],'valid_UTC':bool(h[3]),'monotonic_basis_ns':h[4],'UTC_base_ms':utc,'last_export_ns':h[6],'UTC_ms_at_last_export':utc+(h[6]-h[4])//1000000 if h[3] else None,'type4_sent_count':h[7],'native_date':b[64:80].hex(),'native_timezone':b[80:88].hex(),'reason':reason,'errors':errors,'synthetic_cp_clock':True,'original_CP_executed':False,'physical_RTC_written':False}
 else:out['clock']=None
 for i in range(14):
  r=b[512+i*256:512+(i+1)*256];seq,serial=struct.unpack_from('<2Q',r)
  if not serial:continue
  reason,source,Q,stage,rc,fr=struct.unpack_from('<4I2i',r,16);gen,started,ended=struct.unpack_from('<3Q',r,40);valid,sent=struct.unpack_from('<2I',r,240);ready=r[64:108];request=r[108:152];reply=r[152:196];done=r[196:240];rq=struct.unpack_from('<I',request,12)[0];sq=struct.unpack_from('<I',reply,12)[0]
  out['transactions'].append({'slot':i,'sequence':seq,'published_stable':seq%2==0,'serial':serial,'reason':reason,'actual_AP_source':hex(source),'Q_field_after_cleanup':hex(Q),'type2_embedded_Q':hex(rq),'reply_embedded_Q':hex(sq),'stage':stage,'return':rc,'native_original_request_free':fr,'clock_generation':gen,'start_ns':started,'end_ns':ended,'UTC_valid':bool(valid),'type4_sent':bool(sent),'ready44':ready.hex(),'type2_request44':request.hex(),'native_AP_type2_reply44':reply.hex(),'type4_done44':done.hex() if any(done) else None,'type2_reply_status_s32':struct.unpack_from('<i',reply,4)[0],'type2_dynamic_Q_matches':rq!=0 and rq==sq,'native_AP_reply_datetime16':reply[16:32].hex(),'native_AP_reply_timezone8':reply[32:40].hex(),'reason4_no_type4':reason==4 and not sent and not any(done),'retired_success':stage==6 and rc==0 and fr==0})
 out['transactions'].sort(key=lambda x:x['serial']);return out
if __name__=='__main__':
 v=decode(sys.argv[1]);o=Path(sys.argv[2]) if len(sys.argv)>2 else None
 if o:o.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(v,ensure_ascii=False,indent=2))
