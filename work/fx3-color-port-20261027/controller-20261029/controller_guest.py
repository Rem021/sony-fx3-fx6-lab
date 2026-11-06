#!/usr/bin/env python3
"""Original updater TAR controller with a RAM filesystem and explicit startup fixtures.

No FDAT/UFU container is produced, no host requested path or shell is used.
"""
from pathlib import Path
import hashlib,json,struct,sys,tarfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'xml-20261029'))
from post_config_guest import Guest as ConfigGuest
from xml_guest import sources,TRUSTED,ROOT,USER,DATA,HEAP,STACK,STOP,R,PIN

UPDATER=DATA+0x2000
RING=DATA+0x2200
RING_VTABLE=DATA+0x2300
CALLBACK=DATA+0x2400
STREAM=DATA+0x4000
PEEK=STOP+0x200
ADVANCE=STOP+0x204
ENVP=DATA+0xe000
ENVAR=DATA+0xe100
ERRNO=DATA+0xe200
STARTUP='/tmp_updater/updater/bodyfs/bin/startupdate.sh'
TEXT=b'FX3 inert controller probe\n'
XML=b'<updater version="1.0"><programs><proc key="trigger.txt"><shell module="probe.txt"/></proc></programs></updater>'

def tar_member(name,data=b'',directory=False):
    info=tarfile.TarInfo(name);info.mode=0o755 if directory else 0o644
    info.type=tarfile.DIRTYPE if directory else tarfile.REGTYPE
    info.size=0 if directory else len(data)
    return info.tobuf(format=tarfile.USTAR_FORMAT)+data+b'\0'*((-len(data))%512)

def tar_stream(same_group=False,malformed=False,bad_checksum=False):
    xml=b'<updater><programs><proc key="trigger.txt">' if malformed else XML
    chunks=[tar_member('0001_program',directory=True),tar_member('0001_program/probe.txt',TEXT),
            tar_member('0100_config',directory=True),tar_member('0100_config/uconfig.xml',xml),
            tar_member(('0100_' if same_group else '0200_')+'trigger.txt',b'inert trigger\n')]
    raw=b''.join(chunks)+b'\0'*1024
    if bad_checksum:raw=bytes([raw[0]^1])+raw[1:]
    return raw

