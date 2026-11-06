#!/usr/bin/env python3
"""Original trusted ShellPlugin command construction, stopping before system()."""
from pathlib import Path
import hashlib,json,struct,sys,xml.etree.ElementTree as ET
from unicorn import UC_HOOK_CODE
from inspect_body_policy import HERE,PATH,PIN,View
sys.path.insert(0,str(HERE.parent/'package-20261028'))
from original_block_checker_guest import Guest as BaseGuest,DATA,STACK,STOP,R

class Guest(BaseGuest):
    def __init__(self,view,attrs):
        self.view=view;self.attrs=attrs;self.strings={};self.next_string=DATA+0x8000;self.boundary=None
        super().__init__(view.raw);self.u.mem_map(DATA+0x4000,0x3c000)
        self.u.mem_write(DATA+0x1000,b'config_sum/config.sum\0')

    def write(self,u,access,a,size,value,unused):assert DATA<=a and a+size<=DATA+0x40000 or STACK<=a and a+size<=STACK+0x10000,('outside synthetic RAM',hex(a),size)
    def text(self,a):
        assert a
        data=bytearray()
        for i in range(4096):
            b=bytes(self.u.mem_read(a+i,1))
            if b==b'\0':return data.decode()
            data+=b
        raise AssertionError('unbounded guest string')
    def allocate_string(self,value):
        raw=value.encode()+b'\0';assert len(raw)<2048 and self.next_string+len(raw)<DATA+0x40000
        address=self.next_string;self.next_string+=2048;self.u.mem_write(address,raw);return address
    def code(self,u,pc,size,user):
        self.instructions+=1;assert self.instructions<2000
        if pc==STOP:u.emu_stop();return
        if pc in self.plt:
            raw=self.plt[pc];name=self.view.names.get(raw,raw);x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(6)]
            if name.startswith('Updater::Xml::DomElement::queryStringAttribute'):
                key=self.text(x[1]);value=self.attrs.get(key)
                if value is None:self.ret(1)
                else:u.mem_write(x[2],struct.pack('<Q',self.allocate_string(value)));self.ret(0)
                return
            if name.startswith('Updater::StringHandler::StringHandler'):self.strings[x[0]]='';self.ret(0);return
            if name.startswith('Updater::StringHandler::SetString'):
                count=5 if name.count('char const*')==5 else 3
                assert name.count('char const*')==count
                self.strings[x[0]]=''.join(self.text(a) for a in x[1:count+1]);self.ret(0);return
            if name.startswith('Updater::StringHandler::GetCharString'):self.ret(self.allocate_string(self.strings[x[0]]));return
            if raw=='strcmp':
                a=self.text(x[0]);b=self.text(x[1]);self.ret(0 if a==b else 0xffffffffffffffff if a<b else 1);return
            if raw=='system':
                self.boundary=dict(operation='system_request_boundary',command=self.text(x[0]),native_execution=False);u.emu_stop();return
            if raw=='printf':self.ret(0);return
            if raw=='__cxa_allocate_exception':assert x[0]==16;self.ret(DATA+0x3000);return
            if raw=='__cxa_throw':
                self.boundary=dict(operation='original_exception_boundary',code=hex(struct.unpack('<I',u.mem_read(x[0]+8,4))[0]),native_unwinding=False);u.emu_stop();return
            raise AssertionError(('unmodelled boundary',name,hex(pc)))
        assert 0x187a4<=pc<0x18b04,('outside selected original ShellPlugin',hex(pc))

    def run(self,mode):
        u=self.u;u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X0,mode);u.reg_write(R.UC_ARM64_REG_X1,DATA+0x1000);u.reg_write(R.UC_ARM64_REG_X2,DATA+0x2000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        u.emu_start(0x187a4,STOP+4,count=2000);assert self.boundary
        return dict(mode=mode,declared_attributes=self.attrs,boundary=self.boundary,instructions=self.instructions)

def main():
    view=View(PATH,PIN);package=HERE.parent/'package-20261028';inventory=json.loads((package/'updater-inventory.json').read_text())
    item=next(r for r in inventory['entries'] if r['path']=='/config/config.xml');config=package/item['output'];assert hashlib.sha256(config.read_bytes()).hexdigest()==item['sha256']
    tree=ET.fromstring(config.read_text());rows=[]
    for key in ['config_sum/config.sum','part_image_sum/part_image.sum']:
        shell=next(p for p in tree.find('programs') if p.attrib['key']==key).find('shell')
        for mode in [3,6]:
            row=Guest(view,dict(shell.attrib)).run(mode);row['trusted_config_key']=key
            assert row['boundary']['operation']=='system_request_boundary'
            command=row['boundary']['command'];assert 'export UPDATER_ACTION_MODE='+str(mode) in command
            assert 'export PATH=/tmp_updater/updater/update/program:/tmp_updater/updater/bodyfs/bin:/usr/bin:$PATH' in command
            assert command.endswith(shell.attrib['module']+' '+shell.attrib['param'])
            rows.append(row)
    bad=Guest(view,{}).run(6);assert bad['boundary']['operation']=='original_exception_boundary';rows.append(dict(case='missing_module_attribute',**bad))
    result=dict(source_library_sha256=PIN,official_config_sha256=item['sha256'],cases=rows,
                scope='Original ShellPlugin::Execute constructs requests for attributes taken from the pinned official config. Host adapters supply XML attribute lookup and StringHandler concatenation; the original XML loader, unpacker, tag callbacks, native shell and PATH resolution are not executed. Every case stops before system or exception unwinding. A PATH prefix or mode-6 request is a candidate mechanism, not whole-container reachability, unsigned code execution, firmware admission or a flash receipt.')
    (HERE/'shell-request-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),mode6_system_requests=sum(r['mode']==6 and r['boundary']['operation']=='system_request_boundary' for r in rows),native_shell_calls=0,camera_actions=0)))

if __name__=='__main__':main()
