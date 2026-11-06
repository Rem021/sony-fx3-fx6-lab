#!/usr/bin/env python3
"""Original XML library and body config/key methods; FILE I/O is RAM-only."""
import hashlib,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'marker-20261029'))
from keytag_factory_guest import Guest as LoaderGuest,DATA,HEAP,STACK,STOP,R
from inspect_body_policy import PATH,PIN,View

HANDLER=DATA+0x100
PATH_STRING=DATA+0x200
KEY_STRING=DATA+0x300
STRING_BYTES=DATA+0x1000
FILE_HANDLE=DATA+0xf000
ROOT='/tmp_updater/updater/update'
TRUSTED='/tmp_updater/updater/bodyfs/config/config.xml'
USER=ROOT+'/config/uconfig.xml'
USER_XML=b'<updater version="1.0"><programs><proc key="offline_probe"><shell module="probe.txt"/></proc></programs></updater>'

class Guest(LoaderGuest):
    def __init__(self,views,files):
        super().__init__(views)
        self.pretty={name:label for base,view in views for name,label in view.names.items()}
        self.files=files;self.file=None;self.file_offset=0;self.events=[];self.imports={};self.entries={}
        self.global_writes=[]
        empty=next((base+s['st_value'],s['st_size']) for base,view in views if view.path.name=='libul_xml.so' for s in view.symbols if view.names.get(s.name)=='Updater::Xml::TiXmlString::nullrep_')
        self.empty_rep=empty
        assert empty[1]==24 and bytes(self.u.mem_read(empty[0],24))==b'\0'*24
        self.budget=1000000
        self.entry_names={base+s['st_value']:view.names.get(s.name,s.name) for base,view in views for s in view.symbols if s['st_value'] and s['st_size']}
        self.allowed=[]
        for base,view in views:
            if view.path.name=='libul_xml.so':
                text=view.elf.get_section_by_name('.text');self.allowed.append((base+text['sh_addr'],base+text['sh_addr']+text['sh_size']))
            else:
                for address,n in view.sizes.items():
                    if any(s in view.labels.get(address,'') for s in ['StringHandler::','XmlConfigHandler::LoadConfig','XmlConfigHandler::LoadUserConfig','XmlConfigHandler::XmlConfigHandler','XmlConfigHandler::IsKey','XmlConfigHandler::isKey']):
                        self.allowed.append((base+address,base+address+n))

    def named(self,name):return next(a for raw,a in self.definitions.items() if self.pretty.get(raw)==name)

    def write_guard(self,u,access,address,size,value,user):
        low,count=self.empty_rep
        if low<=address and address+size<=low+count:
            assert value==0 and bytes(u.mem_read(low,count))==b'\0'*count
            self.global_writes.append(dict(symbol='Updater::Xml::TiXmlString::nullrep_',address=hex(address),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))))
            return
        return super().write_guard(u,access,address,size,value,user)

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<=self.budget,('instruction budget',self.steps)
        if pc==STOP:u.emu_stop();return
        if pc in self.plt:
            name=self.plt[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(8)]
            if name in self.definitions:u.reg_write(R.UC_ARM64_REG_PC,self.definitions[name]);return
            self.imports[name]=self.imports.get(name,0)+1
            if name in ['_Znwm','_Znam','malloc']:self.ret(self.allocate(x[0]));return
            if name in ['_ZdlPv','_ZdaPv','_ZdlPvm','_ZdaPvm','free']:self.ret();return
            if name=='strlen':self.ret(len(self.string(x[0])));return
            if name in ['memcpy','memmove']:
                assert x[2]<=0x10000;u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0]);return
            if name=='memset':assert x[2]<=0x10000;u.mem_write(x[0],bytes([x[1]&255])*x[2]);self.ret(x[0]);return
            if name in ['memcmp','strcmp','strncmp']:
                if name=='memcmp':
                    assert x[2]<=0x10000;a=bytes(u.mem_read(x[0],x[2]));b=bytes(u.mem_read(x[1],x[2]))
                else:
                    a=self.string(x[0]);b=self.string(x[1])
                    if name=='strncmp':assert x[2]<=0x10000;a=a[:x[2]];b=b[:x[2]]
                self.ret(0 if a==b else -1 if a<b else 1);return
            if name in ['isspace','isalpha','isalnum','tolower']:
                c=x[0]&0xffffffff;assert c<128
                alpha=65<=c<=90 or 97<=c<=122
                result={'isspace':c in [9,10,11,12,13,32],'isalpha':alpha,'isalnum':alpha or 48<=c<=57,'tolower':c+32 if 65<=c<=90 else c}[name]
                self.ret(int(result));return
            if name=='strchr':
                data=self.string(x[0])+b'\0';at=data.find(bytes([x[1]&255]));self.ret(0 if at<0 else x[0]+at);return
            if name=='fopen':
                path=self.string(x[0]).decode();mode=self.string(x[1]).decode();assert mode in ['r','rb'] and self.file is None
                found=path in self.files;self.events.append(dict(adapter='RAM fopen',path=path,mode=mode,found=found))
                if found:self.file=self.files[path];self.file_offset=0
                self.ret(FILE_HANDLE if found else 0);return
            if name=='fseek':
                assert x[0]==FILE_HANDLE and self.file is not None
                delta=x[1] if x[1]<1<<63 else x[1]-(1<<64)
                base={0:0,1:self.file_offset,2:len(self.file)}[x[2]];target=base+delta;assert 0<=target<=len(self.file)
                self.file_offset=target;self.events.append(dict(adapter='RAM fseek',offset=target));self.ret(0);return
            if name=='ftell':assert x[0]==FILE_HANDLE and self.file is not None;self.ret(self.file_offset);return
            if name=='fread':
                assert x[3]==FILE_HANDLE and self.file is not None and 0<x[1]<=0x10000 and x[2]<=0x10000
                count=min(x[2],(len(self.file)-self.file_offset)//x[1]);size=count*x[1];assert size<=0x10000
                u.mem_write(x[0],self.file[self.file_offset:self.file_offset+size]);self.file_offset+=size
                self.events.append(dict(adapter='RAM fread',bytes=size,items=count));self.ret(count);return
            if name=='fclose':assert x[0]==FILE_HANDLE and self.file is not None;self.file=None;self.events.append(dict(adapter='RAM fclose'));self.ret(0);return
            raise AssertionError(('unmodelled import',name,hex(pc)))
        assert any(lo<=pc<hi for lo,hi in self.allowed),('outside selected original XML/config/string text',hex(pc))
        if pc in self.entry_names:
            name=self.entry_names[pc];self.entries[name]=self.entries.get(name,0)+1

    def run(self,entry,args):
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        for i,value in enumerate(args):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),value)
        before=self.steps;u.emu_start(entry,STOP+4,count=self.budget)
        assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        return u.reg_read(R.UC_ARM64_REG_X0),self.steps-before

    def string_object(self,address,text):
        assert len(text)<2048
        self.u.mem_write(STRING_BYTES,text.encode()+b'\0')
        self.run(self.named('Updater::StringHandler::StringHandler()'),[address])
        self.run(self.named('Updater::StringHandler::SetString(char const*)'),[address,STRING_BYTES])

    def load(self,path,user=False):
        self.string_object(PATH_STRING,path)
        method='LoadUserConfig' if user else 'LoadConfig'
        result,steps=self.run(self.named(f'Updater::XmlConfigHandler::{method}(Updater::StringHandler const&)'),[HANDLER,PATH_STRING])
        return dict(method=method,return_value=result,instructions=steps,path=path)

    def key(self,key):
        self.string_object(KEY_STRING,key)
        result,steps=self.run(self.named('Updater::XmlConfigHandler::IsKey(Updater::StringHandler const&)'),[HANDLER,KEY_STRING])
        return dict(key=key,matches=bool(result),return_value=result,instructions=steps)