class Guest(ConfigGuest):
    def __init__(self,views,stream):
        trusted=(HERE.parent/'package-20261028/updaterfs/config/config.xml').read_bytes()
        assert hashlib.sha256(trusted).hexdigest()=='09cd171039d921224fe9e66b9e44350f7f5e8bc8e75cea7aefe2235719f544da'
        super().__init__(views,{TRUSTED:trusted})
        package=HERE.parent/'package-20261028'
        source=next(r for r in json.loads((package/'updater-inventory.json').read_text())['entries'] if r['path']=='/bin/startupdate.sh')
        script=(package/source['output']).read_bytes()
        assert len(script)==source['size'] and hashlib.sha256(script).hexdigest()==source['sha256']
        self.files[STARTUP]=script;self.startup_source_sha256=source['sha256']
        assert len(stream)<=0x8000
        self.stream=stream;self.position=0;self.u.mem_write(STREAM,stream)
        self.ring_events=[];self.system_requests=[];self.file_handles={};self.dirs={'/tmp_updater','/tmp_updater/updater'}
        self.fs_events=[];self.controller_events=[]
        families=['UpdaterBody::','BodyInformation::','FlagFirmwareInformationHandler::','MountPoint::','MountEntryHandler::MountEntryHandler','BaseMountEntryHandler::BaseMountEntryHandler',
                  'BaseKeyTag::','NoKeyTag::','CommonKeyTag::','ConfigKeyTag::','KeyTagFactory::','PackedFileHeader::','PackedFirmwareBuffer::',
                  'CreateValueFromOctalString','NewFirmwareFile::','BaseNewFirmwareFile::','BuildInPlugin::']
        for base,view in views:
            for address,n in view.sizes.items():
                if any(t in view.labels.get(address,'') for t in families):self.allowed.append((base+address,base+address+n))
        self.u.mem_write(RING,struct.pack('<Q',RING_VTABLE));self.u.mem_write(RING_VTABLE+0x48,struct.pack('<QQ',PEEK,ADVANCE))
        self.u.mem_write(ENVP,struct.pack('<Q',ENVAR));self.u.mem_write(ENVAR,b'\0'*8)
        body=views[0][1];bindings=[]
        for rel in body.elf.get_section_by_name('.rela.dyn').iter_relocations():
            s=body.symbols[rel['r_info_sym']]
            if s.name=='environ':
                assert rel['r_info_type']==1025
                self.u.mem_write(0x10000000+rel['r_offset'],struct.pack('<Q',ENVP));bindings.append(hex(rel['r_offset']))
        assert bindings==['0x31fe0'];self.environment_fixture=dict(got_offsets=bindings,entries=0)

    def object_string(self,pointer):return self.string(struct.unpack('<Q',self.u.mem_read(pointer+8,8))[0]).decode()

    def code(self,u,pc,size,user):
        x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(8)]
        if pc in [PEEK,ADVANCE]:
            assert x[0]==RING
            self.steps+=1;assert self.steps<=self.budget
            if pc==PEEK:
                assert 0<x[2]<=0x10000
                n=min(x[2],len(self.stream)-self.position)
                u.mem_write(x[1],struct.pack('<Q',STREAM+self.position))
                self.ring_events.append(dict(operation='RAM ring peek',offset=self.position,requested=x[2],returned=n))
                self.ret(n)
            else:
                assert 0<x[1]<=0x10000
                n=min(x[1],len(self.stream)-self.position)
                self.ring_events.append(dict(operation='RAM ring advance',offset=self.position,requested=x[1],returned=n))
                self.position+=n;self.ret(n)
            return
        if pc in self.plt:
            raw=self.plt[pc];name=self.pretty.get(raw,raw)
            if raw.startswith('pthread_mutex_'):
                assert raw in ['pthread_mutex_init','pthread_mutex_lock','pthread_mutex_unlock']
                assert any(lo<=x[0]<hi for lo,hi in [(DATA,DATA+0x10000),(HEAP,HEAP+0x100000),(STACK,STACK+0x10000)])
                self.mutex_events.append(dict(adapter=raw,address=hex(x[0]),single_thread_fixture=True));self.steps+=1;assert self.steps<=self.budget;self.ret(0);return
            if raw=='time':assert x[0]==0;self.events.append(dict(adapter='fixed synthetic time',value=0));self.steps+=1;self.ret(0);return
            if raw=='__errno_location':self.steps+=1;self.ret(ERRNO);return
            if raw=='__xstat':
                assert x[0]==0
                path=self.string(x[1]).decode();assert path in ['/tmp_updater/UFP','/root/IAMUPDATER',USER,STARTUP],('undeclared RAM stat',path)
                exists=path in self.files;self.stat_events.append(dict(adapter='RAM existence-only stat',path=path,exists=exists))
                self.steps+=1;assert self.steps<=self.budget;self.ret(0 if exists else -1);return
            if name.startswith('Updater::DirectoryHandler::Create('):
                path=self.object_string(x[0]);assert path==ROOT or path in [ROOT+'/program',ROOT+'/config']
                assert str(Path(path).parent) in self.dirs;self.dirs.add(path)
                self.fs_events.append(dict(operation='RAM directory create',path=path));self.steps+=1;self.ret(1);return
            if raw=='mkdir':
                path=self.string(x[0]).decode();assert path in [ROOT+'/program',ROOT+'/config'] and x[1]==0o755
                assert str(Path(path).parent) in self.dirs and path not in self.dirs
                self.dirs.add(path);self.fs_events.append(dict(operation='RAM mkdir',path=path,mode=oct(x[1])))
                self.steps+=1;self.ret(0);return
            if name=='Updater::FileHandler::FileHandler()':
                assert x[0] not in self.file_handles;self.file_handles[x[0]]=dict(path=None,data=bytearray(),closed=False)
                self.steps+=1;self.ret();return
            if name=='Updater::FileHandler::Open(char const*, int, unsigned int, int*)':
                path=self.string(x[1]).decode();assert x[0] in self.file_handles
                assert path in [ROOT+'/program/probe.txt',USER,ROOT+'/trigger.txt'] and x[2]==0xc1 and x[3]==0o644
                assert str(Path(path).parent) in self.dirs and path not in self.files
                self.file_handles[x[0]]['path']=path;u.mem_write(x[4],struct.pack('<I',0))
                self.fs_events.append(dict(operation='RAM file open',path=path,flags=hex(x[2]),mode=oct(x[3])))
                self.steps+=1;self.ret(1);return
            if name=='Updater::FileHandler::WriteAll(unsigned char const*, unsigned long, unsigned long*)':
                sink=self.file_handles[x[0]];assert sink['path'] is not None and not sink['closed'] and 0<x[2]<=0x8000
                assert STREAM<=x[1] and x[1]+x[2]<=STREAM+len(self.stream)
                sink['data'].extend(u.mem_read(x[1],x[2]));u.mem_write(x[3],struct.pack('<Q',x[2]))
                self.fs_events.append(dict(operation='RAM file write',path=sink['path'],bytes=x[2]))
                self.steps+=1;self.ret(1);return
            if name=='Updater::FileHandler::Close()':
                sink=self.file_handles[x[0]];assert sink['path'] is not None and not sink['closed'];sink['closed']=True
                self.files[sink['path']]=bytes(sink['data']);self.fs_events.append(dict(operation='RAM file close',path=sink['path'],bytes=len(sink['data']),sha256=hashlib.sha256(sink['data']).hexdigest()))
                self.steps+=1;self.ret(1);return
            if name=='Updater::FileHandler::~FileHandler()':
                sink=self.file_handles.pop(x[0]);assert sink['closed'];self.steps+=1;self.ret();return
            if name=='Updater::XmlConfigHandler::Join(bool)':
                self.steps+=1;self.boundary=dict(operation='before_original_join',pc=hex(pc),no_native_thread_join=True);u.emu_stop();return
            if raw=='system':
                command=self.string(x[0]).decode();self.steps+=1;assert self.steps<=self.budget
                row=dict(command=command,pc=hex(pc),native_execution=False)
                if not self.system_requests:
                    assert command.endswith('/tmp_updater/updater/bodyfs/bin/startupdate.sh')
                    assert 'UPDATER_ACTION_MODE=6;' in command
                    row['role']='startup_result_fixture';row['fixture_wait_status']=0;self.system_requests.append(row);self.ret(0);return
                assert command.endswith('; probe.txt')
                row['role']='input_driven_request_boundary';self.system_requests.append(row)
                self.boundary=dict(operation='system_request_boundary',**row);u.emu_stop();return
        if pc in self.entry_names and any(t in self.entry_names[pc] for t in ['KeyTagFactory::GetKeyTag','ConfigKeyTag::PostExecute','UpdaterBody::Execute','PackedFileHeader::Parse']):
            self.controller_events.append(dict(entry=self.entry_names[pc],pc=hex(pc),stream_position=self.position))
        return super().code(u,pc,size,user)

    def execute(self):
        self.run(self.named('Updater::UpdaterBody::UpdaterBody(bool, Updater::UPDATER_ACTION_MODE, UpdaterAPI::firmware_information_t::information&)'),[UPDATER,1,6,DATA+0x2600])
        u=self.u;u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        for i,value in enumerate([UPDATER,RING,CALLBACK]):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),value)
        u.emu_start(self.named('Updater::UpdaterBody::Execute(Updater::RingBuffer*, Updater::CallbackInterface*)'),STOP+4,count=self.budget)
        assert self.boundary and u.reg_read(R.UC_ARM64_REG_PC)==int(self.boundary['pc'],16)
        assert STACK<=u.reg_read(R.UC_ARM64_REG_SP)<STACK+0x10000
        return dict(boundary=self.boundary,stream_bytes=len(self.stream),stream_sha256=hashlib.sha256(self.stream).hexdigest(),consumed_bytes=self.position,
                    system_requests=self.system_requests,ring_adapter_events=self.ring_events,filesystem_adapters=self.fs_events,stat_adapters=self.stat_events,
                    controller_entries=self.controller_events,original_function_entries=self.entries,host_import_counts=self.imports,mutex_adapters=self.mutex_events,
                    original_empty_string_zero_writes=self.global_writes,environment_fixture=self.environment_fixture,startup_script_sha256=self.startup_source_sha256,startup_errno_fixture=0,total_instructions=self.steps,
                    extracted_files=[dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for path,raw in self.files.items() if path.startswith(ROOT+'/')])

