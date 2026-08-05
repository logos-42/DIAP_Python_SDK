#!/usr/bin/env bash
# ============================================================================
# diap-sdk 一键发布脚本
#
# 用法:
#   bash scripts/release.sh          # 跑测试 + 构建 + 上传 PyPI + git tag
#   bash scripts/release.sh --skip-tests   # 跳过测试
#   bash scripts/release.sh --dry-run      # 只构建不上传
#
# 认证 (三选一):
#   1) ~/.pypirc 已配置 (推荐):
#        [pypi]
#        username = __token__
#        password = pypi-xxxx
#   2) 环境变量:
#        TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxxx bash scripts/release.sh
#   3) 交互输入: 脚本会提示粘贴 token
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

SKIP_TESTS=false
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --skip-tests) SKIP_TESTS=true ;;
    --dry-run) DRY_RUN=true ;;
  esac
done

# 当前版本 (从 diap/__init__.py 读取, 唯一事实来源)
VERSION=$(python3 -c "import diap; print(diap.__version__)")
echo "=== diap-sdk v$VERSION 发布 ==="

# 1. 测试
if [ "$SKIP_TESTS" = false ]; then
  echo ""
  echo "[1/4] 运行测试..."
  python3 -m pytest -q
fi

# 2. 构建
echo ""
echo "[2/4] 构建 wheel + sdist..."
rm -rf dist build *.egg-info
python3 -m build
ls -la dist/

# 3. 上传 PyPI
if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "[3/4] DRY-RUN: 跳过上传"
else
  echo ""
  echo "[3/4] 上传到 PyPI..."
  if [ -f "$HOME/.pypirc" ]; then
    python3 -m twine upload dist/*
  elif [ -n "${TWINE_PASSWORD:-}" ]; then
    TWINE_USERNAME="${TWINE_USERNAME:-__token__}" python3 -m twine upload dist/*
  else
    echo "未找到认证配置, 请执行以下任一方式:"
    echo "  A) 创建 ~/.pypirc:"
    echo "     printf '[pypi]\\nusername = __token__\\npassword = pypi-你的token\\n' > ~/.pypirc && chmod 600 ~/.pypirc"
    echo "  B) 环境变量:"
    echo "     TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-你的token bash scripts/release.sh"
    exit 1
  fi
fi

# 4. git tag + push
if [ "$DRY_RUN" = false ]; then
  echo ""
  echo "[4/4] git tag v$VERSION + push..."
  git add -A
  git commit -m "release: v$VERSION" || echo "(无新提交)"
  git tag -f "v$VERSION"
  git push origin main --tags
fi

echo ""
echo "=== 发布完成: https://pypi.org/project/diap-sdk/$VERSION/ ==="
