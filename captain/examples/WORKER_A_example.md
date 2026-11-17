# EXAMPLE BRIEF — Agent A (Dart edit, single test file)
#
# Batch 1 on Keshab1997/docify. Splits by FILE, so A/B/C can run in parallel
# without touching each other. The captain fills the same template for B and C.

Fill these task fields into the current [worker template](../WORKER_BRIEF_TEMPLATE.md).
This example is not a standalone prompt. Leave the real-branch selection and
reporting blocks intact; don't use the fallback name in a linked Arena chat.

**Agent:** A

**Goal:** the home screen stops overflowing horizontally on a 360×800 phone viewport,
with a widget test that renders it at that size and proves it.

**Repository:** `Keshab1997/docify`  ·  **Arena branch:** `auto` (or the exact branch shown in this worker's chat)  ·  **Standalone fallback:** `agent/A/home-overflow`

**Files you own (only these):**

- `lib/screens/home_screen.dart`
- `test/home_screen_test.dart` (create if missing)

**DO NOT TOUCH:** `pubspec.yaml`, `pubspec.lock`, `lib/main.dart`,
`lib/theme/**`, `.github/workflows/**`, `android/**`, `ios/**`, `tool/**`,
`AGENTS.md` — and never `main`.

**Interface:** keep the public widget name `HomeScreen` and its constructor
signature exactly as it is; only the internal layout changes. Do not rename
anything, do not add a package.

**Check:** `python3 tool/preflight.py && flutter test test/home_screen_test.dart`

**Stage paths:** `lib/screens/home_screen.dart test/home_screen_test.dart`

**Commit:** `fix(home): fit the home screen in a 360px viewport`
