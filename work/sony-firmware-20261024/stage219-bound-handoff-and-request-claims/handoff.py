"""Local handoff data only; PID/nonce/plan hash are not caller authentication."""
from pathlib import Path
from hashlib import sha256
import secrets,struct,sys,zlib
H=Path(__file__).resolve().parent;ROOT=H.parents[2];sys.path.insert(0,str(ROOT/'outputs/fx3-recovery-adapter'))
from fx3_recovery import boot_worker as B
from fx3_recovery.files import require,encode,new_directory
from fx3_recovery.capture import hex_value
MAGIC=b'FX3HANDOFFv1'.ljust(16,b'\0')
CLAIM=b'FX3CLAIMPENDv1'.ljust(16,b'\0')
MAX_NS=120_000_000_000


def packet(req,pid,ppid,camera_tick_ns,plan_digest,nonce=None,ttl_ns=MAX_NS):
    require(type(req) is bytes and len(req)==128,'exact boot request bytes required')
    capture=req[16:32].hex();role,window=struct.unpack_from('<II',req,36);total=struct.unpack_from('<Q',req,48)[0]
    require(role in (0,1) and req==B.request(capture,'boot'+str(role),window,total),'boot request must match canonical wire')
    require(type(pid) is int and type(ppid) is int and 1<pid<=2147483647 and 1<ppid<=2147483647 and pid!=ppid,'bounded observed target PID/PPID required')
    require(type(camera_tick_ns) is int and 0<camera_tick_ns<2**63-MAX_NS and type(ttl_ns) is int and 0<ttl_ns<=MAX_NS,'target CLOCK_MONOTONIC and bounded TTL required; never use host clock')
    require(hex_value(plan_digest,64),'nonzero caller-supplied plan digest required, not attestation')
    nonce=secrets.token_hex(32) if nonce is None else nonce
    require(hex_value(nonce,64),'nonzero nonce required')
    raw=bytearray(256);raw[:16]=MAGIC;raw[16:32]=req[16:32];raw[32:64]=bytes.fromhex(nonce);raw[64:96]=bytes.fromhex(plan_digest);raw[96:128]=sha256(req).digest()
    struct.pack_into('<IIIIIIQQQIII',raw,128,pid,ppid,role,window,1,3,camera_tick_ns,camera_tick_ns+ttl_ns,total,struct.unpack_from('<I',req,124)[0],1,1)
    struct.pack_into('<I',raw,252,zlib.crc32(raw[:252]));return bytes(raw)


def create(req,pid,ppid,camera_tick_ns,plan_digest,destination,nonce=None,ttl_ns=MAX_NS):
    raw=packet(req,pid,ppid,camera_tick_ns,plan_digest,nonce,ttl_ns)
    info={'schema':'fx3-local-handoff-data-v1','handoff_sha256':sha256(raw).hexdigest(),'boot_request_sha256':sha256(req).hexdigest(),
          'nonce':raw[32:64].hex(),'pid':pid,'ppid':ppid,'clock_domain':'caller-supplied target CLOCK_MONOTONIC; not measured',
          'plan_digest_operator_supplied':True,'PID_nonce_plan_is_not_caller_authentication':True,'camera_operations':0,
          'trusted_launcher_or_complete_receipt_verified':False,'cross_request_global_exclusion_implemented':False,**B.BOOT_FALSE}
    new_directory(destination,{'fx3-boot-handoff-v1.bin':raw,'fx3-boot-request-v1.bin':req,'handoff-info.json':encode(info)});return info


def decode_claim(raw):
    require(type(raw) is bytes and len(raw)==256 and raw[:16]==CLAIM and zlib.crc32(raw[:252])==struct.unpack_from('<I',raw,252)[0],'pending claim wire/CRC differs')
    state,kind,pid,ppid=struct.unpack_from('<IIII',raw,16);role,window=struct.unpack_from('<II',raw,184)
    require(state==0x50454e44 and kind in (0,1) and 1<pid<=2147483647 and 1<ppid<=2147483647 and pid!=ppid and role in (0,1) and window<=3 and raw[192:252]==bytes(60),'claim fields differ')
    require(any(raw[32:64]) and any(raw[64:80]) and any(raw[80:112]) and any(raw[112:144]) and any(raw[144:176]),'empty claim binding')
    return {'state':'PENDING_NEVER_COMPLETION','kind':'nonce' if kind==0 else 'capture-window','pid':pid,'ppid':ppid,'nonce':raw[32:64].hex(),
            'capture_id':raw[64:80].hex(),'handoff_sha256':raw[80:112].hex(),'boot_request_sha256':raw[112:144].hex(),
            'plan_digest_operator_supplied':raw[144:176].hex(),'target_tick_ns':struct.unpack_from('<Q',raw,176)[0],
            'target':'boot'+str(role),'window':window,'receipt_authenticated':False,'operation_complete':False,**B.BOOT_FALSE}
