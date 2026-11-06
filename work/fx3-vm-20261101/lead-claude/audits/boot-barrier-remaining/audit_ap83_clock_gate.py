#!/usr/bin/env python3
"""Offline AP83 CPU/clock and post-clear wait audit; adjacent proof only.

No QEMU executable, guest command, runtime mutation, lock, or device access.
FDT/CPIO and the two counter banks are decoded directly from saved inputs.
"""
import sys
sys.dont_write_bytecode = True
import hashlib
import io
import json
import plistlib
import re
import struct
import subprocess
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

from audit_boot_barrier import ROOT, OUT, APDIR, DATA, PINNED, dis, identity

RT = ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
Q = RT/'qemu-display-build/sources/qemu-11.1.2'
ORIGINAL_DTB = ROOT/'work/sony-firmware-20261024/stage205-FX3-hardware-profile-differences/originals/7.02-setting-cxd90057.dtb'
RUNS = ['ap83ar4face-4cd8574a', 'ap83bgpe14-f83e3fc5', 'ap84amttcg-953a9d56']
PINNED_INPUTS = {
    ORIGINAL_DTB: 'c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280',
    RT/'helpers/fx3-ui-gate-v11.c': 'bb6650761764f2990650243b9e81ef7f4434c165faef8701afa1033cb961261c',
    RT/'helpers/fx3-ui-gate-v11.so': '54eeed923a6412cd2c6743f6e8c968d1ede71b92aa79aca4575868ebccc4a9ec',
    Q/'accel/tcg/tcg-all.c': '7ad8dcc2528e459abaf98787670d3674c570c689de6d9936fdaf761abcd43627',
    Q/'hw/timer/sony_hwtimer.c': '050193cca7d211539430440f076d7edf15c70bb1275003369057e8d93b97c30b',
}
RAM_HASHES = {
    RUNS[0]: 'b815b836b01c094cfc4fa23b357a1f6cba1356cd30c45b066cf9dbadc53f26ae',
    RUNS[1]: 'cc7f8eb540183061c74d33c1452be7ce7989a40e348fcb1d0839fc224307653f',
    RUNS[2]: 'f3e0019198537876a6fb592bba85252f60df372b713ba36005ee151857eca35b',
}
FIELDS = ('peak_all peak_gate field_samples hist_0 hist_1 hist_2 hist_3 hist_4 hist_5 '
          'gate_hist_0 gate_hist_1 gate_hist_2 gate_hist_3 gate_hist_4 gate_hist_5 '
          'system_false backlog_skip time_skip time_pass dequeue_total timer_dequeue '
          'a12_nonzero a13_nonzero last_object last_a18 last_a12 last_a13 '
          'first_ns last_ns mirror_skip selftest bound').split()


def fdt(path):
    b = path.read_bytes()
    h = struct.unpack_from('>10I', b)
    assert h[0] == 0xd00dfeed and h[1] == len(b)
    strings = b[h[3]:h[3]+h[8]]
    i, stack, nodes, offsets = h[2], [], {}, {}
    while True:
        at = i
        token = struct.unpack_from('>I', b, i)[0]
        i += 4
        if token == 1:
            end = b.index(0, i)
            stack.append(b[i:end].decode())
            i = (end+4)&~3
        elif token == 2:
            stack.pop()
        elif token == 3:
            n, no = struct.unpack_from('>II', b, i)
            i += 8
            key = strings[no:strings.index(0, no)].decode()
            path_name = '/'.join(stack) or '/'
            nodes.setdefault(path_name, {})[key] = b[i:i+n]
            offsets[(path_name, key)] = {'token_offset':hex(at), 'data_offset':hex(i), 'length':n}
            i = (i+n+3)&~3
        elif token == 9:
            break
        else:
            assert token == 4
    return nodes, offsets


