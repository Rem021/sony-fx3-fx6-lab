# r17 N64 单轮零键结果与 N1 描述性对照

2026-11-04。**本轮零键范围通过：真实首帧/待机OSD、v5尾段快照、修复后的cont回执字段、健康与恢复退出均有实际证据。** 仅此一轮，总guest阶段51.462641s，0键、0手动确认，无重试、无部署、无源/guest/平台/入口修改。交互与长稳未在本轮测试，单样本不证明性能改善或历史停帧根因。

run `v25gate-n64-r17-9829a474`；URL `http://127.0.0.1:54267/`；专用Chrome session `fx3r17-n64-54267`，1280×1200。runner PID82131、QEMU PID82256；host launch UUID **`3bfd7ffd-166d-408e-ab9d-e719f6bc85b1`**、tag **`0x8f45125ec4c50b81`**；浏览器Start独立request UUID **`8f4ab320-9e42-4340-8046-2db616dc2836`**。

## 冻结与执行

- host SOURCE-FREEZE SHA `267ac6e3080511aecb4a7e8ae549d6d2f7140f6bb43eaeada9e204aa497473c0`；交付清单 `9cfe744df158c209b8cf02719b41fc56015e3fd6ffc82e293943c5c31ed91116`；runner `845a1f2d33a00d10ede293d5e397c88f7b0e387460ce1f890475b5b18a4006f8`。启动前32源/36交付核验，通过；结束后32源/14固定输入独立重算一致。17项既有离线测试未重复。
- N64 candidate `96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672`；CPIO `aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9`；原DTB `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`；kernel `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`；实际QEMU `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`。
- 原4核/cortex-a35/5120MiB/MTTCG/noicount等平台值保留，实际命令在command.json。唯一参数 `--port 0 --max-minutes 3 --max-steps 32 --snapshot-tail --gate-publish-interval 64`。卷UUID正确、无占用、双锁free后启动；没有其它诊断开关。

## 时间、截图、原始读回

| 事件 | 实际证据 |
|---|---|
| 网页Start | 20:37:41.019Z，POST start HTTP202，一次 |
| 初始cont | Popen相对+0.639771s |
| 首份宿主导出帧 | seq1，Popen相对**39.805790..39.805956s**（同域单调时钟夹逼） |
| 首份浏览器带帧status | 20:38:21.132Z，Start后40.113s |
| 首张亲看图 | R17-N64-first-observed.png，mtime20:38:25.682627Z；HD/AF-C/AWB等待机OSD可辨识，页面0/32键 |
| 网页End | 20:38:29.620Z，HTTP202；Start后**48.601s**，180s内 |
| final ACK | 20:38:32.520Z，HTTP200，自然PAGE回执 |

HTTP时间为浏览器请求记录附实际状态码；receipt.created_utc=20:37:12.936627Z在浏览器等待之前，不能当guest起点。Popen单调起点夹在408346.517993708..408346.518159500；首次导出不等于最早原生提交。截图时PAGE尚显示starting，画面已经可见；后续runner记录standby_ready=true，未按guest键或手动确认。

初始seq1 raw/PNG身份仅由导出metadata保留（raw SHA `3a609a4d5b896bcb5622a25856834644ebef259cf3de280ddba31d93e8841fb4`、PNG `0a319c4e7c37c25f6079cfeb460c078d3d692257a1579fda966b1a82a9840515`），不能冒充当前磁盘raw就是该早期帧；后续完整待机raw/PNG已独立核为 `b10896e7772ab4eb12f434e8c8035ab19d41ffc4451acbe9c0ef9e0052e03051` / `e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4`。亲看网页PNG SHA `a069918f916b2c2489c1fb9e91726cc3e04e4960736d0b70c66c233bdb5a8b40`。这是软件OSD，不是实时取景或CP多层合成验收。

End前最后导出seq66。原End暂停态16MiB ring完整/有效，SHA **`8da14bc4092bfbdf3b90d932a8b2379efdad0b6f8e6d5f5d3087125008ee90ab`**；528 accepted events，busy drop0、坏槽0。独立64KiB UI bank SHA **`05719deeac2c627da1f3612adff5181a0b86a2c152401da4acf047bf201df810`**。这些原End读回先于尾段，原状态不被尾段替代。

## v5尾段及字段修正的实际验证

verdict **valid_nontransactional_tail_checkpoint**，errors空，capture25.422ms（2s预算）、含停机两读总27.742ms。host单调start408395.490278333、cont回执408395.492019041、ACK见到408395.515700333、paused证明408395.516265541、end408395.518020208。

