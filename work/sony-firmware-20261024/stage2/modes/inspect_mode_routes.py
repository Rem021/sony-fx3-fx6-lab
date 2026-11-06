#!/usr/bin/env python3
"""Read-only, fixed-image FX3 mode-map probe. No device I/O, patching or ELF execution.
Uses only the Python standard library; all addresses are module-relative VAs.
The input hash is mandatory: these locations are not transferable patch offsets.
"""
import argparse, hashlib, json, pathlib, struct
EXPECTED = '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
class Image:
    def __init__(self,path,expected=EXPECTED):
        self.b=path.read_bytes()
        if hashlib.sha256(self.b).hexdigest()!=expected: raise ValueError('Wrong appFw.so hash; refusing fixed-map interpretation')
        if self.b[:6]!=b'\x7fELF\x02\x01': raise ValueError('Expected ELF64 LE')
        shoff=struct.unpack_from('<Q',self.b,40)[0];ents,count,idx=struct.unpack_from('<HHH',self.b,58)
        if ents!=64 or shoff+ents*count>len(self.b): raise ValueError('Invalid section bounds')
        self.ss=[struct.unpack_from('<IIQQQQIIQQ',self.b,shoff+i*ents) for i in range(count)]
        self.rel={}
        for s in self.ss:
            if s[1]!=8 and s[4]+s[5]>len(self.b): raise ValueError('Invalid data bounds')
            if s[1]==4:
                if s[9]!=24:raise ValueError('Unexpected RELA entry size')
                for off in range(s[4],s[4]+s[5],24):
                    to,info,add=struct.unpack_from('<QQq',self.b,off)
                    if info&0xffffffff==1027:self.rel[to]=add
    def off(self,va):
        for s in self.ss:
            if s[1]!=8 and s[3] and s[3]<=va<s[3]+s[5]:return s[4]+va-s[3]
        raise ValueError(f'Unmapped VA {va:#x}')
    def n(self,va,size=4,signed=False):return int.from_bytes(self.b[self.off(va):self.off(va)+size],'little',signed=signed)
    def ptr(self,va):return self.rel.get(va,self.n(va,8))
    def text(self,va):
        off=self.off(va);end=self.b.find(b'\0',off,off+8192)
        if end<0:raise ValueError('Unterminated bounded string')
        return self.b[off:end].decode('ascii')
    def string_at_ptr(self,slot):return self.text(self.ptr(slot))
    def jump(self,table,base,index,size=1):return base+4*self.n(table+size*index,size,True)
    def adrp_add_string(self,pc):
        a,b=self.n(pc),self.n(pc+4)
        if a&0x9f000000!=0x90000000 or b&0xff800000!=0x91000000:raise ValueError('Not ADRP + ADD')
        imm=((a>>29)&3)|(((a>>5)&0x7ffff)<<2)
        if imm&(1<<20):imm-=1<<21
        va=(pc&~0xfff)+(imm<<12)+((b>>10)&0xfff)
        return {'va':hex(va),'text':self.text(va)}

def inspect(p):
    e=Image(p)
    fmt=[e.string_at_ptr(0x411f108+8*i).removeprefix('VAL_setting_file_format_') for i in range(14)]
    fr=[e.string_at_ptr(0x411f390+8*i).removeprefix('VAL_setting_movie_rec_frame_rate_xavc_hs_4k_') for i in range(10)]
    vpc=[{'value':i,'formatter_case':hex(e.jump(0x398927c,0x2e5409c,i)),'label':e.adrp_add_string(e.jump(0x398927c,0x2e5409c,i))['text']} for i in range(12)]
    mapped=[]
    for i in range(7):
        to=e.jump(0x39895ac,0x2e691b8,i)
        mapped.append({'enum':i,'label':fr[i],'jump_byte':hex(e.n(0x39895ac+i,1)),'table_va':hex(0x39895ac+i),'target':hex(to),'route':'assert/notify_model_system_error' if to==0x2e691e0 else 'quality-selection','scope':'non-template converter used by GetMovieRecStatus/GetMovieRemain'})
    # Independent runtime FrameRate formatter: values 3 and 7 mean 29.97 and 59.94.
    frame_names=[{'value':i,'formatter_case':hex(e.jump(0x3989288,0x2e54160,i-1)),'label':e.adrp_add_string(e.jump(0x3989288,0x2e54160,i-1))['text']} for i in range(1,10)]
    file_routes=[{'enum':i+5,'label':fmt[i+5],'converter_target':hex(e.jump(0x398958c,0x2e68fec,i,2))} for i in range(7)]
    selected=[(0x2e69198,36,'converter HS4K dispatch'),(0x2e691e0,140,'converter failure branch'),(0x2e50c58,32,'proxy enable and frame pass-through'),(0x2e50d10,12,'proxy VPC=6 assignment'),(0x2e6a8f8,84,'GetMovieRemain converter then proxy call'),(0x2ebf404,32,'assert notification imports __assert_fail'),(0x2bdf97c,36,'named SetMovieRecParam builder slow/quick dispatch; not normal record proof'),(0x2be3230,12,'format builder tail call')]
    snippets=[{'va':hex(v),'length':n,'purpose':label,'bytes':e.b[e.off(v):e.off(v)+n].hex()} for v,n,label in selected]
    return {'input':str(p),'sha256':EXPECTED,'machine':'ELF64 AArch64 ET_DYN','address_basis':'module-relative virtual addresses, not camera runtime addresses','main_file_format_enum':fmt,'has_hs_hd_main_enum':any('HS_HD' in x for x in fmt),'main_converter_file_routes':file_routes,'hs4k_frame_enum':fr,'hs4k_converter_routes':mapped,'vpc_formatter':vpc,'independent_frame_rate_formatter':frame_names,'selected_instruction_bytes':snippets,'assert_import':{'plt':'0x1594060','symbol':'__assert_fail'},'actual_setter':{'plt':'0x15944f0','symbol':'mpr::SetMovieRecParam(mpr::movieRecParam const&)','calls':['0x2e6f7bc','0x2e6f9b0'],'format_builder_candidate':'0x2bdf414','normal_record_mapping':'not fully reconstructed; do not substitute query-converter route for encoder acceptance'},'proxy_conversion':{'entry':'0x2e50bf0','vpc_420_hevc':6,'vpc_write':'0x2e50d10..0x2e50d14','frame_passthrough':'str w3,[x6] at 0x2e50c64','direct_callers':['0x2e6a948','0x2e6f0a0'],'scope':'helper used by query and actual setter wrapper; no camera recording tested'},'not_performed':['firmware execution','patch generation','repack','camera connection','write','boot/record/recovery validation']}

