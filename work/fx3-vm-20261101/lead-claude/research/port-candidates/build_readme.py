import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/'platform-matrix.json').read_text());rows=m['models']
assert len(m['archive_downloads'])==11 and all(r.get('published_main_platform') for r in rows),'Collect all requested source baselines before final report'
out=['# Sony 固件/功能移植到经典 FX3：平台候选比较','',
'核查日期：2026-11-03；目标为经典 **ILME-FX3**。比较 8 个候选与 FX3 基线，只做 Sony 官方公开资料和 GPL 源码静态核查。','',
'**优先研究 FX3A，其次 A7S III，再次 FX30；FX5 是本组中跨平台差异最大的整套系统供体。** 其他候选的主 GPL 都落在 CXD90057 / Cortex-A35 ×4 / GIC-400 / Linux 4.9.337 这一公开源码基线，不能仅凭“较新机型”或“BIONZ XR”判断它们换了应用处理器平台。下面的排序是工程推断（B），并不表示任何机型可直接互刷。','',
'**若目的只是 BIG6 六宫格主页，经典 FX3 已有原生实现。** Sony 的说明明确列出 FX3 Ver.7.00、FX3A Ver.2.00、FX30 Ver.6.00 的 BIG6 门槛；无需以跨机型固件作为此前提。本轮仅核对说明，没有下载更新包或操作机身。[Sony 官方说明](https://www.sony.com/zh-cn/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx30/articles/00365338)','',
'## 证据范围与读法','',
'- **A**：直接读取的 Sony 分发源码、文件哈希/行号，或 Sony 官方规格/发布/支持页。源码结论只覆盖该型号关联的公开包及所查示例配置。','- **B**：平台/硬件差异的工程解释、候选排序，以及明确标出的“规格未列”推断。','- **未知**：实际机身选用的 DTB/defconfig、硅片修订、专有 HAL/IPC/ISP、校准、签名和存储密钥状态。公开文件相同不等于实际配置或二进制兼容。','',
'先读了用户指定的 [Stage133 方法先例](../../../../sony-firmware-20261024/stage133-FX5-source-availability-and-portability/README.md) 与 `code-portability-review.json`，再重新读取/哈希 FX3 与 FX5 已有本地 GPL 原包，并从各机型官方开源页取得本次表内版本。版本选自本次 [B2B 索引](https://oss.sony.net/Products/Linux/B2B/category01.html) / [DI 索引](https://oss.sony.net/Products/Linux/DI/category01.html)；不是声称所有地区当前机身固件的最新版本。','',
'## 主平台矩阵（A：型号关联公开源码）','',
'| 机型 / 所查 GPL 页 | SoC compatible | CPU / DTS 核数 | GIC | 内核 Makefile | 所查示例 TEE | OP-TEE / crypt_emmc 节点 |','|---|---|---|---|---|---|---|']
for r in rows:
 p=r['published_main_platform'];tee='启用' if p['TEE_in_selected_example_config'] else '未启用' if p['TEE_in_selected_example_config'] is False else '未确认'
 cpu=', '.join(x.replace('arm,','') for x in p['cpu_compatible'])+' ×'+str(p['cpu_nodes'])
 out.append(f"| [{r['model']}]({r['oss_page']['url']}) {r['source_release']} | `{', '.join(p['compatible'])}` | {cpu} | `{', '.join(p['gic_compatible'])}` | {p['kernel_version']} | {tee} | {'有 / 有' if p['OPTEE_node_in_primary_dtsi'] and p['crypt_emmc_node_in_primary_dtsi'] else '所查主 dtsi 未见 / 未见'} |")
out += ['',
'上表的 CXD90057 行读取 `arch/arm64/boot/dts/cxd/cxd90057.dtsi`，CPU 在 93/102/111/120 行，GIC 在 133 行，根 compatible 在 42 行；示例 `cxd90057_set_defconfig` 的 `CONFIG_NR_CPUS=4` 与 `# CONFIG_TEE is not set` 另有行号证据。FX5 读取 `cxd90xxx.dtsi`，相应根/CPU/GIC/OP-TEE 在 37、109/118/127/136、149、185 行，`crypt_emmc_init` 在 1117 行；`cxd90201_set.dts` 引用该 dtsi，示例 `cxd90201_set_defconfig` 开启 TEE/OP-TEE。这些字符串不独立证明 FX5 实装硅片的完整商业料号。','',
'FX5 既有 `cemmc-init` 公开代码还直接调用 TEE context/session/invoke 和 eMMC 密钥初始化接口，已重新哈希并保留三份选段。[本地源码证据](FX5-secure-storage-local-evidence.json) 证明存在安全存储初始化支持；**不证明任何实机当前加密布局或已取得解密/签名能力**。同样，FX3 等示例 TEE 关闭、主 dtsi 无 crypt_emmc，不等于物理机身完全没有安全世界或加密。','',
'### 共享文件与另列的 kernel-u','',
'| 主包机型 | 主 dtsi 与 FX3 字节相同 | 示例 defconfig 相同 | 根 Makefile 相同 |','|---|---|---|---|']
for r in rows:
 q=r['published_file_equality_to_FX3'];out.append('| '+r['alias']+' | '+' | '.join('是' if q[k] else '否' for k in ['dtsi_evidence','config_evidence','kernel_evidence'])+' |')
