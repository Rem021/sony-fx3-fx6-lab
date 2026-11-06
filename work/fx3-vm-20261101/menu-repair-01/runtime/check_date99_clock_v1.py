from pathlib import Path
import datetime as dt,struct,subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';fixtures=[]
def packdate(x,t):return struct.pack('<H5BBHHB3x',x.year,x.month,x.day,x.hour,x.minute,x.second,0,x.microsecond//1000,0,t)
epoch=dt.datetime(1970,1,1)
for year,month,day in [(1970,1,1),(1999,12,31),(2000,2,29),(2021,1,1),(2024,2,29),(2038,1,19),(2099,12,31),(2100,3,1),(2400,2,29),(9998,12,31)]:
 for td,dst in [(540,0),(-300,60),(0,0),(1440,-1440),(-1440,0)]:
  for t in [0,1]:
   x=dt.datetime(year,month,day,23,59,58,900000);off=td+dst;utc=x-dt.timedelta(minutes=off) if t==0 else x;out=utc+dt.timedelta(milliseconds=6123,minutes=off);delta=utc-epoch;ms=delta.days*86400000+delta.seconds*1000+delta.microseconds//1000;fixtures.append((packdate(x,t),struct.pack('<hhHH',td,dst,0,0),ms,packdate(out,0)))
s='static const struct {unsigned char d[16],tz[8];long utc;unsigned char expected[16];} fixture99[]={\n'
for a,b,c,d in fixtures:s+='{'+','.join(['{'+','.join(str(x) for x in a)+'}','{'+','.join(str(x) for x in b)+'}',str(c)+'L','{'+','.join(str(x) for x in d)+'}'])+'},\n'
s+='};\n';(H/'date99-clock-fixture-v1.h').write_text(s)
p=H/'check-date99-clock-v1.c';p.write_text(r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
typedef unsigned char B;typedef unsigned W;typedef unsigned long U;
static W rd16(const B*p){return p[0]|(W)p[1]<<8;}static void cp_copy(B*d,const B*s,U n){memcpy(d,s,n);}
#include "fx3-date99-clock-core-v1.h"
#include "date99-clock-fixture-v1.h"
int main(void){for(unsigned i=0;i<sizeof fixture99/sizeof *fixture99;i++){struct date99_clock c={0};B out[16];long utc;assert(!c99_build(&c,fixture99[i].d,fixture99[i].tz,1,8000000000UL,10000000000UL,7));assert(c.valid&&c.generation==7&&c.utc_ms==fixture99[i].utc&&c.basis_ns==9000000000UL);assert(!c99_read(&c,15123000000UL,out,&utc)&&utc==fixture99[i].utc+6123&&!memcmp(out,fixture99[i].expected,16));struct date99_clock old=c;B bad[16];memcpy(bad,fixture99[i].d,16);bad[2]=13;assert(c99_build(&c,bad,fixture99[i].tz,1,8,10,8)&&!memcmp(&c,&old,sizeof c));}
 B d[16]={0xe5,7,1,1},tz[8]={0},out[16];struct date99_clock c={0};d[12]=3;assert(!c99_build(&c,d,tz,4,1,10,1)&&!c.valid&&!c99_read(&c,11,out,0)&&!memcmp(out,d,16));assert(c99_build(&c,d,tz,1,1,10,2));d[12]=0;assert(c99_build(&c,d,tz,1,11,10,2));d[0]=0x34;d[1]=8;d[2]=2;d[3]=29;assert(c99_build(&c,d,tz,1,1,10,2));puts("DATE99_CLOCK_PASS 100independent_Python_datetime_vectors/UTC_TD_DST/type0_type1/leap_century/millisecond_monotonic_progress/half_RTT_basis/unknown_BY_BOOT/no_write_on_invalid");}
''');args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];subprocess.run(args,check=True);q=subprocess.run([str(p.with_suffix(''))],capture_output=True,text=True);p.with_suffix('.log').write_text(q.stdout+q.stderr);print(q.stdout+q.stderr);assert not q.returncode;(R/'date99-clock-oracle-v1.json').write_text(json.dumps({'independent_oracle':'Python datetime/timedelta, integer UTC milliseconds from1970; no C algorithm used','vectors':len(fixtures),'fixture_sha256':hashlib.sha256((H/'date99-clock-fixture-v1.h').read_bytes()).hexdigest(),'C_ASan_UBSan_exit':q.returncode},indent=2)+'\n')
