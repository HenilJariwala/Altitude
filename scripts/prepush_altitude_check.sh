#!/usr/bin/env bash
set -u

printf '%s\n' '============================================================'
printf '%s\n' 'ALTITUDE PRE-PUSH CHECK'
printf '%s\n' '============================================================'

if [ ! -d .git ]; then
  echo 'ERROR: Run this from the Altitude Git repository root.'
  exit 2
fi

FAIL=0

echo
echo '[1] Git status'
git status --short

echo
echo '[2] Branch and remotes'
printf 'Branch: '
git branch --show-current
git remote -v

echo
echo '[3] Tracked files that should normally stay out of Git'
TRACKED_BAD="$(git ls-files | grep -E '(^|/)(\.env$|\.venv/|__pycache__/|\.DS_Store$|test_reports/|data/chroma/|data/.*\.(db|sqlite|sqlite3)$)' || true)"
if [ -n "$TRACKED_BAD" ]; then
  echo "$TRACKED_BAD"
  echo 'WARNING: Review these before pushing.'
  FAIL=1
else
  echo 'PASS: no obvious local secrets/runtime data are tracked.'
fi

echo
echo '[4] Conflict markers'
if grep -RInE '^(<<<<<<<|=======|>>>>>>>)' app scripts knowledge_base 2>/dev/null; then
  echo 'WARNING: merge-conflict marker(s) found.'
  FAIL=1
else
  echo 'PASS: no merge-conflict markers found.'
fi

echo
echo '[5] Python compilation'
if python -m compileall -q app scripts; then
  echo 'PASS: Python compilation.'
else
  echo 'FAIL: Python compilation.'
  FAIL=1
fi

echo
echo '[6] Git whitespace/error check'
if git diff --check; then
  echo 'PASS: working-tree diff check.'
else
  echo 'FAIL: git diff --check.'
  FAIL=1
fi

echo
echo '[7] Quick feature test'
if [ -f scripts/test_all_features.py ]; then
  if python scripts/test_all_features.py --quick; then
    echo 'PASS: quick feature test.'
  else
    echo 'WARNING: quick feature test reported a failure. Review before push.'
    FAIL=1
  fi
else
  echo 'SKIP: scripts/test_all_features.py not found.'
fi

echo
echo '============================================================'
if [ "$FAIL" -eq 0 ]; then
  echo 'PRE-PUSH RESULT: PASS'
  exit 0
else
  echo 'PRE-PUSH RESULT: REVIEW REQUIRED'
  exit 1
fi
