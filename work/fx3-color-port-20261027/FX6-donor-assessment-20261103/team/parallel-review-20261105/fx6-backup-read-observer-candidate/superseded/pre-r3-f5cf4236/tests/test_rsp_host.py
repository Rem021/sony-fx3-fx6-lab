#!/usr/bin/env python3
"""Real-socket tests of the actual strict RSP class; no QEMU."""
import importlib.util,json,socket,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('rsp',HERE/'observer/rsp_readonly.py');rsp=importlib.util.module_from_spec(spec);spec.loader.exec_module(rsp)
checks=[]
def check(n,f):f();checks.append(n)
def server_once(actions):
 a,b=socket.socketpair();a.settimeout(.5);b.settimeout(.5);errs=[]
 def run():
  try:
   assert b.recv(1)==b'$';raw=b''
   while True:
    c=b.recv(1)
    if c==b'#':break
    raw+=c
   tail=b.recv(2)
   actions(b,raw,tail)
  except BaseException as e:errs.append(repr(e))
  finally:
   try:b.close()
   except:pass
 t=threading.Thread(target=run);t.start();return a,t,errs
def ok_packet(s):return b'+$OK#'+f'{sum(b"OK")&255:02x}'.encode()
def invalid_checksum():
 a,t,e=server_once(lambda b,raw,tail:(b.sendall(b'+$OK#00'),b.recv(1)))
 r=rsp.RSP(a)
 try:
  try:r.command('Qqemu.PhyMemMode:1')
  except ValueError as x:assert 'checksum' in str(x)
  else:raise AssertionError('bad checksum accepted')
 finally:r.close();t.join(2)
 assert not e,e
check('invalid_checksum_+$OK#00_rejected',invalid_checksum)
def missing_checksum():
 a,t,e=server_once(lambda b,raw,tail:(b.sendall(b'+$OK#'),b.close()))
 r=rsp.RSP(a)
 try:
  try:r.command('Qqemu.PhyMemMode:1')
  except (ConnectionError,ValueError,TimeoutError):pass
  else:raise AssertionError('missing checksum accepted')
 finally:r.close();t.join(2)
check('missing_checksum_EOF_rejected',missing_checksum)
def fragmented_merged():
 a,t,e=server_once(lambda b,raw,tail:(b.sendall(b'+'),b.sendall(b'$O'),b.sendall(b'K#'),b.sendall(f'{sum(b"OK")&255:02x}'.encode()),b.recv(1)))
 r=rsp.RSP(a)
 try:assert r.command('Qqemu.PhyMemMode:1')=='OK'
 finally:r.close();t.join(2)
 assert not e,e
check('fragmented_packet_and_leading_ack',fragmented_merged)
def async_stop_console():
 def act(b,raw,tail):
  b.sendall(b'+'+b'$O4f4b#'+f'{sum(b"O4f4b")&255:02x}'.encode());b.recv(1)
  b.sendall(b'+$T05thread:1;#'+f'{sum(b"T05thread:1;")&255:02x}'.encode());b.recv(1)
  b.sendall(ok_packet(b));b.recv(1)
 a,t,e=server_once(act);r=rsp.RSP(a)
 try:assert r.command('Qqemu.PhyMemMode:1')=='OK';assert r.stops==['T05thread:1;']
 finally:r.close();t.join(2)
 assert not e,e
check('console_O_and_async_T_handled',async_stop_console)
def duplicate_thread():
 a,b=socket.socketpair();b.settimeout(.2)
 r=rsp.RSP(a)
 try:
  try:r.select_thread('T05thread:1;thread:2;')
  except ValueError as x:assert 'exactly one' in str(x)
  else:raise AssertionError('duplicate thread accepted')
 finally:r.close();b.close()
check('duplicate_T05_thread_rejected',duplicate_thread)
def unique_hex_thread():
 a,b=socket.socketpair();b.settimeout(.2)
 def srv():
  for want in (b'Hgp1.2',b'Hcp1.2'):
   assert b.recv(1)==b'$';raw=b''
   while True:
    c=b.recv(1)
    if c==b'#':break
    raw+=c
   b.recv(2);b.sendall(ok_packet(b));b.recv(1)
  b.close()
 t=threading.Thread(target=srv);t.start();r=rsp.RSP(a)
 try:assert r.select_thread('T05thread:p1.2;')=='p1.2'
 finally:r.close();t.join(2)
check('unique_hex_pPID_TID_accepted',unique_hex_thread)
def timeout():
 a,b=socket.socketpair();b.settimeout(.2)
 def srv():
  assert b.recv(1)==b'$';time.sleep(.25);b.close()
 t=threading.Thread(target=srv);t.start();r=rsp.RSP(a)
 try:
  try:r.command('Qqemu.PhyMemMode:1',timeout=.05)
  except (TimeoutError,ConnectionError):pass
  else:raise AssertionError('silent RSP accepted')
 finally:r.close();t.join(2)
check('timeout_rejected',timeout)
out={'status':'PASS_NO_QEMU_REAL_SOCKET','fixture':'real RSP class over socketpair; no QEMU/guest','cases':checks,'count':len(checks),'rsp_sha256':__import__('hashlib').sha256((HERE/'observer/rsp_readonly.py').read_bytes()).hexdigest()}
(HERE/'tests/rsp-host-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
