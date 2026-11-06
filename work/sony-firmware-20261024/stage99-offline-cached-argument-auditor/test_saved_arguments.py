#!/usr/bin/env python3
"""Adversarial synthetic checks; no Windows or device process is started."""
import ast,contextlib,copy,hashlib,io,json,tempfile,unittest
from pathlib import Path
import audit_saved_arguments as a

HERE=Path(__file__).resolve().parent
ID=r'USB\VID_054C&PID_0DA1\AUDIT_SYNTHETIC_SECRET_COMPONENT'
REC={'capture_kind':'native_argv','program':r'C:\Windows\System32\pnputil.exe',
    'argv':['/enum-devices','/connected','/instanceid',ID,'/relations']}


class SavedArgumentTests(unittest.TestCase):
    def test_ascii_case_and_hash_contract(self):
        j=a.audit(ID.lower(),ID,REC)
        self.assertEqual(j['status'],'MATCH_WITHIN_PROVIDED_RECORDS')
        self.assertEqual(j['cim_id']['uppercase_utf8_sha256'],hashlib.sha256(ID.upper().encode('utf-8')).hexdigest())
        self.assertEqual(j['recorded_argument']['backslash_count'],2)

    def test_json_serialization_is_decoded_once(self):
        decoded=json.loads(json.dumps({'instance_id':ID}))['instance_id']
        self.assertEqual(a.audit(decoded,decoded,REC)['status'],'MATCH_WITHIN_PROVIDED_RECORDS')
        self.assertEqual(decoded.count('\\'),2)

    def test_actually_doubled_slashes_are_not_unescaped(self):
        rec=copy.deepcopy(REC);rec['argv'][3]=ID.replace('\\','\\\\')
        self.assertEqual(a.audit(ID,ID,rec)['status'],'MISMATCH_RECORDED_NATIVE_ARGUMENT')
        j=a.audit(rec['argv'][3],rec['argv'][3],rec)
        self.assertEqual(j['status'],'MATCH_BUT_IDENTIFIER_SHAPE_REQUIRES_REVIEW')

    def test_whitespace_and_literal_quotes_preserved(self):
        for value in (' '+ID,ID+' ', '"'+ID+'"',"'"+ID+"'"):
            with self.subTest(kind=len(value)):
                rec=copy.deepcopy(REC);rec['argv'][3]=value
                self.assertEqual(a.audit(ID,ID,rec)['status'],'MISMATCH_RECORDED_NATIVE_ARGUMENT')

    def test_cim_and_root_mismatch_is_not_hidden_by_missing_argv(self):
        self.assertEqual(a.audit(ID,ID+'X',{})['status'],'MISMATCH_CIM_AND_SELECTED_ROOT_RECORDS')

    def test_non_ascii_does_not_claim_dotnet_equivalence(self):
        value=ID+'ß';rec=copy.deepcopy(REC);rec['argv'][3]=value
        self.assertEqual(a.audit(value,value,rec)['status'],'UNKNOWN_NON_ASCII_NORMALIZATION')

    def test_display_command_or_wql_is_not_native_argv(self):
        for rec in ({'command_public':'pnputil /enum-devices /instanceid '+ID},
                    {'server_side_filter':"PNPDeviceID LIKE 'USB\\\\VID_054C%'"},
                    {'capture_kind':'shell_commandline','program':REC['program'],'argv':REC['argv']}):
            self.assertEqual(a.audit(ID,ID,rec)['status'],'UNKNOWN_MISSING_NATIVE_ARGV_OR_SOURCE')

    def test_shell_program_is_not_pnputil_capture(self):
        rec=copy.deepcopy(REC);rec['program']='powershell.exe'
        self.assertEqual(a.audit(ID,ID,rec)['status'],'UNKNOWN_MISSING_NATIVE_ARGV_OR_SOURCE')

    def test_hardware_id_filter_does_not_prove_instance_binding(self):
        rec=copy.deepcopy(REC);rec['argv'][2]='/deviceid'
        j=a.audit(ID,ID,rec)
        self.assertEqual(j['argument_record']['syntax'],'HARDWARE_OR_COMPATIBLE_ID_FILTER_NOT_INSTANCE_ID')
        self.assertFalse(j['recorded_argument']['available'])

    def test_tree_root_is_positional(self):
        rec=copy.deepcopy(REC);rec['argv']=['/enum-devicetree',ID,'/connected','/drivers']
        self.assertEqual(a.audit(ID,ID,rec)['status'],'MATCH_WITHIN_PROVIDED_RECORDS')
        rec['argv']=['/enum-devicetree','/instanceid',ID]
        self.assertEqual(a.audit(ID,ID,rec)['argument_record']['syntax'],'DEVICE_TREE_ROOT_MUST_BE_POSITIONAL')

    def test_ambiguous_or_missing_instance_value(self):
        for argv in (['/enum-devices','/instanceid'],['/enum-devices','/instanceid','/connected'],
                     ['/enum-devices','/instanceid',ID,'/instanceid',ID]):
            rec=copy.deepcopy(REC);rec['argv']=argv
            self.assertTrue(a.audit(ID,ID,rec)['status'].startswith('UNKNOWN'))

    def test_other_command_or_extra_filter_does_not_get_match(self):
        for argv in (['/remove-device',ID],['/scan-devices','/instanceid',ID],
                     ['/enum-devices','/instanceid',ID,'/class','disk'],
                     ['/enum-devices','/instanceid',ID,'extra']):
            rec=copy.deepcopy(REC);rec['argv']=argv
            self.assertTrue(a.audit(ID,ID,rec)['status'].startswith('UNKNOWN'))

    def test_public_report_never_echoes_identifier(self):
        for rec in (REC,{},dict(REC,argv=['/enum-devices','/instanceid',ID+'X'])):
            text=json.dumps(a.audit(ID,ID,rec))
            self.assertNotIn('AUDIT_SYNTHETIC_SECRET_COMPONENT',text)
            self.assertNotIn('actual_device_serial',text)

    def test_json_pointer_escape_and_array(self):
        doc={'a/b':[{'~key':ID}]}
        self.assertEqual(a.pointer(doc,'/a~1b/0/~0key'),ID)
        with self.assertRaises(ValueError):a.pointer(doc,'/bad~2')
        with self.assertRaises(ValueError):a.pointer(doc,'/a~1b/01')

    def test_file_workflow_and_output_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='audit-fixture-') as temp:
            root=Path(temp);paths=[]
            for name,value in (('cim.json',{'instance_id':ID}),('root.json',{'instance_id':ID}),('receipt.json',REC)):
                p=root/name;p.write_text(json.dumps(value));paths.append(p)
            hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            out=root/'report.json';argv=['--project-root',str(root),'--cim',str(paths[0]),'--selected-root',str(paths[1]),'--receipt',str(paths[2]),'--output',str(out)]
            stdout=io.StringIO()
            with contextlib.redirect_stdout(stdout):self.assertEqual(a.main(argv),0)
            self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],hashes)
            raw=out.read_bytes();self.assertNotIn(b'SYNTHETIC_SECRET',raw)
            with contextlib.redirect_stdout(stdout):self.assertEqual(a.main(argv),2)
            self.assertEqual(out.read_bytes(),raw)
            self.assertNotIn('SYNTHETIC_SECRET',stdout.getvalue())

    def test_utf16_json_from_windows_style_file(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='audit-utf-fixture-') as temp:
            root=Path(temp);p=root/'cim.json'
            p.write_bytes(json.dumps({'instance_id':ID}).encode('utf-16'))
            doc,metadata=a.read_json(root,p)
            self.assertEqual(doc['instance_id'],ID)
            self.assertEqual(metadata['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())

    def test_link_outside_root_and_directory_inputs_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='audit-path-fixture-') as temp:
            outer=Path(temp);root=outer/'project';root.mkdir();target=outer/'outside.json';target.write_text('{}')
            link=root/'link.json';link.symlink_to(target)
            with self.assertRaises(ValueError):a.read_json(root,link)
            with self.assertRaises(ValueError):a.read_json(root,target)
            with self.assertRaises(ValueError):a.read_json(root,root)
            with self.assertRaises(ValueError):a.checked_path(root,root/'..'/'outside.json')

    def test_no_device_process_or_network_execution_imports(self):
        tree=ast.parse((HERE/'audit_saved_arguments.py').read_text())
        imports={n.names[0].name for n in ast.walk(tree) if isinstance(n,ast.Import)}
        self.assertEqual(imports,{'argparse','hashlib','json','os','re','stat'})
        self.assertNotIn('subprocess',(HERE/'audit_saved_arguments.py').read_text())
        forbidden={'system','popen','spawnl','spawnv','execv','execve','startfile'}
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in forbidden for n in ast.walk(tree)))


if __name__=='__main__':
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(SavedArgumentTests)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'synthetic_inputs_only':True,'device_queries_or_child_processes':False,'details':stream.getvalue()}
    path=HERE/'synthetic-test-results.json'
    with path.open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2);handle.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='details'}))
    if not result.wasSuccessful():print(stream.getvalue())
    raise SystemExit(not result.wasSuccessful())
