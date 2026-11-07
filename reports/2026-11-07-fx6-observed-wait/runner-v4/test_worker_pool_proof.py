import copy
import difflib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import test_runner_proof_schema as old_tests

spec = importlib.util.spec_from_file_location('runner_v4',Path(__file__).with_name('run_observer_once.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
FLAGS = ('all_other_raw_records_byte_identical','original_order_preserved','both_original_trailer_records_byte_identical')
OFFSETS = ['0x12d824c','0x12d8250','0x12d8254','0x12d825c','0xc09e50']
SOURCE = '''/* fixture source */
static void fx6_patch_blocking_calls(void *real_init) {
    static const unsigned long offs[5] = {0x12d824cUL, 0x12d8250UL, 0x12d8254UL, 0x12d825cUL, 0xc09e50UL};
    for (int i = 0; i < 5; i++) {
        use(offs[i]);
    }
}
'''


def elf(text=b'old text'):
    names = b'\0.text\0.rodata\0.got.plt\0.bss\0.shstrtab\0'
    entries = [(b'.text',1,6,text),(b'.rodata',1,2,b'constant'),(b'.got.plt',1,3,b'got bytes'),(b'.bss',8,3,b'')]
    raw = bytearray(64)
    sections = [(0,0,0,0,0,0,0,0,0,0)]
    for name,typ,flags,data in entries:
        off = len(raw);raw.extend(data)
        sections.append((names.index(name),typ,flags,0x1000+off,off,16 if typ==8 else len(data),0,0,1,0))
    off = len(raw);raw.extend(names)
    sections.append((names.index(b'.shstrtab'),3,0,0,off,len(names),0,0,1,0))
    shoff = len(raw)
    for s in sections:raw.extend(struct.pack('<IIQQQQIIQQ',*s))
    raw[:16] = b'\x7fELF\x02\x01\x01'+b'\0'*9
    struct.pack_into('<HHI',raw,16,3,183,1)
    struct.pack_into('<Q',raw,40,shoff)
    struct.pack_into('<HHH',raw,58,64,len(sections),len(sections)-1)
    return bytes(raw)


def record(name,data,ino):
    n = name.encode()+b'\0'
    values = [ino,0o100755,0,0,1,0,len(data),0,0,0,0,len(n),0]
    raw = b'070701'+b''.join(f'{v:08x}'.encode() for v in values)+n
    raw += b'\0'*((-len(raw))%4)
    raw += data
    raw += b'\0'*((-len(raw))%4)
    return raw


def cpio(shim,init=b'unchanged init',trailer_ino=3):
    return (record('init',init,1)+record('usr/lib/libgrm-fbinit9.so',shim,2)+
        record('TRAILER!!!',b'',trailer_ino)+record('usr/bin/snapshot',b'unchanged helper',4)+record('TRAILER!!!',b'',5))


class WorkerProofChecks(unittest.TestCase):
    raw = old_tests.ProofSchemaChecks.raw
    js = old_tests.ProofSchemaChecks.js
    old_fixture = old_tests.ProofSchemaChecks.fixture

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)

    def fixture(self,proof_edit=None,source_edit=None,source_proof_edit=None,repro_text=None,extra_init=False,trailer_changed=False,diff_bad=False):
        snapshot,base,_,_,pins = self.old_fixture()
        old_shim = self.raw('baseline-shim.elf.fixture',elf())
        new_shim = self.raw('restored-shim.elf.fixture',elf(b'new text'))
        reproduced = self.raw('reproduced-shim.elf.fixture',elf(repro_text or b'old text')+b'nonallocated debug difference')
        parent_cpio = self.raw('snapshot.cpio.fixture',cpio(Path(old_shim['path']).read_bytes()))
        snapshot['initrd'] = parent_cpio
        old_snapshot_proof = json.loads(Path(snapshot['input_member_diff_verification']['path']).read_text())
        old_snapshot_proof['derived_cpio'] = parent_cpio
        snapshot['input_member_diff_verification'] = self.js('snapshot-proof.json',old_snapshot_proof)
        parent_manifest = self.js('snapshot-manifest.json',snapshot)
        child_cpio = self.raw('restored.cpio.fixture',cpio(Path(new_shim['path']).read_bytes(),b'changed init' if extra_init else b'unchanged init',99 if trailer_changed else 3))
        old_source = self.raw('baseline.c',SOURCE.encode())
        restored = SOURCE.replace('offs[5]','offs[4]').replace('0x12d825cUL, ','').replace('i < 5','i < 4')
        if source_edit:restored = source_edit(restored)
        new_source = self.raw('restored.c',restored.encode())
        udiff = ''.join(difflib.unified_diff(SOURCE.splitlines(True),restored.splitlines(True),fromfile='baseline.c',tofile='restored.c'))
        diff_ref = self.raw('source.diff',(udiff+('unexplained extra text\n' if diff_bad else '')).encode())
        repro = self.js('baseline-reproduction.json',{'schema':'fx6-worker-pool-baseline-reproduction-v1',
            'source':old_source,'actual_shim':old_shim,'reproduced_shim':reproduced,
            'sections_identical':True,'section_names':['.text','.rodata','.got','.got.plt','.bss']})
        build = self.js('build.json',{'schema':'fx6-worker-pool-shim-build-v1','source':new_source,'output':new_shim,'command':['fixture-compiler','-shared']})
        sp = {'schema':'fx6-worker-pool-source-change-v1','baseline_source':old_source,'restored_source':new_source,
            'source_diff':diff_ref,'baseline_shim':old_shim,'restored_shim':new_shim,'baseline_reproduction':repro,'build_receipt':build,
            'before_nop_offsets':OFFSETS,'after_nop_offsets':[x for x in OFFSETS if x!='0x12d825c'],
            'removed_nop_offsets':['0x12d825c'],'all_other_source_bytes_identical':True}
        if source_proof_edit:source_proof_edit(sp)
        source_ref = self.js('source-proof.json',sp)
        p = {'schema':'fx6-worker-pool-restore-member-diff-v1','parent_snapshot_manifest':parent_manifest,
            'parent_snapshot_cpio':parent_cpio,'derived_cpio':child_cpio,
            'changed_existing_members':['usr/lib/libgrm-fbinit9.so'],
            'changed_member_payload':{'before':{k:old_shim[k] for k in ('bytes','sha256')},'after':{k:new_shim[k] for k in ('bytes','sha256')}},
            'source_change_verification':source_ref,**{k:True for k in FLAGS}}
        if proof_edit:proof_edit(p)
        child = {**snapshot,'initrd':child_cpio,'mode':'worker-pool-restore','parent_snapshot_manifest':parent_manifest,
            'parent_snapshot_initrd':parent_cpio,'source_change_verification':source_ref,
            'input_member_diff_verification':self.js('worker-proof.json',p)}
        pins.update(PARENT_SNAPSHOT_SHA=parent_manifest['sha256'],PARENT_SNAPSHOT_CPIO_SHA=parent_cpio['sha256'])
        return child,base,pins

    def verify(self,f):
        child,base,pins=f
        with patch.multiple(runner,**pins):runner.verify_member_proof(child,base)

    def test_accepts_full_chain_one_shim_and_source_change_absent_got(self):
        self.verify(self.fixture())

    def test_rejects_any_other_or_missing_changed_member(self):
        for names in [[],['init'],['usr/lib/libgrm-fbinit9.so','init'],[{'member':'usr/lib/libgrm-fbinit9.so'}]]:
            with self.subTest(names=names):
                with self.assertRaisesRegex(RuntimeError,'must change only'):
                    self.verify(self.fixture(proof_edit=lambda d,n=names:d.update(changed_existing_members=n)))

    def test_worker_flags_literal_true_required(self):
        for key in FLAGS:
            for value in [False,1,'true',None]:
                with self.subTest(key=key,value=value):
                    with self.assertRaisesRegex(RuntimeError,'worker required proof flags'):
                        self.verify(self.fixture(proof_edit=lambda d,k=key,v=value:d.update({k:v})))

    def test_actual_nonshim_or_trailer_record_changes_rejected(self):
        for opts in [{'extra_init':True},{'trailer_changed':True}]:
            with self.subTest(opts=opts):
                with self.assertRaisesRegex(RuntimeError,'unexplained worker CPIO raw record change'):
                    self.verify(self.fixture(**opts))

    def test_unrelated_source_edit_rejected_even_with_matching_diff(self):
        with self.assertRaisesRegex(RuntimeError,'source changed beyond'):
            self.verify(self.fixture(source_edit=lambda s:s+'int unrelated=1;\n'))

    def test_bad_diff_or_wrong_offset_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'source diff does not match'):
            self.verify(self.fixture(diff_bad=True))
        with self.assertRaisesRegex(RuntimeError,'unexpected removed NOP'):
            self.verify(self.fixture(source_proof_edit=lambda d:d.update(removed_nop_offsets=['0xc09e50'])))

    def test_baseline_reproduction_recomputed_not_trusted(self):
        with self.assertRaisesRegex(RuntimeError,'reproduced ELF sections differ'):
            self.verify(self.fixture(repro_text=b'tampered baseline text'))

    def test_wrong_mode_and_parent_manifest_pin_rejected(self):
        f=self.fixture();f[0]['mode']='observer-only'
        with self.assertRaisesRegex(RuntimeError,'requires worker-pool-restore'):
            self.verify(f)
        f=self.fixture();f[2]['PARENT_SNAPSHOT_SHA']='0'*64
        with self.assertRaisesRegex(RuntimeError,'parent snapshot manifest pinned SHA mismatch'):
            self.verify(f)

    def test_payload_and_source_ref_binding_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'shim payload fingerprint mismatch'):
            self.verify(self.fixture(proof_edit=lambda d:d['changed_member_payload']['after'].update(sha256='0'*64)))
        f=self.fixture();f[0]['source_change_verification']=copy.deepcopy(f[0]['source_change_verification']);f[0]['source_change_verification']['sha256']='0'*64
        with self.assertRaisesRegex(RuntimeError,'worker source proof references disagree'):
            self.verify(f)


if __name__=='__main__':unittest.main()