def inspect_mpr(p):
    expected='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    e=Image(p,expected)
    # Symbol-resolved table VA, audited against R_AARCH64_GLOB_DAT at GOT 0x2f9a40.
    table=0x2cb108
    rows=[]
    for vpc in [5,6,7,8]:
        raw=[e.n(table+24*vpc+4*k) for k in range(6)]
        rows.append({'vpc':vpc,'table_va':hex(table+24*vpc),'codec':raw[0],'packed_resolution':hex(raw[1]),'width':raw[1]&65535,'height':raw[1]>>16,'color_format_enum':raw[3],'bit_depth_enum':raw[4],'gop_enum':raw[5],'selector_stream0_result':15 if raw[0]==1 else None,'selector_stream1_result':18 if raw[0]==1 else None})
    regions=[('GetVideoParamComb HEVC HD branch',0xc9f60,0x6c),('GetCodecInfoForCodec stream selection',0xcd45c,0x9c),('EnqueueExecEncOpen main and proxy calls',0xd673c,0x50),('SetMovieRecParam entry',0xf0ff0,0x50),('HD HEVC MP4 level branch',0x115fb4,0x34)]
    return {'input':str(p),'sha256':expected,'table_symbol':'mpr::g_videoParamComb','video_param_comb_table_rows':rows,'get_video_param_comb':{'function':'0xc9e84','hd_branch':'0xc9fa8..0xc9fc8','input_fields':['VideoCodec','VideoResolution','ColorFormat','VideoBitDepth','GopStructure'],'hd_hevc_420_tuple':[1,2,0,1,0],'hd_hevc_420_vpc':6,'hd_hevc_422_tuple':[1,2,1,1,0],'hd_hevc_422_vpc':8,'frame_rate_argument':False},'get_codec_info_for_codec':{'function':'0xcd40c','inputs':['VideoParamComb','StreamType'],'hevc_stream0_codec_id':15,'hevc_stream1_codec_id':18,'resolution_or_fps_check_in_hevc_selector':False},'encoder_command_callers':{'function':'mpr::EnqueueExecEncOpen(mpr::MovieRecInfo&)','main_call':'0xd6748','main_stream_type':0,'proxy_call':'0xd6784','proxy_stream_type':1,'main_vpc_field':'MovieRecInfo+0x1c8','proxy_vpc_field':'MovieRecInfo+0x1f0','other_callers_file':'libmpr-codec-callers.json'},'hd_writer_profile':{'function':'XavcsMovieWriter::ConvertVPCToLevel','entry':'0x115e78','vpc6_and8_target':hex(e.jump(0x2cdfac,0x115e98,6)),'known_quality6_level':5,'known_quality26_frame3_level':4,'scope':'static MP4 level selection; caller-level stream acceptance and actual mux not tested'},'selected_bytes':[{'purpose':n,'va':hex(v),'length':z,'bytes':e.b[e.off(v):e.off(v)+z].hex()} for n,v,z in regions],'interpretation':'Static software representation and encoder-command construction only; no execution, complete profile acceptance or camera validation'}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('appfw',type=pathlib.Path);a.add_argument('--output',type=pathlib.Path,required=True);a.add_argument('--mpr',type=pathlib.Path);n=a.parse_args()
    d=inspect(n.appfw)
    if n.mpr:d['mpr']=inspect_mpr(n.mpr)
    n.output.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'sha256':d['sha256'],'main_hs_hd_enum':d['has_hs_hd_main_enum'],'converter_hs4k_routes':d['hs4k_converter_routes'],'output':str(n.output)},indent=2))
if __name__=='__main__':main()
