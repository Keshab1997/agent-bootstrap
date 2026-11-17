# EXAMPLE BRIEF — Agent C (different REPO → zero conflict by construction)
#
# This is the safest kind of parallelism: A and B share docify (so they are
# partition by file), C is in flutter-builder, so it cannot collide with anyone.
# Note the repo-specific trap: in flutter-builder, agent-pack/ is canonical and
# the installer copy must be re-embedded — that is the one "check" C runs.

Fill these task fields into the current [worker template](../WORKER_BRIEF_TEMPLATE.md).
This example is not a standalone prompt. Leave the real-branch selection and
reporting blocks intact; don't use the fallback name in a linked Arena chat.

**Agent:** C

**Goal:** `agent-pack/AGENTS.template.md` explains the single-test-file rule in
one extra sentence, and the installer payload is re-embedded so the byte-for-byte
tests still pass.

**Repository:** `Keshab1997/flutter-builder`  ·  **Arena branch:** `auto` (or the exact branch shown in this worker's chat)  ·  **Standalone fallback:** `agent/C/pack-wording`

**Files you own (only these):**

- `agent-pack/AGENTS.template.md` (canonical)
- `scripts/install-agent-pack.sh` (**only** via the sync script — never by hand)

**DO NOT TOUCH:** `PACK_VERSION`, any `@v1.x.y` pin, `README.md`, `AGENTS.md`,
`.github/workflows/**`, `tests/**`, `flutter-builder-manual-ci.patch` — and
never `main`, never a tag.

**Interface:** keep the existing section titles and the `preflight.py` wording
unchanged; you are adding one sentence, nothing else.

After editing the canonical template, run `python3 scripts/sync-agent-pack.py`
to update the embedded payload before the check.

**Check:** `python3 -m pytest tests/ -q`

**Stage paths:** `agent-pack/AGENTS.template.md scripts/install-agent-pack.sh`

**Commit:** `docs(pack): say why a Dart edit runs only its own test file`
