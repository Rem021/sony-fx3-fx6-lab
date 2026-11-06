from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-osd-lifetime-v1.c').read_text()
s=s.replace('Pair deadline only fails an exact still-pending headless software transaction.','Pair deadline only fails an exact still-pending headless software transaction; active allocator deadline also records blocked76c ACK/local calls.')
s=s.replace('static unsigned lock,ready,started;','static unsigned lock,ready,started;static void start_watch(void);')
s=s.replace('if(expired){int rc=', '''unsigned blocked=0;U blocked_age=0;enter();for(unsigned i=0;i<8;i++)if(active[i].sequence&&now>=active[i].since&&now-active[i].since>=2000000000UL){blocked=1;blocked_age=now-active[i].since;break;}leave();if(blocked){dprintf(2,"FX3_OSD_ALLOC_DEADLINE age_ns=%lu no_ACK_added=1 original_call_still_waiting=1\\n",blocked_age);stacks();pools("allocation-deadline");dprintf(2,"FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END diagnostic_only=1\\n");return 0;}if(expired){int rc=''')
a=s.index('static unsigned packet(');s=s[:a]+'''static void start_watch(void){enter();if(started){leave();return;}started=1;leave();U t=0;if(pthread_create(&t,0,watcher,0)){dprintf(2,"FX3_OSD_LIFE_WATCHER_FAILED no_protocol_change=1\\n");return;}pthread_detach(t);}\n'''+s[a:]
needle='op=lp_role(dst,n,caller-(U)di.base);if(op)'
assert needle in s;s=s.replace(needle,'op=lp_role(dst,n,caller-(U)di.base);if(enabled()&&dst==0x8288076cU&&(n==8||n==40)){dladdr((void *)caller,&di);op=n==8?0x6008:0x7040;}if(op)')
s=s.replace('caller-(U)di.base);}*__errno_location()=saved;int rc=alloc_next','di.base?caller-(U)di.base:caller);start_watch();}*__errno_location()=saved;int rc=alloc_next')
s=s.replace('dst==0x8280084eU)){n=size_next','dst==0x8280084eU||dst==0x8288076cU)){n=size_next')
s=s.replace('op=packet(dst,src,b,n);','op=packet(dst,src,b,n);if(dst==0x8288076cU&&((n==8&&(b[0]==3||b[0]==5)&&b[1]==0x60)||n==40))op=n==8?0x6008:0x7040;')
s=s.replace('else lp_descriptor(&ledger,op);','else if(op==0x1003||op==0x1005)lp_descriptor(&ledger,op);')
s=s.replace('dst!=0x8280084eU)){','dst!=0x8280084eU&&dst!=0x8288076cU)){')
# Retire before forwarding free: native pointer reuse may happen before free returns.
a=s.index('int osal_free_msg(');s=s[:a]+r'''int osal_free_msg(unsigned dst,void *p){int saved=*__errno_location();init();if(!free_next)return -1021;struct lp_record retired={0};int tracked=0;if(enabled()&&p&&(dst==0x8280074dU||dst==0x8280084dU||dst==0x8280084eU||dst==0x8288076cU)){enter();for(unsigned i=0;i<LP_LIMIT;i++)if(ledger.records[i].pointer==(U)p&&ledger.records[i].destination==dst){retired=ledger.records[i];memset(ledger.records+i,0,sizeof ledger.records[i]);ledger.live--;tracked=1;break;}leave();}*__errno_location()=saved;int rc=free_next(dst,p);int after=*__errno_location();if(tracked){enter();int record=0;if(!rc)ledger.frees++;else{int vacant=-1;for(unsigned i=0;i<LP_LIMIT;i++){if(ledger.records[i].pointer==(U)p){record=-2;break;}if(!ledger.records[i].pointer&&vacant<0)vacant=i;}if(!record&&vacant>=0){ledger.records[vacant]=retired;ledger.live++;}else ledger.drops++;}U count=ledger.frees,live=ledger.live;leave();dprintf(2,"FX3_OSD_LIFE_USER_FREE destination=%#x pointer=%p role=%x result=%d record=%d count=%lu tracked_live=%lu retired_before_native_free=1 original_call_forwarded=1\n",dst,p,retired.op,rc,record,count,live);}*__errno_location()=after;return rc;}
'''
(H/'fx3-osd-lifetime-v2.c').write_text(s)
s=(R/'build_lifetime86.py').read_text().replace('fx3-osd-lifetime-v1','fx3-osd-lifetime-v2');(R/'build_life86b.py').write_text(s)
