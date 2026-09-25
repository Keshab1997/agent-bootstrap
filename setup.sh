#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# agent-bootstrap : one-shot setup for an AI agent / fresh machine.
#
#   curl -fsSL https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/setup.sh | bash
#
# What it does:
#   1. checks python3 + network to api.github.com
#   2. fetches gh_app.py + app-meta.json (clone if git is available, else raw)
#   3. starts the OAuth device flow and prints the 8-character user code
#   4. polls until the human approves, then stores the token in ./secrets/
#
# Nothing in this script or repo is a secret. No credentials are downloaded.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO="Keshab1997/agent-bootstrap"
BRANCH="main"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
DEST="${BOOTSTRAP_DIR:-$PWD/agent-bootstrap}"

say()  { printf '%s\n' "$*"; }
step() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
die()  { printf '\n\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

say "=============================================================="
say " agent-bootstrap -- GitHub App connector (zero-secret)"
say " repo   : https://github.com/${REPO}"
say " target : ${DEST}"
say "=============================================================="

# --- 1. prerequisites ------------------------------------------------------
step "checking prerequisites"
command -v python3 >/dev/null 2>&1 || die "python3 not found (need >=3.8)"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' \
  || die "python3 too old: $(python3 -V 2>&1)"
say "  python3 : $(python3 -V 2>&1)"

if command -v curl >/dev/null 2>&1; then NET=curl
elif command -v wget >/dev/null 2>&1; then NET=wget
else die "need curl or wget"; fi
say "  fetcher : ${NET}"

fetch() { # fetch <url> <outfile>
  if [ "$NET" = curl ]; then curl -fsSL --max-time 30 "$1" -o "$2"
  else wget -q -T 30 -O "$2" "$1"; fi
}

fetch "https://api.github.com" /tmp/_ab_probe.$$ 2>/dev/null \
  || say "  ! api.github.com probe failed (may still work)"
rm -f /tmp/_ab_probe.$$
say "  network : api.github.com reachable"

# --- 2. get the files ------------------------------------------------------
step "fetching the bootstrap kit"
mkdir -p "$DEST"
if command -v git >/dev/null 2>&1 && [ -d "$DEST/.git" ]; then
  ( cd "$DEST" && git pull --ff-only -q ) && say "  updated existing clone"
elif command -v git >/dev/null 2>&1; then
  git clone -q --depth 1 "https://github.com/${REPO}.git" "$DEST" \
    && say "  cloned ${REPO}" \
    || { say "  git clone failed, falling back to raw download"
         fetch "$RAW/gh_app.py"     "$DEST/gh_app.py"
         fetch "$RAW/app-meta.json" "$DEST/app-meta.json"
         fetch "$RAW/vault.py"      "$DEST/vault.py" 2>/dev/null || true; }
else
  fetch "$RAW/gh_app.py"     "$DEST/gh_app.py"
  fetch "$RAW/app-meta.json" "$DEST/app-meta.json"
  fetch "$RAW/vault.py"      "$DEST/vault.py" 2>/dev/null || true
  say "  downloaded raw files"
fi
chmod +x "$DEST/gh_app.py" 2>/dev/null || true

[ -f "$DEST/gh_app.py" ] || die "gh_app.py missing -- download failed"
say "  files   : $(ls "$DEST" | tr '\n' ' ')"

# --- 3. already connected? -------------------------------------------------
step "checking for an existing token"
if ( cd "$DEST" && python3 gh_app.py status >/dev/null 2>&1 ); then
  ( cd "$DEST" && python3 gh_app.py status )
  say ""
  say "Already connected -- nothing to do."
  say "  whoami : python3 ${DEST}/gh_app.py whoami"
  exit 0
fi
say "  no valid token found, pairing required"

# --- 4. device flow --------------------------------------------------------
step "starting the OAuth device flow"
say ""
say "  >>> A HUMAN MUST APPROVE THIS IN A BROWSER <<<"
say ""
( cd "$DEST" && python3 gh_app.py connect )

step "done"
say "  token stored in : ${DEST}/secrets/gh_token.txt  (chmod 600)"
say "  try it out      : python3 ${DEST}/gh_app.py whoami"
say "  list repos      : python3 ${DEST}/gh_app.py repos --limit 20"
say "  raw API call    : python3 ${DEST}/gh_app.py api GET /user"
say "  disconnect      : python3 ${DEST}/gh_app.py revoke"
