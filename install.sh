#!/usr/bin/env bash
# 홈택스 도움 무료판 — macOS/Linux/Git Bash 진입점. 실제 설치는 install.py가 수행한다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo python
    return 0
  fi
  echo 'Python 3.10 이상이 필요합니다. Windows는 py -3 install.py 를 사용하세요.' >&2
  exit 1
}
INSTALLER="$HERE/install.py"
if [ ! -f "$INSTALLER" ]; then
  echo 'install.py가 없습니다. 패키지를 다시 확인하세요.' >&2
  exit 1
fi
PY="$(pick_python)"
exec "$PY" -B "$INSTALLER" "$@"
