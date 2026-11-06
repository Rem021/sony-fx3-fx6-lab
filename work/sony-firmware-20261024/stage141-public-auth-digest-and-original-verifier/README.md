# FX3 7.02：公开摘要提供者与原认证校验函数

2026-10-27。**固定公开材料已与 FX3 原库逐字节对应，CPU摘要提供者也已接通上一轮会话控制器和原 AArch64 校验函数。没有向相机发送认证、USB或驱动请求。** 本轮仍不证明实机认证、正常退出或救砖。

阶段140的19个成员已逐一复核，上一轮属于会话控制器实现及47个离线场景的进展。当前16项验收要求、授权及Mac-only约束保持。内置盘临时空间紧张期间继续使用既有项目的外置临时目录，没有清理其他数据。

## 固定来源与原字节对应

从 [PMCA固定提交](https://github.com/ma1co/Sony-PMCA-RE/tree/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0) 取得 constants.py、crypto.py和MIT许可，均先保留原字节/SHA，未导入或执行这些下载文件。见 [upstream-inputs.json](upstream-inputs.json)。

`constants.py` 的 SHA 为 `94bf081d3c1a51a60cf8fc214dce25a491413d4d786716460fde3fba832eb692`。仅通过 AST literal读取 SHA256表的三项512B材料，分别与原 `libsencore.so` 的 VA `0x55780`、`0x55580`、`0x55380` 完全相同。本轮没有打印材料，也没有取得或宣称取得Sony工厂私有密钥。

原 `xxhop` 返回挑战码8；`xxstep` 将挑战512B和该轮材料512B拼成1024B，经 `SEN_SSL_GenerateDigestData(type1)` 调用 SHA-256，然后比较32B结果。原调用者 `NinThread` 的轮寄存器从1开始递增到3；公开主机序列用索引0–2。新提供者显式对应这两个编号。

静态原函数、地址、输入组装、材料指纹和调用者寄存器见 [original-digest-review.json](original-digest-review.json)、[caller-round-review.json](caller-round-review.json)。原 CmdDecode 对命令值取低8位，这一行为已单独记录，没有用主机端完整16位解析替换原函数。

## CPU提供者实现

[public_digest_provider.py](public_digest_provider.py) 在构造时验证固定公开文件SHA并读取literal材料；`compute()`只接受挑战码8、轮索引0/1/2和512B不可变字节，返回32B SHA-256。数据读取完成之后，摘要计算不访问文件或设备。

`compute_inert_task()` 可接收阶段140的独立惰性摘要任务；会话控制器本身没有被修改，仍保留截止时间、发送额度与UNKNOWN语义。相机原校验函数的这条路径使用码8，因此该FX3专用提供者拒绝旧SHA1码2。下载的旧faulty-SHA1源码仅作公开来源参考，未执行，也没有把阶段140的测试摘要当成真实SHA1实现。

## 原函数离线验证

[test_provider_with_original.py](test_provider_with_original.py) 在 Unicorn 中执行三个未修改的原函数：xxstep、CmdDecode、SEN_SSL_GenerateDigestData。内存复制/比较及EVP摘要接口由明确声明的CPU桥提供，摘要桥使用主机SHA-256；没有运行相机自己的OpenSSL二进制，更没有运行完整NinThread或其历史/模式文件操作。

| 检查 | 结果 | 适用范围 |
|---|---|---|
| 三轮 × 八种声明挑战 | 24项返回0 | 原输入组装、轮材料和摘要比较在该夹具下相符 |
| 摘要翻转、用错轮材料、挑战变化 | 9项返回-2 | 原比较拒绝了这些不匹配输入 |
| 原轮号0/4 | 2项返回-3 | 未进入不支持的材料索引 |
| 挑战码2、客户端命令1、盐字段不一致 | 3项返回-1 | 原命令检查拒绝这些声明输入 |
| 新提供者无效输入及非literal来源 | 7项输入和1项AST表达式拒绝 | 只证明CPU输入边界，未尝试执行来源代码 |

随后将固定阶段140控制器 → 新公开摘要提供者 → 原校验函数接在一起，两次认证序列的六轮摘要均被原校验函数接受。总计169次原函数进入，输入包/挑战只读、写入区域、边界保护、保存寄存器及SP/返回均通过检查。

完整轨迹、原函数SHA和执行源码副本见 [run-original-verifier/results.json](run-original-verifier/results.json)。六轮集成中的挑战生成、最终认证接受应答、模式切换、驱动状态和物理确认都是夹具。**原摘要比较返回0不等于整机认证成功、命令表可用或所有写者已经结束。**

## 下一步与验收缺口

摘要材料/编号不再只靠测试占位函数。下一步实现并离线审查Mac传输层，确认单机身份、端点/包长、显式驱动接管与恢复、在途操作的真实结束判据及时间界限。真实后端应保持阶段140的无重试、迟到/未知结果和证据分层；当前还没有可执行的服务上机放行。

本轮仍缺实机认证、同机完整健康备份和79MB MAIN恢复、独立救援、1080p29.97 HEVC MAIN实录、音画同步、热/长录及冷启动验收。所有这些要求保持，未放行持久刷写。
