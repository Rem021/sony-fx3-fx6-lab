import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('owned_runner',Path(__file__).with_name('run_observer_once.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class QMPChecks(unittest.TestCase):
    def test_single_reader_events_errors_and_close(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as name:
            root=Path(name).resolve();server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            old=Path.cwd()
            try: os.chdir(root);server.bind('q')
            finally: os.chdir(old)
            server.listen(1);faults=[]
            def peer():
                try:
                    conn,_=server.accept();reader=conn.makefile('rb')
                    conn.sendall(b'{"QMP":{"version":{}}}\r\n')
                    one=json.loads(reader.readline());self.assertEqual(one['execute'],'first')
                    conn.sendall((json.dumps({'event':'STOP'})+'\r\n'+json.dumps({'return':{'ok':True},'id':one['id']})+'\r\n').encode())
                    two=json.loads(reader.readline());self.assertEqual(two['id'],one['id']+1)
                    conn.sendall((json.dumps({'error':{'class':'TestError'},'id':two['id']})+'\r\n').encode())
                    reader.readline();reader.close();conn.close()
                except BaseException as exc: faults.append(exc)
                finally:server.close()
            thread=threading.Thread(target=peer,daemon=True);thread.start()
            q=runner.QMP(root)
            self.assertEqual(q.call('first'),{'ok':True})
            with self.assertRaisesRegex(RuntimeError,'TestError'):q.call('second')
            with self.assertRaisesRegex(RuntimeError,'QMP closed'):q.call('third')
            q.close();thread.join(3)
            self.assertFalse(thread.is_alive());self.assertEqual(faults,[])


if __name__=='__main__':unittest.main()