out += ['',
'该相同比较是逐文件 SHA-256，不把整个源包视为相同，也不把通用 SoC dtsi 当作完整型号板卡描述。包里另有 FPGA/QEMU 的 A35/A53 示例；它们没有用于上表的机身平台判定。完整文件哈希和原行在 [source-analysis.json](source-analysis.json) 与 [platform-matrix.json](platform-matrix.json)。','',
'| 官方另列包 | 内核 | 其中主平台示例 | 状态 |','|---|---|---|---|']
for r in rows:
 for a in r['platforms']:
  if '/linux-kernel-u.tar.gz' not in a['archive_url']:continue
  p=next(p for p in a['published_platform_files'] if p['production_platform_candidate'])
  out.append(f"| [{r['alias']} linux-kernel-u]({a['archive_url']}) | {a['kernel_version']} | `{','.join(p['root_compatible'])}` / {','.join(sorted(set(p['cpu_compatibles'])))} ×{p['cpu_nodes_in_file']} / `{','.join(p['gic_compatibles'])}` | 用途、是否选用未知 |")
out += ['',
'`-u` 只是公开包名，本轮没有构建/启动它，也没有证据把它解释为额外物理 CPU、当前相机内核或独立子系统。不得因为一个 GPL 页面列了两个内核就推定有两套硬件平台。','',
'## 硬件规格对照','',
'像素单位为 MP（百万）；“静/影/总”分别是官方列出的静态有效、视频有效、总像素，`?` 表示该项在所查表中没有单列。传感器“型号”列只写官方 Exmor 类别；**精确 IMX 料号均未从这些官方来源核实**，像素相近不当作同一颗传感器。','',
'| 机型 / 规格来源 | 发布/修订年 | 传感器类型与像素：静 / 影 / 总 MP | IBIS | EVF | SDI | 内置 ND | 卡槽 |','|---|---|---|---|---|---|---|---|']
for r in rows:
 mp=' / '.join('?' if r[k] is None else f'{r[k]:g}' for k in ['still_mp','movie_mp','total_mp'])
 if r.get('effective_max_mp'):mp+='；有效最大'+str(r['effective_max_mp'])
 year=str(r['year'])+('（宣布；上市延期）' if r['id']=='FX5' else '（型号修订）' if r['id']=='FX3A' else '')
 evf=r['evf'].replace('（B：规格未列）','*')
 out.append(f"| [{r['alias']}]({r['specification_page']['url']}) | {year} | {r['sensor']}；{mp} | {'5轴' if r['ibis'] else '无'} | {evf} | {'12G/6G/3G/HD' if r['id']=='FX6' else '未列*'} | {'电子可变 1/4–1/128' if r['id']=='FX6' else '未列*'} | {r['cards']} |")
out += ['',
'`*` 为 B：从所查官方完整规格/接口表未列该内置项作出的比较用推断，JSON 留为未知，不作拆机层面的绝对排除。没有把远程 App 的 ND 控制栏是否支持当成物理 ND 存在与否的依据。IBIS、像素、列明的 EVF 和卡槽为 A；FX6 无 IBIS 还由 [Sony 官方访谈](https://www.sony.jp/ichigan/a-universe/news/750/) 明确说明。FX6 的原配 LCD 不是电子取景器；FX5 可配外置 EVF 也不等于机身内置。','',
'FX3A 确实存在，[Sony 支持页](https://support.sony.jp/electronics/support/articles/00376946) 将 2025 年 5 月 FX3 停售与 FX3A 型号替换直接关联；本轮未定位精确的全球首销日。FX3A 的屏幕为 2,359,296 dots，经典 FX3 规格约 144 万 dots；即使其他公开规格接近，显示链和板级器件仍不能假设相同。','',
'FX5 在 [2026-07-22 公告](https://www.sony.jp/CorporateCruise/Press/202607/26-0722B/) 发布，随后 [2026-08-18 延期通知](https://www.sony.jp/pro-cam/info2/20260818.html) 撤回原上市日；本次读取的 [产品页](https://www.sony.jp/pro-cam/products/ILME-FX5/) 仍标 Coming Soon / 发售日未定。因此表中 2026 是宣布年，不能写成已在日本实际上市的确认年份。','',
'各机型发布年份来源：'+ '、'.join(f"[{r['alias']}]({r['release_page']['url']})" for r in rows if r.get('release_page'))+'。所有抓取 URL、时间、原 HTML SHA-256 与选段行号汇总于 JSON。','',
'## 移植难度排序（B：由易到难；全部仍缺二进制/实机证据）','',
'比较对象是“把整套系统或成像相关功能搬到经典 FX3 的相对工程工作量”；权重依次是主平台、成像硬件、外设/操控与私有应用依赖。没有可量化的成功概率。','',
'| 顺位 | 候选 | 理由及较合理的研究用途 |','|---|---|---|']
byid={r['id']:r for r in rows}
for rank in m['ranking']:
 out.append(f"| {rank['rank']} | {byid[rank['model_id']]['alias']} | {rank['reason']} **用途：**{rank['best_use']}。 |")
