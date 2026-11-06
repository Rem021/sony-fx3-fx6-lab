from fx3_native import *
import csv,hashlib,importlib.metadata,re,shutil,zipfile
OUT=ROOT/'outputs/h265-path-research'
app=Native('/lib/appFw.so');mpr=Native('/lib/libmpr.so');av=Native('/lib/libInfraAvbbc.so')
converter=json.loads((OUT/'converter-emulation-results.json').read_text(encoding='utf-8'))
downstream=json.loads((OUT/'mpr-downstream-emulation.json').read_text(encoding='utf-8'))
packet=json.loads((OUT/'encoder-packet-emulation.json').read_text(encoding='utf-8'))
converter_checks=all(all(v for k,v in c.items() if isinstance(v,bool)) for c in converter['checks'])
if not converter_checks or not all(downstream['checks'].values()) or not all(packet['checks'].values()):raise RuntimeError('An experimental check failed')

# Verify every delivered Ghidra entry against the unchanged source library.
shutil.copyfile(ROOT/'outputs/h265-analysis/ghidra-format-converter.c.txt',OUT/'app-original-converter.c.txt')
for filename in ['disasm-2e69180-2e6927c.txt','disasm-2e692c0-2e69368.txt','disasm-1693d40-1693e50.txt']:
    source=ROOT/'outputs/h265-analysis'/filename
    if source.exists():shutil.copyfile(source,OUT/filename)
