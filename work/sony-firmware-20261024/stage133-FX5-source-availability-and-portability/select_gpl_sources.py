#!/usr/bin/env python3
"""Read archive metadata and copy bounded regular source files; do not build/run them."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import json
import re
import tarfile

HERE = Path(__file__).resolve().parent


def main():
    receipt = json.loads((HERE / 'fx5-gpl-download-receipt.json').read_text())
    destination = HERE / 'gpl-selection'
    destination.mkdir()
    reviewed = []
    total = 0
    for record in receipt['records']:
        archive = HERE / record['path']
        assert archive.stat().st_size == record['bytes']
        assert sha256(archive.read_bytes()).hexdigest() == record['sha256']
        kernel = archive.name == 'linux-kernel.tar.gz'
        with tarfile.open(archive, 'r:gz') as stream:
            members = stream.getmembers()
            chosen = []
            names = set()
            for member in members:
                name = PurePosixPath(member.name)
                assert not name.is_absolute() and '..' not in name.parts
                if not member.isfile():
                    continue
                assert member.name not in names
                names.add(member.name)
                selected = not kernel or member.name == 'linux-kernel/Makefile' or \
                    member.name.startswith('linux-kernel/arch/arm64/boot/dts/cxd/') or \
                    member.name.startswith('linux-kernel/arch/arm64/configs/cxd')
                if not selected:
                    continue
                assert member.size <= 2 * 1024 * 1024
                total += member.size
                assert total <= 16 * 1024 * 1024
                output = destination.joinpath(*name.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                data = stream.extractfile(member).read()
                assert len(data) == member.size
                with output.open('xb') as handle:
                    handle.write(data)
                chosen.append({'member': member.name, 'path': output.relative_to(HERE).as_posix(),
                               'bytes': len(data), 'sha256': sha256(data).hexdigest()})
            reviewed.append({'archive': record['path'], 'archive_sha256': record['sha256'],
                             'archive_member_count': len(members), 'selected_regular_sources': chosen,
                             'archive_CXD_path_names': [m.name for m in members if 'cxd' in m.name.lower()] if kernel else []})
    makefile = (destination / 'linux-kernel/Makefile').read_text()
    version = '.'.join(re.search(r'^' + key + r' = (\d+)$', makefile, re.M).group(1)
                       for key in ('VERSION', 'PATCHLEVEL', 'SUBLEVEL'))
    facts = {'scope': 'Official model-associated GPL source only; selected arm64 platform sources are not proof of exact shipping board/config',
             'model': 'ILME-FX5', 'download_page': receipt['official_model_page'], 'kernel_source_version': version,
             'archives': reviewed, 'copied_regular_source_bytes': total,
             'nonregular_archive_entries_not_extracted': True,
             'code_built_or_executed': False, 'whole_device_firmware_image_obtained': False,
             'actual_SoC_ID_bootloader_security_storage_geometry_or_camera_compatibility_proven': False}
    (HERE / 'gpl-source-selection-receipt.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'kernel_source_version': version, 'selected_files': sum(len(r['selected_regular_sources']) for r in reviewed),
                      'selected_bytes': total, 'whole_device_image_obtained': False}))


if __name__ == '__main__':
    main()
