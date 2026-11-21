# Example task — Agent A

Use the [GitHub brief template](../WORKER_BRIEF_TEMPLATE.md) in `Keshab1997/docify`.
Device-Flow task: omits `"arena"`, branches `agent/A/home-screen-complete`
from `origin/main` (`"base_sha": null`), and posts `@Keshab1997` to `"tracker"`
after push. Put the prose in `BRIEF.md` and the JSON in `task.json`.
Use a confirmed compatible Flutter pin; this version is illustrative.
One big deliverable per brief — see the [Speed rules](../CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority).

**Goal:** Finish the Home screen: responsive layout, document cards, and empty/loading/error states, all covered by widget tests.

**Acceptance:**

1. No overflow at 360×800, 412×915 and 800×1280.
2. Documents render as `DocumentCard`s; tapping one calls the existing `onOpen` callback.
3. Empty, loading and error states each have their own widget; the error state's Retry button calls the existing `onRefresh` callback.
4. `test/home_screen_test.dart` covers all three viewports and all three states.

**Interface / exclusions:** Keep `HomeScreen`'s public name and constructor. No theme, routing, localization, or dependency edits.

```json
{
  "repo": "Keshab1997/docify",
  "worker": "A",
  "task": "home-screen-complete",
  "allowed": [
    "lib/screens/home_screen.dart",
    "lib/widgets/home/home_header.dart",
    "lib/widgets/home/document_card.dart",
    "lib/widgets/home/home_states.dart",
    "test/home_screen_test.dart"
  ],
  "commit": "feat(home): responsive home with cards and empty, loading and error states",
  "check": {
    "kind": "flutter",
    "version": "3.50.0",
    "test": "test/home_screen_test.dart"
  },
  "base_sha": null
}
```