checks=[]
for path in sorted(OUT.glob('*.c.txt')):
    text=path.read_text(encoding='utf-8');name=re.search(r'^Program: (.+)$',text,re.M)[1].strip()
    native={'appFw.so':app,'libmpr.so':mpr,'libInfraAvbbc.so':av}[name]
    for address,codehex in re.findall(r'===== ELF 0x([0-9a-f]+).*?Entry bytes: ([0-9a-f]+)',text,re.S):
        original=native.read(int(address,16),len(codehex)//2)
        checks.append({'file':path.name,'library':name,'ELF_VA':'0x'+address,'entry_matches_original':original.hex()==codehex})
if not checks or not all(c['entry_matches_original'] for c in checks):raise RuntimeError('Ghidra/source instruction mismatch')
(OUT/'ghidra-entry-verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')

offset=next(o+0x39895ae-a for a,z,o,name in app.sections if a<=0x39895ae<z)
candidate={
 'status':'offline_converter_prototype_only',
 'target':'Sony ILME-FX3 firmware 7.02, extracted /lib/appFw.so',
 'source_sha256':app.record['sha256'],
 'candidate_modification':{'ELF_VA':'0x39895ae','original_file_offset':offset,'expected_before_hex':'0a','in_emulator_after_hex':'53','length':1},
 'meaning':'In the normal XAVC HS 4K frame switch, route only ordinal 2 (29.97p) to the existing 60/50 quality-selection preamble, keeping the actual frame ordinal for common final conversion.',
 'primary_test_profile':{'width':3840,'height':2160,'frame_rate_numerator':30000,'frame_rate_denominator':1001,'codec':'HEVC / H.265','chroma':'4:2:2','bit_depth':10,'nominal_bitrate_bps':100000000,'model_record_setting_ordinal':16,'VideoParamComb':7,'DefStruct_FrameRate':3,'DefStruct_VQuality':12},
 'verified_scope':['Original converter assertion reproduced','Candidate converter returns requested frame rather than 59.94','Original app bitrate table agrees with original MPR conversion','MPR basic enum validation','MP4 metadata level selection','30000/1001 fraction conversion','Original SetEncOpenParam fills 3840x2160 / HEVC / 29.97 parameter packet'],
 'not_completed':['Menu availability/inhibition rules and a coherent user selection workflow','Live model refresh and state transitions','Hardware codec open/start or encoded bitstream production','VPS/SPS/PPS, actual GOP cadence, timestamps, audio synchronization and long recording','Image signing, update package rebuilding, or installability'],
 'artifacts':'No modified ELF, firmware or flash package is delivered. Candidate byte is changed only in volatile Unicorn memory by the accompanying experiment script.'
}
if app.read(0x39895ae,1)!=b'\x0a':raise RuntimeError('Candidate precondition mismatch')
(OUT/'candidate-plan.json').write_text(json.dumps(candidate,indent=2),encoding='utf-8')

labels={0:'59.94p',1:'50p',2:'29.97p',3:'25p',4:'23.98p',5:'119.88p',6:'100p',8:'invalid'}
qualities={8:'200M 4:2:2 10bit',16:'100M 4:2:2 10bit',17:'100M 4:2:0 10bit',24:'50M 4:2:0 10bit',30:'invalid'}
with (OUT/'converter-test-matrix.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    w=csv.writer(stream);w.writerow(['candidate_in_RAM','input_frame','input_record_setting','result','VideoParamComb','DefStruct_FrameRate','DefStruct_VQuality','instructions'])
    for row in converter['cases']:
        w.writerow([row['candidate_memory_patch'],labels[row['input_frame_ordinal']],qualities[row['input_record_setting_ordinal']],row['reason'],row['VideoParamComb'],row['DefStruct_FrameRate'],row['DefStruct_VQuality'],row['steps']])

versions={name:importlib.metadata.version(name) for name in ['unicorn','capstone','pyelftools']}
provenance={'platform':'Windows x64; no camera connection','tools':versions,'ghidra':'12.1.4 headless ELF import, selected functions only','libraries':[{'logical_path':n.record['path'],'source_bytes':len(n.blob),'sha256':n.record['sha256']} for n in [app,mpr,av]],'unicorn_primary_source':'https://github.com/unicorn-engine/unicorn/releases/tag/2.1.4','execution_boundary':'No syscall bridge, OS loader, camera application startup or hardware device emulation. Unknown execution/memory access stops; bounded instruction counts/timeouts.','emulation_adapters':['Application hash-container lookup replaced by its exact original 26-entry constant map; the map source and constructor reference are recorded. All eight tested key/value pairs also match original MPR instructions.','Application S&Q query fixed to normal movie mode.','MPR logging calls ignored.','Defined same-library PLT entries and data relocations resolved in isolated memory; external calls not forwarded.']}
(OUT/'experiment-provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')

report='''FX3 7.02：4K30 H.265 转换路径与编码参数离线研究
日期：2026-10-16

结论
已经补出一条可复核的“转换层候选路径”，并用原始 ARM64 指令仿真验证到编码器打开前的参数包：3840×2160、30000/1001 fps（29.97p）、100 Mbps、H.265、4:2:2 10bit。附带的 4:2:0 100 Mbps 输入也能经过相同转换链，但它的菜单质量选项尚未实现。
这比上一轮“只有不支持分支”的结论前进了一步；尚未形成相机可用的完整录制功能。真实硬件编码器没有被打开，没有生成 H.265 码流，也没有证明修改后的文件能够安装。
所有候选字节只改在仿真内存。原始 BODYDATA.DAT、提取的 appFw.so 和所有厂家模板均未修改；没有刷机或连接相机。

一、候选修改及其含义
目标：/lib/appFw.so；转换函数 ELF VA 0x2e68048。
普通 HS 4K 帧率分派表位于 0x39895ac，序号 2 对应 29.97p；原表字节 0a 使其转入 0x2e691e0 的断言路径。
实验将 ELF VA 0x39895ae 的单字节从 0a 改为 53，使这一项跳到 0x2e69304，复用现有 60/50p 的质量参数选择入口。
关键区别是只复用“码率/色彩参数组”，保留实际的输入帧率。共用的最终转换会将模型帧率序号 2 转为 DefStruct::FrameRate 3，后者由原始时间基函数输出 30000/1001；实验没有把 60p 视频伪装成 30p。
这个候选不修改 25p、既有帧率或 S&Q 的分派表。S&Q 功能没有作为本轮解锁目标验证。
具体目标哈希、字节前提及适用范围见 candidate-plan.json。候选只适用于本次精确哈希样本，未交付修改后的固件或 ELF。

二、原转换函数仿真结果
对照原始与候选内存各运行 8 种帧率 × 5 种质量输入，共 80 组。
- 原始 29.97p 输入：在第一次错误记录调用处停止，符合前一轮的静态断言路径。
- 候选 100M 4:2:2 10bit 输入：正常返回 VideoParamComb=7、FrameRate=3、VQuality=12。
- 候选 100M 4:2:0 10bit 输入：正常返回 VideoParamComb=5、FrameRate=3、VQuality=12。
- 59.94、50、25、23.98、119.88、100p 以及无效帧率的测试结果与原始对照一致；25p 仍被拒绝。
- 无效质量值仍被拒绝。候选仅使 29.97p 走入已有参数选择链，不是整体跳过错误检查。
所用输入为人工构造的函数参数，不代表相机菜单已经可以选到它们。完整矩阵见 converter-test-matrix.csv 和 converter-emulation-results.json。

三、码率映射的来源已核实
应用层质量表的原始常量位于 .rodata 0x39898b0..0x3989980，共 26 对 (Mbps, DefStruct::VQuality)。初始化代码在 0x1693d8c 设置表起点，0x1693dac 设置长度 0xd0，0x1693dbc 将其放入 0x968b890 对应的 C++ 容器。
例如 0x3989918 明确保存 (100,12)，相邻还有 (150,13)、(50,14)。原始 libmpr.so 的 GetVQuality(100) 也返回 12，GetVideoBitrate(12) 返回 100000 kbps。
仿真替换的是未启动应用时尚未建立的哈希容器查找，不是自行猜测码率枚举。具体常量及初始化引用见 app-quality-map-evidence.json；仿真结果中另保存了完整 26 对常量。

四、继续追到 MPR 与编码器接口
1. 基础检查：libmpr.so 的 CheckMovieRecParam（0xcc4d4）对候选的 VPC 5/7、FrameRate 3、VQuality 12 返回 0；无效帧率 12 或质量 255 返回错误 3。这个检查主要检查字段是否为无效枚举，不等同于硬件能力认证。
2. 封装档位：XavcsMovieWriter::ConvertVPCToLevel（0x115e78）对两种 HEVC UHD 组合和 29.97p 都写入现有 level 枚举 7；本轮保持该原始枚举，不擅自重定义 HEVC level。
3. 时间基：ConvertFrameRateToNumerAndDenom（0x2c0de8）真实返回 30000、1001；ConvertFrameRateForCodec（0x2c0d04）保留 30p 档与 NTSC 标志。
4. 实际参数包：SetEncOpenParam（0xd13f8）及其同库转换函数在仿真中正常返回。输出宽高为 3840/2160，codec 字节 0x66=15（沿用 HEVC Long GOP 转换分支），帧率字节 0x80=3，NTSC 字节 0x81=1，质量字节 0x82=49；4:2:2 的色彩字节 0x94=2，bit-depth 字节 0x95=1。对应的 60p 对照使用相同 codec、质量、色彩和深度字段，帧率仍能区分。
5. 更下游的 libInfraAvbbc.so 已定位 EncOpenAstra/EncOpen2Astra/MultiEncOpen 的 SetParameter 与 SetAvailableFormat，相关定点反编译已保存。它们继续分派命令及资源管理；本轮没有运行这类带状态对象的序列，也没有进入硬件编码过程。
下游函数证据见 mpr-downstream-emulation.json、encoder-packet-emulation.json、mpr-encoder-parameters.c.txt、avbbc-encoder-boundary.c.txt。

五、仿真范围与实际缺口
使用 Unicorn 2.1.4 执行选定 ARM64 指令，设置了指令数、时间及地址访问边界。没有操作系统/系统调用转发、USB、相机连接、完整应用启动或硬件设备模拟。日志调用被忽略；同库链接由原始符号/重定位解析；参数包中的缓冲区地址和非关键状态字段为合成数据。
仍未补齐或验证：
- 菜单对 HS 4K 30p 的排斥/可用性规则、质量选择界面，以及实时模型状态切换。原代码没有独立 HS 4K 30p 质量组；候选暂借 60/50 组，不能直接当成完整用户设置流程。
- 实际硬件编码器是否接受参数包；微码/驱动是否还有能力表、码率或资源约束。
- 输出 VPS/SPS/PPS、真实 GOP 长度与节奏、帧间预测、封装时间戳、音画同步和长时间录制稳定性。本轮只定位到 Long GOP 类别，未证明实际 GOP 参数可用。
- 镜像签名、更新包重建、启动和安装链。没有进行这些操作，也没有生成可刷写文件。

六、如何使用本轮成果
主候选是 4K 29.97p、100M、4:2:2 10bit 的 HEVC 路径。100M 4:2:2 本就是现有 HS 4K 60/50 参数组中的质量，便于下一轮先集中处理帧率与菜单关系；4:2:0 100M 的质量菜单还需要额外处理。
可以继续离线追踪菜单排斥数据、SetAvailableFormat 和 MC 编码命令的能力约束。现有证据说明转换层和参数准备层可以接通；没有足够证据宣称实机内录已经解锁。

附件和复核
- candidate-plan.json：精确候选与未完成部分；不是刷机包。
- converter-test-matrix.csv：80 组原始/候选转换对照。
- converter-emulation-results.json：指令步数、输出枚举和容器替代说明。
- mpr-downstream-emulation.json：15 次原始 MPR 函数调用及检查。
- encoder-packet-emulation.json：两种 HEVC 组合 × 29.97/59.94p 共 4 个参数包。
- ghidra-entry-verification.json：随附定点反编译的函数入口字节与原 ELF 的核对。
- experiment-provenance.json：库哈希、工具版本、替代接口和执行边界。
- analysis-source/：本轮精确脚本，供在当前工作区复现；不含修改或写入相机的流程。
全部地址为原 ELF VA；Ghidra 导入基址为 0x100000，界面/反编译地址需相应加上该偏移。反编译器的类型和未命名函数属于推测，结论以原指令、常量及仿真输出为准。
本轮直接使用 Ghidra、Capstone 与 Unicorn。REA 的 Windows 接口不接纳此 ARM64 ELF，未将这些补充分析标记为成功运行 REA 固件后端。
'''
(OUT/'FX3-7.02-4K30-H265转换路径研究.txt').write_text(report,encoding='utf-8-sig')

source_dir=OUT/'analysis-source';source_dir.mkdir(exist_ok=True)
for name in ['fx3_native.py','trace_h265_downstream.py','extract_mpr_tables.py','emulate_h265_converter.py','emulate_mpr_downstream.py','emulate_encoder_packet.py','trace_encoder_api.py','query_avbbc_helpers.py','verify_app_quality_map.py','locate_h265_gate.py','run_native_ghidra.ps1','build_h265_path_report.py']:
    shutil.copyfile(ROOT/'work'/name,source_dir/name)
shutil.copyfile(ROOT/'work/ghidra-scripts/Fx3ReadOnly.java',source_dir/'Fx3ReadOnly.java')
(source_dir/'README.txt').write_text('These are source snapshots from work/, not a standalone emulator kit. Run the work/ originals in the existing workspace; fx3_native.py verifies extracted library hashes. Dependencies: work/python-packages (unicorn==2.1.4, capstone==5.0.9, pyelftools==0.33), prior outputs/config-analysis inventory, original extracted usr files, and the portable Ghidra/JDK project for optional decompilation.\nRun emulate_mpr_downstream.py and emulate_encoder_packet.py to regenerate experiments; they also refresh the converter matrix. No script writes a camera, patched ELF or firmware package. Candidate byte is applied only to Unicorn volatile memory.\n',encoding='utf-8')
manifest=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name not in ['file-manifest.json','delivery-verification.json']:
        manifest.append({'path':path.relative_to(OUT).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'file-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
archive=ROOT/'outputs/FX3-7.02-4K30-H265离线研究证据.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name!='delivery-verification.json':z.write(path,path.relative_to(OUT).as_posix())
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise RuntimeError('Archive CRC failed')
body=ROOT/'outputs/firmware/BODYDATA.DAT';digest=hashlib.sha256()
with body.open('rb') as stream:
    for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
expected='f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854'
if digest.hexdigest()!=expected:raise RuntimeError('Original firmware changed')
verification={'all_checks_passed':True,'converter_cases':len(converter['cases']),'downstream_calls':len(downstream['cases']),'parameter_packets':len(packet['cases']),'ghidra_entries_verified':len(checks),'original_libraries_match_extraction_hashes':True,'BODYDATA_unchanged_sha256':digest.hexdigest(),'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_crc_passed':True,'no_patched_firmware_created':True}
(OUT/'delivery-verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
print(json.dumps(verification,indent=2))
