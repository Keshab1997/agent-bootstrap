# Example task — Agent B

Fill into the [compact brief](../WORKER_BRIEF_TEMPLATE.md). First linked task; `null` is only valid when the attached branch HEAD is at current `main`.
Use a confirmed compatible Flutter pin; the version here is illustrative.

**Goal and acceptance:** Read the Paywall strings from `app_strings.dart`; preserve the existing English UI and test it.

**Interface / exclusions:** Add `paywallTitle = 'Unlock everything'`, `paywallSubtitle = 'One payment. No subscription.'`, and `paywallCta = 'Continue'`. Do not rename existing keys or edit Home.

```json
{
  "repo": "Keshab1997/docify",
  "worker": "B",
  "task": "paywall-strings",
  "allowed": [
    "lib/screens/paywall_screen.dart",
    "lib/l10n/app_strings.dart",
    "test/paywall_screen_test.dart"
  ],
  "commit": "refactor(paywall): read user-facing strings from app_strings",
  "check": {
    "kind": "flutter",
    "version": "3.50.0",
    "test": "test/paywall_screen_test.dart"
  },
  "arena": {
    "branch": "auto",
    "base_sha": null
  }
}
```
