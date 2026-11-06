#!/usr/bin/env python3
"""Original AArch64 ET_REL UPM receiver/dispatch/factor7 over explicit RAM OSAL."""
import hashlib, io, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID
from unicorn import arm64_const as R

HERE = Path(__file__).resolve().parent
RAM, STACK = 0x50000000, 0x60000000
INPUT = RAM + 0x1000

class Peer:
    def __init__(self, state):
        record = json.loads((HERE/'service-inspection-results.json').read_text())['source']
        raw = (HERE/record['output']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        elf = ELFFile(io.BytesIO(raw)); self.source_sha256 = record['sha256']
        assert elf['e_type'] == 'ET_REL' and elf['e_machine'] == 'EM_AARCH64'
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.sections = {}
        preferred = {'.text': 0x10000000, '.rodata': 0x11000000, '.data': 0x12000000, '.bss': 0x13000000}
        for i, sec in enumerate(elf.iter_sections()):
            if not sec['sh_flags'] & 2 or not sec['sh_size']: continue
            base = preferred.get(sec.name, 0x14000000+i*0x100000)
            self.u.mem_map(base, (sec['sh_size']+4095)&-4096)
            if sec['sh_type'] != 'SHT_NOBITS': self.u.mem_write(base, sec.data())
            self.sections[i] = base
        symbols = list(elf.get_section_by_name('.symtab').iter_symbols())
        self.text = self.sections[2]; self.data = self.sections[23]; self.bss = self.sections[27]
        self.calls, self.relocations = {}, []
        undefined = {}
        def address(sym):
            idx = sym['st_shndx']
            if isinstance(idx, int):
                assert idx in self.sections
                return self.sections[idx] + sym['st_value']
            if idx == 'SHN_ABS': return sym['st_value']
            assert idx == 'SHN_UNDEF'
            if sym.name not in undefined: undefined[sym.name] = 0x20000000+len(undefined)*16
            return undefined[sym.name]
        for sec in elf.iter_sections():
            if sec['sh_type'] != 'SHT_RELA' or sec['sh_info'] not in self.sections: continue
            base = self.sections[sec['sh_info']]
            for rel in sec.iter_relocations():
                sym = symbols[rel['r_info_sym']]; pc = base+rel['r_offset']
                if rel['r_info_type'] == 257:
                    target = address(sym)+rel['r_addend']; self.u.mem_write(pc, struct.pack('<Q', target))
                    self.relocations.append(dict(address=hex(pc), type='ABS64', symbol=sym.name, target=hex(target)))
                elif sec['sh_info'] == 2 and rel['r_info_type'] in [282, 283]:
                    self.calls[pc] = dict(name=sym.name, target=address(sym)+rel['r_addend'], defined=isinstance(sym['st_shndx'], int), call=rel['r_info_type']==283)
        for lo in [RAM, STACK]: self.u.mem_map(lo, 0x10000)
        self.fixture = dict(type=1, jack=1, other_words=[0]*8)
        self.fixture.update(state)
        assert len(self.fixture['other_words']) == 8
        self.power = struct.pack('<10I', self.fixture['other_words'][0], self.fixture['type'], self.fixture['jack'], *self.fixture['other_words'][1:])
        assert len(self.power) == 40
        # Read-only fixture for framework cached power state, not hardware readback.
        self.u.mem_write(self.bss+0x950+4+0xc0, self.power)
        self.steps = 0; self.events = []; self.entries = {}; self.allocations = {}; self.next_alloc = 0
        self.started = False; self.waiting = False; self.pending = None; self.reply = None
        self.dump_mode=False; self.dump_rows=[]
        self.allowed = [(0x13de8,0x13ee8),(0x13cf8,0x13dd8),(0x13a68,0x13bc0),(0x1ba18,0x1ba40)]
        self.labels = {0x13de8:'receiver_thread',0x13cf8:'command3_handler',0x1ba18:'factor7_power_copy',0x13a68:'reply_wrapper'}
        self.u.reg_write(R.UC_ARM64_REG_SP, STACK+0xf000)
        self.u.hook_add(UC_HOOK_CODE,self.code)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_guard)
        self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)

    def write_guard(self,u,access,at,size,value,user):
        assert any(lo<=at and at+size<=lo+0x10000 for lo in [RAM,STACK]), ('UPM write outside RAM',hex(at),size)
    def invalid(self,u,access,at,size,value,user):
        raise AssertionError(('UPM unmapped access',hex(u.reg_read(R.UC_ARM64_REG_PC)),hex(at),size))
    def ret(self,value=0):
        self.u.reg_write(R.UC_ARM64_REG_X0,value&0xffffffffffffffff)
        self.u.reg_write(R.UC_ARM64_REG_PC,self.u.reg_read(R.UC_ARM64_REG_X30))

    def code(self,u,pc,size,user):
        self.steps += 1; assert self.steps < 10000
        if self.dump_mode and pc==0x70000000: u.emu_stop(); return
        off = pc-self.text
        assert any(lo<=off<hi for lo,hi in self.allowed), ('UPM code outside scope',hex(pc),hex(off))
        if off in self.labels:
            label=self.labels[off];self.entries[label]=self.entries.get(label,0)+1
        call=self.calls.get(pc)
        if not call: return
        if call['call']: u.reg_write(R.UC_ARM64_REG_X30,pc+4)
        if call['defined']:
            u.reg_write(R.UC_ARM64_REG_PC,call['target']);return
        name=call['name'];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
        if name=='printk' and self.dump_mode:
            def string(at):
                out=bytearray()
                for k in range(256):
                    byte=bytes(u.mem_read(at+k,1))
                    if byte==b'\0': return out.decode()
                    out.extend(byte)
                raise AssertionError('unterminated UPM string')
            fmt=string(x[0]); label=string(x[1])
            row=dict(format=fmt,label=label,value=x[2]&0xffffffff)
            if fmt=='%32s: %d(%s)\n': row['enum_label']=string(x[3])
            else: assert fmt in ['%32s: %d mA\n','%32s: %d mV\n']
            self.dump_rows.append(row);self.ret();return
        if name=='osal_valloc_msg_wait':
            assert x[0] in [0x928708f7,self.reply_target] and x[2] in [16,156] and x[3]==1
            self.next_alloc+=1;assert self.next_alloc<=4
            p=RAM+0x4000+self.next_alloc*0x200;u.mem_write(p-16,b'\0'*(x[2]+16));u.mem_write(x[1],struct.pack('<Q',p));self.allocations[p]=x[2]
            self.events.append(dict(adapter='RAM allocation',target=hex(x[0]),bytes=x[2]));self.ret();return
        if name=='osal_set_msg_src':
            assert x[0] in self.allocations and x[1]==0x80920021
            u.mem_write(x[0]-12,struct.pack('<I',x[1]));self.ret();return
        if name=='memcpy':
            assert x[2] in [16,152,156,208]
            assert any(lo<=x[0] and x[0]+x[2]<=lo+0x10000 for lo in [RAM,STACK])
            u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0]);return
        if name=='osal_snd_msg':
            assert x[1] in self.allocations
            payload=bytes(u.mem_read(x[1],self.allocations[x[1]]));source=struct.unpack('<I',u.mem_read(x[1]-12,4))[0]
            assert source==0x80920021
            if x[0]==0x928708f7:
                assert len(payload)==16;kind='RAM startup notification sink'
            else:
                assert x[0]==self.reply_target and len(payload)==156;self.reply=payload;kind='RAM power reply'
            self.events.append(dict(adapter=kind,target=hex(x[0]),source=hex(source),payload_hex=payload.hex()));self.ret();return
        if name=='osal_rcv_msg_tmo':
            assert x[0]==0x80920871 and x[2]==0xffffffff
            if self.pending is None: self.waiting=True;u.emu_stop();return
            payload,source=self.pending;self.pending=None
            u.mem_write(INPUT-12,struct.pack('<I',source));u.mem_write(INPUT,payload);u.mem_write(x[1],struct.pack('<Q',INPUT))
            self.events.append(dict(adapter='RAM kernel receive',source=hex(source),request_hex=payload.hex()));self.ret();return
        if name=='osal_get_msg_src':
            assert x[0]==INPUT;self.ret(struct.unpack('<I',u.mem_read(INPUT-12,4))[0]);return
        if name=='osal_free_msg':
            assert x[0]==0x80920871 and x[1]==INPUT;self.events.append(dict(adapter='RAM input free'));self.ret();return
        raise AssertionError(('unmodelled UPM import',name,hex(off)))

    def request(self,payload,source=0x011d0000):
        assert len(payload)==208 and struct.unpack_from('<I',payload)[0]==3
        assert not self.started and self.pending is None
        self.reply_target=struct.unpack_from('<I',payload,0xa4)[0];assert self.reply_target!=0
        self.pending=(payload,source);self.started=True
        self.u.emu_start(self.text+0x13de8,0,count=10000)
        assert self.waiting and self.reply is not None
        return self.reply,dict(instructions=self.steps,entries=self.entries,events=self.events,declared_cached_power_state=self.fixture)

    def dump(self):
        assert not self.started
        self.dump_mode=True;self.allowed.append((0x144f8,0x14728));self.u.mem_map(0x70000000,4096)
        self.u.mem_write(INPUT,self.power);self.u.reg_write(R.UC_ARM64_REG_X0,INPUT);self.u.reg_write(R.UC_ARM64_REG_X30,0x70000000)
        self.u.emu_start(self.text+0x144f8,0x70000004,count=10000)
        assert self.u.reg_read(R.UC_ARM64_REG_PC)==0x70000000 and self.u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        return self.dump_rows

