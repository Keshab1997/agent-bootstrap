# WORKER BRIEF TEMPLATE — the captain fills this, Keshab pastes it, the worker runs it
#
# Rules for the captain:
#   * every field filled, no placeholders left, no essays
#   * {{BRANCH}} is always agent/<letter>/<short-slug> — never `main`
#   * CHECK is one command, and it must be the cheap one
#   * DO NOT TOUCH lists every shared surface in the repo
#   * if two briefs would touch the same file, they are not parallel — stop

✂ ═══════════════ COPY FROM HERE (give the whole block to the worker) ═══════════════

# You are agent {{LETTER}}. One task, one branch, then you stop.

You work in your own sandbox. Nobody else is watching this chat. Do the task
below, push your branch, report in the format at the end. Do not ask Keshab
questions — if something is unclear or too big, stop and say so in your report.

## 0. GitHub access — check first, pair only if asked to

```bash
DST=/home/user/agent-bootstrap
[ -f "$DST/gh_app.py" ] || git clone https://github.com/Keshab1997/agent-bootstrap "$DST"
python3 "$DST/gh_app.py" connect     # if it says ALREADY CONNECTED: nothing to do
```

If it prints a code like `XXXX-XXXX`, show it to Keshab as a headline
(*"Open https://github.com/login/device and enter XXXX-XXXX"*) and wait for his
approval. Never ask him for a token. If your turn ends before he approves:
`python3 "$DST/device_pair.py" start` then `python3 "$DST/device_pair.py" poll 60`
— the code stays valid ~15 min, do **not** take a new one.

## 1. Your task

**Goal (one sentence, testable):** {{GOAL}}

**Repository:** `Keshab1997/{{REPO}}`  ·  **Branch:** `{{BRANCH}}`  (branch only — never `main`)

```bash
cd /home/user
[ -d {{REPO}} ] || git clone https://github.com/Keshab1997/{{REPO}}.git /home/user/{{REPO}}
cd /home/user/{{REPO}}
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }; f'
git fetch origin && git checkout -B {{BRANCH}} origin/main
```

**Files you own (only these):**

{{ALLOWED_FILES}}

**DO NOT TOUCH** (they belong to the captain or to another worker):

- `pubspec.yaml`, `pubspec.lock`, any version bump, any dependency addition
- `.github/workflows/**`, anything under `android/` and `ios/`
- `AGENTS.md` managed block, `tool/**`, `secrets/**`
- any file another worker owns in this batch — assumed, not negotiable
- **`main` itself. You never push, merge or rebase `main`.**

**Interface (exact names/strings the captain froze — use these verbatim):**

{{INTERFACE}}

## 2. Your one check — then push

Run exactly this, and only this:

```bash
{{CHECK}}
```

If it fails: fix **your** change until it passes. Never run the full test
battery, `flutter analyze`, `flutter build`, `gradlew`, or CI — those are the
captain's call, and waiting on them is the one thing this setup is designed to
avoid.

Then commit and push your branch:

```bash
git add -A
git commit -m "{{COMMIT_MESSAGE}}"
git push -u origin {{BRANCH}}
```

Commit message style: `type(scope): what changed` — `fix(home): …`,
`feat(settings): …`, `docs: …`. One concern per commit. If your work needs a
second commit, make it; do not squash history you do not own.

## 3. Report — copy-paste this block back to Keshab

```
AGENT {{LETTER}} DONE
branch: {{BRANCH}}
sha: <git rev-parse --short HEAD>
files: <git diff --stat origin/main...HEAD | tail -1>
check: {{CHECK}} → <pass/fail + one line of evidence>
changed: <one sentence: what is different now>
not touched: <anything you deliberately left alone>
blocked: <none | what stopped you, and what decision is needed>
```

## 4. Stop rules

Stop and report (do **not** improvise) when: the task needs a file you do not
own, the change grows past the goal above, the interface seems wrong, the check
fails for a reason that is not your change, or you would need a decision from
Keshab. A stopped worker with a clear report is useful; a wandering worker
pushing a surprise diff is not.

✂ ═══════════════ COPY ENDS HERE ═══════════════
