# Example task — Agent A

Fill into the [compact brief](../WORKER_BRIEF_TEMPLATE.md). First linked task; `null` is only valid when the attached branch HEAD is at current `main`.
Use a confirmed compatible Flutter pin; the version here is illustrative.

**Goal and acceptance:** Stop Home from overflowing at 360×800 and add a widget test for that viewport.

**Interface / exclusions:** Keep the public widget name and constructor. No theme, routing, localization, or dependency edits.

```json
{
  "repo": "Keshab1997/docify",
  "worker": "A",
  "task": "home-overflow",
  "allowed": [
    "lib/screens/home_screen.dart",
    "test/home_screen_test.dart"
  ],
  "commit": "fix(home): fit the home screen in a 360px viewport",
  "check": {
    "kind": "flutter",
    "version": "3.50.0",
    "test": "test/home_screen_test.dart"
  },
  "arena": {
    "branch": "auto",
    "base_sha": null
  }
}
```
