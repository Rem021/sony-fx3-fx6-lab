"""Pure HOST_ONLY records. No device completion inference or user-file trust."""
from hashlib import sha256
import struct
import receipt_receiver as R
SCOPE=0x484f5354
def _header(data,magic,size,kind,identity,nonce):
    if len(data)!=size or data[:8]!=magic or struct.unpack_from('<4I',data,8)!=(1,size,kind,SCOPE):raise R.Rejected('host record scope/version')
    if struct.unpack_from('<IIQQ',data,24)!=(identity.uid,identity.pid,identity.sec,identity.usec) or data[48:64]!=nonce:
        raise R.Rejected('host record identity/nonce')
    if data[64:96]!=sha256(R.GRANT_ID.encode()).digest():raise R.Rejected('host record grant')

def trial(data,*,identity=None,nonce=None,archive_uid=None,root_login_required=False):
    if len(data)!=256:raise R.Rejected('host trial bytes')
    uid,pid,sec,usec=struct.unpack_from('<IIQQ',data,24)
    if identity is None:
        identity=R.Identity(uid,pid,sec,usec,'archive metadata only','')
        nonce=data[48:64]
    _header(data,b'FX3HST01',256,1,identity,nonce)
    if not pid or sec<=0 or usec>=1_000_000 or (archive_uid is not None and uid!=archive_uid):raise R.Rejected('host archive incarnation')
    if sha256(data[:224]).digest()!=data[224:]:raise R.Rejected('host trial checksum')
    expected=nonce+bytes([0xa5])*32+struct.pack('<IIQ',uid,pid,sec)
    if data[96:128]!=sha256(expected).digest():raise R.Rejected('host RAM payload checksum')
    if struct.unpack_from('<I',data,128)[0]!=1 or struct.unpack_from('<4I',data,160)!=(1,0,0,0) or struct.unpack_from('<I',data,176)[0]!=64 or any(data[180:224]):
        raise R.Rejected('host work/device operation bounds')
    audit_return,audit_uid,record_uid,session,security_session,attrs,flags=struct.unpack_from('<i6I',data,132)
    if root_login_required and not (uid==0 and audit_return==0 and audit_uid==record_uid==501 and 0<session<0xffffffff and session==security_session and flags==3):
        raise R.Rejected('root audit/GUI/TTY not validated')
    return {'scope':'HOST_ONLY','kind':'trial','uid':uid,'pid':pid,'birth_sec':sec,'birth_usec':usec,'nonce':nonce.hex(),
            'payload_bytes':64,'payload_sha256':data[96:128].hex(),'record_sha256':sha256(data).hexdigest(),
            'audit_uid':audit_uid,'audit_session':session,'security_attributes':attrs,'login_flags':flags,
            'device_operations':0,'physical_camera_acceptance':False,'transport_authenticated':False}

def readback(data,identity,nonce,expected_trial_nonce,*,root_login_required=False):
    _header(data,b'FX3HRD01',384,2,identity,nonce)
    if sha256(data[:352]).digest()!=data[352:]:raise R.Rejected('host readback checksum')
    archive=trial(data[96:352],archive_uid=identity.uid,root_login_required=root_login_required)
    if archive['nonce']!=expected_trial_nonce.hex():raise R.Rejected('host readback original nonce')
    return {'scope':'HOST_ONLY','kind':'readback','uid':identity.uid,'pid':identity.pid,'nonce':nonce.hex(),
            'archive':archive,'archive_sha256':sha256(data[96:352]).hexdigest(),'device_operations':0,
            'physical_camera_acceptance':False,'transport_authenticated':False}
