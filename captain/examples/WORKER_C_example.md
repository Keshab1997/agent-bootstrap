# EXAMPLE BRIEF — Agent C (different REPO → zero conflict by construction)
#
# This is the safest kind of parallelism: A and B share docify (so they are
# partition by file), C is in flutter-builder, so it cannot collide with anyone.
# Note the repo-specific trap: in flutter-builder, agent-pack/ is canonical and
# the installer copy must be re-embedded — that is the one "check" C runs.

# You are agent C. One task, one branch, then you stop.

You work in your own sandbox. Nobody else is watching this chat. Do the task
below, push your branch, report in the format at the end. Do not ask Keshab
questions — if something is unclear or too big, stop and say so in your report.

## 0. GitHub access — check first, pair only if asked to

```bash
DST=/home/user/agent-bootstrap
[ -f "$DST/gh_app.py" ] || git clone https://github.com/Keshab1997/agent-bootstrap "$DST"
python3 "$DST/gh_app.py" connect     # ALREADY CONNECTED → nothing to do
```

If it prints a code, show it as a headline and wait for Keshab's approval. Never
ask him for a token. Turn ended before he approved?
`python3 "$DST/device_pair.py" poll 60` — same code, still valid.

## 1. Your task

**Goal:** `agent-pack/AGENTS.template.md` explains the single-test-file rule in
one extra sentence, and the installer payload is re-embedded so the byte-for-byte
tests still pass.

**Repository:** `Keshab1997/flutter-builder` · **Branch:** `agent/C/pack-wording` (never `main`)

```bash
cd /home/user
[ -d flutter-builder ] || git clone https://github.com/Keshab1997/flutter-builder.git /home/user/flutter-builder
cd /home/user/flutter-builder
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }; f'
git fetch origin && git checkout -B agent/C/pack-wording origin/main
```

**Files you own (only these):**

- `agent-pack/AGENTS.template.md` (canonical)
- `scripts/install-agent-pack.sh` (**only** via the sync script — never by hand)

**DO NOT TOUCH:** `PACK_VERSION`, any `@v1.x.y` pin, `README.md`, `AGENTS.md`,
`.github/workflows/**`, `tests/**`, `flutter-builder-manual-ci.patch` — and
never `main`, never a tag.

**Interface:** keep the existing section titles and the `preflight.py` wording
unchanged; you are adding one sentence, nothing else.

## 2. Your one check — then push

The repo's trap is that `installer-tests` compares the two copies byte for byte,
so:

```bash
python3 scripts/sync-agent-pack.py            # rewrite the embedded payload
python3 -m pytest tests/ -q                   # ~6 s, the repo's real gate
```

Do not install Flutter (this repo has no Dart code), do not run the installer
end to end, do not dispatch CI.

```bash
git add -A
git commit -m "docs(pack): say why a Dart edit runs only its own test file"
git push -u origin agent/C/pack-wording
```

## 3. Report — copy-paste this block back to Keshab

```
AGENT C DONE
branch: agent/C/pack-wording
sha: <git rev-parse --short HEAD>
files: agent-pack/AGENTS.template.md, scripts/install-agent-pack.sh
check: pytest tests/ -q → 256 passed; sync-agent-pack.py --check → in sync
changed: one sentence added under the check-policy table in the pack template
not touched: PACK_VERSION, pins, workflows, anything that needs a release
blocked: none
```

## 4. Stop rules

Stop and report if the wording change would require a version bump or a release
(that is Keshab's call via the captain), if a test outside your diff goes red, or
if you feel the urge to hand-edit the heredoc — that is exactly the trap this
brief exists to prevent.
