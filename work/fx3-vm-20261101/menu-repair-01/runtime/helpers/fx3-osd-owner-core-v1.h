#ifndef FX3_OSD_OWNER_CORE_V1
#define FX3_OSD_OWNER_CORE_V1
struct qo_lease{unsigned long pointer,stamp,sequence;unsigned destination,source,bytes,phase;unsigned char raw[96];};
struct qo_model{struct qo_lease leases[3];unsigned long serial,received[3],freed[3],unknown,stale,GUI,errors;};
static int qo_index(unsigned dst){return dst==HO_CONTROL?0:dst==HO_PIXELS?1:dst==HO_META?2:-1;}
static unsigned qo_publication(unsigned dst,unsigned src,const unsigned char *p,unsigned n){if(src!=HO_AP||n<8)return 0;unsigned op=ho_u16(p);for(unsigned j=2;j<8;j++)if(p[j])return 0;if(dst==HO_CONTROL&&op==0x1002&&n==12&&(ho_u32(p+8)==0x1003||ho_u32(p+8)==0x1005))return op;if(dst==HO_PIXELS&&op==0x1003&&n==36)return op;if(dst==HO_META&&op==0x1005&&n==8)return op;return 0;}
static unsigned long qo_register(struct qo_model *m,unsigned dst,unsigned src,const unsigned char *p,unsigned n,unsigned long pointer,unsigned long seq){int i=qo_index(dst);if(i<0||!pointer||n>96||!qo_publication(dst,src,p,n))return 0;if(m->leases[i].pointer){m->errors++;return 0;}struct qo_lease *q=m->leases+i;q->pointer=pointer;q->stamp=++m->serial;q->sequence=seq;q->destination=dst;q->source=src;q->bytes=n;q->phase=1;memcpy(q->raw,p,n);return q->stamp;}
static int qo_confirm(struct qo_model *m,unsigned dst,unsigned long p,unsigned long stamp,int result){int i=qo_index(dst);if(i<0)return -1;struct qo_lease *q=m->leases+i;if(q->pointer!=p||q->stamp!=stamp)return -1;q->phase=result?3:2;return 0;}
/* 1=send still in flight,0=current exact accepted publication,-1=old/foreign/failed. */
static int qo_match(const struct qo_model *m,unsigned dst,unsigned src,const unsigned char *p,unsigned n,unsigned long pointer,unsigned long seq){int i=qo_index(dst);if(i<0)return -1;const struct qo_lease *q=m->leases+i;if(q->pointer!=pointer||q->sequence!=seq||q->destination!=dst||q->source!=src||q->bytes!=n||n>96||memcmp(q->raw,p,n))return -1;return q->phase==1?1:q->phase==2?0:-1;}
/* Retire BEFORE native free, so immediate native pointer reuse cannot erase a new lease. */
static void qo_retire(struct qo_model *m,unsigned dst,unsigned long p){int i=qo_index(dst);if(i>=0&&m->leases[i].pointer==p)memset(m->leases+i,0,sizeof m->leases[i]);}
static int qo_GUI(unsigned dst,unsigned src,const unsigned char *p,unsigned n,unsigned *offset){if(dst!=HO_CONTROL||src!=0x9088076bU||n<8)return 0;unsigned op=ho_u16(p);if(op==0x1000&&n==80&&ho_u32(p+12)<=16){*offset=0;return 80;}if(op==0x1001&&n==96&&ho_u16(p+8)<256&&ho_u32(p+28)<=16){*offset=80+ho_u16(p+8)*96;return 96;}if(op==0x1004&&n==16){*offset=80+256*96;return 16;}return 0;}
#endif
