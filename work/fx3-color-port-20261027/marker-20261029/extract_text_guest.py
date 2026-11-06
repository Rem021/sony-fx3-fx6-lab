#!/usr/bin/env python3
"""Original normal-file extraction to a RAM-only sink; no host target file or shell."""
import hashlib,json,struct,tarfile
from parse_tar_header_guest import Guest as ParserGuest,OBJ,BLOCK
from keytag_factory_guest import DATA,STOP,HERE,View,PATH,PIN,R

ROOT=DATA+0x1000
TARGET=DATA+0x1100
ROOT_BYTES=DATA+0x1200
INFO=DATA+0x7000
BODY=DATA+0x7100
XML=DATA+0x7200
VTABLE=DATA+0x7300
PAYLOAD=DATA+0xc000
PREDICATE=STOP+0x100
PREFIX=b'/tmp_updater/updater/update'
TEXT=b'FX3 offline extraction probe\n'

class Guest(ParserGuest):
    def __init__(self,views,raw,payload,chunk_limit,skip_header=True):
        super().__init__(views,raw)
        assert len(payload)<=0x2000 and 0<chunk_limit<=0x2000
        self.extra_permitted_names += ['BaseKeyTag::Extract','BaseNewFirmwareFile::Extract','NewFirmwareFile::']
        self.u.mem_write(PAYLOAD,payload)
        self.payload=payload;self.chunk_limit=chunk_limit;self.skip_header=skip_header
        self.cursor=0;self.sink=bytearray();self.events=[];self.opened=False;self.closed=False

    def code(self,u,pc,size,user):
        x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(5)]
        if pc==PREDICATE:
            assert x[0]==XML
            getter=self.string(struct.unpack('<Q',u.mem_read(x[1]+8,8))[0])
            self.events.append(dict(adapter='XML IsKey fixture',name=getter.decode(),result=False))
            self.ret(0);return
        if pc in self.plt:
            name=self.pretty.get(self.plt[pc],self.plt[pc])
            if name=='Updater::PackedFirmwareBuffer::SkipCurrentBlock()':
                self.events.append(dict(adapter='SkipCurrentBlock',result=self.skip_header))
                self.ret(int(self.skip_header));return
            if name=='Updater::PackedFirmwareBuffer::ReadDataWithoutCopy(unsigned char**, unsigned long)':
                assert self.opened and 0<x[2]<=len(TEXT)
                n=min(len(self.payload)-self.cursor,x[2],self.chunk_limit)
                assert n>=0
                u.mem_write(x[1],struct.pack('<Q',PAYLOAD+self.cursor))
                self.events.append(dict(adapter='ReadDataWithoutCopy',requested=x[2],available=n,offset=self.cursor))
                self.ret(n);return
            if name=='Updater::PackedFirmwareBuffer::SkipBlock(unsigned long)':
                assert self.opened and 0<x[1]<=len(self.payload)-self.cursor
                self.cursor+=x[1]
                self.events.append(dict(adapter='SkipBlock',bytes=x[1]))
                self.ret(1);return
            if name=='Updater::FileHandler::FileHandler()':
                self.events.append(dict(adapter='FileHandler constructor'));self.ret();return
            if name=='Updater::FileHandler::Open(char const*, int, unsigned int, int*)':
                assert not self.opened
                path=self.string(x[1]).decode()
                assert path==PREFIX.decode()+'/program/probe.txt' and x[2]==0xc1 and x[3]==0o644
                self.opened=True;u.mem_write(x[4],struct.pack('<I',0))
                self.events.append(dict(adapter='RAM sink Open',path=path,flags=hex(x[2]),mode=oct(x[3])))
                self.ret(1);return
            if name=='Updater::FileHandler::WriteAll(unsigned char const*, unsigned long, unsigned long*)':
                assert self.opened and not self.closed and 0<x[2]<=len(TEXT)
                assert x[1]==PAYLOAD+self.cursor
                data=bytes(u.mem_read(x[1],x[2]));self.sink.extend(data)
                u.mem_write(x[3],struct.pack('<Q',len(data)))
                self.events.append(dict(adapter='RAM sink WriteAll',bytes=len(data)))
                self.ret(1);return
            if name=='Updater::FileHandler::Close()':
                assert self.opened and not self.closed
                self.closed=True;self.events.append(dict(adapter='RAM sink Close'));self.ret(1);return
            if name=='Updater::FileHandler::~FileHandler()':
                self.events.append(dict(adapter='RAM sink destructor',explicit_close_preceded=self.closed));self.ret();return
        return super().code(u,pc,size,user)

    def named(self,label):
        return next(address for name,address in self.definitions.items() if self.pretty.get(name)==label)

    def extract(self):
        parsed=self.parse();assert parsed['parse_result']==0
        assert parsed['normalized_name']=='program/probe.txt'
        self.u.mem_write(ROOT_BYTES,PREFIX+b'\0')
        ctor=self.named('Updater::StringHandler::StringHandler()')
        setter=self.named('Updater::StringHandler::SetString(char const*)')
        getter=self.named('Updater::StringHandler::GetCharString() const')
        triple=self.named('Updater::StringHandler::SetString(char const*, char const*, char const*)')
        self.run(ctor,[ROOT]);self.run(setter,[ROOT,ROOT_BYTES]);self.run(ctor,[TARGET])
        root,_=self.run(getter,[ROOT]);name,_=self.run(getter,[OBJ+8])
        # The source controller uses these same root/name strings and a '/' literal
        # at 0x12628..0x12638. Execute its original StringHandler concat, not a host concat.
        self.run(triple,[TARGET,root,0x1001b8c8,name])
        tag,_=self.run(0x1001335c,[parsed['index'],OBJ+8])
        file_type=bytes(self.u.mem_read(OBJ+0x16c,1))[0]
        mode=struct.unpack('<I',self.u.mem_read(OBJ+0x60,4))[0]
        size=struct.unpack('<Q',self.u.mem_read(OBJ+0x80,8))[0]
        assert mode==0o644 and size==len(TEXT) and file_type==ord('0')
        # Confirmed by UpdaterBody::Execute 0x1263c..0x12664 and NewFirmwareFile ctor.
        self.u.mem_write(INFO,struct.pack('<QQQQQ',OBJ+8,TARGET,OBJ+0x28,OBJ+0x50,file_type))
        self.u.mem_write(BODY+0x20,struct.pack('<Q',XML))
        self.u.mem_write(XML,struct.pack('<Q',VTABLE))
        self.u.mem_write(VTABLE+0x28,struct.pack('<Q',PREDICATE))
        result,instructions=self.run(0x10013138,[tag,BODY,DATA+0x6000,INFO])
        return dict(parse=parsed,extract_return=result,extract_instructions=instructions,total_instructions=self.steps,
                    declared_file_bytes=size,declared_file_mode=oct(mode),supplied_payload_bytes=len(self.payload),
                    consumed_bytes=self.cursor,sink_bytes=len(self.sink),sink_sha256=hashlib.sha256(self.sink).hexdigest(),
                    content_equal_expected=bytes(self.sink)==TEXT,explicit_close_observed=self.closed,events=self.events)

