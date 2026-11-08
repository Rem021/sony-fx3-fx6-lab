from elftools.elf.elffile import ELFFile
import capstone, struct, json

P="/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
f=open(P,'rb'); e=ELFFile(f); f.seek(0); d=f.read()
secs={s.name:s for s in e.iter_sections()}
t=secs['.text']; TB,TO,TS=t['sh_addr'],t['sh_offset'],t['sh_size']
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM); md.detail=True

SITES=[0xc187d8,0xc18854,0xc264d8,0xc55990,0xc5599c,0xf64648,0xf646ac,0xf669a0,0xf66a04,
       0xf6c13c,0xf6c1a0,0xf7731c,0xf77730,0xfb9a98,0xfb9e6c,0xfb9fa4,0xfba018,0xfbe448,
       0xfd0870,0xfdac48,0xfdc374,0xfe0510,0xfe4884,0xfe7e74,0xfec610,0xfec920,0xfeca18,
       0xfecbcc,0xfeccbc,0xfef8f4,0xff1a28,0xff3858,0xff57c8,0xff7904,0xffb830]

def func_start(addr, back=0x400):
    for a in range(addr, addr-back, -4):
        w=struct.unpack_from('<I',d,TO+a-TB)[0]
        if (w&0xFFC07FFF)==0xA9807BFD:   # stp x29,x30,[sp,#-N]!
            return a
    return None

out={}
for s in SITES:
    st=func_start(s)
    # disassemble from func start to site+8
    start=st if st else s-0x80
    code=d[TO+start-TB:TO+s-TB+0x10]
    reg={}
    ctx=[]
    for ins in md.disasm(code,start):
        if ins.address>s+4: break
        ctx.append(ins)
    # walk backwards from the call for w0 assignment
    slot=None; how=None; tbl=None
    for ins in reversed(ctx[:-1]):
        ops=ins.op_str.replace(' ','')
        if ins.address>s: continue
        if ins.mnemonic in ('mov','movz') and ops.startswith('w0,#'):
            v=int(ops.split('#')[1].split(',')[0],0)
            slot=v; how='imm'; break
        if ins.mnemonic=='ldr' and ops.startswith('w0,[x'):
            slot=None; how='mem:'+ins.op_str; break
        if ins.mnemonic=='ldrb' and ops.startswith('w0,[x'):
            slot=None; how='byte:'+ins.op_str; break
        if ins.mnemonic in ('mov','add','sub','ldr','ldrb','ldrh','csel','mul','madd','smull') and 'w0' in ops.split(',')[0]:
            how='computed:'+ins.mnemonic+' '+ins.op_str; break
    out[s]={'func':hex(st) if st else None,'slot':slot,'how':how}

print("site        func        slot      how")
for s in SITES:
    o=out[s]
    print("0x%06x  %-10s %-9s %s"%(s,o['func'],o['slot'],o['how']))
json.dump({str(k):v for k,v in out.items()},open('/private/tmp/fx6_lookup_sites.json','w'),indent=1)
