int printf(const char*,...); int snprintf(char*,unsigned long,const char*,...); int putchar(int);
int main(void){
 printf("starttime=%llu digest=%016llx\n",1234ULL,0x123456789abcdef0ULL);
 printf("pid=%ld starttime=%llu seq=%ld cap=%zu data_reads=%d eof_probe=%d attempts=%d/%d\n",239L,777ULL,2L,262144UL,1,1,1,1);
 printf("bytes=%zu lines=%zu term=%d complete=%d atomic=%d\n",10563UL,105,1,1,0);
 char b[32];snprintf(b,sizeof b,"/proc/%ld",239L);printf("path=%s\n",b);
 putchar('X');putchar('\n');return 0;
}