def sources():
    xml=json.loads((HERE/'xml-source.json').read_text());ap=HERE.parent/'ap-input-20261029'
    common=next(r for r in json.loads((ap/'additional-source-members.json').read_text()) if r['original_path']=='/lib/libupdatercommon.so')
    return [(0x10000000,View(PATH,PIN)),(0x20000000,View(ap/common['output'],common['sha256'])),(0x30000000,View(HERE/xml['output'],xml['sha256']))]

def main():
    views=sources();config=HERE.parent/'package-20261028/updaterfs/config/config.xml';raw=config.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='09cd171039d921224fe9e66b9e44350f7f5e8bc8e75cea7aefe2235719f544da'
    fixtures=[('trusted_only',None,None),('valid_user',USER_XML,1),('malformed_user',b'<updater><programs><proc key="offline_probe">',0),('missing_user_file',None,0)]
    rows=[]
    for label,user_xml,expected in fixtures:
        files={TRUSTED:raw}
        if user_xml is not None:files[USER]=user_xml
        g=Guest(views,files);g.run(g.named('Updater::XmlConfigHandler::XmlConfigHandler(Updater::UPDATER_ACTION_MODE)'),[HANDLER,6])
        loads=[g.load(TRUSTED)];assert loads[0]['return_value']==1
        if expected is not None:
            loads.append(g.load(USER,True));assert loads[-1]['return_value']==expected
        keys=[]
        if expected!=0:
            keys=[g.key(k) for k in ['config_sum/config.sum','offline_probe','absent_key']]
            assert [r['matches'] for r in keys]==[True,label=='valid_user',False]
        assert bytes(g.u.mem_read(g.empty_rep[0],24))==b'\0'*24
        rows.append(dict(case=label,declared_action_mode=6,loads=loads,keys=keys,original_function_entries=g.entries,host_import_counts=g.imports,file_adapter_events=g.events,original_empty_string_zero_writes=g.global_writes,total_instructions=g.steps,user_xml_sha256=hashlib.sha256(user_xml).hexdigest() if user_xml is not None else None))
    result=dict(body_sha256=PIN,common_sha256=views[1][1].pin if hasattr(views[1][1],'pin') else hashlib.sha256(views[1][1].raw).hexdigest(),xml_sha256=hashlib.sha256(views[2][1].raw).hexdigest(),official_config_sha256=hashlib.sha256(raw).hexdigest(),cases=rows,
                scope='Original body XML handler construction/LoadConfig/LoadUserConfig/IsKey/isKey, original libul_xml document construction/loadFile/Parse/DOM traversal/attributes and original StringHandler execute in Unicorn. Source ELF data/relocations are mapped, original code allowlisted, synthetic writes and steps bounded. The sole permitted library-global writes re-store zero within the exact original 24-byte TiXmlString::nullrep_ symbol, logged and checked to remain all zero. Host adapters implement RAM-only FILE reads, allocation, bounded libc bytes/strings and ASCII ctype. User fixture is inert XML and is not saved as a complete container or dispatched to plugins. No host target file/shell/native target library, updater initialization thread, guard/Plugin execution, outer container admission, USB or camera operation.')
    (HERE/'xml-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),valid_user_key_matched=True,malformed_and_missing_load_rejected=True,camera_actions=0)))

if __name__=='__main__':main()
