#!/usr/bin/env python3
"""Read-only AP93-r5 audit. Only writes adjacent offscreen-proof.json.

Original AArch64 descriptor code is replayed in isolated Unicorn, never QEMU.
External calls and command submission are intercepted; no guest/device IO runs.
Synthetic nearest-neighbour pixels and lifetime guards are host vectors, not
Sony hardware arithmetic or a validation of an implemented v19 backend.
"""
from pathlib import Path
import copy
import hashlib
import json
import plistlib
import re
import runpy
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
from unicorn import arm64_const as ar

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'menu-repair-01').is_dir())
RUNTIME = ROOT / 'menu-repair-01/runtime'
RUN = RUNTIME / 'runs/ap93r5frame-19bbfb81'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
PINS = {
    'provider': '88effc3d0cf05c7027d30e1b7a505e88cad96ba001e55815c9300a422dff0bc1',
    'serial.log': '823a77ce7fc9946cc15ccb9f4627cd36424a7e846edbd00d8693a6e14a55aad3',
    'fx3-gpe-backend-v3.c': 'e5a46b178254c3e35848680e9d5ab04521a3515ac1168af1f8f11bcf1edfe5da',
    'fx3-gpe-observe-v18-frame-target.c': '27b22047abd724d41af315b16781552e9e376085d0707114f8d0010774cc5307',
    'fx3-gpe-resource-v3-target.inc': '25f79aa749e39f5b202aaed3c62e858f057d0b30d163f390dafb07f0c8f678c8',
    'fx3-timer-observe-v3.c': '1b3135edb19e8d7577d3b0a3f361ccb807f90fa67f054045bfe305dbaa0cd85d',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def provenance(path, pin=None):
    data = path.read_bytes()
    if pin:
        assert sha(data) == pin, ('input changed', str(path), sha(data))
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}


def u32(p, o):
    return struct.unpack_from('<I', p, o)[0]


def u64(p, o):
    return struct.unpack_from('<Q', p, o)[0]


def fields(p, kind):
    """Every byte belongs to exactly one field; reserved bytes stay visible."""
    common = [(0,8,'dst_physical'), (8,4,'dst_x'), (12,4,'dst_y'),
              (16,4,'dst_width'), (20,4,'dst_height')]
    if kind == 'FillRect':
        spec = common + [(24,4,'dst_stride_pixels'), (28,4,'dst_format'),
            (32,4,'color_bytes'), (36,1,'selector'), (37,1,'K'), (38,1,'async'),
            (39,1,'reserved27'), (40,8,'callback'), (48,8,'argument')]
    else:
        spec = common + [(24,4,'clip_x'), (28,4,'clip_y'), (32,4,'clip_width'),
            (36,4,'clip_height'), (40,4,'dst_adjust_x'), (44,4,'dst_adjust_y'),
            (48,4,'dst_stride_pixels'), (52,4,'dst_format'), (56,8,'src_physical'),
            (64,4,'src_x'), (68,4,'src_y'), (72,4,'src_width'), (76,4,'src_height'),
            (80,4,'src_adjust_x'), (84,4,'src_adjust_y'), (88,4,'src_stride_pixels'),
            (92,4,'src_format'), (96,4,'scale_x_bits'), (100,4,'scale_y_bits'),
            (104,4,'rotation'), (108,4,'color_bytes'), (112,1,'P70_selector'),
            (113,1,'P71_conversion'), (114,1,'P72_K'), (115,1,'P73_reg467'),
            (116,1,'P74_coordinate_mode'), (117,1,'P75_color_op'),
            (118,1,'P76_op730'), (119,1,'P77_H'), (120,1,'P78_V'),
            (121,1,'async'), (122,6,'reserved7a_7f'), (128,8,'callback'), (136,8,'argument')]
    out, covered = [], []
    for off, n, name in spec:
        b = p[off:off+n]
        row = {'offset': hex(off), 'bytes': n, 'name': name, 'raw_hex': b.hex()}
        row['value'] = list(b) if 'bytes' in name or 'reserved' in name else int.from_bytes(b, 'little')
        if 'physical' in name or name in ('callback','argument'):
            row['value_hex'] = hex(int.from_bytes(b,'little'))
        if 'scale_' in name:
            row['float32'] = struct.unpack('<f', b)[0]
        out.append(row)
        covered.extend(range(off,off+n))
    assert covered == list(range(len(p)))
    return out


