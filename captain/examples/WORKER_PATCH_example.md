# EXAMPLE — public-repo patch worker, zero authorization

Example only, not a live assignment. The base is a real historical commit;
a live brief must pin the captain's current reviewed base instead.

# You are agent A. One task, one local branch, one patch. No GitHub login.

Do not run `connect`, request authorization, read/copy credentials, configure a
credential helper or push. The captain reviews and publishes. If blocked, report.

**Goal:** Add a short README note that an entirely fresh workspace still needs
its first approval; do not promise permanent or cross-workspace access.
**Public repository:** `Keshab1997/agent-bootstrap`
**Base:** `0d4577fe71a5a1acae73237e3d77ec7b987e5f95`
**Local branch:** `agent/A/docs-fresh-workspace`
**Allowed file:** `README.md`
**Interface:** none; documentation only.
**DO NOT TOUCH:** all Python/shell code, prompts, `captain/`, `app-meta.json`,
`.gitignore`, workflows, secrets, versions and dependencies.

```bash
GIT_TERMINAL_PROMPT=0 git clone https://github.com/Keshab1997/agent-bootstrap.git /home/user/agent-bootstrap
cd /home/user/agent-bootstrap
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git checkout -b agent/A/docs-fresh-workspace 0d4577fe71a5a1acae73237e3d77ec7b987e5f95
```

If a clone/branch already exists, inspect and resume it, never reset it. Read
`AGENTS.md` if present. If public cloning fails, report; do not pair as a workaround.

Make the one documentation change. Run only the repository's offline cheap gate:

```bash
python3 selftest.py
```

Then inspect scope and secrets, commit locally and export:

```bash
git diff --check
git diff -- README.md
git add -- README.md
git diff --cached
git commit -m "docs(auth): clarify the fresh-workspace approval boundary"
git diff --name-only 0d4577fe71a5a1acae73237e3d77ec7b987e5f95 HEAD
mkdir -p /home/user/handoff
git diff --binary --full-index 0d4577fe71a5a1acae73237e3d77ec7b987e5f95 HEAD > /home/user/handoff/A-fresh-workspace.patch
test -s /home/user/handoff/A-fresh-workspace.patch
sha256sum /home/user/handoff/A-fresh-workspace.patch
```

Only `README.md` may appear in the changed paths. No push. Present the actual
patch for download and ask Keshab to attach it to the captain's chat with this
report (fill the output fields with real results, never the example guesses):

```text
AGENT A DONE
mode: patch (no GitHub authorization)
repo: Keshab1997/agent-bootstrap
base: 0d4577fe71a5a1acae73237e3d77ec7b987e5f95
branch: agent/A/docs-fresh-workspace (local only)
sha: <actual full local commit SHA>
patch: A-fresh-workspace.patch
sha256: <actual checksum>
files: README.md
check: python3 selftest.py → <actual result>
changed: <actual one-sentence summary>
not touched: code, prompts, workflows, credentials, settings
blocked: <none or actual blocker>
```

Stop if any other file or a credential is needed. A worker's path is not a shared
file: the patch attachment itself must reach the captain.