def main():
    views=sources();cases=[('new_group',False,False,False),('same_group',True,False,False),('malformed_xml',False,True,False),('bad_tar_checksum',False,False,True)];rows=[]
    for label,same,malformed,bad in cases:
        g=Guest(views,tar_stream(same,malformed,bad))
        try:row=g.execute()
        except Exception as error:
            p=HERE/'attempts';p.mkdir(exist_ok=True)
            failure=dict(case=label,error=repr(error),pc=hex(g.u.reg_read(R.UC_ARM64_REG_PC)),steps=g.steps,system_requests=g.system_requests,fs_events=g.fs_events,stat_events=g.stat_events,ring_events=g.ring_events,controller_entries=g.controller_events)
            file=p/f'{label}-{len(list(p.glob("*.json"))):02d}.json';file.write_text(json.dumps(failure,indent=2)+'\n');raise
        row['case']=label;rows.append(row)
        if label=='new_group':
            assert row['boundary']['operation']=='system_request_boundary' and len(row['system_requests'])==2
            assert g.files[USER]==XML and g.files[ROOT+'/program/probe.txt']==TEXT
        elif label=='same_group':assert row['boundary']['operation']=='before_original_join' and len(row['system_requests'])==1
        else:assert row['boundary']['operation']=='original_exception_boundary' and row['boundary']['code']=='0x30002' and len(row['system_requests'])==1
    output=dict(body_sha256=PIN,common_sha256=hashlib.sha256(views[1][1].raw).hexdigest(),xml_sha256=hashlib.sha256(views[2][1].raw).hexdigest(),cases=rows,
                scope='Original UpdaterBody constructor and Execute entry, original TAR header/parser/checksum/index switching, key tags/BodyInformation, file type dispatch/extraction, 512-byte rounded PackedFirmwareBuffer skips, config post callback, XML load/parse/match, guardless queue and synchronous plugin command generation execute in one synthetic process per case. A small plaintext TAR exists only in RAM; no UFU/FDAT or encrypted/signed firmware package is emitted. RAM ring and filesystem, empty environment, fixed time, absent UFP/IAMUPDATER stat and sequential mutexes are explicit fixtures. The initial absolute startupdate.sh request receives an explicitly fabricated zero status without executing a script; no real startup readiness is inferred. Later input-driven system request or original exception/Join boundary stops execution. No cryptographic/outer external admission, native target load, shell process, real root state/permissions, device, USB or flash.')
    (HERE/'controller-guest-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),new_group_reaches_request=True,same_group_no_retroactive_trigger=True,malformed_and_checksum_rejected=True,native_system_calls=0,camera_actions=0)))

if __name__=='__main__':main()
