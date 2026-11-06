"""Discover read-only AArch64 system register numbers from actual QEMU XML.
Never selects another CPU: pN reads the CPU chosen by the native debug stop.
"""
from pathlib import Path
import re,json,xml.etree.ElementTree as ET
class Sysregs:
    def __init__(self,gate,run):
        self.gate=gate;self.run=Path(run);self.regs={};self.docs={};self.next=0
        self.walk(self.fetch('target.xml'))
        for name in ['SP_EL0','TPIDR_EL0']:
            if name not in self.regs or self.regs[name]['bitsize']!=64:raise RuntimeError('Required QEMU read-only system register unavailable: '+name)
        (self.run/'gdb104-register-map.json').write_text(json.dumps(self.regs,indent=2)+'\n')
    def fetch(self,name):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise RuntimeError('Unexpected GDB feature name')
        if name in self.docs:return self.docs[name]
        out='';offset=0
        while True:
            r=self.gate.packet(f'qXfer:features:read:{name}:{offset:x},1000')
            if not r or r[0]not in 'ml':raise RuntimeError('GDB target XML unavailable: '+name)
            out+=r[1:];offset+=len(r[1:])
            if len(out)>1048576:raise RuntimeError('Oversize GDB feature')
            if r[0]=='l':break
            if len(r)==1:raise RuntimeError('Empty nonfinal GDB XML chunk')
        (self.run/('gdb104-'+name)).write_text(out)
        # QEMU's generated target.xml uses xi:include without declaring xi.
        # GDB accepts that dialect; normalize only the parser copy, retain raw.
        parsed=out
        if 'xi:'in parsed and 'xmlns:xi='not in parsed:
            parsed=re.sub(r'<target(?=[\s>])','<target xmlns:xi="http://www.w3.org/2001/XInclude"',parsed,count=1)
        root=ET.fromstring(parsed);self.docs[name]=root;return root
    def walk(self,node):
        tag=node.tag.split('}')[-1]
        if tag=='include':self.walk(self.fetch(node.attrib['href']));return
        if tag=='reg':
            number=int(node.attrib.get('regnum',str(self.next)),0);self.next=number+1
            self.regs[node.attrib['name'].upper()]={'number':number,'bitsize':int(node.attrib['bitsize'])}
        for child in node:self.walk(child)
    def read(self,name):
        d=self.regs[name.upper()];r=self.gate.packet('p'+format(d['number'],'x'))
        if not re.fullmatch(r'[0-9a-fA-F]{'+str(d['bitsize']//4)+'}',r):raise RuntimeError('Short read-only GDB register: '+name)
        return int.from_bytes(bytes.fromhex(r),'little')
