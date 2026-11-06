#!/usr/bin/env python3
"""Original GET_FILE2 decision fragments only; no camera or file service executes."""
from pathlib import Path
import argparse,datetime,hashlib,io,json,struct,sys,traceback
from elftools.elf.elffile import ELFFile
import capstone,unicorn
from unicorn import arm64_const as ar
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage129-AP-DMM-config-and-device-trial-plan'));import ap_config_audit as previous
sys.path.insert(0,str(BASE/'stage9-protocol/host'));import offline_codec as oldcodec
SO=BASE/'stage2/extraction/files/nflasha15/lib/libJiritsu.so'
SO_SHA='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
S=0x11000000;FP=S+0x8000;REQ=S+0x100;ROOTPTR=S+0x1000;STATE=S+0x2000;PATH=S+0x5000
SP=0x10020000;STATE_SLOT=0x46bd8
def sha(b):return hashlib.sha256(b).hexdigest()
def reg(s):return getattr(ar,'UC_ARM64_REG_'+s.upper())
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
class Image:
    def __init__(self):
        raw=SO.read_bytes();assert sha(raw)==SO_SHA;self.elf=ELFFile(io.BytesIO(raw))
        assert self.elf['e_machine']=='EM_AARCH64';self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        self.md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
        sy=self.elf.get_section_by_name('.dynsym');p=self.elf.get_section_by_name('.plt')['sh_addr']
        self.plt={p+32+i*16:sy.get_symbol(r['r_info_sym']).name for i,r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())}
        assert self.plt[0x5ca0]=='_ZN11CFileAccessC1Ev' and self.plt[0x5b00]=='_ZN11CFileAccess4openEPKci'
    def read(self,a,n):
        s=next(s for s in self.segments if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        return s.data()[a-s['p_vaddr']:a-s['p_vaddr']+n]
    def cstr(self,a):return self.read(a,100).split(b'\0')[0].decode('ascii')
    def listing(self,a,z):
        instructions=[]
        for i in self.md.disasm(self.read(a,z-a),a):
            target=None
            if i.mnemonic in ('b','bl'):
                try:target=self.plt.get(int(i.op_str.lstrip('#'),16))
                except ValueError:pass
            instructions.append({'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,'original_import':target})
        return {'range':[hex(a),hex(z)],'sha256':sha(self.read(a,z-a)),'instructions':instructions}
class Guest:
    def __init__(self,image):
        self.image=image;self.u=unicorn.Uc(unicorn.UC_ARCH_ARM64,unicorn.UC_MODE_ARM);pages={}
        for s in image.segments:
            flags=(unicorn.UC_PROT_READ if s['p_flags']&4 else 0)|(unicorn.UC_PROT_WRITE if s['p_flags']&2 else 0)|(unicorn.UC_PROT_EXEC if s['p_flags']&1 else 0)
            assert not flags&(unicorn.UC_PROT_WRITE) or not flags&(unicorn.UC_PROT_EXEC)
            for a in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):pages[a]=flags
        for a,flags in sorted(pages.items()):self.u.mem_map(a,4096,flags)
        for s in image.segments:self.u.mem_write(s['p_vaddr'],s.data())
        self.u.mem_map(S,0x10000);self.u.mem_map(0x10000000,0x20000)
        self.u.mem_write(S,bytes([0xa5])*0x10000);self.u.mem_write(0x10000000,bytes([0xc3])*0x20000)
        self.boundaries={0x5ca0:'before_original_FileAccess_constructor',0x5b00:'before_original_FileAccess_open',
            0xa0e4:'before_regular_stat_path',0x9ef0:'before_original_error_status_path'}
        self.hooks=[self.u.hook_add(unicorn.UC_HOOK_CODE,self.code),self.u.hook_add(unicorn.UC_HOOK_MEM_WRITE,self.write)]
        self.reason=None;self.pcs=[];self.stores=[]
    def code(self,u,pc,n,user):
        self.pcs.append(hex(pc))
        if pc in self.boundaries:self.reason=self.boundaries[pc];u.emu_stop();return
        assert 0xa020<=pc<0xa074,hex(pc)
    def write(self,u,access,a,n,v,user):self.stores.append({'pc':hex(u.reg_read(reg('pc'))),'address':hex(a),'bytes':n})
    def phase(self,label,entry,**regs):
        before=[(s['p_vaddr'],bytes(self.u.mem_read(s['p_vaddr'],s['p_memsz']))) for s in self.image.segments]
        before += [(S,bytes(self.u.mem_read(S,0x10000))),(0x10000000,bytes(self.u.mem_read(0x10000000,0x20000)))]
        for n,v in regs.items():self.u.reg_write(reg(n),v)
        self.pcs=[];self.stores=[];self.reason=None;self.u.emu_start(entry,0,count=100,timeout=1000000)
        assert self.reason and not self.stores
        assert all(bytes(self.u.mem_read(a,len(b)))==b for a,b in before)
        return {'label':label,'entry':hex(entry),'stop_pc':hex(self.u.reg_read(reg('pc'))),'reason':self.reason,
            'pcs':self.pcs,'original_stores':self.stores,'all_images_stack_scratch_unchanged':True,
            'constructor_file_open_write_sync_stat_mount_or_transport_executed':False}
    def close(self):
        for h in self.hooks:self.u.hook_del(h)
def case(image,label,kind=0,selector=3,global_pointer=True,object_pointer=True,pending_pointer=True,pending_bytes=7,name_nonempty=True):
    m=Guest(image)
    def q(a,n):m.u.mem_write(a,struct.pack('<Q',n))
    try:
        m.u.mem_write(REQ,bytes(0x80));m.u.mem_write(REQ+0x28,bytes([kind,selector,0]))
        m.u.mem_write(FP+0x68,b'declared-path\0' if name_nonempty else b'\0')
        q(STATE_SLOT,ROOTPTR if global_pointer else 0);q(ROOTPTR,STATE if object_pointer else 0)
        q(STATE+0x1828,S+0x6000 if pending_pointer else 0);q(STATE+0x1830,pending_bytes);q(STATE+0x1840,PATH)
        m.u.mem_write(PATH,b'/tmp/jiritsu/jit.log\0')
        ev=[m.phase('independent post-path-resolution frame: original special-case decision',0xa020,
            sp=SP,x29=FP,x19=REQ)]
        selected=name_nonempty and kind==0 and selector==3 and global_pointer and object_pointer and pending_pointer and pending_bytes!=0
        expected='before_original_error_status_path' if not name_nonempty else 'before_original_FileAccess_constructor' if selected else 'before_regular_stat_path'
        assert ev[-1]['reason']==expected
        args=None
        if selected:
            assert m.u.reg_read(reg('x0'))==FP+0xaa8
            ev.append(m.phase('independent post-constructor frame: original write-open argument setup',0xa060))
            assert ev[-1]['reason']=='before_original_FileAccess_open'
            args=[m.u.reg_read(reg('x0')),m.u.reg_read(reg('x1')),m.u.reg_read(reg('w2'))]
            assert args==[FP+0xaa8,PATH,0x441]
        return {'label':label,'declared_kind':kind,'declared_selector':selector,'declared_global_pointer':global_pointer,
            'declared_object_pointer':object_pointer,'declared_pending_pointer':pending_pointer,'declared_pending_bytes':pending_bytes,
            'declared_resolved_name_nonempty':name_nonempty,'original_special_branch_selected':selected,
            'native_prepared_open_arguments':args,'events':ev,
            'inputs_after_unexecuted_path_resolution_and_constructor_are_explicit':True,
            'real_runtime_reachability_or_any_file_operation_proven':False}
    finally:m.close()
def run(out):
    previous.shared_volume_check();assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());image=Image()
    j={'status':'RUNNING','source_sha256':sha(Path(__file__).read_bytes()),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'cases':[],'actual_Mac_cache_camera_Windows_file_or_host_service_operations':False,'goal_complete':False,'persistent_write_release':False}
    try:
        trials=[('pending_jit_log',{}),('global_null',{'global_pointer':False}),('object_null',{'object_pointer':False}),
            ('pending_null',{'pending_pointer':False}),('pending_empty',{'pending_bytes':0}),
            ('upstream_read_args_ff',{'selector':0xff}),('empty_resolved_name',{'name_nonempty':False})]
        for label,args in trials:j['cases'].append(case(image,label,**args))
        assert sha(Path(oldcodec.__file__).read_bytes())=='38d2c77bcf4403f600726eb88868d714e2186627564653d8578cef4e98e23977'
        ap='/setting/DmmCfg.bin';prefix=image.cstr(0x30e17)
        assert prefix=='/tmp/jiritsu' and image.cstr(0x327e6)=='%s%s' and image.cstr(0x11d7e)=='%s/%s'
        try:oldcodec.encode_setpath(ap,sequence=1)
        except oldcodec.CodecError:rejected=True
        else:raise AssertionError('old conservative policy unexpectedly accepts setting')
        j['backup_candidate_limits']={'stage9_codec_source_sha256':sha(Path(oldcodec.__file__).read_bytes()),
            'stage9_setpath_rejects_plain_AP_path':rejected,'stage9_max_host_data':oldcodec.MAX_DATA_BYTES,
            'official_AP_file_bytes':66796,'official_AP_exceeds_old_host_limit_by':66796-oldcodec.MAX_DATA_BYTES,
            'plain_absolute_AP_path_native_format_candidate':prefix+ap,
            'native_format_selection_static_not_snprintf_executed':True,
            'request_has_no_device_file_length_limit':oldcodec.encode_read(sequence=2).hex(),
            'AP_backup_current_adapter_ready':False}
        urls={'pmca_pinned_readFile':'https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L916-L934',
            'linux49_open_flags':'https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/fcntl.h',
            'linux49_mount_flags':'https://github.com/torvalds/linux/blob/v4.9/include/uapi/linux/fs.h'}
        put(STAGE/'source-and-scope-audit.json',{'original_Jiritsu_sha256':SO_SHA,
            'listings':[image.listing(a,z) for a,z in ((0x9e74,0xa29c),(0x92e8,0x940c),(0x771c,0x7734),
                (0xead0,0xedcc),(0xe220,0xe610))],
            'primary_sources_revisited':urls,'decoded_open_flags441':['O_WRONLY','O_CREAT','O_APPEND'],
            'sys_mount_input_flags':'0xc0ed0490','sys_mount_input_MS_RDONLY_bit_set':False,
            'actual_mount_helper_effects_unproven':True,
            'special_kind0_selector3_writes_pending_buffer_to_jit_log_before_stat':True,
            'special_does_not_prove_firmware_bytes_written_or_exploit':True,
            'FF_selector_bypasses_special_fragment_but_not_mount_stat_allocation_fsync_cleanup':True,
            'normal_GetFile2_open_flags':0,'file_size_is_stat_derived_whole_read_not_bounded_by_request_max':True,
            'close_calls_fsync_and_exception_handlers_do_not_prove_runtime_cleanup_completion':True,
            'PMCA_pFunc_ff01_cmd2_is_a_separate_family_not_the_proven_Jiritsu_route':True,
            'PMCA_ff01_model_acceptance_native_handler_mapping_and_no_side_effects_unproven':True})
        j['native_phases']=sum(len(c['events']) for c in j['cases']);assert j['native_phases']==8
        j['status']='PASS_GET_FILE2_SPECIAL_BRANCH_AND_BACKUP_LIMIT_AUDIT_NOT_READ_ONLY_DEVICE_RELEASE'
        put(out/'read-path-results.json',j)
        print(json.dumps({'status':j['status'],'cases':7,'native_phases':8,'backup_adapter_ready':False,'device_operations':False}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc();put(out/'attempt-failure.json',j);raise
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);run(a.parse_args().out)
