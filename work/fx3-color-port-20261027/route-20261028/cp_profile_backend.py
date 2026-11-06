#!/usr/bin/env python3
"""Execute original Thumb constructor + ARM memcpy, compare both processor profiles."""
from hashlib import sha256
import json
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
from cp_look_route import image, BASE, HERE


def main():
    b=image();u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
    u.mem_map(BASE,(len(b)+4095)&~4095);u.mem_write(BASE,b)
    u.mem_map(0x1ff0000,0x50000)
    stack,stop=0x50000000,0x60000000
    u.mem_map(stack,0x10000);u.mem_map(stop,0x1000)
    u.reg_write(R.UC_ARM_REG_SP,stack+0xf000);u.reg_write(R.UC_ARM_REG_LR,stop|1)
    for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
    counter=[0];copies=[]
    def code(u,pc,size,unused):
        if pc==stop:u.emu_stop();return
        off=pc-BASE
        assert 0x911650<=off<0x9169b8 or 0x450400<=off<0x450700,hex(pc)
        counter[0]+=1
        if off==0x450400:
            dst,src,n=[u.reg_read(r) for r in [R.UC_ARM_REG_R0,R.UC_ARM_REG_R1,R.UC_ARM_REG_R2]]
            assert n==140 and 0x1ff0000<=dst and dst+n<=0x2040000
            copies.append(dict(dst=hex(dst),src=hex(src),bytes=n))
    def write(u,access,address,size,value,unused):
        assert (0x1ff0000<=address and address+size<=0x2040000
                or stack<=address and address+size<=stack+0x10000),hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start((BASE+0x911650)|1,stop+4,count=500000)
    assert u.reg_read(R.UC_ARM_REG_PC)==stop and u.reg_read(R.UC_ARM_REG_SP)==stack+0xf000
    assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
    for c in copies:
        assert bytes(u.mem_read(int(c['dst'],16),140))==b[int(c['src'],16)-BASE:int(c['src'],16)-BASE+140]
    parent=HERE.parent
    av_path=HERE.parents[2]/'work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin'
    av=av_path.read_bytes();assert sha256(av).hexdigest()=='0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'
    initialized=(parent/'initialized-profile-region.bin').read_bytes()
    receipt=json.loads((parent/'initializer-guest-results.json').read_text())
    assert sha256(initialized).hexdigest()==receipt['initialized_region_sha256']
    profile=bytes(u.mem_read(0x2015794,70*140));(HERE/'CP-look22-initialized.bin').write_bytes(profile)
    matches=[]
    for i in range(70):
        cp_pointer,cp_reg,cp_words=struct.unpack_from('<III',profile,i*140)
        av_row=initialized[0xb05638-0xae0000+i*152:0xb05638-0xae0000+(i+1)*152]
        av_pointer,av_reg,av_words=struct.unpack_from('<QQI',av_row)
        cp_name=profile[i*140+12:(i+1)*140].split(b'\0',1)[0].decode()
        av_name=av_row[20:148].split(b'\0',1)[0].decode()
        assert cp_name==av_name and (cp_reg,cp_words)==(av_reg,av_words),(i,cp_name,av_name)
        backed=0<=cp_pointer-BASE and cp_pointer-BASE+cp_words*4<=len(b)
        cp_data=b[cp_pointer-BASE:cp_pointer-BASE+cp_words*4] if backed else None
        av_data=av[av_pointer-0xffffffc001000000:av_pointer-0xffffffc001000000+av_words*4]
        matches.append(dict(index=i,name=cp_name,register_offset=hex(cp_reg),words=cp_words,
                            sha256=sha256(cp_data).hexdigest() if backed else None,CP_data_pointer=hex(cp_pointer),
                            CP_data_file=hex(cp_pointer-BASE) if backed else None,
                            payload_equal=cp_data==av_data if backed else None,
                            differences=[{'word':j,'CP':hex(c),'AV':hex(a)} for j,(c,a) in enumerate(zip(struct.unpack('<'+'I'*cp_words,cp_data),struct.unpack('<'+'I'*av_words,av_data))) if c!=a][:16] if backed else []))
    assert sum(x['payload_equal'] is True for x in matches)==67
    assert {x['CP_data_pointer'] for x in matches if x['payload_equal'] is None}=={'0x13e624c','0x13e6250','0x13e6254'}
    result=dict(status='PASS_ORIGINAL_CP_CONSTRUCTOR_AND_PROFILE_COMPARISON',
                original_instructions=counter[0],constructor_file_span=['0x911650','0x9169b8'],
                constructor_sha256=sha256(b[0x911650:0x9169b8]).hexdigest(),
                memcpy_VA='0x558400',memcpy_original_ARM_executed=True,
                copies=copies,profile22_matches=matches,
                initialized_profile_sha256=sha256(profile).hexdigest(),
                scope='Original CP constructor in CPU guest and byte comparisons, not actual DSP load or MAIN/monitor selection.')
    (HERE/'cp-profile-backend-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'instructions',counter[0],'copies',len(copies),'compared entries',len(matches),
          'equal payloads',sum(x['payload_equal'] is True for x in matches))
    print(json.dumps([x for x in matches if not x['payload_equal']],indent=2))


if __name__=='__main__':main()
