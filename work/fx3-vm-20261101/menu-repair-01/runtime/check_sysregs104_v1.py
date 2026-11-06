from pathlib import Path
import tempfile,re
from gdb_sysregs104_v1 import Sysregs
docs={'target.xml':'<target xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include href="core.xml"/><xi:include href="system-registers.xml"/></target>','core.xml':'<feature><reg name="x0" bitsize="64" regnum="0"/><reg name="pc" bitsize="64" regnum="32"/></feature>','system-registers.xml':'<feature><reg name="SP_EL0" bitsize="64" regnum="97"/><reg name="TPIDR_EL0" bitsize="64"/></feature>'}
class Gate:
 def __init__(self):self.commands=[]
 def packet(self,p):
  self.commands.append(p)
  if p.startswith('qXfer:'):
   m=re.fullmatch(r'qXfer:features:read:([^:]+):([0-9a-f]+),1000',p);assert m;off=int(m[2],16);s=docs[m[1]];chunk=s[off:off+31];return('l'if off+len(chunk)==len(s)else'm')+chunk
  assert p in ['p61','p62'];return (0xffffffc012340000 if p=='p61'else 0x7f12340000).to_bytes(8,'little').hex()
with tempfile.TemporaryDirectory(prefix='fx3-sysregs104-')as td:
 g=Gate();s=Sysregs(g,td);assert s.read('SP_EL0')==0xffffffc012340000 and s.read('TPIDR_EL0')==0x7f12340000;assert not any(x.startswith(('H','G','P'))or x in ['?','qC']for x in g.commands)
print('AP104_ACTUAL_XML_NUMBERING_CHUNKS_READ_ONLY_PN_NO_CPU_SELECTION_PASS')
