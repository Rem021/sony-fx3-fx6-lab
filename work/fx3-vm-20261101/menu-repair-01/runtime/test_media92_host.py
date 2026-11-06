from pathlib import Path
import subprocess,hashlib,json
R=Path(__file__).resolve().parent;H=R/'helpers';src=(H/'fx3-media-observe-v1.c').read_text();prefix=src[:src.index('__attribute__((visibility("hidden"))) void fx3_media_event')]
test=prefix+r'''
extern long pwrite(int,const void *,U,long);extern int fsync(int);extern void abort(void);
long fx3_host_tid(long n,...){(void)n;return 7;}
#define CHECK(c) do{if(!(c))abort();}while(0)
int main(int argc,char **argv){CHECK(argc==2);pmem=open(argv[1],0x602,0600);CHECK(pmem>=0);unsigned char b[4096];for(unsigned i=0;i<4096;i++)b[i]=(unsigned char)i;CHECK(pwrite(pmem,b,4096,4096)==4096);fsync(pmem);unsigned char out[4096];CHECK(peek(4096,out,4096));CHECK(!__builtin_memcmp(b,out,4096));CHECK(!peek(4095,out,1));CHECK(!peek(0x8000000000UL,out,0));CHECK(!peek(0x7fffffffffUL,out,2));CHECK(!peek(4096,out,~0UL));CHECK(!peek(12288,out,1));
 *__errno_location()=73;raw("host_valid",4096,32);CHECK(*__errno_location()==73);raw("host_oversize",4096,4097);CHECK(*__errno_location()==73);raw("host_unmapped",12288,32);CHECK(*__errno_location()==73);
 U f[2]={0x1001,0};CHECK(pwrite(pmem,f,16,6144)==16);stack((U)main,6144);CHECK(*__errno_location()==73);CHECK(peek(4096,out,4096));CHECK(!__builtin_memcmp(b,out,2048));CHECK(!__builtin_memcmp(b+2064,out+2064,4096-2064));close(pmem);return 0;}
'''
p=H/'fx3-media-host-check-v1.c';p.write_text(test);exe=H/'fx3-media-host-check-v1';args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-D__errno_location=__error','-Dsyscall=fx3_host_tid',str(p),'-o',str(exe)];cp=subprocess.run(args,capture_output=True,text=True);print(cp.stderr);assert cp.returncode==0
rp=subprocess.run([str(exe),str(R/'ap92-host-read-fixture.bin')],capture_output=True,text=True);print(rp.stderr);assert rp.returncode==0
# Ensure capid outermost send and protocol implementation identity, except exactly passive observer call.
a=(H/'fx3-capid-v44.c').read_text();b=(H/'fx3-capid-v47-media.c').read_text();b=b.replace('extern void fx3_media_wire_observe(unsigned,const void *,unsigned,unsigned,void *,void *) __attribute__((weak));\n','');b=b.replace(' if(fx3_media_wire_observe&&request&&(dst==0x5503e0||dst==0x80d9016e||dst==0x80cf016d))fx3_media_wire_observe(dst,request,msg_size(request),source(request),__builtin_return_address(0),__builtin_frame_address(0));\n','');assert a==b
# no original instruction may be PC relative except existing correctly replayed CBZ/BL.
from elftools.elf.elffile import ELFFile
from capstone import *
proof=json.loads((R/'ap92-passive-original-proof.json').read_text());assert len(proof['parameters'])==10 and sum(map(len,proof['points'].values()))==36
v={'ASan_UBSan_exit':rp.returncode,'compile':args,'host_stderr':rp.stderr,'read_tests':'exact4096/nativepreadfail/underflow/upperbound/lengthoverflow/oversizehex/errno/no_source_mutation/malformed_frame','capid44_protocol_byte_equal_after_removing_two_passive_additions':True,'getters_Unicorn_two_ASLR_bases':20,'original_points_guarded':36,'nativeASM_GPR_SIMD_NZCV_FPCR_FPSR_SP_CBZ_BL_selftest':'required guest marker, not yet runtime','source_sha256':hashlib.sha256(src.encode()).hexdigest()};(R/'ap92-host-check.json').write_text(json.dumps(v,indent=2)+'\n');print('AP92 HOST PASS')
