/* Own ABI fixture: no SDK, DLL, link, device or runtime calls. */
typedef unsigned char UCHAR;
typedef unsigned short USHORT;
typedef unsigned short WCHAR;
typedef unsigned int ULONG;
typedef unsigned int DWORD;
typedef unsigned long long ULONG_PTR;
typedef struct { ULONG Data1; USHORT Data2, Data3; UCHAR Data4[8]; } GUID;
typedef struct {
    USHORT Length;
    UCHAR ScsiStatus, PathId, TargetId, Lun, CdbLength, SenseInfoLength, DataIn;
    ULONG DataTransferLength, TimeOutValue;
    ULONG_PTR DataBufferOffset;
    ULONG SenseInfoOffset;
    UCHAR Cdb[16];
} SCSI_PASS_THROUGH;
typedef struct { DWORD cbSize; GUID InterfaceClassGuid; DWORD Flags; ULONG_PTR Reserved; } SP_DEVICE_INTERFACE_DATA;
typedef struct { DWORD cbSize; GUID ClassGuid; DWORD DevInst; ULONG_PTR Reserved; } SP_DEVINFO_DATA;
typedef struct { DWORD cbSize; WCHAR DevicePath[1]; } SP_DEVICE_INTERFACE_DETAIL_DATA_W;
#define OFF(T,F) __builtin_offsetof(T,F)
#define CHECK(X) _Static_assert((X), #X)
CHECK(sizeof(void*) == 8);
CHECK(sizeof(ULONG) == 4);
CHECK(sizeof(ULONG_PTR) == 8);
CHECK(sizeof(SCSI_PASS_THROUGH) == 56);
CHECK(OFF(SCSI_PASS_THROUGH, DataIn) == 8);
CHECK(OFF(SCSI_PASS_THROUGH, DataTransferLength) == 12);
CHECK(OFF(SCSI_PASS_THROUGH, TimeOutValue) == 16);
CHECK(OFF(SCSI_PASS_THROUGH, DataBufferOffset) == 24);
CHECK(OFF(SCSI_PASS_THROUGH, SenseInfoOffset) == 32);
CHECK(OFF(SCSI_PASS_THROUGH, Cdb) == 36);
CHECK(sizeof(SP_DEVICE_INTERFACE_DATA) == 32);
CHECK(OFF(SP_DEVICE_INTERFACE_DATA, Reserved) == 24);
CHECK(sizeof(SP_DEVINFO_DATA) == 32);
CHECK(OFF(SP_DEVINFO_DATA, DevInst) == 20);
CHECK(OFF(SP_DEVINFO_DATA, Reserved) == 24);
CHECK(sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_W) == 8);
CHECK(OFF(SP_DEVICE_INTERFACE_DETAIL_DATA_W, DevicePath) == 4);
CHECK(((4u << 16) | (3u << 14) | (0x401u << 2)) == 0x4d004u);
