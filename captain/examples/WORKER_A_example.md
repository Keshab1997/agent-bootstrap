# Example task — Agent A

Use the [GitHub brief template](../WORKER_BRIEF_TEMPLATE.md) in `Keshab1997/docify`.
First task with that repo attached in Arena; `null` is valid only when the
attached branch is at current `main`. Put the prose in `BRIEF.md` (with
the approved tracking issue if available) and the JSON in `task.json`.
Use a confirmed compatible Flutter pin; this version is illustrative.

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
