#!/usr/bin/env bash
# Converge one fleet repo on the flutter-builder pack in the working tree:
# refresh tool/* + the AGENTS.md managed block, move every reusable-workflow
# pin to the same version, run the repo's own preflight gate, then commit and
# push straight to its default branch (Keshab's solo-work law: no branches, no
# PRs). The version is read from the pack, never typed here, so the pack and
# the pins cannot drift apart again.
#
# Usage: fleet-bump.sh <repo-name> [--dry-run]
set -uo pipefail

name="${1:?repo name}"; dry="${2:-}"
root="/var/tmp/fleet/$name"
builder="${FLUTTER_BUILDER:-/home/user/flutter-builder}"
pack="$builder/scripts/install-agent-pack.sh"
bump="$builder/scripts/bump-ref.sh"
token="${GH_TOKEN_FILE:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/secrets/gh_token.txt}"

ref="$(sed -n 's/^PACK_VERSION=//p' "$pack" | head -1)"
[ -n "$ref" ] || { echo "$name NO_PACK_VERSION"; exit 1; }

rm -rf "$root"; mkdir -p /var/tmp/fleet
git clone -q --depth 1 "https://github.com/Keshab1997/$name.git" "$root" \
  || { echo "$name CLONE_FAIL"; exit 1; }
cd "$root" || exit 1
branch="$(git rev-parse --abbrev-ref HEAD)"
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git config credential.helper '!f() { echo "username=x-access-token"; echo "password=$(cat '"$token"')"; }; f'

bash "$pack" ${dry:+--dry-run} --force >"/tmp/pack-$name.log" 2>&1; pack_rc=$?
bash "$bump" --ref "$ref" ${dry:+--dry-run} >"/tmp/ref-$name.log" 2>&1; ref_rc=$?
after="$(python3 tool/preflight.py 2>&1 | tail -1)"

if [ "$pack_rc" -ne 0 ] || [ "$ref_rc" -ne 0 ]; then
  echo "$name TOOL_FAIL pack=$pack_rc ref=$ref_rc :: $(grep -i -m1 'error\|refus\|missing' /tmp/pack-$name.log /tmp/ref-$name.log | head -1)"
  exit 1
fi
# Self-check: every flutter-builder pin under .github/workflows must be $ref.
pins="$(grep -rhoE 'flutter-builder/\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml@[^[:space:]#"]+' \
        .github/workflows 2>/dev/null | sed 's/.*@//' | sort -u | tr '\n' ' ')"
case " $pins " in *" $ref "*) ;; *) echo "$name PIN_FAIL found: ${pins:-none}"; exit 1 ;; esac
if [ -n "$pins" ] && [ "$(echo "$pins" | wc -w)" -ne 1 ]; then
  echo "$name PIN_FAIL mixed: $pins"; exit 1
fi

changed="$(git status --porcelain | wc -l)"
if [ "$changed" -eq 0 ]; then echo "$name ALREADY_AT $ref ($branch)"; exit 0; fi
if [ -n "$dry" ]; then
  echo "$name DRY_RUN would change $changed file(s) on $branch (pins: ${pins:-none})"
  git status --porcelain | head -12
  exit 0
fi
git add -A
git commit -q -F - <<MSG
chore(agent): flutter-builder agent pack and CI pin $ref

Refreshes tool/* and the AGENTS.md managed block with
install-agent-pack.sh --force ($ref) and moves every
Keshab1997/flutter-builder reusable-workflow pin to $ref with bump-ref.sh,
so the pack version and the CI pin finally agree.

v1.18.8 reworded the pack's CI law: CI is one dispatch per batch, run by the
agent once the batch is ready (captain/ci_dispatch.py), never mid-task, and
Captain workers never dispatch. v1.18.9 fixed preflight: it now honours the
file's own // ignore: and // ignore_for_file: directives (generated l10n
carries them, so the gate no longer reports what flutter analyze suppresses)
and reports an unused import on the import's own line.

Local gate: python3 tool/preflight.py
MSG
git push -q origin "HEAD:$branch" \
  && echo "$name PUSHED $(git rev-parse --short HEAD) on $branch | files=$changed | pins=$pins| preflight: $after" \
  || echo "$name PUSH_FAIL"
