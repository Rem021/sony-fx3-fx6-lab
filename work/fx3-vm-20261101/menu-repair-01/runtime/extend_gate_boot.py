from pathlib import Path
import json,struct
R=Path(__file__).resolve().parent;H=R/'helpers';p=H/'fx3-ui-gate-v1.c';s=p.read_text().replace('count[16]','count[48]').replace('if(id==15)','if(id==47)').replace(',15,31)',',47,31)').replace('ram[1]=1','ram[1]=2')
insert=r'''
static U known_sequence,boot_reserve;static __thread U create_sequence,create_function,completion_sequence,completion_handle;
static void boot_event(struct ctx *c,U *r,U n){
 U id=c->id,tid=syscall(178),token=0;int important=1;
 if(id==12){create_sequence=r[0];create_function=r[2];U fn=r[2]-app_base;important=fn==0x2b61efc||fn==0x2b5fae4||fn==0x2b61a90||fn==0x2b60208;if(important)save(&known_sequence,r[0]);}
 if(id==21){completion_sequence=r[0];completion_handle=(W)r[1];important=r[0]==load(&known_sequence);}
 if(id==22)important=r[0]==load(&known_sequence);if(id==30)important=completion_sequence==load(&known_sequence);
 if(id==23||id==24)token=*(W *)(r[29]+0x7c);if(id==20&&r[1])token=*(U *)r[1];
 if(important&&ram){U index=__atomic_fetch_add(&boot_reserve,1,__ATOMIC_RELAXED);if(index<64){U record[24]={id,n,tid,c->pc-app_base,r[0],r[1],r[2],r[3],r[4],r[19],r[20],r[21],r[22],r[25],r[26],r[27],r[28],r[29],token,create_sequence,create_function,completion_sequence,completion_handle,0x544f4f4245544147UL};volatile U *out=ram+0x4000/8+index*24;for(int i=0;i<23;i++)out[i]=record[i];__asm__ volatile("dmb sy":::"memory");out[23]=record[23];ram[5]=index+1;}else ram[6]=index-63;}
 if(important&&(n<=50||n%1000==0||id==12||id==21||id==30))dprintf(2,"FX3_BOOT_GATE_SAMPLE id=%lu n=%lu tid=%lu pc=%#lx x0=%#lx x1=%#lx x2=%#lx x3=%#lx x4=%#lx x19=%#lx remaining=%lu expected=%#lx/%#lx/%#lx/%#lx token_or_req=%#lx create_sequence=%#lx create_function=%#lx completion_sequence=%#lx completion_handle=%#lx\n",id,n,tid,c->pc-app_base,r[0],r[1],r[2],r[3],r[4],r[19],r[22],r[25],r[26],r[27],r[28],token,create_sequence,create_function,completion_sequence,completion_handle);
 mirror();
}
'''
pos=s.index('__attribute__((visibility("hidden"))) int fx3_gate_test_compare');s=s[:pos]+insert+s[pos:]
s=s.replace('if(id>=12){*__errno_location()=saved;return;}U n=', 'if(id>=40){*__errno_location()=saved;return;}if(id>=12){U n=add(&st.count[id],1);boot_event(c,r,n);*__errno_location()=saved;return;}U n=')
s=s.replace('d>-(1L<<27)+4096&&d<(1L<<27)-4096','d>-(1L<<26)+4096&&d<(1L<<26)-4096')
s=s.replace('unsigned char *p=pool->p+pool->used;pool->used+=128;', 'unsigned char *p=pool->p+pool->used;long delta=(long)((U)p-pc);if(delta<=-(1L<<27)||delta>=(1L<<27))return -8;pool->used+=128;')
ui=json.loads((R/'ap77-instruction-review.json').read_text());boot=json.loads((R/'ap77-boot-instruction-review.json').read_text());allins={int(i['va'],16):i for blocks in [ui,boot] for block in blocks.values() for i in block}
newpc=[0x2b63224,0x2b63900,0x2b66de4,0x2b66e04,0x2b67674,0x2b67678,0x2b60208,0x2dd0cb4,0x2dec7e4,0x2b634dc,0x2b6353c,0x2b63628,0x2b63678,0x2b63624,0x2b61efc,0x2b62438,0x2b61a90,0x2b5fae4,0x2b63538]
# Derive every added instruction from the reviewed immutable ELF bytes, reject unsupported classes.
for pc in newpc:assert allins[pc]['instruction'].split()[0] in ['stp','add','str','bl','sub','mov','cmp','cbnz','ret']
import re
for name,extra in [('offsets',','.join(hex(x) for x in newpc)),('words',','.join(hex(struct.unpack('<I',bytes.fromhex(allins[x]['bytes']))[0]) for x in newpc)),('regs',','.join(['31']*len(newpc)))]:
 pat=rf'(const (?:U|W) {name})\[12\]=(\{{)([^}}]+)(\}});';s,n=re.subn(pat,lambda m:m[1]+'[31]='+m[2]+m[3]+','+extra+m[4]+';',s);assert n==1,(name,n)
s=s.replace('for(int i=0;i<12;i++)','for(int i=0;i<31;i++)').replace('BOUND count=12','BOUND count=31')
p.write_text(s)
(R/'ap77-installed-points.json').write_text(json.dumps({'UI_points':list(range(12)),'boot_points':[dict(id=12+i,**allins[pc]) for i,pc in enumerate(newpc)],'selftest_id':47,'counter_count':48,'record_capacity':64,'physical':'0x41dc00000','bytes':65536},indent=2)+'\n')
