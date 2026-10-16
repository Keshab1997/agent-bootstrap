# EXAMPLE BRIEF — Agent B (same repo as A, different files, same batch)

# You are agent B. One task, one branch, then you stop.

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

**Goal:** every user-visible string on the paywall screen comes from
`lib/l10n/app_strings.dart` instead of being hardcoded, and the screen renders
identically (en) with the new keys.

**Repository:** `Keshab1997/docify` · **Branch:** `agent/B/paywall-strings` (never `main`)

```bash
cd /home/user
[ -d docify ] || git clone https://github.com/Keshab1997/docify.git /home/user/docify
cd /home/user/docify
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }; f'
git fetch origin && git checkout -B agent/B/paywall-strings origin/main
```

**Files you own (only these):**

- `lib/screens/paywall_screen.dart`
- `lib/l10n/app_strings.dart`
- `test/paywall_screen_test.dart` (create if missing)

**DO NOT TOUCH:** `lib/screens/home_screen.dart` (**agent A owns it in this
batch**), `lib/theme/**`, `pubspec.yaml`, `.github/workflows/**`, `android/**`,
`ios/**`, `tool/**`, `AGENTS.md` — and never `main`.

**Interface (frozen by the captain — use these exact keys):**

```dart
// lib/l10n/app_strings.dart — add only; do not rename existing keys
static const paywallTitle = 'Unlock everything';
static const paywallSubtitle = 'One payment. No subscription.';
static const paywallCta = 'Continue';
```

## 2. Your one check — then push

```bash
export PATH=/var/tmp/flutter/bin:$PATH PUB_CACHE=/var/tmp/pub-cache
flutter test test/paywall_screen_test.dart
```

SDK missing? Install once (~50 s):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) \
  --root /var/tmp/flutter --quiet --json
```

Only that one test file — not the full suite, not `flutter analyze`.

```bash
git add -A
git commit -m "refactor(paywall): read user-facing strings from app_strings"
git push -u origin agent/B/paywall-strings
```

## 3. Report — copy-paste this block back to Keshab

```
AGENT B DONE
branch: agent/B/paywall-strings
sha: <git rev-parse --short HEAD>
files: lib/screens/paywall_screen.dart, lib/l10n/app_strings.dart, test/paywall_screen_test.dart
check: flutter test test/paywall_screen_test.dart → pass
changed: 3 hardcoded strings replaced by the frozen keys; no visual change
not touched: home_screen.dart (agent A), theme, pubspec
blocked: none
```

## 4. Stop rules

Stop and report if a string belongs to a shared widget outside your files, if
`app_strings.dart` already has a key that means the same thing (the captain
decides the merge of duplicates), or if the paywall test fails outside your diff.
