import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('runner_v3',Path(__file__).with_name('run_observer_once.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

SNAPSHOT_FLAGS = ('all_other_raw_records_byte_identical','original_order_preserved',
    'both_original_trailer_records_byte_identical','appfw_launcher_observer_shim_backup_unchanged')
OBSERVER_FLAGS = ('all_other_payloads_and_headers_identical','original_order_preserved',
    'original_post_trailer_records_preserved')


class ProofSchemaChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)

    def raw(self,name,data):
        p = self.root/name
        p.write_bytes(data)
        return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

    def js(self,name,data):
        return self.raw(name,(json.dumps(data,sort_keys=True)+'\n').encode())

    def fixture(self,snapshot_edit=None,parent_edit=None,parent_proof_edit=None):
        base_cpio = self.raw('base.cpio.fixture',b'actual base bytes')
        parent_cpio = self.raw('observer.cpio.fixture',b'actual observer bytes')
        child_cpio = self.raw('snapshot.cpio.fixture',b'actual snapshot bytes')
        base_manifest = self.raw('base-manifest.fixture',b'base manifest fixture')
        base = {'initrd':base_cpio}
        for key in ('kernel','dtb','backup','fx3_platform','model_env','owner_baseline'):
            base[key] = {'fixture':key}
        oldproof = {'schema':'fx6-observer-only-member-diff-v1','baseline':base_cpio,
                    'candidate':parent_cpio,**{k:True for k in OBSERVER_FLAGS}}
        if parent_proof_edit:
            parent_proof_edit(oldproof)
        parent_proof = self.js('observer-proof.json',oldproof)
        parent = {**base,'initrd':parent_cpio,'input_member_diff_verification':parent_proof,
                  'baseline_manifest':base_manifest,'baseline_initrd':base_cpio}
        if parent_edit:
            parent_edit(parent)
        parent_ref = self.js('observer-manifest.json',parent)
        proof = copy.deepcopy({'schema':'fx6-wait-snapshot-member-diff-v1','parent_observer_cpio':parent_cpio,
                 'derived_cpio':child_cpio,**{k:True for k in SNAPSHOT_FLAGS}})
        if snapshot_edit:
            snapshot_edit(proof)
        proof_ref = self.js('snapshot-proof.json',proof)
        child = {**base,'initrd':child_cpio,'input_member_diff_verification':proof_ref,
            'baseline_manifest':base_manifest,'baseline_initrd':base_cpio,
            'parent_observer_manifest':parent_ref,'parent_observer_initrd':parent_cpio}
        pins = {'PARENT_OBSERVER_SHA':parent_ref['sha256'],'PARENT_CPIO_SHA':parent_cpio['sha256'],
                'PARENT_PROOF_SHA':parent_proof['sha256']}
        return child,base,parent,oldproof,pins

    def verify(self,fixture):
        child,base,_,_,pins = fixture
        with patch.multiple(runner,**pins):
            runner.verify_member_proof(child,base)

    def test_accepts_snapshot_full_parent_chain_and_original_observer(self):
        f = self.fixture()
        self.verify(f)
        _,base,parent,_,_ = f
        runner.verify_member_proof(parent,base)

    def test_each_snapshot_flag_requires_literal_true(self):
        for key in SNAPSHOT_FLAGS:
            for bad in [False,None,1,'true']:
                with self.subTest(key=key,bad=bad):
                    f = self.fixture(snapshot_edit=lambda d,k=key,v=bad:d.update({k:v}))
                    with self.assertRaisesRegex(RuntimeError,'snapshot required proof flags'):
                        self.verify(f)
            f = self.fixture(snapshot_edit=lambda d,k=key:d.pop(k))
            with self.assertRaisesRegex(RuntimeError,'snapshot required proof flags'):
                self.verify(f)

    def test_unknown_or_missing_schema_rejected(self):
        for edit in [lambda d:d.update(schema='future-schema'),lambda d:d.pop('schema')]:
            with self.subTest(edit=edit):
                with self.assertRaisesRegex(RuntimeError,'unknown member proof schema'):
                    self.verify(self.fixture(snapshot_edit=edit))

    def test_derived_cpio_must_equal_manifest(self):
        f = self.fixture(snapshot_edit=lambda d:d['derived_cpio'].update(sha256='0'*64))
        with self.assertRaisesRegex(RuntimeError,'snapshot derived CPIO references disagree'):
            self.verify(f)

    def test_parent_cpio_must_equal_both_references(self):
        f = self.fixture(snapshot_edit=lambda d:d['parent_observer_cpio'].update(sha256='0'*64))
        with self.assertRaisesRegex(RuntimeError,'snapshot parent CPIO references disagree'):
            self.verify(f)

    def test_parent_actual_cpio_tampering_rejected(self):
        f = self.fixture()
        Path(f[0]['parent_observer_initrd']['path']).write_bytes(b'changed parent content')
        with self.assertRaisesRegex(RuntimeError,'parent observer CPIO actual file changed'):
            self.verify(f)

    def test_parent_manifest_pinned_sha_not_replaceable(self):
        f = self.fixture()
        f[0]['parent_observer_manifest']['sha256'] = '0'*64
        with self.assertRaisesRegex(RuntimeError,'parent observer manifest pinned SHA mismatch'):
            self.verify(f)

    def test_missing_parent_reference_and_proof_rejected(self):
        f = self.fixture()
        del f[0]['parent_observer_manifest']
        with self.assertRaisesRegex(RuntimeError,'parent observer manifest reference missing fields'):
            self.verify(f)
        f = self.fixture(parent_edit=lambda d:d.pop('input_member_diff_verification'))
        with self.assertRaisesRegex(RuntimeError,'parent observer proof reference missing fields'):
            self.verify(f)

    def test_parent_original_schema_and_flags_checked(self):
        with self.assertRaisesRegex(RuntimeError,'unknown observer member proof schema'):
            self.verify(self.fixture(parent_proof_edit=lambda d:d.update(schema='unknown')))
        for key in OBSERVER_FLAGS:
            with self.subTest(key=key):
                with self.assertRaisesRegex(RuntimeError,'observer required proof flags'):
                    self.verify(self.fixture(parent_proof_edit=lambda d,k=key:d.pop(k)))

    def test_parent_frozen_baseline_fields_checked(self):
        for key in ('kernel','dtb','backup','fx3_platform','model_env','owner_baseline'):
            with self.subTest(key=key):
                with self.assertRaisesRegex(RuntimeError,'parent observer unexpected baseline change'):
                    self.verify(self.fixture(parent_edit=lambda d,k=key:d.update({k:{'changed':True}})))

    def test_child_actual_cpio_tampering_rejected(self):
        f = self.fixture()
        Path(f[0]['initrd']['path']).write_bytes(b'changed child content')
        with self.assertRaisesRegex(RuntimeError,'snapshot derived CPIO actual file changed'):
            self.verify(f)


if __name__ == '__main__':
    unittest.main()
