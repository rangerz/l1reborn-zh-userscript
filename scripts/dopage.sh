#!/bin/zsh
# 一頁一個 commit：套字典 → build → test → commit → push
#   scripts/dopage.sh <page> <dict.py>
#   MSG="自訂 commit message" scripts/dopage.sh <page> <dict.py>
set -e
cd "$(dirname "$0")/.."
page=$1; dict=$2
[ -n "$page" ] && [ -n "$dict" ] || { echo "用法: scripts/dopage.sh <page> <dict.py>"; exit 2; }
python3 scripts/pagetool.py apply "$page" "$dict"
npm run build >/dev/null 2>&1 || { echo "BUILD FAIL: $page"; npm run build 2>&1 | grep -m1 Error; exit 1; }
npm test 2>&1 | grep -E '^ℹ fail' | grep -q 'fail 0' || { echo "TEST FAIL: $page"; exit 1; }
git add "data/translations/pages/$page.json" dist/l1reborn-zh.user.js
git commit -q -m "${MSG:-$page page translations}"
git push -q origin main
git log --oneline -1
