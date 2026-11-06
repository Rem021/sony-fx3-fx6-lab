#include <stdio.h>
#include <string.h>
#include <assert.h>
static unsigned blend_markers,reject_records,unavailable_records;
static char last_hex[289];
static int captured_fputs(const char *s,FILE *f){
 if(strstr(s,"FX3_GPE_CMD op=" )&&strstr(s,"approx_blend=1")){assert(strstr(s,"formula=straight_over_v1"));blend_markers++;}
 if(strstr(s,"FX3_GPE_REJECT_PARAMS")){
  reject_records++;const char *p=strstr(s,"raw_hex=");assert(p);p+=8;
  if(!strncmp(p,"unavailable",11))unavailable_records++;
  else {size_t n=strcspn(p,"\n");assert(n<sizeof(last_hex));memcpy(last_hex,p,n);last_hex[n]=0;}
 }
 return fputs(s,f);
}
#define fputs captured_fputs
#define main retained_v13_main
#include "check-adapter-v14-guard-base.c"
#undef main
#undef fputs
static void mkblit14(unsigned char *p,unsigned fmt){
 memset(p,0,144);p64(p,PAYLOAD_BASE+0x400);p64(p+56,PAYLOAD_BASE);p32(p+16,2);p32(p+20,2);
 p32(p+32,2);p32(p+36,2);p32(p+48,4);p32(p+52,fmt);p32(p+72,2);p32(p+76,2);p32(p+88,5);p32(p+92,fmt);
 p[112]=1;p[114]=127;p[121]=1;
}
static void check_hex(const unsigned char *p,unsigned n){
 char want[289];const char *digits="0123456789abcdef";
 for(unsigned i=0;i<n;i++){want[2*i]=digits[p[i]>>4];want[2*i+1]=digits[p[i]&15];}want[2*n]=0;assert(!strcmp(want,last_hex));
}
int fx3_original_test_main(void){
 physical=80;process_mem=80;draw_complete=complete;unsigned char p[144],f[24]={0};
 reset();seen=1000;mkfill(p,1);p[36]=1;p[35]=1;p[38]=0;p64(p+40,(U)callback);p64(p+48,0xabc);
 p32(memory+0x100,0x03abef43);unsigned bm=blend_markers,cb=callbacks,st=statuses;
 assert(fill(0,0,100,0x123,p)==0);assert(callbacks==cb+1&&statuses==st+1&&order==2);
 assert(lastcb.sequence==100&&lastcb.argument==0xabc&&laststatus==0);assert(memory[0x100]==0x44);
 assert(blend_markers==bm+1);order=0;assert(flush(0,0,101,0x123,f)==0&&laststatus==0);
 /* New supported blend and flip paths still share v13's bounded extent and
  * original Main failure completion rules. Every reject has full raw bytes. */
 for(unsigned t=0;t<13;t++){
  reset();mkblit14(p,1);
  if(t==0)p64(p,PAYLOAD_BASE-1);if(t==1)p64(p+56,EXT_BASE+EXT_BYTES);
  if(t==2)p64(p,EXT_BASE+EXT_BYTES-20);if(t==3)p[115]=1;
  if(t==4)p[116]=1;if(t==5)p[117]=16;if(t==6)p[118]=1;
  if(t==7)p[119]=2;if(t==8)p[120]=255;if(t==9)p[112]=2;
  if(t==10)p32(p+92,0);if(t==11)p32(p+104,1);if(t==12)p[113]=4;
  memcpy(before,memory,sizeof(memory));unsigned rr=reject_records;st=statuses;seen=5000;
  assert(blit(0,0,200+t,0x123,p)==5&&statuses==st);assert(!memcmp(before,memory,sizeof(memory)));
  assert(reject_records==rr+1);check_hex(p,144);
 }
 reset();mkfill(p,0);p[36]=2;p[37]=127;p64(p,EXT_BASE);unsigned rr=reject_records;memcpy(before,memory,sizeof(memory));
 assert(fill(0,0,250,0,p)==5&&!memcmp(before,memory,sizeof(memory)));assert(reject_records==rr+1);check_hex(p,56);
 reset();mkfill(p,1);badread=1;rr=unavailable_records;assert(fill(0,0,251,0,p)==5);assert(unavailable_records==rr+1);
 for(unsigned fmt=0;fmt<2;fmt++)for(unsigned flip=0;flip<4;flip++){
  reset();mkblit14(p,fmt);unsigned bpp=fmt?4:2;p[114]=255;p[119]=flip&1;p[120]=(flip>>1)&1;
  for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++){
   unsigned v=fmt?0x123456ff+(y*2+x)*0x10000:0x135f+(y*2+x)*0x100;
   memcpy(memory+0x100+(y*5+x)*bpp,&v,bpp);
  }
  memcpy(before,memory,sizeof(memory));
  for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++){
   unsigned sx=(flip&1)?1-x:x,sy=(flip&2)?1-y:y;
   memcpy(before+0x500+(y*4+x)*bpp,memory+0x100+(sy*5+sx)*bpp,bpp);
  }
  bm=blend_markers;assert(blit(0,0,300+flip,0,p)==0);assert(!memcmp(memory,before,sizeof(memory)));assert(blend_markers==bm+1);
 }
 /* At >200, every accepted approximate command emits its own formula marker. */
 reset();seen=10000;mkfill(p,0);p[36]=2;p[37]=127;bm=blend_markers;
 for(unsigned i=0;i<257;i++)assert(fill(0,0,400+i,0,p)==0);assert(blend_markers==bm+257);
 printf("PASS adapter-v14 blend_markers=%u rejected_full_params=%u unavailable=%u completion/extent/flip/throttle checks ASan/UBSan enabled\n",blend_markers,reject_records,unavailable_records);return 0;
}

int main(void){int result=fx3_original_test_main();assert(fx3_gpe_snapshot_unlock()==-1);assert(!fx3_gpe_snapshot_trylock());assert(fx3_gpe_snapshot_trylock()==-1);assert(command_lock);assert(command(0,0,0,0,0,0)==5);assert(!fx3_gpe_snapshot_unlock());assert(!command_lock);assert(fx3_gpe_snapshot_unlock()==-1);return result;}
