#ifndef FX3_OSD_CORE_V3_H
#define FX3_OSD_CORE_V3_H
#define HO_AP 0x8288076cU
#define HO_CONTROL 0x8280074dU
#define HO_PIXELS 0x8280084dU
#define HO_META 0x8280084eU
#define HO_BASE 0x41e000000UL
#define HO_RESERVE 0x1000000UL
#define HO_HEADER 0x10000UL
#define HO_SLOTS 8UL
#define HO_SLOT_STRIDE 0x180000UL
#define HO_DATA 0x100UL
#define HO_MAX 0x12c000UL
#define HO_MAGIC 0x31474e495244534fUL
struct ho_frame {unsigned long token,physical,format,width,height,stride,span,fb,bitmap,entry,allocation,metadata,fbformat,sem,config_hash,bitmapformat,bits,map_begin,map_end,map_offset;};
struct ho_model {unsigned pending,stage,failed,retained;unsigned long seq,duplicates,rejected,epoch,source_seq;unsigned char control[12],descriptor[36];struct ho_frame frame;};
static unsigned ho_u16(const unsigned char *p){return p[0]|(unsigned)p[1]<<8;}
static unsigned ho_u32(const unsigned char *p){return ho_u16(p)|ho_u16(p+2)<<16;}
static unsigned long ho_hash(const void *p,unsigned long n){const unsigned char *b=p;unsigned long h=14695981039346656037UL;while(n--){h^=*b++;h*=1099511628211UL;}return h;}
static int ho_control(struct ho_model *s,unsigned src,const unsigned char *p,unsigned n){static const unsigned char prefix[8]={2,16,0,0,0,0,0,0};if(s->failed||src!=HO_AP||n!=12||memcmp(p,prefix,8)||(ho_u32(p+8)!=0x1003&&ho_u32(p+8)!=0x1005)){s->rejected++;return -1;}if(s->pending){s->duplicates++;return 1;}if(ho_u32(p+8)==0x1005&&!s->retained){s->rejected++;return -1;}s->pending=ho_u32(p+8);s->stage=1;memcpy(s->control,p,12);return 0;}
static int ho_publish(struct ho_model *s,unsigned src,unsigned dst,const unsigned char *p,unsigned n){if(n<2||s->failed||src!=HO_AP||!s->pending){s->rejected++;return -1;}unsigned kind=ho_u16(p);if(kind!=s->pending||((kind==0x1003)&&(dst!=HO_PIXELS||n!=36))||((kind==0x1005)&&(dst!=HO_META||n!=8))){s->rejected++;return -1;}for(unsigned i=2;i<8;i++)if(p[i]){s->rejected++;return -1;}
 if(s->stage!=1){if(s->stage>=2&&(kind==0x1005||!memcmp(s->descriptor,p,36))){s->duplicates++;return 1;}s->rejected++;return -1;}
 if(kind==0x1003){unsigned w=ho_u16(p+20),h=ho_u16(p+22),x=ho_u16(p+24),y=ho_u16(p+26),rw=ho_u16(p+28),rh=ho_u16(p+30);if(ho_u32(p+12)!=1||ho_u16(p+16)>1||ho_u16(p+18)||!w||!h||w>640||h>480||x>w||y>h||rw>w-x||rh>h-y){s->rejected++;return -1;}memcpy(s->descriptor,p,36);}
 else if(!s->retained){s->rejected++;return -1;}s->stage=2;return 0;}
static int ho_cpu_mapping(unsigned long bits,unsigned long span,unsigned long physical,unsigned long begin,unsigned long end,unsigned long offset,const char perms[4],int devmem){return devmem&&perms[0]=='r'&&perms[3]=='s'&&span&&begin<end&&bits>=begin&&bits<end&&span<=end-bits&&offset<=~0UL-(bits-begin)&&offset+bits-begin==physical;}
static int ho_gpe_format(unsigned native){return native==1||native==7?0:native==2||native==8?1:-1;}
static int ho_validate(const struct ho_model *s,const struct ho_frame *f,unsigned long bitmap_bytes,int active_extent,unsigned long extent_base,unsigned long extent_bytes){if(s->failed||s->stage!=2||ho_gpe_format(f->bitmapformat)!=(int)f->format||f->format>1||!f->width||!f->height||f->width>640||f->height>480||f->stride<f->width||f->stride>4096||!f->fb||!f->bitmap||!f->allocation||!f->sem||!active_extent)return -1;unsigned long bpp=f->format?4:2,span=((f->height-1)*f->stride+f->width)*bpp;if(span>HO_MAX||span>bitmap_bytes||f->span!=span||extent_bytes<0x100||f->physical<extent_base+0x100||f->physical>=extent_base+extent_bytes||span>extent_base+extent_bytes-f->physical||f->physical%bpp)return -1;if(s->pending==0x1003&&(f->token!=ho_u32(s->descriptor+8)||f->width!=ho_u16(s->descriptor+20)||f->height!=ho_u16(s->descriptor+22)||(f->fbformat==2)!=ho_u16(s->descriptor+16)))return -1;return 0;}
static int ho_commit(struct ho_model *s,const struct ho_frame *f,int copied,int all_releases_ok){if(s->failed||s->stage!=2||!copied||!all_releases_ok)return -1;s->frame=*f;s->seq++;if(s->pending==0x1003){s->retained=1;s->source_seq=s->seq;}s->stage=3;return 0;}
static int ho_prepare_ack(struct ho_model *s,unsigned char out[8]){if(s->failed||s->stage!=3)return -1;memset(out,0,8);out[0]=s->pending&255;out[1]=0x60;s->stage=4;return 0;}
static void ho_send_failed(struct ho_model *s){s->failed=1;s->stage=5;}
static int ho_signal_begin(struct ho_model *s,unsigned sem,unsigned msg){if(s->failed||s->stage!=4||sem!=s->frame.sem||msg!=((s->pending&255)|0x6000))return -1;s->pending=0;s->stage=0;return 0;}
#endif
