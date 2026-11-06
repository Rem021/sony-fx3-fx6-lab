import datetime,hashlib,json,pathlib,re
from analyze_sources import ROOT,analyze
MODELS={
 'FX3':{'model':'ILME-FX3','alias':'经典 FX3','source_release':'Ver.7.00','year':2021,'sensor':'35mm 全画幅 Exmor R CMOS，35.6 × 23.8 mm','still_mp':12.1,'movie_mp':10.3,'total_mp':12.9,'ibis':True,'evf':'无内置 EVF（B：规格未列）','cards':'2 × CFexpress Type A / SD UHS-II 复合槽','display_dots':1440000},
 'FX3A':{'model':'ILME-FX3A','alias':'FX3A','source_release':'Ver.2.00','year':2025,'sensor':'35mm 全画幅 Exmor R CMOS，35.6 × 23.8 mm','still_mp':12.1,'movie_mp':10.3,'total_mp':12.9,'ibis':True,'evf':'无内置 EVF（B：规格未列）','cards':'2 × CFexpress Type A / SD UHS-II 复合槽','display_dots':2359296},
 'A7SIII':{'model':'ILCE-7SM3','alias':'A7S III','source_release':'Ver.5.00','year':2020,'sensor':'35mm 全画幅 Exmor R CMOS，35.6 × 23.8 mm','still_mp':12.1,'movie_mp':None,'total_mp':12.9,'ibis':True,'evf':'内置 0.64 英寸 OLED，9,437,184 dots','cards':'2 × CFexpress Type A / SD UHS-II 复合槽'},
 'FX30':{'model':'ILME-FX30','alias':'FX30','source_release':'Ver.6.00','year':2022,'sensor':'APS-C / Super35 Exmor R CMOS，23.3 × 15.5 mm','still_mp':26.0,'movie_mp':20.1,'total_mp':27.0,'ibis':True,'evf':'无内置 EVF（B：规格未列）','cards':'2 × CFexpress Type A / SD UHS-II 复合槽'},
 'FX6':{'model':'ILME-FX6V/FX6T','alias':'FX6','source_release':'V6.00','year':2020,'sensor':'35mm 全画幅 Exmor R CMOS','still_mp':None,'movie_mp':10.26,'total_mp':12.9,'ibis':False,'evf':'无内置 EVF；原配 3.5 英寸 LCD 不是 EVF','cards':'2 × CFexpress Type A / SD UHS-II 复合槽'},
 'A7IV':{'model':'ILCE-7M4','alias':'A7 IV','source_release':'Ver.6.00','year':2021,'sensor':'35mm 全画幅 Exmor R CMOS，35.9 × 23.9 mm','still_mp':33.0,'movie_mp':None,'total_mp':34.1,'ibis':True,'evf':'内置 0.5 英寸 OLED，3,686,400 dots','cards':'槽1 CFexpress Type A / SD UHS-II；槽2 SD UHS-II'},
 'FX2':{'model':'ILME-FX2B/FX2','alias':'FX2','source_release':'V1.00','year':2025,'sensor':'35mm 全画幅 Exmor R CMOS，35.9 × 23.9 mm','still_mp':33.0,'movie_mp':27.6,'total_mp':34.1,'ibis':True,'evf':'内置可俯仰 0.5 英寸 OLED，3,686,400 dots','cards':'槽1 CFexpress Type A / SD UHS-II；槽2 SD UHS-II'},
 'A1':{'model':'ILCE-1','alias':'A1 / α1','source_release':'Ver.4.00','year':2021,'sensor':'35mm 全画幅堆栈式 Exmor RS CMOS，35.9 × 24.0 mm','still_mp':50.1,'movie_mp':None,'total_mp':50.5,'ibis':True,'evf':'内置 0.64 英寸 OLED，9,437,184 dots','cards':'2 × CFexpress Type A / SD UHS-II 复合槽'},
 'FX5':{'model':'ILME-FX5','alias':'FX5','source_release':'未标机身版本的 GPL 页','year':2026,'sensor':'35mm 全画幅堆栈式 Exmor RS CMOS，35.9 × 24.0 mm','still_mp':None,'movie_mp':None,'effective_max_mp':16.6,'total_mp':18.2,'ibis':True,'evf':'机身不内置；可选外置 DVF-EL1，0.58 英寸 OLED，约707万 dots','cards':'2 × CFexpress 2 Type A / SDXC UHS-II 复合槽'},
}
RANKS=[
 ('FX3A',1,'第一梯队','所查 GPL 平台与 FX3 相同；官方规格的传感器类别、尺寸、像素、IBIS、双复合卡槽和机身用途最近。LCD 从约144万变为2359296 dots、型号标识及潜在器件修订仍需适配，不能直接互刷。','显示/资源和同系列应用差异研究；新增功能收益可能有限'),
 ('A7SIII',2,'第一梯队','同类 12.1MP 全画幅、相同尺寸和总像素，IBIS/双复合槽接近；所查 GPL 平台相同。EVF、操控、冷却和消费级静态/视频应用路径与 FX3 不同，官方规格不能证明同一传感器料号。','同代图像/录制控制逻辑比较'),
 ('FX30',3,'第二梯队','所查 GPL 平台相同，Cinema Line 操控、冷却、IBIS 和双复合槽接近；APS-C 26MP / 视频20.1MP 与 FX3 的低像素全幅相差很大，传感器读出和 ISP 标定不能照搬。','菜单/界面/操作资源参考优先于成像链移植'),
 ('FX6',4,'第三梯队，中段次序依目标变化','所查主平台及低像素全幅规格接近；但 FX6 无机身 IBIS、带 SDI/可变 ND、专业接口和录制/控制路径不同，并另附 kernel-u 源码。ND/SDI 是 FX3 缺少的硬件，不能靠固件获得。','专业菜单/录制状态机参考；若只研究成像链，可提高优先级'),
 ('A7IV',5,'第三梯队，中段次序依目标变化','所查 GPL 平台相同、全幅和 IBIS 接近；33MP 读出/ISP、EVF、无风扇机身与单 CFe 槽布局不同。保留 FX3 成像驱动的单项 UI 研究可排在 FX6 前。','同代应用机制研究，不提供高像素/超采样硬件能力'),
 ('FX2',6,'第四梯队，中段次序依目标变化','主 GPL 仍为 CXD90057/A35/GIC-400/4.9.337；33MP/视频27.6MP、AI 处理单元、俯仰 EVF、单 CFe 槽、控制/流媒体依赖有差异。另列的 kernel-u 版本不证明另一颗处理器或实际选用状态。BIG6 是较近的 UI 参考，AI 能力不能预设可移植。','UI 布局参考；单项 UI 可排在 A7 IV/FX6 前'),
 ('A1',7,'第四梯队，中段次序依目标变化','所查主 GPL 平台接近仍不抵消 50.1MP 堆栈传感器、8K/高速读出、EVF 和相应 ISP/缓冲链差异。静态平台共性只支持源码比对。','同代基础组件和接口比较'),
 ('FX5',8,'第五梯队','A53/GIC-v3/5.15 + OP-TEE/crypt_emmc 与 FX3 的 A35/GIC-400/4.9 示例明确跨平台；BIONZ XR2、新堆栈传感器、显示、电池、网络/音频架构也不同。属于完整 BSP/安全世界/专有 HAL 适配。','仅作产品/交互参考，当前最不适合整套系统供体'),
]
def evidence_text(page,terms):
 p=ROOT/page['text_path'];ls=p.read_text().splitlines()
 return [{'line':i+1,'text':s[:650]} for i,s in enumerate(ls) if any(t in s for t in terms)]
