"""Original FX3 launch-route evidence only; never loads or executes Sony code."""
from pathlib import Path
from hashlib import sha256
import io,json,re,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
OLD=BASE/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands'


class Image:
    def __init__(self,path,want):
        self.path=path;self.raw=path.read_bytes();assert sha256(self.raw).hexdigest()==want
        self.elf=ELFFile(io.BytesIO(self.raw));self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
        self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        table=self.elf.get_section_by_name('.dynsym');self.syms={s.name:s for s in table.iter_symbols() if s.name}
        p=self.elf.get_section_by_name('.plt')['sh_addr']
        self.plt={p+32+i*16:table.get_symbol(r['r_info_sym']).name for i,r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())}
        self.instructions=list(self.md.disasm(self.elf.get_section_by_name('.text').data(),self.elf.get_section_by_name('.text')['sh_addr']))
    def read(self,at,n):
        s=next(s for s in self.segments if s['p_vaddr']<=at and at+n<=s['p_vaddr']+s['p_filesz'])
        return self.raw[s['p_offset']+at-s['p_vaddr']:s['p_offset']+at-s['p_vaddr']+n]
    def text(self,at):return self.read(at,256).split(b'\0',1)[0].decode('ascii')
    def function(self,name):
        s=self.syms[name];raw=self.read(s['st_value'],s['st_size'])
        return {'name':name,'VA':s['st_value'],'bytes':len(raw),'sha256':sha256(raw).hexdigest(),
            'original_hex':raw.hex(),'instructions':[{'pc':i.address,'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,
                'PLT':self.plt.get(int(i.op_str[1:],16)) if i.mnemonic in ('b','bl') and i.op_str.startswith('#0x') else None}
                for i in self.md.disasm(raw,s['st_value'])]}
    def call(self,pc,name):
        ins=list(self.md.disasm(self.read(pc,4),pc));assert len(ins)==1 and ins[0].mnemonic=='bl'
        assert self.plt[int(ins[0].op_str[1:],16)]==name
        return {'pc':pc,'original_hex':self.read(pc,4).hex(),'callee':name}


def main():
    jir=Image(OLD/'originals/lib/libJiritsu.so','bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9')
    core=Image(BASE/'stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/lib/libsencore.so','a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    debug=jir.function('cmd_debug');date=jir.function('sys_set_timeofday');shell=jir.function('_ZN13CShellExecute12ExecShellNewEPc')
    values={}
    for i in debug['instructions']:
        match=re.fullmatch(r'mov w([0-5]), #(0x[0-9a-f]+|[0-9]+)',i['asm'])
        if match and i['pc']<0x83e8:values[int(match[1])]=int(match[2],0)
    assert values=={0:2017,1:7,2:4,3:21,4:42,5:26}
    assert jir.text(0x31e6d)=='/bin/date -s %02d%02d%02d%02d%04d.%02d'
    assert jir.text(0x30707)=='/bin/sh' and jir.text(0x3070f)=='-c'
    calls=[jir.call(0x83e8,'sys_set_timeofday'),jir.call(0x7bd8,'_ZN13CShellExecute12ExecShellNewEPc'),
           jir.call(0x6cb0,'fork'),jir.call(0x6cc0,'_exit'),jir.call(0x6cd0,'execv'),jir.call(0x6ce0,'waitpid')]
    assert jir.read(0x6cbc,4).hex()=='00008012' and jir.read(0x6cdc,4).hex()=='02008052'
    assert jir.read(0x83ec,4).hex()=='601e00b9' and jir.read(0x83f0,4).hex()=='00008052'
    direct=[]
    targets={jir.syms['_ZN13CShellExecute12ExecShellNewEPc']['st_value']}
    targets.update(a for a,n in jir.plt.items() if n=='_ZN13CShellExecute12ExecShellNewEPc')
    for i in jir.instructions:
        if i.mnemonic in ('b','bl') and i.op_str.startswith('#0x') and int(i.op_str[1:],16) in targets:direct.append(i.address)
    assert direct==[0x7acc,0x7bd8]
    assert jir.text(0x31203)=='/tmp/jiritsu/libJit.so'
    assert jir.text(0x31ffe)=='/tmp/jiritsu/ramdsk_libJit/libJit.so'
    assert jir.text(0x32049)=='CreateScriptI' and jir.text(0x3206b)=='LoadScriptI'
    loads=[jir.call(pc,'dlopen') for pc in (0x8f1c,0x9908,0xbb04)]
    assert jir.read(0x98e4,4).hex()=='e0efff35'
    calls.extend(loads);calls.extend([jir.call(0xbadc,'sys_file_copy'),jir.call(0xbb4c,'dlsym'),jir.call(0xbbb4,'dlsym')])
    assert core.text(0x171ac)=='libpro%02X.so'
    plugin_name=next(n for n in core.syms if 'GetPluginModule' in n)
    plugin=core.function(plugin_name)
    core.call(0xdc24,'snprintf');core.call(0xdc40,'dlopen')
    # Do not promote the generic helper's name-format argument into a USB path
    # control claim; the observed callsite/factory still needs its own binding.
    functions=[debug,date,shell,jir.function('sys_tar_process'),jir.function('adj_cmd_set_file2'),
               jir.function('_ZN10IM_JIRITSU10CImJiritsu10jit_threadEPv') if '_ZN10IM_JIRITSU10CImJiritsu10jit_threadEPv' in jir.syms else
               jir.function(next(n for n in jir.syms if 'jit_thread' in n)),plugin]
    report={'status':'STATIC_LAUNCH_ROUTES_AUDITED_NOT_CAMERA_ENTRY_PROOF',
        'sources':[{'path':str(x.path),'sha256':sha256(x.raw).hexdigest()} for x in (jir,core)],
        'functions':functions,'specific_calls':calls,'direct_shell_callers_in_this_library':direct,
        'findings':{
            'debug_fixed_argv':'/bin/date -s 070421422017.26','debug_command_accepts_no_user_shell_text':True,
            'debug_stores_child_status_then_returns_zero':True,
            'fork_failure_calls__exit_minus1_in_calling_process':True,
            'waitpid_options_zero_no_timeout':True,
            'execv_inherits_environment_not_explicit_per_child_env':True,
            'direct_file_load_fixed_path':'/tmp/jiritsu/libJit.so',
            'jit_thread_fixed_copy_then_load_path':'/tmp/jiritsu/ramdsk_libJit/libJit.so',
            'jit_thread_calls_factory_inside_current_process_not_isolated_exec':True,
            'module_factory_example_format':'libpro%02X.so',
            'arbitrary_RAM_path_process_launch_proven':False},
        'reject_as_ready_routes':['debug/date trigger','fixed Jiritsu library replacement','tar helper name alone','generic module helper name alone'],
        'actual_loader_thread_exits_or_return_to_MSC_proven':False,'original_Sony_code_loaded_or_executed':False,
        'new_camera_or_USB_operations':0}
    with (HERE/'launch-route-review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'functions':len(functions),'fixed_date':'070421422017.26','isolated_RAM_launch_proven':False,'new_camera_operations':0}))


if __name__=='__main__':main()
