#!/usr/bin/env bash
# 1.0 前：sdist 审阅，**绝不** twine upload。
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf dist .pack-check
python3 -m pip install -q build
python3 -m build --sdist
TGZ=$(ls -1 dist/*.tar.gz | head -1)
echo "packed: $TGZ"
tar -tzf "$TGZ" | head -80
if tar -tzf "$TGZ" | grep -E '(\.env|credentials|\.pem$)' >/dev/null; then
  echo "pack-check: refuse — sensitive paths" >&2
  exit 2
fi
# 项目名 f2b
tar -tzf "$TGZ" | grep -q '/src/f2b/' || tar -tzf "$TGZ" | grep -q 'f2b/'
echo "PACK_CHECK_OK name=f2b (PyPI 预留)"
