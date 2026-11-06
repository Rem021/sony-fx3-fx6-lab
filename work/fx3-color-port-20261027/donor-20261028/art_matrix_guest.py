#!/usr/bin/env python3
"""Bounded original ARM64 matrix quantizer and register-label serializers.

No dylib is loaded. Unicorn RAM is synthetic; there is no host/device MMIO.
All vendor instruction entry points are explicitly bounded. Host shims cover
allocation, deallocation, memcpy, ldexp, and short libc++ string assignment.
"""
from pathlib import Path
import csv,hashlib,json,math,random,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC,UC_ARM64_REG_D0,UC_ARM64_REG_CPACR_EL1
from macho_static import MachO

HERE=Path(__file__).resolve().parent
REGS=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4]
STOP=0x20000000
HEAP=0x30000000
STACK=0x40000000


class Guest:
    def __init__(self,m,entries):
        self.m=m;self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.heap=HEAP;self.calls={};self.assignments=[];self.steps=0
        self.ranges=[(a,a+len(m.function(a))) for a in entries]
        for seg in m.segments:
            if seg['name']=='__LINKEDIT':continue
            n=(seg['vm_bytes']+4095)&-4096
            self.uc.mem_map(seg['va'],n,UC_PROT_READ|UC_PROT_WRITE|UC_PROT_EXEC)
            self.uc.mem_write(seg['va'],m.read(seg['va'],seg['file_bytes']))
            self.uc.mem_protect(seg['va'],n,UC_PROT_READ|UC_PROT_EXEC)
        self.uc.mem_map(STOP,4096,UC_PROT_READ|UC_PROT_EXEC)
        self.uc.mem_map(HEAP,0x200000,UC_PROT_READ|UC_PROT_WRITE)
        self.uc.mem_map(STACK,0x10000,UC_PROT_READ|UC_PROT_WRITE)
        self.uc.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20)
        self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xff00)
        self.uc.hook_add(UC_HOOK_CODE,self.hook)
        expected={0x6de49c:'__Znwm',0x6de484:'__ZdlPv',0x6de580:'_ldexp',0x6de5b0:'_memcpy'}
        for a,n in expected.items():assert m.stubs[a]==n,(hex(a),m.stubs[a],n)

    def alloc(self,n):
        p=self.heap;self.heap=(p+max(n,1)+15)&-16;assert self.heap<HEAP+0x200000
        return p

    def q(self,p,*v):self.uc.mem_write(p,struct.pack('<'+'Q'*len(v),*v))
    def uq(self,p):return struct.unpack('<Q',self.uc.mem_read(p,8))[0]

    def vector(self,raw,stride):
        assert len(raw)%stride==0
        p=self.alloc(24);data=self.alloc(len(raw));self.uc.mem_write(data,raw)
        self.q(p,data,data+len(raw),data+len(raw));return p

    def matrix(self,rows):
        refs=[]
        for r in rows:
            vec=self.vector(struct.pack('<'+'d'*len(r),*r),8)
            refs.append(bytes(self.uc.mem_read(vec,24)))
        return self.vector(b''.join(refs),24)

    def readmatrix(self,p):
        b=self.uq(p);end=self.uq(p+8);rows=[]
        for row in range(b,end,24):
            rb=self.uq(row);re=self.uq(row+8)
            rows.append(list(struct.unpack('<'+'d'*((re-rb)//8),self.uc.mem_read(rb,re-rb))))
        return rows

    def hook(self,uc,pc,size,user):
        self.steps+=1;assert self.steps<50000,'instruction bound'
        if pc==STOP:uc.emu_stop();return
        if pc in self.m.stubs:
            name=self.m.stubs[pc];self.calls[name]=self.calls.get(name,0)+1
            x=[uc.reg_read(r) for r in REGS]
            if pc==0x6de49c:uc.reg_write(UC_ARM64_REG_X0,self.alloc(x[0]))
            elif pc==0x6de484:pass
            elif pc==0x6de5b0:
                assert x[2]<=0x10000
                uc.mem_write(x[0],bytes(uc.mem_read(x[1],x[2])))
            elif pc==0x6de580:
                d=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0]
                exponent=x[0]&0xffffffff
                if exponent&0x80000000:exponent-=1<<32
                assert -40<=exponent<=40
                uc.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',math.ldexp(d,exponent)))[0])
            elif pc==0x6de208:
                raw=bytes(uc.mem_read(x[1],64));s=raw.split(b'\0',1)[0];assert len(s)<23
                uc.mem_write(x[0],s+b'\0'*(23-len(s))+bytes([len(s)]))
                self.assignments.append(dict(destination=hex(x[0]),source=hex(x[1]),text=s.decode('ascii')))
            elif pc==0x6de250:
                assert 'basic_string' in name
                raw=bytes(uc.mem_read(x[1],24));assert raw[23]<23
                text=raw[:raw[23]];assert x[2]<=len(text)
                s=text[x[2]:x[2]+x[3]];assert len(s)<23
                uc.mem_write(x[0],s+b'\0'*(23-len(s))+bytes([len(s)]))
            else:raise AssertionError(('unmodeled import',hex(pc),name))
            uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30));return
        assert any(a<=pc<b for a,b in self.ranges),('out of bounds code',hex(pc))

    def run(self,entry,args):
        self.steps=0
        for r,v in zip(REGS,args):self.uc.reg_write(r,v)
        self.uc.reg_write(UC_ARM64_REG_X30,STOP)
        self.uc.emu_start(entry,STOP+4,count=50000)
        assert self.uc.reg_read(UC_ARM64_REG_PC)==STOP


def fcvt(v):return min((1<<31)-1,max(-(1<<31),math.trunc(v)))
def rounded(v):return fcvt(v+(-0.5 if v<0 else 0.5))


def recovered(matrix,fraction_bits,limit_exponent,mode):
    """Finite-domain translation; deliberately retains source's > positive edge."""
    scale=2.0**fraction_bits;limit=2.0**limit_exponent;out=[]
    for i,row in enumerate(matrix):
        values=[]
        for v in row:
            s=v*scale
            if s>limit:s=limit-1
            elif s<=-limit:s=-limit
            values.append(s)
        total=sum(rounded(v) for v in values)
        gain=scale/total if mode==1 and total else 1.0
        ints=[fcvt(gain*rounded(v)) for v in values]
        if mode and sum(ints)!=scale:ints[i]=int(scale)-sum(ints[j] for j in range(3) if j!=i)
        out.append(ints)
    return out


def matrix_cases():
    ident=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
    rows=list(csv.DictReader((HERE.parent/'tables/venice_matrix_signed_q16.csv').open()))
    cp=[[float(r['coefficient']) for r in rows[i*3:i*3+3]] for i in range(3)]
    fixtures=[('identity',ident),('fx3-existing-venice-q16',cp),
              ('zero-rows',[[0.,0.,0.]]*3),
              ('half-rounding',[[0.5/65536,-0.5/65536,1.5/65536],[1.5/65536,-1.5/65536,2.5/65536],[-2.5/65536,2.5/65536,1.0]]),
              ('limit-exact-and-adjacent',[[8.,8.+1/65536,8.-1/65536],[-8.,-8.-1/65536,-8.+1/65536],[9.,-9.,1.]])]
    rng=random.Random(0x56454e494345)
    for i in range(64):
        a=[[rng.uniform(-0.9,0.9) for _ in range(3)] for _ in range(3)]
        for j in range(3):a[j][j]=1.-sum(a[j][k] for k in range(3) if k!=j)
        fixtures.append((f'finite-matrix-{i:02}',a))
    return fixtures


def main():
    source=json.loads((HERE/'art-generator-source.json').read_text());m=MachO(source['path'])
    assert hashlib.sha256(m.file).hexdigest()==source['sha256']
    results=[]
    for label,matrix in matrix_cases():
        for mode in [0,1]:
            guest=Guest(m,[0x46994,0x53d4]);out=guest.matrix([[0.]*3 for _ in range(3)]);inp=guest.matrix(matrix)
            guest.run(0x46994,[out,inp,16,19,mode])
            actual=guest.readmatrix(out);expected=recovered(matrix,16,19,mode)
            assert actual==expected,(label,mode,actual,expected)
            results.append(dict(case=label,mode=mode,input=matrix,output=actual,row_sums=[sum(r) for r in actual],instructions=guest.steps,imports=guest.calls))
    registers=[]
    for a,label,shape in [(0x5c3b24,'Lmx0',(9,4)),(0x5c3e8c,'Lmx1',(9,4)),(0x5c41f4,'Lmx2',(9,4)),(0x5c455c,'Lmx3',(9,4)),(0x5c48c4,'Lmx4',(9,4)),(0x5c4c2c,'MTX',(9,2)),(0x5c4dd0,'DEMTX',None), (0x5c25a8,'Lut1D0-RAM','ram'),(0x5c2628,'Lut1D1-RAM','ram'),(0x5c26a8,'Lut1D2-RAM','ram')]:
        guest=Guest(m,[a])
        if shape=='ram':p=guest.vector(bytes(24*3),24);q=guest.vector(bytes(24*2),24)
        elif shape:
            rows=[]
            for _ in range(shape[0]):
                row=guest.vector(bytes(24*shape[1]),24);rows.append(bytes(guest.uc.mem_read(row,24)))
            p=guest.vector(b''.join(rows),24);q=guest.alloc(24)
        else:p=guest.alloc(48);q=0
        guest.run(a,[p,q]);assert len(guest.assignments)>0
        registers.append(dict(label=label,entry=hex(a),shape=shape,instructions=guest.steps,assignments=guest.assignments))
    result=dict(source_sha256=source['sha256'],matrix_function='0x46994',vector_constructor='0x53d4',
                parameters=dict(fraction_bits=16,limit_exponent=19),matrix_cases=results,register_cases=registers,
                scope='Original quantizer, original vector construction, and register-label caller instructions in bounded synthetic Unicorn RAM. Host shims: new/delete/memcpy/ldexp and short string assignment. Not an ISP execution, native library load, camera register write, MAIN pixel test, or flash proof.')
    (HERE/'art-matrix-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'matrix_cases':len(results),'register_cases':len(registers),'all_exact':True,'fx3_existing_matrix_same':all(r['output']==[[75487,-7714,-2237],[-2656,79077,-10885],[-807,475,65868]] for r in results if r['case']=='fx3-existing-venice-q16')}))

if __name__=='__main__':main()
