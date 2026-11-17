# EXAMPLE BRIEF — Agent B (same repo as A, different files, same batch)

Fill these task fields into the current [worker template](../WORKER_BRIEF_TEMPLATE.md).
This example is not a standalone prompt. Leave the real-branch selection and
reporting blocks intact; don't use the fallback name in a linked Arena chat.

**Agent:** B

**Goal:** every user-visible string on the paywall screen comes from
`lib/l10n/app_strings.dart` instead of being hardcoded, and the screen renders
identically (en) with the new keys.

**Repository:** `Keshab1997/docify`  ·  **Arena branch:** `auto` (or the exact branch shown in this worker's chat)  ·  **Standalone fallback:** `agent/B/paywall-strings`

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

**Check:** `python3 tool/preflight.py && flutter test test/paywall_screen_test.dart`

**Stage paths:** `lib/screens/paywall_screen.dart lib/l10n/app_strings.dart test/paywall_screen_test.dart`

**Commit:** `refactor(paywall): read user-facing strings from app_strings`
