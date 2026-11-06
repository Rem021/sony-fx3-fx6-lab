#!/usr/bin/env python3
"""Pin public data to original FX3 material and review original hash input/rounds."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def reader():
    prior = BASE / 'stage134-backup-reader-scope-and-service-extension'
    receipt = prior / 'final-receipt.json'
    assert sha256(receipt.read_bytes()).hexdigest() == '5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    path = prior / 'audit_readers.py'
    pin = next(x for x in json.loads(receipt.read_text())['files'] if x['path'] == path.relative_to(ROOT).as_posix())
    assert sha256(path.read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('fixed_elf', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provider_module():
    spec = importlib.util.spec_from_file_location('local_digest_provider', HERE / 'public_digest_provider.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    upstream = json.loads((HERE / 'upstream-inputs.json').read_text())
    assert upstream['fixed_commit'] == 'a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0'
    for record in upstream['records']:
        assert not record.get('download_failed')
        p = ROOT / record['path']
        assert p.stat().st_size == record['bytes'] and sha256(p.read_bytes()).hexdigest() == record['sha256']
    p = provider_module()
    provider = p.FX3PublicDigestProvider()
    source = HERE / 'upstream/constants.py'
    keys = p.parse_sha256_material(source.read_bytes())
    elf = reader().Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    rows = []
    for index, va in enumerate((0x55780, 0x55580, 0x55380)):
        assert elf.read(va, 512) == keys[index]
        rows.append({'host_round_index': index, 'original_round_argument': index + 1,
                     'original_material_VA': hex(va), 'bytes': 512,
                     'material_sha256': sha256(keys[index]).hexdigest(), 'exact_bytes_match': True})
    functions = [elf.function(n) for n in ['_Z5xxhopPhS_', '_Z6xxstepPhS_i',
                                           '_Z9CmdDecodePtPh', 'SEN_SSL_GenerateDigestData']]
    ins = {int(i['pc'], 16): i for f in functions for i in f['instructions']}
    for pc, assembly in {0x15be8:'mov w0, #8',0x15c50:'cmp w0, #8',
                         0x15c80:'cmp w0, #3',0x15ca4:'mov x2, #0x200',
                         0x15cec:'mov x2, #0x400',0x15cf4:'mov x4, #0x20',
                         0x15cf8:'mov w0, #1',0x15cac:'cmp w21, #2',
                         0x15cb4:'cmp w21, #3',0x15cbc:'cmp w21, #1',
                         0x15d24:'add x0, x0, #4',0x15b90:'and w1, w1, #0xff'}.items():
        assert ins[pc]['asm'] == assembly, (hex(pc), ins[pc])
    calls = [elf.expect_call(pc,name) for pc,name in [(0x15d00,'SEN_SSL_GenerateDigestData'),
              (0x15d2c,'memcmp'),(0x16488,'EVP_sha256'),(0x164e0,'EVP_DigestUpdate'),(0x164fc,'EVP_DigestFinal_ex')]]
    result = {'status':'PASS_PUBLIC_SHA256_MATERIAL_AND_ORIGINAL_FX3_INPUT_ASSEMBLY_NOT_DEVICE_AUTH',
        'provider_source_sha256':sha256((HERE/'public_digest_provider.py').read_bytes()).hexdigest(),
        'public_constants_sha256':p.PUBLIC_CONSTANTS_SHA256,
        'fixed_public_commit':upstream['fixed_commit'],'original_core_sha256':sha256(elf.raw).hexdigest(),
        'round_material_map':rows,'functions':functions,'checked_calls':calls,
        'original_challenge_code':8,'digest':'SHA-256','input_model':'512B response challenge +512B round material',
        'native_verifier_rounds':[1,2,3],'host_provider_rounds':[0,1,2],
        'provider_rejects_legacy_SHA1_code2_for_this_fixed_FX3_verifier':True,
        'legacy_faulty_SHA1_source_downloaded_but_not_executed_or_used':True,
        'CmdDecode_low8_behavior_not_assumed_full16':True,
        'raw_key_material_or_factory_private_credentials_printed':False,
        'public_data_not_claimed_Sony_factory_private_key_or_live_authentication':True,
        'original_Sony_execution_this_script':False,'camera_or_driver_operations':0,
        'goal_complete':False,'persistent_write_release':False}
    with (HERE/'original-digest-review.json').open('x') as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps({'status':result['status'],'material_blocks_matching':3,'original_functions':4,'challenge_code':8,'camera_operations':0}))


if __name__=='__main__':
    main()
