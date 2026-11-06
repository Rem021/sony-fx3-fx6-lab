"""Small synthetic newc/ELF tests exercising the production implementation.

Fixture-only pins/guard are injected through Python, never exposed by CLI.
All artifacts stay in a new directory and are retained for review.
"""
import copy
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import unittest
import argparse

import fixed_layout as m

OUT = m.HERE / 'test-artifacts'  # overridden only by this test script's --evidence-name


def elf_fixture(soname='fx3-ui-gate-v14-n1.so', stripped=False, remove_static=False):
    names = ['', '.text', '.dynstr', '.dynsym', '.dynamic', '.bss', '.symtab', '.strtab']
    if remove_static:
        names=names[:-2]
    if not stripped:
        names += ['.debug_info']
    names += ['.shstrtab']
    strings = b'\0libc.so.6\0libdl.so.2\0' + soname.encode() + b'\0gate_bind\0syscall\0'
    offsets = {x:strings.index(x.encode()+b'\0') for x in ('libc.so.6','libdl.so.2',soname,'gate_bind','syscall')}
    dynsym = bytes(24) + struct.pack('<IBBHQQ',offsets['gate_bind'],0x12,0,1,0x4000b0,16) + struct.pack('<IBBHQQ',offsets['syscall'],0x12,0,0,0,0)
    dynamic = b''.join(struct.pack('<qQ',t,v) for t,v in [(1,offsets['libc.so.6']),(1,offsets['libdl.so.2']),(14,offsets[soname]),(0,0)])
    shstr = b'\0' + b''.join(n.encode()+b'\0' for n in names[1:])
    shstr_offset = 544 if stripped else 640
    shoff = 768 if stripped else 896
    data = bytearray(shoff+64*len(names))
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    struct.pack_into('<16sHHIQQQIHHHHHH',data,0,ident,3,183,1,0,64,shoff,0,64,56,1,64,len(names),len(names)-1)
    struct.pack_into('<IIQQQQQQ',data,64,1,7,0,0x400000,0x400000,512,544,4096)
    data[176:192] = bytes(range(16))
    data[224:224+len(dynsym)] = dynsym
    data[304:304+len(strings)] = strings
    data[416:480] = dynamic
    data[512:536] = bytes(24)
    data[536:542] = b'\0keep\0'
    if not stripped:
        data[560:624] = b'D'*64
    data[shstr_offset:shstr_offset+len(shstr)] = shstr
    table = {
        '':(0,0,0,0,0,0,0,0,0),
        '.text':(1,6,0x4000b0,176,16,0,0,16,0),
        '.dynstr':(3,2,0x400130,304,len(strings),0,0,1,0),
        '.dynsym':(11,2,0x4000e0,224,len(dynsym),2,1,8,24),
        '.dynamic':(6,3,0x4001a0,416,64,2,0,8,16),
        '.bss':(8,3,0x400200,512,32,0,0,8,0),
        '.symtab':(2,0,0,512,24,7,1,8,24),
        '.strtab':(3,0,0,536,6,0,0,1,0),
        '.debug_info':(1,0,0,560,64,0,0,1,0),
        '.shstrtab':(3,0,0,shstr_offset,len(shstr),0,0,1,0)}
    for i,n in enumerate(names):
        struct.pack_into('<IIQQQQIIQQ',data,shoff+64*i,0 if not n else shstr.index(n.encode()+b'\0'),*table[n])
    return bytes(data)


