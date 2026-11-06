#!/usr/bin/env python3
"""Repeat independent parser-body calls with adjacent original NOR bytes in RAM."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
helper = HERE/'probe_mis_consumer.py'
helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('current_DGU_RAM_prefix',helper)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
from unicorn import UC_PROT_READ

NOR_BASE = 0xfe049000
NOR_PIN = '4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'


class Guest(old.Guest):
    def __init__(self,dgu,mis,nor):
        super().__init__(dgu,mis)
        self.nor = nor
        self.u.mem_map(NOR_BASE,(len(nor)+4095)&~4095,UC_PROT_READ)
        self.u.mem_write(NOR_BASE,nor)

    def read(self,u,access,at,size,value,user):
        if NOR_BASE <= at and at+size <= NOR_BASE+len(self.nor):
            return
        super().read(u,access,at,size,value,user)


def main():
    out = HERE/'DGU-MIS-with-NOR-results.json'
    assert not out.exists()
    original = old.FW/'stage198-AP-CP-loaders-and-partition-selection/originals'
    dgu = (original/'DGU.bin').read_bytes()
    mis = (original/'MIS.bin').read_bytes()
    nor_path = old.TASK/'config-producer-20261029/original-files/loader_nor.bin'
    nor = nor_path.read_bytes()
    for key,data in [('DGU',dgu),('MIS',mis)]:
        assert hashlib.sha256(data).hexdigest() == old.PINS[key]
    assert hashlib.sha256(nor).hexdigest() == NOR_PIN
    cases = []
    for offset in [0xa00,0xc200,0x13200]:
        r = Guest(dgu,mis,nor).call(0xfe04536c,[0x10,old.MIS+offset])
        cases.append(dict(script_offset=hex(offset),result=r))
    at = 0xfe05fe48-NOR_BASE
    result = dict(source_pins=dict(**old.PINS,NOR=NOR_PIN),
        helper=dict(path=helper.name,sha256=helper_sha),
        added_original_NOR=dict(path=str(nor_path),bytes=len(nor),base=hex(NOR_BASE),
            word_at_probe='0x'+nor[at:at+8][::-1].hex(),compared_magic='0x59634649cafec0da',
            original_bytes_match_magic=False,range_only_original_file_bytes=True),
        cases=cases,scope='Independent explicit original DGU/MIS/NOR RAM composition. Original NOR is read-only data; no NOR code or original boot-information block is mapped/executed. Other restrictions are inherited from the strict DGU-only probe. These bytes are a source-context projection, not a live boot-state measurement.',
        CPU_or_hardware_operations_executed=0,device_actions=0,native_Sony_programs_executed=0,
        modified_firmware_or_flashable_package_produced=False)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(script=x['script_offset'],boundary=x['result']['boundary'],
                          instructions=x['result']['original_instructions'],dispatches=len(x['result']['original_dispatches'])) for x in cases]))


if __name__ == '__main__':
    main()