out += ['',
'**中段不是稳定的绝对名次。** FX6 / A7 IV、FX2 / A1 会随待移植的具体功能改变顺序：只比较 UI，FX2/FX30 的 Cinema Line 操作资源更有价值；只比较低像素全幅成像链，FX6 的研究顺位可以上升。FX2 的 AI、A1 的 8K/高速堆栈读出、FX6 的 ND/SDI、FX5 的新传感器/安全世界，不会因共享 ARM64 或菜单资源而变成 FX3 硬件能力。','',
'## 未关闭的关键问题','',
'1. FX3 参考是 Ver.7.00 GPL，不是对用户 7.02 当前 boot/DTB/ELF/内核配置的同机指纹读取；其他机型也只覆盖表内公开源码版本。','2. 仍未知每款机身实际所选 DTB、内存映射、板级修订、传感器料号/时序、协处理器固件及标定。完整相同 dtsi/defconfig 也不能消除这些缺口。','3. 未取得或比较本轮供体完整机身固件、专有应用/HAL/IPC/ISP、分区和启动签名链；因此没有二进制兼容结论、可刷包或刷写放行。','4. 未确认任何机身当前 TEE、eMMC 加密、密钥或恢复入口；不从公开示例配置推演已可解密、重签或跨机刷写。','5. 精确传感器 IMX 料号、本次“规格未列”项及 FX5 最终上市日仍保留未知。','6. 同平台候选的下一项可复核工作应围绕一个明确功能比较其依赖和硬件前提；“最近供体”本身不能回答是否真的增加目标录制模式。','',
'## 下载与复核记录','',
'只获取 Linux GPL 源码包以读取根 Makefile、Sony DTS/DTSI、defconfig；FX3/FX5 复用现有本地原包并重新哈希。**没有下载或修改相机固件更新包，没有触碰相机、VM/runtime，没有执行下载的 Sony 代码。** 新抓取包以 1 MiB HTTP Range 完整顺序组装，用服务器长度、Content-MD5 和本地完整 SHA-256 检查；中断/重试的输出未当作成功包。','',
'| 机型 / 源包直链 | 完整字节数 | SHA-256 |','|---|---:|---|']
for a in m['archive_downloads']:
 name='linux-kernel-u' if '-u.tar' in a['url'] else 'linux-kernel'
 out.append(f"| [{a['model']} / {name}]({a['url']}) | {a['bytes']} | `{a['sha256']}` |")
out += ['',
'已有 FX5 `cemmc-init` 复核原包 SHA-256：`'+m['FX5_cemmc_local_source_evidence']['archive_sha256_reverified']+'`；[来源直链]('+m['FX5_cemmc_local_source_evidence']['archive_url']+')。此包本轮仅本地读取。','',
'交付与证据入口：','',
'- [platform-matrix.json](platform-matrix.json)：9 行机型、主平台、源码原行/文件哈希、硬件规格、B 级排序、全部来源 URL/下载 SHA 与未知项。','- [source-analysis.json](source-analysis.json)：11 份内核源码包的 Makefile / DTS / defconfig 选段索引。','- [page-receipts.json](page-receipts.json)、[spec-page-receipts.json](spec-page-receipts.json)、`receipts/`：官方页 HTML 摘要和每包长度、Content-MD5/完整 SHA-256、提取成员摘要。','- `source-excerpts/`：未执行的 Sony 平台源码选段；`pages/`：公开 HTML 与 UTF-8 可读文本；`gpl-archives/`：本轮取得的 Linux GPL 临时原包。','- `collect_sources.py` / `range_collect.py` / `collect_specs.py` / `analyze_sources.py` / `build_matrix.py` / `build_readme.py`：只读公开抓取、选段和报告生成脚本，写入均限于本目录。','',
'复核状态：完整包和选段的 SHA-256、JSON 可解析性、9 机型/11 内核包覆盖与本地证据链接在 [validation.json](validation.json) 登记。这是静态资料验收，没有构建、启动、实机或功能移植验收。','']
(ROOT/'README.md').write_text('\n'.join(out))
print('wrote README.md',len(out),'lines')
