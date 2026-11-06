#include <stdarg.h>
typedef struct _IO_FILE FILE;
#include <string.h>
#include <unistd.h>
FILE *stderr=(FILE*)2;
static void out(int fd,const char*s,size_t n){(void)write(fd,s,n);}
static int fmt(char*out,size_t cap,const char*fmt,va_list ap){
 size_t n=0;
 for(;*fmt;fmt++){
  if(*fmt!='%'){if(n+1<cap)out[n]=*fmt;n++;continue;}
  fmt++;int width=0,zero=0;if(*fmt=='0'){zero=1;fmt++;}while(*fmt>='0'&&*fmt<='9'){width=width*10+(*fmt-'0');fmt++;}
  if(*fmt=='s'){const char*s=va_arg(ap,const char*);if(!s)s="(null)";for(;*s;s++){if(n+1<cap)out[n]=*s;n++;}continue;}
  if(*fmt=='c'){char c=(char)va_arg(ap,int);if(n+1<cap)out[n]=c;n++;continue;}
  unsigned long long v=0;int neg=0;
  if(*fmt=='d'||*fmt=='l'){if(*fmt=='l')fmt++;if(*fmt=='d'){long x=va_arg(ap,long);if(x<0){neg=1;v=(unsigned long long)(-x);}else v=(unsigned long long)x;}}
  else if(*fmt=='z'&&fmt[1]=='u'){fmt++;v=va_arg(ap,size_t);}
  else if(*fmt=='l'&&fmt[1]=='l'&&(fmt[2]=='u'||fmt[2]=='x')){int hx=fmt[2]=='x';fmt+=2;v=va_arg(ap,unsigned long long);char tmp[32];int k=0;do{unsigned d=v&15;tmp[k++]="0123456789abcdef"[d];v>>=4;}while(v);for(int j=0;j<width-k;j++){if(n+1<cap)out[n]='0';n++;}while(k){if(n+1<cap)out[n]=tmp[--k];n++;} (void)hx;continue;}
  else if(*fmt=='u'){v=va_arg(ap,unsigned);}else {if(n+1<cap)out[n]='%';n++;continue;}
  char tmp[32];int k=0;do{unsigned d=v%10;tmp[k++]='0'+d;v/=10;}while(v);if(neg){if(n+1<cap)out[n]='-';n++;}for(int j=0;j<width-k;j++){if(n+1<cap)out[n]='0';n++;}while(k){if(n+1<cap)out[n]=tmp[--k];n++;}
 }
 if(cap)out[n<cap?n:cap-1]=0;return (int)n;
}
int printf(const char*f,...){char b[8192];va_list ap;va_start(ap,f);int n=fmt(b,sizeof b,f,ap);va_end(ap);out(1,b,n);return n;}
int fprintf(FILE*s,const char*f,...){char b[8192];va_list ap;va_start(ap,f);int n=fmt(b,sizeof b,f,ap);va_end(ap);out(s==stderr?2:1,b,n);return n;}
int snprintf(char*out,size_t cap,const char*f,...){va_list ap;va_start(ap,f);int n=fmt(out,cap,f,ap);va_end(ap);return n;}
int putchar(int c){unsigned char x=(unsigned char)c;out(1,(char*)&x,1);return c;}
int __uflow(FILE*f){(void)f;return -1;}
int __overflow(FILE*f,int c){(void)f;(void)c;return -1;}
