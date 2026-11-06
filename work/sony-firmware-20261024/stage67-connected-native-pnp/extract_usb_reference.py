#!/usr/bin/env python3
"""Read original USB components from a pinned official image; never load them."""
from pathlib import Path
import datetime
import io
import json
import sys
from elftools.elf.elffile import ELFFile

STAGE = Path(__file__).resolve().parent
BASE = STAGE.parent
sys.path.insert(0, str(BASE/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h
sys.path.insert(0, str(BASE/'stage2/extraction'))
import read_filesystems as fs


def main():
    h.im.volume()
    assert h.im.sha(Path(fs.__file__).read_bytes()) == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    image = BASE/'stage2/extraction/nflasha15.img'
    pin = 'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    assert h.im.sha(image.read_bytes()) == pin
    names = {'/kmod/usbg_storage.ko', '/kmod/usb_extcmd.ko', '/kmod/usb_f_mass_storage.ko',
             '/lib/libInfraUsbCmn.so', '/lib/libUsbControl.so', '/lib/libusbcmd.so', '/bin/usb_insmod.sh'}
    reader = fs.Ext2(image)
    found = {x['path']:x for x in reader.walk() if x['path'] in names}
    assert set(found) == names
    rows = []
    for name in sorted(names):
        entry = found[name]
        assert entry['type'] == 0x8000 and entry['size'] < 200000
        raw = reader.data(entry['inode'])
        assert len(raw) == entry['size']
        target = STAGE/'official-files/nflasha15'/name.lstrip('/')
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        record = {'image_sha256':pin, 'entry':entry, 'output':str(target.relative_to(h.ROOT)),
                  'bytes':len(raw), 'sha256':h.im.sha(raw)}
        if name.endswith(('.ko','.so')):
            elf = ELFFile(io.BytesIO(raw))
            assert elf['e_machine'] == 'EM_AARCH64' and elf.little_endian and elf.elfclass == 64
            record['ELF_type'] = elf['e_type']
            syms = elf.get_section_by_name('.symtab') or elf.get_section_by_name('.dynsym')
            record['selected_symbols'] = [
                {'name':x.name,'value':hex(x['st_value']),'size':x['st_size'],'section':x['st_shndx']}
                for x in syms.iter_symbols() if any(k.lower() in x.name.lower()
                    for k in ('inquiry','checkExtCommand','ExtCommand','Lun','Storage','Jiritsu','SCSI'))]
        else:
            record['text_read_not_executed'] = raw.decode('ascii')
        rows.append(record)
    out = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'script_sha256':h.im.sha(Path(__file__).read_bytes()),
           'reader_sha256':h.im.sha(Path(fs.__file__).read_bytes()),
           'source_image':str(image.relative_to(h.ROOT)), 'source_image_sha256':pin,
           'files':rows,'camera_or_module_execution_mount_or_modified_firmware':False,
           'packaged_component_is_not_proof_of_current_runtime_loaded_driver':True}
    h.im.write_json(STAGE/'usb-original-extraction.json',out)
    print(json.dumps({'files':[{'path':r['output'],'sha256':r['sha256'],'symbols':len(r.get('selected_symbols',[]))} for r in rows]}))


if __name__ == '__main__':
    main()