def main():
    ap=HERE.parent/'ap-input-20261029'
    common=next(r for r in json.loads((ap/'additional-source-members.json').read_text()) if r['original_path']=='/lib/libupdatercommon.so')
    views=[(0x10000000,View(PATH,PIN)),(0x20000000,View(ap/common['output'],common['sha256']))]
    header=tarfile.TarInfo('0001_program/probe.txt');header.mode=0o644;header.size=len(TEXT)
    raw=header.tobuf(format=tarfile.USTAR_FORMAT)
    fixtures=[('whole_payload',TEXT,4096,True,1),('five_byte_segments',TEXT,5,True,1),
              ('missing_payload',b'',4096,True,0),('header_skip_failure',TEXT,4096,False,0)]
    rows=[]
    for label,payload,limit,skip,expected in fixtures:
        row=Guest(views,raw,payload,limit,skip).extract();row['case']=label
        assert row['extract_return']==expected
        if expected:assert row['content_equal_expected'] and row['explicit_close_observed'] and row['consumed_bytes']==len(TEXT)
        else:assert row['sink_bytes']==0
        if not skip:assert not any(e['adapter']=='RAM sink Open' for e in row['events'])
        rows.append(row)
    output=dict(body_library_sha256=PIN,common_library_sha256=common['sha256'],header_sha256=hashlib.sha256(raw).hexdigest(),
                expected_payload_sha256=hashlib.sha256(TEXT).hexdigest(),cases=rows,
                scope='Original header parsing/normalization/factory/StringHandler concat/BaseKeyTag::Extract/NewFirmwareFile construction/BaseNewFirmwareFile::Extract/type dispatch/normal-file extraction execute in Unicorn synthetic RAM. The declared file is harmless text mode 0644. XML IsKey is an explicit false fixture, not the original XML dispatcher. Input-buffer and FileHandler boundaries are strict memory adapters. No host target path is opened, full TAR or updater container produced, original updater script run, native target library loaded, USB or camera accessed. No controller action mode, outer validation, real loader admission or firmware flashing is established.')
    (HERE/'extract-text-guest-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),successful_content_checks=2,original_false_returns=2,host_target_file_writes=0,camera_actions=0)))

if __name__=='__main__':main()
