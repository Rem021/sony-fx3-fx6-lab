from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;M=R.parents[3];proof=R.parents[1]/'lead-claude/audits/boot-screen-controller/boot-screen-proof.json'
p=json.loads(proof.read_text());seed=R.parent/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin';b=seed.read_bytes()[0xd2000:0xd2000+1369580];assert hashlib.sha256(b).hexdigest()==p['CP_Backup_fixture']['seed_same_bank_sha256'];h=14695981039346656037
for x in b:h=((h^x)*1099511628211)&((1<<64)-1)
(R/'helpers/fx3-cp-backup-profile-v1.h').write_text(f'#define CP_SEED_FNV64 0x{h:016x}UL\n#define CP_SEED_SHA256 "{hashlib.sha256(b).hexdigest()}"\n')
(R/'ap88-cp-storage-profile.json').write_text(json.dumps({'proof':str(proof),'proof_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'profile':'Explicit virtualCP bank at alreadyreserved AP fixture secondBK4; notnativeCPprimarybinding','physical':hex(0x4040d2000),'bytes':len(b),'root_physical':'0x404000000','root_range_bytes':'0x221000','root_firstbank_untouched':True,'bank_sha256':hashlib.sha256(b).hexdigest(),'bank_fnv64':hex(h),'reset_contract':p['CP_Backup_fixture']['projection']['resets'],'lifetime':'one module/boot epoch,strictF1thenF4oncesuccessful; originalBackup_save0; QMPsnapshotonly'},indent=2)+'\n');print(hex(h))
