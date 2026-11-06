#!/usr/bin/env python3
"""Capture the exact original memory-buffer flow; no vendor program is loaded."""
import sys
sys.dont_write_bytecode = True
from capture_contract import capture

SELECT = {
    'libupdatercommon.so': [
        '_ZN7Updater10RingBufferC2Ev',
        '_ZN7Updater10RingBuffer10InitializeEPhm',
        '_ZN7Updater10RingBuffer5ResetEv',
        '_ZN7Updater10RingBuffer5IsEndEv',
        '_ZN7Updater10RingBuffer11GetDataSizeEv',
        '_ZN7Updater10RingBuffer19ReadDataWithoutCopyEPPhm',
        '_ZN7Updater10RingBuffer13writeToBufferEPKhmb',
        '_ZN7Updater10RingBuffer26getEmptySizeWithoutLockingEv',
        '_ZN7Updater10RingBuffer9WriteDataEPKhmb',
        '_ZN7Updater10RingBuffer12GetEmptySizeEv',
        '_ZN7Updater10RingBuffer10memoryCopyEPhPKhm',
        '_ZN7Updater10RingBuffer14readFromBufferEPhm',
        '_ZN7Updater10RingBuffer8ReadDataEPhm',
    ],
    'libupdatercorecommon.so': [
        '_ZN7Updater12BaseFirmware10InitializeEPNS_10BaseModuleE',
        '_ZN7Updater12BaseFirmware14StartWriteFirmEv',
        '_ZN7Updater10BaseModule9WriteDataEPKhmb',
    ],
    'libsdfileinputupdaterapi.so': [
        '_ZN7Updater13BufferManagerC2Ev',
        '_ZN7Updater13BufferManager17GetResponseBufferEv',
        '_ZN7Updater13BufferManager13GetWorkBufferEv',
        '_ZN7Updater21SDUUDConditionCheckerC2Ev',
        '_ZN7Updater21SDUUDConditionChecker10InitializeEPNS_27SDFileInputBodyLoaderModuleEPNS_17SDDecryptorModuleE',
        '_ZN7Updater21SDUUDConditionChecker23SkipContentsInformationERNS_15FsysFileHandlerE',
    ],
}

if __name__ == '__main__':
    capture(SELECT, 'flow-contract.json', 'flow', ['RingBuffer', 'BaseFirmware', 'BufferManager', 'SDUUDConditionChecker'])
