"""Target-filtered Mac descriptor transport. Importing this module performs no USB I/O.

The live loader is guarded before CDLL loading/initialization. This first transport
step exposes descriptors only: no open/claim/control/bulk/reset/driver APIs are bound.
"""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
U8,U16,U32= C.c_uint8,C.c_uint16,C.c_uint32
VOID=C.c_void_p


class DeviceDescriptor(C.Structure):
    _fields_=[('bLength',U8),('bDescriptorType',U8),('bcdUSB',U16),('bDeviceClass',U8),
        ('bDeviceSubClass',U8),('bDeviceProtocol',U8),('bMaxPacketSize0',U8),
        ('idVendor',U16),('idProduct',U16),('bcdDevice',U16),('iManufacturer',U8),
        ('iProduct',U8),('iSerialNumber',U8),('bNumConfigurations',U8)]


class EndpointDescriptor(C.Structure):
    _fields_=[('bLength',U8),('bDescriptorType',U8),('bEndpointAddress',U8),('bmAttributes',U8),
        ('wMaxPacketSize',U16),('bInterval',U8),('bRefresh',U8),('bSynchAddress',U8),
        ('extra',C.POINTER(U8)),('extra_length',C.c_int)]


class InterfaceDescriptor(C.Structure):
    _fields_=[('bLength',U8),('bDescriptorType',U8),('bInterfaceNumber',U8),('bAlternateSetting',U8),
        ('bNumEndpoints',U8),('bInterfaceClass',U8),('bInterfaceSubClass',U8),('bInterfaceProtocol',U8),
        ('iInterface',U8),('endpoint',C.POINTER(EndpointDescriptor)),('extra',C.POINTER(U8)),('extra_length',C.c_int)]


class Interface(C.Structure):
    _fields_=[('altsetting',C.POINTER(InterfaceDescriptor)),('num_altsetting',C.c_int)]


class ConfigDescriptor(C.Structure):
    _fields_=[('bLength',U8),('bDescriptorType',U8),('wTotalLength',U16),('bNumInterfaces',U8),
        ('bConfigurationValue',U8),('iConfiguration',U8),('bmAttributes',U8),('MaxPower',U8),
        ('interface',C.POINTER(Interface)),('extra',C.POINTER(U8)),('extra_length',C.c_int)]


class TransportError(RuntimeError):
    pass


def layout():
    return {'device_size':C.sizeof(DeviceDescriptor),'endpoint_size':C.sizeof(EndpointDescriptor),
        'interface_desc_size':C.sizeof(InterfaceDescriptor),'interface_size':C.sizeof(Interface),
        'config_size':C.sizeof(ConfigDescriptor),'endpoint_extra':EndpointDescriptor.extra.offset,
        'interface_endpoint':InterfaceDescriptor.endpoint.offset,'config_interface':ConfigDescriptor.interface.offset}


class Bindings:
    """A passed-in, already loaded ABI. Native loading is only through load_live()."""
    def __init__(self,lib):
        specs={
            'libusb_fx3_set_target':([U32],C.c_int),
            'libusb_init':([C.POINTER(VOID)],C.c_int),
            'libusb_exit':([VOID],None),
            'libusb_get_device_list':([VOID,C.POINTER(C.POINTER(VOID))],C.c_ssize_t),
            'libusb_free_device_list':([C.POINTER(VOID),C.c_int],None),
            'libusb_get_device_descriptor':([VOID,C.POINTER(DeviceDescriptor)],C.c_int),
            'libusb_get_active_config_descriptor':([VOID,C.POINTER(C.POINTER(ConfigDescriptor))],C.c_int),
            'libusb_free_config_descriptor':([C.POINTER(ConfigDescriptor)],None)}
        for name,(args,result) in specs.items():
            function=getattr(lib,name);function.argtypes=args;function.restype=result
            setattr(self,name,function)


def _extra(node):
    if not 0<=node.extra_length<=4096 or (node.extra_length and not node.extra):
        raise TransportError('invalid extra descriptor bounds')


