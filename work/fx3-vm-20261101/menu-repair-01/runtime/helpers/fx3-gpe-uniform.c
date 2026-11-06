/* FX3 libgpe c30c: uniform overwrite subset, no blit/blend approximation. */
struct uniform_plan {unsigned long address,offset,pitch,line,span;unsigned int rows;unsigned char value;};
static int uniform_plan(const unsigned int *p,struct uniform_plan *o){
 if(!p||!o)return 5;const unsigned char *r=(const unsigned char *)p;
 if(p[7]>1||r[36]||r[37]!=255||r[38]||r[39])return 5;
 for(unsigned int i=40;i<56;i++)if(r[i])return 5; /* no deferred callback */
 unsigned int x=p[2],y=p[3],w=p[4],h=p[5],stride=p[6],bpp=p[7]?4:2;
 if(!w||!h||w>8192||h>8192||stride>16384||!stride||x>stride||w>stride-x||y>16383)return 5;
 if(r[32]!=r[33]||r[32]!=r[34]||r[32]!=r[35])return 5;
 struct uniform_plan z={0};z.address=(unsigned long)p[0]|((unsigned long)p[1]<<32);z.pitch=(unsigned long)stride*bpp;z.offset=(unsigned long)y*z.pitch+(unsigned long)x*bpp;z.line=(unsigned long)w*bpp;z.rows=h;z.span=z.offset+(h-1UL)*z.pitch+z.line;z.value=p[7]?r[32]:(unsigned char)((r[32]&240)|(r[32]>>4));
 if(z.address<0x43feb5100UL||z.address>=0x43fff5000UL||z.span>0x43fff5000UL-z.address)return 5;*o=z;return 0;
}
static void uniform_write(unsigned char *p,const struct uniform_plan *z){for(unsigned int y=0;y<z->rows;y++)for(unsigned long x=0;x<z->line;x++)p[z->offset+y*z->pitch+x]=z->value;}
