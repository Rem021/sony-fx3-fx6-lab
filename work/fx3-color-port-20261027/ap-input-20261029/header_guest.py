#!/usr/bin/env python3
"""Original current AP FDAT header construction/set/check in synthetic RAM."""
from pathlib import Path
import hashlib,json,struct,sys,zlib
from current_static import View,sources,HERE

PREVIOUS=HERE.parent/'package-20261028'
sys.path.insert(0,str(PREVIOUS))
from original_block_checker_guest import Guest,DATA,STACK,STOP,R


class HeaderGuest(Guest):
    def __init__(self,view):
        super().__init__(view.raw);self.view=view
        # Resolve defined in-image dynamic pointers for original constructors.
        for r in view.elf.get_section_by_name('.rela.dyn').iter_relocations():
            typ=r['r_info_type'];s=view.symbols[r['r_info_sym']]
            if typ==1027:value=r['r_addend']
            elif typ in [257,1025] and s['st_shndx']!='SHN_UNDEF':value=s['st_value']+r['r_addend']
            else:continue
            self.u.mem_write(r['r_offset'],struct.pack('<Q',value))

    def code(self,u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        self.instructions+=1;assert self.instructions<180000
        if pc in self.plt:
            name=self.plt[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(3)]
            if name=='_Znam':assert x[0]==512;self.ret(DATA+0x1000)
            elif name in ['pthread_mutex_init','pthread_mutex_lock','pthread_mutex_unlock']:self.ret(0)
            elif name=='memset':
                assert DATA<=x[0] and x[0]+x[2]<=DATA+0x4000
                u.mem_write(x[0],bytes([x[1]&255])*x[2]);self.ret(x[0])
            elif name=='memcpy':
                assert DATA<=x[0] and x[0]+x[2]<=DATA+0x4000
                u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0])
            elif name=='memcmp':
                a=bytes(u.mem_read(x[0],x[2]));b=bytes(u.mem_read(x[1],x[2]));self.ret((0 if a==b else -1 if a<b else 1)&0xffffffffffffffff)
            else:raise AssertionError(('unmodeled import',name,hex(pc)))
            return
        assert any(a<=pc<b for a,b in [(0x8854,0x885c),(0x8930,0x8954),(0x8954,0x89b0),(0x89b0,0x8a6c),(0x8a74,0x8b24)]),hex(pc)

    def run(self,entry,args):
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_LR,STOP)
        for i,value in enumerate(args):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),value)
        before=self.instructions;u.emu_start(entry,STOP+4,count=80000)
        assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        return u.reg_read(R.UC_ARM64_REG_X0),self.instructions-before


def main():
    source=next(s for s in sources() if Path(s['path']).name=='libupdatercorecommon.so');view=View(source['path'],source['sha256'])
    compatibility=json.loads((HERE/'legacy-format-compatibility-results.json').read_text())
    plain=HERE.parents[2]/'work/sony-firmware-20261024/fx3-7.02-decrypted.fdat'
    # A full hash was verified by check_legacy_compatibility; this read uses the
    # same source and records the actual header hash separately.
    with plain.open('rb') as f:header=f.read(512)
    assert header[:8]==b'UDTRFIRM' and struct.unpack_from('<I',header,8)[0]==zlib.crc32(header[12:])
    damaged=bytearray(header);damaged[0x100]^=1
    repaired=bytearray(damaged);struct.pack_into('<I',repaired,8,zlib.crc32(repaired[12:]))
    badmagic=bytearray(header);badmagic[0]^=1
    fixtures=[('original',header,True),('changed_crc_region',bytes(damaged),False),('changed_region_recomputed_crc',bytes(repaired),True),('changed_magic',bytes(badmagic),False)]
    rows=[]
    for mode in [0,1]:
        for label,data,expected in fixtures:
            g=HeaderGuest(view);g.u.mem_write(DATA+0x800,data)
            _,ctor=g.run(0x8954,[DATA,mode]);_,setter=g.run(0x89b0,[DATA,DATA+0x800,512]);ret,checker=g.run(0x8a74,[DATA])
            assert bool(ret)==expected,(mode,label,ret)
            rows.append(dict(fixture=label,constructor_bool=mode,header_sha256=hashlib.sha256(data).hexdigest(),accepted=bool(ret),instructions=dict(constructor=ctor,set_header=setter,check=checker)))
    (HERE/'header-guest-results.json').write_text(json.dumps(dict(source_sha256=source['sha256'],original_plain_source_sha256=compatibility['original_plain_fdat_sha256'],original_header_sha256=hashlib.sha256(header).hexdigest(),cases=rows,
        scope='Original constructor, SetHeader, Check and small local helpers execute in synthetic Unicorn memory. Host shims: allocation, mutex, memset/memcpy/memcmp only. Header CRC gate accepting a modified CRC region is not full firmware admission, signature bypass, body loading, native execution or a flash test.'),indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'original_header_pass':True,'bad_crc_rejected':True,'recomputed_crc_passes_header_only':True,'camera_actions':0}))

if __name__=='__main__':main()
