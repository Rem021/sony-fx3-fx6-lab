#!/usr/bin/env python3
"""Offline parser tests: strict block boundaries and producer source contract."""
import hashlib,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(HERE));import mapping_parser as M
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team');R6=TEAM/'parallel-review-20261105/runs/r6-stop-only-20261106T2005Z/run/serial.log';R66=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/runs/cp-bind-66ed0f78/serial.log';INIT=HERE/'work/cpio/init'
def cut(path,n):
 b=Path(path).read_bytes();return b''.join(b.splitlines(keepends=True)[:n])
def err(data,contract='official_im_elf'):
 try:M.select_appfw(data,producer_contract=contract)
 except M.MapParserError as e:return e
 raise AssertionError('expected rejection')
class ParserTests(unittest.TestCase):
 def test_source_contract(self):
  s=INIT.read_text();assert "grep '/usr/bin/im.elf' /proc/$im_pid/maps" in s;assert 'FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN' in s;assert 'cat /proc/uptime /proc/$im_pid/maps' in s
 def test_current_official_block_foreign(self):
  d=cut(R6,9222);e=err(d);self.assertEqual(e.code,'im_endmaps_source_is_imelf_only');self.assertEqual(e.block['begin_line'],8955);self.assertEqual(e.block['end_line'],9222);self.assertEqual(e.diagnostics['appfw_rows'],4);self.assertGreater(e.diagnostics['foreign_rows'],0)
 def test_current_active_and_full_end(self):
  for n in (9078,9081):self.assertEqual(err(cut(R6,n)).code,'newest_block_incomplete')
  e=err(Path(R6).read_bytes());self.assertEqual(e.code,'newest_block_incomplete');self.assertEqual(e.block['begin_line'],47959)
 def test_66ed_early_nested_and_end(self):
  for n in (8039,8041):self.assertEqual(err(cut(R66,n)).code,'newest_block_incomplete')
  m=M.select_appfw(cut(R66,8950));self.assertEqual(m['block_span'],[8029,8950]);self.assertEqual(hex(m['ap']['bias']),'0x7ed3ccc000');self.assertEqual(len(m['ap']['rows']),3);self.assertEqual(m['block']['nested_children'],1);bs,_=M.parse_map_blocks(cut(R66,8950));self.assertTrue(any(b['depth']>0 and b['overlap_with_previous'] for b in bs))
  e=err(Path(R66).read_bytes());self.assertEqual(e.code,'newest_block_incomplete');self.assertEqual(e.block['begin_line'],69489)
 def test_full_contract_synthetic(self):
  d=cut(R6,9222);m=M.select_appfw(d,producer_contract='full_proc_maps');self.assertEqual(m['block_span'],[8955,9222]);self.assertEqual(m['ap']['bias'],0x7efab5b000);self.assertEqual(len(m['ap']['rows']),4);self.assertEqual(m['producer_contract'],'full_proc_maps');self.assertEqual(len(m['static_words']),4);self.assertEqual([r['line'] for r in m['ap']['rows']],[9078,9079,9080,9081])
  loads=M.elf_loads(M.APP_ELF);self.assertEqual(len(loads),2);self.assertTrue(any('x' in r['perms'] for r in m['ap']['rows']));self.assertTrue(all(r['path']==M.AP_PATH.decode() for r in m['ap']['rows']))
 def test_negative_pid_end(self):
  d=cut(R6,9222).replace(b'FX3_AP_IM_ENDMAPS_239_END',b'FX3_AP_IM_ENDMAPS_238_END');self.assertIn(err(d).code,('newest_block_incomplete','im_endmaps_source_is_imelf_only','nested_block_incomplete'))
 def test_negative_missing_end(self):self.assertEqual(err(cut(R6,9221)).code,'newest_block_incomplete')
 def test_negative_nested(self):
  d=cut(R6,9222);d=d.replace(b'FX3_AP_IM_ENDMAPS_239_BEGIN',b'FX3_AP_EARLY_MAPS_239_9_BEGIN\nFX3_AP_IM_ENDMAPS_239_BEGIN',1);self.assertIn(err(d).code,('newest_block_incomplete','im_endmaps_source_is_imelf_only'))
 def test_negative_mixed_inode(self):
  d=cut(R6,9222);d=d.replace(b'7efab5b000-7efd45c000 r-xp 00000000 00:02 1048',b'7efab5b000-7efd45c000 r-xp 00000000 00:02 9999',1);e=err(d,'full_proc_maps');self.assertEqual(e.code,'mixed_inode')
 def test_negative_permissions(self):
  d=cut(R6,9222);d=d.replace(b'7efab5b000-7efd45c000 r-xp 00000000',b'7efab5b000-7efd45c000 rw-p 00000000',1);e=err(d,'full_proc_maps');self.assertIn(e.code,('nonexec_code','bad_bias'))
 def test_negative_offset(self):
  d=cut(R6,9222);d=d.replace(b'7efab5b000-7efd45c000 r-xp 00000000',b'7efab5b000-7efd45c000 r-xp 00001000',1);e=err(d,'full_proc_maps');self.assertEqual(e.code,'bad_bias')
 def test_negative_interval_gap(self):
  d=cut(R6,9222);d=b''.join(l for l in d.splitlines(keepends=True) if b'7efd46c000-7efda4c000 r--p 02901000' not in l);e=err(d,'full_proc_maps');self.assertIn(e.code,('coverage_gap','bad_bias'))
 def test_no_appfw(self):
  d=cut(R6,9222);lines=[l for l in d.splitlines(keepends=True) if b'/usr/lib/appFw.so' not in l];e=err(b''.join(lines),'full_proc_maps');self.assertEqual(e.code,'no_appfw')
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ParserTests);res=unittest.TextTestRunner(verbosity=1).run(suite);print(json.dumps({'tests':suite.countTestCases(),'failures':len(res.failures),'errors':len(res.errors)}));sys.exit(not res.wasSuccessful())
