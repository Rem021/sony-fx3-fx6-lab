from pathlib import Path
import json,subprocess,os,hashlib,sys,struct
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-ui-gate-v10.c').read_text().replace('0x3150414e53504e46UL','0x3250414e53504e46UL').replace('if(id>=52){','if(id>=60){');needle=' U id=c->id,tid=syscall(178),token=0;int important=1;';add=r'''
 if(id==52){token=r[0];dprintf(2,"FX3_UUD_FACE_ENTER tid=%lu sequence=%#lx desired144=%u no_frames_generated=1\n",tid,r[0],*(W *)(app_base+0x8226db8));}
 if(id==53){dprintf(2,"FX3_UUD_FACE_RETURN tid=%lu original_ret=0x2d11e8c no_frames_generated=1\n",tid);if(ram){unsigned int (*snapshot)(void *,unsigned int)=dlsym(0,"fx3_pin_snapshot");if(snapshot){unsigned n=snapshot((unsigned char *)ram+0xb040,0x2fc0);if(n){ram[0xb000/8+1]=n;ram[0xb000/8+2]=tid;ram[0xb000/8+3]=2;ram[0xb000/8+4]=28;ram[0xb000/8+5]=14;__asm__ volatile("dmb sy":::"memory");ram[0xb000/8]=0x3250414e53504e46UL;dprintf(2,"FX3_PIN_GRAPH2_QMP_SNAPSHOT bytes=%u at_face_return=1 endpoints=28 edges=14\n",n);}}}}
 if(id==54){token=(W)r[0];dprintf(2,"FX3_UUD_PARAM144_STORE tid=%lu value=%u destination=%#lx original_point=0x27bec60 caller=%#lx passive=1\n",tid,(W)r[0],r[25],r[30]-app_base);}
 if(id==55){token=(W)r[1];dprintf(2,"FX3_UUD_BACKUP_COMPARE tid=%lu id1841=%u id1842=%u original_cmp=unsigned caller=%#lx passive=1\n",tid,(W)r[1],(W)r[0],r[30]-app_base);}
 if(id==56){token=(W)r[0];dprintf(2,"FX3_UUD_BACKUP_WRITE_CALL tid=%lu id=0x02cf1841 value=%u original_callee=0x2ebfdfc passive=1\n",tid,(W)r[0]);}
 if(id==57){token=(W)r[0];dprintf(2,"FX3_UUD_OPTION_SNAPSHOT tid=%lu value=%u destination=%#lx original_store=1\n",tid,(W)r[0],r[19]+0x6e0);}
 if(id==58){token=r[0];const unsigned char *q=(void *)r[0];char raw[49];const char *h="0123456789abcdef";for(int i=0;i<24;i++){raw[i*2]=h[q[i]>>4];raw[i*2+1]=h[q[i]&15];if(ram)((volatile unsigned char *)ram)[0xc800+i]=q[i];}raw[48]=0;dprintf(2,"FX3_UUD_CHANGE_MODE_INPUT tid=%lu bytes=24 raw=%s original_call=1\n",tid,raw);}
 if(id==59){token=r[0];dprintf(2,"FX3_UUD_BACKUP_WRITE_RETURN tid=%lu original_call=0x28272d4 after_call=0x28272d8 result=%#lx passive=1\n",tid,r[0]);}
''';assert needle in s;s=s.replace(needle,needle+add);s=s.replace('offsets[52]','offsets[60]').replace('words[52]','words[60]').replace('regs[52]','regs[60]').replace('i<52;i++)if','i<60;i++)if').replace('i<52;i++){rc=install','i<60;i++){rc=install').replace('BOUND count=52','BOUND count=60')
sys.path.insert(0,str(R.parents[3]/'work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/lib/python3.14/site-packages'));from elftools.elf.elffile import ELFFile
with (R.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so').open('rb') as f:
 elf=ELFFile(f);pts=[]
 for va in [0x2d11dd4,0x2d11e8c,0x27bec60,0x28272b8,0x28272d4,0x2c245f4,0x2d11e4c,0x28272d8]:
  seg=next(z for z in elf.iter_segments() if z['p_type']=='PT_LOAD' and z['p_vaddr']<=va<z['p_vaddr']+z['p_filesz']);f.seek(seg['p_offset']+va-seg['p_vaddr']);pts.append((va,struct.unpack('<I',f.read(4))[0]))
for name,values in [('offsets',[z[0] for z in pts]),('words',[z[1] for z in pts]),('regs',[31]*8)]:
 a=s.index('const '+('W' if name=='words' else 'U')+' '+name+'[60]');b=s.index('};',a);s=s[:b]+','+','.join(hex(z) for z in values)+s[b:]
(H/'fx3-ui-gate-v11.c').write_text(s);e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));a=[x.replace('fx3-ui-gate-v10','fx3-ui-gate-v11') for x in json.loads((H/'fx3-ui-gate-v10-build.json').read_text())['args']];p=subprocess.run(a,env=e,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/'fx3-ui-gate-v11-build.json').write_text(json.dumps({'args':a,'exit':0,'source_sha256':hashlib.sha256((H/'fx3-ui-gate-v11.c').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-ui-gate-v11.so').read_bytes()).hexdigest(),'original_new_points':pts,'snapshot_version':2},indent=2)+'\n');print('gatev11 built 60 points',pts)
