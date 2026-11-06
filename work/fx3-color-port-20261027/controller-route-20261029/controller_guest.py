#!/usr/bin/env python3
"""Original output wrappers, global-pointer getter and controller list in RAM."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'image-lifecycle-20261029'))
from registry_guest import Guest as RegistryGuest,image,BASE,PIN,OBJ,DATA
MANAGER=0x11e076c
HEAD=MANAGER+0x110
CANDIDATE=DATA+0xb000
GLOBAL_A=0x13c4abc
GLOBAL_B=0x13c5134
SPLIT_BYTE=GLOBAL_B+0x394
SPANS=[(0x40a590,0x40a5a4),(0x9cfce8,0x9cfd10),(0x9d7c30,0x9d7c90),
       (0x9d824c,0x9d825e),(0x428f0c,0x4293c0),(0x429438,0x4299a4),(0x429a0c,0x429e3c),
       (0x69e402,0x69e4f0),(0x69e4f0,0x69e596),(0x69fe40,0x69ff4e),
       (0x69ea22,0x69ea96),(0x69ea96,0x69eb0e),(0x69eb0e,0x69eb7e),
       (0x69ec28,0x69eca0),(0x69ed18,0x69ed90),
       (0x23e55c,0x23e6d0),(0x23e6d0,0x23e89c),(0x23e89c,0x23e984),
       (0x23ea88,0x23ec54),(0x23ee20,0x23efec)]

def words(u,at,n):return list(struct.unpack('<'+'I'*n,u.mem_read(at,n*4)))

class Guest(RegistryGuest):
    def __init__(self,raw,split=0,registered=False):
        super().__init__(raw)
        self.u.mem_map(0x11e0000,0x1000);self.u.mem_map(0x13c5000,0x1000);self.u.mem_map(0x118c000,0x1000)
        self.split=split;self.registered=registered;self.controller_id=0
        self.manager_writes=[];self.output_entries={};self.wrapper_arguments=[];self.output_return_codes=[]
        self.pointer_production=None
        assert bytes(self.u.mem_read(0xeee420,1))==b'\0' # Original diagnostic flag, not patched.

    def write(self,u,access,at,size,value,user):
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if MANAGER<=at and at+size<=MANAGER+0x150:
            assert 0x69fe40<=pc<0x69ff4e or 0x69e4f0<=pc<0x69e596,hex(pc)
            self.manager_writes.append(dict(offset=hex(at-MANAGER),bytes=size,value=hex(value),pc=hex(pc)));return
        if 0x118c6a0<=at and at+size<=0x118c6c0:
            assert pc in [0x429254,0x429de4],hex(pc)
            return
        if at==0x1004794:
            assert pc==0x42925a and size==1 and value==1
            return
        return super().write(u,access,at,size,value,user)

    def code(self,u,pc,size,user):
        if pc==self.stop_point:return super().code(u,pc,size,user)
        if pc in [0x4ec038,0x9d1b4c,0x53ce98]:
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            self.boundary=dict(operation='before_original_dynamic_cast' if pc==0x4ec038 else 'before_original_output_error_cleanup',
                               pc=hex(pc),registers=[hex(v) for v in regs],original_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),
                               native_call=False,service_reply_supplied=False,cast_result_supplied=False)
            if pc==0x4ec038:
                assert regs[0]==CANDIDATE and regs[1]==0xbadc28 and regs[2] in [0xbaddc8,0xbae48c]
                self.boundary['candidate_object_constructed']=False
                self.boundary['cast_target']='SplitEEController' if regs[2]==0xbae48c else 'EEController'
            u.emu_stop();return
        labels={0x428f0c:'first_output_helper',0x429438:'second_output_helper',0x429a0c:'third_output_helper',
                0x69ea22:'EE_first_wrapper',0x69ec28:'SplitEE_first_wrapper',0x69eb0e:'EE_third_wrapper',
                0x69ed18:'SplitEE_third_wrapper',0x69e402:'controller_lookup'}
        if pc in labels:
            label=labels[pc];self.output_entries[label]=self.output_entries.get(label,0)+1
            if pc in [0x69ea22,0x69ec28,0x69eb0e,0x69ed18]:
                regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
                sp=u.reg_read(R.UC_ARM_REG_SP)
                self.wrapper_arguments.append(dict(wrapper=label,pc=hex(pc),registers=[hex(v) for v in regs],
                                                   stack_words=[hex(v) for v in words(u,sp,5)],
                                                   r3_image=None if not regs[3] else bytes(u.mem_read(regs[3],0x98)).hex()))
        if pc in [0x429258,0x429dda]:
            self.output_return_codes.append(dict(pc=hex(pc),raw_r1=u.reg_read(R.UC_ARM_REG_R1)))
        if any(a<=pc<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)

    def initialize_manager(self):
        self.u.mem_write(MANAGER,b'\xa7'*0x150)
        out=self.bounded(0x69fe88,[]);assert out['returned']
        assert words(self.u,MANAGER,4)==[0,MANAGER+0x10,16,16]
        assert words(self.u,HEAD,4)==[HEAD,HEAD,0,MANAGER+4]
        chain=[];ptr=words(self.u,MANAGER+4,1)[0]
        while ptr:
            assert ptr not in chain;chain.append(ptr);ptr=words(self.u,ptr,1)[0]
        assert chain==[MANAGER+0x10+16*i for i in range(16)]
        initialized=dict(header=[hex(v) for v in words(self.u,MANAGER,4)],head=[hex(v) for v in words(self.u,HEAD,4)],
                         original_free_nodes=[hex(p) for p in chain],native_calls=0)
        if self.registered:
            out=self.bounded(0x69e4f0,[MANAGER,CANDIDATE]);assert out['returned']
            self.controller_id=int(out['raw_r0'],16);assert self.controller_id==1
            assert words(self.u,HEAD,3)==[MANAGER+0x10,MANAGER+0x10,1]
            assert words(self.u,MANAGER+0x10,4)==[HEAD,HEAD,1,CANDIDATE]
        return dict(initialized=initialized,original_registered_id=self.controller_id,registered_candidate_pointer=hex(CANDIDATE) if self.registered else None,
                    candidate_object_constructed=False,scope='Original manager initialization and list registration. The registered address is an explicit object-pointer fixture, not a constructed EE controller or a normal NRV broker result.',
                    writes=self.manager_writes)

    def prepare(self):
        upstream=super().prepare()
        # Original caller fragment obtains actual global addresses through original getter.
        self.fragment(0x40a590-BASE,0x40a5a4-BASE,{9:OBJ,8:0})
        assert words(self.u,OBJ+0x8d8,3)==[0,GLOBAL_A,GLOBAL_B]
        self.pointer_production=dict(original_caller_fragment='0x40a590..0x40a5a4',original_getter='0x9cfce8',fields_8d8_8dc_8e0=[hex(v) for v in words(self.u,OBJ+0x8d8,3)])
        # Still explicit inputs: no normal controller acquisition/binding is claimed.
        self.u.mem_write(OBJ+0x8e4,struct.pack('<I',self.controller_id))
        self.u.mem_write(OBJ+0x70,struct.pack('<I',0xffffffff))
        self.u.mem_write(SPLIT_BYTE,bytes([self.split]))
        return upstream

def main():
    raw=image();rows=[]
    for registered in [False,True]:
        for split in [0,1]:
            for kind in [3,4]:
                g=Guest(raw,split,registered);g.initialize();manager=g.initialize_manager()
                descriptor=None if kind==3 else g.seed_descriptor(0x440,1)
                row=g.execute_case(0x9000,0,kind)
                expected_wrapper=('SplitEE_' if split else 'EE_')+('third_wrapper' if kind==3 else 'first_wrapper')
                assert g.output_entries[expected_wrapper]==2 and g.output_entries['controller_lookup']==2
                if registered:
                    assert all(p['boundary']['pc']=='0x4ec038' for p in row['phases'])
                    assert all(p['boundary']['cast_target']==('SplitEEController' if split else 'EEController') for p in row['phases'])
                    assert not g.output_return_codes
                else:
                    target='0x53ce98' if kind==3 else '0x9d1b4c'
                    assert all(p['boundary']['pc']==target for p in row['phases'])
                    assert len(g.output_return_codes)==2 and all(x['raw_r1']==2 for x in g.output_return_codes)
                rows.append(dict(case=f'{"registered_candidate" if registered else "empty_manager"}_split{split}_kind{kind}',
                                 manager=manager,explicit_split_flag=split,explicit_object_controller_id=g.controller_id,
                                 explicit_object_70_invalid_handle=True,held_descriptor_fixture=descriptor,original_pointer_production=g.pointer_production,
                                 caller=row,output_entries=g.output_entries,original_wrapper_arguments=g.wrapper_arguments,original_output_return_codes=g.output_return_codes,
                                 scope='One initialized manager and one declared scene configuration per case. Original helper and wrapper code run; empty-manager failure is real guest control flow. Positive lookup stops before casting an unconstructed candidate. No cast, virtual call, controller submission or device result is fabricated.'))
    g=Guest(raw,registered=True);manager=g.initialize_manager()
    matched=g.bounded(0x69e402,[MANAGER,1]);missing=g.bounded(0x69e402,[MANAGER,2])
    assert matched['returned'] and matched['raw_r0']==hex(CANDIDATE)
    assert missing['returned'] and missing['raw_r0']=='0x0'
    result=dict(cp_sha256=PIN,cases=rows,list_lookup_cases=[dict(manager=manager,matched=matched,missing=missing)],
                source_spans=[dict(va=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a-BASE:z-BASE]).hexdigest()) for a,z in SPANS],
                scope='Original global-pointer getter, controller-manager initialization/register/search and downstream output wrappers in Unicorn RAM only. 8 caller cases stop at unreplied dynamic-cast/error-cleanup boundaries; 1 list case verifies match and miss without reply stubs. Original diagnostic flags are zero; inherited context/lock, VFX/STP/pre/EI/queue fixtures remain. Controller ID binding, candidate object address, invalid own descriptor and zeroed global bodies/split flags are declared inputs. No normal NRV-controller allocation, real constructed EE object, MAIN recording pixels, complete donor ISP, modified package or flashability is proven.')
    (HERE/'controller-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(caller_cases=len(rows),list_lookup_cases=1,dynamic_cast_results_supplied=0,device_actions=0)))

if __name__=='__main__':main()