def main():
 pages=json.loads((ROOT/'page-receipts.json').read_text())['pages'];pm={p['model']:p for p in pages}
 specs=json.loads((ROOT/'spec-page-receipts.json').read_text());sm={p['id']:p for p in specs['pages']}
 receipts=[json.loads(p.read_text()) for p in sorted((ROOT/'receipts').glob('*-kernel*.json'))]
 analyses=[analyze(r) for r in receipts];(ROOT/'source-analysis.json').write_text(json.dumps(analyses,indent=2)+'\n')
 results=[]
 for key,meta in MODELS.items():
  row={'id':key,**meta,'oss_page':pm[key],'specification_page':sm.get(key+'-spec'),'release_page':sm.get(key+'-release'),'evidence_grade':'A for extracted source / official specifications; B for portability ranking and stated absence inferences','exact_sensor_IMX_part_number':None,'sensor_part_number_status':'Not disclosed in the inspected official specifications; no same-die claim from equal pixels or Exmor name.'}
  row['platforms']=[a for a in analyses if a['model']==key]
  main=next((a for a in row['platforms'] if '/linux-kernel.tar.gz' in a['archive_url']),None)
  if main:
   primary=next((p for p in main['published_platform_files'] if p['production_platform_candidate']),None)
   if primary:
    config=next((c for c in main['published_configs'] if c['path'].endswith(('cxd90057_set_defconfig','cxd90201_set_defconfig'))),None)
    cfg='\n'.join(x['text'] for x in config['matches']) if config else ''
    row['published_main_platform']={'compatible':primary['root_compatible'],'cpu_compatible':sorted(set(primary['cpu_compatibles'])),'cpu_nodes':primary['cpu_nodes_in_file'],'gic_compatible':primary['gic_compatibles'],'kernel_version':main['kernel_version'],
      'TEE_in_selected_example_config':True if 'CONFIG_TEE=y' in cfg else False if '# CONFIG_TEE is not set' in cfg else None,
      'OPTEE_in_selected_example_config':True if 'CONFIG_OPTEE=y' in cfg else False if '# CONFIG_OPTEE is not set' in cfg else None,
      'OPTEE_node_in_primary_dtsi':primary['optee_node'],'crypt_emmc_node_in_primary_dtsi':primary['crypt_emmc_node'],
      'physical_encrypted_eMMC':None,'scope':'Published primary SoC dtsi and one published example defconfig, not a measurement of shipping body configuration.','grade':'A','dtsi_evidence':primary['evidence'],'config_evidence':config,'kernel_evidence':main['kernel_version_evidence']}
  row['shipping_selected_dtb_verified']=False;row['shipping_kernel_or_security_state_measured']=False
  row['sdi']={'value':True if key=='FX6' else None,'grade':'A' if key=='FX6' else 'B','note':'12G/6G/3G/HD-SDI, BNC ×1' if key=='FX6' else 'Official interface specification does not list SDI; treated as absent for this comparison, not a board inspection.'}
  row['internal_nd']={'value':True if key=='FX6' else None,'grade':'A' if key=='FX6' else 'B','note':'Electronic variable ND 1/4–1/128' if key=='FX6' else 'Not listed in inspected official specification; no hardware presence claimed. External filter/metadata or app ND control support is not physical internal ND evidence.'}
  if row['specification_page']:
   row['hardware_line_evidence']=evidence_text(row['specification_page'],['撮像素子','有効画素','総画素','スロット','記録媒体','メディア','CFexpress','イメージセンサーシフト','総ドット数','SDI出力','NDフィルター','ビューファインダー','ドット数'])
  if key=='FX6':row['ibis_absence_source']=sm.get('FX6-IBIS')
  if key=='FX5':
   row['year_note']='Announced 2026-07-22; Japan launch postponed 2026-08-18 and product page still Coming Soon / date undecided when checked. This is announcement year, not confirmed shipping year.'
   row['launch_delay_source']=sm.get('FX5-delay');row['current_product_source']=sm.get('FX5-product')
  if key=='FX3A':
   row['year_note']='Official Sony support says FX3 discontinued May 2025 and model changed to FX3A; exact first worldwide sale date not established.'
   row['year_source']=sm.get('FX3A-change')
  results.append(row)
 baseline=next(r['published_main_platform'] for r in results if r['id']=='FX3')
 for row in results:
  p=row.get('published_main_platform')
  if p:
   row['published_file_equality_to_FX3']={k:p[k]['sha256']==baseline[k]['sha256'] if p[k] and baseline[k] else None for k in ['dtsi_evidence','config_evidence','kernel_evidence']}
 matrix={'schema_version':1,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'ILME-FX3 classic; published Ver.7.00 GPL baseline; not exact measured 7.02 body configuration',
  'scope':'Public official pages and GPL static metadata only; no camera/runtime, no camera firmware package download or modification, no downloaded code execution.',
  'evidence_grades':{'A':'Direct inspected Sony-distributed source, hash/line evidence, or official Sony page; scoped to exactly what it states.','B':'Engineering inference / ranking / absence inference; not hardware or binary compatibility proof.'},
  'models':results,'ranking':[{'model_id':m,'rank':n,'tier':t,'grade':'B','reason':why,'best_use':use} for m,n,t,why,use in RANKS],
  'common_unknowns':['Selected shipping DTB and defconfig; exact silicon stepping and RAM/board wiring','Private sensor/ISP/coproc firmware, HAL/IPC ABI and calibration','Boot/signature/model validation and storage partition/key layout','No binary transplant, full camera system boot or physical compatibility tested','Exact sensor IMX part numbers unverified in these official sources','A missing crypt_emmc node or CONFIG_TEE=n is not proof the physical body has no encryption or secure world'],
  'all_oss_page_downloads':pages,'all_spec_and_release_page_downloads':specs,
  'archive_downloads':[{'model':r['model'],'url':r['url'],'bytes':r['bytes'],'sha256':r['sha256'],'reused_local_archive':r.get('reused_local_archive'),'content_md5_verified':r.get('content_md5_verified'),'transport':r.get('transport','Reused existing local archive and rehashed this turn'),'receipt':'receipts/'+r['model']+('-kernel-u.json' if '-u.tar' in r['url'] else '-kernel.json')} for r in receipts],
  'FX5_cemmc_local_source_evidence':json.loads((ROOT/'FX5-secure-storage-local-evidence.json').read_text()),
  'native_feature_reference':{'url':'https://www.sony.com/zh-cn/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx30/articles/00365338','verified_via':'web search/open content; local HTTP capture returned 403, so no local page SHA','fact':'Official Sony article dated 2025-08-27 states BIG6 requires FX3 Ver.7.00, FX3A Ver.2.00, FX30 Ver.6.00.','grade':'A'},
  'method_precedent':{'README':str(ROOT.parents[3]/'sony-firmware-20261024/stage133-FX5-source-availability-and-portability/README.md'),'note':'User-designated Stage133 read first; baseline facts reverified from local GPL bytes rather than copied as shipping-body claims.'},
  'camera_or_runtime_touched':False,'camera_firmware_package_downloaded_or_modified':False,'downloaded_code_executed':False}
 (ROOT/'platform-matrix.json').write_text(json.dumps(matrix,ensure_ascii=False,indent=2)+'\n')
 print('wrote platform-matrix.json',len(results),'models',len(receipts),'archive receipts')
if __name__=='__main__':main()
