# 固定绑定（运行箭头本轮未执行）

```mermaid
flowchart TD
  A[r37 prepare_run] --> B[本r37 run-inputs/config与LOCAL-SOURCE冻结]
  B --> C[r37 common: root/profile/完整SOURCE校验]
  C --> D[r37 preflight: 继承冻结链与r36文件验证]
  D --> E[r37 launch_prepare 的固定argv模板]
  E --> F[r37同名runner + r35-diagnostic-package + snapshot-tail/N64]
  F --> G[固定r36 candidate与CPIO]
  F --> H[原QEMU/kernel/DTB与运行门]
  I[r37 Node tool_call相对URL] --> J[r37 return_adapter 新CORE pin]
  J --> K[r37 operate与本地operator/JS]
  K --> L[原r21允许依赖]
```

SOURCE冻结42项包含本CORE、return-tools及新selector；CORE37项避免adapter自引用。prepare在新run写完整SOURCE映射，common/adapter必须精确相等，不能接受仍指向旧r30的配置或不完整LOCAL映射。

实际新runner的24个项目模块路径和hash见ALLOWED-IMPORT-BINDING.json：5个关键模块（selector、web、ring、log、startup observation）来自本r37，其余允许的原依赖来自已冻结r21；原source40、delivery145和平台检查完整保留。Node实际导入的adapter是本r37/return-tools/return_adapter.py，OPERATE_SHA仍是未改动operate的原摘要，CORE pin精确更新。

原r30只作为只读源/对比输入，未调用其main。r36只引用不复制，固定CPIO与DTB按原加载地址使用，包manifest历史状态不重写。正常真实run的VM产物目录仍由原runner创建在TRY/runs；本轮没有执行该分支。
