# Example task — Agent B

Use the [GitHub brief template](../WORKER_BRIEF_TEMPLATE.md) in `Keshab1997/docify`.
First task with that repo attached in Arena; `null` is valid only when the
attached branch is at current `main`. Put the prose in `BRIEF.md` (with
the approved tracking issue if available) and the JSON in `task.json`.
Use a confirmed compatible Flutter pin; this version is illustrative.
One big deliverable per brief — see the [Speed rules](../CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority).

**Goal:** Complete the Paywall: plan cards, a restore-purchases button, and every user-facing string read from `app_strings.dart`, with widget tests.

**Acceptance:**

1. Add and use `paywallTitle = 'Unlock everything'`, `paywallSubtitle = 'One payment. No subscription.'`, `paywallCta = 'Continue'` and `paywallRestore = 'Restore purchases'`.
2. Plans render as `PlanCard`s; the selected plan is highlighted and the CTA buys that plan.
3. `RestorePurchasesButton` calls the existing purchase service's `restore()` and shows a SnackBar on success and on failure.
4. `test/paywall_screen_test.dart` covers the strings, plan selection and both restore outcomes.

**Interface / exclusions:** Do not rename existing string keys, edit Home, or change the purchase service itself.

```json
{
  "repo": "Keshab1997/docify",
  "worker": "B",
  "task": "paywall-complete",
  "allowed": [
    "lib/screens/paywall_screen.dart",
    "lib/widgets/paywall/plan_card.dart",
    "lib/widgets/paywall/restore_purchases_button.dart",
    "lib/l10n/app_strings.dart",
    "test/paywall_screen_test.dart"
  ],
  "commit": "feat(paywall): plan cards, restore purchases and shared strings",
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
