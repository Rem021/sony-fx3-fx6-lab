#!/usr/bin/env python3
"""Original CP image-registry code in RAM only; no service or hardware replies."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'stp-buffer-20261029'))
from buffer_query_guest import Guest as QueryGuest,image,BASE,PIN,OBJ
from caller_binding_guest import STACK,DATA,STOP

POOL=0x1172e70
STRIDE=0x88
GROUP_STRIDE=60*STRIDE
GROUP3=POOL+3*GROUP_STRIDE
CURRENT=0x13c38d8
PREVIOUS=0x13c38e8
CAPACITY=0xf1b630
ENABLED=0xf1b620
# These are VA bounds. No embedded string/switch data is admitted as executable.
SPANS=[(0x9cf02c,0x9cf09c),(0x9cecb8,0x9ced44),(0x9e6c5e,0x9e6caa),
       (0x403a78,0x403c9c),(0x403cd0,0x403d16),(0x403d54,0x403df4),
       (0x44f004,0x44f084),(0x44d710,0x44d732),(0x44e934,0x44e954),
       (0x9d4c5e,0x9d4c92),(0x66a736,0x66a746),(0x9cee38,0x9cef30)]
BOUNDARIES={0x5579d4:'before_destructor_registration',0x4a032c:'before_common_handle_operation',
            0x44de7c:'before_owned_image_release',0x428f0c:'before_next_output_helper',
            0x429a0c:'before_other_output_helper'}

class Guest(QueryGuest):
    def __init__(self,raw):
        super().__init__(raw)
        self.u.mem_map(0x1172000,0x9000)
        self.registry_writes=[];self.index_writes=[];self.lifecycle_entries={}
        self.initialization=None;self.temporary_cleanup_inputs=[]

    def write(self,u,access,at,size,value,user):
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if POOL<=at and at+size<=POOL+4*GROUP_STRIDE:
            assert any(a<=pc<z for a,z in SPANS) or 0x558af4<=pc<0x558c30 or 0x558400<=pc<0x558700,hex(pc)
            self.registry_writes.append(dict(offset=hex(at-POOL),bytes=size,value=hex(value),pc=hex(pc)));return
        if CURRENT<=at and at+size<=PREVIOUS+16:
            assert pc in [0x403bca,0x403c5c,0x9cef2a],hex(pc)
            self.index_writes.append(dict(va=hex(at),bytes=size,value=hex(value),pc=hex(pc)));return
        return super().write(u,access,at,size,value,user)

    def code(self,u,pc,size,user):
        if pc==self.stop_point:return super().code(u,pc,size,user)
        if pc in BOUNDARIES:
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            row=dict(operation=BOUNDARIES[pc],pc=hex(pc),registers=[hex(v) for v in regs],
                     original_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),native_call=False,service_reply_supplied=False)
            if pc==0x4a032c:
                row['request_input_word']=hex(struct.unpack('<I',u.mem_read(regs[2]-4,4))[0])
            if pc==0x428f0c:
                row['argument2_payload']=None if not regs[2] else bytes(u.mem_read(regs[2],0x98)).hex()
                row['argument2_selected_fields']=None if not regs[2] else {hex(off):hex(struct.unpack('<I',u.mem_read(regs[2]+off,4))[0]) for off in [0x18,0x20,0x28,0x2c,0x30,0x68,0x78]}
            self.boundary=row;u.emu_stop();return
        for va,label in [(0x9cecb8,'frame_threshold_cleanup'),(0x9ced10,'entry_reset'),
                         (0x403a78,'reuse_or_acquire'),(0x403cd0,'entry_status'),
                         (0x403d54,'allocate_entry'),(0x44f004,'acquire_descriptor'),
                         (0x44d710,'image_acquire_wrapper'),(0x44e934,'image_status_wrapper'),
                         (0x9e6c5e,'descriptor_release_or_clear'),(0x9cee38,'frame_metadata_writer')]:
            if pc==va:self.lifecycle_entries[label]=self.lifecycle_entries.get(label,0)+1
        if pc==0x66a736:
            ptr=u.reg_read(R.UC_ARM_REG_R0);b=bytes(u.mem_read(ptr,0x50))
            self.temporary_cleanup_inputs.append(dict(va=hex(ptr),handle=hex(struct.unpack_from('<I',b)[0]),owned_byte=b[6],descriptor_sha256=hashlib.sha256(b).hexdigest()))
        if any(a<=pc<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)

    def bounded(self,va,args,extra=()):
        self.boundary=None;u=self.u
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),args[i] if i<len(args) else 0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        if extra:u.mem_write(STACK+0xf000,struct.pack('<'+'I'*len(extra),*extra))
        u.emu_start(va|1,STOP+4,count=120000)
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if self.boundary:assert pc==int(self.boundary['pc'],16)
        else:
            assert pc==STOP,hex(pc)
            assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
            assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return dict(boundary=self.boundary,raw_r0=hex(u.reg_read(R.UC_ARM_REG_R0)),returned=pc==STOP)

    def initialize(self):
        self.u.mem_write(POOL,b'\xa7'*(4*GROUP_STRIDE))
        out=self.bounded(0x9cf02c,[])
        assert out['boundary']['pc']=='0x5579d4'
        assert out['boundary']['registers'][:3]==['0x9ceab3','0x0','0x13fcc64']
        expected=bytearray(b'\xa7'*STRIDE)
        struct.pack_into('<I',expected,0,0xffffffff)
        struct.pack_into('<H',expected,4,0);expected[6]=0
        struct.pack_into('<I',expected,8,0);expected[0x10:0x64]=b'\0'*0x54
        struct.pack_into('<III',expected,0x64,0xffffffff,0xffffffff,0)
        expected[0x70]=1;expected[0x71]=0
        struct.pack_into('<III',expected,0x78,0,0,0)
        body=bytes(self.u.mem_read(POOL,4*GROUP_STRIDE))
        assert body==bytes(expected)*240
        self.initialization=dict(original_initialized_records=240,record_bytes=STRIDE,group_stride=hex(GROUP_STRIDE),
                                 body_sha256=hashlib.sha256(body).hexdigest(),untouched_padding_preserved=True,
                                 boundary=out['boundary'],original_write_events=len(self.registry_writes))
        return self.initialization

    def seed_descriptor(self,key=0x440,owned=0,handle=0x12345678):
        # An explicit held-descriptor fixture, never a real allocation reply or pixel buffer.
        body=bytearray(self.u.mem_read(GROUP3,STRIDE))
        struct.pack_into('<I',body,0,handle);struct.pack_into('<H',body,4,1)
        body[6]=owned;struct.pack_into('<I',body,8,key)
        struct.pack_into('<III',body,0x10,0x52000100,0x12340,0x56780)
        self.u.mem_write(GROUP3,bytes(body))
        assert not any(lo<=0x52000100<=hi for lo,hi,_ in self.u.mem_regions())
        return dict(held_record_va=hex(GROUP3),handle=hex(handle),key=hex(key),owned_byte=owned,
                    plane_words=['0x52000100','0x12340','0x56780'],plane_memory_mapped=False,
                    origin='declared already-held descriptor metadata only; not a query reply, allocation or live snapshot')

    def mark_frame(self,frame,subframe=0):
        # Original writer checks the two existing descriptor words before modifying metadata.
        row=self.bounded(0x9cee38,[3,frame,subframe,0],
                         [0x52000100,0x12340,0x11223344,0x55667788,0x99aabbcc,0,0,0,0])
        assert row['returned'] and row['raw_r0']=='0x1'
        assert struct.unpack('<I',self.u.mem_read(GROUP3+0x64,4))[0]==((frame<<8)+subframe)&0xffffffff
        return dict(original_writer='0x9cee38',declared_frame=hex(frame),declared_subframe=hex(subframe),
                    returned=row,record_metadata=bytes(self.u.mem_read(GROUP3+0x64,0x24)).hex())

def main():
    raw=image();rows=[]
    init=Guest(raw);initialization=init.initialize()
    rows.append(dict(case='original_registry_constructor_240_records',result=initialization))
    for label,frame,sub,owned,upper in [
        ('expired_borrowed_descriptor',0x203,0,0,None),
        ('future_frame_kept',0x204,1,0,None),
        ('upper_marker_keeps_descriptor',0x203,0,0,0x20401),
        ('expired_owned_descriptor_stops_before_release',0x203,0,1,None)]:
        g=Guest(raw);g.initialize();fixture=g.seed_descriptor(owned=owned);writer=g.mark_frame(frame,sub)
        if upper is not None:g.u.mem_write(GROUP3+0x68,struct.pack('<I',upper))
        before=bytes(g.u.mem_read(GROUP3,STRIDE));out=g.bounded(0x9cecb8,[3,0x204,0])
        after=bytes(g.u.mem_read(GROUP3,STRIDE))
        if owned:
            assert out['boundary']['pc']=='0x44de7c' and before==after
            assert out['boundary']['registers'][:3]==['0x12345678','0x2','0x5']
        elif frame==0x203 and upper is None:
            assert out['returned'] and struct.unpack_from('<I',after)[0]==0xffffffff
            assert after[0x10:0x50]==b'\0'*0x40 and after[0x64:0x6c]==b'\xff'*8
            assert after[0x70:0x72]==b'\1\0' and after[0x78:0x84]==b'\0'*12
        else:assert out['returned'] and before==after
        rows.append(dict(case=label,descriptor_fixture=fixture,original_frame_writer=writer,
                         declared_upper_marker=None if upper is None else hex(upper),threshold_arguments=[3,'0x204',0],
                         result=out,record_before=before.hex(),record_after=after.hex(),entries=g.lifecycle_entries))
    g=Guest(raw);g.initialize();before=bytes(g.u.mem_read(GROUP3,STRIDE));out=g.bounded(0x9cecb8,[3,0x204,0])
    assert out['returned'] and bytes(g.u.mem_read(GROUP3,STRIDE))==before
    rows.append(dict(case='empty_descriptor_cleanup_noop',result=out,entries=g.lifecycle_entries))
    # These combined caller cases retain all declared upstream VFX/STP/queue/input fixtures.
    for label,selector,key,owned,status in [
        ('cached_440_passes_original_payload',0,0x440,1,0),
        ('cached_614_passes_original_payload',2,0x614,1,0),
        ('mismatched_key_owned_stops_at_release',0,0x614,1,0),
        ('mismatched_key_borrowed_clears_then_acquires',0,0x614,0,0),
        ('fresh_entry_stops_at_handle_operation',0,None,0,0),
        ('cached_status_pending_stops_at_handle_operation',0,0x440,1,1)]:
        g=Guest(raw);g.initialize();fixture=None if key is None else g.seed_descriptor(key,owned)
        if status:g.u.mem_write(GROUP3+0x71,bytes([status]))
        row=g.execute_case(0x9000,selector,4)
        first=row['phases'][0]['boundary']
        if key is not None and key==(0x440 if selector==0 else 0x614) and not status:
            assert first['pc']=='0x428f0c'
            assert first['argument2_selected_fields']=={'0x18':'0x0','0x20':'0x1','0x28':'0x52000100','0x2c':'0x12340','0x30':'0x56780','0x68':'0x0','0x78':'0x5'}
            assert bytes(g.u.mem_read(GROUP3+6,1))==bytes([owned])
            assert g.lifecycle_entries.get('image_acquire_wrapper',0)==0 and g.lifecycle_entries.get('image_status_wrapper',0)==0
            assert len(g.temporary_cleanup_inputs)==2 and all(t['handle']=='0x12345678' and t['owned_byte']==0 for t in g.temporary_cleanup_inputs)
        elif key is not None and not status and owned:assert first['pc']=='0x44de7c'
        else:
            assert first['pc']=='0x4a032c' and first['registers'][:2]==['0x2a','0x5'] and first['request_input_word']=='0x2'
            assert g.lifecycle_entries.get('image_status_wrapper' if status else 'image_acquire_wrapper',0)==2
            if key is not None and not status:
                assert struct.unpack('<I',g.u.mem_read(GROUP3,4))[0]==0xffffffff
                assert bytes(g.u.mem_read(GROUP3+0x10,0x40))==b'\0'*0x40
        rows.append(dict(case=label,declared_descriptor_fixture=fixture,declared_status_byte=status,
                         caller=row,entries=g.lifecycle_entries,registry_index_writes=g.index_writes,temporary_cleanup_inputs=g.temporary_cleanup_inputs))
    g=Guest(raw);g.initialize();row=g.execute_case(0x5000,0,0)
    assert all(p['boundary']['pc']=='0x428f0c' and p['boundary']['argument2_payload'] is None for p in row['phases'])
    assert g.lifecycle_entries['frame_threshold_cleanup']==2 and not g.lifecycle_entries.get('image_acquire_wrapper',0)
    rows.append(dict(case='kind1_empty_registry_cleanup_then_next_helper',caller=row,entries=g.lifecycle_entries))
    result=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(va=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a-BASE:z-BASE]).hexdigest()) for a,z in SPANS],
                scope='Original RAM registry constructor initializes 240 records and stops before destructor registration. Original metadata writer and threshold cleanup execute with explicit held-descriptor fixtures; owned release stops before its service. Independent original MLUT-caller cases execute real reuse/acquire and descriptor-copy/cleanup instructions, then stop before output helper or common handle operation, with no service reply fabrication. Upstream scene, mode, look22, VFX hardware/OSAL/STP/queue fixtures remain. Descriptor plane words are unmapped synthetic values; no pixel memory, source CMOS RAW, DMA, recording, donor ISP or flashability is proven. No native or device execution.')
    (HERE/'registry-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),initialized_records=240,service_replies=0,real_pixel_buffers=0,device_actions=0)))

if __name__=='__main__':main()
