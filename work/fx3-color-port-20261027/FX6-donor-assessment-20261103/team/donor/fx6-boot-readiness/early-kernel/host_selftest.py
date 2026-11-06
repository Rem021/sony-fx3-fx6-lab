#!/usr/bin/env python3
"""No-QEMU relative AF_UNIX check and immutable historical receipt addendum."""
import hashlib
import json
import os
import socket
import tempfile
from pathlib import Path

from fixed_runner import HERE,connect_relative,serial_observation

RUN=HERE/'runs/fixed-fx3-9581d529'
PIN_RECEIPT='18890489ebb215641b43213b380d7eb06367ffb5861a020f1d5254395910b921'
PIN_SERIAL='24b010d7d6aafb4fa84d5c34dec3b9d73bd93d88f40e9c8a0f2c23f01da005b3'
FX3_SERIAL=HERE.parents[6]/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2gapinternal-47e2924a/serial.log'
FX3_SERIAL_SHA='8157737391d2d8e3acf46790312826b0084539bda82e2bbe228bc1f1d6f1d16b'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cwd=Path.cwd()
    with tempfile.TemporaryDirectory(prefix='socket-check-',dir=HERE) as tmp_name:
        path=Path(tmp_name)
        absolute_length=len(str(path/'q').encode())
        if absolute_length<=104:raise ValueError('not a long AF_UNIX path test')
        server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            os.chdir(path)
            try:server.bind('q');server.listen(1)
            finally:os.chdir(cwd)
            connect_relative(client,path)
            peer,_=server.accept()
            try:client.sendall(b'host-only');received=peer.recv(32)
            finally:peer.close()
            if received!=b'host-only' or Path.cwd()!=cwd:raise ValueError('relative socket connect failed')
        finally:
            client.close();server.close()
    receipt_path=RUN/'run-receipt.json';serial_path=RUN/'serial.log'
    if sha(receipt_path)!=PIN_RECEIPT or sha(serial_path)!=PIN_SERIAL:raise ValueError('historical run changed')
    prior=json.loads(receipt_path.read_text())
    observation=serial_observation(serial_path.read_bytes())
    if prior['linux_version_marker'] is not False or observation['linux_version_line'] is None:
        raise ValueError('prior boolean mismatch not reproduced')
    if sha(FX3_SERIAL)!=FX3_SERIAL_SHA:raise ValueError('pinned FX3 serial changed')
    baseline_observation=serial_observation(FX3_SERIAL.read_bytes())
    if baseline_observation['init_boundary_line']!='FX3_DEVTMPFS_RC=0':raise ValueError('original FX3 init marker not parsed')
    if baseline_observation['first_module_line']!='FX3_INSMOD_RC_/kmod/devno.ko=0':raise ValueError('original FX3 first module marker not parsed')
    if observation['init_boundary_line'] is not None:raise ValueError('early FX6 run unexpectedly reached init')
    return {'status':'PASS_HOST_ONLY','af_unix_relative_socket':{'absolute_path_utf8_bytes':absolute_length,'received':received.decode(),'cwd_restored':True,'qemu_started':False,'runtime_locks_acquired':False},'existing_run_addendum':{'run_receipt_path':str(receipt_path),'run_receipt_sha256':PIN_RECEIPT,'serial_path':str(serial_path),'serial_sha256':PIN_SERIAL,'old_receipt_linux_version_marker':False,'corrected_full_serial_linux_version_line':observation['linux_version_line'],'first_line':observation['first_line'],'classification':'FX6 original kernel early printk on unchanged FX3 platform; no init/AP/AV/CP proof','original_receipt_modified':False},'init_boundary_parser_baseline':{'historical_fx3_serial_path':str(FX3_SERIAL),'sha256':FX3_SERIAL_SHA,'actual_complete_init_line':baseline_observation['init_boundary_line'],'actual_rc':baseline_observation['init_boundary_rc'],'actual_first_original_module_line':baseline_observation['first_module_line'],'fx6_early_run_init_line':observation['init_boundary_line'],'Freeing_unused_kernel_memory_is_not_init_success':True}}


if __name__=='__main__':
    value=main();(HERE/'host-selftest-and-run-addendum.json').write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');print(json.dumps(value,indent=2,ensure_ascii=False))
