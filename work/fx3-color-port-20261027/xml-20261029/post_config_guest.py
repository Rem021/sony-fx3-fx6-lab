#!/usr/bin/env python3
"""Original config-tag post callback reaches original XML load and dispatch in RAM."""
import hashlib,json,struct
from dispatch_guest import Guest as DispatchGuest
from xml_guest import sources,HERE,HANDLER,TRUSTED,USER,USER_XML,ROOT,DATA,STACK,STOP,R,PIN

ROOT_STRING=DATA+0x500
BODY=DATA+0x700

class Guest(DispatchGuest):
    def __init__(self,views,files):
        super().__init__(views,files)
        body=views[0][1];self.allowed += [(0x1001371c,0x1001371c+len(body.function(0x1371c))),(0x1001b4c8,0x1001b4d8)]
        self.stat_events=[]

    def code(self,u,pc,size,user):
        if pc in self.plt:
            name=self.plt[pc]
            if name=='__xstat':
                assert u.reg_read(R.UC_ARM64_REG_X0)==0
                path=self.string(u.reg_read(R.UC_ARM64_REG_X1)).decode();assert path==USER
                output=u.reg_read(R.UC_ARM64_REG_X2);assert STACK<=output<STACK+0x10000
                exists=path in self.files;self.stat_events.append(dict(adapter='RAM existence-only stat',path=path,exists=exists))
                self.steps+=1;assert self.steps<=self.budget;self.ret(0 if exists else -1);return
            if name=='__cxa_allocate_exception':
                assert u.reg_read(R.UC_ARM64_REG_X0)==16
                self.steps+=1;assert self.steps<=self.budget;self.ret(self.allocate(16));return
            if name=='__cxa_throw':
                pointer=u.reg_read(R.UC_ARM64_REG_X0)
                self.steps+=1;assert self.steps<=self.budget
                self.boundary=dict(operation='original_exception_boundary',code=hex(struct.unpack('<I',u.mem_read(pointer+8,4))[0]),pc=hex(pc),native_unwind=False)
                u.emu_stop();return
        return super().code(u,pc,size,user)

    def post(self):
        self.string_object(ROOT_STRING,ROOT)
        self.u.mem_write(BODY+8,struct.pack('<Q',ROOT_STRING));self.u.mem_write(BODY+0x20,struct.pack('<Q',HANDLER))
        u=self.u
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        u.reg_write(R.UC_ARM64_REG_X0,DATA+0x900);u.reg_write(R.UC_ARM64_REG_X1,BODY)
        before=self.steps;u.emu_start(0x1001371c,STOP+4,count=self.budget)
        if self.boundary:assert self.boundary['operation']=='original_exception_boundary'
        else:assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        return dict(instructions=self.steps-before,stat_adapters=self.stat_events,exception_boundary=self.boundary)

def main():
    views=sources();trusted=(HERE.parent/'package-20261028/updaterfs/config/config.xml').read_bytes()
    assert hashlib.sha256(trusted).hexdigest()=='09cd171039d921224fe9e66b9e44350f7f5e8bc8e75cea7aefe2235719f544da'
    cases=[('present_valid',USER_XML),('absent',None),('present_malformed',b'<updater><programs><proc key="offline_probe">')]
    rows=[]
    for label,user_xml in cases:
        files={TRUSTED:trusted}
        if user_xml is not None:files[USER]=user_xml
        g=Guest(views,files)
        g.run(g.named('Updater::XmlConfigHandler::XmlConfigHandler(Updater::UPDATER_ACTION_MODE)'),[HANDLER,6])
        g.run(g.named('Updater::XmlConfigHandler::Initialize(Updater::CallbackInterface*)'),[HANDLER,DATA+0x8000])
        assert g.load(TRUSTED)['return_value']==1
        post=g.post();outcome=None;match=None
        if label=='present_malformed':assert post['exception_boundary']['code']=='0x30002'
        else:
            assert post['exception_boundary'] is None
            match=g.key('offline_probe');assert match['matches']==(label=='present_valid')
            outcome=g.dispatch('offline_probe',label=='present_valid')
            if label=='present_valid':assert outcome['boundary']['command'].endswith('; probe.txt')
        opens=[e for e in g.events if e['adapter']=='RAM fopen' and e['path']==USER]
        assert len(opens)==(0 if label=='absent' else 1)
        rows.append(dict(case=label,post_callback=post,key_check=match,dispatch=outcome,user_file_open_requests=len(opens),
                         original_function_entries=g.entries,host_import_counts=g.imports,mutex_adapters=g.mutex_events,file_adapter_events=g.events,original_empty_string_zero_writes=g.global_writes,total_instructions=g.steps))
    output=dict(body_sha256=PIN,common_sha256=hashlib.sha256(views[1][1].raw).hexdigest(),xml_sha256=hashlib.sha256(views[2][1].raw).hexdigest(),cases=rows,
                scope='Original ConfigKeyTag::PostExecute plus its 16-byte stat wrapper, original root/name StringHandler concatenation, original vtable LoadUserConfig, libul_xml FILE/document parsing, key lookup and synchronous guardless queue/Plugin/ShellPlugin route execute in the same RAM fixture. Stat supplies explicit synthetic existence; FILE supplies declared immutable bytes; mutexes are sequential fixtures. Missing optional file is skipped; malformed existing XML reaches original throw code 0x30002 without native unwinding. Valid inert user proc reaches system request boundary without executing it. No complete TAR/controller group transition, external input API, real root/stat, original script process, native loader, signature admission, USB/camera or flashing is proven.')
    (HERE/'post-config-guest-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_post_to_system_boundary=1,missing_file_skipped=True,malformed_original_exception='0x30002',native_system_calls=0,camera_actions=0)))

if __name__=='__main__':main()
