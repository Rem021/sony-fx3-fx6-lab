#!/usr/bin/env python3
"""Read-only outcome proof from the sealed single-variable restore run."""
import hashlib,io,json,mmap,plistlib,re,struct,subprocess
from collections import Counter
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/worker-pool-restore-a3af746e3d'
CPIO_SHA='6c698c7d1d4eac7ff54fc2bd6a54a54c3d4c9156f308aefae96b043ef22c5993'
SERIAL_SHA='2f86db9e4692c333aa17aa8e3e070ffa0705740c8aa8e687dac443b9a6a33b99'
CACHE={}

def sha(b):return hashlib.sha256(b).hexdigest()

def fp(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def scan(b):
 rows=[];pos=0;nonzero=re.compile(b'[^\x00]')
 while pos+110<=len(b):
  if b[pos]==0:
   m=nonzero.search(b,pos)
   if not m:break
   pos=m.start()
  assert b[pos:pos+6]==b'070701',pos
  v=[int(b[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
  n=b[pos+110:pos+110+v[11]];assert len(n)==v[11] and n[-1:]==b'\0'
  start=(pos+110+v[11]+3)&~3;end=(start+v[6]+3)&~3;assert end<=len(b)
  rows.append({'name':n[:-1].decode(),'header':pos,'offset':start,'bytes':v[6],'end':end,'fields':v,'sha256':sha(b[start:start+v[6]]),'raw_sha256':sha(b[pos:end])});pos=end
 assert not any(b[pos:]);return rows

def extract(text):
    blocks = re.findall(r'^FX6_WAIT_SNAPSHOT_MAPS_BEGIN tid=(\d+)\s*\n(.*?)^FX6_WAIT_SNAPSHOT_MAPS_END[^\n]*$',
                        text, re.M|re.S)
    if len(blocks) != 1:
        raise ValueError('expected exactly one recorded maps snapshot')
    maps = blocks[0][1]
    addresses, threads = [], {}
    for line in text.splitlines():
        reg = re.match(r'^FX6_WAIT_SNAPSHOT_REG tid=(\d+) (.*)',line)
        if reg:
            tid = int(reg[1]);fields=dict(re.findall(r'(\w+)=(0x[0-9a-f]+)',reg[2]))
            if tid in threads:raise ValueError('duplicate register snapshot')
            threads[tid]={'registers':fields,'frame_records':[]}
            for role in ('pc','lr'):
                addresses.append({'tid':tid,'role':role,'address':fields[role]})
        frame = re.match(r'^FX6_WAIT_SNAPSHOT_FRAME tid=(\d+) index=(\d+) (.*)',line)
        if frame:
            tid,index=int(frame[1]),int(frame[2]);fields=dict(re.findall(r'(\w+)=(0x[0-9a-f]+)',frame[3]))
            if tid not in threads:raise ValueError('frame precedes registers')
            if index != len(threads[tid]['frame_records']):raise ValueError('frame index discontinuity')
            threads[tid]['frame_records'].append(fields)
            addresses.append({'tid':tid,'role':'frame_saved_lr','frame_index':index,'address':fields['saved_lr']})
    for label in ('COMM','SYSCALL'):
        for tid,body in re.findall(r'^FX6_WAIT_SNAPSHOT_'+label+r'_BEGIN tid=(\d+)\s*\n(.*?)^FX6_WAIT_SNAPSHOT_'+label+r'_END[^\n]*$',text,re.M|re.S):
            if int(tid) in threads:threads[int(tid)][label.lower()]=body.strip()
    if not threads:raise ValueError('no successful register snapshots')
    return {'maps':maps,'addresses':addresses,'threads':threads,
            'scope':'Only register PC/LR and recorded FP saved LR; no full-unwind claim'}

def parse_maps(text):
    result = []
    for line in text.splitlines():
        m = re.search(r'(?<![0-9a-f])([0-9a-f]+)-([0-9a-f]+) ([rwxps-]{4}) ([0-9a-f]+) [0-9a-f:]+ \d+\s*(.*)', line)
        if m:
            a, b, perms, offset, path = m.groups()
            result.append(dict(start=int(a,16), end=int(b,16), perms=perms,
                               offset=int(offset,16), path=path))
    return result

def resolve(archive, maps, address):
    address = int(address, 0) if isinstance(address, str) else address
    out = {'address':hex(address)}
    matches = [m for m in maps if m['start'] <= address < m['end']]
    if len(matches) != 1:
        return dict(out, status='no_unique_mapping')
    mapping = matches[0]
    out['mapping'] = {k:hex(v) if isinstance(v,int) else v for k,v in mapping.items()}
    if not mapping['path'].startswith('/') or ' (deleted)' in mapping['path']:
        return dict(out, status='not_file_backed')
    try:
        data = member(archive, mapping['path'])
    except ValueError as exc:
        return dict(out, status='member_unresolved', error=str(exc))
    out['elf_sha256'] = hashlib.sha256(data).hexdigest()
    out['elf_bytes'] = len(data)
    elf = ELFFile(io.BytesIO(data))
    if elf['e_machine'] != 'EM_AARCH64' or elf.elfclass != 64:
        return dict(out, status='not_aarch64_elf')
    # Linux mapping offsets are page aligned; confirm load bias by every
    # segment compatible with the selected file mapping.
    biases = set()
    for s in elf.iter_segments():
        if s['p_type'] != 'PT_LOAD':
            continue
        if ('x' in mapping['perms']) != bool(s['p_flags'] & 1):
            continue
        # This harness temporarily makes patched code pages writable; W in
        # /proc/maps therefore need not equal the original ELF PF_W flag.
        off = s['p_offset'] & ~4095
        va = s['p_vaddr'] & ~4095
        extent = ((s['p_offset']+s['p_filesz']+4095) & ~4095)-off
        if off <= mapping['offset'] < off+extent:
            biases.add(mapping['start']-(va+mapping['offset']-off))
    if len(biases) != 1:
        return dict(out, status='ambiguous_PT_LOAD_bias' if biases else 'no_PT_LOAD_bias',
                    biases=[hex(x) for x in sorted(biases)])
    bias = biases.pop()
    va = address-bias
    segments = [s for s in elf.iter_segments() if s['p_type']=='PT_LOAD'
                and s['p_vaddr'] <= va < s['p_vaddr']+s['p_filesz']]
    if len(segments) != 1:
        return dict(out, status='not_unique_file_backed_PT_LOAD', elf_va=hex(va))
    s = segments[0]
    file_offset = s['p_offset']+va-s['p_vaddr']
    out.update(status='resolved', load_bias=hex(bias), elf_va=hex(va), file_offset=hex(file_offset),
               executable=bool(s['p_flags'] & 1))
    symbols = []
    for table in (elf.get_section_by_name('.dynsym'), elf.get_section_by_name('.symtab')):
        if table:
            for sym in table.iter_symbols():
                if sym['st_info']['type'] == 'STT_FUNC' and sym['st_size'] > 0 and sym['st_value'] <= va < sym['st_value']+sym['st_size']:
                    symbols.append({'name':sym.name,'start':hex(sym['st_value']),
                                    'bytes':sym['st_size'],'offset':hex(va-sym['st_value'])})
    out['covering_function_symbols'] = list({json.dumps(x,sort_keys=True):x for x in symbols}.values())
    if s['p_flags'] & 1:
        start = max(s['p_vaddr'], (va-16)&~3)
        end = min(s['p_vaddr']+s['p_filesz'], va+16)
        begin = s['p_offset']+start-s['p_vaddr']
        cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        out['instructions'] = [{'va':hex(i.address),'assembly':i.mnemonic+' '+i.op_str}
                               for i in cs.disasm(data[begin:begin+end-start], start)]
        out['preceding_instruction'] = next((i for i in out['instructions'] if int(i['va'],16)==va-4), None)
    return out

def member(archive,wanted):
 name=wanted.lstrip('./')
 if name not in CACHE:
  with Path(archive).open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
   rows=scan(raw);matches=[r for r in rows if r['name'].lstrip('./')==name]
   assert len(matches)==1,(name,len(matches));r=matches[0];CACHE[name]=raw[r['offset']:r['offset']+r['bytes']]
 return CACHE[name]
class Image:
 def __init__(self,b):self.b=b;self.e=ELFFile(io.BytesIO(b));self.cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 def offset(self,va,n=1):
  ss=[s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']];assert len(ss)==1;z=ss[0];return z['p_offset']+va-z['p_vaddr']
 def read(self,va,n):o=self.offset(va,n);return self.b[o:o+n]
 def u64(self,va):return struct.unpack('<Q',self.read(va,8))[0]
 def cstring(self,va):o=self.offset(va);return self.b[o:self.b.index(b'\0',o)].decode()
 def insn(self,va):
  i=next(self.cs.disasm(self.read(va,4),va));return {'va':hex(va),'file_offset':hex(self.offset(va,4)),'word':hex(struct.unpack('<I',self.read(va,4))[0]),'assembly':i.mnemonic+' '+i.op_str}
 def branch(self,pc):
  w=struct.unpack('<I',self.read(pc,4))[0];assert w&0x7c000000==0x14000000;v=w&0x3ffffff
  if v&0x2000000:v-=0x4000000
  return pc+v*4

def main():
 vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert vol.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 manifest=json.loads((HERE/'candidate-manifest.json').read_text());archive=Path(manifest['initrd']['path']);assert fp(archive)['sha256']==CPIO_SHA
 raw=(RUN/'serial.log').read_bytes();assert sha(raw)==SERIAL_SHA
 text=raw.decode('utf-8','replace').replace('\r\n','\n');snap=extract(text);maps=parse_maps(snap['maps']);selected=[a for a in snap['addresses'] if a['tid'] in [224,227,231]]
 resolved=[dict(item,resolution=resolve(archive,maps,item['address'])) for item in selected];assert all(a['resolution']['status']=='resolved' for a in resolved)
 bytid={str(tid):{'comm':snap['threads'][tid]['comm'],'syscall':snap['threads'][tid].get('syscall'),'registers':snap['threads'][tid]['registers'],'addresses':[r for r in resolved if r['tid']==tid]} for tid in [224,227,231]}
 def va_set(tid):return {r['resolution']['elf_va'] for r in bytid[str(tid)]['addresses'] if r['resolution']['mapping']['path']=='/usr/lib/appFw.so'}
 assert {'0x20ef7cc','0x20f160c','0x20d00e8','0x1cd8100','0x1cd86a8','0x1e2528c'}<=va_set(231)
 assert {'0x1acd988','0x12d9dec','0xc09de8'}<=va_set(224) and '0x20c4560' in va_set(227)
 a=Image(member(archive,'usr/lib/appFw.so'));assert sha(a.b)=='a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'
 identities={hex(v):a.cstring(v) for v in [0x25ac4f0,0x25ac49d,0x2600678,0x2602418,0x25ffa11]}
 assert identities['0x25ac4f0']=='void model::sequence_cold_boot::init_hdmi()' and identities['0x2600678']=='adf_set_hdmi_format'
 vtable=a.u64(0x2ee45a8);rtti=a.u64(vtable+8);rtti_name=a.cstring(a.u64(rtti+8));assert rtti_name=='N5model18sequence_cold_bootE' and a.u64(vtable+0x20)==0x1cd826c
 edges=[]
 for pc,target in [(0x1cd86a4,0x1cd80dc),(0x1cd80fc,0x20d00bc),(0x20d00e4,0x20f158c),(0x20f1608,0x20ef604),(0x20ef790,0xb17c70),(0x20ef79c,0xb1a120),(0x20ef7c8,0xb19ec0),(0x1cd86ac,0x1accea8),(0x20ef7dc,0xb17880),(0x20ef7e8,0xb19d40),(0x20c455c,0xb19e30)]:
  assert a.branch(pc)==target;edges.append({**a.insn(pc),'target':hex(target)})
 expected_packet=struct.pack('<5H',0x200d,0x032d,10,0x8001,0).hex()
 lines=text.splitlines();events=[];unhandled=[]
 for number,line in enumerate(lines,1):
  if line.startswith('FX6_QUEUE_OBS_ENTER ') or line.startswith('FX6_QUEUE_OBS_EXIT '):events.append({'line':number,'text':line})
  if 'FX3_BACKUP_CP_UNHANDLED' in line and 'destination=0x92840747' in line:unhandled.append({'line':number,'text':line})
 enter=[r for r in events if 'OBS_ENTER ' in r['text']];leave=[r for r in events if 'OBS_EXIT ' in r['text']];assert len(enter)==9 and len(leave)==8
 assert all(f' seq={n} ' in leave[n-1]['text'] and ' rc=0 ' in leave[n-1]['text'] for n in range(1,9))
 ninth=enter[-1];assert all(t in ninth['text'] for t in ['seq=9 ','tid=231 ','site=bb_request_reply ','qid=0x81cf610f ','timeout=-1 '])
 assert not any(' seq=9 ' in r['text'] for r in leave)
 assert any('raw='+expected_packet in r['text'] for r in unhandled) and any('source=0x81cf610f no_reply=1' in r['text'] for r in unhandled)
 detach=re.findall(r'^FX6_WAIT_SNAPSHOT_DETACH tid=(\d+) rc=0 ',text,re.M);assert len(detach)==len(set(detach))==129
 endline=next(line for line in lines if line.startswith('FX6_WAIT_SNAPSHOT_END '));assert all(t in endline for t in ['processed=129 ','enumerated=129 ','failures=0 ','detach_failed=0 ','elapsed_ms=975'])
 initend=next(line for line in lines if line.startswith('FX6_WAIT_SNAPSHOT_INIT_END '));assert initend.endswith('rc=0')
 counts=Counter(t.get('comm','') for t in snap['threads'].values());seqqueue=sum(n for name,n in counts.items() if name.startswith('SeqQueue'));threadpool=sum(n for name,n in counts.items() if name.startswith('SeqThreadPool'));assert seqqueue==45 and threadpool==4
 receipt=json.loads((RUN/'run-receipt.json').read_text());assert receipt['process_reaped'] is True and receipt['locks_released'] is True and receipt['files']['serial.log']['sha256']==SERIAL_SHA
 assert receipt['manifest_sha256']==fp(HERE/'candidate-manifest.json')['sha256']
 selected_insns=[a.insn(v) for v in [0x1cd86a0,0x1cd86a8,0x1e25280,0x1e25288,0x1cd80f4,0x20f15a0,0x20f15ac,0x20f15b0,0x20f15b4,0x20f15b8,0x20f15bc,0x20f15c0,0x20f15c4,0x20f15f4,0x20f15f8,0x20f15fc,0x20f1600,0x20ef788,0x20ef7bc,0x20ef7c0,0x20ef7c4,0x20ef7d0,0x20ef7d4,0x20ef7d8,0x20c4544,0x20c454c,0x20c4560]]
 proof={'schema':'fx6-worker-pool-restore-outcome-v1','manifest':fp(HERE/'candidate-manifest.json'),'archive':fp(archive),'run_receipt':fp(RUN/'run-receipt.json'),'serial':fp(RUN/'serial.log'),'run_end':{k:receipt[k] for k in ['reason','error','elapsed_seconds','process_reaped','locks_released']},'snapshot':{'observed_register_tids':len(snap['threads']),'successful_unique_detach_tids':len(set(detach)),'seq_queue_threads':seqqueue,'seq_thread_pool_threads':threadpool,'end_log':endline,'init_end_log':initend},'selected_addresses_resolved':len(resolved),'threads':bytid,'original_identities':identities,'coldboot_job':{'vtable':hex(vtable),'rtti':rtti_name,'execute':'0x1cd826c','actual_saved_lr_within_execute':'0x1cd86a8','native_worker_virtual_execute_call':'0x1e25288','current_blocking_call':'0x1cd86a4 ->0x1cd80dc init_hdmi','future_fulfill_after_that_call':'0x1cd86ac ->0x1accea8','native_execute_observed':True,'future_current_invocation_completed':False},'call_edges':edges,'selected_instruction_contracts':selected_insns,'receive_events':events,'bb_request':{'logical_destination':'0x92840747','reply_queue_from_message_source':'0x81cf610f','request_bytes':10,'reply_copy_bytes':12,'request_halfwords_hex':['0x200d','0x032d','0x000a','0x8001','0x0000'],'expected_raw_hex':expected_packet,'actual_unhandled_logs':unhandled,'current_receive':ninth,'current_receive_has_exit':False,'caller_name':'adf_set_hdmi_format','default_send_receive_contract':'allocate request to destination, copy10B, set message source to temporary reply queue, send, receive timeout-1 on same queue, then copy12B reply and free','interpretation':'Actual CP bridge reports unhandled/no_reply; no protocol-correct12B reply is proven. Reply format and hardware implementation are not inferred from this10B request.'},'conclusions':{'confirmed':'Restoring only the native pool call caused real sequence_cold_boot execute to run; current block is its init_hdmi request/reply path before promise fulfillment','appfw_thread':'TID224 still waits on the same cold-boot future because TID231 has not returned from init_hdmi to its fulfill call','pool0_thread':'TID227 SeqThreadPool0 is waiting on its own work-available condition at20c455c; it is not this cold-boot executing thread','limits':['no claim that CP route destination absence is a physical-camera fault','no fabricated reply or ready/notify writes','no UI/menu success claim','FP records are observed frames, not a complete unwind','runtime instruction-byte readback at12d825c still absent; behavioral counterfactual is actual native execution']},'analysis_guest_connection':False}
 (HERE/'restore-outcome.json').write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'proof':fp(HERE/'restore-outcome.json'),'selected_addresses_resolved':len(resolved),'coldboot_execute_observed':True,'blocking_call':'cold_boot::init_hdmi ->adf_set_hdmi_format ->bb send_and_wait_cmp_i','unanswered_reply_queue':'0x81cf610f','packet':expected_packet,'seq_queue_threads':seqqueue,'helper_detaches':len(set(detach))},indent=2))
if __name__=='__main__':main()
