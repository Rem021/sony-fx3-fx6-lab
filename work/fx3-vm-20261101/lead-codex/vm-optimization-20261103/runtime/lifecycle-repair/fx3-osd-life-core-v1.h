#ifndef FX3_OSD_LIFE_CORE_V1
#define FX3_OSD_LIFE_CORE_V1
#define LP_LIMIT 8192
struct lp_record{unsigned long pointer,serial;unsigned destination,bytes,op,sent;};
struct lp_model{struct lp_record records[LP_LIMIT];unsigned long allocations,returns,sends,frees,reuses,live,drops,sequence,pair_started;unsigned pending,failed;};
static unsigned lp_role(unsigned dst,unsigned n,unsigned long native_caller){return dst==0x8280074dU&&n==12&&native_caller==0xf1db8?0x1002:dst==0x8280084dU&&n==36&&native_caller==0xf1e44?0x1003:dst==0x8280084eU&&n==8&&native_caller==0xf1d2c?0x1005:0;}
static int lp_return(struct lp_model *m,unsigned long pointer,unsigned dst,unsigned n,unsigned op,int rc){m->returns++;if(rc||!pointer)return -1;int free=-1;for(unsigned j=0;j<LP_LIMIT;j++){if(m->records[j].pointer==pointer){m->reuses++;free=j;m->live--;break;}if(!m->records[j].pointer&&free<0)free=j;}if(free<0){m->drops++;return -2;}m->records[free]=(struct lp_record){pointer,m->returns,dst,n,op,0};m->live++;return free;}
static int lp_sent(struct lp_model *m,unsigned long pointer,unsigned dst,unsigned op){for(unsigned j=0;j<LP_LIMIT;j++)if(m->records[j].pointer==pointer&&m->records[j].destination==dst&&m->records[j].op==op){m->records[j].sent++;m->sends++;return j;}return -1;}
static int lp_freed(struct lp_model *m,unsigned long pointer,unsigned dst,int rc){if(rc)return -1;for(unsigned j=0;j<LP_LIMIT;j++)if(m->records[j].pointer==pointer&&m->records[j].destination==dst){memset(m->records+j,0,sizeof m->records[j]);m->frees++;m->live--;return j;}return -1;}
static int lp_control(struct lp_model *m,unsigned next,unsigned long now){if(m->failed||m->pending||(next!=0x1003&&next!=0x1005)||!now)return -1;m->pending=next;m->pair_started=now;m->sequence++;return 0;}
static int lp_descriptor(struct lp_model *m,unsigned kind){if(m->failed||m->pending!=kind)return -1;m->pending=0;m->pair_started=0;return 0;}
static int lp_expired(const struct lp_model *m,unsigned long now){return !m->failed&&m->pending&&now>=m->pair_started&&now-m->pair_started>=2000000000UL;}
#endif