def span(base, step, line, rows):
    assert rows > 0 and line > 0
    return {'start': hex(base), 'step': step, 'line_bytes': line, 'rows': rows,
            'last_row_start': hex(base+(rows-1)*step),
            'end_exclusive': hex(base+(rows-1)*step+line),
            'envelope_bytes': (rows-1)*step+line, 'touched_bytes': rows*line}


def synthetic_vectors():
    """Independent integer-4x oracle with transparent colours and sentinels."""
    result = []
    for name, pixel in [('opaque_white',lambda x,y:0xffff),
                        ('nonuniform_alpha',lambda x,y:((x*37+y*53)^0xa530)&0xffff)]:
        src = bytearray(b'\x3d' * 0x780)
        if name == 'opaque_white':
            # Actual seq216 fills all 32 pixels in 29 rows; child tail stays.
            src[:32*29*2] = b'\xff' * (32*29*2)
        for y in range(29):
            for x in range(29): struct.pack_into('<H',src,(y*32+x)*2,pixel(x,y))
        dst = bytearray(b'\xa5' * 0x7400)
        before_src, before_dst = bytes(src), bytes(dst)
        for sy in range(29):
            for sx in range(29):
                value = src[(sy*32+sx)*2:(sy*32+sx)*2+2]
                for ry in range(4):
                    for rx in range(4):
                        off = ((sy*4+ry)*128+sx*4+rx)*2
                        dst[off:off+2] = value
        for y in range(116):
            for x in range(116):
                got = struct.unpack_from('<H',dst,(y*128+x)*2)[0]
                assert got == pixel(x//4,y//4)  # floor(x*29/116), no alpha blend
            assert dst[(y*128+116)*2:(y+1)*128*2] == b'\xa5'*24
        assert src == before_src
        assert src[0x740:] == b'\x3d'*0x40
        result.append({'name':name, 'model':'nearest_v1 replacement; not hardware oracle',
            'source_sha256':sha(src), 'destination_before_sha256':sha(before_dst),
            'destination_after_sha256':sha(dst), 'checked_pixels':116*116,
            'padding_bytes_preserved':116*24, 'source_unchanged':True,
            'corner_values_le16':[struct.unpack_from('<H',dst,(y*128+x)*2)[0]
                                   for x,y in [(0,0),(3,3),(4,0),(115,115)]]})
    # Counterexample to 'inside live parent + any live bitmap' being sufficient.
    def admission(parent, child, bitmap, held, epoch_match, compaction, start, end):
        if not parent:return 'parent_stale'
        if not child:return 'child_not_active'
        if not bitmap or not held:return 'bitmap_binding_or_lease_missing'
        if not epoch_match:return 'queued_ABA'
        if compaction:return 'compaction_uncovered'
        if not (0x410936c80 <= start < end <= 0x41093e080):return 'child_bounds'
        return 'admit_model'
    good = [True,True,True,True,True,False,0x410936c80,0x41093e068]
    cases = [('live',{},'admit_model'), ('parent_closed',{0:False},'parent_stale'),
             ('freed_child_parent_live',{1:False},'child_not_active'),
             ('unrelated_bitmap',{2:False},'bitmap_binding_or_lease_missing'),
             ('unheld_reference',{3:False},'bitmap_binding_or_lease_missing'),
             ('reused_address',{4:False},'queued_ABA'),
             ('compaction_pending',{5:True},'compaction_uncovered'),
             ('end_exact_child',{7:0x41093e080},'admit_model'),
             ('one_byte_past_child_inside_parent',{7:0x41093e081},'child_bounds'),
             ('before_child_inside_parent',{6:0x410936c7f},'child_bounds')]
    for name, edits, expected in cases:
        args=good[:]
        for index,value in edits.items():args[index]=value
        got=admission(*args);assert got==expected
        result.append({'name':name,'kind':'proposed guard model only', 'inputs':args,
                       'expected':expected, 'passed':True, 'rejected_pixels_written':0 if got!='admit_model' else None})
    return result


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume.get('VolumeUUID') == UUID and volume.get('MountPoint') == '/Volumes/KAFU2T'
    provider = HERE.parent / 'gpe-blend-p3/audit_gpe_blend.py'
    inputs = [provenance(provider,PINS['provider']),provenance(RUN/'serial.log',PINS['serial.log'])]
    lib = runpy.run_path(str(provider),run_name='offscreen_readonly_provider')
    obj,gpe = lib['Image']('libObj.so'),lib['Image']('libgpe.so')
    inputs += [provenance(im.path,im.sha) for im in (obj,gpe)]
    source_evidence={}
    for name in ('fx3-gpe-backend-v3.c','fx3-gpe-observe-v18-frame-target.c',
                 'fx3-gpe-resource-v3-target.inc','fx3-timer-observe-v3.c'):
        path=RUNTIME/'helpers'/name;inputs.append(provenance(path,PINS[name]))
        lines=path.read_text().splitlines()
        terms=('if(!q[115])','legacy_plan_blit(raw,n,p)','u32(q+16)!=u32(q+72)',
            '!dr.native_open','dr.type!=0x403','child_epoch_untracked',
            'scope=allocation_interval','same_parent=','bitmap_read=',
            'int read=peek(command+0x78','p->approx_blend=1;',
            'p->approx_stretch=dw!=sw','if(p->approx_fmt2)','else if(p->approx_blend)',
            'resource_lookup(plan.dst','resource_register','frame_target_tuple')
        source_evidence[name]=[{'line':i,'text':s} for i,s in enumerate(lines,1) if any(t in s for t in terms)]
    text=(RUN/'serial.log').read_bytes()
    lines=text.split(b'\n')
    commands={};evidence=[];parent={};active={};retired=[]
    for n,rawline in enumerate(lines,1):
        s=rawline.decode(errors='replace').rstrip('\r')
        if any(t in s for t in ('mpMemoryHeap','FX3_GPE_RESOURCE_REGISTER',
                'FX3_GPE_RESOURCE_BOUND','scr7248','FX3_UI_FILL_EXEC seq=8 ',
                'FX3_UI_FILL_RETURN seq=8 ')):
            evidence.append({'serial_LF_line':n,'text':s})
        kv=dict(re.findall(r'(\w+)=(\S+)',s))
        if s.startswith('FX3_GPE_RESOURCE_REGISTER '):
            o=int(kv['object'],0);parent[o]={'serial_LF_line':n,**kv}
        if s.startswith('FX3_GPE_RESOURCE_SUBALLOC '):
            o=int(kv['object'],0);p=int(kv['phys'],0);lp=int(kv['logical'],0)
            active[o,lp]={'serial_LF_line':n,**kv}
            if p in (0x4109364c0,0x410936c80):evidence.append({'serial_LF_line':n,'text':s})
        if s.startswith('FX3_GPE_RESOURCE_SUBFREE '):
            key=(int(kv['object'],0),int(kv['logical'],0))
            a=active.pop(key,None)
            if a and int(a['phys'],0) in (0x4109364c0,0x410936c80):
                retired.append({'serial_LF_line':n,'text':s,'allocation':a})
        if s.startswith('FX3_GPE_RESOURCE_RETIRE '):
            o=int(kv['object'],0)
            active={k:v for k,v in active.items() if k[0]!=o};parent.pop(o,None)
        ma=re.search(r'FX3_GPE_(RAW|REJECT)_PARAMS op=(FillRect|BitBlit) seq=(216|217) read=1 len=(56|144) raw_hex=([0-9a-f]+)',s)
        if ma:
            kind,seq=ma[2],int(ma[3]);p=bytes.fromhex(ma[5]);assert len(p)==int(ma[4])
            commands[seq]={'serial_LF_line':n,'kind':kind,'raw_hex':p.hex(),'fields':fields(p,kind),
                           'active_observed_suballocations':copy.deepcopy(list(active.values())),
                           'observed_parents':copy.deepcopy(list(parent.values()))}
            evidence.append({'serial_LF_line':n,'text':s})
        if re.search(r'FX3_GPE_CMD op=.*seq=(216|217)\b',s):evidence.append({'serial_LF_line':n,'text':s})
    assert set(commands)=={216,217}
    fill=bytes.fromhex(commands[216]['raw_hex']);p=bytes.fromhex(commands[217]['raw_hex'])
    assert (u64(fill,0),u32(fill,16),u32(fill,20),u32(fill,24))==(0x4109364c0,32,29,32)
    assert fill[32:39]==bytes.fromhex('ffffffff00ff00')
    assert (u64(p,0),u64(p,56))==(0x410936c80,0x4109364c0)
    assert struct.unpack_from('<2I',p,16)==(116,116) and struct.unpack_from('<2I',p,72)==(29,29)
    assert p[112:122]==bytes.fromhex('0000ff00000000000000')
    assert all(v==0 for v in p[122:])

    class Replay(lib['Replay']):
        def hook(self,uc,address,size,arg):
            name=self.image.plt.get(address,'')
            if 'StretchRotateBlit' in name:
                uc.reg_write(ar.UC_ARM64_REG_PC,0xc878);return
            if name in ('cslMakeZoomSprite','cslMakeZoomRotateSprite'):
                self.other.append({'kind':name,'caller_va':hex(self.reg(30)-4),
                    'dst_x':self.reg(1)&0xffffffff,'dst_y':self.reg(2)&0xffffffff,
                    'src_struct40':bytes(uc.mem_read(self.reg(0),40)).hex(),
                    'scale_float':[struct.unpack('<f',struct.pack('<I',uc.reg_read(r)&0xffffffff))[0]
                                   for r in (ar.UC_ARM64_REG_S0,ar.UC_ARM64_REG_S1)]})
                self.ret();return
            super().hook(uc,address,size,arg)
    replay=Replay(gpe)
    rr=replay.run(0xcf2c,p)
    assert rr['route']==['0xc878'] and rr['status']=='submission_intercepted'
    zoom=next(d for d in rr['other_descriptors'] if d['kind']=='cslMakeZoomSprite')
    regs={int(r['reg'],16):r['value'] for r in rr['register_writes']}
    assert zoom['scale_float']==[4.0,4.0] and regs[0x467]==0 and regs[0x760]==0
    assert regs[0x20]==(0x410936c80&0xffffffff) and regs[0x462]==(0x4109364c0&0xffffffff)
    assert regs[0x463]==32
    commands[217]['original_replay']=rr
    commands[216]['original_replay']=replay.run(0xc30c,fill)
    # A same-sized counterfactual proves that even THEN selector0/K255 is b578,
    # not the b234 blending branch; it does not replace the captured request.
    equal=bytearray(p);struct.pack_into('<2I',equal,16,29,29)
    eq=replay.run(0xcf2c,equal)
    assert eq['route']==['0xb578']
    counterfactual={'description':'synthetic: only destination size changed to 29x29',
                    'raw_hex':equal.hex(),'original_replay':eq}
    sf=span(0x4109364c0,64,64,29)
    ss=span(0x4109364c0,64,58,29)
    ds=span(0x410936c80,256,232,116)
    for seq in commands:
        q=commands[seq]
        relevant=[]
        for a in q.pop('active_observed_suballocations'):
            if int(a['phys'],0) in (0x4109364c0,0x410936c80):relevant.append(a)
        q['active_by_observed_malloc_free_events_only']=relevant
        q['observed_parents']=[r for r in q['observed_parents'] if int(r['phys'],0)==0x410924000]
        assert len(q['observed_parents'])==1
        assert len(relevant)==(1 if seq==216 else 2)
    assert int(ss['end_exclusive'],16)<=0x410936c40<0x410936c80
    assert int(ds['end_exclusive'],16)<=0x41093e080<0x410c64000

    ranges_obj=[(0xee638,0xee76c),(0xee76c,0xee8a4),(0xef1ac,0xef210),
        (0xef638,0xef69c),(0xefd0c,0xefe84),(0xeff44,0xeffbc),
        (0xf0a98,0xf0acc),(0xf0c80,0xf0cb8),(0xf0f04,0xf0fcc),
        (0xf1010,0xf12b4),(0xf12b4,0xf15bc),(0xf17d0,0xf19b8),
        (0xfb1e8,0xfb2a4),(0x100ab4,0x100cf8),(0x100e9c,0x101194),
        (0x1013a8,0x101548),(0x1017ac,0x101cfc),
        (0x102560,0x10266c),(0x102718,0x102814),(0x102814,0x102930),(0x102b98,0x102c08),
        (0x103184,0x1031b0),(0x1031b0,0x103454),(0x103454,0x103760),(0x103760,0x103b90),
        (0xf96f4,0xf97ec),
        (0x150b9c,0x150c58),(0x150f34,0x150fe4),(0xffaac,0xffc58)]
    ranges_gpe=[(0xcf2c,0xd148),(0xc878,0xcf2c),(0xc30c,0xc6f8),
                (0xb234,0xb578),(0xb578,0xb7b8),(0x13e5c,0x140a8)]
    original={im.path.name:[{'start':hex(a),'end_exclusive':hex(b),
        'raw_sha256':sha(im.read(a,b-a)),'instructions':im.block(a,b)} for a,b in ranges]
        for im,ranges in [(obj,ranges_obj),(gpe,ranges_gpe)]}
    rel={}
    for sec in obj.elf.iter_sections():
        if sec['sh_type']=='SHT_RELA':
            for r in sec.iter_relocations():rel[r['r_offset']]=r['r_addend']
    assert rel[0x252650]==0x1dedd8 and rel[0x252668]==0x252648
    assert rel[0x252748]==0xf0a98 and rel[0x261c50]==0x252660
    vtable={'rtti_string_va':'0x1dedd8','rtti_string':obj.read(0x1dedd8,29).split(b'\0')[0].decode(),
        'rtti_va':'0x252648','vtable_address_point':'0x252670',
        'relative_relocations':{hex(a):hex(rel[a]) for a in (0x252650,0x252668,0x252748,0x261c50,
             0x261e98,0x262878,0x261f58,0x262450)},
        'slots':{hex(a-0x252670):hex(rel[a]) for a in range(0x252670,0x252758,8)}}
    xrefs=[];scan_coverage=[]
    targets={0x103550,0x10364c,0x102560,0x1025c4,0x102814}
    for sec in obj.elf.iter_sections():
        if sec['sh_flags']&4:
            instructions=list(lib['CS'].disasm(sec.data(),sec['sh_addr']))
            assert len(instructions)*4==sec['sh_size']
            scan_coverage.append({'section':sec.name,'start':hex(sec['sh_addr']),
                'bytes':sec['sh_size'],'decoded_bytes':len(instructions)*4})
            for i in instructions:
                if i.mnemonic in ('bl','b') and i.op_str.startswith('#') and int(i.op_str[1:],16) in targets:
                    xrefs.append({'va':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'bytes':i.bytes.hex()})
    assert any(r['va']=='0xf14fc' and r['asm']=='bl #0x102560' for r in xrefs)
    proof={'schema':'offscreen-subblock-audit-v1','outcome':'audit_complete',
        'scope':'offline read-only; no QEMU; no v19 implementation; no hardware pixel oracle',
        'volume_uuid':UUID,'inputs':inputs,'serial_line_numbering':'LF only, one-based',
        'commands':[commands[k] for k in sorted(commands)],'runtime_evidence':evidence,
        'relevant_observed_frees_after_or_before_commands':retired,
        'spans':{'fill_destination':sf,'blit_source':ss,'blit_destination':ds,
                 'parent':['0x410924000','0x410c64000'],
                 'source_child':['0x4109364c0','0x410936c40'],
                 'destination_child':['0x410936c80','0x41093e080'],
                 'physical_envelopes_disjoint':True},
        'same_size_counterfactual':counterfactual,'bitmap_impl_type':vtable,
        'original_code':original,'allocation_direct_xrefs':xrefs,'xref_scan_coverage':scan_coverage,
        'current_adapter_source_evidence':source_evidence,'host_vectors':synthetic_vectors(),
        'conclusions':{
            'actual_seq217_route':'cf2c -> d0b4(P74=0) -> d124 -> c878; zoom 4.0 x 4.0',
            'seq217_not_b234_or_memcpy':True,'selector0_K255_blend_disabled_reg760':0,
            'v16r2_planner_reject':'P73=0 enters legacy; dst116x116 != src29x29 => unsupported2',
            'v18_target_reject':'Heap2 parent origin malloc_parent_v1 type0 fails native_open/type403 gate',
            'offscreen_bitmap_is_original_supported_use':'A1 BitmapImpl allocate+CmdFillrect/CmdRectDraw lifecycle; A2 actual Heap2 writes',
            'exact_runtime_bitmap_class':'U: only CmdFillrect bitmap pointer field readable, not complete bitmap object',
            'parent_plus_existence_is_general_memory_safety_proof':False,
            'child_event_reconstruction':'two allocations observed active; does not cover compaction or queued ABA',
            'nearest_v1':'explicit visual approximation; replacement/no source-over for this subset'},
        'unproven':['exact AP93 allocation caller stack and concrete BitmapImpl vptr/metadata for these two children',
            'seq217 source/destination bitmap object pointers and their captured original lock ownership',
            'compaction absence or complete mutation interception in AP93',
            'queued raw-parameter ABA identity through FIFO',
            'Sony reg467=0 filter/sample phase/edge behavior and exact hardware pixels',
            'v19 implementation, sanitizer/backend execution, guest readback and subsequent UI input loop']}
    dest=HERE/'offscreen-proof.json'
    dest.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
    print('PASS: rebuilt offscreen-proof.json; 56/144 bytes decoded; original zoom=4x4 blend=off; 12 host vectors')


if __name__=='__main__':
    main()
