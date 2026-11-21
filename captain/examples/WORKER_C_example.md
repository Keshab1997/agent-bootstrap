# Example task — Agent C

Use the [GitHub brief template](../WORKER_BRIEF_TEMPLATE.md) in `Keshab1997/flutter-builder`.
Arena-lane task: `"arena": {"branch": "auto", "base_sha": null}` on the
attached chat's `arena/*` branch. Put the prose in `BRIEF.md` and the JSON
in `task.json`.
One big deliverable per brief — see the [Speed rules](../CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority).

**Goal:** Document all three cheap-gate rules in the agent pack and guard them with a test.

**Acceptance:**

1. The template explains, one sentence each, why a Dart edit runs only its own test file, why `pub get` uses `--enforce-lockfile`, and why agents never run `flutter build`.
2. The embedded installer payload is regenerated with `python3 scripts/sync-agent-pack.py`, and `--check` passes.
3. `tests/test_pack_gate_rules.py` fails if any of the three sentences disappears from the template or the payload.

**Interface / exclusions:** Edit the canonical template, then sync. Keep existing titles, pins, and preflight wording; no version bump or tag.

```json
{
  "repo": "Keshab1997/flutter-builder",
  "worker": "C",
  "task": "pack-gate-rules",
  "allowed": [
    "agent-pack/AGENTS.template.md",
    "scripts/install-agent-pack.sh",
    "tests/test_pack_gate_rules.py"
  ],
  "commit": "docs(pack): explain the three gate rules and guard them with a test",
  "check": {
    "kind": "pytest",
    "target": "tests"
  },
  "arena": {"branch": "auto", "base_sha": null}
}
```
