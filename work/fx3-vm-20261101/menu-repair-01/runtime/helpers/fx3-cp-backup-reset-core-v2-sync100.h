/* FX3 pinned BK4 CP software profile. No native CP execution claimed. */
typedef unsigned char B; typedef unsigned int W; typedef unsigned long U;
#define CP_BANK_BYTES 1369580U
#define CP_BANK_PHYS 0x4040d2000UL
static W rd16(const B*p){return (W)p[0]|(W)p[1]<<8;}
static W rd32(const B*p){return rd16(p)|rd16(p+2)<<16;}
static void wr32(B*p,W v){for(unsigned i=0;i<4;i++)p[i]=(B)(v>>(8*i));}
static void cp_copy(B*d,const B*s,U n){for(U i=0;i<n;i++)d[i]=s[i];}
static int cp_equal(const B*a,const B*b,U n){for(U i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static U cp_digest(const B*p,U n){U h=14695981039346656037UL;for(U i=0;i<n;i++){h^=p[i];h*=1099511628211UL;}return h;}
struct cp_entry{W key,attribute,offset,size,maximum,unit,repeat,copies,default_offset;};
struct cp_stats{W selected,repeat_items,changed,copies;U before,after;};
static int cp_header(const B*b,U n,int checksum){
 if(!b||n!=CP_BANK_BYTES||rd32(b)!=0x04000000||rd32(b+4)!=0xaaaaaaaa||(b[8]!=0||b[9]>1||b[10]!=0||b[11]!=0)||rd32(b+12)!=0x00344b42||rd32(b+16)!=819||rd32(b+20)!=31197||rd32(b+24)!=192384||rd32(b+28)!=1177196)return -7;
 if(256UL+6UL*(rd32(b+16)+rd32(b+20))>rd32(b+24))return -7;
 if(checksum){W sum=0;for(U i=0;i<n;i++)if(i<32||i>=36)sum+=b[i];if(sum!=rd32(b+32))return -7;}return 0;
}
/* Decode every row, including unselected and variable-capacity rows. */
static int cp_entry_at(const B*b,W sid,W pid,W index,struct cp_entry*e){
 W at=256+6*819+(index+pid)*6,attr=rd16(b+at),ptr=rd32(b+at+2);if(ptr==0xffffffff)return 1;
 W size=ptr>>24,offset=ptr&0xffffff,maximum=0;
 if(offset<192384||offset>=CP_BANK_BYTES)return -7;
 if(size==255){if(offset>CP_BANK_BYTES-2)return -7;size=rd16(b+offset);offset+=2;}
 else if(!size){if(offset>CP_BANK_BYTES-4)return -7;size=rd16(b+offset);maximum=rd16(b+offset+2);offset+=4;if(size>maximum)return -7;}
 W capacity=maximum?maximum:size;if(offset>CP_BANK_BYTES||capacity>CP_BANK_BYTES-offset)return -7;
 *e=(struct cp_entry){(sid<<16)|pid,attr,offset,size,maximum,0,0,0,0};return 0;
}
static int cp_validate(const B*b,int checksum){
 if(cp_header(b,CP_BANK_BYTES,checksum))return -7;W repeat=0,found=0;
 for(W sid=0;sid<819;sid++){W cnt=rd16(b+256+sid*6),idx=rd32(b+258+sid*6);if(idx>31197||cnt>31197-idx)return -7;
  for(W pid=0;pid<cnt;pid++){struct cp_entry e;int rc=cp_entry_at(b,sid,pid,idx,&e);if(rc<0)return rc;if(rc)continue;
   if(e.key==0x003e000c){if(e.size!=1||e.maximum)return -7;repeat=b[e.offset]+1;found++;}
  }
 }return found==1&&repeat==4?0:-7;
}
#ifndef CP_ITEM_TRACE
#define CP_ITEM_TRACE(e,flag,changed) ((void)0)
#endif
static int cp_reset(B*b,W flag,struct cp_stats*s){
 if(!s||cp_validate(b,0)||(flag!=1&&flag!=4))return -7;
 *s=(struct cp_stats){0};s->before=cp_digest(b,CP_BANK_BYTES);W mask=flag==1?0x40:4;
 /* Two passes: all selected default bounds before any mutation. */
 for(unsigned pass=0;pass<2;pass++)for(W sid=0;sid<819;sid++){W cnt=rd16(b+256+sid*6),idx=rd32(b+258+sid*6);
  for(W pid=0;pid<cnt;pid++){struct cp_entry e;int rc=cp_entry_at(b,sid,pid,idx,&e);if(rc<0)return rc;if(rc||!(e.attribute&mask))continue;
   if(e.maximum)return -7;e.repeat=e.attribute&128?4:1;if(e.size%e.repeat)return -7;e.unit=e.size/e.repeat;e.copies=flag==1?e.repeat:1;e.default_offset=e.offset+e.size;
   if(e.default_offset>CP_BANK_BYTES||e.unit>CP_BANK_BYTES-e.default_offset)return -7;
   if(pass){int changed=0;for(W copy=0;copy<e.copies;copy++){B*d=b+e.offset+copy*e.unit;const B*src=b+e.default_offset;if(!cp_equal(d,src,e.unit))changed=1;cp_copy(d,src,e.unit);if(!cp_equal(d,src,e.unit))return -7;}s->selected++;s->copies+=e.copies;s->repeat_items+=e.repeat>1;s->changed+=changed;CP_ITEM_TRACE(&e,flag,changed);}
  }
 }
 if(s->selected!=(flag==1?317U:2U)||s->repeat_items!=(flag==1?2U:0U))return -7;s->after=cp_digest(b,CP_BANK_BYTES);return 0;
}
