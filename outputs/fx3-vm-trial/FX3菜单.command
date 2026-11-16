#!/bin/zsh
# Local FX3 menu launcher; the original TRY2 launcher is retained separately.
set -euo pipefail
if (( $# > 1 )) || { (( $# == 1 )) && [[ "$1" != --check ]]; }; then
  print -u2 '仅支持双击启动，或 --check 检查入口。'
  exit 2
fi
script_dir="${0:A:h}"
repo_root="${script_dir:h:h}"
rel_runtime="work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r10-independent-diagnostics"
runtime=""
for cand_rt in \
  "${FX3_V25_RUNTIME_DIR:-}" \
  "$HOME/AI-Workspace/AI/Projects/Mac/$rel_runtime" \
  "$HOME/AI-Workspace/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/$rel_runtime" \
  "$repo_root/$rel_runtime" \
  "/Volumes/KAFU2T/AI/Projects/Mac/$rel_runtime"; do
  if [[ -n "$cand_rt" && -f "$cand_rt/run_trial_v25_diag_r3.py" ]]; then
    runtime="$cand_rt"
    break
  fi
done
if [[ -z "$runtime" ]]; then
  print -u2 'FX3 运行目录缺失（已探测内盘 AI-Workspace 与回退路径）；未启动模拟器。'
  exit 2
fi
if [[ "$runtime" == /Volumes/KAFU2T/* ]]; then
  volume_uuid="$(/usr/sbin/diskutil info -plist /Volumes/KAFU2T 2>/dev/null | /usr/bin/plutil -extract VolumeUUID raw -o - - 2>/dev/null)" || {
    print -u2 'KAFU2T 未挂载或无法识别；未启动模拟器。'
    exit 2
  }
  if [[ "$volume_uuid" != F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B ]]; then
    print -u2 '外盘身份不符；未启动模拟器。'
    exit 2
  fi
fi
python_bin=""
for cand_py in \
  "${FX3_PYTHON:-}" \
  "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" \
  "$HOME/.local/bin/python3" \
  "/opt/homebrew/bin/python3" \
  "/usr/local/bin/python3" \
  "$(command -v python3 2>/dev/null || true)" \
  "/usr/bin/python3"; do
  if [[ -n "$cand_py" && -x "$cand_py" ]]; then
    python_bin="$cand_py"
    break
  fi
done
if [[ ! -f "$runtime/run_trial_v25_diag_r3.py" || -z "$python_bin" || ! -x "$python_bin" ]]; then
  print -u2 'FX3 入口文件或 Python 3 缺失；未启动模拟器。'
  exit 2
fi
"$python_bin" -B - "$runtime" <<'PYCHECK'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
freeze = (root / 'SOURCE-FREEZE.json').read_bytes()
if hashlib.sha256(freeze).hexdigest() != '65db2b1048d62b07c656b2af56078227e2ca84d86960fe6ce643f2130dbbe9ce':
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
