#!/usr/bin/env python3
"""Read-only, SHA-pinned cold-boot future producer and five-NOP audit."""
import hashlib, importlib.util, io, json, mmap, plistlib, struct, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
APP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so')
APP_SHA='a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'
CPIO_SHA='453890e36e7e6b4cd66641707cf80bd7754a0a37d6fba8dfce2af55fc169c926'
class Image:
 def __init__(self,data):self.b=data;self.e=ELFFile(io.BytesIO(data));self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 def off(self,v,n=1):
  ss=[s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']]
  assert len(ss)==1,(hex(v),n);s=ss[0];return s['p_offset']+v-s['p_vaddr']
 def read(self,v,n):o=self.off(v,n);return self.b[o:o+n]
 def u64(self,v):return struct.unpack('<Q',self.read(v,8))[0]
 def u32(self,v):return struct.unpack('<I',self.read(v,4))[0]
 def string(self,v):o=self.off(v);return self.b[o:self.b.index(b'\0',o)].decode()
 def instruction(self,v):
  i=next(self.md.disasm(self.read(v,4),v));return {'va':hex(v),'file_offset':hex(self.off(v,4)),'word':hex(self.u32(v)),'assembly':i.mnemonic+' '+i.op_str}
 def branch(self,v):
  w=self.u32(v);assert w&0x7c000000==0x14000000
  imm=w&0x3ffffff
  if imm&0x2000000:imm-=0x4000000
  return v+4*imm
def fp(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
 vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert vol.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 b=APP.read_bytes();assert hashlib.sha256(b).hexdigest()==APP_SHA;a=Image(b)
 spec=importlib.util.spec_from_file_location('builder',HERE/'build_candidate.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 cpio=Path(json.loads((HERE/'candidate-manifest.json').read_text())['initrd']['path']);assert builder.fp(cpio)['sha256']==CPIO_SHA
 with cpio.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
  rows=builder.scan(raw);by={r['name']:r for r in rows}
  app=by['usr/lib/appFw.so'];assert app['sha256']==APP_SHA
  r=by['usr/lib/libgrm-fbinit9.so'];shim=raw[r['offset']:r['offset']+r['bytes']]
 s=Image(shim);assert hashlib.sha256(shim).hexdigest()=='c58b6509e451a32474a6e2ace7c680a58427a5b685eaf27ece9a51153c2a3f45'
 tab=next(x for x in s.e.get_section_by_name('.symtab').iter_symbols() if x.name=='fx6_patch_blocking_calls.offs');nops=list(struct.unpack('<5Q',s.read(tab['st_value'],tab['st_size'])))
 assert nops==[0x12d824c,0x12d8250,0x12d8254,0x12d825c,0xc09e50]
 expected=[(0xc09de4,0x12d9fc8),(0x12da020,0x12d8174),(0x12d9dbc,0x1acce10),(0x12d9dc8,0x1acce84),(0x12d9ddc,0x10fa3cc),(0x12d9de0,0x10f727c),(0x12d9de8,0x1acd874),(0x1acd984,0xb19e30),(0x10fa424,0x10b9cb8),(0x10fa45c,0x10f62ac),(0x10b6ff4,0x1d96364),(0x10b700c,0x1e2d2c8),(0x1e2d2fc,0x1d72e50),(0x1e2d324,0x1e277e8),(0x1cd86ac,0x1accea8),(0x1accef0,0xb193d0),(0x12d824c,0x1a6ee10),(0x12d8250,0x1a5a230),(0x12d8254,0x20ed13c),(0x12d825c,0x1d96370),(0xc09e50,0xc09c14),(0x1d963c4,0x222dd58),(0x1e2535c,0x1e2518c)]
 edges=[]
 for pc,target in expected:
  assert a.branch(pc)==target;edges.append({**a.instruction(pc),'target':hex(target)})
 plt=a.e.get_section_by_name('.plt');dyn=a.e.get_section_by_name('.dynsym');imports={plt['sh_addr']+32+i*16:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(a.e.get_section_by_name('.rela.plt').iter_relocations())}
 assert imports[0xb19e30]=='_ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE' and imports[0xb193d0]=='_ZNSt18condition_variable10notify_oneEv'
 assert a.string(0x253e6c8)=='model_mutex.cpp' and a.string(0x253e740)=='void model::model_future::wait()'
 assert a.u64(0x29b91b0+0x2d*8)==0x10b6fe4
 assert struct.unpack('<h',a.read(0x24b5f48,2))[0]==0
 vtable=a.u64(0x2ee45a8);assert vtable==0x2ec5ee0
 rtti=a.u64(vtable+8);name=a.string(a.u64(rtti+8));assert name=='N5model18sequence_cold_bootE'
 assert a.u64(vtable+0x20)==0x1cd826c
 poolmap=a.u64(0x2eefd48);assert poolmap==0x25a1560
 worker=struct.unpack('<i',a.read(poolmap+0x2d*4,4))[0];assert worker==0
 assert a.u64(0x2eecc80)==0x1e25354
 snapshot_path=REPO/'work/fx6-wait-analysis-20261107/snapshot.json';resolved_path=snapshot_path.with_name('resolved.json');snapshot=json.loads(snapshot_path.read_text());resolved=json.loads(resolved_path.read_text());serial=Path(snapshot['serial']);assert fp(serial)['sha256']==snapshot['serial_sha256']
 serial_text=serial.read_text(errors='replace');runtime_nops=[]
 for n in nops:
  line=next(line for line in serial_text.splitlines() if f'FX6_PATCH_NOP off={hex(n)} ' in line);assert 'mprotect=0' in line;runtime_nops.append(line)
 tid224=[r for r in resolved['addresses'] if r['tid']==224];assert any(r['resolution'].get('elf_va')=='0x1acd988' for r in tid224)
 selected=[0x1acce20,0x1acce38,0x1acce90,0x1acce98,0x1accea0,0x1accecc,0x1accee4,0x1accef0,0x1acd8b4,0x1acd8b8,0x1acd8bc,0x1acd97c,0x1acd980,0x12d9c7c,0x12d9dcc,0x10b9ce0,0x10b9ce4,0x10b9cec,0x10b9cf0,0x10b9cf4,0x10f73e8,0x10f7408,0x10f7410,0x10f7418,0x1d72e74,0x1d72e78,0x1d72e80,0x1cd86a8,0x1d963a4,0x1d963cc,0x1d963d0,0x1e2527c,0x1e25280,0x1e25288,0x1e27918,0x1e27938]
 proof={'schema':'fx6-coldboot-future-wait-chain-v1','appfw':fp(APP),'actual_cpio':builder.fp(cpio),'actual_cpio_appfw_member_sha256':app['sha256'],'actual_cpio_shim':{'member':'usr/lib/libgrm-fbinit9.so','bytes':len(shim),'sha256':hashlib.sha256(shim).hexdigest(),'nop_table_va':hex(tab['st_value']),'nop_table_file_offset':hex(s.off(tab['st_value'])),'nop_offsets':[hex(n) for n in nops]},'final_snapshot':fp(snapshot_path),'final_resolved':fp(resolved_path),'final_serial':fp(serial),'actual_threads':{k:v['comm'] for k,v in snapshot['threads'].items()},'actual_appfw_wait':[r for r in tid224 if r['resolution'].get('elf_va') in ['0xd5ec','0xb3610','0x1acd988','0x12d9dec','0x12da024','0xc09de8']],'call_edges':edges,'selected_instruction_contracts':[a.instruction(v) for v in selected],'imports':{hex(v):imports[v] for v in [0xb19e30,0xb193d0]},'future':{'function':'model::model_future::wait()','entry':'0x1acd874','identity_source':'assert literal model_mutex.cpp / void model::model_future::wait()','promise_constructor':'0x1acce10','promise_ready_byte_offset':0,'promise_result_offset':4,'promise_condvar_pointer_offset':8,'future_layout':['ready_byte_pointer','result_pointer','condition_variable_pointer'],'promise_local_offset_from_initialize_fp':'0xb0','future_local_offset_from_initialize_fp':'0x210','fulfilled_by':'sequence_cold_boot::execute completion at0x1cd86ac ->0x1accea8','fulfill_effect':'under model mutex: ready byte=1, then notify_one on the promise condvar; waiter clears ready on return'},'dispatch':{'command_type':'0x2d','request_constructor':'0x10b9cb8','enqueue_wrapper':'0x10fa3cc','pending_list':'0x4da6500','flush':'0x10f727c','single_request_table_slot':'0x29b9318','single_request_dispatch':'0x10b6fe4','job_factory':'0x1e2d2c8','job_constructor':'0x1d72e50','vtable':hex(vtable),'rtti':name,'execute':'0x1cd826c','job_promise_field':'0x10','pool_map_table':hex(poolmap),'pool_index':worker,'worker_thread_metadata_id':6,'enqueue_worker_cond_notify':'0x1e27938'},'producer_executor':{'removed_callsite':'0x12d825c','original_target':'0x1d96370','worker_count':45,'worker_indices':'0..44','thread_metadata_ids':'6..50','entry':'0x1e25354 ->0x1e2518c','native_execute_virtual_callsite':'0x1e25288','virtual_slot':'0x10'},'runtime_nop_logs':runtime_nops,'conclusions':{'confirmed':'AppFw sampled in the model cold-boot future wait; actual shim NOP table removes the native pool creation call used by that future producer','causal_inference':'High-confidence self-induced executor removal explains absence of fulfillment without first invoking MWF/hardware-service absence as root cause','not_proved':['guest code NOP bytes readback','counterfactual run with worker pool restored','sequence_cold_boot reaches its success/notify path with remaining infra NOPs','native UI/menu readiness or physical camera safety']},'guest_execution_by_this_script':False}
 (HERE/'wait-chain.json').write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'proof':fp(HERE/'wait-chain.json'),'future':proof['future']['function'],'producer_rtti':name,'pool_index':worker,'removed_pool_call':'0x12d825c ->0x1d96370','worker_count':45,'serial_sha256':snapshot['serial_sha256']},indent=2))
if __name__=='__main__':main()