def main():
    rows=[]
    for label,state,factor in [('ac_connected',{},7),('battery',dict(type=2,jack=2),7),('ac_unconnected',dict(type=1,jack=2),7),('invalid_factor',{},24)]:
        peer=Peer(state);payload=bytearray(208);struct.pack_into('<I',payload,0,3);struct.pack_into('<I',payload,8,factor);struct.pack_into('<I',payload,0xa4,0x0192002a)
        reply,meta=peer.request(bytes(payload));status=struct.unpack_from('<i',reply)[0]
        assert status==(-1018 if factor==24 else 0)
        if factor==7: assert reply[24:64]==peer.power and meta['entries']['factor7_power_copy']==1
        else: assert 'factor7_power_copy' not in meta['entries']
        rows.append(dict(case=label,status=status,reply_hex=reply.hex(),**meta))
    selected_relocations=[r for r in peer.relocations if int(r['address'],16) in [peer.text+0x13dd8,peer.text+0x13de0,peer.text+0x13ee8,peer.data+0x408] or 0x110009d0<=int(r['address'],16)<0x11000a08]
    result=dict(source_sha256=peer.source_sha256,applied_abs64_count=len(peer.relocations),selected_guest_relocations=selected_relocations,cases=rows,scope='Original kernel UPM receive loop, command table relocation, command3 handler, factor7 callback and reply wrapper execute in Unicorn. Original ABS64 module relocations are resolved into declared RAM; imported branch relocations are redirected only in the guest. Framework power cache and OSAL allocation/channel/source/notification sinks are explicit synthetic inputs. No kernel module loading, initialization, physical power reading, native IPC, USB, firmware or device writes.')
    (HERE/'upm-peer-results.json').write_text(json.dumps(result,indent=2)+'\n')
    labels=[]
    for state,expected in [({},('PS_TYPE_ACV','PS_AC_CONNECT_OK')),(dict(type=2,jack=2),('PS_TYPE_BATTERY','PS_AC_CONNECT_NG')),(dict(type=0xffffffff,jack=0xffffffff),('PS_TYPE_UNKNOWN','PS_AC_CONNECT_UNKNOWN'))]:
        peer=Peer(state);printed=peer.dump()
        assert printed[0]['label']=='type' and printed[1]['label']=='jack'
        assert (printed[0]['enum_label'],printed[1]['enum_label'])==expected
        labels.append(dict(declared_state=peer.fixture,original_printk_requests=printed,instructions=peer.steps))
    (HERE/'power-enum-results.json').write_text(json.dumps(dict(cases=labels,scope='Original named power-status diagnostic code and literal relocations execute in Unicorn; printk is a captured string request with no native log. State inputs are synthetic, not a hardware reading.'),indent=2)+'\n')
    print(json.dumps(dict(peer_cases=len(rows),enum_cases=len(labels),original_power_replies=True,native_kernel_loads=0)))

if __name__=='__main__':main()
