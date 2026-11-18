# Example task — Agent C

Use the [GitHub brief template](../WORKER_BRIEF_TEMPLATE.md) in `Keshab1997/flutter-builder`.
First task with that repo attached in Arena; `null` is valid only when the
attached branch is at current `main`. Put the prose in `BRIEF.md` (with
the approved tracking issue if available) and the JSON in `task.json`.

**Goal and acceptance:** Explain the single-test-file rule in one sentence. Update the embedded installer payload so the parity tests pass.

**Interface / exclusions:** Use `python3 scripts/sync-agent-pack.py` after editing the canonical template. Keep existing titles, pins, and preflight wording; no version bump or tag.

```json
{
  "repo": "Keshab1997/flutter-builder",
  "worker": "C",
  "task": "pack-wording",
  "allowed": [
    "agent-pack/AGENTS.template.md",
    "scripts/install-agent-pack.sh"
  ],
  "commit": "docs(pack): say why a Dart edit runs only its own test file",
  "check": {
    "kind": "pytest",
    "target": "tests"
  },
  "arena": {
    "branch": "auto",
    "base_sha": null
  }
}
```
