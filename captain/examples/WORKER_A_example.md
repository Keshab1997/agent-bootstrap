# EXAMPLE BRIEF — Agent A (Dart edit, single test file)
#
# Batch 1 on Keshab1997/docify. Splits by FILE, so A/B/C can run in parallel
# without touching each other. The captain fills the same template for B and C.

# You are agent A. One task, one branch, then you stop.

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

**Goal:** the home screen stops overflowing horizontally on a 360×800 phone viewport,
with a widget test that renders it at that size and proves it.

**Repository:** `Keshab1997/docify` · **Branch:** `agent/A/home-overflow` (never `main`)

```bash
cd /home/user
[ -d docify ] || git clone https://github.com/Keshab1997/docify.git /home/user/docify
cd /home/user/docify
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }; f'
git fetch origin && git checkout -B agent/A/home-overflow origin/main
```

**Files you own (only these):**

- `lib/screens/home_screen.dart`
- `test/home_screen_test.dart` (create if missing)

**DO NOT TOUCH:** `pubspec.yaml`, `pubspec.lock`, `lib/main.dart`,
`lib/theme/**`, `.github/workflows/**`, `android/**`, `ios/**`, `tool/**`,
`AGENTS.md` — and never `main`.

**Interface:** keep the public widget name `HomeScreen` and its constructor
signature exactly as it is; only the internal layout changes. Do not rename
anything, do not add a package.

## 2. Your one check — then push

```bash
export PATH=/var/tmp/flutter/bin:$PATH PUB_CACHE=/var/tmp/pub-cache   # SDK, see note
flutter test test/home_screen_test.dart
```

The Flutter SDK is not installed in your sandbox. If that command cannot find
`flutter`, install it once (~50 s, no credentials):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) \
  --root /var/tmp/flutter --quiet --json
```

Run **only** that one test file. Not the full suite, not `flutter analyze`, not
`flutter build`.

Then:

```bash
git add -A
git commit -m "fix(home): fit the home screen in a 360px viewport"
git push -u origin agent/A/home-overflow
```

## 3. Report — copy-paste this block back to Keshab

```
AGENT A DONE
branch: agent/A/home-overflow
sha: <git rev-parse --short HEAD>
files: lib/screens/home_screen.dart, test/home_screen_test.dart
check: flutter test test/home_screen_test.dart → pass, 1 test, no RenderFlex overflow
changed: wrapped the header row in Flexible and clipped the trailing chip row
not touched: theme, routing, pubspec, workflows
blocked: none
```

## 4. Stop rules

Stop and report if the fix needs `lib/theme/**` or `pubspec.yaml` (another worker
or the captain owns them), if the overflow turns out to be caused by a shared
widget used by other screens, or if the test fails for a reason outside your diff.