def parse_config(pointer):
    if not pointer:raise TransportError('missing configuration descriptor')
    config=pointer.contents
    if config.bLength!=9 or config.bDescriptorType!=2 or not 1<=config.bNumInterfaces<=8 or not config.interface:
        raise TransportError('invalid configuration shape')
    _extra(config)
    minimum=9;rows=[]
    for n in range(config.bNumInterfaces):
        interface=config.interface[n]
        if not 1<=interface.num_altsetting<=4 or not interface.altsetting:
            raise TransportError('invalid alternate-setting array')
        for a in range(interface.num_altsetting):
            alternate=interface.altsetting[a]
            if alternate.bLength!=9 or alternate.bDescriptorType!=4 or alternate.bNumEndpoints>8:
                raise TransportError('invalid interface descriptor')
            _extra(alternate)
            if alternate.bNumEndpoints and not alternate.endpoint:raise TransportError('missing endpoint array')
            minimum+=9;endpoints=[];seen=set()
            for e in range(alternate.bNumEndpoints):
                endpoint=alternate.endpoint[e];address=int(endpoint.bEndpointAddress)
                if endpoint.bLength not in (7,9) or endpoint.bDescriptorType!=5 or not endpoint.wMaxPacketSize:
                    raise TransportError('invalid endpoint descriptor')
                if not address&15 or address&0x70 or address in seen:raise TransportError('invalid or duplicate endpoint address')
                _extra(endpoint);seen.add(address);minimum+=endpoint.bLength
                endpoints.append({'descriptor_order':e,'address':address,'direction':'IN' if address&128 else 'OUT',
                    'transfer_type':int(endpoint.bmAttributes)&3,'max_packet_size':int(endpoint.wMaxPacketSize)})
            rows.append({'interface':int(alternate.bInterfaceNumber),'alternate':int(alternate.bAlternateSetting),
                'class':int(alternate.bInterfaceClass),'subclass':int(alternate.bInterfaceSubClass),
                'protocol':int(alternate.bInterfaceProtocol),'endpoints':endpoints})
    if not minimum<=config.wTotalLength<=65535:raise TransportError('configuration total length too small')
    return {'configuration':int(config.bConfigurationValue),'total_length':int(config.wTotalLength),'interfaces':rows,
            'authentication_or_service_endpoint_roles_proven':False}


def query_descriptors(abi,location,expected_pid=0x0da1):
    if type(location) is not int or not 0<location<=0xffffffff or expected_pid not in (0x0da1,0x0336):
        raise TransportError('invalid fixed target')
    if abi.libusb_fx3_set_target(location)!=0:raise TransportError('private target selector rejected')
    context=VOID()
    if abi.libusb_init(C.byref(context))!=0 or not context:
        raise TransportError('USB context not established; no default-context cleanup attempted')
    devices=C.POINTER(VOID)();config=C.POINTER(ConfigDescriptor)()
    list_owned=False;config_owned=False
    try:
        count=abi.libusb_get_device_list(context,C.byref(devices))
        if count<0:raise TransportError('enumeration failed')
        list_owned=bool(devices)
        if count!=1 or not devices or not devices[0]:raise TransportError('exactly one selected device required')
        descriptor=DeviceDescriptor()
        if abi.libusb_get_device_descriptor(devices[0],C.byref(descriptor))!=0:raise TransportError('device descriptor unavailable')
        if descriptor.bLength!=18 or descriptor.bDescriptorType!=1 or descriptor.idVendor!=0x054c or descriptor.idProduct!=expected_pid:
            raise TransportError('descriptor differs from selected FX3 profile')
        if abi.libusb_get_active_config_descriptor(devices[0],C.byref(config))!=0:raise TransportError('active configuration unavailable')
        config_owned=bool(config)
        parsed=parse_config(config)
        return {'VID':int(descriptor.idVendor),'PID':int(descriptor.idProduct),'USB_BCD':int(descriptor.bcdUSB),
            **parsed,'only_selected_target':True,'no_serial_strings_requested_or_stored':True,
            'device_or_interface_open_claim_driver_change_vendor_auth_or_media_operation':False,
            'descriptor_query_is_active_standard_USB_read_not_IORegistry_only':True,
            'actual_recording_authentication_backup_or_recovery_proven':False}
    finally:
        if config_owned:abi.libusb_free_config_descriptor(config)
        if list_owned:abi.libusb_free_device_list(devices,1)
        abi.libusb_exit(context)


def load_live(location,expected_pid=0x0da1):
    """Fail before CDLL or libusb_init under the current cache-only authority."""
    goal=json.loads((BASE/'GOAL_STATUS.json').read_text())
    if goal['authorization'].get('Mac_active_USB_descriptor_read_authorized') is not True or \
       goal['prepared_first_device_trial'].get('Mac_descriptor_probe_released') is not True:
        raise TransportError('active descriptor read requires its own reviewed release and matching user authorization')
    target=goal['authorization'].get('Mac_active_USB_descriptor_target',{})
    if type(location) is not int or target.get('locationID')!=location or target.get('VID')!=0x054c or target.get('PID')!=expected_pid:
        raise TransportError('requested target is outside the specific descriptor-read authority')
    receipt=json.loads((HERE/'native-build-receipt.json').read_text())
    pin=receipt['library'];library=ROOT/pin['path']
    if library.stat().st_size!=pin['bytes'] or sha256(library.read_bytes()).hexdigest()!=pin['sha256']:
        raise TransportError('private library pin mismatch')
    if layout()!=receipt['probe_header_layout']:raise TransportError('C/ctypes ABI mismatch')
    return Bindings(C.CDLL(str(library)))
