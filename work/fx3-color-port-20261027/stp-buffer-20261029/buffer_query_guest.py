#!/usr/bin/env python3
"""Original mode/selector producers -> original MLUT caller -> image-query boundary."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'frame-route-20261029'))
from caller_gate_guest import Guest as GateGuest,image,BASE,PIN,OBJ,RECORDS
from scene_context_guest import SCENE,SOURCE
BSS_VECTOR=0x118b6c0
SPANS=[(0x300242,0x300252),(0x300282,0x30028a),(0x303746,0x303764),(0x303184,0x30319a),
       (0x307040,0x30706e),(0x597a1a,0x597a52),(0x149fa4,0x14a17e),(0x320438,0x3205a8),(0x3205c4,0x320608)]

class Guest(GateGuest):
    def __init__(self,raw):
        super().__init__(raw);self.u.mem_map(0x118b000,4096);self.vector_writes=[];self.producer_writes=[]
    def write(self,u,access,at,size,value,user):
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if BSS_VECTOR<=at and at+size<=BSS_VECTOR+0xc8:
            assert 0x9d7210<=pc<0x9d7320
            self.vector_writes.append(dict(offset=hex(at-BSS_VECTOR),bytes=size,value=hex(value),pc=hex(pc)));return
        if at in [OBJ+0x4b0,OBJ+0x440,OBJ+0x15d8]:
            self.producer_writes.append(dict(offset=hex(at-OBJ),bytes=size,value=hex(value),pc=hex(pc)))
        return super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc==self.stop_point:return super().code(u,pc,size,user)
        if pc in [0x9cecb8,0x403a78,0x429a0c]:
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            self.boundary=dict(operation='before_original_frame_query' if pc==0x9cecb8 else 'before_original_image_query' if pc==0x403a78 else 'before_original_next_stage',
                               pc=hex(pc),registers=[hex(v) for v in regs],query_result_supplied=False,native_call=False)
            if pc==0x403a78:
                self.boundary['temporary_image_first_word']=hex(struct.unpack('<I',u.mem_read(regs[3],4))[0]);assert self.boundary['temporary_image_first_word']=='0xffffffff'
            u.emu_stop();return
        if any(a<=pc-BASE<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)
    def supply_original_mode_record(self,mode):
        # Constructor inputs are declared. They are not claimed to be a normal menu selection.
        self.record_constructor=True
        self.call(0x9d1038,[mode,0,0,0x40fc09],[0,1,0,SOURCE])
        self.record_constructor=False
        assert struct.unpack('<I',self.u.mem_read(SOURCE,4))[0]==mode
        self.fragment(0x8ce7ac,0x8ce7d0,{4:SCENE,5:SOURCE})
    def execute_case(self,mode,selector,constant_kind=0):
        upstream=self.prepare()
        if not constant_kind:self.supply_original_mode_record(mode)
        self.call(0x9d7210,[SCENE,BSS_VECTOR])
        assert struct.unpack('<I',self.u.mem_read(BSS_VECTOR+0xc,4))[0]==SCENE+0xde0
        # Explicit synthetic input fields; original load/store snippets populate the consumer object.
        self.u.mem_write(SCENE+0xde0+0x968,struct.pack('<I',selector))
        self.u.mem_write(SCENE+0xd30,struct.pack('<I',0x204))
        self.fragment(0x300242,0x300252,{4:OBJ,11:BSS_VECTOR})
        self.fragment(0x300282,0x30028a,{4:OBJ,1:SCENE+0xde0})
        if constant_kind==3:self.fragment(0x303184,0x30319a,{9:OBJ})
        elif constant_kind==4:self.fragment(0x307040,0x30706e,{11:OBJ,0:0,2:0})
        else:self.fragment(0x303746,0x303764,{9:OBJ})
        kind=struct.unpack('<I',self.u.mem_read(OBJ+0x15d8,4))[0]
        assert struct.unpack('<I',self.u.mem_read(OBJ+0x4b0,4))[0]==mode
        assert struct.unpack('<I',self.u.mem_read(OBJ+0x440,4))[0]==selector
        phases=[self.invoke_prefix(),self.invoke_prefix()]
        assert phases[0]['phase']==dict(state=1,look=0,pending=0,commands=0)
        assert phases[1]['phase']==dict(state=2,look=22,pending=1,commands=1)
        return dict(declared_mode=hex(mode),declared_parameter_968=selector,declared_frame_word='0x204',constant_kind_source=constant_kind,
                    original_record_mode=hex(struct.unpack('<I',self.u.mem_read(SOURCE,4))[0]),
                    original_record_sha256=hashlib.sha256(bytes(self.u.mem_read(SOURCE,0x32c))).hexdigest(),original_constructor_writes=self.constructor_writes,
                    original_buffer_kind=kind,original_producer_writes=self.producer_writes,original_bss_vector_writes=self.vector_writes,
                    original_bss_parameter_pointer=hex(struct.unpack('<I',self.u.mem_read(BSS_VECTOR+0xc,4))[0]),
                    upstream=upstream,phases=phases,commands=[list(c) for c in self.commands],instructions_total=self.instructions)

def main():
    raw=image();rows=[]
    fixtures=[('mode5000_frame_query',0x5000,0,0,1,0x9cecb8),('original_kind4_query440',0x9000,0,4,4,0x403a78),
              ('original_kind4_query614',0x9000,2,4,4,0x403a78),('original_constant_three',0x9000,0,3,3,0x429a0c)]
    for label,mode,selector,constant,expected_kind,target in fixtures:
        guest=Guest(raw);row=guest.execute_case(mode,selector,constant);row['case']=label
        assert row['original_buffer_kind']==expected_kind
        for phase in row['phases']:
            boundary=phase['boundary'];assert boundary['pc']==hex(target) and not boundary['query_result_supplied']
            if target==0x9cecb8:assert boundary['registers'][:3]==['0x3','0x204','0x0']
            elif target==0x403a78:assert boundary['registers'][:3]==['0x3','0x440' if selector==0 else '0x614','0x0']
            else:assert boundary['registers'][:2]==[hex(OBJ),hex(OBJ+0x1248)]
        rows.append(row)
    result=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(file_offset=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a:z]).hexdigest()) for a,z in SPANS],
                scope='Original GetInfo constructor supplies declared mode to the record and original copies. Original vector constructor populates the actual BSS address returned by the original getter. Original Sync snippets produce object mode and selector; original ImgModeDefaultParam/wrapper supplies type1, and original constant stores supply type3/type4. No type2 production is claimed. Original gated MLUT caller then executes through the next utility up to original frame/image queries or next stage, without query replies. Declared input modes/selector/frame word, original-caller fragment entry, producer-fragment live-ins, STP success stub, free VFX/OSAL/hardware/pre/EI/queue fixtures and look22 remain. These are independent from the STP-before-MMIO experiment; they do not establish actual STP completion, normal mode selection, buffers, pixels, donor ISP or modified firmware acceptance. No target-native or device action.')
    (HERE/'buffer-query-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_buffer_kinds=[r['original_buffer_kind'] for r in rows],query_replies_fabricated=0,real_buffers=0,device_actions=0)))

if __name__=='__main__':main()
