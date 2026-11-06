#!/bin/zsh
# Local FX3 menu launcher; the original TRY2 launcher is retained separately.
set -euo pipefail
if (( $# > 1 )) || { (( $# == 1 )) && [[ "$1" != --check ]]; }; then
  print -u2 '仅支持双击启动，或 --check 检查入口。'
  exit 2
fi
volume_uuid="$(/usr/sbin/diskutil info -plist /Volumes/KAFU2T 2>/dev/null | /usr/bin/plutil -extract VolumeUUID raw -o - - 2>/dev/null)" || {
  print -u2 'KAFU2T 未挂载或无法识别；未启动模拟器。'
  exit 2
}
if [[ "$volume_uuid" != F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B ]]; then
  print -u2 '外盘身份不符；未启动模拟器。'
  exit 2
fi
runtime='/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r11-visible-rejection'
python_bin='/Library/Frameworks/Python.framework/Versions/3.14/bin/python3'
if [[ ! -f "$runtime/run_trial_v25_diag_r3.py" || ! -x "$python_bin" ]]; then
  print -u2 'FX3 入口文件或 Python 3.14 缺失；未启动模拟器。'
  exit 2
fi
"$python_bin" -B - "$runtime" <<'PYCHECK'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
freeze = (root / 'SOURCE-FREEZE.json').read_bytes()
if hashlib.sha256(freeze).hexdigest() != '8be8343b234d5d579e75fcf86b002ed675376d0de896cb6925fbf6af64454985':
    raise SystemExit('FX3 版本清单不符；未启动模拟器。')
for name, expected in json.loads(freeze)['files_sha256'].items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
        raise SystemExit('FX3 入口校验失败：' + name + '；未启动模拟器。')
PYCHECK
if [[ "${1:-}" == --check ]]; then
  print '入口检查通过；未启动网页或模拟器。'
  exit 0
fi
print 'FX3 菜单：本轮上限 4096 次按键／60 分钟。'
print '请打开下方打印的本机网址，再在网页点击「开始本轮模拟器」。'
print '每次按键后看清目标画面；网页提示时点击「我已看图，继续」。'
print '结束时请点击网页「结束试用」，等待终端输出退出回执；仅关闭网页不会停止模拟器。'
print '已有运行占用时请等待，不要删除锁文件。'
exec "$python_bin" -B "$runtime/run_trial_v25_diag_r3.py" --port 0 --max-minutes 60 --max-steps 4096
