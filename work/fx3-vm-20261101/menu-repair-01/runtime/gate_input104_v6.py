"""AP104 original owner lifetime and completion probes; QEMU Z1 only.
No original memory/register writes. Inherited input/shutdown controls unchanged.
"""
import json,re,struct,time,select
from gate_input102_v4 import valid_command,KernelObserver as BackupObserver
from gdb_native104_v3 import InputGate
from gdb_sysregs104_v2 import Sysregs

class KernelObserver(BackupObserver):
    def __init__(self,run,gate,qmp,proof):
        super().__init__(run,gate,qmp,proof)
        self.extra=json.loads((run.parent.parent/'ap104-observer-original-proof-v1.json').read_text())
        self.module_bases={};self.sysregs=None;self.owner_epochs={};self.epoch_counts={};self.calls={};self.tids={};self.serial_offset=0;self.serial_tail='';self.written=0;self.last_metadata=0;self.first_unfetched=None
    def _add(self,base,points):
        self.gate.connect()
        if self.sysregs is None:self.sysregs=Sysregs(self.gate,self.run)
        for p in points:
            address=base+p['offset'];raw=self.gate.virtual_read(address,4)
            if raw is None or raw.hex()!=p['raw']:raise RuntimeError('AP104 original point unavailable/mismatch: '+p['label'])
            if self.gate.packet(f'Z1,{address:x},4')!='OK':raise RuntimeError('AP104 TCG breakpoint unavailable')
            self.points[address]=dict(p,runtime_word=raw.hex(),runtime_address=hex(address))
    def install_uipc(self,base):
        if 'uipc'in self.module_bases:return
        self._add(base,[p for p in self.extra['uipc_points'] if p['label']!='completion_alloc_owner_read']);self.module_bases['uipc']=base;self.save(force=True)
    def install_gpe(self,base):
        if 'gpe'in self.module_bases:return
        # Installation occurs while paused outside a debug stop. Try native
        # CPU address spaces only for original-word validation. Every later
        # debug stop selects its actual CPU again; no qC/Hg while observing.
        self.gate.connect();threads=[];r=self.gate.packet('qfThreadInfo')
        while r.startswith('m'):threads.extend(r[1:].split(','));r=self.gate.packet('qsThreadInfo')
        if r!='l':raise RuntimeError('Cannot enumerate paused native CPUs')
        selected=None
        for t in threads:
            if self.gate.packet('Hg'+t)!='OK':raise RuntimeError('Cannot select paused address space')
            if all(self.gate.virtual_read(base+p['offset'],4)==bytes.fromhex(p['raw'])for p in self.extra['user_gpe_points']):selected=t;break
        if selected is None:raise RuntimeError('No paused AP address space matches original libgpe words')
        self._add(base,self.extra['user_gpe_points']);self.module_bases['gpe']=base;self.user_install_cpu=selected;self.save(force=True)
    def _maps(self):
        with (self.run/'serial.log').open('rb')as f:f.seek(self.serial_offset);raw=f.read();self.serial_offset=f.tell()
        s=self.serial_tail+raw.decode(errors='replace')
        for m in re.finditer(r'FX3_GPE104_[A-Z_]+ tid=(\d+) tpidr=(0x[0-9a-f]+)',s):self.tids[int(m[2],16)]=int(m[1])
        self.serial_tail=s[-1024:]
    def _queue(self,pointer):
        if not 0xffffff8000000000<=pointer<1<<64:return {'pointer':hex(pointer),'unavailable':True}
        b=self.gate.virtual_read(pointer,64)
        if b is None:return {'pointer':hex(pointer),'unavailable':True}
        return {'pointer':hex(pointer),'raw64':b.hex(),'flags':b[0],'message_count_s16':struct.unpack_from('<h',b,2)[0],'owner_token':hex(struct.unpack_from('<Q',b,48)[0]),'wait_list_raw':hex(struct.unpack_from('<Q',b,8)[0]),'message_list_raw':hex(struct.unpack_from('<Q',b,16)[0]),'lock_pointer_raw':hex(struct.unpack_from('<Q',b,56)[0])}
    def _thread(self,kernel):
        tp=self.sysregs.read('TPIDR_EL0');self._maps();r={'TPIDR_EL0':hex(tp),'mapped_user_tid':self.tids.get(tp),'mapped_user_tid_scope':'latest passive logger syscall(gettid) for this TPIDR; kernel rows independently read native task pid'}
        if kernel:
            task=self.sysregs.read('SP_EL0');r['native_task']=hex(task)
            if 0xffffff8000000000<=task<1<<64:
                pid=self.gate.virtual_read(task+self.extra['current_task']['pid_offset'],4);comm=self.gate.virtual_read(task+self.extra['current_task']['comm_offset'],16)
                r['native_task_pid']=int.from_bytes(pid,'little')if pid else None;r['native_comm']=comm.split(b'\0',1)[0].decode(errors='replace')if comm else None
        return tp,r
    def poll(self):
        try:return self._poll_native()
        except Exception as exc:
            self.observer_error=repr(exc)
            # Persist BEFORE cleanup, including partial failing record and
            # actual post-step PC. Failure evidence must not depend on close.
            (self.run/'ap104-error-records.json').write_text(json.dumps({'observer_error':repr(exc),'records':self.records,'first_unfetched':self.first_unfetched,'guest_resume_after_error':False},indent=2)+'\n')
            self.save(force=True)
            raise
    def _poll_native(self):
        if not self.points or self.removed:return False
        if self.qmp('query-status').get('return',{}).get('status')!='debug':
            if not self.gate.wait_native_stop(.25):return False
            if self.qmp('query-status').get('return',{}).get('status')!='debug':return False
        if self.gate.native_stop is None and not self.gate.wait_native_stop(3):
            raise RuntimeError('AP104 debug stop lacks native T05 identity')
        self.gate.bind_native_stop()
        native_stop=self.gate.native_stop;native_thread=self.gate.native_thread
        started=time.monotonic();raw=bytes.fromhex(self.gate.packet('g'));regs=struct.unpack_from('<33Q',raw);pc=regs[32]
        if pc not in self.points:raise RuntimeError('AP104 unexpected native debug stop '+hex(pc))
        point=self.points[pc]
        if point.get('module')not in ['uipc','gpe']:return super().poll()
        module=point['module'];label=point['label'];tp,thread=self._thread(module=='uipc')
        record={'index':len(self.records)+1,'host_monotonic':started,'point':point,'registers':{f'x{i}':hex(regs[i])for i in list(range(8))+list(range(19,31))},'SP':hex(regs[31]),'PC':hex(pc),'PSTATE':hex(struct.unpack_from('<I',raw,264)[0]),'thread':thread,'native_stop_reply':native_stop,'native_cpu_thread':native_thread,'read_only_original_memory_and_registers':True}
        self.records.append(record);queue=None;expected=None
        if module=='uipc':
            queue=regs[point['queue_register']];record['queue_before']=self._queue(queue)
            record['kernel_caller_PC']=hex(regs[30]);record['dynamic_flags_raw_w19']=hex(regs[19]&0xffffffff)
            if label.startswith('dynamic_owner_'):
                record['original_frame_module8c_and_saved_link80']=self.read(regs[29]+0x80,16)
                expected=regs[point['token_register']]if point['token_register']is not None else 0
                record['owner_store_expected']=hex(expected)
            else:record['destination_QID']=hex(regs[24]&0xffffffff)
        else:
            lr=regs[30];base=self.module_bases['gpe'];record['caller_PC']=hex(lr);record['caller_libgpe_relative']=hex(lr-base)if base<=lr<base+0x20000 else None
            kind='sync'if'SyncCallback'in label else'send';key=(kind,tp,regs[31]);record['function_stack_identity']=[kind,hex(tp),hex(regs[31])]
            if label=='original_Main_SyncCallback_enter':
                record.update(destination_QID=hex(regs[1]&0xffffffff),this_pointer=hex(regs[0]),call_path='original_Main_SyncCallback');self.calls[key]=record['index']
            elif label=='original_SendDrawComp_enter':
                q=regs[0]&0xffffffff;n=regs[2];b=self.gate.virtual_read(regs[1],n)if 0<n<=64 else None
                record.update(destination_QID=hex(q),status_pointer=hex(regs[1]),bytes=n,status_raw=None if b is None else b.hex(),call_path='original_Main_SyncCallback'if lr==base+0xa12c else'original_Main_failure_status'if lr==base+0x9c50 else'caller_outside_known_original_completion_sites',observed_owner_epoch=self.owner_epochs.get(q));self.calls[key]=record['index']
            else:
                entry=self.calls.pop(key,None);record['call_enter_index']=entry;record['return_w0']=regs[0]&0xffffffff
                if label=='original_shared_Send_return':record['completion_bool_result']=regs[0]&255 if entry is not None else None;record['unmatched_shared_send_return']=entry is None
        if self.gate.packet(f'z1,{pc:x},4')!='OK':raise RuntimeError('AP104 remove native breakpoint failed')
        stepped=self.gate.packet('s')
        record['step_stop']=stepped
        if not stepped.startswith('T05'):raise RuntimeError('AP104 original instruction step failed')
        self.gate.bind_native_stop()
        after=bytes.fromhex(self.gate.packet('g'));after_regs=struct.unpack_from('<33Q',after)
        expected_pc=regs[30] if module=='gpe'and label.endswith('_return')else pc+4
        record['step_native_cpu_thread']=self.gate.native_thread
        record['post_step_PC']=hex(after_regs[32]);record['expected_post_step_PC']=hex(expected_pc)
        if after_regs[32]!=expected_pc:raise RuntimeError('AP104 original single-vCPU instruction PC mismatch')
        if self.gate.packet(f'Z1,{pc:x},4')!='OK':raise RuntimeError('AP104 native breakpoint rearm failed')
        if module=='uipc':
            record['queue_after_original_instruction']=self._queue(queue)
            if expected is not None:
                actual=record['queue_after_original_instruction'].get('owner_token')
                if actual!=hex(expected):raise RuntimeError('AP104 native owner store readback mismatch')
                if label=='dynamic_owner_claim'and expected:
                    q=(expected&0xffffffff)|0x80000000;epoch=self.epoch_counts.get(q,0)+1;self.epoch_counts[q]=epoch;identity={'observation_epoch':epoch,'claim_record':record['index'],'queue_pointer':hex(queue),'owner_token':hex(expected),'expected_published_QID':hex(q),'scope':'counted exact original owner store; not an extra original generation field'};self.owner_epochs[q]=identity;record['new_observation_epoch']=identity
                elif expected==0:
                    before=int(record['queue_before'].get('owner_token','0'),16);q=(before&0xffffffff)|0x80000000;record['released_observation_epoch']=self.owner_epochs.pop(q,None)
            if label=='first_unfetched_return':
                record['actual_original_error_w0']=struct.unpack_from('<i',after)[0];self.first_unfetched={'record':record['index'],'destination_QID':record.get('destination_QID'),'queue_before':record['queue_before'],'host_monotonic':started,'actual_original_error_w0':record['actual_original_error_w0']}
        record['step_stop']=stepped;record['observer_pause_seconds']=time.monotonic()-started;self.total_pause+=record['observer_pause_seconds'];self.save()
        if self.first_unfetched is None:self.qmp('cont')
        return True
    def save(self,force=False):
        if not hasattr(self,'written'):return
        pending=self.records[self.written:]
        with (self.run/'ap104-observations.jsonl').open('a')as f:
            for r in pending:
                if 'step_stop'not in r and not self.removed:break
                f.write(json.dumps(r)+'\n');self.written+=1
        if not force and not self.removed and time.monotonic()-self.last_metadata<1:return
        self.last_metadata=time.monotonic();meta={'method':'QEMU TCG Z1 tables; native stopped CPU; original instruction single step; no original memory/register writes','module_bases':{k:hex(v)for k,v in self.module_bases.items()},'backup_base_from_sysfs':None if self.base is None else hex(self.base),'installed_points':list(self.points.values()),'records_count':len(self.records),'observer_error':getattr(self,'observer_error',None),'total_observer_pause_seconds':self.total_pause,'first_unfetched':self.first_unfetched,'breakpoints_removed':self.removed,'removal_replies_nonzero':getattr(self,'removal_replies_nonzero',None),'fallback_clear_all_CPUs':getattr(self,'fallback_clear_all_CPUs',None),'original_words_unchanged':getattr(self,'original_words_unchanged',None),'optional_probe_omitted':'completion_alloc_owner_read at +3480 only; all original owner stores, all native completion sites and first_unfetched at +34a4 retained', 'notification_mode':'native T05 identity; Hg/Hc only actual stopped CPU; vCont;s:thread holds other CPUs; asynchronous vCont;c resume','timing_limit':'Recorded pause sums processing after debug detection; excludes stop-notification transit and QMP latency. Debug observation alters scheduling; UART order alone is not happens-before'}
        if self.removed:meta['records']=self.records
        (self.run/'ap104-kernel-observations.json').write_text(json.dumps(meta,indent=2)+'\n')