guest PID**237** / root **`0x7eda4cad60`**，nonce **`0xf658a26d8edfe276`**，probe9/TID240，launch/tag匹配。两个976B文件逐字节相等，含192B header + **784B/98Q** payload，SHA均 **`e29aa1a0b3e053ea2e7ca2560b407b1f2af16797cb3e4435906fddc68d8b2b9f`**；独立header magic/version5/长度/commit、完整98Q、request重建SHA、FNV全部通过，FNV32 stored=computed=**`0x7cc03260`**。guest clock1 copy47187668000..47187900992ns，232992ns；统计clock7不与该域相减。

**新字段本轮实际通过：qmp_cont_attempted=true、qmp_cont_acknowledged=true，旧qmp_cont_sent字段不存在。** 与QMP pre-tail paused id163、cont id164同id ACK、running id165、stop id166、再paused id167完全一致。N1原r16回执中遗留sent=false原样保留，不改其历史。此次只覆盖成功cont分支，回复丢失/发送未知分支没有在本轮触发。

原生自检日志声明GPR31/SIMD32/NZCV/FPCR/FPSR/SP及NOP/CBNZ/BL通过；BOUND记录publication_interval=64、普通RAM权威统计和v5 ready。原End active bank0（+0x100）发布序号110；尾段mirror_skip0/selftest1/bound1，id5..11=`[991,922,69,68,968,964,991]`，gate_hist=`[0,1,68,323,274,325]`，last_a18=3，object_mismatch/root_change各0。完整98Q/字段名/ACK原字见R17-N64-SNAPSHOT-INDEPENDENT.json。发布序号是累计数，不是Hz、耗时或精确普通RAM末状态。

**snapshot_is_end_state=false**：额外诊断cont自然probe检查点，逐字段原子读取非事务一致；ACK后到停机的自然事件计数未知。两读相同证明slot不可变，不能证明原End时刻完整状态。尾段时间不计启动性能。

## 健康与清理

health/protocol/render/diagnostic/lifecycle全部passed，host error/early stop为空，0 key HTTP / 0 confirm HTTP / 0 native recv-done。无ready后原生省电或model power off；menu_verified=false保留。

API16原20s合同**1.824233s通过**：restore103-007-api16.bin为原16字节 `000b00b4fd7bbba9fd030091f35301a9`，SHA `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`；header F100FILE/control0x100c1ea9/status0/seen1，SHA `e8668d6dda28642898c97841bc9ae5d653e42b7924dc2a7675e5c6d6bb2e1cd6`；host未写原代码。native_unbind_return=0，QMP quit id200同id成功ACK及SHUTDOWN事件，exit0/reaped/PID absent。独立ps证实82131/82256消失，双锁free；网页finalACK=true，专用浏览器close且active=false/pid=null。

限定存储日志pre-run本地12:21:59–12:36:59、run12:37:36–12:38:37，均25s上限内exit0无匹配；不是一般存储可靠性证明。完整时间/HTTP/锁/输入/恢复验证在R17-N64-TIMELINE.json、WEB-HTTP、VERIFICATION与RUN-STORAGE文件中。

## 与封存N1的描述性对照

| 项目 | r16 N1（618bcb5b） | r17 N64（9829a474） |
|---|---:|---:|
| 实际guest键/手动确认 | 0/0 | 0/0 |
| 首份host导出帧相对Popen | 40.321419..40.321612s | 39.805790..39.805956s |
| Start→End | 51.952s | 48.601s |
| guest阶段总时长（含清理） | 54.619892s | 51.462641s |
| 原End镜像发布序号 | 8332 | 110 |
| 尾段id5/id7/id8 | 1171/121/119 | 991/69/68 |
| v5双读/98Q/FNV | passed | passed |
| 健康/恢复/回收 | passed | passed |

两个run不是同一时间窗口或同一状态轨迹，End由人工看到画面后触发；guest对象地址不同，host版本只修回执/标签，运行控制流相同也不使调度可重复。上述累计计数**不能直接作差、作比或当作性能收益**；N64配置减少镜像发布机会的设计不等于已测量成本降低。两次各一个样本均出帧，不能据此推断速度提升、零帧根因或因果关系。N1完整原结论已封存，未修改。

本零键run至此封存。后续另授权的交互轮必须使用独立run/证据，不能用正常退出替代交互通过。交互、长稳和性能因果在本轮仍未测；不部署。交付冻结在R17-N64-SHA256SUMS，校验见R17-N64-HASH-CHECK.txt。
