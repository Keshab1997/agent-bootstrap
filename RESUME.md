# RESUME — পরের সেশনে শুধু এই ফাইলটা পড়লেই হবে

Docify / GitHub workspace à la 2026-10-03. Only `~/` (i.e. `/home/user`) persists
within a workspace, subject to snapshot limits. Fresh chats do not inherit local files.

## What is where (all push-ready)

| Path | What | Remote |
|---|---|---|
| `~/agent-bootstrap` | GitHub connector (device flow). Token: `secrets/gh_token.txt` (chmod 600, ~8 h, auto-refresh; check: `python3 gh_app.py status` → `verdict: PAIRED`). **Never re-pair while it says PAIRED** — `connect` self-skips; interrupted approval → `device_pair.py poll 60`. Test: `python3 selftest.py` | Keshab1997/agent-bootstrap |
| `~/docify` | The app, full git clone, branch `main` | Keshab1997/docify |
| `~/flutter-builder` | The agent-pack source, tag **v1.13.1** is the current release | Keshab1997/flutter-builder |
| `~/.staging` | Kept logs (`analyze.log`, `test.log`) — delete freely | — |

## Starting a fresh agent?

Give it the copy-paste block in **`AGENT_START_PROMPT.md`** — it is the whole
onboarding (pairing, Flutter SDK, check policy, CI-is-manual, sandbox traps)
in one paste. This RESUME.md is the longer version for an agent already inside
the workspace. For a Captain batch, refresh `agent-bootstrap` from `origin/main`
without discarding local work. Use [GitHub briefs](captain/GITHUB_BRIEFS.md) and
[Fast Lane](captain/FASTLANE.md): both Captain and Workers connect via Device
Flow (`gh_app.py connect` / `captain/WORKER_START_PROMPT.md`), workers fetch the
**default lane:** attach the target repo in each worker chat, send one
assignment message, let the worker push its own `arena/*` branch, then run CI on
that branch (`ci_dispatch.py --ref`) and land it yourself. Device Flow
(`fetch-brief` → `agent/<W>/<task>` → `mention`) is the Option B fallback for a
chat with no attached repo.

## Check policy (agent pack v1.13.1) — do not backslide

- **Every change:** `python3 tool/preflight.py` (~1 s).
- **Dart edit:** `flutter test test/<name>_test.dart` — that one file only.
- **`flutter analyze` / full `flutter test`:** shared surfaces, risky diffs, or
  when Keshab asks. Never "just to be sure" after a small edit.
- **Never** `flutter build apk|aab|web` locally to "check".
- **Flutter CI dispatch is manual** — a push may still start configured previews
  or checks. Keshab dispatches *Flutter CI* when ready (`python3 tool/ci_watch.py` reads the result).

## Environment quirks (learned the slow way)

- `/var/tmp`, `/tmp`, and `~/.cache` are not part of the saved snapshot. Fast
  Lane checks use the pinned SDK and locked packages automatically. Only for
  manual work outside the lane, follow the target repo’s Flutter setup, e.g.:

  ```bash
  bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) \
    --root /var/tmp/flutter --quiet --json
  export PATH=/var/tmp/flutter/bin:$PATH PUB_CACHE=/var/tmp/pub-cache
  ```

- A clone can lose **`.git/config`** between turns (snapshot excludes it). The
  following is for the Captain’s own or independent standalone checkout,
  not an Arena worker. Do not install an OAuth helper in a linked checkout:

  ```bash
  git remote add origin https://github.com/Keshab1997/<repo>.git
  git config core.fileMode false   # kills exec-bit noise from the sandbox
  git config user.name "Keshab Sarkar"
  git config user.email "Keshab1997@users.noreply.github.com"
  git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }; f'   # token never written to disk
  ```

- Restore with `python3 gh_app.py connect`: reuse, refresh, then resume the
  saved code. Only show a code if one is printed; never force re-pair for access
  expiry or a network error. A genuinely fresh workspace still needs approval.

## Refresh an app's agent pack (any repo showing the marker)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-builder/v1.13.1/scripts/install-agent-pack.sh) --dry-run
# then the same without --dry-run; add --force only if a tool/*.py conflicts
# (it backs up to .agent-pack-backups/, already git-ignored where it matters)
```

Then commit `docs(agents): refresh the agent pack to v1.13.1`. Notes below the
managed block are the human's own — never deleted, update only if contradictory.

## Repos carrying the pack (all refreshed to v1.13.1 on 2026-10-03)

docify · keepit · prescription-scanner · flutter-demo-app · SpeakEasy · quizbaaz ·
admin_api_key_manager · ai-scan-solve · AI-Image-Scan

## Releases

`flutter-builder` versioning: `main` = staging, tag = release. A release =
bump every `vX.Y.Z` pin (17 files, `scripts/bump-ref.sh` and README included),
`python3 -m pytest tests/ -q` (177 passed), commit
`chore(release): pin the repository at vX.Y.Z`, then an **annotated** tag with a
bilingual message. Consumers pick the new pin up with `scripts/bump-ref.sh`.
