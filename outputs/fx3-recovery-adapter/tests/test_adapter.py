"""Real old FX3 image roundtrips plus meaningful fail-closed/rollback fault tests."""
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
import json
import os
import struct
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent.parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from fx3_recovery import engine as E
from fx3_recovery.files import read_file,new_directory,encode,check_volume
from fx3_recovery.fat import FatP1,MAX_P1
from fx3_recovery.squash import inflate_bounded

RUN=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work/sony-firmware-20261024/stage185-fx3-offline-recovery-adapter/runs/tests'
sys.argv=sys.argv[:1]
REFERENCES=ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine'


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume();RUN.mkdir(mode=0o700,exist_ok=False)
        cls.images={v:read_file(REFERENCES/v/'nflasha1',MAX_P1) for v in ('2.04','2.05')}
        cls.before={v:E.sha(b) for v,b in cls.images.items()}
        cls.bundles={}
        for version in cls.images:
            out=RUN/('bundle-'+version)
            E.create_bundle(REFERENCES/version/'nflasha1',out)
            cls.bundles[version]=out

    def fixture(self,name,raw):
        parent=RUN/name
        new_directory(parent,{'input.p1':raw})
        return parent/'input.p1'

    def test_real_two_version_build_and_exact_inverse(self):
        for version,out in self.bundles.items():
            with self.subTest(version=version):
                m,source,candidate=E.load_bundle(out)
                self.assertNotEqual(source,candidate)
                self.assertFalse(m['flashable']);self.assertFalse(m['current_body_p1_identity_verified'])
                self.assertEqual(len(m['transformation']['groups']),2)
                restored=RUN/('restored-'+version)
                receipt=E.rollback(out,out/'candidate.p1',restored)
                self.assertTrue(receipt['byte_identical_to_backup'])
                self.assertEqual(read_file(restored/'restored.p1',MAX_P1),self.images[version])
                self.assertEqual(E.diagnose(out,out/'candidate.p1')['state'],'CANDIDATE')
                self.assertEqual(E.diagnose(out,out/'source.p1')['state'],'ORIGINAL')

    def test_fx3_specific_sites_and_model_region_preserved(self):
        m,source,candidate=E.load_bundle(self.bundles['2.05'])
        fat=FatP1(candidate);fs=E.SquashFS(fat.contents(E.INITRD));rows={r['path']:r for r in fs.walk()}
        sd=fs.contents(rows['/usr/lib/libsdfileinputupdaterapi.so'])
        self.assertEqual(sd[0x9fd4:0x9fdc],bytes.fromhex('20008052c0035fd6'))
        self.assertEqual(sd[0xabf0:0xabf8],bytes.fromhex('00008052c0035fd6'))
        oldfs=E.SquashFS(FatP1(source).contents(E.INITRD));oldrows={r['path']:r for r in oldfs.walk()}
        old=oldfs.contents(oldrows['/usr/lib/libsdfileinputupdaterapi.so'])
        self.assertEqual(sd[0xa004:0xa02c],old[0xa004:0xa02c])
        self.assertEqual(sd[0xa0cc:0xa0d4],old[0xa0cc:0xa0d4]) # A7CII location is not patched.
        self.assertEqual(sd[0xace8:0xacf0],old[0xace8:0xacf0])

    def test_repeated_output_and_original_path_refused(self):
        path=REFERENCES/'2.05/nflasha1';before=E.sha(read_file(path,MAX_P1))
        with self.assertRaises(FileExistsError):E.create_bundle(path,self.bundles['2.05'])
        with self.assertRaises(FileExistsError):E.create_bundle(path,path)
        self.assertEqual(E.sha(read_file(path,MAX_P1)),before)

    def test_unknown_body_and_foreign_source_scope_rejected(self):
        raw=self.images['2.05']
        with self.assertRaises(ValueError):E.binding('reference',raw,'1'*64)
        with self.assertRaises(ValueError):E.binding('unverified-snapshot',raw,'1'*64)
        full=raw+b'\xff'*(MAX_P1-len(raw))
        path=self.fixture('synthetic-full-snapshot',full)
        out=RUN/'snapshot-bundle'
        E.create_bundle(path,out,'unverified-snapshot','1'*64)
        m,source,candidate=E.load_bundle(out)
        self.assertIsNone(m['inspection']['recognized_reference'])
        self.assertFalse(m['binding']['camera_verified'])
        self.assertEqual(source[len(raw):],candidate[len(raw):])
        with self.assertRaises(ValueError):E.binding('reference',full,None)
        with self.assertRaises(ValueError):E.binding('unverified-snapshot',full,'RAW-SERIAL')

    def test_fat_copy_mismatch_cycle_and_crosslink(self):
        source=self.images['2.05'];f=FatP1(source)
        broken=bytearray(source);broken[512+19]^=1
        with self.assertRaises(ValueError):E.inspect_image(bytes(broken))
        # Encode a self-cycle in both FAT copies; it must not loop.
        cluster=f.files[E.INITRD]['clusters'][0]
        broken=bytearray(source)
        for start in (512,512+16384):
            at=start+cluster+cluster//2;word=struct.unpack_from('<H',broken,at)[0]
            word=(word&0x000f)|(cluster<<4) if cluster&1 else (word&0xf000)|cluster
            struct.pack_into('<H',broken,at,word)
        with self.assertRaises(ValueError):FatP1(bytes(broken))
        # Repoint initrd to the existing kernel chain without modifying FAT data.
        broken=bytearray(source);at=source.find(b'INITRD  IMG')
        self.assertGreater(at,0)
        struct.pack_into('<H',broken,at+26,f.files[E.KERNEL]['clusters'][0])
        with self.assertRaises(ValueError):FatP1(bytes(broken))

    def test_long_name_checksum_and_short_image_rejected(self):
        source=self.images['2.05'];at=next(i for i in range(33280,33280+16384,32) if source[i+11]==15)
        broken=bytearray(source);broken[at+13]^=1
        with self.assertRaises(ValueError):FatP1(bytes(broken))
        with self.assertRaises(ValueError):FatP1(source[:1024])

    def test_invalid_boot_checksum(self):
        raw=self.images['2.05'];fat=FatP1(raw);bad=bytearray(raw)
        at=fat.mapping(E.CHECKSUM)[0][0];bad[at]=ord('0') if bad[at]!=ord('0') else ord('1')
        with self.assertRaises(ValueError):E.inspect_image(bytes(bad))

    def test_bad_or_already_modified_library_rejected(self):
        m,source,candidate=E.load_bundle(self.bundles['2.05'])
        report=E.inspect_image(candidate)
        self.assertFalse(report['component_profile_match'])
        with self.assertRaises(ValueError):E.block_groups(candidate)
        with self.assertRaises(ValueError):E.verify_derivative(candidate,source)

    def test_decompression_bomb_and_trailing_stream_rejected(self):
        import zlib
        with self.assertRaises(ValueError):inflate_bounded(zlib.compress(bytes(1000000)),8192)
        with self.assertRaises(ValueError):inflate_bounded(zlib.compress(b'legitimate')+b'trailing',8192)
        with self.assertRaises(ValueError):E.pack_same_size(b'x'*256,1)

    def test_mixed_and_unknown_images_not_automatically_rolled_back(self):
        out=self.bundles['2.05'];m,source,candidate=E.load_bundle(out)
        mixed=bytearray(source);span=m['transformation']['spans'][0];a,n=span['offset'],span['bytes'];mixed[a:a+n]=candidate[a:a+n]
        path=self.fixture('mixed',bytes(mixed))
        self.assertEqual(E.diagnose(out,path)['state'],'MIXED_KNOWN_SPANS')
        with self.assertRaises(ValueError):E.rollback(out,path,RUN/'mixed-denied')
        bad=bytearray(candidate);bad[0]^=1
        path=self.fixture('unknown',bytes(bad))
        self.assertEqual(E.diagnose(out,path)['state'],'UNKNOWN_BYTES')
        with self.assertRaises(ValueError):E.rollback(out,path,RUN/'unknown-denied')
        self.assertFalse((RUN/'mixed-denied').exists());self.assertFalse((RUN/'unknown-denied').exists())

    def test_tampered_manifest_images_and_false_live_flags(self):
        out=self.bundles['2.05'];m,source,candidate=E.load_bundle(out)
        for label,change in [('live',lambda x:x.update(flashable=True)),('body',lambda x:x.update(current_body_p1_identity_verified=True)),
                             ('hash',lambda x:x.update(candidate_sha256='0'*64)),
                             ('span',lambda x:x['transformation']['spans'][0].update(offset=0))]:
            obj=json.loads(encode(m));change(obj);p=RUN/('tampered-'+label)
            new_directory(p,{'source.p1':source,'candidate.p1':candidate,'manifest.json':encode(obj)})
            with self.assertRaises(ValueError):E.load_bundle(p)
        obj=json.loads(encode(m));p=RUN/'duplicate-json'
        text=encode(obj).decode().replace('"flashable": false','"flashable": false, "flashable": false',1)
        new_directory(p,{'source.p1':source,'candidate.p1':candidate,'manifest.json':text.encode()})
        with self.assertRaises(ValueError):E.load_bundle(p)

    def test_symlinks_devices_and_interrupted_bundle(self):
        path=RUN/'symlink-input';os.symlink(REFERENCES/'2.05/nflasha1',path)
        with self.assertRaises(ValueError):read_file(path,MAX_P1)
        with self.assertRaises(ValueError):read_file('/dev/null',MAX_P1)
        out=RUN/'partial-bundle'
        new_directory(out,{'source.p1':self.images['2.05']})
        with self.assertRaises(OSError):E.load_bundle(out)
        self.assertTrue((out/'source.p1').exists()) # Failure evidence is retained.

    def test_cli_and_optimized_mode_do_not_open_live_backend(self):
        env=dict(os.environ);env['PYTHONPATH']=str(HERE)
        r=subprocess.run([sys.executable,'-B','-m','fx3_recovery','verify','--bundle',str(self.bundles['2.05'])],
                         env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(json.loads(r.stdout)['flashable'])
        r=subprocess.run([sys.executable,'-B','-m','fx3_recovery','--flash'],env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode,2)
        code='from fx3_recovery.fat import FatP1; FatP1(bytes(512))'
        r=subprocess.run([sys.executable,'-O','-B','-c',code],env=env,capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertIn('ValueError',r.stderr)

    @classmethod
    def tearDownClass(cls):
        for version in cls.images:
            if E.sha(read_file(REFERENCES/version/'nflasha1',MAX_P1))!=cls.before[version]:
                raise AssertionError('original Sony reference mutated')


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'status':'PASS_OFFLINE_FX3_IMAGE_ADAPTATION' if result.wasSuccessful() else 'FAIL',
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'original_references_unchanged':AdapterTests.before,
            'real_reference_versions':['2.04','2.05'],'current_7_02_camera_image_tested':False,
            'source_sha256':{str(p.relative_to(HERE)):sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'fx3_recovery').glob('*.py'))},
            'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'new_camera_or_USB_operations':0}
    new_directory(RUN/'test-receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