def cpu_summary(path):
    nodes, offsets = fdt(path)
    cpus = []
    for name, p in nodes.items():
        if p.get('device_type') != b'cpu\0':
            continue
        cpus.append({'node':name, 'reg':int.from_bytes(p['reg'], 'big'),
            'properties_hex':{k:v.hex() for k,v in p.items()},
            'property_offsets':{k:offsets[(name,k)] for k in p}})
    return {**identity(path), 'cpus':cpus,
        'psci':{k:v.hex() for k,v in nodes.get('/psci',{}).items()},
        'bootargs':nodes.get('/chosen',{}).get('bootargs',b'').rstrip(b'\0').decode()}


def cpio_members(path):
    b = path.read_bytes()
    off = 0
    while off+110 <= len(b):
        assert b[off:off+6] == b'070701'
        fields = [int(b[off+6+8*i:off+14+8*i],16) for i in range(13)]
        name = b[off+110:off+110+fields[11]-1].decode()
        a = (off+110+fields[11]+3)&~3
        raw = b[a:a+fields[6]]
        assert len(raw) == fields[6]
        off = (a+fields[6]+3)&~3
        yield name.lstrip('./'), raw
        if name == 'TRAILER!!!':
            return
    raise AssertionError('CPIO trailer missing')


def hits(lines, needle):
    return [{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')}
        for i,s in enumerate(lines) if needle in s]


def snapshots(lines, expected_affinity):
    result = []
    for i,s in enumerate(lines):
        marker=re.fullmatch(rb'FX3_TASK_SNAPSHOT_([0-9]+)_BEGIN\r?',s)
        if not marker:
            continue
        tid=marker[1]
        names=[x for x in lines[i+1:i+9] if x.startswith(b'Name:')]
        if not names or names[0].rstrip(b'\r')!=b'Name:\tAppFw':
            continue
        end = next(j for j in range(i+1,len(lines))
            if lines[j].rstrip(b'\r') == b'FX3_TASK_SNAPSHOT_'+tid+b'_END')
        body = lines[i:end+1]
        assert not any(re.fullmatch(rb'FX3_TASK_SNAPSHOT_[0-9]+_BEGIN\r?',x) for x in body[1:])
        syscall = [(i+k+1,x.decode().strip()) for k,x in enumerate(body)
            if re.match(rb'^(29|98) 0x', x)]
        assert len(syscall) == 1
        fields = syscall[0][1].split()
        result.append({'TID':int(tid),'begin_line':i+1,'end_line':end+1,
            'syscall_line':syscall[0][0], 'syscall_text':syscall[0][1],
            'syscall_number':int(fields[0]), 'args':[int(x,16) for x in fields[1:7]],
            'sp':fields[7], 'pc':fields[8],
            'Cpus_allowed_list':next(x.decode().split(':',1)[1].strip() for x in body if x.startswith(b'Cpus_allowed_list:')),
            'kernel_stack':[x.decode().strip() for x in body if x.startswith(b'[<')]})
    assert len(result) == 3
    assert all(x['Cpus_allowed_list']==expected_affinity for x in result)
    assert result[0]['syscall_number']==98
    assert result[1]['syscall_number']==result[2]['syscall_number']==29
    assert result[1]['syscall_text']==result[2]['syscall_text']
    assert result[1]['args'][1]&0xffffffff == 0x80000001
    assert all(any('osal_wai_sem_tmo' in s for s in x['kernel_stack']) for x in result[1:])
    return result


def read_run(name):
    cpu_count=4 if name.startswith('ap84') else 1
    folder = RT/'runs'/name
    receipt_path = folder/'receipt.json'
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt['duration_seconds']>=300 and receipt['qemu_exit']==0
    assert receipt['process_reaped'] and receipt['inputs_unchanged']
    assert not receipt['guest_exception_markers'] and not receipt['menu_verified']
    command_path = folder/'command.json'
    command = json.loads(command_path.read_bytes())
    assert command['args'][command['args'].index('-smp')+1]==str(cpu_count)
    assert command['args'][command['args'].index('-accel')+1]==('tcg,thread=multi' if cpu_count==4 else 'tcg')
    assert '-icount' not in command['args'] and command['icount_profile'] is None
    candidate_path = Path(command['candidate'])
    assert identity(candidate_path)['sha256'] == command['candidate_sha256']
    candidate = json.loads(candidate_path.read_bytes())
    for key in ['initrd','dtb']:
        assert identity(Path(candidate[key]['path']))['sha256'] == candidate[key]['sha256']
    cpus = cpu_summary(Path(candidate['dtb']['path']))
    assert [x['reg'] for x in cpus['cpus']]==list(range(cpu_count))
    if cpu_count==4:
        assert all(x['properties_hex']['enable-method']==b'psci\0'.hex() for x in cpus['cpus'])
    members = dict(cpio_members(Path(candidate['initrd']['path'])))
    init = members['init']
    selected = [{'line':i+1,'text':s} for i,s in enumerate(init.decode().splitlines())
        if any(x in s for x in ['cpuset','/proc/uptime','FX3_AP_SNAPSHOT','group in'])]
    assert any('echo 0 > /dev/cgroup/$group/cpuset.cpus' in x['text'] for x in selected)
    gate = members['simulation/fx3-ui-gate-v1.so']
    assert hashlib.sha256(gate).hexdigest() == PINNED_INPUTS[RT/'helpers/fx3-ui-gate-v11.so']
    ram_path = folder/'ui-gate-counters.bin'
    ram = ram_path.read_bytes()
    assert hashlib.sha256(ram).hexdigest()==RAM_HASHES[name]
    saved = next(x for x in receipt['read_only_guest_memory_snapshots'] if x['name']==ram_path.name)
    assert saved['sha256']==RAM_HASHES[name] and len(ram)==65536
    h = struct.unpack_from('<16Q',ram)
    assert h[0]==0x3145544147335846 and h[1]==2 and h[2] in [0,1]
    v = struct.unpack_from('<96Q',ram,0x100+h[2]*0x1000)
    counts = list(v[:64]);stats = dict(zip(FIELDS,v[64:]))
    assert counts[8]==stats['time_pass']==2
    assert stats['dequeue_total']==counts[11]==counts[5]
    assert stats['backlog_skip']+stats['time_pass']==counts[5]
    assert stats['selftest']==stats['bound']==1 and stats['mirror_skip']==0
    lines = (folder/'serial.log').read_bytes().split(b'\n')
    updates = hits(lines,b'FX3_UI_GATE_SAMPLE id=8 ')
    assert len(updates)==2
    producers = hits(lines,b'FX3_UI_GATE_SAMPLE id=9 ')
    assert max(x['line'] for x in producers)>updates[-1]['line']
    sn = snapshots(lines,'0-3' if cpu_count==4 else '0')
    assert all('tid='+str(sn[0]['TID'])+' ' in x['text'] for x in updates)
    assert sn[1]['begin_line']>updates[-1]['line']
    gpe = hits(lines,b'FX3_GPE_CMD ')
    assert len(gpe)==2 and 'op=FillRect ' in gpe[0]['text'] and 'op=Flush ' in gpe[1]['text']
    assert all('result=0 ' in x['text'] for x in gpe)
    uptime=[]
    for i,s in enumerate(lines):
        if s.rstrip(b'\r')==b'FX3_GUEST_UPTIME_SNAPSHOT':
            j=next(j for j in range(i+1,min(i+12,len(lines)))
                if re.fullmatch(rb'[0-9]+\.[0-9]+ [0-9]+\.[0-9]+\r?',lines[j]))
            a,c=lines[j].decode().split()
            uptime.append({'line':j+1,'uptime':float(a),'idle':float(c)})
    assert len(uptime)==3
    surface = folder/'osd-draw-0001.raw'
    raw = surface.read_bytes()
    assert len(raw)==0x12c000 and not any(raw)
    return {'receipt':{**identity(receipt_path), **{k:receipt[k] for k in ['duration_seconds','qemu_exit','process_reaped','inputs_unchanged','guest_exception_markers','menu_verified']}},
        'command':{**identity(command_path),'args':command['args'],'icount_profile':None},
        'candidate':identity(candidate_path), 'DTB':cpus,
        'initrd':{**identity(Path(candidate['initrd']['path'])),'init_sha256':hashlib.sha256(init).hexdigest(),
            'init_selected_lines':selected,'gate_member_sha256':hashlib.sha256(gate).hexdigest()},
        'counter_RAM':{**identity(ram_path),'physical':hex(saved['address']), 'header':list(h),
            'selected_bank':h[2],'counter_ids':counts,'statistics':stats},
        'serial':{**identity(folder/'serial.log'),'ui_update_entries':updates,
            'producer_samples':producers,'gpe':gpe,'AppFw_snapshots':sn,
            'uptime_samples':uptime,'cpu_boot_evidence':hits(lines,('Brought up '+str(cpu_count)+' CPUs').encode())+hits(lines,b'NR_CPUS=4')},
        'first_draw_surface':{**identity(surface),'all_zero':True},
        'limits':['cpuset files alone do not establish task placement; actual allowed CPU lists are captured above',
            'id8 records entry before BL, not return from UI update',
            'a18 counter samples are concurrent and last_a18 is not a queue-length invariant',
            'three uptime samples precede the end of observation; no host timestamp per sample',
            'no saved AppFw user stack or ioctl argument bytes, so semaphore ID/caller/timeout unknown']}


def source_lines(path, needles):
    lines = path.read_text().splitlines()
    result = {s:[{'line':i+1,'text':x} for i,x in enumerate(lines) if s in x] for s in needles}
    assert all(result.values())
    return {**identity(path),'matching_lines':result}


def sem_wrapper():
    path=APDIR/'libosal_uipc.so'
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3'
    elf=ELFFile(io.BytesIO(raw))
    segment=next(s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=0x37b0< s['p_vaddr']+s['p_filesz'])
    offset=segment['p_offset']+0x37b0-segment['p_vaddr']
    rows=[{'VA':hex(i.address),'raw':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str}
        for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(raw[offset:offset+0x70],0x37b0)]
    assert len(rows)==0x70//4
    assert next(x for x in rows if x['VA']=='0x37c8')['instruction']=='str w0, [x29, #0x20]'
    assert next(x for x in rows if x['VA']=='0x37d0')['instruction']=='str x1, [x29, #0x28]'
    assert next(x for x in rows if x['VA']=='0x37dc')['instruction']=='mov x1, #-0x7fffffff'
    return {**identity(path),'u_osal_wai_sem_tmo':rows,
        'ioctl_argument':'16 bytes: semID u32 +0, padding4 +4, timeout u64 +8; recorded x2 pointer alone does not reveal these bytes'}


def main():
    assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert OUT == Path(__file__).resolve().parent
    for path,want in PINNED_INPUTS.items():
        assert identity(path)['sha256']==want,str(path)
    assert hashlib.sha256(DATA['ap']).hexdigest()==PINNED['ap']
    original=cpu_summary(ORIGINAL_DTB)
    assert [x['reg'] for x in original['cpus']]==[0,1,2,3]
    assert all(x['properties_hex']['enable-method']==b'spin-table\0'.hex() for x in original['cpus'])
    gate_text=(RT/'helpers/fx3-ui-gate-v11.c').read_text()
    offsets=re.search(r'const U offsets\[60\]=\{([^}]+)',gate_text)[1]
    words=re.search(r'const W words\[60\]=\{([^}]+)',gate_text)[1]
    offsets=[int(x,0) for x in offsets.split(',')]
    words=[int(x,0) for x in words.split(',')]
    anchors=[]
    for va,word in zip(offsets,words):
        row=dis('ap',va,4)[0]
        assert row['bytes']==struct.pack('<I',word).hex()
        anchors.append(row)
    blocks={hex(va):dis('ap',va,n) for va,n in [(0x16f2478,0x28),(0x16f25ec,0x68),
        (0x16f1998,0xb0),(0x16f1a48,0x50),(0x16f1d08,0xb0),(0x16f22c4,0x1c)]}
    assert blocks['0x16f2478'][1]['instruction']=='cmp w0, #2'
    assert dis('ap',0x16f2640,4)[0]['instruction']=='bl #0x16f1998'
    runs={n:read_run(n) for n in RUNS}
    assert runs[RUNS[1]]['initrd']['sha256']==runs[RUNS[2]]['initrd']['sha256']
    proof={'scope':'Offline saved AP83/AP84a evidence and original image audit only; only adjacent proof write; no QEMU or live guest',
        'sources':{str(p.relative_to(ROOT)):identity(p) for p in PINNED_INPUTS},
        'original_CPU_DTB':original,'observer_60_instruction_anchors':anchors,'AP_blocks':blocks,
        'QEMU_MTTCG':source_lines(Q/'accel/tcg/tcg-all.c',[
            'mttcg_supported && !icount_enabled()', 'No MTTCG when icount is enabled']),
        'Sony_timer':source_lines(Q/'hw/timer/sony_hwtimer.c',[
            '250LL << (s->control & 7)', 'QEMU_CLOCK_VIRTUAL', 'timer_new_ns']),
        'OSAL_sem_wrapper':sem_wrapper(), 'runs':runs,
        'pending_ioctl_observer_limit':source_lines(RT/'helpers/ioctl-trace-v11.c',[
            'int result = function(fd, request, argument);', 'FX3_IOCTL_PASS seq=',
            'if(is_uipc&&command==7&&outer_read==16)recv_begin']),
        'minimal_followup':[
            {'VA':'appFw+0x16f2640','read':'x0 object, TID, a18/a12; existing entry only'},
            {'VA':'appFw+0x16f2644','read':'x20, TID; confirms update 16f1998 returned'},
            {'VA':'appFw+0x16f1a1c and +0x16f1a20','read':'TID/object, before/after GraphicsEngine::drawFramebuffer'},
            {'VA':'appFw+0x16f22c8 and +0x16f22cc','read':'TID/x0 before, w0 after GraphicsEngine::processSystemMessage'},
            {'VA':'libosal_uipc+0x37b0','read':'TID, w0 actual semID, w1 timeout, x30/user frame chain'},
            {'VA':'libosal_uipc+0x37e0','read':'x2 points {u32 semID, padding, u64 timeout}; preserve 16 bytes and caller stack'},
        ],
        'proposed_comparison_not_executed':[
            {'profile':'baseline','cpus':1,'tcg':'existing default','icount':None},
            {'profile':'parallelism','cpus':4,'tcg':'thread=multi','icount':None,
             'requires':['matching four virt CPU nodes/cpu-map and PSCI enable-method','cpuset permits0-3','Brought up4 CPUs and per-thread Cpus_allowed_list','actual host vCPU worker threads']},
            {'profile':'instruction clock','cpus':1,'tcg':'thread=single','icount':'shift=0,align=off,sleep=off',
             'requires':['same candidate/modules/probes','compare at matched boot stage and instruction/virtual time, not only host duration']},
        ],
        'official_sources':[{'url':'https://www.qemu.org/docs/master/devel/tcg-icount.html','checked':'2026-11-02',
            'purpose':'icount is instruction-derived virtual time; incompatible with MTTCG; not cycle accurate'},
            {'url':'https://www.qemu.org/docs/master/devel/multi-thread-tcg.html','checked':'2026-11-02',
             'purpose':'one vCPU worker per emulated CPU in MTTCG; icount selects round-robin single mode'}],
        'unproven':['AP84 native cpuset r2 and icount comparison outcomes','whether time correction resolves current semaphore wait',
            'the blocked semaphore ID, owner/signaler, timeout and complete user call chain',
            'any nonuniform original-menu pixels, input round trip or physical/hardware equivalence']}
    target=OUT/'ap83-clock-gate-proof.json'
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print('PASS: original4/AP83guest1/AP84actual4 CPU; affinity readback; 60 original probe anchors; three direct RAM decodes; persistent post-clear semaphore waits; MTTCG/icount split; no guest execution')


if __name__=='__main__':
    main()