def newc(rows):
    b = bytearray()
    for i,(name,payload,mode,nlink) in enumerate(rows+[('TRAILER!!!',b'',0,1)]):
        vals=[i+1,mode,0,0,nlink,0,len(payload),0,0,0,0,len(name.encode())+1,0]
        b += b'070701' + b''.join(f'{v:08x}'.encode() for v in vals)
        b += name.encode()+b'\0'
        b += bytes(m.aligned(len(b))-len(b))
        b += payload
        b += bytes(m.aligned(len(b))-len(b))
    return bytes(b)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.volume_check()
        OUT.mkdir()  # intentionally exclusive, no automatic cleanup

    def setUp(self):
        self.d = OUT/self._testMethodName
        self.d.mkdir()
        self.base = self.d/'base'; self.base.mkdir()
        self.raw = self.d/'raw.so'; self.raw.write_bytes(elf_fixture())
        self.helper = self.d/'stripped.so'; self.helper.write_bytes(elf_fixture(stripped=True))
        self.old = b'O'*2048
        self.archive = self.base/'guest.cpio'
        self.archive.write_bytes(newc([('before',b'B'*113,0o100644,1),(m.MEMBER,self.old,0o100755,1),('after',b'A'*333,0o100600,1)]))
        self.dtb = self.base/'guest.dtb'; self.dtb.write_bytes(b'unchanged-dtb-fixture')
        self.candidate = self.base/'candidate.json'
        self.candidate.write_text(json.dumps(dict(initrd=dict(path=str(self.archive),sha256=m.sha_file(self.archive)),
                                                 dtb=dict(path=str(self.dtb),sha256=m.sha_file(self.dtb)),
                                                 memory_mib=5120,cores=4,noicount=True,other={'a':[1,2]})))
        with self.archive.open('rb') as f:
            row=m.index_archive(f)[1]
        self.pins=dict(candidate_sha256=m.sha_file(self.candidate),archive_sha256=m.sha_file(self.archive),
                       archive_size=self.archive.stat().st_size,header_offset=row['header_offset'],
                       payload_offset=row['payload_offset'],slot_size=row['size'],mode=row['mode'],
                       member_sha256=m.digest(self.old),dtb_sha256=m.sha_file(self.dtb))
        self.contract=self.d/'release.json'
        self.release=dict(schema='fx3-fixed-layout-release/v1',helper_version='r14',variant='N1',
                          soname='fx3-ui-gate-v14-n1.so',raw_sha256=m.sha_file(self.raw),stripped_sha256=m.sha_file(self.helper),
                          diagnostic_contract={'fixture':True})
        # Deliberately synthetic build metadata; ELF fixture bytes were generated
        # above, not compiled. Real samples use executed frozen Zig commands.
        src=self.d/'fixture.c'; src.write_text('/* synthetic provenance fixture */\n')
        manifest=self.d/'SOURCE-SHA256SUMS'; manifest.write_text(m.sha_file(src)+'  fixture.c\n')
        command=[str(Path(sys.executable).resolve()),'cc',str(src),'-o',str(self.raw)]
        build=self.d/'BUILD.json'; build.write_text(json.dumps({'variants':{'N1':dict(command=command,exit=0,sha256=m.sha_file(self.raw))}}))
        stripped_command=list(command); stripped_command[-1]=str(self.helper); stripped_command.insert(2,'-Wl,--strip-debug')
        self.receipt_path=self.d/'STRIP-BUILD.json'
        self.receipt=dict(schema='fx3-linker-strip-build/v1',exit=0,original_command=command,command=stripped_command,
                          raw_sha256=m.sha_file(self.raw),stripped_sha256=m.sha_file(self.helper),
                          command_input_hashes=m.command_inputs(command))
        self.receipt_path.write_text(json.dumps(self.receipt))
        self.release['provenance']={k:dict(path=str(p),sha256=m.sha_file(p)) for k,p in
            [('raw_build_manifest',build),('source_manifest',manifest),('strip_build_receipt',self.receipt_path)]}
        self.save_contract()

    def save_contract(self):
        self.contract.write_text(json.dumps(self.release))

    def plan(self):
        return m.make_plan(self.base,self.raw,self.helper,self.contract,self.pins)[0]

    def write(self, plan, name='output', **kw):
        return m.write_archive(plan,self.d/name,pins=self.pins,require_r15=False,guard=lambda:None,**kw)

    def repin(self):
        c=json.loads(self.candidate.read_text()); c['initrd']['sha256']=m.sha_file(self.archive)
        self.candidate.write_text(json.dumps(c))
        self.pins['archive_sha256']=m.sha_file(self.archive)
        self.pins['archive_size']=self.archive.stat().st_size
        self.pins['candidate_sha256']=m.sha_file(self.candidate)

    def test_roundtrip_and_manifest(self):
        plan=self.plan()
        m.exclusive_json(self.d/'plan.json',plan)
        before=self.archive.read_bytes(); dtb=self.dtb.read_bytes()
        receipt=self.write(plan)
        after=(self.d/'output/guest.cpio').read_bytes()
        offset,size=plan['allowed_change'].values()
        self.assertEqual(len(before),len(after))
        self.assertEqual(before[:offset],after[:offset]); self.assertEqual(before[offset+size:],after[offset+size:])
        self.assertEqual(after[offset:offset+size],self.helper.read_bytes()+bytes(size-self.helper.stat().st_size))
        self.assertEqual(self.archive.read_bytes(),before); self.assertEqual(self.dtb.read_bytes(),dtb)
        self.assertTrue(receipt['outside_slot_every_byte_equal'])
        c=json.loads(self.candidate.read_text()); d=json.loads((self.d/'output/candidate.json').read_text())
        self.assertEqual({k:v for k,v in d.items() if k not in ('initrd','fixed_layout_diagnostic_contract')},
                         {k:v for k,v in c.items() if k!='initrd'})
        self.assertEqual(c['dtb'],d['dtb'])

    def test_plan_reads_small_metadata_only(self):
        class Counting(io.BytesIO):
            count=0
            def read(self,n=-1):
                b=super().read(n); self.count+=len(b); return b
        f=Counting(self.archive.read_bytes()); rows=m.index_archive(f)
        self.assertLess(f.count,len(f.getvalue())//2)
        self.assertEqual(len(rows),4)

    def test_elf_section_metadata_differences_reported(self):
        a=self.plan()['audit']
        self.assertTrue(a['program_headers_equal'])
        self.assertFalse(a['pt_load_whole_bytes_equal'])
        self.assertEqual({r['field'] for r in a['elf_header_changes']},{'shoff','shnum','shstrndx'})
        self.assertEqual(a['removed_debug_sections'],['.debug_info'])
        self.assertEqual(len(a['alloc_sections']),5)

    def test_elf_alloc_tamper(self):
        b=bytearray(self.helper.read_bytes()); b[177]^=1
        with self.assertRaisesRegex(ValueError,'SHF_ALLOC bytes'):
            m.audit_elf(self.raw.read_bytes(),b)

    def test_elf_program_header_tamper(self):
        b=bytearray(self.helper.read_bytes()); b[68]^=1
        with self.assertRaisesRegex(ValueError,'program headers'):
            m.audit_elf(self.raw.read_bytes(),b)

    def test_elf_alloc_layout_tamper(self):
        b=bytearray(self.helper.read_bytes()); sh=m.ELF(b).h[6]; b[sh+64+16]^=1
        with self.assertRaisesRegex(ValueError,'SHF_ALLOC layout'):
            m.audit_elf(self.raw.read_bytes(),b)

    def test_elf_wrong_architecture(self):
        b=bytearray(self.helper.read_bytes()); struct.pack_into('<H',b,18,62)
        with self.assertRaisesRegex(ValueError,'AArch64'):
            m.audit_elf(self.raw.read_bytes(),b)

    def test_elf_nonsection_header_change(self):
        b=bytearray(self.helper.read_bytes()); b[24]=1
        with self.assertRaisesRegex(ValueError,'outside section-table'):
            m.audit_elf(self.raw.read_bytes(),b)

    def test_malformed_section_table_rejected(self):
        b=bytearray(self.helper.read_bytes()); elf=m.ELF(b); s=elf.by_name['.symtab']
        # Duplicate the null section name: malformed metadata must be rejected.
        struct.pack_into('<I',b,elf.h[6]+64*s['index'],0)
        with self.assertRaises(ValueError):
            m.audit_elf(self.raw.read_bytes(),b)

    def test_approved_static_symbol_removal(self):
        audit=m.audit_elf(self.raw.read_bytes(),elf_fixture(stripped=True,remove_static=True))
        self.assertEqual(audit['removed_static_symbol_sections'],['.strtab','.symtab'])

    def test_strip_all_build_command_rejected(self):
        self.receipt['command'][2]='-Wl,--strip-all'
        self.receipt_path.write_text(json.dumps(self.receipt))
        self.release['provenance']['strip_build_receipt']['sha256']=m.sha_file(self.receipt_path); self.save_contract()
        with self.assertRaisesRegex(ValueError,'beyond --strip-debug'):
            self.plan()

    def test_source_provenance_mismatch(self):
        (self.d/'fixture.c').write_text('changed\n')
        with self.assertRaisesRegex(ValueError,'source manifest input hash'):
            self.plan()

    def test_build_provenance_hash_mismatch(self):
        self.release['provenance']['raw_build_manifest']['sha256']='0'*64; self.save_contract()
        with self.assertRaisesRegex(ValueError,'provenance hash'):
            self.plan()

    def test_oversize_helper(self):
        self.helper.write_bytes(self.helper.read_bytes()+bytes(2049))
        with self.assertRaisesRegex(ValueError,'exceeds'):
            self.plan()

    def test_wrong_release_version(self):
        self.release['helper_version']='r15'; self.save_contract()
        with self.assertRaisesRegex(ValueError,'version mismatch'):
            self.plan()

    def test_wrong_release_schema(self):
        self.release['schema']='unknown'; self.save_contract()
        with self.assertRaisesRegex(ValueError,'contract version'):
            self.plan()

    def test_wrong_release_hash(self):
        self.release['stripped_sha256']='0'*64; self.save_contract()
        with self.assertRaisesRegex(ValueError,'ELF hash mismatch'):
            self.plan()

    def test_r14_real_write_gate(self):
        with self.assertRaisesRegex(ValueError,'requires final r15'):
            m.write_archive(self.plan(),self.d/'output',pins=self.pins,guard=lambda:None)
        self.assertFalse((self.d/'output').exists())

    def test_original_member_hash_mismatch(self):
        with self.archive.open('r+b') as f:
            f.seek(self.pins['payload_offset']); f.write(b'X')
        with self.assertRaisesRegex(ValueError,'member hash mismatch'):
            self.plan()

    def test_missing_target_member(self):
        with self.archive.open('r+b') as f:
            f.seek(self.pins['header_offset']+110); f.write(b'Z')
        with self.assertRaisesRegex(ValueError,'missing/duplicate'):
            self.plan()

    def test_unrelated_payload_corruption_write_rejected(self):
        with self.archive.open('rb') as f:
            offset=m.index_archive(f)[0]['payload_offset']
        with self.archive.open('r+b') as f:
            f.seek(offset); f.write(b'Z')
        plan=self.plan()
        with self.assertRaisesRegex(ValueError,'complete source archive hash'):
            self.write(plan)
        self.assertFalse((self.d/'output').exists())

    def test_duplicate_member(self):
        self.archive.write_bytes(newc([(m.MEMBER,self.old,0o100755,1)]*2)); self.repin()
        with self.assertRaisesRegex(ValueError,'duplicate member'):
            self.plan()

    def test_nonregular_target(self):
        self.archive.write_bytes(newc([('before',b'B'*113,0o100644,1),(m.MEMBER,self.old,0o120755,1),('after',b'A'*333,0o100600,1)])); self.repin()
        self.pins['mode']=0o120755
        with self.assertRaisesRegex(ValueError,'standalone regular'):
            self.plan()

    def test_hardlink_target(self):
        self.archive.write_bytes(newc([('before',b'B'*113,0o100644,1),(m.MEMBER,self.old,0o100755,2),('after',b'A'*333,0o100600,1)])); self.repin()
        with self.assertRaisesRegex(ValueError,'standalone regular'):
            self.plan()

    def test_member_path_traversal(self):
        self.archive.write_bytes(newc([('../bad',b'',0o100644,1)])); self.repin()
        with self.assertRaisesRegex(ValueError,'unsafe member path'):
            self.plan()

    def test_crc_archive_rejected(self):
        b=bytearray(self.archive.read_bytes()); b[:6]=b'070702'; self.archive.write_bytes(b)
        with self.assertRaisesRegex(ValueError,'070701'):
            self.plan()

    def test_trailing_padding_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes()+bytes(4)); self.repin()
        with self.assertRaisesRegex(ValueError,'exactly at EOF'):
            self.plan()

    def test_truncated_archive(self):
        self.archive.write_bytes(self.archive.read_bytes()[:-1]); self.repin()
        with self.assertRaises(ValueError): self.plan()

    def test_original_dtb_mismatch(self):
        self.dtb.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'DTB hash'):
            self.plan()

    def test_candidate_hash_mismatch(self):
        self.candidate.write_text('{}')
        with self.assertRaisesRegex(ValueError,'manifest hash'):
            self.plan()

    def test_existing_output_rejected(self):
        plan=self.plan(); (self.d/'output').mkdir()
        with self.assertRaisesRegex(ValueError,'already exists'):
            self.write(plan)
        self.assertEqual(list((self.d/'output').iterdir()),[])

    def test_symlink_input_rejected(self):
        p=self.d/'alias.so'; p.symlink_to(self.helper)
        with self.assertRaisesRegex(ValueError,'symlink'):
            m.make_plan(self.base,self.raw,p,self.contract,self.pins)

    def test_symlink_output_rejected(self):
        plan=self.plan(); (self.d/'output').symlink_to(self.d/'nonexistent')
        with self.assertRaisesRegex(ValueError,'symlink'):
            self.write(plan)

    def test_symlink_parent_rejected(self):
        p=self.d/'alias'; p.symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):
            m.safe_path(p/'child')

    def test_uuid_mismatch_before_output(self):
        def bad_guard(): m.require(False,'target volume UUID/mount mismatch')
        with self.assertRaisesRegex(ValueError,'UUID'):
            m.write_archive(self.plan(),self.d/'output',pins=self.pins,require_r15=False,guard=bad_guard)
        self.assertFalse((self.d/'output').exists())

    def test_stale_plan(self):
        plan=self.plan(); self.contract.write_text(self.contract.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'stale'):
            self.write(plan)

    def test_output_failure_preserved_incomplete(self):
        def fault(src,dst): raise OSError('deliberate synthetic failure')
        with self.assertRaisesRegex(OSError,'synthetic failure'):
            self.write(self.plan(),fault=fault)
        out=self.d/'output'
        self.assertTrue((out/'guest.cpio').exists())
        self.assertTrue((out/'INCOMPLETE.json').exists())
        self.assertEqual(json.loads((out/'FAILED.json').read_text())['state'],'incomplete')
        self.assertFalse((out/'COMPLETE.json').exists())

    def test_output_tamper_preserved_incomplete(self):
        def tamper(src,dst):
            pos=dst.tell(); dst.seek(0); dst.write(b'X'); dst.seek(pos)
        with self.assertRaisesRegex(ValueError,'outside permitted'):
            self.write(self.plan(),fault=tamper)
        self.assertEqual(json.loads((self.d/'output/FAILED.json').read_text())['state'],'incomplete')
        self.assertFalse((self.d/'output/COMPLETE.json').exists())

    def test_final_r15_fixture_write(self):
        self.raw.write_bytes(elf_fixture(soname='fx3-ui-gate-v15-n1.so'))
        self.helper.write_bytes(elf_fixture(soname='fx3-ui-gate-v15-n1.so',stripped=True,remove_static=True))
        self.release.update(helper_version='r15',soname='fx3-ui-gate-v15-n1.so',
                            raw_sha256=m.sha_file(self.raw),stripped_sha256=m.sha_file(self.helper))
        build_path=Path(self.release['provenance']['raw_build_manifest']['path'])
        build=json.loads(build_path.read_text()); build['variants']['N1']['sha256']=m.sha_file(self.raw)
        build_path.write_text(json.dumps(build))
        self.receipt.update(raw_sha256=m.sha_file(self.raw),stripped_sha256=m.sha_file(self.helper))
        self.receipt_path.write_text(json.dumps(self.receipt))
        for key in ('raw_build_manifest','strip_build_receipt'):
            ref=self.release['provenance'][key]; ref['sha256']=m.sha_file(ref['path'])
        self.save_contract()
        receipt=m.write_archive(self.plan(),self.d/'output',pins=self.pins,guard=lambda:None)
        self.assertEqual(receipt['state'],'complete')

    def test_outside_span_checker_detects_tamper(self):
        a=io.BytesIO(b'a'*100); b=io.BytesIO(b'X'+b'a'*99)
        with self.assertRaisesRegex(ValueError,'outside permitted'):
            m.verify_outside(a,b,50,10)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence-name',default='test-artifacts')
    args=parser.parse_args()
    m.require(__import__('re').fullmatch(r'test-artifacts(?:-[A-Za-z0-9]+)?',args.evidence_name) is not None,'bad evidence directory')
    OUT=m.HERE/args.evidence_name
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(tests=result.testsRun,failures=[(str(t),e) for t,e in result.failures],
                errors=[(str(t),e) for t,e in result.errors],passed=result.wasSuccessful(),
                real_cpio_written=False,synthetic_only=True)
    (OUT/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
