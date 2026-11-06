#!/usr/bin/env python3
"""Finish the static input-to-consumer link using the original exported methods."""
import sys
sys.dont_write_bytecode = True
from capture_contract import capture

SELECT = {
    'libupdatercorecommon.so': [
        '_ZN7Updater12BaseFirmware9WriteDataEPKhmb',
        '_ZN7Updater12BaseFirmware12EndWriteFirmEv',
    ],
    'libupdatercommon.so': [
        '_ZN7Updater10RingBuffer8SkipDataEm',
    ],
    'libsdfileinputupdaterapi.so': [
        '_ZN7Updater17SDDecryptorModule5IsEndEv',
        '_ZN7Updater17SDDecryptorModule7executeEv',
    ],
}

if __name__ == '__main__':
    capture(SELECT, 'tail-flow-contract.json', 'tail-flow', ['BaseFirmware', 'RingBuffer', 'SDDecryptorModule'])
