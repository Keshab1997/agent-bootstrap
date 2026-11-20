#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  captain_up.sh — one-shot Captain boot (Keshab-approved 2026-11-20).
#
#    bash captain_up.sh [DST]        # default DST=/home/user/agent-bootstrap
#    # or from an empty sandbox:
#    bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/captain_up.sh)
#
#  Does, in order:
#    1. ensure the bootstrap clone (clone if missing; repair a dropped
#       .git/config by reattaching origin — never re-clone over work)
#    2. restore GitHub pairing (reuse saved token -> refresh -> resume a
#       pending device code). A device code is printed ONLY when a human
#       browser approval is truly needed — show it to Keshab as a headline.
#    3. print the connection status (expect: verdict PAIRED / HTTP 200)
#    4. fast-forward main (never resets local work)
#    5. print the Captain playbook (CAPTAIN_PROMPT.md + GITHUB_BRIEFS.md)
#
#  Safe to re-run at any time; every step is idempotent.
# ---------------------------------------------------------------------------
set -euo pipefail

DST="${1:-/home/user/agent-bootstrap}"
REPO="https://github.com/Keshab1997/agent-bootstrap"

if [ ! -f "$DST/gh_app.py" ]; then
  echo "== cloning $REPO -> $DST"
  git clone "$REPO" "$DST"
fi
cd "$DST"

# Sandbox trap: .git/config can vanish between turns ("not a git repository").
# Reattach it; do NOT re-clone and do NOT touch secrets/.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
   || ! git remote get-url origin >/dev/null 2>&1; then
  echo "== repairing dropped git config"
  [ -d .git ] || git init -q
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REPO.git"
fi
git config core.fileMode false
git config user.name  "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
HELPER='!f(){ echo username=x-access-token; echo "password=$(cat '"$DST"'/secrets/gh_token.txt)"; }; f'
git config credential.helper "$HELPER"

echo "== pairing (reuse -> refresh -> resume pending code)"
python3 gh_app.py connect
python3 gh_app.py status

echo "== fast-forward playbook (ff-only; local work is never reset)"
if git fetch --quiet origin main 2>/dev/null && [ "$(git branch --show-current 2>/dev/null)" = main ]; then
  git merge --ff-only origin/main >/dev/null 2>&1 \
    || echo "WARN: main could not fast-forward (local commits?); keeping local state"
else
  echo "WARN: fetch failed or not on main; continuing with the local copy"
fi

echo
echo "== playbook =="
cat captain/CAPTAIN_PROMPT.md captain/GITHUB_BRIEFS.md

echo
echo "Captain boot done."
echo "  ledger : python3 captain/ledger.py show        (see captain/LEDGER.md)"
echo "  batch  : python3 captain/batch_status.py       (ledger vs live GitHub refs)"
echo "  CI     : python3 captain/ci_dispatch.py <owner/repo> --watch 900   (after 'batch ready')"
