# Example task — Agent C

Fill into the [compact brief](../WORKER_BRIEF_TEMPLATE.md). Ordinary chat with **no repo attached**. Omit `arena` for a new standalone branch.

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
  }
}
```
