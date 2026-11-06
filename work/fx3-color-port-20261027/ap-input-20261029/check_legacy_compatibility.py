#!/usr/bin/env python3
"""Check the actual current AP legacy AES wrapper against one official block.

Only a 1 KiB existing vector, host AES, and original bounded checksum helper.
No complete changed container is constructed, no Sony executable is loaded.
"""
from pathlib import Path
import hashlib,json,struct,sys
from current_static import View,sources,HERE

def main():
    previous=HERE.parent/'package-20261028';sys.path.insert(0,str(previous))
    from cbc_vectors import crypt,pack,FW
    from original_block_checker_guest import Guest
    source=next(r for r in sources() if Path(r['path']).name=='libupdatertalk.so')
    view=View(source['path'],source['sha256'])
    assert view.function(0x8c0) and view.function(0x8d8)
    # Dec_ScrambleInit loads the key pointer through this original GOT slot.
    rel=next(r for r in view.elf.get_section_by_name('.rela.dyn').iter_relocations() if r['r_offset']==0x10fb8)
    assert rel['r_info_type']==1025
    symbol=view.symbols[rel['r_info_sym']];keyva=symbol['st_value']+rel['r_addend']
    assert symbol['st_size']>=16 and symbol['st_shndx']!='SHN_UNDEF'
    key=view.read(keyva,16) # Original AES format constant, retained in memory only.
    vectors=json.loads((previous/'cbc-vector-results.json').read_text())
    block0=next(r for r in vectors['samples'] if r['block']==0)
    cipher=(previous/'experimental-vectors/block-000000-original.bin').read_bytes()
    assert len(cipher)==1024 and hashlib.sha256(cipher).hexdigest()==block0['original_cipher_sha256']
    manifest=json.loads((FW/'fx3-7.02-offline-manifest.json').read_text())
    plain_path=FW/'fx3-7.02-decrypted.fdat'
    with plain_path.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==manifest['decrypted_fdat_sha256']
        stream.seek(0);payload=stream.read(1020)
    correct=pack(payload,False);legacy=crypt(cipher,key,ecb=True,decrypt=True)
    assert legacy[:512]==correct[:512] and legacy[512:]!=correct[512:]
    core=next(r for r in sources() if Path(r['path']).name=='libupdatercorecommon.so')
    body=Path(core['path']).read_bytes();assert hashlib.sha256(body).hexdigest()==core['sha256']
    g=Guest(body);good=g.call(0xa8e8,correct);bad=g.call(0xa8e8,legacy)
    assert good['returned'] and bad['exception']['code']=='0x30002'
    reencoded=crypt(correct,key,ecb=True)
    restored=crypt(reencoded,key,ecb=True,decrypt=True)
    assert restored==correct and reencoded!=cipher
    reencoded_check=g.call(0xa8e8,restored);assert reencoded_check['returned']
    result=dict(original_aes_wrapper_sha256=source['sha256'],key_symbol=symbol.name,key_bytes=16,key_sha256=hashlib.sha256(key).hexdigest(),
        original_cipher_block_sha256=hashlib.sha256(cipher).hexdigest(),original_plain_fdat_sha256=manifest['decrypted_fdat_sha256'],
        first512_match=True,last512_match=False,expected_raw_block_sha256=hashlib.sha256(correct).hexdigest(),legacy_raw_block_sha256=hashlib.sha256(legacy).hexdigest(),
        original_checksum_helper_sha256=core['sha256'],original_checksum_helper_entry='0xa8e8',
        expected_checksum=struct.unpack_from('<H',legacy)[0],legacy_calculated_checksum=sum(struct.unpack('<511H',legacy[2:]))&0xffff,
        correct_original_block_result=good,legacy_decrypted_original_block_result=bad,
        in_memory_legacy_reencoding=dict(cipher_sha256=hashlib.sha256(reencoded).hexdigest(),different_from_official_cipher=True,restored_original_plain_block=True,original_checksum_result=reencoded_check,output_written=False),
        scope='Source wrapper is statically AES-128 single-block decryption with no CBC chaining. Host CommonCrypto applies that rule to one original 1 KiB vector; original current AP checksum helper executes in bounded synthetic Unicorn RAM. This distinguishes formats, not all admission paths. No full legacy repack, modified firmware, native Sony program, body or device action.')
    (HERE/'legacy-format-compatibility-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'first512_match':True,'second512_match':False,'correct_block_accepted':good['returned'],'legacy_block_error':bad['exception']['code'],'legacy_reencoded_1kb_roundtrip':True,'private_rsa_read':False,'camera_actions':0}))

if __name__=='__main__':main()
