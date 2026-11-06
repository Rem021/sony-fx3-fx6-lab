#!/usr/bin/env python3
"""Original XML key/guard/queue/plugin route, halted before system() entry."""
import hashlib,json,struct
from xml_guest import Guest as XmlGuest,sources,HERE,HANDLER,KEY_STRING,TRUSTED,USER,USER_XML,DATA,HEAP,STACK,STOP,R,PIN

class Guest(XmlGuest):
    def __init__(self,views,files):
        super().__init__(views,files);self.boundary=None;self.mutex_events=[]
        families=['XmlConfigHandler::Initialize','XmlConfigHandler::CheckGuardResult','XmlConfigHandler::checkGuardResult','XmlConfigHandler::executeGuard','XmlConfigHandler::Execute',
                  'ThreadPlugin::ThreadPlugin','ThreadPlugin::Initialize','ThreadIdQueue::ThreadIdQueue','ExecutionQueue::','FreeExecutionQueue::','ExecutionContainer::','BaseQueue::','BaseContainer::','Plugin::Execute','ShellPlugin::Execute']
        for base,view in views:
            for address,n in view.sizes.items():
                if any(t in view.labels.get(address,'') for t in families):self.allowed.append((base+address,base+address+n))

    def code(self,u,pc,size,user):
        if pc in self.plt:
            name=self.plt[pc]
            if name.startswith('pthread_mutex_'):
                assert name in ['pthread_mutex_init','pthread_mutex_lock','pthread_mutex_unlock']
                pointer=u.reg_read(R.UC_ARM64_REG_X0);assert HEAP<=pointer<HEAP+0x100000
                self.mutex_events.append(dict(adapter=name,address=hex(pointer),single_thread_fixture=True))
                self.steps+=1;assert self.steps<=self.budget;self.ret(0);return
            if name=='printf':
                self.events.append(dict(adapter='discarded printf logging',format=self.string(u.reg_read(R.UC_ARM64_REG_X0)).decode()))
                self.steps+=1;assert self.steps<=self.budget;self.ret(0);return
            if name=='system':
                self.steps+=1;assert self.steps<=self.budget
                self.boundary=dict(operation='system_request_boundary',pc=hex(pc),command=self.string(u.reg_read(R.UC_ARM64_REG_X0)).decode(),native_execution=False)
                u.emu_stop();return
        return super().code(u,pc,size,user)

    def dispatch(self,key,expect_system):
        self.string_object(KEY_STRING,key)
        result,steps=self.run(self.named('Updater::XmlConfigHandler::CheckGuardResult(Updater::StringHandler const&)'),[HANDLER,KEY_STRING])
        assert bool(result)==expect_system
        if not expect_system:
            ret,execute_steps=self.run(self.named('Updater::XmlConfigHandler::Execute()'),[HANDLER])
            assert self.boundary is None
            return dict(guard_queue_return=result,guard_queue_instructions=steps,execute_instructions=execute_steps,boundary=None)
        u=self.u
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP);u.reg_write(R.UC_ARM64_REG_X0,HANDLER)
        before=self.steps;u.emu_start(self.named('Updater::XmlConfigHandler::Execute()'),STOP+4,count=self.budget)
        assert self.boundary and u.reg_read(R.UC_ARM64_REG_PC)==int(self.boundary['pc'],16)
        assert STACK<=u.reg_read(R.UC_ARM64_REG_SP)<STACK+0x10000
        return dict(guard_queue_return=result,guard_queue_instructions=steps,execute_instructions=self.steps-before,boundary=self.boundary)

def main():
    views=sources();raw=(HERE.parent/'package-20261028/updaterfs/config/config.xml').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='09cd171039d921224fe9e66b9e44350f7f5e8bc8e75cea7aefe2235719f544da'
    cases=[('trusted_config','config_sum/config.sum',False,True),('user_config','offline_probe',True,True),('unknown_key','absent_key',True,False)]
    rows=[]
    for label,key,with_user,expected in cases:
        files={TRUSTED:raw}
        if with_user:files[USER]=USER_XML
        g=Guest(views,files);g.run(g.named('Updater::XmlConfigHandler::XmlConfigHandler(Updater::UPDATER_ACTION_MODE)'),[HANDLER,6])
        # The initializer creates original execution/free queues and thread bookkeeping.
        # No pthread_create is permitted, and the fixtures contain no thread="yes" node.
        g.run(g.named('Updater::XmlConfigHandler::Initialize(Updater::CallbackInterface*)'),[HANDLER,DATA+0x8000])
        assert g.load(TRUSTED)['return_value']==1
        if with_user:assert g.load(USER,True)['return_value']==1
        outcome=g.dispatch(key,expected)
        if expected:
            command=outcome['boundary']['command'];assert 'export UPDATER_ACTION_MODE=6;' in command
            assert 'export PATH=/tmp_updater/updater/update/program:' in command
            expected_tail='us_crc32sum.sh config file' if label=='trusted_config' else 'probe.txt'
            expected_prefix='export EXTRACT_ROOT=/tmp_updater/updater/update; export PATH=/tmp_updater/updater/update/program:/tmp_updater/updater/bodyfs/bin:/usr/bin:$PATH; export UPDATER_ACTION_MODE=6; '
            assert command==expected_prefix+expected_tail
        rows.append(dict(case=label,key=key,with_user_config=with_user,declared_action_mode=6,**outcome,total_instructions=g.steps,
                         original_function_entries=g.entries,host_import_counts=g.imports,mutex_adapters=g.mutex_events,file_adapter_events=g.events,original_empty_string_zero_writes=g.global_writes))
    result=dict(body_sha256=PIN,common_sha256=hashlib.sha256(views[1][1].raw).hexdigest(),xml_sha256=hashlib.sha256(views[2][1].raw).hexdigest(),official_config_sha256=hashlib.sha256(raw).hexdigest(),user_xml_sha256=hashlib.sha256(USER_XML).hexdigest(),cases=rows,
                scope='Original XML handler construction/Initialize, queue and thread-bookkeeping construction, XML file loading and Parse, key comparison, CheckGuardResult/checkGuardResult/executeGuard, execution queue, Execute/Plugin::Execute/ShellPlugin::Execute and original StringHandler run in one synthetic process per case. The selected official and inert user procs have no guard child or asynchronous thread attribute; no actual guard program outcome is proven. Mutex init/lock/unlock are explicit sequential RAM fixtures; no pthread_create is permitted. Each matching case stops at original system PLT without invoking it or returning fabricated success. Unknown key drains no commands. No host shell/path lookup, full TAR/controller/container, real update admission, native target load, USB or camera.')
    (HERE/'dispatch-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),system_requests=2,unknown_key_no_request=True,native_system_calls=0,camera_actions=0)))

if __name__=='__main__':main()
