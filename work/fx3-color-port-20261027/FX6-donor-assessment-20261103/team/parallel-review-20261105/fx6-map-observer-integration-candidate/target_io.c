#include <errno.h>
#include <stdarg.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>
typedef struct _IO_FILE FILE;
FILE *stderr=(FILE*)2;
static int write_all(int fd,const char*b,size_t n){size_t off=0;int retry=0;while(off<n){ssize_t r=write(fd,b+off,n-off);if(r<0){if(errno==EINTR&&retry++<3)continue;return -1;}if(r==0)return -1;off+=(size_t)r;}return 0;}
static void putc_buf(char*out,size_t cap,size_t *used,int *total,char c){if(*used+1<cap)out[*used]=c;(*used)++;(*total)++;}
static int emit_fmt(char*out,size_t cap,const char*f,va_list ap){
 size_t used=0;int total=0;if(cap)out[0]=0;
 while(*f){
  if(*f!='%'){putc_buf(out,cap,&used,&total,*f++);continue;}
  f++;if(*f=='%'){putc_buf(out,cap,&used,&total,'%');f++;continue;}
  int zero=0,width=0;if(*f=='0'){zero=1;f++;}while(*f>='0'&&*f<='9'){width=width*10+(*f-'0');f++;}
  int lng=0;if(*f=='l'){lng=1;f++;if(*f=='l'){lng=2;f++;}}else if(*f=='z'){lng=3;f++;}
  char spec=*f++;char tmp[64];int k=0;
  if(spec=='s'){const char*s=va_arg(ap,const char*);if(!s)s="(null)";while(*s)putc_buf(out,cap,&used,&total,*s++);continue;}
  if(spec=='c'){putc_buf(out,cap,&used,&total,(char)va_arg(ap,int));continue;}
  int neg=0;unsigned long long v=0;
  if(spec=='d'){long long x;if(lng==2)x=va_arg(ap,long long);else if(lng==1)x=va_arg(ap,long);else x=va_arg(ap,int);if(x<0){neg=1;v=(unsigned long long)(-(x+1))+1;}else v=(unsigned long long)x;}
  else if(spec=='u'){if(lng==3)v=va_arg(ap,size_t);else if(lng==2)v=va_arg(ap,unsigned long long);else if(lng==1)v=va_arg(ap,unsigned long);else v=va_arg(ap,unsigned);}
  else if(spec=='x'){if(lng==2)v=va_arg(ap,unsigned long long);else if(lng==1)v=va_arg(ap,unsigned long);else v=va_arg(ap,unsigned);}
  else {putc_buf(out,cap,&used,&total,'%');putc_buf(out,cap,&used,&total,spec);continue;}
  if(spec=='x'){do{tmp[k++]="0123456789abcdef"[v&15];v>>=4;}while(v);}else{do{tmp[k++]=(char)('0'+v%10);v/=10;}while(v);}
  if(neg)putc_buf(out,cap,&used,&total,'-');
  for(int j=k;j<width;j++)putc_buf(out,cap,&used,&total,zero?'0':' ');
  while(k)putc_buf(out,cap,&used,&total,tmp[--k]);
 }
 if(cap)out[used<cap?used:cap-1]=0;return total;
}
int printf(const char*f,...){char b[8192];va_list ap;va_start(ap,f);int total=emit_fmt(b,sizeof b,f,ap);va_end(ap);size_t n=(size_t)total<sizeof b?(size_t)total:sizeof b-1;return write_all(1,b,n)==0?total:-1;}
int fprintf(FILE*s,const char*f,...){char b[8192];va_list ap;va_start(ap,f);int total=emit_fmt(b,sizeof b,f,ap);va_end(ap);size_t n=(size_t)total<sizeof b?(size_t)total:sizeof b-1;return write_all(s==stderr?2:1,b,n)==0?total:-1;}
int snprintf(char*out,size_t cap,const char*f,...){va_list ap;va_start(ap,f);int n=emit_fmt(out,cap,f,ap);va_end(ap);return n;}
int putchar(int c){unsigned char x=(unsigned char)c;return write_all(1,(char*)&x,1)==0?c:-1;}
int __uflow(FILE*f){(void)f;return -1;}
int __overflow(FILE*f,int c){(void)f;(void)c;return -1;}
