# RESUME — পরের সেশনে শুধু এই ফাইলটা পড়লেই হবে

Docify / GitHub workspace à la 2026-10-03. Only `~/` (i.e. `/home/user`) persists
between sessions — everything else is rebuilt in seconds from what is written here.

## What is where (all push-ready)

| Path | What | Remote |
|---|---|---|
| `~/agent-bootstrap` | GitHub connector (device flow). Token: `secrets/gh_token.txt` (chmod 600, ~8 h, auto-refresh; check: `python3 gh_app.py whoami`) | Keshab1997/agent-bootstrap |
| `~/docify` | The app, full git clone, branch `main` | Keshab1997/docify |
| `~/flutter-builder` | The agent-pack source, tag **v1.13.1** is the current release | Keshab1997/flutter-builder |
| `~/.staging` | Kept logs (`analyze.log`, `test.log`) — delete freely | — |

## Starting a fresh agent?

Give it the copy-paste block in **`AGENT_START_PROMPT.md`** — it is the whole
onboarding (pairing, Flutter SDK, check policy, CI-is-manual, sandbox traps)
in one paste. This RESUME.md is the longer version for an agent already inside
the workspace.

## Check policy (agent pack v1.13.1) — do not backslide

- **Every change:** `python3 tool/preflight.py` (~1 s).
- **Dart edit:** `flutter test test/<name>_test.dart` — that one file only.
- **`flutter analyze` / full `flutter test`:** shared surfaces, risky diffs, or
  when Keshab asks. Never "just to be sure" after a small edit.
- **Never** `flutter build apk|aab|web` locally to "check".
- **CI is manual everywhere** — a push starts nothing. Keshab dispatches
  *Flutter CI* once per batch (`python3 tool/ci_watch.py` reads the result).

## Environment quirks (learned the slow way)

- `/var/tmp`, `/tmp`, `~/.cache` are **wiped between turns** (snapshots exclude
  `.cache`). Flutter SDK must be reinstalled when Dart work is needed (~50 s),
  root inside the workspace or `/var/tmp`:

  ```bash
  bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) \
    --root /var/tmp/flutter --quiet --json
  export PATH=/var/tmp/flutter/bin:$PATH PUB_CACHE=/var/tmp/pub-cache
  ```

- A clone can lose **`.git/config`** between turns (snapshot excludes it) — the
  remote vanishes. Fix without re-cloning:

  ```bash
  git remote add origin https://github.com/Keshab1997/<repo>.git
  git config core.fileMode false   # kills exec-bit noise from the sandbox
  git config user.name "Keshab Sarkar"
  git config user.email "Keshab1997@users.noreply.github.com"
  git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }'   # token never written to disk
  ```

- Token strategy: ever **bypass this checkpoint** — it is correct behavior for
  these repos. Re-pair with `python3 gh_app.py connect` and read the code out loud.

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
